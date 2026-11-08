"""Pipeline pandas determinista: carrega, limpa e registra a qualidade do dataset.

Fonte original: ``data/sales.csv`` (não inventar colunas). Se o arquivo não
existir, gera um sintético determinístico (seed 42) com as colunas esperadas.
Python calcula, IA só explica: nenhum LLM aqui.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Utilidades de normalização
# ---------------------------------------------------------------------------

_MAPA_STATUS: dict[str, str] = {
    "concluido": "concluido",
    "concluído": "concluido",
    "complete": "concluido",
    "completed": "concluido",  # idempotente para concluído
    "cancelado": "cancelado",
    "cancelada": "cancelado",
    "canceled": "cancelado",
    "cancelled": "cancelado",
    "pendente": "pendente",
    "pende": "pendente",
    "pending": "pendente",
    "aguardando": "pendente",
}


def _sem_acento(texto: str) -> str:
    """Remove acentos (á→a, ç→c) preservando o restante."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def normalizar_status(valor: object) -> str:
    """Padroniza status → concluido|cancelado|pendente (tx original fora do mapa mantida)."""
    if pd.isna(valor):
        return ""
    texto = str(valor).strip().lower()
    if not texto:
        return ""
    # Tenta mapa com acento preservado primeiro, depois sem acento.
    canon = _MAPA_STATUS.get(texto) or _MAPA_STATUS.get(_sem_acento(texto))
    return canon if canon is not None else texto


def _detectar_separador(path: Path) -> str:
    """Detecta separador: testa ';' primeiro (se há ';' no cabeçalho), senão ','."""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        cabecalho = fh.readline()
    if ";" in cabecalho:
        return ";"
    return ","


# ---------------------------------------------------------------------------
# Fallback sintético determinístico
# ---------------------------------------------------------------------------

def _gerar_sintetico(path: Path) -> pd.DataFrame:
    """Gera CSV sintético determinístico (seed 42) com as colunas esperadas."""
    import numpy as np  # import tardio: só para o fallback

    path.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)

    cidades = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Fortaleza"]
    estados = ["SP", "RJ", "MG", "PR", "CE"]
    produtos = ["Mouse", "Teclado", "Monitor", "Notebook", "Impressora", "Cadeira"]
    categorias = [
        "Periféricos",
        "Periféricos",
        "Monitores",
        "Computadores",
        "Impressoras",
        "Mobiliário",
    ]
    clientes = [f"Cliente {i:03d}" for i in range(1, 31)]
    status_pool = ["concluido"] * 75 + ["cancelado"] * 15 + ["pendente"] * 10

    n = 200
    datas = pd.date_range("2024-01-01", periods=n, freq="2D")
    df = pd.DataFrame(
        {
            "pedido_id": [f"PED-{i:04d}" for i in range(1, n + 1)],
            "data_pedido": datas.strftime("%Y-%m-%d"),
            "cliente": rng.choice(clientes, n),
            "produto": rng.choice(produtos, n),
            "categoria": rng.choice(categorias, n),
            "cidade": rng.choice(cidades, n),
            "estado": rng.choice(estados, n),
            "quantidade": rng.integers(1, 6, n).tolist(),
            "valor_unitario": rng.integers(50, 3000, n).tolist(),
            "status": [status_pool[i % len(status_pool)] for i in range(n)],
        }
    )
    df["receita"] = df["quantidade"] * df["valor_unitario"]

    # Determinístico: embaralha com seed fixa e injeta 5 duplicatas reais.
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    duplicadas = df.iloc[:5]
    df = pd.concat([df, duplicadas], ignore_index=True)

    df.to_csv(path, index=False, encoding="utf-8")
    return df


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def carregar_dados(path: str | Path) -> pd.DataFrame:
    """Carrega CSV, normaliza tipos/status e retorna DataFrame limpo.

    - Se ``path`` não existir: gera sintético determinístico (seed 42) no mesmo
      caminho e carrega-o (com as colunas esperadas).
    - Detecta separador ``;`` ou ``,`` automaticamente.
    - Converte datas, numéricos, normaliza status, deduplica por pedido_id.
    - Garante ``receita = quantidade * valor_unitario`` (recalculado).
    """
    path = Path(path)
    if not path.exists():
        _gerar_sintetico(path)

    sep = _detectar_separador(path)
    df_bruto = pd.read_csv(path, sep=sep, dtype=str, encoding="utf-8")

    df = df_bruto.copy()

    # Stripping de nomes de coluna
    df.columns = [str(c).strip() for c in df.columns]

    # remove linhas totalmente vazias
    df = df.dropna(how="all").reset_index(drop=True)

    # pedido_id como string limpa
    if "pedido_id" in df.columns:
        df["pedido_id"] = df["pedido_id"].map(
            lambda v: str(v).strip() if pd.notna(v) else v
        )

    # data_pedido
    if "data_pedido" in df.columns:
        s = df["data_pedido"].astype(str).str.strip()
        df["data_pedido"] = pd.to_datetime(s, errors="coerce", dayfirst=False)
    else:
        df["data_pedido"] = pd.NaT

    # numéricos
    if "quantidade" in df.columns:
        df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce")
    else:
        df["quantidade"] = 0
    if "valor_unitario" in df.columns:
        df["valor_unitario"] = pd.to_numeric(df["valor_unitario"], errors="coerce")
    else:
        df["valor_unitario"] = 0.0

    # normaliza status
    if "status" in df.columns:
        df["status"] = df["status"].map(normalizar_status)
    else:
        df["status"] = ""

    # receita: recalculada sempre (garante consistência quantidade*valor)
    df["receita"] = df["quantidade"] * df["valor_unitario"]

    # remove duplicatas por pedido_id (keep first)
    if "pedido_id" in df.columns:
        df = df.drop_duplicates(subset=["pedido_id"], keep="first").reset_index(drop=True)

    return df


def resumo_qualidade(df: pd.DataFrame) -> dict:
    """Resumo de qualidade: linhas brutas, dedup, nulos, duplicadas, período.

    Compatível tanto com df limpo quanto com raw: se tiver 'pedido_id',
    'data_pedido' e nulos por coluna, expõe os números; senão, retorna Nones/0s equivalentes.
    """
    linhas = int(len(df))
    res = {
        "linhas_brutas": linhas,
        "linhas_apos_dedup": linhas,
        "nulos_total": int(df.isna().sum().sum()),
        "nulos_por_coluna": {str(k): int(v) for k, v in df.isna().sum().items()},
        "duplicadas_pedidos": 0,
        "data_min": None,
        "data_max": None,
    }

    if "pedido_id" in df.columns:
        res["duplicadas_pedidos"] = int(df.duplicated(subset=["pedido_id"]).sum())
        # linhas_apos_dedup: se o df já veio dedupado, é len; senão calculamos a teoria
        # (mantemos len atual; carregar_dados já dedupa)
        res["linhas_apos_dedup"] = int(len(df.drop_duplicates(subset=["pedido_id"])))

    if "data_pedido" in df.columns:
        dmin = df["data_pedido"].min()
        dmax = df["data_pedido"].max()
        res["data_min"] = dmin.date().isoformat() if pd.notna(dmin) else None
        res["data_max"] = dmax.date().isoformat() if pd.notna(dmax) else None

    return res


def gerar_csv_limpo(df: pd.DataFrame, path: str | Path) -> Path:
    """Salva df em CSV (UTF-8, vírgula, índice False) e retorna o Path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return path

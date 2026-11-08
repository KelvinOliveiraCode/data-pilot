"""Métricas de negócio determinísticas sobre pedidos concluídos.

Todas as funções recebem um DataFrame pandas limpo (colunas: data, cliente,
categoria, status, valor_unitario, quantidade, receita, cidade, ...),
filtram para pedidos concluídos (status == "concluido", com tolerância a
case/acentos na leitura do status) e devolvem números Python puros
(float/int) ou DataFrames resumidos: nunca chamam rede nem LLM.

Fases 1+2 (or1): 8 funções públicas, mapeadas 1:1 às ferramentas de
tool-calling em `ferramentas.py`.
"""

from __future__ import annotations

import unicodedata

import pandas as pd

__all__ = [
    "calcular_receita_total",
    "calcular_pedidos_concluidos",
    "calcular_ticket_medio",
    "calcular_clientes_unicos",
    "calcular_taxa_cancelamento",
    "calcular_receita_media_por_cliente",
    "calcular_top5_cidades_receita",
    "filtrar_periodo",
]


def _normalizar(texto: str) -> str:
    """Remove acentos e baixa a caixa de um texto (p/ comparar status)."""
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c)).strip().lower()


def _concluidos(df: pd.DataFrame) -> pd.DataFrame:
    """Subconjunto de pedidos concluídos do DataFrame limpo."""
    if df is None or df.empty or "status" not in df.columns:
        return df.iloc[0:0] if df is not None else pd.DataFrame()
    mask = df["status"].map(lambda s: _normalizar(s) == "concluido")
    return df[mask]


def _filtrar_categoria(df: pd.DataFrame, categoria: str | None) -> pd.DataFrame:
    """Aplica filtro opcional por categoria (case/acentos-insensível)."""
    if categoria is None or str(categoria).strip() == "":
        return df
    alvo = _normalizar(categoria)
    mask = df["categoria"].map(lambda c: _normalizar(c) == alvo)
    return df[mask]


def _parse_data(valor: str) -> pd.Timestamp:
    """Converte "YYYY-MM-DD" (ou data ISO) em Timestamp; erro claro se inválido."""
    try:
        return pd.Timestamp(str(valor).strip())
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Data inválida: {valor!r} (use YYYY-MM-DD)") from exc


def calcular_receita_total(df: pd.DataFrame, categoria: str | None = None) -> float:
    """Receita total (soma de `receita`) de pedidos concluídos.

    Args:
        df: DataFrame limpo.
        categoria: filtro opcional de categoria (None = todas).

    Returns:
        Soma da receita como float (0.0 se não houver pedidos).
    """
    base = _filtrar_categoria(_concluidos(df), categoria)
    if base.empty or "receita" not in base.columns:
        return 0.0
    return float(base["receita"].sum())


def calcular_pedidos_concluidos(df: pd.DataFrame, categoria: str | None = None) -> int:
    """Quantidade de pedidos concluídos (nº de linhas concluídas).

    Args:
        df: DataFrame limpo.
        categoria: filtro opcional de categoria (None = todas).

    Returns:
        Contagem como int.
    """
    base = _filtrar_categoria(_concluidos(df), categoria)
    return int(len(base))


def calcular_ticket_medio(df: pd.DataFrame, categoria: str | None = None) -> float:
    """Ticket médio = receita total de concluídos ÷ pedidos concluídos.

    Args:
        df: DataFrame limpo.
        categoria: filtro opcional de categoria (None = todas).

    Returns:
        Ticket médio como float (0.0 se não houver pedidos concluídos).
    """
    pedidos = calcular_pedidos_concluidos(df, categoria)
    if pedidos == 0:
        return 0.0
    return calcular_receita_total(df, categoria) / pedidos


def calcular_clientes_unicos(df: pd.DataFrame, categoria: str | None = None) -> int:
    """Clientes distintos com ao menos um pedido concluído.

    Args:
        df: DataFrame limpo.
        categoria: filtro opcional de categoria (None = todas).

    Returns:
        Contagem de clientes distintos como int.
    """
    base = _filtrar_categoria(_concluidos(df), categoria)
    if base.empty or "cliente" not in base.columns:
        return 0
    return int(base["cliente"].nunique(dropna=True))


def calcular_taxa_cancelamento(df: pd.DataFrame, categoria: str | None = None) -> float:
    """Taxa de cancelamento = cancelados ÷ total de pedidos (0-100, por cento).

    Args:
        df: DataFrame limpo.
        categoria: filtro opcional de categoria (None = todas).

    Returns:
        Percentual (0.0-100.0) como float.
    """
    if df is None or df.empty or "status" not in df.columns:
        return 0.0
    base = _filtrar_categoria(df, categoria)
    total = len(base)
    if total == 0:
        return 0.0
    cancelados = int(base["status"].map(lambda s: _normalizar(s) == "cancelado").sum())
    return float(cancelados / total * 100.0)


def calcular_receita_media_por_cliente(df: pd.DataFrame, categoria: str | None = None) -> float:
    """Receita média por cliente = receita total ÷ clientes únicos (concluídos).

    Args:
        df: DataFrame limpo.
        categoria: filtro opcional de categoria (None = todas).

    Returns:
        Valor como float (0.0 se não houver clientes/pedidos).
    """
    clientes = calcular_clientes_unicos(df, categoria)
    if clientes == 0:
        return 0.0
    return calcular_receita_total(df, categoria) / clientes


def calcular_top5_cidades_receita(df: pd.DataFrame) -> pd.DataFrame:
    """Top-5 cidades por receita de pedidos concluídos.

    Args:
        df: DataFrame limpo com colunas `cidade` e `receita`.

    Returns:
        DataFrame com colunas ["cidade", "receita"] ordenado por receita
        decrescente, no máximo 5 linhas (vazio se não houver dados).
    """
    base = _concluidos(df)
    if base.empty or "cidade" not in base.columns or "receita" not in base.columns:
        return pd.DataFrame(columns=["cidade", "receita"])
    agg = base.groupby("cidade", dropna=True)["receita"].sum().reset_index()
    agg = agg.sort_values("receita", ascending=False).head(5).reset_index(drop=True)
    return agg


def filtrar_periodo(
    df: pd.DataFrame,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    categoria: str | None = None,
) -> pd.DataFrame:
    """Filtra por período (inclusive) e, opcionalmente, por categoria.

    Útil para responder "quanto vendemos entre X e Y" sem o modelo
    precisar calcular datas: ele só passa as strings.

    Args:
        df: DataFrame limpo com coluna `data` (datetime).
        data_inicio: início do período, "YYYY-MM-DD" (None = sem limite).
        data_fim: fim do período, "YYYY-MM-DD" inclusive (None = sem limite).
        categoria: filtro opcional de categoria.

    Returns:
        Subconjunto filtrado (todas as linhas, não só concluídos: o
        chamador decide o que resumir).
    """
    base = df.copy()
    col_data = "data" if "data" in base.columns else "data_pedido"
    if col_data not in base.columns:
        return base.reset_index(drop=True)
    if data_inicio is not None and str(data_inicio).strip() != "":
        base = base[base[col_data] >= _parse_data(data_inicio)]
    if data_fim is not None and str(data_fim).strip() != "":
        fim = _parse_data(data_fim)
        base = base[base[col_data] <= fim]
    base = _filtrar_categoria(base, categoria)
    return base.reset_index(drop=True)

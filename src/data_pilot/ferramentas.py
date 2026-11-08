"""Ferramentas de tool-calling para o LLM (Fase 4).

Cada métrica de `metricas.py` vira um descritor no formato
OpenAI/OpenRouter: `{"type": "function", "function": {...}}`
com nome, descrição em PT-BR e JSON Schema dos parâmetros.

O LLM escolhe nome + argumentos; `executar_ferramenta` despacha para a
função Python e devolve um dict JSON-serializável (DataFrames viram lista
de dicts). Sem SDK de agentes — apenas dicts + `requests` (em `agente.py`).
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from data_pilot import metricas

# --- Descritores de ferramentas (8 no total: 5 base + 3 evoluções) ---

_CATEGORIA_PARAM: dict[str, Any] = {
    "type": "string",
    "description": "Categoria do produto (ex.: eletronicos, moveis). Omita para todas.",
}

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "receita_total",
            "description": "Calcula a receita total de pedidos concluidos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": _CATEGORIA_PARAM,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pedidos_concluidos",
            "description": "Conta pedidos concluidos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": _CATEGORIA_PARAM,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ticket_medio",
            "description": "Calcula o ticket medio (receita / pedidos).",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": _CATEGORIA_PARAM,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clientes_unicos",
            "description": "Conta clientes unicos com pedido concluido.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": _CATEGORIA_PARAM,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "taxa_cancelamento",
            "description": "Calcula taxa de cancelamento em %.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": _CATEGORIA_PARAM,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "receita_media_por_cliente",
            "description": "Calcula receita media por cliente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": _CATEGORIA_PARAM,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top5_cidades_receita",
            "description": "Lista top-5 cidades por receita.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filtrar_periodo",
            "description": "Filtra por periodo (data_inicio/data_fim) e categoria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_inicio": {
                        "type": "string",
                        "description": "Data inicial YYYY-MM-DD (inclusive).",
                    },
                    "data_fim": {
                        "type": "string",
                        "description": "Data final YYYY-MM-DD (inclusive).",
                    },
                    "categoria": _CATEGORIA_PARAM,
                },
                "required": [],
            },
        },
    },
]


def _para_serializavel(valor: Any) -> Any:
    """Converte o retorno das métricas em valor JSON-serializável.

    - DataFrame → lista de dicts (records), com datas vira string ISO.
    - Series → dict; numpy escalares → float/int nativos.
    - Dicts/listas são preservados; o chamador serializa com json.dumps.
    """
    if isinstance(valor, pd.DataFrame):
        limpo = valor.copy()
        for coluna in limpo.columns:
            if pd.api.types.is_datetime64_any_dtype(limpo[coluna]):
                limpo[coluna] = limpo[coluna].dt.strftime("%Y-%m-%d")
        registros = limpo.to_dict("records")
        # Converte numpy scalars dentro dos registros para tipos nativos.
        return json.loads(json.dumps(registros, default=str))
    if isinstance(valor, pd.Series):
        return _para_serializavel(valor.to_dict())
    if isinstance(valor, dict):
        return {str(k): _para_serializavel(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_para_serializavel(v) for v in valor]
    # numpy / pandas escalares
    if isinstance(valor, (pd.Timestamp,)):
        return valor.strftime("%Y-%m-%d")
    try:
        import numpy as np  # noqa: PLC0415  # import local: pandas já depende de numpy

        if isinstance(valor, np.integer):
            return int(valor)
        if isinstance(valor, np.floating):
            return float(valor)
        if isinstance(valor, np.bool_):
            return bool(valor)
    except Exception:  # noqa: BLE001  # numpy sempre presente via pandas; só por segurança
        pass
    return valor


def executar_ferramenta(nome: str, args: dict | None, df: pd.DataFrame) -> dict:
    """Executa a ferramenta `nome` com `args` sobre `df`.

    Args:
        nome: nome snake_case da ferramenta (ex.: "receita_total").
        args: argumentos já decodificados do tool_call do LLM (dict).
        df: DataFrame limpo (saída de `dados.py`).

    Returns:
        Dict JSON-serializável: `{"resultado": valor}` em caso de sucesso
        ou `{"erro": "mensagem"}` em caso de ferramenta desconhecida,
        argumentos inválidos ou exceção na métrica.
    """
    args = args or {}
    try:
        if nome == "receita_total":
            resultado = metricas.calcular_receita_total(df, args.get("categoria"))
        elif nome == "pedidos_concluidos":
            resultado = metricas.calcular_pedidos_concluidos(df, args.get("categoria"))
        elif nome == "ticket_medio":
            resultado = metricas.calcular_ticket_medio(df, args.get("categoria"))
        elif nome == "clientes_unicos":
            resultado = metricas.calcular_clientes_unicos(df, args.get("categoria"))
        elif nome == "taxa_cancelamento":
            resultado = metricas.calcular_taxa_cancelamento(df, args.get("categoria"))
        elif nome == "receita_media_por_cliente":
            resultado = metricas.calcular_receita_media_por_cliente(df, args.get("categoria"))
        elif nome == "top5_cidades_receita":
            resultado = metricas.calcular_top5_cidades_receita(df)
        elif nome == "filtrar_periodo":
            resultado = metricas.filtrar_periodo(
                df,
                data_inicio=args.get("data_inicio"),
                data_fim=args.get("data_fim"),
                categoria=args.get("categoria"),
            )
        else:
            return {"erro": f"Ferramenta desconhecida: {nome!r}"}
    except (ValueError, TypeError) as exc:
        return {"erro": f"Argumentos inválidos para {nome}: {exc}"}
    except Exception as exc:  # noqa: BLE001  # ferramenta nunca deve derrubar o chat
        return {"erro": f"Erro ao executar {nome}: {exc}"}

    # Garante que o resultado é JSON-serializável (DataFrame → lista de dicts).
    try:
        json.dumps(resultado, default=str)
        serializavel = _para_serializavel(resultado)
        json.dumps(serializavel)  # valida de novo sem default
    except (TypeError, ValueError):
        serializavel = str(resultado)
    return {"resultado": serializavel}

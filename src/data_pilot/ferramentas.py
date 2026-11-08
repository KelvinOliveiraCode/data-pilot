"""Ferramentas de tool-calling para o LLM (Fase 4).

Cada métrica de `metricas.py` vira um descritor no formato OpenAI/OpenRouter:
`{"type": "function", "function": {"name": ..., "description": ..., "parameters": {...json schema...}}}`.

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
    "description": "Categoria do produto (ex.: 'eletronicos', 'moveis', 'vestuario'). Omita para todas as categorias.",
}

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "receita_total",
            "description": "Calcula a receita total em reais de pedidos concluídos. Use para perguntas como 'quanto vendemos?', 'qual a receita total?' ou 'faturamento'.",
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
            "description": "Conta quantos pedidos foram concluídos. Use para 'quantos pedidos?', 'número de vendas concluídas?'.",
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
            "description": "Calcula o ticket médio (receita de concluídos dividida por pedidos concluídos). Use para 'ticket médio?', 'valor médio por pedido?'.",
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
            "description": "Conta clientes distintos com ao menos um pedido concluído. Use para 'quantos clientes únicos?', 'base de clientes?'.",
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
            "description": "Calcula a taxa de cancelamento em porcentagem (cancelados dividido pelo total de pedidos). Use para 'taxa de cancelamento?', 'quantos cancelaram?'.",
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
            "description": "Calcula a receita média por cliente (receita total de concluídos dividida por clientes únicos). Use para 'receita média por cliente?', 'quanto cada cliente gera em média?'.",
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
            "description": "Lista as 5 cidades com maior receita de pedidos concluídos, em ordem decrescente. Use para 'quais cidades mais vendem?', 'top cidades?'.",
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
            "description": "Filtra o DataFrame por período (data_inicio e/ou data_fim) e opcionalmente por categoria. Use para perguntas com intervalo de datas, ex.: 'vendas em janeiro', 'receita entre 2024-01-01 e 2024-03-31'. Retorna lista de registros filtrados.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_inicio": {
                        "type": "string",
                        "description": "Data inicial no formato YYYY-MM-DD (inclusive). Omita se não houver início.",
                    },
                    "data_fim": {
                        "type": "string",
                        "description": "Data final no formato YYYY-MM-DD (inclusive). Omita se não houver fim.",
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

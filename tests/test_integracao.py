"""Testes de integração: CSV real -> paridade painel==ferramentas, turno LLM mockado."""

from __future__ import annotations

import pandas as pd

from data_pilot import ferramentas, metricas
from data_pilot.dados import carregar_dados

_CFG_K = ("k", "nvidia/nemotron-3.5-lightning:free", "https://openrouter.ai/api/v1")


def _set_cfg(monkeypatch, cfg) -> None:
    from data_pilot import agente

    monkeypatch.setattr(agente, "_get_config", lambda: cfg)


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data_pedido": pd.to_datetime(["2024-01-05", "2024-01-10", "2024-02-01"]),
            "cliente": ["Ana", "Ana", "Bruno"],
            "categoria": ["Eletronicos", "Eletronicos", "Moveis"],
            "status": ["concluido", "cancelado", "concluido"],
            "cidade": ["Sao Paulo", "Sao Paulo", "Rio"],
            "quantidade": [1, 2, 1],
            "valor_unitario": [100.0, 50.0, 200.0],
            "receita": [100.0, 100.0, 200.0],
        }
    )


def test_paridade_painel_ferramentas() -> None:
    """Os números que o Painel mostra (metricas.calcular_*) batem com o Chat (ferramentas)."""
    df = _df()
    pares = [
        ("receita_total", metricas.calcular_receita_total(df)),
        ("pedidos_concluidos", metricas.calcular_pedidos_concluidos(df)),
        ("ticket_medio", metricas.calcular_ticket_medio(df)),
        ("clientes_unicos", metricas.calcular_clientes_unicos(df)),
        ("taxa_cancelamento", metricas.calcular_taxa_cancelamento(df)),
        ("receita_media_por_cliente", metricas.calcular_receita_media_por_cliente(df)),
    ]
    for nome, esperado in pares:
        assert ferramentas.executar_ferramenta(nome, {}, df)["resultado"] == esperado


def test_turno_llm_mockado_receita_total(monkeypatch) -> None:
    """Simula: usuário 'receita total?' -> tool_call -> número 300 -> resposta."""
    import json

    from data_pilot import agente

    def fake(model: str, messages: list, tools=None, api_key: str = "", base_url: str = ""):
        if any(m.get("role") == "tool" for m in messages):
            return {"content": "A receita total é 300 (100 + 200).", "tool_calls": []}
        return {
            "content": "",
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {"name": "receita_total", "arguments": json.dumps({})},
                }
            ],
        }

    monkeypatch.setattr(agente, "chamar_openrouter", fake)
    _set_cfg(monkeypatch, _CFG_K)
    texto = agente.conversar(_df(), "qual a receita total?")
    assert texto == "A receita total é 300 (100 + 200)."


def test_dataset_real_smoke() -> None:
    """O CSV do repo (ou fallback sintético) carrega e as 8 ferramentas executam."""
    df = carregar_dados("data/sales.csv")
    assert not df.empty
    assert "receita" in df.columns and "status" in df.columns
    for nome in {
        "receita_total",
        "pedidos_concluidos",
        "ticket_medio",
        "clientes_unicos",
        "taxa_cancelamento",
        "receita_media_por_cliente",
    }:
        assert "resultado" in ferramentas.executar_ferramenta(nome, {}, df)
    top5 = ferramentas.executar_ferramenta("top5_cidades_receita", {}, df)["resultado"]
    assert isinstance(top5, list) and len(top5) >= 1
    if "data_pedido" in df.columns:
        assert "resultado" in ferramentas.executar_ferramenta(
            "filtrar_periodo", {"data_inicio": "2024-01-01", "data_fim": "2024-01-31"}, df
        )

"""Testes de contratos das ferramentas (ferramentas.py): TOOLS + executar_ferramenta."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from data_pilot.ferramentas import TOOLS, executar_ferramenta

NOMES_ESPERADOS = {
    "receita_total",
    "pedidos_concluidos",
    "ticket_medio",
    "clientes_unicos",
    "taxa_cancelamento",
    "receita_media_por_cliente",
    "top5_cidades_receita",
    "filtrar_periodo",
}


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data": pd.to_datetime(["2024-01-05", "2024-01-10", "2024-02-01"]),
            "cliente": ["Ana", "Ana", "Bruno"],
            "categoria": ["Eletronicos", "Eletronicos", "Moveis"],
            "status": ["concluido", "cancelado", "concluido"],
            "cidade": ["Sao Paulo", "Sao Paulo", "Rio"],
            "quantidade": [1, 2, 1],
            "valor_unitario": [100.0, 50.0, 200.0],
            "receita": [100.0, 100.0, 200.0],
        }
    )


def test_tools_tem_8_itens_com_name_description_parameters() -> None:
    assert len(TOOLS) == 8
    nomes = set()
    for ferramenta in TOOLS:
        assert ferramenta["type"] == "function"
        funcao = ferramenta["function"]
        assert funcao["name"]
        assert funcao["description"]
        assert funcao["parameters"]["type"] == "object"
        assert "properties" in funcao["parameters"]
        nomes.add(funcao["name"])
    assert nomes == NOMES_ESPERADOS


def test_tools_parametros_conhecidos() -> None:
    por_nome = {t["function"]["name"]: t["function"]["parameters"] for t in TOOLS}
    for nome in NOMES_ESPERADOS - {"top5_cidades_receita", "filtrar_periodo"}:
        assert set(por_nome[nome]["properties"]) == {"categoria"}
    assert set(por_nome["filtrar_periodo"]["properties"]) == {
        "data_inicio",
        "data_fim",
        "categoria",
    }
    assert por_nome["top5_cidades_receita"]["properties"] == {}


def test_executar_receita_total(df: pd.DataFrame) -> None:
    assert executar_ferramenta("receita_total", {}, df) == {"resultado": 300.0}


def test_executar_com_categoria(df: pd.DataFrame) -> None:
    assert executar_ferramenta("receita_total", {"categoria": "Moveis"}, df) == {
        "resultado": 200.0
    }


def test_executar_demais_metricas(df: pd.DataFrame) -> None:
    assert executar_ferramenta("pedidos_concluidos", {}, df) == {"resultado": 2}
    assert executar_ferramenta("ticket_medio", {}, df) == {"resultado": 150.0}
    assert executar_ferramenta("clientes_unicos", {}, df) == {"resultado": 2}
    assert executar_ferramenta("taxa_cancelamento", {}, df) == {
        "resultado": pytest.approx(100.0 / 3.0)
    }
    assert executar_ferramenta("receita_media_por_cliente", {}, df) == {"resultado": 150.0}


def test_executar_top5_cidades_retorna_lista_json(df: pd.DataFrame) -> None:
    resultado = executar_ferramenta("top5_cidades_receita", {}, df)
    assert "resultado" in resultado
    registros = resultado["resultado"]
    assert registros == [
        {"cidade": "Rio", "receita": 200.0},
        {"cidade": "Sao Paulo", "receita": 100.0},
    ]
    json.dumps(resultado)


def test_executar_filtrar_periodo(df: pd.DataFrame) -> None:
    resultado = executar_ferramenta(
        "filtrar_periodo",
        {"data_inicio": "2024-01-01", "data_fim": "2024-01-31"},
        df,
    )
    registros = resultado["resultado"]
    assert len(registros) == 2
    assert registros[0]["data"] == "2024-01-05"
    assert registros[1]["data"] == "2024-01-10"
    json.dumps(resultado)


def test_executar_ferramenta_desconhecida(df: pd.DataFrame) -> None:
    resultado = executar_ferramenta("ferramenta_inexistente", {}, df)
    assert set(resultado) == {"erro"}
    assert "desconhecida" in resultado["erro"].lower()

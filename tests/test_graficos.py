"""Testes dos 4 gráficos Plotly puros (graficos.py) — sem Streamlit."""

from __future__ import annotations

import pandas as pd
import pytest

from data_pilot import graficos

TOP5_COLS = ["cidade", "receita"]


@pytest.fixture
def df() -> pd.DataFrame:
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


@pytest.fixture
def df_vazio() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data_pedido": pd.Series(dtype="datetime64[ns]"),
            "cliente": pd.Series(dtype="object"),
            "categoria": pd.Series(dtype="object"),
            "status": pd.Series(dtype="object"),
            "cidade": pd.Series(dtype="object"),
            "quantidade": pd.Series(dtype="float64"),
            "valor_unitario": pd.Series(dtype="float64"),
            "receita": pd.Series(dtype="float64"),
        }
    )


def test_grafico_receita_por_categoria_concluido(df: pd.DataFrame) -> None:
    fig = graficos.grafico_receita_por_categoria(df)
    assert len(fig.data) == 1
    # receita por categoria sobre concluidos: Eletronicos 100 (cancela 100 fora), Moveis 200
    test = fig.data[0]
    assert test.x == ["Moveis", "Eletronicos"] or set(test.x) == {"Moveis", "Eletronicos"}
    assert sum(test.y) == pytest.approx(300.0)


def _lst(v):
    return list(v) if v is not None else []


def test_grafico_receita_por_categoria_vazio(df_vazio: pd.DataFrame) -> None:
    fig = graficos.grafico_receita_por_categoria(df_vazio)
    assert len(fig.data) == 1
    assert _lst(fig.data[0].x) == [] and _lst(fig.data[0].y) == []


def test_grafico_top5_cidades_horiz(df: pd.DataFrame) -> None:
    fig = graficos.grafico_top5_cidades(df)
    assert len(fig.data) == 1
    test = fig.data[0]
    assert test.orientation == "h"
    assert set(test.y) == {"Sao Paulo", "Rio"}  # y = cidades no modo horizontal
    assert max(test.x) == pytest.approx(200.0)  # x = receitas
    assert fig.layout.title.text == "Top 5 cidades por receita"


def test_grafico_top5_cidades_vazio(df_vazio: pd.DataFrame) -> None:
    fig = graficos.grafico_top5_cidades(df_vazio)
    assert _lst(fig.data[0].x) == [] and _lst(fig.data[0].y) == []


def test_grafico_receita_mensal_linha(df: pd.DataFrame) -> None:
    fig = graficos.grafico_receita_mensal(df)
    assert len(fig.data) == 1
    test = fig.data[0]
    assert test.mode == "lines+markers"
    assert _lst(test.x) == ["2024-01", "2024-02"]
    assert sum(_lst(test.y)) == pytest.approx(300.0)


def test_grafico_receita_mensal_vazio(df_vazio: pd.DataFrame) -> None:
    fig = graficos.grafico_receita_mensal(df_vazio)
    assert _lst(fig.data[0].x) == [] and _lst(fig.data[0].y) == []


def test_grafico_distribuicao_status_donut_df_completo(df: pd.DataFrame) -> None:
    fig = graficos.grafico_distribuicao_status(df)
    assert len(fig.data) == 1
    test = fig.data[0]
    # donut sobre o df completo (conc+cancelado), não só concluídos
    assert set(test.labels) == {"concluido", "cancelado"}
    assert sum(test.values) == 3
    assert test.hole == 0.45


def test_grafico_distribuicao_status_vazio(df_vazio: pd.DataFrame) -> None:
    fig = graficos.grafico_distribuicao_status(df_vazio)
    assert _lst(fig.data[0].labels) == ["sem dados"]
    assert list(fig.data[0].values) == [0]


def test_graficos_titulos_e_template(df: pd.DataFrame) -> None:
    assert graficos.grafico_receita_por_categoria(df).layout.title.text == "Receita por categoria"
    assert graficos.grafico_top5_cidades(df).layout.title.text == "Top 5 cidades por receita"
    assert graficos.grafico_receita_mensal(df).layout.title.text == "Receita mensal"
    titulo_dist = graficos.grafico_distribuicao_status(df).layout.title.text
    assert titulo_dist == "Distribuição de pedidos por status"

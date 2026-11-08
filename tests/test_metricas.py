"""Testes das 8 métricas (metricas.py) sobre DataFrame sintético determinístico."""

from __future__ import annotations

import pandas as pd
import pytest

from data_pilot import metricas
from data_pilot.metricas import (
    calcular_clientes_unicos,
    calcular_pedidos_concluidos,
    calcular_receita_media_por_cliente,
    calcular_receita_total,
    calcular_taxa_cancelamento,
    calcular_ticket_medio,
    calcular_top5_cidades_receita,
    filtrar_periodo,
)


def _df_sintetico() -> pd.DataFrame:
    """5 linhas: 3 concluídos (receitas 100, 200, 100), 1 cancelado, 1 pendente."""
    return pd.DataFrame(
        {
            "data": pd.to_datetime(
                ["2024-01-05", "2024-01-10", "2024-02-01", "2024-02-15", "2024-03-01"]
            ),
            "cliente": ["Ana", "Ana", "Bruno", "Carla", "Ana"],
            "categoria": ["Eletronicos", "Eletronicos", "Moveis", "Eletronicos", "Moveis"],
            "status": ["concluido", "cancelado", "concluido", "concluido", "pendente"],
            "cidade": ["Sao Paulo", "Sao Paulo", "Rio", "Sao Paulo", "Rio"],
            "quantidade": [1, 2, 1, 2, 1],
            "valor_unitario": [100.0, 50.0, 200.0, 50.0, 300.0],
            "receita": [100.0, 100.0, 200.0, 100.0, 300.0],
        }
    )


@pytest.fixture
def df() -> pd.DataFrame:
    return _df_sintetico()


def test_receita_total(df: pd.DataFrame) -> None:
    assert calcular_receita_total(df) == 400.0


def test_pedidos_concluidos(df: pd.DataFrame) -> None:
    assert calcular_pedidos_concluidos(df) == 3


def test_ticket_medio(df: pd.DataFrame) -> None:
    assert calcular_ticket_medio(df) == pytest.approx(400.0 / 3.0)


def test_clientes_unicos(df: pd.DataFrame) -> None:
    assert calcular_clientes_unicos(df) == 3


def test_taxa_cancelamento(df: pd.DataFrame) -> None:
    assert calcular_taxa_cancelamento(df) == pytest.approx(20.0)


def test_receita_media_por_cliente(df: pd.DataFrame) -> None:
    assert calcular_receita_media_por_cliente(df) == pytest.approx(400.0 / 3.0)


def test_top5_cidades_receita(df: pd.DataFrame) -> None:
    top5 = calcular_top5_cidades_receita(df)
    assert list(top5.columns) == ["cidade", "receita"]
    assert len(top5) == 2
    # Empate 200 x 200 entre Rio e Sao Paulo: ordem entre eles não é definida
    # pelo código (só receita DESC). Só garantimos o conjunto e os valores.
    assert sorted(top5["cidade"].tolist()) == ["Rio", "Sao Paulo"]
    assert top5["receita"].tolist() == [200.0, 200.0]
    assert (top5["receita"].diff().dropna() <= 0).all()


def test_filtrar_periodo(df: pd.DataFrame) -> None:
    filtrado = filtrar_periodo(df, data_inicio="2024-02-01", data_fim="2024-02-29")

    assert len(filtrado) == 2
    assert filtrado["cliente"].tolist() == ["Bruno", "Carla"]
    assert filtrado["data"].min() == pd.Timestamp("2024-02-01")
    assert filtrado["data"].max() == pd.Timestamp("2024-02-15")


def test_receita_total_com_filtro_de_categoria(df: pd.DataFrame) -> None:
    assert calcular_receita_total(df, categoria="Moveis") == 200.0


def test_metricas_sobre_df_vazio() -> None:
    vazio = _df_sintetico().iloc[0:0]
    assert calcular_receita_total(vazio) == 0.0
    assert calcular_pedidos_concluidos(vazio) == 0
    assert calcular_ticket_medio(vazio) == 0.0
    assert calcular_clientes_unicos(vazio) == 0
    assert calcular_taxa_cancelamento(vazio) == 0.0
    assert calcular_receita_media_por_cliente(vazio) == 0.0
    top5 = calcular_top5_cidades_receita(vazio)
    assert top5.empty
    assert list(top5.columns) == ["cidade", "receita"]


def test_metricas_expoe_as_8_funcoes() -> None:
    for nome in [
        "calcular_receita_total",
        "calcular_pedidos_concluidos",
        "calcular_ticket_medio",
        "calcular_clientes_unicos",
        "calcular_taxa_cancelamento",
        "calcular_receita_media_por_cliente",
        "calcular_top5_cidades_receita",
        "filtrar_periodo",
    ]:
        assert callable(getattr(metricas, nome, None)), nome

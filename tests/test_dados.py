"""Testes de limpeza de dados (dados.py): CSV, status, dedup, receita."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_pilot.dados import carregar_dados, normalizar_status

COLUNAS = (
    "pedido_id",
    "data_pedido",
    "cliente",
    "produto",
    "categoria",
    "cidade",
    "estado",
    "quantidade",
    "valor_unitario",
    "status",
)


def _csv_texto(separador: str, linhas: list[str]) -> str:
    cabecalho = separador.join(COLUNAS)
    return "\n".join([cabecalho, *linhas]) + "\n"


def _escrever(tmp_path: Path, texto: str) -> Path:
    caminho = tmp_path / "sales.csv"
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def test_carregar_dados_separador_ponto_e_virgula(tmp_path: Path) -> None:
    texto = _csv_texto(
        ";",
        [
            "PED-1;2024-01-05;Ana;Mouse;Eletronicos;Sao Paulo;SP;2;50.5;concluido",
            "PED-2;2024-01-10;Bruno;Cadeira;Moveis;Rio;RJ;1;200;cancelado",
        ],
    )
    df = carregar_dados(_escrever(tmp_path, texto))

    assert len(df) == 2
    assert list(df.columns)[:3] == ["pedido_id", "data_pedido", "cliente"]
    assert df["pedido_id"].tolist() == ["PED-1", "PED-2"]
    assert df["status"].tolist() == ["concluido", "cancelado"]
    assert df["receita"].tolist() == [101.0, 200.0]
    assert pd.api.types.is_datetime64_any_dtype(df["data_pedido"])


def test_carregar_dados_separador_virgula(tmp_path: Path) -> None:
    texto = _csv_texto(
        ",",
        [
            "PED-1,2024-01-05,Ana,Mouse,Eletronicos,Sao Paulo,SP,2,50.5,concluido",
            "PED-2,2024-01-10,Bruno,Cadeira,Moveis,Rio,RJ,1,200,pendente",
        ],
    )
    df = carregar_dados(_escrever(tmp_path, texto))

    assert len(df) == 2
    assert df["status"].tolist() == ["concluido", "pendente"]
    assert df["receita"].tolist() == [101.0, 200.0]
    assert df["data_pedido"].iloc[0] == pd.Timestamp("2024-01-05")


def test_carregar_dados_dedup_por_pedido_id(tmp_path: Path) -> None:
    texto = _csv_texto(
        ",",
        [
            "PED-1,2024-01-05,Ana,Mouse,Eletronicos,Sao Paulo,SP,2,50.5,concluido",
            "PED-1,2024-01-05,Ana,Mouse,Eletronicos,Sao Paulo,SP,2,50.5,concluido",
            "PED-2,2024-01-10,Bruno,Cadeira,Moveis,Rio,RJ,1,200,cancelado",
        ],
    )
    df = carregar_dados(_escrever(tmp_path, texto))

    assert len(df) == 2
    assert df["pedido_id"].tolist() == ["PED-1", "PED-2"]


def test_carregar_dados_receita_recalculada(tmp_path: Path) -> None:
    texto = _csv_texto(
        ",",
        [
            "PED-1,2024-01-05,Ana,Mouse,Eletronicos,Sao Paulo,SP,3,100,concluido",
        ],
    )
    # Adiciona coluna receita errada p/ garantir que carregar_dados recalcula.
    texto = texto.replace("\n", ",receita\n", 1).replace(
        "concluido\n", "concluido,9999\n", 1
    )
    df = carregar_dados(_escrever(tmp_path, texto))

    assert df["receita"].tolist() == [300.0]
    assert (df["receita"] == df["quantidade"] * df["valor_unitario"]).all()


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("concluido", "concluido"),
        ("Concluído", "concluido"),
        ("CONCLUIDO", "concluido"),
        ("completed", "concluido"),
        ("cancelado", "cancelado"),
        ("cancelada", "cancelado"),
        ("CANCELED", "cancelado"),
        ("cancelled", "cancelado"),
        ("pendente", "pendente"),
        (" pendente ", "pendente"),
        ("pending", "pendente"),
        ("aguardando", "pendente"),
        ("", ""),
        ("xyz", "xyz"),
    ],
)
def test_normalizar_status(entrada: object, esperado: str) -> None:
    assert normalizar_status(entrada) == esperado


def test_normalizar_status_valor_nulo() -> None:
    assert normalizar_status(None) == ""

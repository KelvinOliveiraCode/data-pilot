"""Testes do loop tool-calling do agente (agente.py): mockados, sem rede."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from data_pilot import agente
from data_pilot.ferramentas import TOOLS

_CFG_K = ("k", agente.MODELO_PADRAO, agente.BASE_URL_PADRAO)


def _set_cfg(monkeypatch: pytest.MonkeyPatch, cfg: tuple) -> None:
    monkeypatch.setattr(agente, "_get_config", lambda: cfg)


@pytest.fixture
def df() -> pd.DataFrame:
    # receita = 300 (soma sobre concluidos: 100 + 200)
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


def _tool_call(nome: str, args: dict[str, Any], id_: str = "call_1") -> dict[str, Any]:
    import json

    return {
        "id": id_,
        "type": "function",
        "function": {"name": nome, "arguments": json.dumps(args)},
    }


def test_resolver_chave_override_tem_precedencia(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chave digitada na UI (override) tem precedência sobre o env."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")
    assert agente._resolver_chave("ui-key") == "ui-key"
    assert agente._resolver_chave("  ui-key  ") == "ui-key"
    assert agente._resolver_chave("") == "env-key"
    assert agente._resolver_chave(None) == "env-key"
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    assert agente._resolver_chave(None) == ""
    assert agente._resolver_chave("") == ""


def test_conversar_usa_api_key_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """conversar() aceita api_key direto (sessão) sem precisar do env."""
    visto: dict[str, Any] = {}

    def fake(
        model: str,
        messages: list,
        tools: Any = None,
        api_key: str = "",
        base_url: str = "",
    ) -> dict[str, Any]:
        visto["api_key"] = api_key
        return {"content": "ok", "tool_calls": []}

    monkeypatch.setattr(agente, "chamar_openrouter", fake)
    _set_cfg(monkeypatch, ("", agente.MODELO_PADRAO, agente.BASE_URL_PADRAO))
    mini = pd.DataFrame(
        {
            "data_pedido": pd.to_datetime(["2024-01-05"]),
            "cliente": ["Ana"],
            "categoria": ["Eletronicos"],
            "status": ["concluido"],
            "cidade": ["Sao Paulo"],
            "quantidade": [1],
            "valor_unitario": [100.0],
            "receita": [100.0],
        }
    )
    assert agente.conversar(mini, "oi", api_key="session-key") == "ok"
    assert visto["api_key"] == "session-key"


def test_chamar_openrouter_sem_chave_levanta_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        agente.chamar_openrouter(model="m", messages=[], api_key="")


def test_chamar_openrouter_sucesso_sem_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    class Resp:
        status_code = 200

        def json(self) -> dict[str, Any]:
            return {"choices": [{"message": {"content": "Olá", "tool_calls": []}}]}

    monkeypatch.setattr(agente.requests, "post", lambda *a, **k: Resp())
    out = agente.chamar_openrouter(model="m", messages=[], tools=None, api_key="k")
    assert out == {"content": "Olá", "tool_calls": []}


def test_chamar_openrouter_erro_http(monkeypatch: pytest.MonkeyPatch) -> None:
    class Resp:
        status_code = 401
        text = "unauthorized"

    monkeypatch.setattr(agente.requests, "post", lambda *a, **k: Resp())
    with pytest.raises(RuntimeError, match="HTTP 401"):
        agente.chamar_openrouter(model="m", messages=[], api_key="k")


def test_chamar_openrouter_json_invalido(monkeypatch: pytest.MonkeyPatch) -> None:
    class Resp:
        status_code = 200
        text = "não json"

        def json(self) -> Any:
            raise ValueError("bad")

    monkeypatch.setattr(agente.requests, "post", lambda *a, **k: Resp())
    with pytest.raises(RuntimeError, match="não-JSON"):
        agente.chamar_openrouter(model="m", messages=[], api_key="k")


def test_conversar_sem_chave_retorna_aviso(
    df: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_cfg(monkeypatch, ("", agente.MODELO_PADRAO, agente.BASE_URL_PADRAO))
    texto = agente.conversar(df, "qual a receita?")
    assert "OPENROUTER_API_KEY" in texto


def test_conversar_loop_tool_then_final(df: pd.DataFrame, monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[dict[str, Any]] = []

    def fake(
        model: str,
        messages: list,
        tools: Any = None,
        api_key: str = "",
        base_url: str = "",
    ) -> dict[str, Any]:
        chamadas.append({"model": model, "messages": list(messages), "tools": tools})
        if len(chamadas) == 1:
            return {"content": "", "tool_calls": [_tool_call("receita_total", {})]}
        return {"content": "A receita total é 300.", "tool_calls": []}

    monkeypatch.setattr(agente, "chamar_openrouter", fake)
    _set_cfg(monkeypatch, _CFG_K)
    texto = agente.conversar(df, "qual a receita total?")
    assert texto == "A receita total é 300."
    assert len(chamadas) == 2
    assert chamadas[0]["tools"] is TOOLS  # loop sempre envia as 8 ferramentas
    # 2ª rodada: injetou assistant tool_calls + role tool com o número vindo de executar_ferramenta
    segunda = chamadas[1]["messages"]
    assert any(m.get("role") == "tool" for m in segunda)
    tool_msg = [m for m in segunda if m.get("role") == "tool"][0]
    assert "300.0" in tool_msg["content"]


def test_conversar_resposta_direta_sem_tools(
    df: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        agente, "chamar_openrouter",
        lambda **k: {"content": "Oi!", "tool_calls": []},
    )
    _set_cfg(monkeypatch, _CFG_K)
    assert agente.conversar(df, "oi") == "Oi!"


def test_conversar_limite_10_rodadas(df: pd.DataFrame, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        agente, "chamar_openrouter",
        lambda **k: {"content": "", "tool_calls": [_tool_call("receita_total", {})]},
    )
    _set_cfg(monkeypatch, _CFG_K)
    texto = agente.conversar(df, "receita?")
    assert texto.startswith("Limite de 10 rodadas")


def test_conversar_erro_api_vira_texto(df: pd.DataFrame, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(**k: Any) -> dict[str, Any]:
        raise RuntimeError("rede falhou")

    monkeypatch.setattr(agente, "chamar_openrouter", boom)
    _set_cfg(monkeypatch, _CFG_K)
    texto = agente.conversar(df, "oi")
    assert "Erro ao falar com o modelo" in texto and "rede falhou" in texto


def test_conversar_fallback_openrouter_free(
    df: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    chamadas: list[str] = []

    def fake(
        model: str,
        messages: list,
        tools: Any = None,
        api_key: str = "",
        base_url: str = "",
    ) -> dict[str, Any]:
        chamadas.append(model)
        if model == "openrouter/free":
            raise RuntimeError("modelo inválido")
        return {"content": "fallback ok", "tool_calls": []}

    monkeypatch.setattr(agente, "chamar_openrouter", fake)
    _set_cfg(monkeypatch, ("k", "openrouter/free", agente.BASE_URL_PADRAO))
    assert agente.conversar(df, "oi") == "fallback ok"
    assert chamadas == ["openrouter/free", agente.MODELO_PADRAO]


def test_get_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    api_key, modelo, base_url = agente._get_config()
    assert api_key == ""
    assert modelo == agente.MODELO_PADRAO == "nvidia/nemotron-3.5-lightning:free"
    assert base_url == agente.BASE_URL_PADRAO == "https://openrouter.ai/api/v1"

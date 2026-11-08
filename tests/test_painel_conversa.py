"""Testes de smoke das camadas Streamlit (painel.py, conversa.py, app.py).

Mocka `streamlit` inteiro (nenhum runtime de app) e verifica que
`render_painel`/`render_conversa`/`app.main` chamam os elementos esperados.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest


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


@pytest.fixture
def st_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    st = MagicMock()
    # context managers: st.sidebar / st.form / st.spinner / st.expander / st.columns
    st.sidebar.__enter__ = MagicMock(return_value=st)
    st.form.__enter__ = MagicMock(return_value=st)
    st.spinner.__enter__ = MagicMock(return_value=st)
    st.expander.__enter__ = MagicMock(return_value=st)
    def _col():
        c = MagicMock()
        c.__enter__ = MagicMock(return_value=c)
        c.__exit__ = MagicMock(return_value=False)
        # col1.metric / col2.metric ... e col_a.plotly_chart precisam ir pro mock pai
        c.metric = st.metric
        c.plotly_chart = st.plotly_chart
        return c

    def _columns(n=2):
        return tuple(_col() for _ in range(n))

    st.columns.side_effect = _columns
    st.tabs.return_value = (MagicMock(), MagicMock())
    st.selectbox.return_value = "Todas"
    st.multiselect.return_value = ["concluido"]
    _dmin = pd.Timestamp("2024-01-05").date()
    _dmax = pd.Timestamp("2024-02-01").date()
    st.date_input.return_value = (_dmin, _dmax)
    st.text_input.return_value = ""
    st.session_state = _State()
    monkeypatch.setitem(__import__("sys").modules, "streamlit", st)
    return st


def _next_cols(it, n):
    # Streamlit columns(n) returns n context managers; support 2 and 4.
    return tuple(next(it) for _ in range(n))


class _State(dict):
    """session_state como objeto simples com atributos (igual ao real sem Streamlit)."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key) from None

    def __setattr__(self, key, value):
        self[key] = value


def test_render_painel_chama_metricas_e_graficos(st_mock: MagicMock) -> None:
    import data_pilot.painel as painel

    painel.st = st_mock  # painel.py did `import streamlit` at import time (real); rebind to mock
    painel.render_painel(_df())

    st_mock.title.assert_called_once()
    st_mock.selectbox.assert_called()
    st_mock.multiselect.assert_called()
    st_mock.date_input.assert_called()
    # 4 cards de KPI
    assert st_mock.metric.call_count == 4
    labels = [c.args[0] for c in st_mock.metric.call_args_list]
    assert "Receita total" in labels and "Clientes únicos" in labels
    # 4 gráficos Plotly: categoria, top5, mensal, status
    assert st_mock.plotly_chart.call_count == 4
    # rodapé: receita média por cliente + taxa
    assert st_mock.divider.called


def test_render_painel_filtro_categoria(st_mock: MagicMock) -> None:
    st_mock.selectbox.return_value = "Moveis"
    import data_pilot.painel as painel

    painel.st = st_mock
    painel.render_painel(_df())
    # com categoria Moveis filtrada, pedidos concluídos = 1 (só Bruno/200)
    metric_vals = [c.args[1] for c in st_mock.metric.call_args_list]
    assert metric_vals[1] == 1  # col2: Pedidos concluídos


def test_render_conversa_sem_chave_mostra_info(
    st_mock: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    # conversa.py lê dotenv em import — força _tem_api_key via env vazio
    import importlib

    import data_pilot.conversa as conversa

    importlib.reload(conversa)
    conversa.render_conversa(_df())

    st_mock.info.assert_called()
    msg = st_mock.info.call_args.args[0]
    assert "OPENROUTER_API_KEY" in msg
    # sem chave: mensagem de configuração aparece e a conversa não segue para
    # o formulário de pergunta (form_submit_button não é acionado como no fluxo com chave)
    assert not st_mock.form_submit_button.called, "sem chave nao deveria oferecer envio"


def test_render_conversa_com_chave_fluxo(
    st_mock: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    import data_pilot.conversa as conversa

    importlib.reload(conversa)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k-falso")
    monkeypatch.setattr(conversa, "conversar", lambda df, perg, historico=None: "Receita é 300.")
    # sem pergunta: só um render de cabeçalho, sem append no histórico
    st_mock.form_submit_button.return_value = False
    st_mock.text_input.return_value = ""
    conversa.render_conversa(_df())
    assert st_mock.subheader.called
    assert st_mock.caption.called
    assert conversa.st.session_state["historico"] == []


def test_app_main_cria_tabs(st_mock: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    import data_pilot.app as app

    # evita carregar CSV real
    monkeypatch.setattr(app, "_carregar", lambda: _df())
    import sys

    app.st = sys.modules["streamlit"]
    # app.py also did `from .painel import render_painel` at import time — the real
    # render_painel's `st` is the REAL streamlit module (cached), not our mock.
    # The painel-level tests above already prove render_painel; here we only verify
    # the shell that app.main() drives: set_page_config + tabs + both tabs rendered.
    called = {}

    def fake_render_painel(df):
        called["painel"] = True

    def fake_render_conversa(df):
        called["conversa"] = True

    # app imported render_painel directly -> patch the name in app namespace
    monkeypatch.setattr(app, "render_painel", fake_render_painel)
    monkeypatch.setattr(app, "render_conversa", fake_render_conversa, raising=False)
    # conversa is lazy-imported inside main(): patch sys.modules first so
    # `from .conversa import render_conversa` resolves to our fake module.
    import types

    fake_conv = types.ModuleType("data_pilot.conversa")
    fake_conv.render_conversa = fake_render_conversa
    monkeypatch.setitem(sys.modules, "data_pilot.conversa", fake_conv)

    app.main()
    st_mock.set_page_config.assert_called()
    assert st_mock.tabs.called
    assert called.get("painel") is True
    assert called.get("conversa") is True


def test_painel_helpers() -> None:
    import data_pilot.painel as painel

    assert painel._fmt_brl(1234.5) == "R$ 1.234,50"
    assert painel._fmt_brl(0) == "R$ 0,00"
    assert painel._col_data(_df()) == "data_pedido"
    df_data = pd.DataFrame({"data": pd.to_datetime(["2024-01-01"])})
    assert painel._col_data(df_data) == "data"
    assert painel._col_data(pd.DataFrame({"x": [1]})) is None


def test_painel_filtrar_periodo_compat_aceita_data_pedido_real() -> None:
    """Regressão do bug: filtrar_periodo precisa aceitar coluna data_pedido."""
    import data_pilot.painel as painel

    df = _df()
    out = painel._filtrar_periodo_compat(df, "2024-01-01", "2024-01-31")
    assert len(out) == 2
    out2 = painel._filtrar_periodo_compat(df, pd.Timestamp("2024-02-01").date(), None)
    assert len(out2) == 1

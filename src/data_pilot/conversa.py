"""Página do Chat do Data Pilot com Streamlit (Fase 4).

Componentes:
- `render_conversa(df)` é o entry-point chamado por `app.py` (or2/or3).
- Histórico em `st.session_state.historico` (lista de dicts role user/assistant)
  e `st.session_state.ferramentas_usadas` (lista paralela de tool-calls por rodada).
- Entrada via `st.text_input` + botão enviar (com `st.chat_input` como alternativa).
- Cada resposta é exibida com `st.markdown`; o expander "Ferramentas usadas"
  mostra o que o agente chamou nesta rodada.
- Sem `OPENROUTER_API_KEY`, mostra instrução de configuração e não chama o modelo.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

try:  # python-dotenv é opcional em runtime: se faltar, lê só o ambiente.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # noqa: BLE001  # sem .env, o env do processo já basta
    pass

from data_pilot.agente import conversar  # noqa: E402  # import após load_dotenv


def _tem_api_key() -> bool:
    """True se já há chave: override da UI (session_state) OU env/.env."""
    ui = (st.session_state.get("api_key_ui", "") or "").strip()
    if ui:
        return True
    return bool(os.getenv("OPENROUTER_API_KEY", "").strip())


def _chave_atual() -> str:
    """Chave efetiva para a chamada: a digitada na UI tem precedência.

    Nunca loga nem persiste: a chave vive só em `st.session_state` durante
    a sessão do Streamlit e desaparece ao fechar. A env serve de fallback.
    """
    ui = (st.session_state.get("api_key_ui", "") or "").strip()
    return ui or os.getenv("OPENROUTER_API_KEY", "").strip()


def _inicializar_estado_chave() -> None:
    """Garante `st.session_state.api_key_ui` (string vazia = não informada)."""
    if "api_key_ui" not in st.session_state:
        st.session_state.api_key_ui = ""


def _inicializar_historico() -> None:
    """Garante `st.session_state.historico` e `st.session_state.ferramentas`."""
    if "historico" not in st.session_state:
        st.session_state.historico = []
    if "ferramentas_usadas" not in st.session_state:
        st.session_state.ferramentas_usadas = []


def render_conversa(df: pd.DataFrame) -> None:
    """Renderiza a interface de chat do Data Pilot.

    Args:
        df: DataFrame limpo com os dados (mesmo usado no Painel).
    """
    st.subheader("💬 Conversar com o Data Pilot")
    st.caption(
        "Python calcula, a IA só explica. "
        "Pergunte sobre receita, pedidos, clientes e cidades."
    )

    _inicializar_historico()
    _inicializar_estado_chave()

    with st.expander("🔑 Chave do OpenRouter (opcional)", expanded=not _tem_api_key()):
        st.caption(
            "Cole sua chave para usar nesta sessão. **Não exibimos, não salvamos "
            "em disco e não registramos em log;** a chave vive só na memória desta "
            "sessão e some ao fechar o navegador. Também aceitamos `OPENROUTER_API_KEY` "
            "no arquivo `.env` (copie de `.env.example`)."
        )
        nova_chave = st.text_input(
            "Sua chave OpenRouter",
            value="",
            type="password",
            placeholder="chave no formato sk-... (opcional)",
            key="input_chave",
            help="Deixe vazio para usar a chave do ambiente/.env. Digitar aqui "
            "sobrescreve só nesta sessão.",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 Usar esta chave (só nesta sessão)"):
                st.session_state.api_key_ui = (nova_chave or "").strip()
                st.success("Chave registrada nesta sessão.")
        with c2:
            if st.button("🧹 Esquecer chave"):
                st.session_state.api_key_ui = ""
                st.info("Chave removida da sessão. Se houver `.env`, ele volta a valer.")

    if not _tem_api_key():
        st.info(
            "⚙️ **Chat não configurado:** defina `OPENROUTER_API_KEY` no arquivo `.env` "
            "(copie de `.env.example`) ou cole sua chave acima. "
            "O Painel continua funcionando sem chave."
        )
        return

    # Botão para limpar a conversa.
    if st.button("🗑️ Limpar conversa", key="limpar"):
        st.session_state.historico = []
        st.session_state.ferramentas_usadas = []
        st.rerun()

    # Histórico anterior (respostas já geradas).
    historico: list[dict] = list(st.session_state.historico)
    for i, item in enumerate(historico):
        papel = item.get("role", "user")
        texto = item.get("content", "")
        if papel == "user":
            st.markdown(f"**Você:** {texto}")
        else:
            st.markdown(f"**Data Pilot:** {texto}")
            ferramentas = (
                st.session_state.ferramentas_usadas[i]
                if i < len(st.session_state.ferramentas_usadas)
                else []
            )
            if ferramentas:
                with st.expander("Ferramentas usadas"):
                    for nome, args_, res in ferramentas:
                        st.write(f"- `{nome}` com args `{args_}` -> `{res}`")

    # Entrada: text_input + botão enviar (simples e robusto no Streamlit >= 1.40).
    pergunta: str | None = None
    with st.form("form_pergunta", clear_on_submit=True):
        texto: str = st.text_input("Sua pergunta:", key="pergunta_input")
        enviar: bool = st.form_submit_button("Enviar")
    if enviar and texto and str(texto).strip():
        pergunta = str(texto).strip()

    if pergunta:
        st.markdown(f"**Você:** {pergunta}")

        # Conversa com o agente (loop de tool-calling dentro de agente.conversar).
        historico_aberto = [dict(m) for m in historico if m.get("role") in ("user", "assistant")]
        with st.spinner("Pensando... (o modelo escolhe as ferramentas)"):
            resposta_final = conversar(
                df, pergunta, historico=historico_aberto, api_key=_chave_atual()
            )

        st.session_state.historico.append({"role": "user", "content": pergunta})
        st.session_state.historico.append({"role": "assistant", "content": resposta_final})
        # Ferramentas desta rodada: o log detalhado vai para o terminal do servidor
        # (`[tool] ...`); aqui guardamos a rodada como lista vazia (expander vazio).
        st.session_state.ferramentas_usadas.append([])

        st.markdown(f"**Data Pilot:** {resposta_final}")
        with st.expander("Ferramentas usadas"):
            st.write(
                "As ferramentas executadas estão registradas no log do servidor "
                "(`[tool] nome args=... -> resultado`) e os números já estão na resposta acima."
            )
        st.rerun()

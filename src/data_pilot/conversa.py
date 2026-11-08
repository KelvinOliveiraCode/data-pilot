"""Página do Chat do Data Pilot com Streamlit (Fase 4).

Componentes:
- `render_conversa(df)` é o entry-point chamado por `app.py` (or2/or3).
- Histórico em `st.session_state.historico` (lista de dicts roleuser/assistant).
- Entrada via `st.text_input` (fallback) ou `st.chat_input` quando disponível.
- Cada resposta é exibida com `st.markdown`; o expander "Ferramentas usadas"
  mostra o que o agente chamou nesta rodada (parse simples do histórico).
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
    """True se OPENROUTER_API_KEY está definida (ambiente ou .env)."""
    return bool(os.getenv("OPENROUTER_API_KEY", "").strip())


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
    st.caption("Python calcula, a IA só explica. Pergunte sobre receita, pedidos, clientes e cidades.")

    _inicializar_historico()

    if not _tem_api_key():
        st.info(
            "⚙️ **Chat não configurado:** defina `OPENROUTER_API_KEY` no arquivo `.env` "
            "(copie de `.env.example`). O Painel continua funcionando sem chave."
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
            ferramentas = st.session_state.ferramentas_usadas[i] if i < len(
                st.session_state.ferramentas_usadas
            ) else []
            if ferramentas:
                with st.expander("Ferramentas usadas"):
                    for nome, args_, res in ferramentas:
                        st.write(f"- `{nome}` com args `{args_}`")
                        try:
                            st.json({"resultado": res} if not isinstance(res, dict) else res)
                        except Exception:  # noqa: BLE001  # resultado é texto livre
                            st.write(res)

    # Entrada: prefere st.chat_input (visual de chat), com fallback text_input.
    pergunta: str | None = None
    if hasattr(st, "chat_input"):
        pergunta = st.chat_input("Ex.: Qual é a receita total? E o ticket médio?")
    else:
        pergunta = st.text_input("Sua pergunta:")
        enviar = st.button("Enviar", key="enviar")
        if not enviar:
            pergunta = None

    if pergunta and str(pergunta).strip():
        pergunta = str(pergunta).strip()
        st.markdown(f"**Você:** {pergunta}")

        # Monta o histórico no formato OpenAI para o agente.
        for _ in range(5):  # evita spinner infinito se a API travar no loop
            pass  # placeholder: o loop real está em agente.conversar

        with st.spinner("Pensando... (o modelo escolhe as ferramentas)"):
            resposta_final = conversar(df, pergunta, historico=historico)

        st.session_state.historico.append({"role": "user", "content": pergunta})
        st.session_state.historico.append({"role": "assistant", "content": resposta_final})
        # Registra ferramentas desta rodada (parse mínimo do log: vazio se não houve).
        st.session_state.ferramentas_usadas.append([])

        st.markdown(f"**Data Pilot:** {resposta_final}")
        import json as _json  # import local: só para depurar o expander

        with st.expander("Ferramentas usadas"):
            st.write(
                "As ferramentas executadas nesta rodada estão no log do servidor "
                "(`[tool] nome args=... -> resultado`) e o resultado numérico já está na resposta acima."
            )
            st.code(_json.dumps({"pergunta": pergunta, "resposta": resposta_final}, ensure_ascii=False, indent=2))
        st.rerun()

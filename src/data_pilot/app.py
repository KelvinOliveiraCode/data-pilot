"""App Streamlit: tabs Painel / Conversa.

- Configuração de página e carregamento com fallback sintético.
- A aba Conversa importa ``render_conversa`` de ``data_pilot.conversa`` de
  forma preguiçosa (lazy): se o módulo ainda não existir (or3), mostra aviso
  amigável em vez de quebrar.
- Streamlit apenas aqui e em painel.py; Plotly apenas em graficos.py.
"""

from __future__ import annotations

import streamlit as st

from .dados import carregar_dados
from .painel import render_painel


def _carregar() -> object:
    """Carrega dados via carregar_dados, com aviso se usar fallback sintético.

    carregar_dados já gera sintético determinístico quando o arquivo falta;
    aqui apenas detectamos a ausência do arquivo para avisar o usuário.
    """
    from pathlib import Path

    path = Path("data/sales.csv")
    if not path.exists():
        st.warning(
            "Arquivo `data/sales.csv` não encontrado — usando dados sintéticos "
            "determinísticos (fallback). Coloque um CSV em `data/sales.csv` "
            "para usar dados reais."
        )
    try:
        return carregar_dados(path)
    except Exception as exc:  # pragma: no cover
        st.error(f"Falha ao carregar dados: {exc}")
        st.stop()


def main() -> None:
    st.set_page_config(page_title="Data Pilot", layout="wide")
    df = _carregar()

    aba_painel, aba_conversa = st.tabs(["📊 Painel", "💬 Conversa"])

    with aba_painel:
        render_painel(df)

    with aba_conversa:
        try:
            from .conversa import render_conversa

            render_conversa(df)
        except ImportError:
            st.info(
                "A conversa ainda não foi implementada (or3). "
                "Instale/complete `src/data_pilot/conversa.py` com `render_conversa(df)` "
                "para habilitar esta aba."
            )


if __name__ == "__main__":
    main()

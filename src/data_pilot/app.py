"""App Streamlit: tabs Painel / Conversa.

- Configuração de página e carregamento com fallback sintético.
- A aba Conversa importa ``render_conversa`` de ``data_pilot.conversa`` de
  forma preguiçosa (lazy): se o módulo ainda não existir (or3), mostra aviso
  amigável em vez de quebrar.
- Streamlit apenas aqui e em painel.py; Plotly apenas em graficos.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

# app.py é executado como script solto pelo Streamlit (`streamlit run .../app.py`),
# sem package parent => `from .dados import ...` falha com
# "ImportError: attempted relative import with no known parent package".
# Solução: garantir que a pasta src/ entra no sys.path e usar imports absolutos.
# (Com `python -m data_pilot.app` ou `data-pilot` também funciona.)
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from data_pilot.dados import carregar_dados  # noqa: E402
from data_pilot.painel import render_painel  # noqa: E402


def _carregar() -> object:
    """Carrega dados via carregar_dados, com aviso se usar fallback sintético.

    carregar_dados já gera sintético determinístico quando o arquivo falta;
    aqui apenas detectamos a ausência do arquivo para avisar o usuário.
    """
    # Resolve o CSV a partir da raiz do repo (ou do CWD se existirem diferenças)
    _candidates = [
        Path("data/sales.csv"),
        Path(__file__).resolve().parents[2] / "data" / "sales.csv",
    ]
    path = next((p for p in _candidates if p.exists()), _candidates[0])
    _ = os  # (mantido para compatibilidade futura com paths relativos)
    if not path.exists():
        st.warning(
            "Arquivo `data/sales.csv` não encontrado: usando dados sintéticos "
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
            from data_pilot.conversa import render_conversa

            render_conversa(df)
        except ImportError:
            st.info(
                "A conversa ainda não foi implementada (or3). "
                "Instale/complete `src/data_pilot/conversa.py` com `render_conversa(df)` "
                "para habilitar esta aba."
            )


if __name__ == "__main__":
    main()

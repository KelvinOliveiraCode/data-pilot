"""Página do painel (Streamlit apenas aqui e em app.py)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .graficos import (
    grafico_distribuicao_status,
    grafico_receita_mensal,
    grafico_receita_por_categoria,
    grafico_top5_cidades,
)
from .metricas import (
    clientes_unicos,
    filtrar_periodo,
    pedidos_concluidos,
    receita_media_por_cliente,
    receita_total,
    taxa_cancelamento,
    ticket_medio,
)


def _fmt_brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_painel(df: pd.DataFrame) -> None:
    """Renderiza o painel de vendas (KPIs, filtros e gráficos)."""
    st.title("📊 Data Pilot — Painel de Vendas")

    # Sidebar: filtros
    with st.sidebar:
        st.header("Filtros")

        categorias = []
        if "categoria" in df.columns:
            categorias = sorted(df["categoria"].dropna().unique().tolist())
        cat_sel = st.selectbox(
            "Categoria",
            options=["Todas"] + categorias,
            index=0,
        )

        status_opts = []
        if "status" in df.columns:
            status_opts = sorted(df["status"].dropna().unique().tolist())
        default_status = ["concluido"] if "concluido" in status_opts else status_opts[:1]
        status_sel = st.multiselect(
            "Status",
            options=status_opts,
            default=default_status,
        )

        # Período: mínimo/máximo do dataset
        dmin = dmax = None
        if "data_pedido" in df.columns and not df.empty:
            dmin = pd.to_datetime(df["data_pedido"], errors="coerce").min()
            dmax = pd.to_datetime(df["data_pedido"], errors="coerce").max()
        if pd.notna(dmin) and pd.notna(dmax):
            periodo = st.date_input(
                "Período",
                value=(dmin.date(), dmax.date()),
                min_value=dmin.date(),
                max_value=dmax.date(),
            )
        else:
            periodo = st.date_input("Período", value=())

    # Aplica filtros
    df_f = df.copy()
    # filtrar_periodo aceita tupla (início, fim) ou valores avulsos
    if periodo:
        if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
            df_f = filtrar_periodo(df_f, periodo[0], periodo[1])
        elif isinstance(periodo, (tuple, list)) and len(periodo) == 1:
            df_f = filtrar_periodo(df_f, periodo[0], None)
        else:
            df_f = filtrar_periodo(df_f, periodo, None)

    if cat_sel and cat_sel != "Todas" and "categoria" in df_f.columns:
        df_f = df_f[df_f["categoria"] == cat_sel]

    if status_sel and "status" in df_f.columns:
        df_f = df_f[df_f["status"].isin(status_sel)]

    # KPIs (4 cards) — sobre o df filtrado
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Receita total", _fmt_brl(receita_total(df_f)))
    col2.metric("Pedidos concluídos", pedidos_concluidos(df_f))
    col3.metric("Ticket médio", _fmt_brl(ticket_medio(df_f)))
    col4.metric("Clientes únicos", clientes_unicos(df_f))

    # 2 gráficos lado a lado
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(grafico_receita_por_categoria(df_f), use_container_width=True)
    with col_b:
        st.plotly_chart(grafico_top5_cidades(df_f), use_container_width=True)

    # 1 gráfico linha: receita mensal
    st.plotly_chart(grafico_receita_mensal(df_f), use_container_width=True)

    # Distribuição de status sempre sobre o df filtrado pré-status?
    # A especificação pede "sobre df completo" em graficos.py; no painel
    # mostramos sobre o df com filtros categoria/período (sem status) p/ não
    # esconder as outras fatias. Reaproveita df_f2 (sem filtro de status).
    df_status_base = df.copy()
    if periodo:
        if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
            df_status_base = filtrar_periodo(df_status_base, periodo[0], periodo[1])
        elif isinstance(periodo, (tuple, list)) and len(periodo) == 1:
            df_status_base = filtrar_periodo(df_status_base, periodo[0], None)
        else:
            df_status_base = filtrar_periodo(df_status_base, periodo, None)
    if cat_sel and cat_sel != "Todas" and "categoria" in df_status_base.columns:
        df_status_base = df_status_base[df_status_base["categoria"] == cat_sel]
    st.plotly_chart(
        grafico_distribuicao_status(df_status_base), use_container_width=True
    )

    # Rodapé
    st.divider()
    st.write(f"Receita média por cliente: **{_fmt_brl(receita_media_por_cliente(df_f))}**")
    st.write(f"Taxa de cancelamento: **{taxa_cancelamento(df_f):.1%}**")

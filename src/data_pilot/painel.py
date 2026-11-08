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

# Compatibilidade de API: o plano previa nomes curtos em ``metricas.py``,
# mas a implementação das Fases 1+2 expõe ``calcular_*``. Importamos o que
# existe e expomos aliases curtos quando necessário.
try:
    from .metricas import calcular_clientes_unicos as clientes_unicos
    from .metricas import calcular_pedidos_concluidos as pedidos_concluidos
    from .metricas import calcular_receita_media_por_cliente as receita_media_por_cliente
    from .metricas import calcular_receita_total as receita_total
    from .metricas import calcular_taxa_cancelamento as taxa_cancelamento
    from .metricas import calcular_ticket_medio as ticket_medio
    from .metricas import filtrar_periodo
except ImportError:  # pragma: no cover - API curta do plano
    from .metricas import (
        clientes_unicos,  # type: ignore[no-redef]
        filtrar_periodo,  # type: ignore[no-redef]
        pedidos_concluidos,  # type: ignore[no-redef]
        receita_media_por_cliente,  # type: ignore[no-redef]
        receita_total,  # type: ignore[no-redef]
        taxa_cancelamento,  # type: ignore[no-redef]
        ticket_medio,  # type: ignore[no-redef]
    )


def _fmt_brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _col_data(df: pd.DataFrame) -> str | None:
    if "data" in df.columns:
        return "data"
    if "data_pedido" in df.columns:
        return "data_pedido"
    return None


def _filtrar_periodo_compat(df: pd.DataFrame, inicio, fim) -> pd.DataFrame:
    """Chama filtrar_periodo aceitando date/datetime/str em qualquer API."""
    try:
        return filtrar_periodo(df, data_inicio=inicio, data_fim=fim)  # type: ignore[arg-type]
    except TypeError:
        # API alternativa pode exigir string
        return filtrar_periodo(
            df,
            data_inicio=str(inicio) if inicio is not None else None,
            data_fim=str(fim) if fim is not None else None,
        )


def _taxa_cancelamento(df: pd.DataFrame) -> float:
    taxa = taxa_cancelamento(df)
    # metricas reais devolve 0–100 (por cento); formato {:.1%} espera 0–1.
    # Detecta: se >1, é percentual e já mostramos como %.
    return taxa


def render_painel(df: pd.DataFrame) -> None:
    """Renderiza o painel de vendas (KPIs, filtros e gráficos)."""
    st.title("📊 Data Pilot: Painel de Vendas")

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
        col_data = _col_data(df)
        dmin = dmax = None
        if col_data and not df.empty:
            dmin = pd.to_datetime(df[col_data], errors="coerce").min()
            dmax = pd.to_datetime(df[col_data], errors="coerce").max()
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
    if periodo:
        if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
            df_f = _filtrar_periodo_compat(df_f, periodo[0], periodo[1])
        elif isinstance(periodo, (tuple, list)) and len(periodo) == 1:
            df_f = _filtrar_periodo_compat(df_f, periodo[0], None)
        else:
            df_f = _filtrar_periodo_compat(df_f, periodo, None)

    if cat_sel and cat_sel != "Todas" and "categoria" in df_f.columns:
        df_f = df_f[df_f["categoria"] == cat_sel]

    if status_sel and "status" in df_f.columns:
        df_f = df_f[df_f["status"].isin(status_sel)]

    # KPIs (4 cards): sobre o df filtrado
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

    # Distribuição de status: sobre base SEM filtro de status (para não
    # esconder as outras fatias): a função em graficos.py já usa o df
    # completo que recebe aqui (com período/categoria aplicados).
    df_status_base = df.copy()
    if periodo:
        if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
            df_status_base = _filtrar_periodo_compat(df_status_base, periodo[0], periodo[1])
        elif isinstance(periodo, (tuple, list)) and len(periodo) == 1:
            df_status_base = _filtrar_periodo_compat(df_status_base, periodo[0], None)
        else:
            df_status_base = _filtrar_periodo_compat(df_status_base, periodo, None)
    if cat_sel and cat_sel != "Todas" and "categoria" in df_status_base.columns:
        df_status_base = df_status_base[df_status_base["categoria"] == cat_sel]
    st.plotly_chart(grafico_distribuicao_status(df_status_base), use_container_width=True)

    # Rodapé
    st.divider()
    st.write(f"Receita média por cliente: **{_fmt_brl(receita_media_por_cliente(df_f))}**")
    taxa = _taxa_cancelamento(df_f)
    if taxa > 1:  # já é percentual (0–100)
        st.write(f"Taxa de cancelamento: **{taxa:.1f}%**")
    else:
        st.write(f"Taxa de cancelamento: **{taxa:.1%}**")

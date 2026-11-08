"""Gráficos Plotly puros (sem Streamlit, sem side effects).

Funções retornam ``plotly.graph_objects.Figure`` e operam apenas via
:mod:`data_pilot.metricas` (com fallbacks locais quando a API varia).
Sem ``st.*``.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

# Compatibilidade: o plano da Fase 3 previa ``receita_por_categoria`` /
# ``receita_mensal`` / ``top5_cidades_receita`` em ``metricas.py``, mas a
# implementação entregue das Fases 1+2 expõe ``calcular_top5_cidades_receita``
# (e não define receita por categoria/mensal). Importamos o que existe e,
# para o que falta, calculamos localmente a partir das colunas do dataset.
try:  # API real das Fases 1+2
    from .metricas import calcular_top5_cidades_receita as _top5_impl  # noqa: F401
except ImportError:  # pragma: no cover
    _top5_impl = None

try:  # possível API alternativa
    from .metricas import top5_cidades_receita as _top5_alt  # noqa: F401
except ImportError:  # pragma: no cover
    _top5_alt = None


def _concluidos(df: pd.DataFrame) -> pd.DataFrame:
    if "status" not in df.columns:
        return df
    return df[df["status"].map(lambda s: str(s).strip().lower() == "concluido")]


def _top5_cidades(df: pd.DataFrame) -> pd.DataFrame:
    if _top5_impl is not None:
        try:
            return _top5_impl(df)
        except Exception:
            pass
    if _top5_alt is not None:
        try:
            return _top5_alt(df)
        except Exception:
            pass
    sub = _concluidos(df)
    if "cidade" not in sub.columns or "receita" not in sub.columns or sub.empty:
        return pd.DataFrame(columns=["cidade", "receita"])
    return (
        sub.groupby("cidade", dropna=False)["receita"]
        .sum()
        .reset_index()
        .sort_values("receita", ascending=False)
        .head(5)
        .reset_index(drop=True)
    )


def _receita_categoria(df: pd.DataFrame) -> pd.DataFrame:
    sub = _concluidos(df)
    if "categoria" not in sub.columns or "receita" not in sub.columns or sub.empty:
        return pd.DataFrame(columns=["categoria", "receita"])
    return (
        sub.groupby("categoria", dropna=False)["receita"]
        .sum()
        .reset_index()
        .sort_values("receita", ascending=False)
        .reset_index(drop=True)
    )


def _receita_mensal_df(df: pd.DataFrame) -> pd.DataFrame:
    sub = _concluidos(df)
    if "receita" not in sub.columns or sub.empty:
        return pd.DataFrame(columns=["mes", "receita"])
    col_data = "data" if "data" in sub.columns else "data_pedido"
    if col_data not in sub.columns:
        return pd.DataFrame(columns=["mes", "receita"])
    datas = pd.to_datetime(sub[col_data], errors="coerce")
    sub = sub.copy()
    sub["_mes"] = datas.dt.strftime("%Y-%m")
    sub = sub.dropna(subset=["_mes"])
    if sub.empty:
        return pd.DataFrame(columns=["mes", "receita"])
    return (
        sub.groupby("_mes", dropna=False)["receita"]
        .sum()
        .reset_index()
        .rename(columns={"_mes": "mes"})
        .sort_values("mes")
        .reset_index(drop=True)
    )


def grafico_receita_por_categoria(df: pd.DataFrame) -> go.Figure:
    """Bar vertical da receita por categoria (concluídos, DESC)."""
    try:  # usa metricas se existir no futuro
        from .metricas import receita_por_categoria

        dados = receita_por_categoria(df)
    except (ImportError, TypeError):
        dados = _receita_categoria(df)
    fig = go.Figure(
        data=[
            go.Bar(
                x=dados["categoria"].tolist() if not dados.empty else [],
                y=dados["receita"].tolist() if not dados.empty else [],
                name="Receita",
            )
        ]
    )
    fig.update_layout(
        title="Receita por categoria",
        xaxis_title="Categoria",
        yaxis_title="Receita (R$)",
        template="plotly_white",
    )
    return fig


def grafico_top5_cidades(df: pd.DataFrame) -> go.Figure:
    """Bar horizontal do top-5 de cidades por receita (concluídos)."""
    dados = _top5_cidades(df)
    # Plotly desenha o primeiro elemento embaixo; invertemos p/ maior no topo.
    dados = dados.iloc[::-1].reset_index(drop=True) if not dados.empty else dados
    fig = go.Figure(
        data=[
            go.Bar(
                x=dados["receita"].tolist() if not dados.empty else [],
                y=dados["cidade"].tolist() if not dados.empty else [],
                orientation="h",
                name="Receita",
            )
        ]
    )
    fig.update_layout(
        title="Top 5 cidades por receita",
        xaxis_title="Receita (R$)",
        yaxis_title="Cidade",
        template="plotly_white",
    )
    return fig


def grafico_receita_mensal(df: pd.DataFrame) -> go.Figure:
    """Linha + marcadores da receita mensal (concluídos)."""
    try:  # usa metricas se existir no futuro
        from .metricas import receita_mensal

        dados = receita_mensal(df)
    except (ImportError, TypeError):
        dados = _receita_mensal_df(df)
    fig = go.Figure(
        data=[
            go.Scatter(
                x=dados["mes"].tolist() if not dados.empty else [],
                y=dados["receita"].tolist() if not dados.empty else [],
                mode="lines+markers",
                name="Receita",
            )
        ]
    )
    fig.update_layout(
        title="Receita mensal",
        xaxis_title="Mês",
        yaxis_title="Receita (R$)",
        template="plotly_white",
    )
    return fig


def grafico_distribuicao_status(df: pd.DataFrame) -> go.Figure:
    """Donut com contagens por status sobre o **df completo** (não só concluídos)."""
    if "status" not in df.columns or df.empty:
        contagens = pd.Series(dtype=int)
    else:
        contagens = df["status"].fillna("").value_counts(dropna=False)

    labels = contagens.index.astype(str).tolist()
    values = contagens.tolist()

    if not labels:
        labels = ["sem dados"]
        values = [0]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                name="Pedidos",
            )
        ]
    )
    fig.update_layout(
        title="Distribuição de pedidos por status",
        template="plotly_white",
    )
    return fig

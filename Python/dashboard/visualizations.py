import pandas as pd
import plotly.express as px
import streamlit as st

PALETA = {
    "mist": "#CBD5E1",
    "smoke": "#94A3B8",
    "steel": "#64748B",
    "slate": "#475569",
    "graphite": "#334155",
    "charcoal": "#1F2937",
}


def _estilizar_figura(fig):
    text_color = st.get_option("theme.textColor") or "#0f172a"
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": text_color},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(127,127,127,0.25)")
    return fig


def render_dashboard_charts(
    df_resumo: pd.DataFrame,
    df_evolucao_mensal: pd.DataFrame,
) -> None:
    if df_evolucao_mensal.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    col_top_1, col_top_2 = st.columns(2)

    with col_top_1:
        with st.container(border=True):
            fig_percentual = px.bar(
                df_evolucao_mensal,
                x="mes",
                y="percentual_qtd_x_frota",
                title="% QTD x FROTA",
                text="percentual_qtd_x_frota",
                color="percentual_qtd_x_frota",
                color_continuous_scale=[PALETA["mist"], PALETA["steel"], PALETA["charcoal"]],
            )
            fig_percentual.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            fig_percentual.update_coloraxes(showscale=False)
            st.plotly_chart(_estilizar_figura(fig_percentual), use_container_width=True)

    with col_top_2:
        with st.container(border=True):
            fig_qtd_frota = px.line(
                df_evolucao_mensal,
                x="mes",
                y=["total_qtd", "total_frota"],
                markers=True,
                title="QTD x FROTA",
                color_discrete_map={
                    "total_qtd": PALETA["graphite"],
                    "total_frota": PALETA["smoke"],
                },
            )
            fig_qtd_frota.update_traces(line={"width": 2.5}, marker={"size": 5})
            st.plotly_chart(_estilizar_figura(fig_qtd_frota), use_container_width=True)

    col_bottom_1, col_bottom_2 = st.columns(2)

    with col_bottom_1:
        with st.container(border=True):
            fig_servico = px.bar(
                df_evolucao_mensal,
                x="mes",
                y="total_qtd",
                title="QTD SERVICO EXECUTADO",
                text="total_qtd",
                color="total_qtd",
                color_continuous_scale=[PALETA["mist"], PALETA["slate"], PALETA["graphite"]],
            )
            fig_servico.update_traces(textposition="outside")
            fig_servico.update_coloraxes(showscale=False)
            st.plotly_chart(_estilizar_figura(fig_servico), use_container_width=True)

    with col_bottom_2:
        with st.container(border=True):
            ranking = df_resumo.sort_values("total_qtd", ascending=True).tail(8)
            fig_ranking = px.bar(
                ranking,
                x="total_qtd",
                y="equipamento",
                orientation="h",
                title="TOTAL PRINCIPAIS SERVICOS",
                text="media_percentual",
                color="total_qtd",
                color_continuous_scale=[PALETA["smoke"], PALETA["slate"], PALETA["charcoal"]],
            )
            fig_ranking.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            fig_ranking.update_coloraxes(showscale=False)
            st.plotly_chart(_estilizar_figura(fig_ranking), use_container_width=True)


def render_resumo_chart(df_resumo: pd.DataFrame) -> None:
    if df_resumo.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    with st.container(border=True):
        fig = px.bar(
            df_resumo.sort_values("percentual_recalculado", ascending=False),
            x="equipamento",
            y="percentual_recalculado",
            title="% QTD x Frota por Equipamento",
            text="percentual_recalculado",
            color="percentual_recalculado",
            color_continuous_scale=[PALETA["mist"], PALETA["steel"], PALETA["charcoal"]],
        )
        fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(_estilizar_figura(fig), use_container_width=True)

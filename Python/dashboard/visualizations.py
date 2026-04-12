import pandas as pd
import plotly.express as px
import streamlit as st


def _estilizar_figura(fig):
    fig.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"color": "#0f172a"},
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
    fig.update_yaxes(gridcolor="#e2e8f0")
    return fig


def _abrir_secao() -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)


def _fechar_secao() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard_charts(
    df_resumo: pd.DataFrame,
    df_evolucao_mensal: pd.DataFrame,
) -> None:
    if df_evolucao_mensal.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    col_top_1, col_top_2 = st.columns(2)

    with col_top_1:
        _abrir_secao()
        fig_percentual = px.bar(
            df_evolucao_mensal,
            x="mes",
            y="percentual_qtd_x_frota",
            title="% QTD x FROTA",
            text="percentual_qtd_x_frota",
        )
        fig_percentual.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
        st.plotly_chart(_estilizar_figura(fig_percentual), use_container_width=True)
        _fechar_secao()

    with col_top_2:
        _abrir_secao()
        fig_qtd_frota = px.line(
            df_evolucao_mensal,
            x="mes",
            y=["total_qtd", "total_frota"],
            markers=True,
            title="QTD x FROTA",
        )
        st.plotly_chart(_estilizar_figura(fig_qtd_frota), use_container_width=True)
        _fechar_secao()

    col_bottom_1, col_bottom_2 = st.columns(2)

    with col_bottom_1:
        _abrir_secao()
        fig_servico = px.bar(
            df_evolucao_mensal,
            x="mes",
            y="total_qtd",
            title="QTD SERVICO EXECUTADO",
            text="total_qtd",
        )
        fig_servico.update_traces(textposition="outside")
        st.plotly_chart(_estilizar_figura(fig_servico), use_container_width=True)
        _fechar_secao()

    with col_bottom_2:
        _abrir_secao()
        ranking = df_resumo.sort_values("total_qtd", ascending=True).tail(8)
        fig_ranking = px.bar(
            ranking,
            x="total_qtd",
            y="equipamento",
            orientation="h",
            title="TOTAL PRINCIPAIS SERVICOS",
            text="media_percentual",
        )
        fig_ranking.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
        st.plotly_chart(_estilizar_figura(fig_ranking), use_container_width=True)
        _fechar_secao()


def render_resumo_chart(df_resumo: pd.DataFrame) -> None:
    if df_resumo.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    _abrir_secao()
    fig = px.bar(
        df_resumo.sort_values("percentual_recalculado", ascending=False),
        x="equipamento",
        y="percentual_recalculado",
        title="% QTD x Frota por Equipamento",
        text="percentual_recalculado",
    )
    fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    st.plotly_chart(_estilizar_figura(fig), use_container_width=True)
    _fechar_secao()

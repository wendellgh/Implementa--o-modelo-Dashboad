import pandas as pd
import plotly.express as px
import streamlit as st


def render_graficos_resumo(df_resumo_filtrado: pd.DataFrame) -> None:
    fig_qtd_frota = px.bar(
        df_resumo_filtrado,
        x="equipamento",
        y=["total_qtd", "total_frota"],
        barmode="group",
        title="QTD x Frota por Equipamento",
    )
    st.plotly_chart(fig_qtd_frota, use_container_width=True)

    fig_percentual = px.bar(
        df_resumo_filtrado,
        x="equipamento",
        y="percentual_recalculado",
        title="% QTD x Frota por Equipamento",
        text="percentual_recalculado",
    )
    fig_percentual.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    st.plotly_chart(fig_percentual, use_container_width=True)


def render_grafico_evolucao(df_evolucao_filtrado: pd.DataFrame) -> None:
    if df_evolucao_filtrado.empty:
        st.info("Sem dados de evolucao mensal para o filtro selecionado.")
        return

    fig_evolucao = px.line(
        df_evolucao_filtrado,
        x="mes",
        y="percentual_qtd_x_frota",
        color="equipamento",
        markers=True,
        title="Evolucao Mensal - % QTD x Frota",
    )
    st.plotly_chart(fig_evolucao, use_container_width=True)


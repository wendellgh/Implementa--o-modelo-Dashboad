import streamlit as st

from dashboard.config import APP_TITLE, PAGE_CONFIG
from dashboard.data import carregar_dados
from dashboard.filters import aplicar_filtro_equipamento
from dashboard.metrics import calcular_kpis, render_kpis
from dashboard.tables import render_tabela_resumo
from dashboard.visualizations import render_grafico_evolucao, render_graficos_resumo


def main() -> None:
    st.set_page_config(**PAGE_CONFIG)
    st.title(APP_TITLE)

    try:
        df_resumo, df_evolucao = carregar_dados()
    except Exception as error:
        st.error(f"Erro ao carregar dados do banco: {error}")
        st.stop()

    if df_resumo.empty:
        st.warning("A view vw_dashboard_resumo nao retornou dados.")
        st.stop()

    kpis = calcular_kpis(df_resumo)
    render_kpis(kpis)
    st.divider()

    _, df_resumo_filtrado, df_evolucao_filtrado = aplicar_filtro_equipamento(
        df_resumo=df_resumo,
        df_evolucao=df_evolucao,
    )

    render_graficos_resumo(df_resumo_filtrado)
    render_grafico_evolucao(df_evolucao_filtrado)
    render_tabela_resumo(df_resumo_filtrado)


if __name__ == "__main__":
    main()

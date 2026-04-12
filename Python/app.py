import streamlit as st

from dashboard.config import APP_TITLE, PAGE_CONFIG
from dashboard.data import (
    carregar_base,
    montar_evolucao_mensal,
    montar_resumo_equipamento,
    montar_tabela_evolucao,
)
from dashboard.filters import aplicar_filtros, render_sidebar
from dashboard.metrics import calcular_kpis, render_kpis
from dashboard.styles import aplicar_estilos_globais, render_titulo_principal
from dashboard.tables import render_tabela_detalhe, render_tabela_evolucao, render_tabela_resumo
from dashboard.visualizations import render_dashboard_charts, render_resumo_chart


def main() -> None:
    st.set_page_config(**PAGE_CONFIG)
    aplicar_estilos_globais()

    try:
        df_base = carregar_base()
    except Exception as error:
        st.error(f"Erro ao carregar dados do banco: {error}")
        st.stop()

    if df_base.empty:
        st.warning("Sem dados na tabela base_historica_manutencao.")
        st.stop()

    filtros = render_sidebar(df_base)
    menu = str(filtros["menu"])
    df_filtrado = aplicar_filtros(df_base, filtros)

    resumo = montar_resumo_equipamento(df_filtrado)
    evolucao_mensal = montar_evolucao_mensal(df_filtrado)
    evolucao_tabela = montar_tabela_evolucao(df_filtrado)

    render_titulo_principal(APP_TITLE)

    if menu == "Dashboard":
        kpis = calcular_kpis(resumo)
        render_kpis(kpis)
        st.write("")
        render_dashboard_charts(resumo, evolucao_mensal)
    elif menu == "Resumo":
        render_resumo_chart(resumo)
        render_tabela_resumo(resumo)
    else:
        render_tabela_evolucao(evolucao_tabela)
        render_tabela_detalhe(df_filtrado)


if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd

from dashboard.auth import render_login, usuario_eh_admin
from dashboard.config import APP_TITLE, PAGE_CONFIG
from dashboard.data import (
    carregar_base,
    montar_equipamentos_por_contrato,
    montar_evolucao_mensal,
    montar_frota_operadora_por_mes,
    montar_manutencao_por_contrato,
    montar_resumo_equipamento,
    montar_servicos_executados_por_tipo,
    montar_tabela_evolucao,
    carregar_base_outra_tabela
)
from dashboard.database import get_db_diagnostics, get_db_target_label
from dashboard.data_entry import render_entrada_dados
from dashboard.filters import aplicar_filtros, render_sidebar
from dashboard.metrics import calcular_kpis, render_kpis, render_total_servicos_executados
from dashboard.styles import aplicar_estilos_globais, render_titulo_principal
from dashboard.tables import render_tabela_detalhe, render_tabela_evolucao, render_tabela_resumo, render_servicos_executados
from dashboard.visualizations import (
    render_dashboard_charts,
    render_frota_operadora_chart,
    render_resumo_chart,
    render_servicos_executados_chart,
)

ENTRADA_DADOS_MENU_ITEM = "Entrada de Dados"
ORACLE_DESTBOAD_MENU_ITEM = "Oracle DESTBOAD"


def render_consulta_destboad_oracle() -> None:
    st.subheader("Consulta Oracle - DESTBOAD")

    if not usuario_eh_admin():
        st.warning("A consulta Oracle esta disponivel apenas para usuarios administradores.")
        return

    if st.button("Consultar Oracle", type="primary"):
        try:
            from Oracle.repositorio_oracle import consultar_destboad_json

            dados = consultar_destboad_json()
            df_destboad = pd.DataFrame(dados)

            st.success(f"Consulta realizada com sucesso. Registros retornados: {len(dados)}")
            st.json(dados)

            csv = df_destboad.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Baixar CSV",
                data=csv,
                file_name="saida_oracle_destboad.csv",
                mime="text/csv",
            )

        except Exception as erro:
            st.error("Erro ao consultar Oracle.")
            st.exception(erro)


def main() -> None:
    st.set_page_config(**PAGE_CONFIG)
    aplicar_estilos_globais()
    render_login()

    try:
        df_base = carregar_base()
    except Exception as error:
        st.error(f"Erro ao carregar dados do banco: {error}")
        st.caption(f"Destino de conexao detectado: {get_db_target_label()}")
        st.caption("Diagnostico de secrets/env:")
        st.json(get_db_diagnostics())
        error_text = str(error).lower()
        if "localhost" in error_text or "connection refused" in error_text:
            st.info(
                "No Streamlit Cloud, configure DB remoto em Secrets: DATABASE_URL, "
                "NEON_DATABASE_URL ou DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD."
            )
        st.stop()

    if df_base.empty:
        st.warning("Sem dados na tabela base_historica_manutencao.")
        st.stop()

    filtros = render_sidebar(df_base)
    menu = str(filtros["menu"])
    df_filtrado = aplicar_filtros(df_base, filtros)

    resumo = montar_resumo_equipamento(df_filtrado)
    equipamentos_contrato = montar_equipamentos_por_contrato(df_filtrado)
    evolucao_mensal = montar_evolucao_mensal(df_filtrado)
    evolucao_tabela = montar_tabela_evolucao(df_filtrado)
    frota_operadora = montar_frota_operadora_por_mes(df_filtrado)
    manutencao_contrato = montar_manutencao_por_contrato(df_filtrado)

    render_titulo_principal(APP_TITLE)

    if menu == "Dashboard":
        kpis = calcular_kpis(resumo)
        render_kpis(kpis)
        st.write("")
        render_dashboard_charts(resumo, evolucao_mensal, manutencao_contrato, equipamentos_contrato)
    elif menu == "Resumo":
        render_resumo_chart(resumo)
        render_tabela_resumo(resumo)
    elif menu == ENTRADA_DADOS_MENU_ITEM:
        render_entrada_dados(df_base)
    elif menu == "Contando Frota - Teste.":
        render_frota_operadora_chart(frota_operadora)
    elif menu =="Serviços Executados - Teste":
        df_servicos = carregar_base_outra_tabela()
        if df_servicos.empty:
            st.warning("Sem dados na tabela servico_executado.")
            st.stop()

        servicos_filtrados = aplicar_filtros(df_servicos, filtros)
        servicos_resumo = montar_servicos_executados_por_tipo(servicos_filtrados)
        total_servicos = int(servicos_filtrados["qtd_servico"].sum())
        render_total_servicos_executados(total_servicos)
        st.write("")
        render_servicos_executados_chart(servicos_resumo)
        render_servicos_executados(servicos_filtrados)
    elif menu == ORACLE_DESTBOAD_MENU_ITEM:
        render_consulta_destboad_oracle()

    else:
        render_tabela_evolucao(evolucao_tabela)
        render_tabela_detalhe(df_filtrado)


if __name__ == "__main__":
    main()

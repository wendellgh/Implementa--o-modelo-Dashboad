import streamlit as st

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
ORACLE_DESTBOAD_MENU_ITEM = "Dados da Manutenção - Oracle"


def render_consulta_destboad_oracle() -> None:
    st.subheader("Dados da Manutenção - Oracle")

    if not usuario_eh_admin():
        st.warning("A consulta Oracle esta disponivel apenas para usuarios administradores.")
        return

    st.info(
        "Consultar Oracle salva os CSVs localmente. Para atualizar o dashboard, "
        "mantenha a carga no banco habilitada."
    )

    carregar_apos_consulta = st.checkbox("Carregar no banco apos consultar", value=True)
    substituir_tabela = st.checkbox("Substituir toda a tabela servicos_executados")

    if st.button("Consultar Oracle", type="primary"):
        try:
            from Oracle.repositorio_oracle import consultar_destboad_dataframe
            from Oracle.servicos_executados_pipeline import (
                CSV_DESTBOAD_BRUTO,
                CSV_SERVICOS_EXECUTADOS,
                carregar_servicos_executados_csv,
                salvar_servicos_executados_csv,
                transformar_destboad_em_servicos_executados,
            )

            df_destboad = consultar_destboad_dataframe()

            CSV_DESTBOAD_BRUTO.parent.mkdir(parents=True, exist_ok=True)
            df_destboad.to_csv(CSV_DESTBOAD_BRUTO, index=False, encoding="utf-8-sig")

            df_servicos = transformar_destboad_em_servicos_executados(df_destboad)
            salvar_servicos_executados_csv(df_servicos, CSV_SERVICOS_EXECUTADOS)

            st.success(
                "Consulta realizada com sucesso. "
                f"Registros Oracle: {len(df_destboad)} | "
                f"linhas para servicos_executados: {len(df_servicos)}"
            )
            st.caption(f"CSV bruto salvo em: {CSV_DESTBOAD_BRUTO}")
            st.caption(f"CSV para carga salvo em: {CSV_SERVICOS_EXECUTADOS}")

            st.dataframe(df_servicos.head(100), use_container_width=True)

            if carregar_apos_consulta:
                total_carregado = carregar_servicos_executados_csv(
                    CSV_SERVICOS_EXECUTADOS,
                    substituir_tabela=substituir_tabela,
                    substituir_periodos_csv=not substituir_tabela,
                )
                carregar_base_outra_tabela.clear()
                st.success(f"Banco atualizado. Linhas carregadas: {total_carregado}")

            csv_oracle = df_destboad.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Baixar CSV Oracle bruto",
                data=csv_oracle,
                file_name="saida_oracle_destboad.csv",
                mime="text/csv",
            )

            csv_servicos = df_servicos.to_csv(sep=";", index=False).encode("utf-8-sig")
            st.download_button(
                "Baixar CSV servicos_executados",
                data=csv_servicos,
                file_name="servicos_executados.csv",
                mime="text/csv",
            )

        except Exception as erro:
            st.error("Erro ao consultar Oracle.")
            st.exception(erro)

    if st.button("Carregar CSV no banco"):
        try:
            from Oracle.servicos_executados_pipeline import (
                CSV_SERVICOS_EXECUTADOS,
                carregar_servicos_executados_csv,
            )

            total_carregado = carregar_servicos_executados_csv(
                CSV_SERVICOS_EXECUTADOS,
                substituir_tabela=substituir_tabela,
                substituir_periodos_csv=not substituir_tabela,
            )
            carregar_base_outra_tabela.clear()
            st.success(f"Carga concluida. Linhas carregadas: {total_carregado}")
        except Exception as erro:
            st.error("Erro ao carregar CSV local.")
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

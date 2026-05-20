import importlib.util
import tempfile
from collections.abc import Callable
from pathlib import Path

import streamlit as st

from dashboard.auth import render_login, usuario_eh_admin
from dashboard.config import APP_TITLE, PAGE_CONFIG
from dashboard.analise_falhas import render_analise_falhas
from dashboard.data import (
    carregar_base,
    carregar_base_outra_tabela,
    montar_equipamentos_por_contrato,
    montar_evolucao_mensal,
    montar_frota_contrato_por_mes,
    montar_manutencao_por_contrato,
    montar_resumo_equipamento,
    montar_servicos_executados_por_tipo,
    montar_tabela_evolucao,
)
from dashboard.database import get_db_diagnostics, get_db_target_label
from dashboard.data_entry import render_entrada_dados
from dashboard.filters import aplicar_filtros, render_filtros, render_sidebar
from dashboard.metrics import (
    calcular_kpis,
    render_kpis,
    render_total_servicos_executados,
)
from dashboard.styles import aplicar_estilos_globais, render_titulo_principal
from dashboard.tables import (
    render_servicos_executados,
    render_tabela_detalhe,
    render_tabela_evolucao,
    render_tabela_resumo,
)
from dashboard.visualizations import (
    render_dashboard_charts,
    render_frota_contrato_chart,
    render_resumo_chart,
    render_servicos_executados_chart,
)

ENTRADA_DADOS_MENU_ITEM = "Entrada de Dados"
ORACLE_DESTBOAD_MENU_ITEM = "Dados da Manutenção - Oracle"
ANALISE_FALHAS_MENU_ITEM = "Análise de Falhas"
CSV_SERVICOS_EXTERNO_RELATIVO = Path("Importacoes") / "bsa_serv_exce.csv"
CSV_BASE_HISTORICA_RELATIVO = Path("Importacoes") / "Basehistorica.csv"
IMPORTADOR_BASE_HISTORICA_RELATIVO = (
    Path("Importacoes") / "importacao_historico_manutencao.py"
)


def _candidatos_arquivo_importacao(caminho_relativo: Path) -> list[Path]:
    app_path = Path(__file__).resolve()
    candidatos = [
        caminho_relativo,
        Path.cwd() / caminho_relativo,
        app_path.parents[1] / caminho_relativo,
        app_path.parent / caminho_relativo,
    ]
    return list(dict.fromkeys(candidatos))


def _candidatos_csv_servicos_externo_padrao() -> list[Path]:
    return _candidatos_arquivo_importacao(CSV_SERVICOS_EXTERNO_RELATIVO)


def _resolver_csv_servicos_externo_padrao() -> Path | None:
    for caminho in _candidatos_csv_servicos_externo_padrao():
        if caminho.exists():
            return caminho
    return None


def _candidatos_csv_base_historica_padrao() -> list[Path]:
    return _candidatos_arquivo_importacao(CSV_BASE_HISTORICA_RELATIVO)


def _resolver_csv_base_historica_padrao() -> Path | None:
    for caminho in _candidatos_csv_base_historica_padrao():
        if caminho.exists():
            return caminho
    return None


def _carregar_importador_base_historica() -> Callable[..., int]:
    for caminho in _candidatos_arquivo_importacao(IMPORTADOR_BASE_HISTORICA_RELATIVO):
        if caminho.exists():
            spec = importlib.util.spec_from_file_location(
                "importacao_historico_manutencao",
                caminho,
            )
            if spec is None or spec.loader is None:
                break

            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            return modulo.carregar_csv

    caminhos_tentados = "\n".join(
        str(caminho)
        for caminho in _candidatos_arquivo_importacao(
            IMPORTADOR_BASE_HISTORICA_RELATIVO
        )
    )
    raise FileNotFoundError(
        "Importador da Basehistorica nao encontrado. "
        f"Caminhos verificados:\n{caminhos_tentados}"
    )


def _parametros_modo_carga_servicos(modo_carga: str) -> tuple[bool, bool]:
    substituir_tabela = modo_carga.startswith("Substituir toda")
    append = modo_carga.startswith("Apenas adicionar")
    substituir_periodos_csv = not substituir_tabela and not append
    return substituir_tabela, substituir_periodos_csv


def render_consulta_destboad_oracle() -> None:
    st.subheader("Dados da Manutenção - Oracle")

    if not usuario_eh_admin():
        st.warning(
            "A consulta Oracle esta disponivel apenas para usuarios administradores."
        )
        return

    st.info(
        "Consultar Oracle salva os CSVs localmente. Para atualizar o dashboard, "
        "mantenha a carga no banco habilitada."
    )

    carregar_apos_consulta = st.checkbox("Carregar no banco apos consultar", value=True)
    modo_carga = st.radio(
        "Modo de carga no banco",
        [
            "Substituir periodos do CSV",
            "Apenas adicionar (append)",
            "Substituir toda a tabela servicos_executados",
        ],
        help=(
            "Use append apenas para dados novos. Para recarregar um periodo sem "
            "duplicar, use a substituicao de periodos."
        ),
    )
    substituir_tabela, substituir_periodos_csv = _parametros_modo_carga_servicos(
        modo_carga
    )
    if modo_carga.startswith("Apenas adicionar"):
        st.warning(
            "Append nao remove registros existentes. Use apenas quando tiver certeza "
            "de que os dados ainda nao foram carregados."
        )

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
                    substituir_periodos_csv=substituir_periodos_csv,
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
                substituir_periodos_csv=substituir_periodos_csv,
            )
            carregar_base_outra_tabela.clear()
            st.success(f"Carga concluida. Linhas carregadas: {total_carregado}")
        except Exception as erro:
            st.error("Erro ao carregar CSV local.")
            st.exception(erro)

    st.divider()
    st.subheader("Importar CSV externo")
    st.caption(
        "Use para carregar dados complementares que vieram de fora, como "
        "`Importacoes/bsa_serv_exce.csv`."
    )
    csv_externo_padrao = _resolver_csv_servicos_externo_padrao()
    csv_externo = st.file_uploader(
        "Enviar CSV externo de serviços executados",
        type=["csv"],
        help=(
            "Se nenhum arquivo for enviado, o botão usa o arquivo padrão "
            f"{CSV_SERVICOS_EXTERNO_RELATIVO}."
        ),
    )
    if csv_externo_padrao is None:
        st.caption(f"Arquivo padrão: {CSV_SERVICOS_EXTERNO_RELATIVO}")
    else:
        st.caption(f"Arquivo padrão encontrado: {csv_externo_padrao}")

    if st.button("Carregar CSV externo no banco"):
        try:
            from Oracle.servicos_executados_pipeline import (
                carregar_servicos_executados_csv,
            )

            if csv_externo is None:
                if csv_externo_padrao is None:
                    caminhos_tentados = "\n".join(
                        str(caminho)
                        for caminho in _candidatos_csv_servicos_externo_padrao()
                    )
                    st.warning("Arquivo padrão não encontrado. Caminhos verificados:")
                    st.code(caminhos_tentados)
                    return

                caminho_csv_externo = csv_externo_padrao
                total_carregado = carregar_servicos_executados_csv(
                    caminho_csv_externo,
                    substituir_tabela=substituir_tabela,
                    substituir_periodos_csv=substituir_periodos_csv,
                )
            else:
                with tempfile.TemporaryDirectory() as pasta_temp:
                    caminho_csv_externo = Path(pasta_temp) / Path(csv_externo.name).name
                    caminho_csv_externo.write_bytes(csv_externo.getvalue())
                    total_carregado = carregar_servicos_executados_csv(
                        caminho_csv_externo,
                        substituir_tabela=substituir_tabela,
                        substituir_periodos_csv=substituir_periodos_csv,
                    )

            carregar_base_outra_tabela.clear()
            st.success(f"CSV externo carregado. Linhas carregadas: {total_carregado}")
        except Exception as erro:
            st.error("Erro ao carregar CSV externo.")
            st.exception(erro)

    st.divider()
    st.subheader("Teste: Importar Basehistorica.csv")
    st.caption(
        "Use parama base histórica de teste em `base_historica_manutencao`."
    )
    modo_carga_base = st.radio(
        "Modo de carga da Basehistorica",
        [
            "Substituir periodos da Basehistorica",
            "Apenas adicionar Basehistorica (append)",
            "Substituir toda a tabela base_historica_manutencao",
        ],
        help=(
            "Para testes recorrentes, prefira substituir períodos. Append pode "
            "duplicar se o mesmo arquivo for carregado novamente."
        ),
    )
    substituir_tabela_base = modo_carga_base.startswith("Substituir toda")
    append_base = modo_carga_base.startswith("Apenas adicionar")
    substituir_periodos_base = not substituir_tabela_base and not append_base
    if append_base:
        st.warning(
            "Append nao remove registros existentes. Use apenas para dados realmente "
            "novos."
        )

    csv_base_historica_padrao = _resolver_csv_base_historica_padrao()
    csv_base_historica = st.file_uploader(
        "Enviar Basehistorica.csv",
        type=["csv"],
        key="upload_basehistorica_teste",
        help=(
            "Se nenhum arquivo for enviado, o botão usa o arquivo padrão "
            f"{CSV_BASE_HISTORICA_RELATIVO}."
        ),
    )
    if csv_base_historica_padrao is None:
        st.caption(f"Arquivo padrão: {CSV_BASE_HISTORICA_RELATIVO}")
    else:
        st.caption(f"Arquivo padrão encontrado: {csv_base_historica_padrao}")

    if st.button("Carregar Basehistorica.csv de teste no banco"):
        try:
            carregar_csv = _carregar_importador_base_historica()

            if csv_base_historica is None:
                if csv_base_historica_padrao is None:
                    caminhos_tentados = "\n".join(
                        str(caminho)
                        for caminho in _candidatos_csv_base_historica_padrao()
                    )
                    st.warning(
                        "Basehistorica.csv padrão não encontrada. Caminhos verificados:"
                    )
                    st.code(caminhos_tentados)
                    return

                caminho_base_historica = csv_base_historica_padrao
                total_carregado = carregar_csv(
                    caminho_base_historica,
                    substituir_tabela=substituir_tabela_base,
                    substituir_periodos_csv=substituir_periodos_base,
                    chunksize=5000,
                )
            else:
                with tempfile.TemporaryDirectory() as pasta_temp:
                    caminho_base_historica = (
                        Path(pasta_temp) / Path(csv_base_historica.name).name
                    )
                    caminho_base_historica.write_bytes(csv_base_historica.getvalue())
                    total_carregado = carregar_csv(
                        caminho_base_historica,
                        substituir_tabela=substituir_tabela_base,
                        substituir_periodos_csv=substituir_periodos_base,
                        chunksize=5000,
                    )

            carregar_base.clear()
            st.success(
                "Basehistorica.csv carregado para teste. "
                f"Linhas carregadas: {total_carregado}"
            )
        except Exception as erro:
            st.error("Erro ao carregar Basehistorica.csv.")
            st.exception(erro)


def montar_servicos_executados_dashboard(filtros: dict[str, object]):
    try:
        df_servicos = carregar_base_outra_tabela()
    except Exception as erro:
        st.warning(f"Erro ao carregar servicos_executados: {erro}")
        return None

    if df_servicos.empty:
        return None

    servicos_filtrados = aplicar_filtros(df_servicos, filtros)
    if servicos_filtrados.empty and filtros.get("periodo"):
        filtros_sem_periodo = dict(filtros)
        filtros_sem_periodo["periodo"] = None
        servicos_filtrados = aplicar_filtros(df_servicos, filtros_sem_periodo)

    return montar_servicos_executados_por_tipo(servicos_filtrados)


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

    menu = render_sidebar(df_base)
    render_titulo_principal(APP_TITLE)

    if menu == ENTRADA_DADOS_MENU_ITEM:
        render_entrada_dados(df_base)
        return

    if menu == ORACLE_DESTBOAD_MENU_ITEM:
        render_consulta_destboad_oracle()
        return

    if menu == ANALISE_FALHAS_MENU_ITEM:
        render_analise_falhas()
        return

    if menu == "Dashboard":
        filtros_area = st.container()
        with filtros_area:
            filtros = render_filtros(df_base, menu)
        kpis_area = st.container()
    elif menu == "Serviços Executados - Teste":
        total_servicos_area = st.container()
        filtros_area = st.container()
        with filtros_area:
            filtros = render_filtros(df_base, menu)
    else:
        filtros = render_filtros(df_base, menu)

    df_filtrado = aplicar_filtros(df_base, filtros)
    filtros_sem_periodo = dict(filtros)
    filtros_sem_periodo["periodo"] = None
    df_filtrado_sem_periodo = aplicar_filtros(df_base, filtros_sem_periodo)

    resumo = montar_resumo_equipamento(df_filtrado)
    equipamentos_contrato = montar_equipamentos_por_contrato(df_filtrado)
    evolucao_mensal_12_meses = montar_evolucao_mensal(
        df_filtrado_sem_periodo,
        limite_meses=12,
    )
    evolucao_tabela = montar_tabela_evolucao(df_filtrado)
    frota_contrato = montar_frota_contrato_por_mes(df_filtrado)
    manutencao_contrato = montar_manutencao_por_contrato(df_filtrado)

    if menu == "Dashboard":
        kpis = calcular_kpis(resumo, evolucao_mensal_12_meses)
        servicos_resumo_dashboard = montar_servicos_executados_dashboard(filtros)
        with kpis_area:
            render_kpis(kpis)
        st.write("")
        render_dashboard_charts(
            resumo,
            evolucao_mensal_12_meses,
            manutencao_contrato,
            equipamentos_contrato,
            servicos_resumo_dashboard,
        )
    elif menu == "Resumo":
        render_resumo_chart(resumo)
        render_tabela_resumo(resumo)
    elif menu in {"Contando Frota - Teste", "Contando Frota - Teste."}:
        render_frota_contrato_chart(frota_contrato)
    elif menu =="Serviços Executados - Teste":
        df_servicos = carregar_base_outra_tabela()
        if df_servicos.empty:
            st.warning("Sem dados na tabela servico_executado.")
            st.stop()

        servicos_filtrados = aplicar_filtros(df_servicos, filtros)
        servicos_resumo = montar_servicos_executados_por_tipo(servicos_filtrados)
        total_servicos = int(servicos_filtrados["qtd_servico"].sum())
        with total_servicos_area:
            render_total_servicos_executados(total_servicos)
        st.write("")
        render_servicos_executados_chart(servicos_resumo)
        render_servicos_executados(servicos_filtrados)
    else:
        render_tabela_evolucao(evolucao_tabela)
        render_tabela_detalhe(df_filtrado)


if __name__ == "__main__":
    main()

import pandas as pd
import streamlit as st

from dashboard.styles import tema_claro_ativo


def _estilizar_dataframe(df: pd.DataFrame):
    if df.empty or not tema_claro_ativo():
        return df

    return (
        df.style.set_properties(
            **{
                "background-color": "#ffffff",
                "color": "#1f2937",
                "border-color": "rgba(37, 56, 78, 0.18)",
            }
        )
        .set_table_styles(
            [
                {
                    "selector": "thead th",
                    "props": [
                        ("background-color", "#eef3f8"),
                        ("color", "#1f2937"),
                        ("border-color", "rgba(37, 56, 78, 0.18)"),
                    ],
                },
                {
                    "selector": "tbody tr:nth-child(even) td",
                    "props": [("background-color", "#f8fbff")],
                },
            ],
            overwrite=False,
        )
    )


def render_tabela_resumo(df_resumo: pd.DataFrame) -> None:
    with st.container(border=True):
        st.subheader("Resumo por Equipamento")
        df_view = df_resumo.sort_values("percentual_recalculado", ascending=False)
        st.dataframe(
            _estilizar_dataframe(df_view),
            use_container_width=True,
            hide_index=True,
        )


def render_tabela_evolucao(df_evolucao: pd.DataFrame) -> None:
    with st.container(border=True):
        st.subheader("Evolucao Mensal")
        df_view = df_evolucao.sort_values(["mes", "equipamento"])
        st.dataframe(
            _estilizar_dataframe(df_view),
            use_container_width=True,
            hide_index=True,
        )


def render_tabela_detalhe(df_filtrado: pd.DataFrame) -> None:
    with st.container(border=True):
        st.subheader("Base Filtrada")
        df_view = df_filtrado.copy()
        for coluna in ["data_ref", "data_competencia"]:
            if coluna in df_view.columns:
                df_view[coluna] = pd.to_datetime(
                    df_view[coluna],
                    errors="coerce",
                ).dt.strftime("%Y-%m-%d")
        df_view = df_view.sort_values("data_ref", ascending=False)
        st.dataframe(
            _estilizar_dataframe(df_view),
            use_container_width=True,
            hide_index=True,
        )


def render_servicos_executados(filtrados: pd.DataFrame) -> None:
    with st.container(border=True):
        st.subheader("Serviços Executados - Teste")

        df_view = filtrados.copy()
        for coluna in ["data_ref", "data_competencia"]:
            if coluna in df_view.columns:
                df_view[coluna] = pd.to_datetime(
                    df_view[coluna],
                    errors="coerce",
                ).dt.strftime("%Y-%m-%d")

        df_view = df_view.sort_values("data_ref", ascending=False)
        st.dataframe(
            _estilizar_dataframe(df_view),
            use_container_width=True,
            hide_index=True,
        )


def render_os_fora_criterio(df_os: pd.DataFrame | None) -> None:
    total = 0 if df_os is None else len(df_os)
    with st.expander(
        f"Detalhamento das OS sem item-base ({total})",
        expanded=False,
    ):
        st.caption(
            "Uma linha por OS sem ABA_ITEM = 1. Os valores respeitam o período "
            "de abertura e os demais filtros selecionados na tela."
        )

        if df_os is None:
            st.warning("Não foi possível carregar o diagnóstico de itemização.")
            return
        if df_os.empty:
            st.info("Nenhuma OS fora do critério para os filtros selecionados.")
            return

        colunas = {
            "motivo_exclusao": "Situação",
            "numero_os": "OS",
            "status": "Status",
            "data_ref": "Abertura",
            "data_fechamento": "Fechamento",
            "cliente": "Cliente/Contrato",
            "praca": "Praça",
            "coordenacao": "Coordenação",
            "equipamento": "Equipamento",
            "itens_encontrados": "Itens encontrados",
            "servicos_executados": "Códigos de serviço",
            "descricoes_servicos": "Serviços executados",
        }
        df_view = df_os.reindex(columns=colunas).rename(columns=colunas)
        df_view["_abertura_ordem"] = pd.to_datetime(
            df_view["Abertura"],
            errors="coerce",
        )
        df_view["Abertura"] = df_view["_abertura_ordem"].dt.strftime("%d/%m/%Y")
        df_view["Fechamento"] = pd.to_datetime(
            df_view["Fechamento"],
            errors="coerce",
        ).dt.strftime("%d/%m/%Y")

        for coluna in [
            "Status",
            "Abertura",
            "Fechamento",
            "Cliente/Contrato",
            "Praça",
            "Coordenação",
            "Equipamento",
            "Itens encontrados",
            "Códigos de serviço",
            "Serviços executados",
        ]:
            df_view[coluna] = df_view[coluna].fillna("").replace("", "—")

        prioridade = {
            "Pendência de itemização": 0,
            "Orçamento sem item-base": 1,
        }
        df_view["_prioridade"] = df_view["Situação"].map(prioridade).fillna(2)
        df_view = (
            df_view.sort_values(
                ["_prioridade", "_abertura_ordem", "OS"],
                ascending=[True, False, True],
            )
            .drop(columns=["_prioridade", "_abertura_ordem"])
            .reset_index(drop=True)
        )
        st.dataframe(
            _estilizar_dataframe(df_view),
            use_container_width=True,
            hide_index=True,
        )


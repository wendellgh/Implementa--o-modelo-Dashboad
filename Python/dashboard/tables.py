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


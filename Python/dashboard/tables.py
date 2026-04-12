import pandas as pd
import streamlit as st


def render_tabela_resumo(df_resumo: pd.DataFrame) -> None:
    with st.container(border=True):
        st.subheader("Resumo por Equipamento")
        st.dataframe(
            df_resumo.sort_values("percentual_recalculado", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


def render_tabela_evolucao(df_evolucao: pd.DataFrame) -> None:
    with st.container(border=True):
        st.subheader("Evolucao Mensal")
        st.dataframe(
            df_evolucao.sort_values(["mes", "equipamento"]),
            use_container_width=True,
            hide_index=True,
        )


def render_tabela_detalhe(df_filtrado: pd.DataFrame) -> None:
    with st.container(border=True):
        st.subheader("Base Filtrada")
        df_view = df_filtrado.copy()
        if "data_ref" in df_view.columns:
            df_view["data_ref"] = pd.to_datetime(df_view["data_ref"], errors="coerce").dt.strftime("%Y-%m-%d")
        st.dataframe(
            df_view.sort_values("data_ref", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

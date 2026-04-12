import pandas as pd
import streamlit as st


def render_tabela_resumo(df_resumo_filtrado: pd.DataFrame) -> None:
    st.subheader("Resumo por Equipamento")
    st.dataframe(df_resumo_filtrado, use_container_width=True)


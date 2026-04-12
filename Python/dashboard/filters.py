import pandas as pd
import streamlit as st


def aplicar_filtro_equipamento(
    df_resumo: pd.DataFrame,
    df_evolucao: pd.DataFrame,
) -> tuple[str, pd.DataFrame, pd.DataFrame]:
    equipamentos = ["Todos"] + sorted(df_resumo["equipamento"].dropna().unique().tolist())
    equipamento_sel = st.selectbox("Filtrar equipamento", equipamentos)

    if equipamento_sel == "Todos":
        return equipamento_sel, df_resumo.copy(), df_evolucao.copy()

    df_resumo_filtrado = df_resumo[df_resumo["equipamento"] == equipamento_sel].copy()
    df_evolucao_filtrado = df_evolucao[df_evolucao["equipamento"] == equipamento_sel].copy()

    return equipamento_sel, df_resumo_filtrado, df_evolucao_filtrado


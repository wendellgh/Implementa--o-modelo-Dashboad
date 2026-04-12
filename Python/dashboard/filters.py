from datetime import date

import pandas as pd
import streamlit as st

from dashboard.config import MENU_ITEMS


def render_sidebar(df_base: pd.DataFrame) -> dict[str, object]:
    data_valida = df_base["data_ref"].dropna()
    if data_valida.empty:
        data_min = date.today()
        data_max = date.today()
    else:
        data_min = data_valida.min().date()
        data_max = data_valida.max().date()

    with st.sidebar:
        st.markdown("### Navegacao")
        menu = st.radio("Pagina", MENU_ITEMS, index=0)

        st.markdown("### Filtros")
        periodo = st.date_input(
            "Periodo",
            value=(data_min, data_max),
            min_value=data_min,
            max_value=data_max,
        )

        contratos = sorted([x for x in df_base["contrato"].dropna().unique().tolist() if x])
        filtro_contrato = st.multiselect("Contrato", contratos)

        equipamentos = sorted([x for x in df_base["equipamento"].dropna().unique().tolist() if x])
        filtro_equipamento = st.multiselect("Equipamento", equipamentos)

    return {
        "menu": menu,
        "periodo": periodo,
        "filtro_contrato": filtro_contrato,
        "filtro_equipamento": filtro_equipamento,
    }


def aplicar_filtros(df_base: pd.DataFrame, filtros: dict[str, object]) -> pd.DataFrame:
    df_filtrado = df_base.copy()

    periodo = filtros.get("periodo")
    if isinstance(periodo, tuple) and len(periodo) == 2:
        inicio = pd.to_datetime(periodo[0])
        fim = pd.to_datetime(periodo[1])
        df_filtrado = df_filtrado[
            (df_filtrado["data_ref"] >= inicio) & (df_filtrado["data_ref"] <= fim)
        ]
    elif isinstance(periodo, date):
        dia = pd.to_datetime(periodo)
        df_filtrado = df_filtrado[df_filtrado["data_ref"] == dia]

    filtro_contrato = filtros.get("filtro_contrato", [])
    if filtro_contrato:
        df_filtrado = df_filtrado[df_filtrado["contrato"].isin(filtro_contrato)]

    filtro_equipamento = filtros.get("filtro_equipamento", [])
    if filtro_equipamento:
        df_filtrado = df_filtrado[df_filtrado["equipamento"].isin(filtro_equipamento)]

    return df_filtrado

import pandas as pd
import streamlit as st


def calcular_kpis(df_resumo: pd.DataFrame) -> dict[str, float | int]:
    media_entrada_manut = round(float(df_resumo["media_percentual"].mean()), 2)
    total_qtd = int(df_resumo["total_qtd"].sum())
    total_frota = int(df_resumo["total_frota"].sum())
    percentual_geral = round((total_qtd / total_frota) * 100, 2) if total_frota else 0.0

    return {
        "media_entrada_manut": media_entrada_manut,
        "total_qtd": total_qtd,
        "total_frota": total_frota,
        "percentual_geral": percentual_geral,
    }


def render_kpis(kpis: dict[str, float | int]) -> None:
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Media Entrada em Manut.", f"{float(kpis['media_entrada_manut']):.2f}%")
    col2.metric("Total QTD", f"{int(kpis['total_qtd']):,}".replace(",", "."))
    col3.metric("Total Frota", f"{int(kpis['total_frota']):,}".replace(",", "."))
    col4.metric("% QTD x Frota", f"{float(kpis['percentual_geral']):.2f}%")


import pandas as pd
import streamlit as st


def calcular_kpis(df_resumo: pd.DataFrame) -> dict[str, float | int | str]:
    if df_resumo.empty:
        return {
            "media_entrada_manut": 0.0,
            "total_qtd": 0,
            "total_frota": 0,
            "percentual_geral": 0.0,
            "mtbf_horas": "N/D",
        }

    media_entrada_manut = round(float(df_resumo["media_percentual"].mean()), 2)
    total_qtd = int(df_resumo["total_qtd"].sum())
    total_frota = int(df_resumo["total_frota"].sum())
    percentual_geral = round((total_qtd / total_frota) * 100, 2) if total_frota else 0.0

    return {
        "media_entrada_manut": media_entrada_manut,
        "total_qtd": total_qtd,
        "total_frota": total_frota,
        "percentual_geral": percentual_geral,
        "mtbf_horas": "N/D",
    }


def _format_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _render_card(titulo: str, valor: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{titulo}</div>
            <div class="kpi-value">{valor}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(kpis: dict[str, float | int | str]) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        _render_card("Media Entrada em Manut.", f"{float(kpis['media_entrada_manut']):.2f}%")
    with c2:
        _render_card("MTBF (Horas)", str(kpis["mtbf_horas"]))
    with c3:
        _render_card("Total QTD", _format_int(int(kpis["total_qtd"])))
    with c4:
        _render_card("Total Frota", _format_int(int(kpis["total_frota"])))
    with c5:
        _render_card("% QTD x Frota", f"{float(kpis['percentual_geral']):.2f}%")

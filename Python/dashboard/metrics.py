import pandas as pd
import streamlit as st

MESES_MEDIA_MENSAL_ANUAL = 12


def _calcular_entrada_media_mensal_anual(
    df_evolucao_mensal: pd.DataFrame | None,
) -> int:
    if (
        df_evolucao_mensal is None
        or df_evolucao_mensal.empty
        or "total_qtd" not in df_evolucao_mensal.columns
    ):
        return 0

    total_12_meses = pd.to_numeric(
        df_evolucao_mensal["total_qtd"],
        errors="coerce",
    ).fillna(0).sum()

    return round(float(total_12_meses) / MESES_MEDIA_MENSAL_ANUAL)


def calcular_kpis(
    df_resumo: pd.DataFrame,
    df_evolucao_mensal: pd.DataFrame | None = None,
) -> dict[str, float | int | str]:
    entrada_media_mensal = _calcular_entrada_media_mensal_anual(df_evolucao_mensal)

    if df_resumo.empty:
        return {
            "entrada_media_mensal": entrada_media_mensal,
            "total_qtd": 0,
            "total_frota": 0,
            "percentual_geral": 0.0,
            "mtbf_horas": "N/D",
        }

    total_qtd = int(df_resumo["total_qtd"].sum())
    total_frota = int(df_resumo["total_frota"].sum())
    percentual_geral = round((total_qtd / total_frota) * 100, 2) if total_frota else 0.0
    mtbf_horas = round(total_frota * 24 * 30 / total_qtd) if total_qtd else "N/D"

    return {
        "entrada_media_mensal": entrada_media_mensal,
        "total_qtd": total_qtd,
        "total_frota": total_frota,
        "percentual_geral": percentual_geral,
        "mtbf_horas": mtbf_horas,
    }


def _format_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _render_card(titulo: str, valor: str, icone: str = "⚙️") -> None:
    st.markdown(
        f"""
        <div class="kpi-card" data-icon="{icone}">
            <div class="kpi-title">{titulo}</div>
            <div class="kpi-value">{valor}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(kpis: dict[str, float | int | str]) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        _render_card(
            "Total de equipamentos alocados no período",
            _format_int(int(kpis["total_frota"])),
            "🚌",
        )
    with c2:
        _render_card(
            "Equipamentos com Entrada em Manutenção",
            _format_int(int(kpis["total_qtd"])),
            "⚙️",
        )
    with c3:
        _render_card(
            "Equips. em Manutenção x Frota %",
            f"{float(kpis['percentual_geral']):.2f}%",
            "📊",
        )
    with c4:
        _render_card(
            "Média de Manutenção Anual",
            _format_int(int(kpis["entrada_media_mensal"])),
            "📈",
        
        )
    with c5:
        _render_card(
            "MTBF (Horas)",
            _format_int(int(kpis["mtbf_horas"]))
            if isinstance(kpis["mtbf_horas"], (int, float))
            else str(kpis["mtbf_horas"]),
            "⏱️",
        )


def render_total_servicos_executados(total_servicos: int) -> None:
    coluna_total, _, _, _ = st.columns([1.3, 1, 1, 1])

    with coluna_total:
        _render_card("Total de Serviços Executados", _format_int(total_servicos))


def render_indicadores_servicos_executados(
    total_servicos: int,
    total_os_periodo: int | None,
) -> None:
    coluna_servicos, coluna_os_periodo, _, _ = st.columns([1.3, 1.3, 1, 1])

    with coluna_servicos:
        _render_card("Total de Serviços Executados", _format_int(total_servicos))

    with coluna_os_periodo:
        valor = "N/D" if total_os_periodo is None else _format_int(total_os_periodo)
        _render_card("Total de OS no período", valor, "📋")

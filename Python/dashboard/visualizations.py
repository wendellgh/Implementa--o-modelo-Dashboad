import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.styles import tema_claro_ativo

PALETA = {
    "primaria": "#007AFF",
    "secundaria": "#34C759",
    "terciaria": "#546E7A",
    "acento": "#FF3B30",
    "destaque_tecnico": "#00D4FF",
    "texto_eixos": "#E0E0E0",
}

ESCALA_ALERTA = [PALETA["secundaria"], PALETA["primaria"], PALETA["acento"]]
COR_PERCENTUAL_BAIXO = "#2F80ED"
COR_PERCENTUAL_MEDIO = "#F2C94C"
COR_PERCENTUAL_ALTO = PALETA["acento"]
ESCALA_OPERACIONAL = [
    PALETA["terciaria"],
    PALETA["destaque_tecnico"],
    PALETA["primaria"],
]
ESCALA_RANKING = [
    PALETA["terciaria"],
    PALETA["destaque_tecnico"],
    PALETA["primaria"],
]
CORES_CATEGORICAS = [
    PALETA["primaria"],
    PALETA["secundaria"],
    PALETA["terciaria"],
    PALETA["destaque_tecnico"],
]


def _tema_claro() -> bool:
    return tema_claro_ativo()


def _cor_texto_tema() -> str:
    return "#1f2937" if _tema_claro() else PALETA["texto_eixos"]


def _cor_grade_tema() -> str:
    return "rgba(31,41,55,0.16)" if _tema_claro() else "rgba(224,224,224,0.18)"


def _estilizar_figura(fig):
    text_color = _cor_texto_tema()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": text_color},
        title={"font": {"color": text_color}},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        legend={
            "font": {"color": text_color},
            "orientation": "h",
            "yanchor": "top",
            "y": -0.18,
            "xanchor": "center",
            "x": 0.5,
        },
    )
    axis_font = {"color": text_color}
    fig.update_xaxes(
        showgrid=False,
        tickfont=axis_font,
        title_font=axis_font,
    )
    fig.update_yaxes(
        gridcolor=_cor_grade_tema(),
        tickfont=axis_font,
        title_font=axis_font,
    )
    return fig


def _mostrar_rotulos_barras(fig, template: str = "%{text}") -> None:
    fig.update_traces(
        texttemplate=template,
        textposition="inside",
        insidetextanchor="middle",
        constraintext="none",
        cliponaxis=False,
        textfont={"color": _cor_texto_tema(), "size": 12},
        selector={"type": "bar"},
    )
    fig.update_layout(uniformtext={"minsize": 10, "mode": "show"})


def _formatar_mes_curto(data_mes: pd.Timestamp) -> str:
    meses_pt = {
        1: "Jan",
        2: "Fev",
        3: "Mar",
        4: "Abr",
        5: "Mai",
        6: "Jun",
        7: "Jul",
        8: "Ago",
        9: "Set",
        10: "Out",
        11: "Nov",
        12: "Dez",
    }
    data_mes = pd.Timestamp(data_mes)
    return f"{meses_pt[data_mes.month]}/{data_mes:%y}"


def _cor_percentual_frota(valor: float) -> str:
    if valor >= 15:
        return COR_PERCENTUAL_ALTO
    if valor >= 5:
        return COR_PERCENTUAL_MEDIO
    return COR_PERCENTUAL_BAIXO


def _calcular_tendencia_linear(valores: pd.Series) -> pd.Series:
    serie = pd.to_numeric(valores, errors="coerce")
    x = pd.Series(range(len(serie)), index=serie.index, dtype="float")
    validos = serie.notna()

    if validos.sum() < 2:
        return pd.Series([pd.NA] * len(serie), index=serie.index)

    x_validos = x[validos]
    y_validos = serie[validos].astype(float)
    variancia_x = ((x_validos - x_validos.mean()) ** 2).sum()

    if variancia_x == 0:
        return pd.Series([y_validos.iloc[0]] * len(serie), index=serie.index)

    inclinacao = (
        (x_validos - x_validos.mean()) * (y_validos - y_validos.mean())
    ).sum() / variancia_x
    intercepto = y_validos.mean() - inclinacao * x_validos.mean()

    return (intercepto + inclinacao * x).clip(lower=0).round(2)


def render_dashboard_charts(
    df_resumo: pd.DataFrame,
    df_evolucao_mensal: pd.DataFrame,
    df_manutencao_contrato: pd.DataFrame,
    df_equipamentos_contrato: pd.DataFrame,
    df_servicos_resumo: pd.DataFrame | None = None,
) -> None:
    if df_evolucao_mensal.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    col_top_1, col_top_2 = st.columns(2)

    with col_top_1:
        with st.container(border=True):
            ranking = df_resumo.sort_values("total_qtd", ascending=True).tail(8)
            fig_ranking = px.bar(
                ranking,
                x="total_qtd",
                y="equipamento",
                orientation="h",
                title="EQUIPAMENTOS COM MAIOR NÚMERO DE MANUTENÇÕES",
                text="total_qtd",
                color="total_qtd",
                color_continuous_scale=ESCALA_RANKING,
                labels={
                    "total_qtd": "Quantidade em manutenção",
                    "equipamento": "Equipamento",
                },
            )
            _mostrar_rotulos_barras(fig_ranking, "%{text:.0f}")
            fig_ranking.update_coloraxes(showscale=False)
            st.plotly_chart(_estilizar_figura(fig_ranking), use_container_width=True)

    with col_top_2:
        with st.container(border=True):
            if df_servicos_resumo is None:
                st.info("Sem dados de serviços executados por tipo.")
            else:
                render_servicos_executados_chart(
                    df_servicos_resumo,
                    usar_container=False,
                )

    col_bottom_1, col_bottom_2 = st.columns(2)

    with col_bottom_1:
        with st.container(border=True):
            percentual_frota = df_evolucao_mensal.sort_values("mes").copy()
            percentual_frota["mes_label"] = percentual_frota["mes"].apply(
                _formatar_mes_curto
            )
            percentual_frota["cor_barra"] = percentual_frota[
                "percentual_qtd_x_frota"
            ].apply(
                _cor_percentual_frota,
            )
            ordem_meses = percentual_frota["mes_label"].tolist()
            fig_percentual = px.bar(
                percentual_frota,
                x="mes_label",
                y="percentual_qtd_x_frota",
                title="% TOTAL DA FROTA EM MANUTENÇÃO",
                text="percentual_qtd_x_frota",
                category_orders={"mes_label": ordem_meses},
                labels={
                    "mes_label": "Mês",
                    "percentual_qtd_x_frota": "% Equipamentos",
                },
                hover_data={
                    "mes_label": False,
                    "cor_barra": False,
                    "mes": "|%m/%Y",
                    "percentual_qtd_x_frota": ":.2f",
                },
            )
            fig_percentual.update_traces(marker_color=percentual_frota["cor_barra"])
            percentual_frota["tendencia_percentual"] = _calcular_tendencia_linear(
                percentual_frota["percentual_qtd_x_frota"]
            )
            if percentual_frota["tendencia_percentual"].notna().any():
                fig_percentual.add_scatter(
                    x=percentual_frota["mes_label"],
                    y=percentual_frota["tendencia_percentual"],
                    mode="lines+markers",
                    name="Tendencia",
                    line={"color": PALETA["destaque_tecnico"], "width": 3},
                    marker={
                        "color": PALETA["destaque_tecnico"],
                        "size": 7,
                        "symbol": "circle",
                    },
                    hovertemplate=(
                        "Mes=%{x}<br>Tendencia=%{y:.2f}%<extra></extra>"
                    ),
                )
            fig_percentual.update_xaxes(
                type="category",
                categoryorder="array",
                categoryarray=ordem_meses,
            )
            _mostrar_rotulos_barras(fig_percentual, "%{text:.2f}%")
            st.plotly_chart(_estilizar_figura(fig_percentual), use_container_width=True)

    with col_bottom_2:
        with st.container(border=True):
            if df_manutencao_contrato.empty:
                st.info(
                    "Sem dados de manutenção por contrato para os filtros selecionados."
                )
            else:
                manutencao_contrato = df_manutencao_contrato.sort_values(
                    "quantidade_manutencao",
                    ascending=False,
                )
                ordem_contratos = manutencao_contrato["contrato"].tolist()
                fig_manutencao_contrato = px.bar(
                    manutencao_contrato,
                    x="contrato",
                    y="quantidade_manutencao",
                    color="contrato",
                    color_discrete_sequence=CORES_CATEGORICAS,
                    category_orders={"contrato": ordem_contratos},
                    title="EQUIPAMENTOS EM MANUTENÇÃO POR CONTRATO",
                    text="quantidade_manutencao",
                    labels={
                        "contrato": "Contrato",
                        "quantidade_manutencao": "Quantidade em manutenção",
                    },
                )
                fig_manutencao_contrato.update_xaxes(
                    categoryorder="array",
                    categoryarray=ordem_contratos,
                )
                _mostrar_rotulos_barras(fig_manutencao_contrato, "%{text:.0f}")
                st.plotly_chart(
                    _estilizar_figura(fig_manutencao_contrato),
                    use_container_width=True,
                )

    with st.container(border=True):
        if df_equipamentos_contrato.empty:
            st.info("Sem dados de contrato para os filtros selecionados.")
        else:
            fig_contrato = px.bar(
                df_equipamentos_contrato,
                x="contrato",
                y="quantidade_equipamentos",
                title="EQUIPAMENTOS ALOCADOS POR CONTRATO",
                text="quantidade_equipamentos",
                color="quantidade_equipamentos",
                hover_data={"mes": "|%Y-%m", "quantidade_equipamentos": ":.0f"},
                color_continuous_scale=ESCALA_OPERACIONAL,
                labels={
                    "contrato": "Contrato",
                    "quantidade_equipamentos": "Equipamentos por Contrato",
                },
            )
            _mostrar_rotulos_barras(fig_contrato, "%{text:.0f}")
            fig_contrato.update_coloraxes(showscale=False)
            st.plotly_chart(_estilizar_figura(fig_contrato), use_container_width=True)


def render_resumo_chart(df_resumo: pd.DataFrame) -> None:
    if df_resumo.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    with st.container(border=True):
        fig = px.bar(
            df_resumo.sort_values("percentual_recalculado", ascending=False),
            x="equipamento",
            y="percentual_recalculado",
            title="% QTD x Frota por Equipamento wewedasdasd ",
            text="percentual_recalculado",
            color="percentual_recalculado",
            color_continuous_scale=ESCALA_ALERTA,
        )
        _mostrar_rotulos_barras(fig, "%{text:.2f}%")
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(_estilizar_figura(fig), use_container_width=True)


def render_frota_contrato_chart(df_frota_contrato: pd.DataFrame) -> None:
    if df_frota_contrato.empty:
        st.info("Sem dados de frota CCIT por contrato para os filtros selecionados.")
        return

    mes_label = str(df_frota_contrato["mes_label"].iloc[0]).upper()

    with st.container(border=True):
        fig = px.bar(
            df_frota_contrato,
            x="contrato",
            y="quantidade_frota",
            color="quantidade_frota",
            title=f"FROTA CCIT POR CONTRATO - {mes_label}",
            text="quantidade_frota",
            color_continuous_scale=ESCALA_OPERACIONAL,
            labels={
                "contrato": "Contrato",
                "quantidade_frota": "Frota",
                "mes_label": "Data",
            },
            hover_data={
                "mes": "|%m/%Y",
                "mes_label": False,
                "quantidade_frota": ":.0f",
            },
        )
        fig.update_xaxes(
            categoryorder="array",
            categoryarray=df_frota_contrato["contrato"].tolist(),
        )
        _mostrar_rotulos_barras(fig, "%{text:.0f}")
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(_estilizar_figura(fig), use_container_width=True)


def render_servicos_executados_chart(
    df_servicos_resumo: pd.DataFrame,
    usar_container: bool = True,
) -> None:
    if df_servicos_resumo.empty:
        st.info("Sem serviços executados para os filtros selecionados.")
        return

    ranking = df_servicos_resumo.sort_values(
        "quantidade_servicos",
        ascending=True,
    ).tail(5)
    fig = px.bar(
        ranking,
        x="quantidade_servicos",
        y="servico_executado",
        orientation="h",
        title="SERVIÇOS EXECUTADOS POR TIPO",
        text="quantidade_servicos",
        color="quantidade_servicos",
        color_continuous_scale=ESCALA_RANKING,
        labels={
            "servico_executado": "Serviços Executados",
            "quantidade_servicos": "Quantidade",
        },
    )
    _mostrar_rotulos_barras(fig, "%{text:.0f}")
    fig.update_coloraxes(showscale=False)

    if usar_container:
        with st.container(border=True):
            st.plotly_chart(_estilizar_figura(fig), use_container_width=True)
    else:
        st.plotly_chart(_estilizar_figura(fig), use_container_width=True)

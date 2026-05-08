import pandas as pd
import plotly.express as px
import streamlit as st

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


def _cor_texto_tema() -> str:
    return PALETA["texto_eixos"]


def _estilizar_figura(fig):
    text_color = _cor_texto_tema()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": text_color},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.18,
            "xanchor": "center",
            "x": 0.5,
        },
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(224,224,224,0.18)")
    return fig


def _mostrar_rotulos_barras(fig, template: str = "%{text}") -> None:
    fig.update_traces(
        texttemplate=template,
        textposition="inside",
        insidetextanchor="middle",
        constraintext="none",
        cliponaxis=False,
        textfont={"color": PALETA["texto_eixos"], "size": 12},
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


def render_dashboard_charts(
    df_resumo: pd.DataFrame,
    df_evolucao_mensal: pd.DataFrame,
    df_manutencao_contrato: pd.DataFrame,
    df_equipamentos_contrato: pd.DataFrame,
) -> None:
    if df_evolucao_mensal.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    col_top_1, col_top_2 = st.columns(2)

    with col_top_1:
        with st.container(border=True):
            percentual_frota = df_evolucao_mensal.sort_values("mes").copy()
            percentual_frota["mes_label"] = percentual_frota["mes"].apply(_formatar_mes_curto)
            percentual_frota["cor_barra"] = percentual_frota["percentual_qtd_x_frota"].apply(
                _cor_percentual_frota
            )
            ordem_meses = percentual_frota["mes_label"].tolist()
            fig_percentual = px.bar(
                percentual_frota,
                x="mes_label",
                y="percentual_qtd_x_frota",
                title="% QTD x FROTA",
                text="percentual_qtd_x_frota",
                category_orders={"mes_label": ordem_meses},
                labels={"mes_label": "mes"},
                hover_data={
                    "mes_label": False,
                    "cor_barra": False,
                    "mes": "|%m/%Y",
                    "percentual_qtd_x_frota": ":.2f",
                },
            )
            fig_percentual.update_traces(marker_color=percentual_frota["cor_barra"])
            fig_percentual.update_xaxes(
                type="category",
                categoryorder="array",
                categoryarray=ordem_meses,
            )
            _mostrar_rotulos_barras(fig_percentual, "%{text:.2f}%")
            st.plotly_chart(_estilizar_figura(fig_percentual), use_container_width=True)

    with col_top_2:
        with st.container(border=True):
            if df_manutencao_contrato.empty:
                st.info("Sem dados de manutencao por contrato para os filtros selecionados.")
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
                    title="EQUIPAMENTOS EM MANUTENCAO POR CONTRATO",
                    text="quantidade_manutencao",
                    labels={
                        "contrato": "Contrato",
                        "quantidade_manutencao": "Quantidade em manutencao",
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

    col_bottom_1, col_bottom_2 = st.columns(2)

    with col_bottom_1:
        with st.container(border=True):
            fig_servico = px.bar(
                df_evolucao_mensal,
                x="mes",
                y="total_qtd",
                title="SERVICOS EXECUTADOS",
                text="total_qtd",
                color="total_qtd",
                color_continuous_scale=ESCALA_OPERACIONAL,
            )
            _mostrar_rotulos_barras(fig_servico, "%{text:.0f}")
            fig_servico.update_coloraxes(showscale=False)
            st.plotly_chart(_estilizar_figura(fig_servico), use_container_width=True)

    with col_bottom_2:
        with st.container(border=True):
            ranking = df_resumo.sort_values("total_qtd", ascending=True).tail(8)
            fig_ranking = px.bar(
                ranking,
                x="total_qtd",
                y="equipamento",
                orientation="h",
                title="PRINCIPAIS EQUIPAMENTOS NA MANUTENCAO",
                text="total_qtd",
                color="total_qtd",
                color_continuous_scale=ESCALA_RANKING,
                labels={
                    "total_qtd": "Quantidade em manutencao",
                    "equipamento": "Equipamento",
                },
            )
            _mostrar_rotulos_barras(fig_ranking, "%{text:.0f}")
            fig_ranking.update_coloraxes(showscale=False)
            st.plotly_chart(_estilizar_figura(fig_ranking), use_container_width=True)

    with st.container(border=True):
        if df_equipamentos_contrato.empty:
            st.info("Sem dados de contrato para os filtros selecionados.")
        else:
            fig_contrato = px.bar(
                df_equipamentos_contrato,
                x="contrato",
                y="quantidade_equipamentos",
                title="EQUIPAMENTOS POR CONTRATO - MES MAIS RECENTE",
                text="quantidade_equipamentos",
                color="quantidade_equipamentos",
                hover_data={"mes": "|%Y-%m", "quantidade_equipamentos": ":.0f"},
                color_continuous_scale=ESCALA_OPERACIONAL,
                labels={
                    "contrato": "contrato",
                    "quantidade_equipamentos": "quantidade_equipamentos",
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


def render_frota_operadora_chart(df_frota_operadora: pd.DataFrame) -> None:
    if df_frota_operadora.empty:
        st.info("Sem dados de frota CCIT por operadora para os filtros selecionados.")
        return

    mes_label = str(df_frota_operadora["mes_label"].iloc[0]).upper()

    with st.container(border=True):
        fig = px.bar(
            df_frota_operadora,
            x="operadora",
            y="quantidade_frota",
            color="quantidade_frota",
            title=f"FROTA CCIT POR OPERADORA - {mes_label}",
            text="quantidade_frota",
            color_continuous_scale=ESCALA_OPERACIONAL,
            labels={
                "operadora": "Operadora",
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
            categoryarray=df_frota_operadora["operadora"].tolist(),
        )
        _mostrar_rotulos_barras(fig, "%{text:.0f}")
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(_estilizar_figura(fig), use_container_width=True)


def render_servicos_executados_chart(df_servicos_resumo: pd.DataFrame) -> None:
    if df_servicos_resumo.empty:
        st.info("Sem serviços executados para os filtros selecionados.")
        return

    ranking = df_servicos_resumo.sort_values("quantidade_servicos", ascending=True).tail(5)

    with st.container(border=True):
        fig = px.bar(
            ranking,
            x="quantidade_servicos",
            y="servico_executado",
            orientation="h",
            title="SERVICOS EXECUTADOS POR TIPO",
            text="quantidade_servicos",
            color="quantidade_servicos",
            color_continuous_scale=ESCALA_RANKING,
            labels={
                "servico_executado": "Servico executado",
                "quantidade_servicos": "Quantidade",
            },
        )
        _mostrar_rotulos_barras(fig, "%{text:.0f}")
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(_estilizar_figura(fig), use_container_width=True)

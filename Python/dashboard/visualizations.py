import pandas as pd
import plotly.express as px
import streamlit as st

PALETA = {
    "mist": "#CBD5E1",
    "smoke": "#94A3B8",
    "steel": "#64748B",
    "slate": "#475569",
    "graphite": "#334155",
    "charcoal": "#1F2937",
}


def _cor_texto_tema() -> str:
    theme_base = st.get_option("theme.base")
    return st.get_option("theme.textColor") or ("#F8FAFC" if theme_base == "dark" else "#0F172A")


def _estilizar_figura(fig):
    text_color = _cor_texto_tema()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": text_color},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(127,127,127,0.25)")
    return fig


def _mostrar_rotulos_barras(fig, template: str = "%{text}") -> None:
    fig.update_traces(
        texttemplate=template,
        textposition="inside",
        insidetextanchor="middle",
        constraintext="none",
        cliponaxis=False,
        textfont={"color": "#F8FAFC", "size": 12},
        selector={"type": "bar"},
    )
    fig.update_layout(uniformtext={"minsize": 10, "mode": "show"})


def render_dashboard_charts(
    df_resumo: pd.DataFrame,
    df_evolucao_mensal: pd.DataFrame,
    df_evolucao_equipamento: pd.DataFrame,
    df_equipamentos_contrato: pd.DataFrame,
) -> None:
    if df_evolucao_mensal.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    col_top_1, col_top_2 = st.columns(2)

    with col_top_1:
        with st.container(border=True):
            fig_percentual = px.bar(
                df_evolucao_mensal,
                x="mes",
                y="percentual_qtd_x_frota",
                title="% QTD x FROTaaasdsada mudou??????"  \
                "A",
                text="percentual_qtd_x_frota",
                color="percentual_qtd_x_frota",
                color_continuous_scale=[PALETA["mist"], PALETA["steel"], PALETA["charcoal"]],
            )
            _mostrar_rotulos_barras(fig_percentual, "%{text:.2f}%")
            fig_percentual.update_coloraxes(showscale=False)
            st.plotly_chart(_estilizar_figura(fig_percentual), use_container_width=True)

    with col_top_2:
        with st.container(border=True):
            if df_evolucao_equipamento.empty:
                st.info("Sem dados de frota por equipamento para os filtros selecionados.")
            else:
                fig_qtd_frota = px.bar(
                    df_evolucao_equipamento,
                    x="mes",
                    y="total_frota",
                    color="equipamento",
                    barmode="group",
                    title="FROTA POR EQUIPAMENTO / MES",
                    text="total_frota",
                    labels={
                        "mes": "Mes",
                        "total_frota": "Frota",
                        "equipamento": "Equipamento",
                    },
                )
                _mostrar_rotulos_barras(fig_qtd_frota, "%{text:.0f}")
                st.plotly_chart(_estilizar_figura(fig_qtd_frota), use_container_width=True)

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
                color_continuous_scale=[PALETA["mist"], PALETA["slate"], PALETA["graphite"]],
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
                title="TOTAL PRINCIPAIS SERVICOS",
                text="total_qtd",
                color="total_qtd",
                color_continuous_scale=[PALETA["smoke"], PALETA["slate"], PALETA["charcoal"]],
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
                color_continuous_scale=[
                    PALETA["mist"],
                    PALETA["steel"],
                    PALETA["charcoal"],
                ],
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
            color_continuous_scale=[PALETA["mist"], PALETA["steel"], PALETA["charcoal"]],
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
            color_continuous_scale=[PALETA["mist"], PALETA["steel"], PALETA["charcoal"]],
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

    ranking = df_servicos_resumo.sort_values("quantidade_servicos", ascending=True).tail(20)

    with st.container(border=True):
        fig = px.bar(
            ranking,
            x="quantidade_servicos",
            y="servico_executado",
            orientation="h",
            title="SERVICOS EXECUTADOS POR TIPO",
            text="quantidade_servicos",
            color="quantidade_servicos",
            color_continuous_scale=[PALETA["mist"], PALETA["steel"], PALETA["charcoal"]],
            labels={
                "servico_executado": "Servico executado",
                "quantidade_servicos": "Quantidade",
            },
        )
        _mostrar_rotulos_barras(fig, "%{text:.0f}")
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(_estilizar_figura(fig), use_container_width=True)

import textwrap

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
    "vermelho_tacom":"#a51a24"
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
FONTE_ROTULOS_DADOS = 16
FONTE_ROTULOS_DADOS_COMPACTO = 14


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


def _mostrar_rotulos_barras(
    fig,
    template: str = "%{text}",
    font_size: int = FONTE_ROTULOS_DADOS,
    uniform_min_size: int = 12,
) -> None:
    fig.update_traces(
        texttemplate=template,
        textposition="inside",
        insidetextanchor="middle",
        constraintext="none",
        cliponaxis=False,
        textfont={"color": _cor_texto_tema(), "size": font_size},
        insidetextfont={"color": _cor_texto_tema(), "size": font_size},
        selector={"type": "bar"},
    )
    fig.update_layout(uniformtext={"minsize": uniform_min_size, "mode": "show"})


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


def _quebrar_rotulo_eixo(
    valor: object,
    largura: int = 16,
    max_linhas: int = 3,
) -> str:
    texto = str(valor or "").strip()
    if len(texto) <= largura:
        return texto

    linhas = textwrap.wrap(
        texto,
        width=largura,
        break_long_words=True,
        break_on_hyphens=False,
    )
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        linhas[-1] = f"{linhas[-1][: max(0, largura - 3)].rstrip()}..."

    return "<br>".join(linhas)


def _render_manutencao_por_categoria_chart(
    df_manutencao: pd.DataFrame | None,
    coluna_categoria: str,
    rotulo_categoria: str,
    titulo: str,
    mensagem_vazia: str,
) -> None:
    if df_manutencao is None or df_manutencao.empty:
        st.info(mensagem_vazia)
        return

    manutencao_categoria = df_manutencao.sort_values(
        "quantidade_manutencao",
        ascending=False,
    )
    ordem_categorias = manutencao_categoria[coluna_categoria].tolist()
    fig_manutencao = px.bar(
        manutencao_categoria,
        x=coluna_categoria,
        y="quantidade_manutencao",
        color=coluna_categoria,
        color_discrete_sequence=CORES_CATEGORICAS,
        category_orders={coluna_categoria: ordem_categorias},
        title=titulo,
        text="quantidade_manutencao",
        labels={
            coluna_categoria: rotulo_categoria,
            "quantidade_manutencao": "Quantidade em manutenção",
        },
    )
    fig_manutencao.update_xaxes(
        categoryorder="array",
        categoryarray=ordem_categorias,
        tickmode="array",
        tickvals=ordem_categorias,
        ticktext=[_quebrar_rotulo_eixo(categoria) for categoria in ordem_categorias],
        tickangle=0,
        automargin=True,
    )
    _mostrar_rotulos_barras(fig_manutencao, "%{text:.0f}")
    fig_manutencao.update_layout(showlegend=False)
    fig_manutencao = _estilizar_figura(fig_manutencao)
    fig_manutencao.update_layout(margin={"b": 85})
    st.plotly_chart(
        fig_manutencao,
        use_container_width=True,
    )


def _render_manutencao_operadora_chart(
    df_manutencao_operadora: pd.DataFrame | None,
) -> None:
    if df_manutencao_operadora is None or df_manutencao_operadora.empty:
        st.info("Sem dados de manutenção por operadora para os filtros selecionados.")
        return

    manutencao_operadora = df_manutencao_operadora.sort_values(
        "percentual_manutencao_frota",
        ascending=False,
    ).copy()
    ordem_operadoras = manutencao_operadora["operadora"].tolist()
    manutencao_operadora["rotulo_manutencao"] = manutencao_operadora.apply(
        lambda row: (
            f"{row['quantidade_manutencao']:.0f} "
            f"({row['percentual_manutencao_frota']:.2f}%)"
        ),
        axis=1,
    )

    fig_operadora = px.bar(
        manutencao_operadora,
        x="operadora",
        y="percentual_manutencao_frota",
        color="percentual_manutencao_frota",
        color_continuous_scale=ESCALA_ALERTA,
        category_orders={"operadora": ordem_operadoras},
        title="MANUTENÇÃO X FROTA POR OPERADORA",
        text="rotulo_manutencao",
        custom_data=["quantidade_manutencao", "total_frota"],
        labels={
            "operadora": "Operadora",
            "percentual_manutencao_frota": "% da frota em manutenção",
        },
    )
    fig_operadora.update_xaxes(
        categoryorder="array",
        categoryarray=ordem_operadoras,
        tickmode="array",
        tickvals=ordem_operadoras,
        ticktext=[_quebrar_rotulo_eixo(operadora) for operadora in ordem_operadoras],
        tickangle=0,
        automargin=True,
    )
    fig_operadora.update_yaxes(ticksuffix="%", rangemode="tozero")
    fig_operadora.update_traces(
        texttemplate="%{text}",
        textposition="outside",
        cliponaxis=False,
        textfont={"color": _cor_texto_tema(), "size": FONTE_ROTULOS_DADOS},
        hovertemplate=(
            "Operadora=%{x}<br>"
            "Qtd manutenção=%{customdata[0]:.0f}<br>"
            "Frota total=%{customdata[1]:.0f}<br>"
            "% manutenção/frota=%{y:.2f}%<extra></extra>"
        ),
    )

    limite_y = max(5, manutencao_operadora["percentual_manutencao_frota"].max() * 1.25)
    fig_operadora.update_yaxes(range=[0, limite_y])
    fig_operadora.update_coloraxes(showscale=False)
    fig_operadora = _estilizar_figura(fig_operadora)
    fig_operadora.update_layout(margin={"b": 95}, showlegend=False)
    st.plotly_chart(fig_operadora, use_container_width=True)


def _render_equipamentos_operadora_chart(
    df_equipamentos_operadora: pd.DataFrame | None,
) -> None:
    if df_equipamentos_operadora is None or df_equipamentos_operadora.empty:
        st.info("Sem dados de manutenção por equipamento para os filtros selecionados.")
        return

    equipamentos_operadora = df_equipamentos_operadora.copy()
    ordem_operadoras = (
        equipamentos_operadora[["operadora", "total_operadora"]]
        .drop_duplicates()
        .sort_values("total_operadora", ascending=True)["operadora"]
        .tolist()
    )
    ordem_equipamentos = (
        equipamentos_operadora.groupby("equipamento")["quantidade_manutencao"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    fig_equipamentos = px.bar(
        equipamentos_operadora,
        x="quantidade_manutencao",
        y="operadora",
        color="equipamento",
        orientation="h",
        title="MANUTENÇÃO POR EQUIPAMENTO E OPERADORA",
        text="quantidade_manutencao",
        color_discrete_sequence=CORES_CATEGORICAS,
        category_orders={
            "operadora": ordem_operadoras,
            "equipamento": ordem_equipamentos,
        },
        custom_data=["equipamento", "total_operadora"],
        labels={
            "operadora": "Operadora",
            "equipamento": "Equipamento",
            "quantidade_manutencao": "Quantidade em manutenção",
        },
    )
    fig_equipamentos.update_yaxes(
        categoryorder="array",
        categoryarray=ordem_operadoras,
        tickmode="array",
        tickvals=ordem_operadoras,
        ticktext=[
            _quebrar_rotulo_eixo(operadora, largura=28, max_linhas=2)
            for operadora in ordem_operadoras
        ],
        automargin=True,
    )
    fig_equipamentos.update_traces(
        texttemplate="%{text:.0f}",
        textposition="inside",
        insidetextanchor="middle",
        cliponaxis=False,
        textfont={"color": "#FFFFFF", "size": FONTE_ROTULOS_DADOS_COMPACTO},
        insidetextfont={"color": "#FFFFFF", "size": FONTE_ROTULOS_DADOS_COMPACTO},
        hovertemplate=(
            "Operadora=%{y}<br>"
            "Equipamento=%{customdata[0]}<br>"
            "Qtd manutenção=%{x:.0f}<br>"
            "Total manutenção operadora=%{customdata[1]:.0f}<extra></extra>"
        ),
    )
    altura = max(430, len(ordem_operadoras) * 58 + 180)
    fig_equipamentos = _estilizar_figura(fig_equipamentos)
    fig_equipamentos.update_layout(
        barmode="stack",
        height=altura,
        margin={"l": 190, "b": 105},
        legend={
            "font": {"color": _cor_texto_tema()},
            "orientation": "h",
            "yanchor": "top",
            "y": -0.16,
            "xanchor": "center",
            "x": 0.5,
            "title": {"text": ""},
        },
    )
    fig_equipamentos.update_xaxes(rangemode="tozero")
    st.plotly_chart(fig_equipamentos, use_container_width=True)


def render_analise_operadora_charts(
    df_manutencao_operadora: pd.DataFrame,
    df_equipamentos_operadora: pd.DataFrame,
) -> None:
    st.markdown(
        '<div class="section-title">Análise por Operadora</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        _render_manutencao_operadora_chart(df_manutencao_operadora)

    st.write("")

    with st.container(border=True):
        _render_equipamentos_operadora_chart(df_equipamentos_operadora)


def render_dashboard_charts(
    df_resumo: pd.DataFrame,
    df_evolucao_mensal: pd.DataFrame,
    df_manutencao_contrato: pd.DataFrame,
    df_equipamentos_contrato: pd.DataFrame,
    df_servicos_resumo: pd.DataFrame | None = None,
    df_manutencao_operadora: pd.DataFrame | None = None,
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

    col_manutencao_1, col_manutencao_2 = st.columns(2)

    with col_manutencao_1:
        with st.container(border=True):
            _render_manutencao_por_categoria_chart(
                df_manutencao_contrato,
                "contrato",
                "Contrato",
                "EQUIPAMENTOS EM MANUTENÇÃO POR CONTRATO",
                "Sem dados de manutenção por contrato para os filtros selecionados.",
            )

    with col_manutencao_2:
        with st.container(border=True):
            _render_manutencao_operadora_chart(df_manutencao_operadora)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">Gráficos anuais e variáveis</div>',
        unsafe_allow_html=True,
    )

    col_anual_1, col_anual_2 = st.columns(2)

    with col_anual_1:
        with st.container(border=True):
            percentual_frota = df_evolucao_mensal.sort_values("mes").copy()
            percentual_frota["mes_label"] = percentual_frota["mes"].apply(
                _formatar_mes_curto
            )
            ordem_meses = percentual_frota["mes_label"].tolist()
            fig_percentual = px.line(
                percentual_frota,
                x="mes_label",
                y="percentual_qtd_x_frota",
                title=" RESUMO ANUAL - FROTA EM MANUTENÇÃO (%)",
                text="percentual_qtd_x_frota",
                markers=True,
                category_orders={"mes_label": ordem_meses},
                labels={
                    "mes_label": "Mês",
                    "percentual_qtd_x_frota": "% Equipamentos",
                },
                hover_data={
                    "mes_label": False,
                    "mes": "|%m/%Y",
                    "percentual_qtd_x_frota": ":.2f",
                },
            )
            fig_percentual.update_traces(
                mode="lines+markers+text",
                line={"color": PALETA["vermelho_tacom"], "width": 3},
                marker={
                    "color": PALETA["vermelho_tacom"],
                    "size": 8,
                    "symbol": "circle",
                },
                texttemplate="%{text:.2f}%",
                textposition="top center",
                textfont={"color": _cor_texto_tema(), "size": FONTE_ROTULOS_DADOS},
                cliponaxis=False,
                hovertemplate=(
                    "Mes=%{x}<br>% Equipamentos=%{y:.2f}%<extra></extra>"
                ),
            )
            fig_percentual.update_xaxes(
                type="category",
                categoryorder="array",
                categoryarray=ordem_meses,
            )
            limite_y = max(
                6,
                percentual_frota["percentual_qtd_x_frota"].max() * 1.15,
            )
            fig_percentual.update_yaxes(range=[0, limite_y], dtick=2)
            st.plotly_chart(_estilizar_figura(fig_percentual), use_container_width=True)

    with col_anual_2:
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
                st.plotly_chart(
                    _estilizar_figura(fig_contrato),
                    use_container_width=True,
                )


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
    _mostrar_rotulos_barras(
        fig,
        "%{text:.0f}",
        font_size=18,
        uniform_min_size=16,
    )
    fig.update_coloraxes(showscale=False)
    fig = _estilizar_figura(fig)
    fig.update_xaxes(tickfont={"size": 14})
    fig.update_yaxes(tickfont={"size": 15})

    if usar_container:
        with st.container(border=True):
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.plotly_chart(fig, use_container_width=True)

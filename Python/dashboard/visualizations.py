import textwrap

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.styles import tema_claro_ativo
from dashboard.utils_otimizacoes import formatar_mes

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
CORES_EQUIPAMENTOS = (
    px.colors.qualitative.Dark24
    + px.colors.qualitative.Light24
    + px.colors.qualitative.Alphabet
)
FONTE_ROTULOS_DADOS = 16
FONTE_ROTULOS_DADOS_COMPACTO = 14
DRILL_COL_CONTRATO = "contrato"
DRILL_COL_EQUIPAMENTO = "equipamento"
DRILL_COL_SERVICO_EXECUTADO = "servico_executado"
DRILL_COL_QTD_SERVICO_EXECUTADO = "qtd_servico"
DRILL_NIVEL_KEY = "drill_down_nivel"
DRILL_CONTRATO_KEY = "drill_down_contrato"
DRILL_EQUIPAMENTO_KEY = "drill_down_equipamento"
DRILL_NIVEL_CONTRATOS = 1
DRILL_NIVEL_EQUIPAMENTOS = 2
DRILL_NIVEL_SERVICOS = 3
OS_DRILL_NIVEL_KEY = "os_drill_down_nivel"
OS_DRILL_OPERADORA_KEY = "os_drill_down_operadora"
OS_DRILL_NIVEL_OPERADORAS = 1
OS_DRILL_NIVEL_EQUIPAMENTOS = 2


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
    """Formata mês em português (formato curto). Consolidado em utils_otimizacoes."""
    return formatar_mes(data_mes, formato="curto")


def _formatar_periodo_grafico(inicio: object, fim: object) -> str:
    inicio = pd.to_datetime(inicio, errors="coerce")
    fim = pd.to_datetime(fim, errors="coerce")

    if pd.isna(inicio) or pd.isna(fim):
        return "periodo nao identificado"
    if inicio.to_period("M") == fim.to_period("M"):
        return _formatar_mes_curto(inicio)
    return f"{_formatar_mes_curto(inicio)} a {_formatar_mes_curto(fim)}"


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


def _inicializar_estado_drill_down() -> None:
    st.session_state.setdefault(DRILL_NIVEL_KEY, DRILL_NIVEL_CONTRATOS)
    st.session_state.setdefault(DRILL_CONTRATO_KEY, None)
    st.session_state.setdefault(DRILL_EQUIPAMENTO_KEY, None)


def _reiniciar_drill_down() -> None:
    st.session_state[DRILL_NIVEL_KEY] = DRILL_NIVEL_CONTRATOS
    st.session_state[DRILL_CONTRATO_KEY] = None
    st.session_state[DRILL_EQUIPAMENTO_KEY] = None


def _voltar_drill_down() -> None:
    nivel_atual = st.session_state.get(DRILL_NIVEL_KEY, DRILL_NIVEL_CONTRATOS)

    if nivel_atual == DRILL_NIVEL_SERVICOS:
        st.session_state[DRILL_NIVEL_KEY] = DRILL_NIVEL_EQUIPAMENTOS
        st.session_state[DRILL_EQUIPAMENTO_KEY] = None
    elif nivel_atual == DRILL_NIVEL_EQUIPAMENTOS:
        _reiniciar_drill_down()


def _validar_colunas_drill_down(df: pd.DataFrame) -> bool:
    colunas_obrigatorias = [
        DRILL_COL_CONTRATO,
        DRILL_COL_EQUIPAMENTO,
        DRILL_COL_SERVICO_EXECUTADO,
        DRILL_COL_QTD_SERVICO_EXECUTADO,
    ]
    colunas_ausentes = [coluna for coluna in colunas_obrigatorias if coluna not in df.columns]

    if colunas_ausentes:
        st.warning(
            "Não foi possível renderizar o drill down. "
            f"Colunas ausentes: {', '.join(colunas_ausentes)}."
        )
        st.caption(
            "Ajuste as constantes DRILL_COL_* em dashboard/visualizations.py "
            "caso os nomes das colunas mudem."
        )
        return False

    return True


def _preparar_dataframe_drill_down(df: pd.DataFrame) -> pd.DataFrame:
    df_drill = df.copy()

    for coluna in [
        DRILL_COL_CONTRATO,
        DRILL_COL_EQUIPAMENTO,
        DRILL_COL_SERVICO_EXECUTADO,
    ]:
        df_drill[coluna] = df_drill[coluna].fillna("").astype(str).str.strip()

    df_drill[DRILL_COL_QTD_SERVICO_EXECUTADO] = pd.to_numeric(
        df_drill[DRILL_COL_QTD_SERVICO_EXECUTADO],
        errors="coerce",
    ).fillna(0)

    return df_drill


def _sincronizar_estado_drill_down(df: pd.DataFrame) -> None:
    contrato = st.session_state.get(DRILL_CONTRATO_KEY)
    equipamento = st.session_state.get(DRILL_EQUIPAMENTO_KEY)

    if contrato and contrato not in set(df[DRILL_COL_CONTRATO].dropna().astype(str)):
        _reiniciar_drill_down()
        return

    if not contrato:
        st.session_state[DRILL_NIVEL_KEY] = DRILL_NIVEL_CONTRATOS
        st.session_state[DRILL_EQUIPAMENTO_KEY] = None
        return

    df_contrato = df[df[DRILL_COL_CONTRATO].eq(contrato)]
    if equipamento and equipamento not in set(
        df_contrato[DRILL_COL_EQUIPAMENTO].dropna().astype(str)
    ):
        st.session_state[DRILL_NIVEL_KEY] = DRILL_NIVEL_EQUIPAMENTOS
        st.session_state[DRILL_EQUIPAMENTO_KEY] = None


def _agrupar_drill_down(df: pd.DataFrame, coluna_grupo: str) -> pd.DataFrame:
    resumo = (
        df[df[coluna_grupo].fillna("").astype(str).str.strip().ne("")]
        .groupby(coluna_grupo, as_index=False)
        .agg(quantidade=(DRILL_COL_QTD_SERVICO_EXECUTADO, "sum"))
        .sort_values("quantidade", ascending=False)
    )
    resumo["quantidade"] = resumo["quantidade"].round(0).astype(int)
    return resumo


def _obter_valor_selecionado(evento_plotly: object) -> str | None:
    selecao = getattr(evento_plotly, "selection", None)
    if not selecao and isinstance(evento_plotly, dict):
        selecao = evento_plotly.get("selection")

    pontos = getattr(selecao, "points", None)
    if pontos is None and isinstance(selecao, dict):
        pontos = selecao.get("points")
    if not pontos:
        return None

    ponto = pontos[0]
    customdata = (
        ponto.get("customdata")
        if isinstance(ponto, dict)
        else getattr(ponto, "customdata", None)
    )
    if isinstance(customdata, (list, tuple)) and customdata:
        return str(customdata[0])
    if customdata is not None:
        return str(customdata)

    for chave in ["x", "y", "label"]:
        valor = ponto.get(chave) if isinstance(ponto, dict) else getattr(ponto, chave, None)
        if valor is not None:
            return str(valor)

    return None


def _render_grafico_drill_down(
    resumo: pd.DataFrame,
    coluna_categoria: str,
    titulo: str,
    rotulo_categoria: str,
    chave: str,
    orientacao: str = "v",
) -> object:
    if resumo.empty:
        st.info("Sem dados para os filtros selecionados neste nível.")
        return None

    total_categorias = len(resumo)
    opcoes_quantidade = list(range(10, total_categorias + 1, 10))
    if not opcoes_quantidade or opcoes_quantidade[-1] != total_categorias:
        opcoes_quantidade.append(total_categorias)

    chave_quantidade = f"{chave}_quantidade"
    quantidade_padrao = min(10, total_categorias)
    if st.session_state.get(chave_quantidade) not in opcoes_quantidade:
        st.session_state[chave_quantidade] = quantidade_padrao

    rotulos_seletor = {
        DRILL_COL_CONTRATO: "Contratos exibidos",
        DRILL_COL_EQUIPAMENTO: "Equipamentos exibidos",
        DRILL_COL_SERVICO_EXECUTADO: "Serviços executados exibidos",
    }
    coluna_seletor, _ = st.columns([1.2, 3.8])
    with coluna_seletor:
        quantidade_exibida = st.selectbox(
            rotulos_seletor.get(coluna_categoria, "Itens exibidos"),
            options=opcoes_quantidade,
            key=chave_quantidade,
            format_func=lambda quantidade: (
                f"Todos ({total_categorias})"
                if quantidade == total_categorias
                else f"Top {quantidade}"
            ),
        )

    resumo = resumo.head(quantidade_exibida).copy()
    titulo = f"{titulo} — Top {quantidade_exibida}"
    categorias = resumo[coluna_categoria].fillna("").astype(str)
    if orientacao == "v" and (
        len(resumo) > 18 or categorias.map(len).max() > 22
    ):
        orientacao = "h"

    if orientacao == "h":
        dados = resumo.sort_values("quantidade", ascending=True)
        fig = px.bar(
            dados,
            x="quantidade",
            y=coluna_categoria,
            orientation="h",
            title=titulo,
            text="quantidade",
            color="quantidade",
            color_continuous_scale=ESCALA_RANKING,
            custom_data=[coluna_categoria],
            labels={
                coluna_categoria: rotulo_categoria,
                "quantidade": "Quantidade",
            },
        )
        fig.update_yaxes(
            ticktext=[
                _quebrar_rotulo_eixo(categoria, largura=38, max_linhas=2)
                for categoria in dados[coluna_categoria].tolist()
            ],
            tickvals=dados[coluna_categoria].tolist(),
            automargin=True,
        )
        fig.update_xaxes(rangemode="tozero")
        fig.update_layout(
            height=max(520, min(1500, len(dados) * 30 + 220)),
            margin={"l": 230, "r": 30, "t": 70, "b": 60},
        )
    else:
        dados = resumo
        ordem_categorias = dados[coluna_categoria].tolist()
        fig = px.bar(
            dados,
            x=coluna_categoria,
            y="quantidade",
            title=titulo,
            text="quantidade",
            color="quantidade",
            color_continuous_scale=ESCALA_RANKING,
            category_orders={coluna_categoria: ordem_categorias},
            custom_data=[coluna_categoria],
            labels={
                coluna_categoria: rotulo_categoria,
                "quantidade": "Quantidade",
            },
        )
        fig.update_xaxes(
            categoryorder="array",
            categoryarray=ordem_categorias,
            tickmode="array",
            tickvals=ordem_categorias,
            ticktext=[
                _quebrar_rotulo_eixo(categoria, largura=18, max_linhas=3)
                for categoria in ordem_categorias
            ],
            tickangle=0,
            automargin=True,
        )
        fig.update_yaxes(rangemode="tozero")
        fig.update_layout(height=max(430, min(760, len(dados) * 28 + 320)), margin={"b": 100})

    _mostrar_rotulos_barras(fig, "%{text:.0f}", font_size=15, uniform_min_size=12)
    fig.update_coloraxes(showscale=False)
    fig = _estilizar_figura(fig)
    quantidade_hover = "%{x:.0f}" if orientacao == "h" else "%{y:.0f}"
    fig.update_traces(
        hovertemplate=(
            f"{rotulo_categoria}=%{{customdata[0]}}<br>"
            f"Quantidade={quantidade_hover}<extra></extra>"
        )
    )

    return st.plotly_chart(
        fig,
        use_container_width=True,
        key=chave,
        on_select="rerun",
        selection_mode="points",
    )


def _render_tabela_drill_down(df: pd.DataFrame) -> None:
    df_view = df.copy()
    for coluna in ["data_ref", "data_competencia"]:
        if coluna in df_view.columns:
            df_view[coluna] = pd.to_datetime(df_view[coluna], errors="coerce").dt.strftime(
                "%Y-%m-%d"
            )

    if "data_ref" in df_view.columns:
        df_view = df_view.sort_values("data_ref", ascending=False)

    st.subheader("Dados filtrados")
    st.dataframe(df_view, use_container_width=True, hide_index=True)


def render_drill_down(df: pd.DataFrame) -> None:
    _inicializar_estado_drill_down()

    if df.empty:
        st.info("Sem serviços executados para os filtros selecionados.")
        return
    if not _validar_colunas_drill_down(df):
        return

    df_drill = _preparar_dataframe_drill_down(df)
    _sincronizar_estado_drill_down(df_drill)

    nivel = st.session_state.get(DRILL_NIVEL_KEY, DRILL_NIVEL_CONTRATOS)
    contrato = st.session_state.get(DRILL_CONTRATO_KEY)
    equipamento = st.session_state.get(DRILL_EQUIPAMENTO_KEY)

    with st.container(border=True):
        col_titulo, col_voltar, col_reiniciar = st.columns([5, 1, 1.4])
        with col_titulo:
            st.subheader("Drill Down de Serviços Executados")
            caminho = ["Contratos"]
            if contrato:
                caminho.append(str(contrato))
            if equipamento:
                caminho.append(str(equipamento))
            st.caption(" > ".join(caminho))
        with col_voltar:
            st.button(
                "⬅ Voltar",
                disabled=nivel == DRILL_NIVEL_CONTRATOS,
                on_click=_voltar_drill_down,
                use_container_width=True,
            )
        with col_reiniciar:
            st.button(
                "🔄 Reiniciar Drill Down",
                on_click=_reiniciar_drill_down,
                use_container_width=True,
            )

        if nivel == DRILL_NIVEL_CONTRATOS:
            resumo = _agrupar_drill_down(df_drill, DRILL_COL_CONTRATO)
            evento = _render_grafico_drill_down(
                resumo,
                DRILL_COL_CONTRATO,
                "Nível 1: Contrato / Filial",
                "Contrato",
                "drill_down_contratos_chart",
            )
            contrato_selecionado = _obter_valor_selecionado(evento)
            if contrato_selecionado:
                st.session_state[DRILL_CONTRATO_KEY] = contrato_selecionado
                st.session_state[DRILL_EQUIPAMENTO_KEY] = None
                st.session_state[DRILL_NIVEL_KEY] = DRILL_NIVEL_EQUIPAMENTOS
                st.rerun()
            return

        if nivel == DRILL_NIVEL_EQUIPAMENTOS:
            if not contrato:
                _reiniciar_drill_down()
                st.rerun()

            df_contrato = df_drill[df_drill[DRILL_COL_CONTRATO].eq(contrato)]
            resumo = _agrupar_drill_down(df_contrato, DRILL_COL_EQUIPAMENTO)
            evento = _render_grafico_drill_down(
                resumo,
                DRILL_COL_EQUIPAMENTO,
                f"Nível 2: Equipamentos - {contrato}",
                "Equipamento",
                "drill_down_equipamentos_chart",
            )
            equipamento_selecionado = _obter_valor_selecionado(evento)
            if equipamento_selecionado:
                st.session_state[DRILL_EQUIPAMENTO_KEY] = equipamento_selecionado
                st.session_state[DRILL_NIVEL_KEY] = DRILL_NIVEL_SERVICOS
                st.rerun()
            return

        if not contrato or not equipamento:
            _reiniciar_drill_down()
            st.rerun()

        df_servicos = df_drill[
            df_drill[DRILL_COL_CONTRATO].eq(contrato)
            & df_drill[DRILL_COL_EQUIPAMENTO].eq(equipamento)
        ]
        resumo = _agrupar_drill_down(df_servicos, DRILL_COL_SERVICO_EXECUTADO)
        _render_grafico_drill_down(
            resumo,
            DRILL_COL_SERVICO_EXECUTADO,
            f"Nível 3: Serviços Executados - {equipamento}",
            "Serviço Executado",
            "drill_down_servicos_chart",
            orientacao="h",
        )
        _render_tabela_drill_down(df_servicos)


def _reiniciar_drill_down_os() -> None:
    st.session_state[OS_DRILL_NIVEL_KEY] = OS_DRILL_NIVEL_OPERADORAS
    st.session_state[OS_DRILL_OPERADORA_KEY] = None


def _sincronizar_drill_down_os(df_os: pd.DataFrame) -> None:
    st.session_state.setdefault(OS_DRILL_NIVEL_KEY, OS_DRILL_NIVEL_OPERADORAS)
    st.session_state.setdefault(OS_DRILL_OPERADORA_KEY, None)

    operadora = st.session_state.get(OS_DRILL_OPERADORA_KEY)
    operadoras_disponiveis = set(
        df_os["operadora"].fillna("").astype(str).str.strip()
    )
    if operadora and operadora not in operadoras_disponiveis:
        _reiniciar_drill_down_os()
    elif not operadora:
        st.session_state[OS_DRILL_NIVEL_KEY] = OS_DRILL_NIVEL_OPERADORAS


def _agrupar_ocorrencias_os(
    df_os: pd.DataFrame,
    coluna_grupo: str,
) -> pd.DataFrame:
    colunas = [coluna_grupo, "quantidade_os"]
    if df_os.empty:
        return pd.DataFrame(columns=colunas)

    dados = df_os.copy()
    dados[coluna_grupo] = dados[coluna_grupo].fillna("").astype(str).str.strip()
    dados["numero_os"] = dados["numero_os"].fillna("").astype(str).str.strip()
    dados = dados[dados[coluna_grupo].ne("") & dados["numero_os"].ne("")]

    resumo = (
        dados.groupby(coluna_grupo, as_index=False)
        .agg(quantidade_os=("numero_os", "size"))
        .sort_values(["quantidade_os", coluna_grupo], ascending=[False, True])
    )
    resumo["quantidade_os"] = resumo["quantidade_os"].astype(int)
    return resumo[colunas].reset_index(drop=True)


def _render_ranking_drill_down_os(
    resumo: pd.DataFrame,
    coluna_categoria: str,
    rotulo_categoria: str,
    titulo: str,
    chave: str,
    permitir_selecao: bool,
) -> object:
    if resumo.empty:
        st.info("Sem OS para os filtros selecionados neste nível.")
        return None

    total_categorias = len(resumo)
    opcoes_quantidade = list(range(10, total_categorias + 1, 10))
    if not opcoes_quantidade or opcoes_quantidade[-1] != total_categorias:
        opcoes_quantidade.append(total_categorias)

    chave_quantidade = f"{chave}_quantidade"
    quantidade_padrao = min(10, total_categorias)
    if st.session_state.get(chave_quantidade) not in opcoes_quantidade:
        st.session_state[chave_quantidade] = quantidade_padrao

    coluna_seletor, _ = st.columns([1.2, 3.8])
    with coluna_seletor:
        rotulo_seletor = (
            "Operadoras exibidas"
            if coluna_categoria == "operadora"
            else "Equipamentos exibidos"
        )
        quantidade_exibida = st.selectbox(
            rotulo_seletor,
            options=opcoes_quantidade,
            key=chave_quantidade,
            format_func=lambda quantidade: (
                f"Todos ({total_categorias})"
                if quantidade == total_categorias
                else f"Top {quantidade}"
            ),
        )

    dados = resumo.head(quantidade_exibida).sort_values(
        ["quantidade_os", coluna_categoria],
        ascending=[True, False],
    )
    altura = max(430, min(1000, len(dados) * 34 + 150))
    fig = px.bar(
        dados,
        x="quantidade_os",
        y=coluna_categoria,
        orientation="h",
        color="quantidade_os",
        color_continuous_scale=[PALETA["secundaria"], PALETA["primaria"]],
        text="quantidade_os",
        custom_data=[coluna_categoria],
        labels={
            coluna_categoria: rotulo_categoria,
            "quantidade_os": "Ocorrências de OS",
        },
        title=f"{titulo} — Top {quantidade_exibida}",
    )
    fig.update_layout(height=altura, coloraxis_showscale=False)
    fig.update_xaxes(rangemode="tozero", dtick=10)
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=dados[coluna_categoria].tolist(),
        tickmode="array",
        tickvals=dados[coluna_categoria].tolist(),
        ticktext=[
            _quebrar_rotulo_eixo(categoria, largura=38, max_linhas=2)
            for categoria in dados[coluna_categoria].tolist()
        ],
        automargin=True,
    )
    _mostrar_rotulos_barras(fig, "%{text:.0f}", font_size=14, uniform_min_size=11)
    fig.update_traces(
        hovertemplate=(
            f"{rotulo_categoria}=%{{customdata[0]}}<br>"
            "Ocorrências de OS=%{x:.0f}<extra></extra>"
        )
    )
    fig = _estilizar_figura(fig)

    parametros = {"use_container_width": True, "key": chave}
    if permitir_selecao:
        parametros.update(on_select="rerun", selection_mode="points")
    return st.plotly_chart(fig, **parametros)


def render_drill_down_os(
    df_os: pd.DataFrame | None,
    data_inicio: object,
    data_fim: object,
) -> None:
    periodo = (
        f"{pd.Timestamp(data_inicio).strftime('%d/%m/%Y')} a "
        f"{pd.Timestamp(data_fim).strftime('%d/%m/%Y')}"
    )

    if df_os is None:
        st.warning("Não foi possível carregar as OS do arquivo Oracle.")
        return
    if df_os.empty:
        st.info("Nenhuma OS encontrada no período selecionado.")
        return

    colunas_obrigatorias = ["operadora", "equipamento", "numero_os"]
    colunas_ausentes = [
        coluna for coluna in colunas_obrigatorias if coluna not in df_os.columns
    ]
    if colunas_ausentes:
        st.warning(
            "Não foi possível renderizar o drill down de OS. "
            f"Colunas ausentes: {', '.join(colunas_ausentes)}."
        )
        return

    dados_os = df_os.copy()
    for coluna in colunas_obrigatorias:
        dados_os[coluna] = dados_os[coluna].fillna("").astype(str).str.strip()

    _sincronizar_drill_down_os(dados_os)
    nivel = st.session_state.get(OS_DRILL_NIVEL_KEY, OS_DRILL_NIVEL_OPERADORAS)
    operadora = st.session_state.get(OS_DRILL_OPERADORA_KEY)

    with st.container(border=True):
        coluna_titulo, coluna_voltar, coluna_reiniciar = st.columns([5, 1, 1.4])
        with coluna_titulo:
            st.subheader("Drill Down de OS")
            caminho = ["Operadoras"]
            if operadora:
                caminho.append(str(operadora))
            st.caption(" > ".join(caminho))
        with coluna_voltar:
            st.button(
                "⬅ Voltar",
                key="os_drill_down_voltar",
                disabled=nivel == OS_DRILL_NIVEL_OPERADORAS,
                on_click=_reiniciar_drill_down_os,
                use_container_width=True,
            )
        with coluna_reiniciar:
            st.button(
                "🔄 Reiniciar",
                key="os_drill_down_reiniciar",
                on_click=_reiniciar_drill_down_os,
                use_container_width=True,
            )

        st.caption(
            f"Período selecionado: {periodo}. Somente ABA_ITEM = 1; "
            "todos os status e filtros da tela são considerados. "
            "Cada registro representa uma ocorrência, mesmo quando a OS se repete. "
            "Fonte: Python/Oracle/saida_oracle_destboad.csv."
        )

        if nivel == OS_DRILL_NIVEL_OPERADORAS:
            st.caption(
                "Clique na barra de uma operadora para visualizar seus equipamentos."
            )
            resumo_operadoras = _agrupar_ocorrencias_os(dados_os, "operadora")
            evento = _render_ranking_drill_down_os(
                resumo_operadoras,
                "operadora",
                "Operadora",
                "Nível 1: OS por operadora",
                "os_drill_down_operadoras_chart",
                permitir_selecao=True,
            )
            operadora_selecionada = _obter_valor_selecionado(evento)
            if operadora_selecionada:
                st.session_state[OS_DRILL_OPERADORA_KEY] = operadora_selecionada
                st.session_state[OS_DRILL_NIVEL_KEY] = OS_DRILL_NIVEL_EQUIPAMENTOS
                st.rerun()
            return

        if not operadora:
            _reiniciar_drill_down_os()
            st.rerun()

        dados_operadora = dados_os[dados_os["operadora"].eq(operadora)]
        resumo_equipamentos = _agrupar_ocorrencias_os(
            dados_operadora,
            "equipamento",
        )
        _render_ranking_drill_down_os(
            resumo_equipamentos,
            "equipamento",
            "Equipamento",
            f"Nível 2: OS por equipamento — {operadora}",
            "os_drill_down_equipamentos_chart",
            permitir_selecao=False,
        )


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

    # Otimização: Usar f-string vetorizado ao invés de .apply()
    manutencao_operadora["rotulo_manutencao"] = (
        manutencao_operadora["quantidade_manutencao"].astype(str) + " (" +
        manutencao_operadora["percentual_manutencao_frota"].round(2).astype(str) + "%)"
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
    periodo_grafico = _formatar_periodo_grafico(
        equipamentos_operadora["competencia_inicio"].min(),
        equipamentos_operadora["competencia_fim"].max(),
    )

    # Otimização: Usar apply sem lambda complexa (formato pré-calculado em apply simples)
    equipamentos_operadora["periodo_segmento"] = equipamentos_operadora.apply(
        lambda row: _formatar_periodo_grafico(
            row["competencia_inicio"],
            row["competencia_fim"],
        ),
        axis=1,
    )

    fig_equipamentos = px.bar(
        equipamentos_operadora,
        x="quantidade_manutencao",
        y="operadora",
        color="equipamento",
        orientation="h",
        title=(
            "MANUTENÇÃO POR EQUIPAMENTO E OPERADORA"
            f" - {periodo_grafico} | base_historica_manutencao"
        ),
        text="quantidade_manutencao",
        color_discrete_sequence=CORES_EQUIPAMENTOS,
        category_orders={
            "operadora": ordem_operadoras,
            "equipamento": ordem_equipamentos,
        },
        custom_data=["equipamento", "total_operadora", "periodo_segmento"],
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
            "Total manutenção operadora=%{customdata[1]:.0f}<br>"
            "Período=%{customdata[2]}<br>"
            "Origem=base_historica_manutencao<extra></extra>"
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
    df_evolucao_mensal_periodo: pd.DataFrame,
    df_manutencao_contrato: pd.DataFrame,
    df_equipamentos_contrato: pd.DataFrame,
    df_servicos_resumo: pd.DataFrame | None = None,
    df_manutencao_operadora: pd.DataFrame | None = None,
) -> None:
    if df_evolucao_mensal.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    col_top_1, col_top_2 = st.columns(2)

    with col_top_1, st.container(border=True):
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

    with col_top_2, st.container(border=True):
        if df_servicos_resumo is None:
            st.info("Sem dados de serviços executados por tipo.")
        else:
            render_servicos_executados_chart(
                df_servicos_resumo,
                usar_container=False,
            )

    col_manutencao_1, col_manutencao_2 = st.columns(2)

    with col_manutencao_1, st.container(border=True):
        _render_manutencao_por_categoria_chart(
            df_manutencao_contrato,
            "contrato",
            "Contrato",
            "EQUIPAMENTOS EM MANUTENÇÃO POR CONTRATO",
            "Sem dados de manutenção por contrato para os filtros selecionados.",
        )

    with col_manutencao_2, st.container(border=True):
        _render_manutencao_operadora_chart(df_manutencao_operadora)

    with st.container(border=True):
        if df_evolucao_mensal_periodo.empty:
            st.info("Sem dados mensais para o período selecionado.")
        else:
            manutencao_mensal = df_evolucao_mensal_periodo.sort_values("mes").copy()
            manutencao_mensal["mes_label"] = manutencao_mensal["mes"].apply(
                _formatar_mes_curto
            )
            ordem_meses_periodo = manutencao_mensal["mes_label"].tolist()
            fig_mensal = px.bar(
                manutencao_mensal,
                x="mes_label",
                y="total_qtd",
                title="COMPORTAMENTO MENSAL DA MANUTENÇÃO NO PERÍODO FILTRADO",
                text="total_qtd",
                color="total_qtd",
                color_continuous_scale=ESCALA_RANKING,
                category_orders={"mes_label": ordem_meses_periodo},
                labels={
                    "mes_label": "Mês",
                    "total_qtd": "Quantidade em manutenção",
                    "total_frota": "Frota",
                    "percentual_qtd_x_frota": "% da frota",
                },
                hover_data={
                    "mes_label": False,
                    "mes": "|%m/%Y",
                    "total_qtd": ":.0f",
                    "total_frota": ":.0f",
                    "percentual_qtd_x_frota": ":.2f",
                },
            )
            fig_mensal.update_xaxes(
                type="category",
                categoryorder="array",
                categoryarray=ordem_meses_periodo,
            )
            _mostrar_rotulos_barras(fig_mensal, "%{text:.0f}")
            fig_mensal.update_coloraxes(showscale=False)
            limite_y_mensal = max(5, manutencao_mensal["total_qtd"].max() * 1.18)
            fig_mensal.update_yaxes(range=[0, limite_y_mensal])
            st.plotly_chart(_estilizar_figura(fig_mensal), use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">Gráficos anuais e variáveis</div>',
        unsafe_allow_html=True,
    )

    col_anual_1, col_anual_2 = st.columns(2)

    with col_anual_1, st.container(border=True):
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

    with col_anual_2, st.container(border=True):
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

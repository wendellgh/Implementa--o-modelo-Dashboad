import base64
import html
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard.auth import encerrar_sessao, obter_usuario_logado, usuario_eh_admin
from dashboard.config import MENU_ITEMS
from dashboard.database import get_db_target_info
from dashboard.styles import (
    TEMA_CLARO_ATIVO_KEY,
    tema_claro_ativo,
)

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
SIDEBAR_LOGO_PATH = ASSETS_DIR / "tacom.svg"
ENTRADA_DADOS_MENU_ITEM = "Entrada de Dados"
ORACLE_DESTBOAD_MENU_ITEM = "Dados da Manutenção - Oracle"
PAGINA_ATUAL_KEY = "pagina_atual"
FILTRO_MES_INICIO_KEY = "filtro_mes_inicio"
FILTRO_MES_FIM_KEY = "filtro_mes_fim"
FILTRO_CONTRATO_KEY = "filtro_contrato"
FILTRO_OPERADORA_KEY = "filtro_operadora"
FILTRO_EQUIPAMENTO_KEY = "filtro_equipamento"

MENU_ICONS = {
    "Dashboard": ":material/dashboard:",
    "Resumo": ":material/analytics:",
    "Tabela": ":material/table:",
    "Contando Frota - Teste": ":material/query_stats:",
    "Contando Frota.": ":material/query_stats:",
    "Serviços Executados - Teste": ":material/build:",
    "ServiÃ§os Executados - Teste": ":material/build:",
    ORACLE_DESTBOAD_MENU_ITEM: ":material/database:",
    ENTRADA_DADOS_MENU_ITEM: ":material/edit_note:",
}

NAVIGATION_GROUPS = (
    (
        "Entrada de Dados",
        (
            ("Inserir dados da manutenção", ENTRADA_DADOS_MENU_ITEM),
            ("Dados da Manutenção - Oracle", ORACLE_DESTBOAD_MENU_ITEM),
        ),
    ),
    (
        "Dashboard",
        (
            ("Resumo", "Dashboard"),
            ("Análise por equipamento", "Resumo"),
            ("Tabela", "Tabela"),
            ("Contando Frota", "Contando Frota - Teste"),
            ("Serviços executados", "Serviços Executados - Teste"),
        ),
    ),
)


def _obter_paginas_navegacao() -> list[str]:
    paginas = [
        pagina
        for _, itens in NAVIGATION_GROUPS
        for _, pagina in itens
    ]
    paginas.extend([ENTRADA_DADOS_MENU_ITEM, *MENU_ITEMS])
    return list(dict.fromkeys(paginas))


def _render_navegacao() -> str:
    paginas = _obter_paginas_navegacao()
    pagina_padrao = "Dashboard" if "Dashboard" in paginas else paginas[0]
    st.session_state.setdefault(PAGINA_ATUAL_KEY, pagina_padrao)
    pagina_atual = str(st.session_state[PAGINA_ATUAL_KEY])
    if pagina_atual not in paginas:
        pagina_atual = pagina_padrao
    if pagina_atual == ORACLE_DESTBOAD_MENU_ITEM and not usuario_eh_admin():
        pagina_atual = "Dashboard" if "Dashboard" in paginas else paginas[0]

    pagina_selecionada = pagina_atual
    for indice_grupo, (grupo, itens) in enumerate(NAVIGATION_GROUPS):
        paginas_grupo = [pagina for _, pagina in itens]
        with st.expander(grupo, expanded=pagina_atual in paginas_grupo):
            for indice_item, (rotulo, pagina) in enumerate(itens):
                oracle_bloqueado = (
                    pagina == ORACLE_DESTBOAD_MENU_ITEM and not usuario_eh_admin()
                )
                clicou = st.button(
                    rotulo,
                    key=f"botao_pagina_{indice_grupo}_{indice_item}",
                    type="primary" if pagina == pagina_atual else "secondary",
                    icon=MENU_ICONS.get(pagina),
                    width="stretch",
                    disabled=oracle_bloqueado,
                )
                if oracle_bloqueado:
                    st.caption("Disponivel apenas para administradores.")
                if clicou:
                    pagina_selecionada = pagina

    st.session_state[PAGINA_ATUAL_KEY] = pagina_selecionada

    return str(st.session_state[PAGINA_ATUAL_KEY])


def _render_sidebar_logo() -> None:
    if not SIDEBAR_LOGO_PATH.exists():
        return

    svg_texto = SIDEBAR_LOGO_PATH.read_text(encoding="utf-8")
    if tema_claro_ativo():
        svg_texto = svg_texto.replace("#FFFFFF", "#1f2937")

    svg_base64 = base64.b64encode(svg_texto.encode("utf-8")).decode("utf-8")
    st.markdown(
        (
            '<div class="sidebar-logo">'
            f'<img src="data:image/svg+xml;base64,{svg_base64}" '
            'alt="Tacom" />'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_database_target() -> None:
    info = get_db_target_info()
    st.markdown(
        f"""
        <div class="db-target-badge db-target-{info['kind']}">
            <span class="db-target-dot" aria-hidden="true"></span>
            <span class="db-target-copy">
                <span class="db-target-title">{html.escape(info['title'])}</span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_tema_visual() -> None:
    if TEMA_CLARO_ATIVO_KEY not in st.session_state:
        st.session_state[TEMA_CLARO_ATIVO_KEY] = tema_claro_ativo()

    st.toggle("Tema claro", key=TEMA_CLARO_ATIVO_KEY)


def _eh_pagina_servicos_executados(menu: str) -> bool:
    return "Executados" in menu and menu.startswith("Servi")


def _obter_base_para_filtros(menu: str, df_base: pd.DataFrame) -> pd.DataFrame:
    if not _eh_pagina_servicos_executados(menu):
        return df_base

    try:
        from dashboard.data import carregar_base_outra_tabela

        df_servicos = carregar_base_outra_tabela()
    except Exception as erro:
        st.warning(f"Erro ao carregar filtros de servicos_executados: {erro}")
        return df_base

    if df_servicos.empty:
        return df_base

    return df_servicos


def _obter_coluna_periodo(df_base: pd.DataFrame) -> str:
    if "data_competencia" in df_base.columns:
        return "data_competencia"
    return "data_ref"


def _render_usuario_logado() -> None:
    usuario_logado = obter_usuario_logado()
    if not usuario_logado:
        return

    nome = html.escape(str(usuario_logado.get("nome") or usuario_logado.get("usuario") or "Usuario"))
    perfil = html.escape(str(usuario_logado.get("perfil") or ""))
    prioridade = html.escape(str(usuario_logado.get("prioridade") or ""))

    st.markdown(
        f"""
        <div class="user-session-badge">
            <span class="user-session-name">{nome}</span>
            <span class="user-session-role">Perfil: {perfil} | Prioridade: {prioridade}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Sair", icon=":material/logout:", width="stretch"):
        encerrar_sessao()
        st.rerun()


def _formatar_mes(data_mes: pd.Timestamp) -> str:
    meses_pt = {
        1: "JANEIRO",
        2: "FEVEREIRO",
        3: "MARCO",
        4: "ABRIL",
        5: "MAIO",
        6: "JUNHO",
        7: "JULHO",
        8: "AGOSTO",
        9: "SETEMBRO",
        10: "OUTUBRO",
        11: "NOVEMBRO",
        12: "DEZEMBRO",
    }
    return f"{meses_pt[data_mes.month]}/{data_mes:%y}"


def _criar_opcoes_mensais(data_min: date, data_max: date) -> list[pd.Timestamp]:
    mes_min = pd.Timestamp(data_min).to_period("M").to_timestamp()
    mes_max = pd.Timestamp(data_max).to_period("M").to_timestamp()
    return list(pd.date_range(mes_min, mes_max, freq="MS"))


def _obter_periodo_padrao(meses: list[pd.Timestamp]) -> tuple[pd.Timestamp, pd.Timestamp]:
    mes_anterior = (
        pd.Timestamp(date.today()).to_period("M").to_timestamp()
        - pd.DateOffset(months=1)
    )
    mes_padrao = next((mes for mes in reversed(meses) if mes <= mes_anterior), None)
    if mes_padrao is None:
        mes_padrao = meses[0]

    return mes_padrao, mes_padrao


def _indice_mes(meses: list[pd.Timestamp], mes_procurado: pd.Timestamp) -> int:
    for indice, mes in enumerate(meses):
        if mes == mes_procurado:
            return indice
    return 0


def _normalizar_mes_sessao(
    chave: str,
    meses: list[pd.Timestamp],
    mes_padrao: pd.Timestamp,
) -> pd.Timestamp:
    if chave not in st.session_state:
        return mes_padrao

    valor = st.session_state.get(chave, mes_padrao)
    try:
        mes = pd.Timestamp(valor).to_period("M").to_timestamp()
    except (TypeError, ValueError):
        mes = mes_padrao

    if mes not in meses:
        mes = mes_padrao
        st.session_state[chave] = mes

    return mes


def _normalizar_multiselect_sessao(chave: str, opcoes: list[object]) -> None:
    if chave not in st.session_state:
        return

    valores = st.session_state.get(chave, [])
    if not isinstance(valores, list):
        valores = []

    opcoes_set = set(opcoes)
    valores_validos = [valor for valor in valores if valor in opcoes_set]
    if valores_validos != valores:
        st.session_state[chave] = valores_validos


def render_sidebar(df_base: pd.DataFrame) -> str:
    with st.sidebar:
        _render_sidebar_logo()
        _render_usuario_logado()
        _render_database_target()
        _render_tema_visual()
        st.markdown("### Navegação")
        menu = _render_navegacao()

    return menu


def render_filtros(df_base: pd.DataFrame, menu: str) -> dict[str, object]:
    df_filtros = _obter_base_para_filtros(menu, df_base)
    coluna_periodo = _obter_coluna_periodo(df_filtros)

    data_valida = pd.to_datetime(df_filtros[coluna_periodo], errors="coerce").dropna()
    if data_valida.empty:
        data_min = date.today()
        data_max = date.today()
    else:
        data_min = data_valida.min().date()
        data_max = data_valida.max().date()

    meses_disponiveis = _criar_opcoes_mensais(data_min, data_max)
    periodo_padrao = _obter_periodo_padrao(meses_disponiveis)

    with st.container(border=True):
        st.markdown(
            '<div class="filters-title">Filtros aplicados</div>',
            unsafe_allow_html=True,
        )
        col_inicio, col_fim, col_contrato, col_operadora, col_equipamento = st.columns(
            [0.9, 0.9, 1.35, 1.35, 1.35],
        )
        with col_inicio:
            inicio_sessao = _normalizar_mes_sessao(
                FILTRO_MES_INICIO_KEY,
                meses_disponiveis,
                periodo_padrao[0],
            )
            mes_inicio = st.selectbox(
                "Mes inicial",
                options=meses_disponiveis,
                index=_indice_mes(meses_disponiveis, inicio_sessao),
                format_func=_formatar_mes,
                key=FILTRO_MES_INICIO_KEY,
            )
        with col_fim:
            meses_finais = [mes for mes in meses_disponiveis if mes >= mes_inicio]
            fim_padrao = (
                periodo_padrao[1]
                if periodo_padrao[1] >= mes_inicio
                else mes_inicio
            )
            fim_sessao = _normalizar_mes_sessao(
                FILTRO_MES_FIM_KEY,
                meses_finais,
                fim_padrao,
            )
            mes_fim = st.selectbox(
                "Mes final",
                options=meses_finais,
                index=_indice_mes(meses_finais, fim_sessao),
                format_func=_formatar_mes,
                key=FILTRO_MES_FIM_KEY,
            )

        inicio_mes = pd.Timestamp(mes_inicio)
        fim_mes = pd.Timestamp(mes_fim) + pd.offsets.MonthEnd(0)
        periodo = (inicio_mes, fim_mes)

        contratos = sorted(
            [x for x in df_filtros["contrato"].dropna().unique().tolist() if x]
        )
        operadoras = sorted(
            [x for x in df_filtros["operadora"].dropna().unique().tolist() if x]
        )
        equipamentos = sorted(
            [x for x in df_filtros["equipamento"].dropna().unique().tolist() if x]
        )

        _normalizar_multiselect_sessao(FILTRO_CONTRATO_KEY, contratos)
        _normalizar_multiselect_sessao(FILTRO_OPERADORA_KEY, operadoras)
        _normalizar_multiselect_sessao(FILTRO_EQUIPAMENTO_KEY, equipamentos)

        with col_contrato:
            filtro_contrato = st.multiselect(
                "Contrato",
                contratos,
                placeholder="Selecione os contratos",
                key=FILTRO_CONTRATO_KEY,
            )
        with col_operadora:
            filtro_operadora = st.multiselect(
                "Operadora",
                operadoras,
                placeholder="Selecione as operadoras",
                key=FILTRO_OPERADORA_KEY,
            )
        with col_equipamento:
            filtro_equipamento = st.multiselect(
                "Equipamento",
                equipamentos,
                placeholder="Selecione os equipamentos",
                key=FILTRO_EQUIPAMENTO_KEY,
            )

    return {
        "menu": menu,
        "periodo": periodo,
        "filtro_contrato": filtro_contrato,
        "filtro_operadora": filtro_operadora,
        "filtro_equipamento": filtro_equipamento,
    }


def aplicar_filtros(df_base: pd.DataFrame, filtros: dict[str, object]) -> pd.DataFrame:
    df_filtrado = df_base.copy()
    coluna_periodo = _obter_coluna_periodo(df_filtrado)

    periodo = filtros.get("periodo")
    if isinstance(periodo, tuple) and len(periodo) == 2:
        inicio = pd.to_datetime(periodo[0])
        fim = pd.to_datetime(periodo[1])
        df_filtrado = df_filtrado[
            (df_filtrado[coluna_periodo] >= inicio)
            & (df_filtrado[coluna_periodo] <= fim)
        ]
    elif isinstance(periodo, date):
        dia = pd.to_datetime(periodo)
        df_filtrado = df_filtrado[df_filtrado[coluna_periodo] == dia]

    filtro_contrato = filtros.get("filtro_contrato", [])
    if filtro_contrato:
        df_filtrado = df_filtrado[df_filtrado["contrato"].isin(filtro_contrato)]

    filtro_operadora = filtros.get("filtro_operadora", [])
    if filtro_operadora:
        df_filtrado = df_filtrado[df_filtrado["operadora"].isin(filtro_operadora)]

    filtro_equipamento = filtros.get("filtro_equipamento", [])
    if filtro_equipamento:
        df_filtrado = df_filtrado[df_filtrado["equipamento"].isin(filtro_equipamento)]

    return df_filtrado

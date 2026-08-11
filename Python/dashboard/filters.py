import base64
import html
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from dashboard.auth import encerrar_sessao, obter_usuario_logado, usuario_eh_admin
from dashboard.config import MENU_ITEMS
from dashboard.database import get_db_target_info
from dashboard.styles import (
    TEMA_CLARO_ATIVO_KEY,
    tema_claro_ativo,
)
from dashboard.utils_otimizacoes import (
    formatar_mes,
    normalizar_coluna_texto,
)

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
FUSO_HORARIO_APLICACAO = ZoneInfo("America/Sao_Paulo")
SIDEBAR_LOGO_PATH = ASSETS_DIR / "tacom.svg"
ENTRADA_DADOS_MENU_ITEM = "Entrada de Dados"
MANUTENCAO_FILIAL_MENU_ITEM = "Manutenção Filial"
ORACLE_DESTBOAD_MENU_ITEM = "Dados da Manutenção - Oracle"
ANALISE_FALHAS_MENU_ITEM = "Análise de Falhas"
PAGINA_ATUAL_KEY = "pagina_atual"
FILTRO_MES_INICIO_KEY = "filtro_mes_inicio"
FILTRO_MES_FIM_KEY = "filtro_mes_fim"
FILTRO_CONTRATO_KEY = "filtro_contrato"
FILTRO_OPERADORA_KEY = "filtro_operadora"
FILTRO_EQUIPAMENTO_KEY = "filtro_equipamento"
FILTRO_COORDENACAO_KEY = "filtro_coordenacao"
FILTRO_PRACA_KEY = "filtro_praca"
ULTIMO_FILTRO_ALTERADO_KEY = "ultimo_filtro_alterado"

FILTROS_ENCADEADOS = (
    (FILTRO_COORDENACAO_KEY, "coordenacao"),
    (FILTRO_PRACA_KEY, "praca"),
    (FILTRO_CONTRATO_KEY, "contrato"),
    (FILTRO_OPERADORA_KEY, "operadora"),
    (FILTRO_EQUIPAMENTO_KEY, "equipamento"),
)

MENU_ICONS = {
    "Dashboard": ":material/dashboard:",
    "Resumo": ":material/analytics:",
    "Análise por Operadora": ":material/bar_chart:",
    "Tabela": ":material/table:",
    "Contando Frota - Teste": ":material/query_stats:",
    "Contando Frota.": ":material/query_stats:",
    "Serviços Executados - Teste": ":material/build:",
    "ServiÃ§os Executados - Teste": ":material/build:",
    ANALISE_FALHAS_MENU_ITEM: ":material/rule:",
    ORACLE_DESTBOAD_MENU_ITEM: ":material/database:",
    ENTRADA_DADOS_MENU_ITEM: ":material/edit_note:",
    MANUTENCAO_FILIAL_MENU_ITEM: ":material/edit_note:",
}

NAVIGATION_GROUPS = (
    (
        "Entrada de Dados",
        (
            ("Inserir dados da manutenção", ENTRADA_DADOS_MENU_ITEM),
            ("Manutenção Filial", MANUTENCAO_FILIAL_MENU_ITEM),
            ("Dados da Manutenção - Oracle", ORACLE_DESTBOAD_MENU_ITEM),
        ),
    ),
    (
        "Dashboard",
        (
            ("Resumo", "Dashboard"),
            ("Análise por equipamento", "Resumo"),
            ("Análise por operadora", "Análise por Operadora"),
            ("Tabela", "Tabela"),
            ("Contando Frota", "Contando Frota - Teste"),
            ("Serviços executados", "Serviços Executados - Teste"),
            ("Análise de falhas", ANALISE_FALHAS_MENU_ITEM),
        ),
    ),
)


def _obter_paginas_navegacao() -> list[str]:
    paginas = [
        pagina
        for _, itens in NAVIGATION_GROUPS
        for _, pagina in itens
    ]
    paginas.extend([ENTRADA_DADOS_MENU_ITEM, MANUTENCAO_FILIAL_MENU_ITEM, *MENU_ITEMS])
    return list(dict.fromkeys(paginas))


def _selecionar_pagina(pagina: str) -> None:
    st.session_state[PAGINA_ATUAL_KEY] = pagina


def _render_navegacao() -> str:
    paginas = _obter_paginas_navegacao()
    pagina_padrao = "Dashboard" if "Dashboard" in paginas else paginas[0]
    st.session_state.setdefault(PAGINA_ATUAL_KEY, pagina_padrao)
    pagina_atual = str(st.session_state[PAGINA_ATUAL_KEY])
    if pagina_atual not in paginas:
        pagina_atual = pagina_padrao
    if pagina_atual == ORACLE_DESTBOAD_MENU_ITEM and not usuario_eh_admin():
        pagina_atual = "Dashboard" if "Dashboard" in paginas else paginas[0]

    st.session_state[PAGINA_ATUAL_KEY] = pagina_atual

    for indice_grupo, (grupo, itens) in enumerate(NAVIGATION_GROUPS):
        paginas_grupo = [pagina for _, pagina in itens]
        with st.expander(grupo, expanded=pagina_atual in paginas_grupo):
            for indice_item, (rotulo, pagina) in enumerate(itens):
                oracle_bloqueado = (
                    pagina == ORACLE_DESTBOAD_MENU_ITEM and not usuario_eh_admin()
                )
                st.button(
                    rotulo,
                    key=f"botao_pagina_{indice_grupo}_{indice_item}",
                    type="primary" if pagina == pagina_atual else "secondary",
                    icon=MENU_ICONS.get(pagina),
                    width="stretch",
                    disabled=oracle_bloqueado,
                    on_click=_selecionar_pagina,
                    args=(pagina,),
                )
                if oracle_bloqueado:
                    st.caption("Disponivel apenas para administradores.")

    return str(st.session_state[PAGINA_ATUAL_KEY])


def _detectar_mime_imagem(conteudo: bytes) -> str:
    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if conteudo.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if conteudo.startswith(b"RIFF") and conteudo[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def _preparar_logo_data_uri(caminho: Path) -> tuple[str, str]:
    conteudo = caminho.read_bytes()

    try:
        texto = conteudo.decode("utf-8")
    except UnicodeDecodeError:
        mime = _detectar_mime_imagem(conteudo)
        return mime, base64.b64encode(conteudo).decode("ascii")

    if "<svg" in texto[:500].lower():
        if tema_claro_ativo():
            texto = texto.replace("#FFFFFF", "#1f2937")
        conteudo = texto.encode("utf-8")
        return "image/svg+xml", base64.b64encode(conteudo).decode("ascii")

    mime = _detectar_mime_imagem(conteudo)
    return mime, base64.b64encode(conteudo).decode("ascii")


def _render_sidebar_logo() -> None:
    if not SIDEBAR_LOGO_PATH.exists():
        return

    mime, logo_base64 = _preparar_logo_data_uri(SIDEBAR_LOGO_PATH)
    st.markdown(
        (
            '<div class="sidebar-logo">'
            f'<img src="data:{mime};base64,{logo_base64}" '
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
    # Mantem os filtros principais disponiveis se a fonte secundaria falhar.
    except Exception as erro:  # noqa: BLE001
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
    st.button(
        "Sair",
        icon=":material/logout:",
        width="stretch",
        on_click=encerrar_sessao,
    )


def _formatar_mes(data_mes: pd.Timestamp) -> str:
    """Formata mês em português (formato longo). Consolidado em utils_otimizacoes."""
    return formatar_mes(data_mes, formato="longo")


def _criar_opcoes_mensais(data_min: date, data_max: date) -> list[pd.Timestamp]:
    mes_min = pd.Timestamp(data_min).to_period("M").to_timestamp()
    mes_max = pd.Timestamp(data_max).to_period("M").to_timestamp()
    return list(pd.date_range(mes_min, mes_max, freq="MS"))


def _obter_periodo_padrao(
    meses: list[pd.Timestamp],
    *,
    usar_mes_atual: bool = False,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    data_atual = datetime.now(FUSO_HORARIO_APLICACAO).date()
    mes_atual = pd.Timestamp(data_atual).to_period("M").to_timestamp()
    mes_limite = mes_atual if usar_mes_atual else mes_atual - pd.DateOffset(months=1)
    mes_padrao = next((mes for mes in reversed(meses) if mes <= mes_limite), None)
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


def _registrar_filtro_alterado(chave: str) -> None:
    st.session_state[ULTIMO_FILTRO_ALTERADO_KEY] = chave


def _valores_multiselect_sessao(chave: str) -> list[object]:
    valores = st.session_state.get(chave, [])
    if not isinstance(valores, list):
        return []
    return valores


def _opcoes_texto(df: pd.DataFrame, coluna: str) -> list[str]:
    if coluna not in df.columns:
        return []

    return sorted(
        [
            valor
            for valor in df[coluna].fillna("").astype(str).str.strip().unique().tolist()
            if valor
        ]
    )


def _rotulos_praca(df: pd.DataFrame) -> dict[str, str]:
    """Cria dicionário de rótulos praça → nome_praca (otimizado - sem .iterrows)."""
    if "praca" not in df.columns:
        return {}

    if "nome_praca" not in df.columns:
        return {praca: praca for praca in _opcoes_texto(df, "praca")}

    # Otimização: Vetorizado ao invés de .iterrows()
    df_clean = df[["praca", "nome_praca"]].drop_duplicates().copy()
    df_clean["praca"] = normalizar_coluna_texto(df_clean["praca"])
    df_clean["nome_praca"] = normalizar_coluna_texto(df_clean["nome_praca"])

    rotulos: dict[str, str] = {}
    for praca, nome_praca in zip(df_clean["praca"], df_clean["nome_praca"]):
        if not praca:
            continue
        rotulos[praca] = (
            f"{praca} - {nome_praca}"
            if nome_praca and nome_praca != praca
            else praca
        )

    return rotulos


def _obter_dimensao_pracas() -> pd.DataFrame:
    try:
        from dashboard.data import carregar_dimensao_pracas_servicos

        return carregar_dimensao_pracas_servicos()
    # Mantem os filtros disponiveis se a dimensao de pracas falhar.
    except Exception as erro:  # noqa: BLE001
        st.warning(f"Erro ao carregar filtros de praça: {erro}")
        return pd.DataFrame(columns=["praca", "nome_praca", "coordenacao"])


def _montar_fonte_pracas(df_filtros: pd.DataFrame) -> pd.DataFrame:
    fontes: list[pd.DataFrame] = []

    colunas_praca = [
        coluna
        for coluna in ["praca", "nome_praca", "coordenacao"]
        if coluna in df_filtros.columns
    ]
    if colunas_praca:
        fonte_atual = df_filtros[colunas_praca].copy()
        for coluna in ["praca", "nome_praca", "coordenacao"]:
            if coluna not in fonte_atual.columns:
                fonte_atual[coluna] = ""
        fontes.append(fonte_atual[["praca", "nome_praca", "coordenacao"]])

    dimensao_pracas = _obter_dimensao_pracas()
    if not dimensao_pracas.empty:
        fontes.append(dimensao_pracas[["praca", "nome_praca", "coordenacao"]])

    if not fontes:
        return pd.DataFrame(columns=["praca", "nome_praca", "coordenacao"])

    fonte = pd.concat(fontes, ignore_index=True)
    for coluna in ["praca", "nome_praca", "coordenacao"]:
        fonte[coluna] = fonte[coluna].fillna("").astype(str).str.strip()

    return fonte.drop_duplicates().reset_index(drop=True)


def _preparar_base_opcoes(df_filtros: pd.DataFrame) -> pd.DataFrame:
    colunas = ["coordenacao", "praca", "nome_praca", "contrato", "operadora", "equipamento"]
    df_opcoes = df_filtros.copy()

    if "praca" not in df_opcoes.columns and "coordenacao" not in df_opcoes.columns:
        dimensao_pracas = _montar_fonte_pracas(df_filtros)
        if not dimensao_pracas.empty:
            df_opcoes = dimensao_pracas.copy()

    for coluna in colunas:
        if coluna not in df_opcoes.columns:
            df_opcoes[coluna] = ""
        df_opcoes[coluna] = df_opcoes[coluna].fillna("").astype(str).str.strip()

    return df_opcoes


def _filtrar_base_opcoes_por_periodo(
    df_opcoes: pd.DataFrame,
    periodo: tuple[pd.Timestamp, pd.Timestamp],
) -> pd.DataFrame:
    coluna_periodo = _obter_coluna_periodo(df_opcoes)
    if coluna_periodo not in df_opcoes.columns:
        return df_opcoes

    inicio, fim = periodo
    datas = pd.to_datetime(df_opcoes[coluna_periodo], errors="coerce")
    return df_opcoes[datas.between(inicio, fim)].copy()


def _selecoes_multiselect_sessao() -> dict[str, list[object]]:
    return {
        chave: _valores_multiselect_sessao(chave)
        for chave, _ in FILTROS_ENCADEADOS
    }


def _aplicar_selecoes_opcoes(
    df_opcoes: pd.DataFrame,
    selecoes: dict[str, list[object]],
    *,
    ignorar_chave: str | None = None,
) -> pd.DataFrame:
    filtrado = df_opcoes
    for chave, coluna in FILTROS_ENCADEADOS:
        if chave == ignorar_chave or coluna not in filtrado.columns:
            continue

        valores = selecoes.get(chave, [])
        if valores:
            filtrado = filtrado[filtrado[coluna].isin(valores)]

    return filtrado


def _opcoes_encadeadas(
    df_opcoes: pd.DataFrame,
    selecoes: dict[str, list[object]],
    chave_opcoes: str,
) -> list[str]:
    coluna = dict(FILTROS_ENCADEADOS)[chave_opcoes]
    filtrado = _aplicar_selecoes_opcoes(
        df_opcoes,
        selecoes,
        ignorar_chave=chave_opcoes,
    )
    return _opcoes_texto(filtrado, coluna)


def _normalizar_selecoes_encadeadas(
    df_opcoes: pd.DataFrame,
    selecoes: dict[str, list[object]],
) -> dict[str, list[object]]:
    chaves = [chave for chave, _ in FILTROS_ENCADEADOS]
    chave_prioritaria = st.session_state.get(ULTIMO_FILTRO_ALTERADO_KEY)
    ordem = [chave for chave in chaves if chave != chave_prioritaria]
    if chave_prioritaria in chaves:
        ordem.append(chave_prioritaria)

    for chave in ordem:
        opcoes = _opcoes_encadeadas(df_opcoes, selecoes, chave)
        opcoes_set = set(opcoes)
        valores = selecoes.get(chave, [])
        valores_validos = [valor for valor in valores if valor in opcoes_set]
        if valores_validos != valores:
            st.session_state[chave] = valores_validos
            selecoes[chave] = valores_validos

    return selecoes


def _montar_opcoes_encadeadas(
    df_opcoes: pd.DataFrame,
    selecoes: dict[str, list[object]],
) -> dict[str, list[str]]:
    return {
        chave: _opcoes_encadeadas(df_opcoes, selecoes, chave)
        for chave, _ in FILTROS_ENCADEADOS
    }


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
        data_min = datetime.now(FUSO_HORARIO_APLICACAO).date()
        data_max = data_min
    else:
        data_min = data_valida.min().date()
        data_max = data_valida.max().date()

    meses_disponiveis = _criar_opcoes_mensais(data_min, data_max)
    periodo_padrao = _obter_periodo_padrao(
        meses_disponiveis,
        usar_mes_atual=_eh_pagina_servicos_executados(menu),
    )

    with st.container(border=True):
        st.markdown(
            '<div class="filters-title">Filtros aplicados</div>',
            unsafe_allow_html=True,
        )
        col_inicio, col_fim, _ = st.columns([0.95, 0.95, 3.6])
        with col_inicio:
            inicio_sessao = _normalizar_mes_sessao(
                FILTRO_MES_INICIO_KEY,
                meses_disponiveis,
                periodo_padrao[0],
            )
            mes_inicio = st.selectbox(
                "Inicio",
                options=meses_disponiveis,
                index=_indice_mes(meses_disponiveis, inicio_sessao),
                format_func=_formatar_mes,
                key=FILTRO_MES_INICIO_KEY,
            )
        with col_fim:
            meses_finais = [mes for mes in meses_disponiveis if mes >= mes_inicio]
            fim_padrao = max(periodo_padrao[1], mes_inicio)
            fim_sessao = _normalizar_mes_sessao(
                FILTRO_MES_FIM_KEY,
                meses_finais,
                fim_padrao,
            )
            mes_fim = st.selectbox(
                "Fim",
                options=meses_finais,
                index=_indice_mes(meses_finais, fim_sessao),
                format_func=_formatar_mes,
                key=FILTRO_MES_FIM_KEY,
            )

        inicio_mes = pd.Timestamp(mes_inicio)
        fim_mes = pd.Timestamp(mes_fim) + pd.offsets.MonthEnd(0)
        periodo = (inicio_mes, fim_mes)

        df_opcoes = _preparar_base_opcoes(df_filtros)
        df_opcoes = _filtrar_base_opcoes_por_periodo(df_opcoes, periodo)
        selecoes = _selecoes_multiselect_sessao()
        selecoes = _normalizar_selecoes_encadeadas(df_opcoes, selecoes)
        opcoes = _montar_opcoes_encadeadas(df_opcoes, selecoes)

        st.write("")
        (
            col_coordenacao,
            col_praca,
            col_contrato,
            col_operadora,
            col_equipamento,
        ) = st.columns([1.05, 1.2, 1.35, 1.35, 1.35])

        with col_coordenacao:
            filtro_coordenacao = st.multiselect(
                "Coord.",
                opcoes[FILTRO_COORDENACAO_KEY],
                placeholder="Todas",
                key=FILTRO_COORDENACAO_KEY,
                on_change=_registrar_filtro_alterado,
                args=(FILTRO_COORDENACAO_KEY,),
            )

        df_rotulos_praca = _aplicar_selecoes_opcoes(
            df_opcoes,
            selecoes,
            ignorar_chave=FILTRO_PRACA_KEY,
        )
        rotulos_praca = _rotulos_praca(df_rotulos_praca)

        with col_praca:
            filtro_praca = st.multiselect(
                "Praca",
                opcoes[FILTRO_PRACA_KEY],
                format_func=lambda praca: rotulos_praca.get(str(praca), str(praca)),
                placeholder="Todas",
                key=FILTRO_PRACA_KEY,
                on_change=_registrar_filtro_alterado,
                args=(FILTRO_PRACA_KEY,),
            )

        with col_contrato:
            filtro_contrato = st.multiselect(
                "Contrato",
                opcoes[FILTRO_CONTRATO_KEY],
                placeholder="Todos",
                key=FILTRO_CONTRATO_KEY,
                on_change=_registrar_filtro_alterado,
                args=(FILTRO_CONTRATO_KEY,),
            )
        with col_operadora:
            filtro_operadora = st.multiselect(
                "Operadora",
                opcoes[FILTRO_OPERADORA_KEY],
                placeholder="Todas",
                key=FILTRO_OPERADORA_KEY,
                on_change=_registrar_filtro_alterado,
                args=(FILTRO_OPERADORA_KEY,),
            )
        with col_equipamento:
            filtro_equipamento = st.multiselect(
                "Equip.",
                opcoes[FILTRO_EQUIPAMENTO_KEY],
                placeholder="Todos",
                key=FILTRO_EQUIPAMENTO_KEY,
                on_change=_registrar_filtro_alterado,
                args=(FILTRO_EQUIPAMENTO_KEY,),
            )

    return {
        "menu": menu,
        "periodo": periodo,
        "filtro_contrato": filtro_contrato,
        "filtro_operadora": filtro_operadora,
        "filtro_equipamento": filtro_equipamento,
        "filtro_coordenacao": filtro_coordenacao,
        "filtro_praca": filtro_praca,
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

    filtro_coordenacao = filtros.get("filtro_coordenacao", [])
    if filtro_coordenacao and "coordenacao" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["coordenacao"].isin(filtro_coordenacao)]

    filtro_praca = filtros.get("filtro_praca", [])
    if filtro_praca and "praca" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["praca"].isin(filtro_praca)]

    return df_filtrado

import base64
import html
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard.config import MENU_ITEMS
from dashboard.database import get_db_target_info

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
SIDEBAR_LOGO_PATH = ASSETS_DIR / "tacom.svg"
DATA_INICIO_PADRAO = date(2026, 1, 1)
ENTRADA_DADOS_MENU_ITEM = "Entrada de Dados"
PAGINA_ATUAL_KEY = "pagina_atual"
PAGINA_RADIO_KEY = "pagina_radio"


def _selecionar_entrada_dados() -> None:
    st.session_state[PAGINA_ATUAL_KEY] = ENTRADA_DADOS_MENU_ITEM
    st.session_state[PAGINA_RADIO_KEY] = None


def _render_navegacao() -> str:
    st.session_state.setdefault(PAGINA_ATUAL_KEY, MENU_ITEMS[0])

    st.button(
        ENTRADA_DADOS_MENU_ITEM,
        key="botao_entrada_dados",
        type="primary",
        icon=":material/edit_note:",
        on_click=_selecionar_entrada_dados,
        use_container_width=True,
    )

    pagina_atual = str(st.session_state[PAGINA_ATUAL_KEY])
    indice_menu = MENU_ITEMS.index(pagina_atual) if pagina_atual in MENU_ITEMS else None
    pagina_radio = st.radio(
        "Pagina",
        MENU_ITEMS,
        index=indice_menu,
        key=PAGINA_RADIO_KEY,
    )

    if pagina_radio:
        st.session_state[PAGINA_ATUAL_KEY] = pagina_radio

    return str(st.session_state[PAGINA_ATUAL_KEY])


def _render_sidebar_logo() -> None:
    if not SIDEBAR_LOGO_PATH.exists():
        return

    svg_base64 = base64.b64encode(SIDEBAR_LOGO_PATH.read_bytes()).decode("utf-8")
    st.markdown(
        (
            '<div style="margin: 4px 0 24px 0;">'
            f'<img src="data:image/svg+xml;base64,{svg_base64}" '
            'alt="Tacom" '
            'style="display: block; width: 100%; max-width: 235px; height: auto;" />'
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


def _formatar_mes(data_mes: pd.Timestamp) -> str:
    meses_pt = {
        1: "jan",
        2: "fev",
        3: "mar",
        4: "abr",
        5: "mai",
        6: "jun",
        7: "jul",
        8: "ago",
        9: "set",
        10: "out",
        11: "nov",
        12: "dez",
    }
    return f"{meses_pt[data_mes.month]}/{data_mes:%Y}"


def _criar_opcoes_mensais(data_min: date, data_max: date) -> list[pd.Timestamp]:
    mes_min = pd.Timestamp(data_min).to_period("M").to_timestamp()
    mes_max = pd.Timestamp(data_max).to_period("M").to_timestamp()
    return list(pd.date_range(mes_min, mes_max, freq="MS"))


def _obter_periodo_padrao(meses: list[pd.Timestamp]) -> tuple[pd.Timestamp, pd.Timestamp]:
    mes_inicio_padrao = pd.Timestamp(DATA_INICIO_PADRAO).to_period("M").to_timestamp()
    mes_fim_padrao = pd.Timestamp(date.today()).to_period("M").to_timestamp()

    inicio = next((mes for mes in meses if mes >= mes_inicio_padrao), meses[0])
    fim = next((mes for mes in reversed(meses) if mes <= mes_fim_padrao), meses[-1])

    if inicio > fim:
        inicio = fim

    return inicio, fim


def _indice_mes(meses: list[pd.Timestamp], mes_procurado: pd.Timestamp) -> int:
    for indice, mes in enumerate(meses):
        if mes == mes_procurado:
            return indice
    return 0


def render_sidebar(df_base: pd.DataFrame) -> dict[str, object]:
    data_valida = df_base["data_ref"].dropna()
    if data_valida.empty:
        data_min = date.today()
        data_max = date.today()
    else:
        data_min = data_valida.min().date()
        data_max = data_valida.max().date()

    meses_disponiveis = _criar_opcoes_mensais(data_min, data_max)
    periodo_padrao = _obter_periodo_padrao(meses_disponiveis)

    with st.sidebar:
        _render_sidebar_logo()
        _render_database_target()
        st.markdown("### Navegacao")
        menu = _render_navegacao()

        st.markdown("### Filtros")
        periodo_mensal = st.select_slider(
            "Periodo",
            options=meses_disponiveis,
            value=periodo_padrao,
            format_func=_formatar_mes,
        )

        usar_selecao_manual = st.checkbox("Selecionar periodo por lista")
        if usar_selecao_manual:
            inicio_selecionado = pd.Timestamp(periodo_mensal[0])
            fim_selecionado = pd.Timestamp(periodo_mensal[1])

            mes_inicio = st.selectbox(
                "Mes inicial",
                options=meses_disponiveis,
                index=_indice_mes(meses_disponiveis, inicio_selecionado),
                format_func=_formatar_mes,
            )
            meses_finais = [mes for mes in meses_disponiveis if mes >= mes_inicio]
            mes_fim = st.selectbox(
                "Mes final",
                options=meses_finais,
                index=_indice_mes(meses_finais, max(fim_selecionado, mes_inicio)),
                format_func=_formatar_mes,
            )
        else:
            mes_inicio, mes_fim = periodo_mensal

        inicio_mes = pd.Timestamp(mes_inicio)
        fim_mes = pd.Timestamp(mes_fim) + pd.offsets.MonthEnd(0)
        periodo = (inicio_mes, fim_mes)

        contratos = sorted([x for x in df_base["contrato"].dropna().unique().tolist() if x])
        filtro_contrato = st.multiselect("Contrato", contratos)

        operadoras = sorted([x for x in df_base["operadora"].dropna().unique().tolist() if x])
        filtro_operadora = st.multiselect("Operadora", operadoras)

        equipamentos = sorted([x for x in df_base["equipamento"].dropna().unique().tolist() if x])
        filtro_equipamento = st.multiselect("Equipamento", equipamentos)

    return {
        "menu": menu,
        "periodo": periodo,
        "filtro_contrato": filtro_contrato,
        "filtro_operadora": filtro_operadora,
        "filtro_equipamento": filtro_equipamento,
    }


def aplicar_filtros(df_base: pd.DataFrame, filtros: dict[str, object]) -> pd.DataFrame:
    df_filtrado = df_base.copy()

    periodo = filtros.get("periodo")
    if isinstance(periodo, tuple) and len(periodo) == 2:
        inicio = pd.to_datetime(periodo[0])
        fim = pd.to_datetime(periodo[1])
        df_filtrado = df_filtrado[
            (df_filtrado["data_ref"] >= inicio) & (df_filtrado["data_ref"] <= fim)
        ]
    elif isinstance(periodo, date):
        dia = pd.to_datetime(periodo)
        df_filtrado = df_filtrado[df_filtrado["data_ref"] == dia]

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

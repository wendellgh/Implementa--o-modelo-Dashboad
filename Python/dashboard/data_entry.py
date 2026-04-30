from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import text

from dashboard.database import get_engine


COLUNAS_OPERADORA = ["id_operadora", "operadora"]
COLUNAS_EQUIPAMENTO = ["cod_equipamento", "equipamento"]
COLUNAS_ULTIMAS_ENTRADAS = [
    "Status",
    "Data",
    "Contrato",
    "Operadora",
    "Equipamento",
    "Frota",
    "Qtd manutencao",
    "%",
]
CAMPO_DATA_REF = "entrada_data_ref"
CAMPO_FROTA = "entrada_frota"
CAMPO_QTD = "entrada_qtd"
CAMPO_CONTEXTO_FROTA = "entrada_contexto_frota"
CAMPO_CADASTRAR_NOVO_CONTRATO = "entrada_cadastrar_novo_contrato"
CAMPO_CADASTRAR_NOVA_OPERADORA = "entrada_cadastrar_nova_operadora"
CAMPO_CADASTRAR_NOVO_EQUIPAMENTO = "entrada_cadastrar_novo_equipamento"
CAMPO_NOVO_ID_CONTRATO = "entrada_novo_id_contrato"
CAMPO_NOVO_CONTRATO = "entrada_novo_contrato"
CAMPO_NOVO_ID_OPERADORA = "entrada_novo_id_operadora"
CAMPO_NOVA_OPERADORA = "entrada_nova_operadora"
CAMPO_NOVO_COD_EQUIPAMENTO = "entrada_novo_cod_equipamento"
CAMPO_NOVO_EQUIPAMENTO = "entrada_novo_equipamento"
FLAG_RESET_CAMPOS = "entrada_reset_campos"
FLAG_LANCAMENTO_SALVO = "entrada_lancamento_salvo"
TEXT_INPUT_KEYS = [
    CAMPO_NOVO_ID_CONTRATO,
    CAMPO_NOVO_CONTRATO,
    CAMPO_NOVO_ID_OPERADORA,
    CAMPO_NOVA_OPERADORA,
    CAMPO_NOVO_COD_EQUIPAMENTO,
    CAMPO_NOVO_EQUIPAMENTO,
]
CHECKBOX_INPUT_KEYS = [
    CAMPO_CADASTRAR_NOVO_CONTRATO,
    CAMPO_CADASTRAR_NOVA_OPERADORA,
    CAMPO_CADASTRAR_NOVO_EQUIPAMENTO,
]


def _opcoes_unicas(df: pd.DataFrame, coluna: str) -> list[str]:
    if coluna not in df.columns or df.empty:
        return []

    return sorted(
        valor
        for valor in df[coluna].fillna("").astype(str).str.strip().unique().tolist()
        if valor
    )


def _primeiro_valor(df: pd.DataFrame, coluna: str) -> str:
    if coluna not in df.columns or df.empty:
        return ""

    valores = df[coluna].fillna("").astype(str).str.strip()
    valores = valores[valores.ne("")]
    if valores.empty:
        return ""

    return str(valores.iloc[0])


def _normalizar_texto(valor: object) -> str:
    if pd.isna(valor):
        return ""

    return str(valor).strip()


def _serie_texto(df: pd.DataFrame, coluna: str) -> pd.Series:
    if coluna not in df.columns:
        return pd.Series("", index=df.index, dtype="object")

    return df[coluna].fillna("").astype(str).str.strip()


def _filtrar_por_contrato(df_base: pd.DataFrame, contrato: str) -> pd.DataFrame:
    return df_base[df_base["contrato"].eq(contrato)].copy()


def _filtrar_por_operadora(df_base: pd.DataFrame, operadora: str) -> pd.DataFrame:
    return df_base[df_base["operadora"].eq(operadora)].copy()


def _montar_tabela_operadoras(df_contrato: pd.DataFrame) -> pd.DataFrame:
    if df_contrato.empty:
        return pd.DataFrame(columns=COLUNAS_OPERADORA)

    return (
        df_contrato[COLUNAS_OPERADORA]
        .drop_duplicates()
        .sort_values("operadora")
        .reset_index(drop=True)
    )


def _montar_tabela_equipamentos(df_operadora: pd.DataFrame) -> pd.DataFrame:
    if df_operadora.empty:
        return pd.DataFrame(columns=COLUNAS_EQUIPAMENTO)

    return (
        df_operadora[COLUNAS_EQUIPAMENTO]
        .drop_duplicates()
        .sort_values("equipamento")
        .reset_index(drop=True)
    )


def _montar_tabela_ultimas_entradas(
    df_base: pd.DataFrame,
    contrato: str,
    operadora: str,
    equipamento: str,
    limite: int = 10,
) -> pd.DataFrame:
    if df_base.empty:
        return pd.DataFrame(columns=COLUNAS_ULTIMAS_ENTRADAS)

    df_aux = df_base.copy()
    filtros = {
        "contrato": contrato,
        "operadora": operadora,
        "equipamento": equipamento,
    }
    for coluna, valor in filtros.items():
        valor_normalizado = _normalizar_texto(valor)
        if valor_normalizado and coluna in df_aux.columns:
            df_aux = df_aux[_serie_texto(df_aux, coluna).eq(valor_normalizado)]

    if df_aux.empty:
        return pd.DataFrame(columns=COLUNAS_ULTIMAS_ENTRADAS)

    df_aux["_data_ref"] = pd.to_datetime(df_aux["data_ref"], errors="coerce")
    df_aux = df_aux.sort_values("_data_ref", ascending=False, na_position="last").head(limite)

    percentual = pd.to_numeric(df_aux["percentual"], errors="coerce").fillna(0)
    tabela = pd.DataFrame(
        {
            "Status": "🟢 Inserido",
            "Data": df_aux["_data_ref"].dt.strftime("%d/%m/%Y").fillna(""),
            "Contrato": _serie_texto(df_aux, "contrato"),
            "Operadora": _serie_texto(df_aux, "operadora"),
            "Equipamento": _serie_texto(df_aux, "equipamento"),
            "Frota": pd.to_numeric(df_aux["frota"], errors="coerce").fillna(0).astype(int),
            "Qtd manutencao": pd.to_numeric(df_aux["qtd"], errors="coerce").fillna(0).astype(int),
            "%": percentual.map(lambda valor: f"{valor:.2f}%"),
        }
    )

    return tabela[COLUNAS_ULTIMAS_ENTRADAS].reset_index(drop=True)


def _existe_lancamento_mes(
    df_base: pd.DataFrame,
    data_ref: date,
    contrato: str,
    operadora: str,
    equipamento: str,
) -> bool:
    if df_base.empty or not all([contrato, operadora, equipamento]):
        return False

    data_ref_periodo = pd.Timestamp(data_ref).to_period("M")
    df_aux = df_base.copy()
    df_aux["_mes_ref"] = pd.to_datetime(df_aux["data_ref"], errors="coerce").dt.to_period("M")

    mascara = (
        df_aux["_mes_ref"].eq(data_ref_periodo)
        & _serie_texto(df_aux, "contrato").str.lower().eq(_normalizar_texto(contrato).lower())
        & _serie_texto(df_aux, "operadora").str.lower().eq(_normalizar_texto(operadora).lower())
        & _serie_texto(df_aux, "equipamento").str.lower().eq(_normalizar_texto(equipamento).lower())
    )

    return bool(mascara.any())


def _render_ultimas_entradas(
    df_base: pd.DataFrame,
    data_ref: date,
    contrato: str,
    operadora: str,
    equipamento: str,
) -> None:
    tabela = _montar_tabela_ultimas_entradas(
        df_base,
        contrato=contrato,
        operadora=operadora,
        equipamento=equipamento,
    )

    if _existe_lancamento_mes(df_base, data_ref, contrato, operadora, equipamento):
        st.warning(
            "Ja existe lancamento para este mes, contrato, operadora e equipamento. "
            "Confira as ultimas entradas antes de salvar novamente."
        )

    with st.expander("Ultimas entradas", expanded=True):
        if tabela.empty:
            st.info("Sem entradas anteriores para a selecao atual.")
            return

        st.dataframe(tabela, use_container_width=True, hide_index=True)


def _calcular_percentual(qtd: int, frota: int) -> float:
    if frota <= 0:
        return 0.0

    return round((qtd / frota) * 100, 2)


def _preparar_campos() -> None:
    if st.session_state.pop(FLAG_RESET_CAMPOS, False):
        st.session_state[CAMPO_DATA_REF] = date.today()
        st.session_state[CAMPO_FROTA] = 0
        st.session_state[CAMPO_QTD] = 0
        st.session_state[CAMPO_CONTEXTO_FROTA] = ""
        for campo in TEXT_INPUT_KEYS:
            st.session_state[campo] = ""
        for campo in CHECKBOX_INPUT_KEYS:
            st.session_state[campo] = False

    st.session_state.setdefault(CAMPO_DATA_REF, date.today())
    st.session_state.setdefault(CAMPO_FROTA, 0)
    st.session_state.setdefault(CAMPO_QTD, 0)
    st.session_state.setdefault(CAMPO_CONTEXTO_FROTA, "")
    for campo in TEXT_INPUT_KEYS:
        st.session_state.setdefault(campo, "")
    for campo in CHECKBOX_INPUT_KEYS:
        st.session_state.setdefault(campo, False)


def _render_selectbox_existente(label: str, opcoes: list[str], vazio: str) -> str:
    if opcoes:
        return str(st.selectbox(label, opcoes))

    st.selectbox(label, [vazio], disabled=True)
    return ""


def _render_checkbox_cadastro(label: str, key: str, forcar: bool = False) -> bool:
    if forcar:
        st.session_state[key] = True
        st.checkbox(label, key=key, disabled=True)
        return True

    return bool(st.checkbox(label, key=key))


def _render_campos_novo_contrato() -> tuple[str, str]:
    col_id, col_nome = st.columns([1, 2])
    with col_id:
        id_contrato = st.text_input(
            "ID do contrato",
            key=CAMPO_NOVO_ID_CONTRATO,
            placeholder="Opcional",
        )
    with col_nome:
        contrato = st.text_input(
            "Nome do contrato",
            key=CAMPO_NOVO_CONTRATO,
            placeholder="Digite o novo contrato",
        )

    return str(id_contrato).strip(), str(contrato).strip()


def _render_campos_nova_operadora() -> tuple[str, str]:
    col_id, col_nome = st.columns([1, 2])
    with col_id:
        id_operadora = st.text_input(
            "ID da operadora",
            key=CAMPO_NOVO_ID_OPERADORA,
            placeholder="Opcional",
        )
    with col_nome:
        operadora = st.text_input(
            "Nome da operadora",
            key=CAMPO_NOVA_OPERADORA,
            placeholder="Digite a nova operadora",
        )

    return str(id_operadora).strip(), str(operadora).strip()


def _render_campos_novo_equipamento() -> tuple[str, str]:
    col_codigo, col_nome = st.columns([1, 2])
    with col_codigo:
        cod_equipamento = st.text_input(
            "Codigo do equipamento",
            key=CAMPO_NOVO_COD_EQUIPAMENTO,
            placeholder="Opcional",
        )
    with col_nome:
        equipamento = st.text_input(
            "Nome do equipamento",
            key=CAMPO_NOVO_EQUIPAMENTO,
            placeholder="Digite o novo equipamento",
        )

    return str(cod_equipamento).strip(), str(equipamento).strip()


def _validar_lancamento(
    contrato: str,
    operadora: str,
    equipamento: str,
    frota: int,
    qtd: int,
) -> list[str]:
    erros = []
    if not contrato:
        erros.append("Informe o nome do contrato.")
    if not operadora:
        erros.append("Informe o nome da operadora.")
    if not equipamento:
        erros.append("Informe o nome do equipamento.")
    if frota == 0 and qtd > 0:
        erros.append("Informe uma frota maior que zero para lancar quantidade em manutencao.")

    return erros


def _obter_ultima_frota(df_equipamento: pd.DataFrame) -> int | None:
    if df_equipamento.empty or "frota" not in df_equipamento.columns:
        return None

    df_aux = df_equipamento.copy()
    df_aux["_frota"] = pd.to_numeric(df_aux["frota"], errors="coerce")
    df_aux = df_aux[df_aux["_frota"].notna()]
    if df_aux.empty:
        return None

    if "data_ref" in df_aux.columns:
        df_aux["_data_ref"] = pd.to_datetime(df_aux["data_ref"], errors="coerce")
        df_aux = df_aux.sort_values("_data_ref", ascending=False, na_position="last")

    return int(df_aux["_frota"].iloc[0])


def _atualizar_frota_por_selecao(contexto: str, ultima_frota: int | None) -> None:
    if st.session_state.get(CAMPO_CONTEXTO_FROTA) == contexto:
        return

    st.session_state[CAMPO_CONTEXTO_FROTA] = contexto
    st.session_state[CAMPO_FROTA] = int(ultima_frota or 0)


def salvar_lancamento_manutencao(dados: dict[str, object]) -> None:
    insert_sql = text(
        """
        insert into base_historica_manutencao (
            data_ref,
            id_contrato,
            contrato,
            id_operadora,
            operadora,
            cod_equipamento,
            equipamento,
            frota,
            qtd,
            percentual
        )
        values (
            :data_ref,
            :id_contrato,
            :contrato,
            :id_operadora,
            :operadora,
            :cod_equipamento,
            :equipamento,
            :frota,
            :qtd,
            :percentual
        )
        """
    )

    with get_engine().begin() as conn:
        conn.execute(insert_sql, dados)

    st.cache_data.clear()


def render_entrada_dados(df_base: pd.DataFrame) -> None:
    st.subheader("Entrada de Dados de Manutencao")
    _preparar_campos()

    if st.session_state.pop(FLAG_LANCAMENTO_SALVO, False):
        st.success("Lançamento de manutencao salvo com sucesso.")

    contratos = _opcoes_unicas(df_base, "contrato")
    contrato_selecionado = _render_selectbox_existente(
        "Contrato",
        contratos,
        "Nenhum contrato cadastrado",
    )
    novo_contrato = _render_checkbox_cadastro(
        "Cadastrar novo contrato",
        CAMPO_CADASTRAR_NOVO_CONTRATO,
        forcar=not bool(contratos),
    )

    if novo_contrato:
        id_contrato, contrato = _render_campos_novo_contrato()
        df_contrato = pd.DataFrame(columns=df_base.columns)
        st.info("O novo contrato sera criado quando o lancamento for salvo.")
    else:
        contrato = str(contrato_selecionado)
        df_contrato = _filtrar_por_contrato(df_base, contrato)
        id_contrato = _primeiro_valor(df_contrato, "id_contrato")

    operadoras = _opcoes_unicas(df_contrato, "operadora")
    if operadoras:
        with st.expander("Operadoras do contrato", expanded=False):
            st.dataframe(
                _montar_tabela_operadoras(df_contrato),
                use_container_width=True,
                hide_index=True,
            )

    operadora_selecionada = _render_selectbox_existente(
        "Operadora",
        operadoras,
        "Nenhuma operadora cadastrada",
    )
    nova_operadora = _render_checkbox_cadastro(
        "Cadastrar nova operadora",
        CAMPO_CADASTRAR_NOVA_OPERADORA,
        forcar=not bool(operadoras),
    )

    if nova_operadora:
        id_operadora, operadora = _render_campos_nova_operadora()
        df_operadora = pd.DataFrame(columns=df_base.columns)
        st.info("A nova operadora sera vinculada ao contrato quando o lancamento for salvo.")
    else:
        operadora = str(operadora_selecionada)
        df_operadora = _filtrar_por_operadora(df_contrato, operadora)
        id_operadora = _primeiro_valor(df_operadora, "id_operadora")

    equipamentos = _opcoes_unicas(df_operadora, "equipamento")
    if equipamentos:
        with st.expander("Equipamentos da operadora", expanded=False):
            st.dataframe(
                _montar_tabela_equipamentos(df_operadora),
                use_container_width=True,
                hide_index=True,
            )

    col_data, col_equipamento = st.columns([1, 2])
    with col_data:
        data_ref = st.date_input("Data de referencia", key=CAMPO_DATA_REF)
    with col_equipamento:
        equipamento_selecionado = _render_selectbox_existente(
            "Equipamento",
            equipamentos,
            "Nenhum equipamento cadastrado",
        )

    novo_equipamento = _render_checkbox_cadastro(
        "Cadastrar novo equipamento",
        CAMPO_CADASTRAR_NOVO_EQUIPAMENTO,
        forcar=not bool(equipamentos),
    )
    if novo_equipamento:
        cod_equipamento, equipamento = _render_campos_novo_equipamento()
        ultima_frota = None
    else:
        equipamento = str(equipamento_selecionado)
        df_equipamento = df_operadora[df_operadora["equipamento"].eq(equipamento)]
        cod_equipamento = _primeiro_valor(df_equipamento, "cod_equipamento")
        ultima_frota = _obter_ultima_frota(df_equipamento)

    contexto_frota = "|".join(
        [
            "novo_contrato" if novo_contrato else str(contrato_selecionado),
            "nova_operadora" if nova_operadora else str(operadora_selecionada),
            "novo_equipamento" if novo_equipamento else str(equipamento_selecionado),
        ]
    )
    _atualizar_frota_por_selecao(contexto_frota, ultima_frota)

    col_frota, col_qtd, col_percentual = st.columns(3)
    with col_frota:
        frota = st.number_input("Frota", min_value=0, step=1, key=CAMPO_FROTA)
        if ultima_frota is not None:
            st.caption(f"Ultima frota cadastrada: {ultima_frota}")
    with col_qtd:
        qtd = st.number_input("Qtd em manutencao", min_value=0, step=1, key=CAMPO_QTD)

    percentual = _calcular_percentual(int(qtd), int(frota))
    with col_percentual:
        st.metric("% QTD x Frota", f"{percentual:.2f}%")

    salvar = st.button("Salvar Manutenção", type="primary")

    _render_ultimas_entradas(
        df_base,
        data_ref=data_ref,
        contrato=contrato,
        operadora=operadora,
        equipamento=equipamento,
    )

    if not salvar:
        return

    erros = _validar_lancamento(
        contrato=contrato,
        operadora=operadora,
        equipamento=equipamento,
        frota=int(frota),
        qtd=int(qtd),
    )
    if _existe_lancamento_mes(df_base, data_ref, contrato, operadora, equipamento):
        erros.append(
            "Ja existe lancamento para este mes, contrato, operadora e equipamento. "
            "Nao foi salvo para evitar duplicidade."
        )
    if erros:
        for erro in erros:
            st.error(erro)
        return

    dados = {
        "data_ref": data_ref,
        "id_contrato": id_contrato,
        "contrato": contrato,
        "id_operadora": id_operadora,
        "operadora": operadora,
        "cod_equipamento": cod_equipamento,
        "equipamento": equipamento,
        "frota": int(frota),
        "qtd": int(qtd),
        "percentual": percentual,
    }

    try:
        salvar_lancamento_manutencao(dados)
    except Exception as error:
        st.error(f"Erro ao salvar lancamento: {error}")
        return

    st.session_state[FLAG_RESET_CAMPOS] = True
    st.session_state[FLAG_LANCAMENTO_SALVO] = True
    st.rerun()

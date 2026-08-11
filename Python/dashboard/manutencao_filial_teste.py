from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from sqlalchemy import text

from dashboard.database import get_engine

TABELA_MANUTENCAO_FILIAL_TESTE = "base_historica_manutencao_filial_teste"
FUSO_HORARIO_APLICACAO = ZoneInfo("America/Sao_Paulo")
ORACLE_DIR = Path(__file__).resolve().parents[1] / "Oracle"
LISTA_DEFEITOS_RECLAMADOS_PATH = ORACLE_DIR / "LISTA DRs.csv"
LISTA_DEFEITOS_ENCONTRADOS_PATH = ORACLE_DIR / "LISTA_DEs.csv"
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
CAMPO_DATA_REF = "manutencao_filial_teste_data_ref"
CAMPO_FROTA = "manutencao_filial_teste_frota"
CAMPO_CONTEXTO_FROTA = "manutencao_filial_teste_contexto_frota"
CAMPO_CADASTRAR_NOVO_CONTRATO = "manutencao_filial_teste_cadastrar_novo_contrato"
CAMPO_CADASTRAR_NOVA_OPERADORA = "manutencao_filial_teste_cadastrar_nova_operadora"
CAMPO_CADASTRAR_NOVO_EQUIPAMENTO = "manutencao_filial_teste_cadastrar_novo_equipamento"
CAMPO_NOVO_ID_CONTRATO = "manutencao_filial_teste_novo_id_contrato"
CAMPO_NOVO_CONTRATO = "manutencao_filial_teste_novo_contrato"
CAMPO_NOVO_ID_OPERADORA = "manutencao_filial_teste_novo_id_operadora"
CAMPO_NOVA_OPERADORA = "manutencao_filial_teste_nova_operadora"
CAMPO_NOVO_COD_EQUIPAMENTO = "manutencao_filial_teste_novo_cod_equipamento"
CAMPO_NOVO_EQUIPAMENTO = "manutencao_filial_teste_novo_equipamento"
CAMPO_NUMERO_SERIE = "manutencao_filial_teste_numero_serie"
CAMPO_DEFEITO_ENCONTRADO = "manutencao_filial_teste_defeito_encontrado"
CAMPO_DEFEITO_RECLAMADO = "manutencao_filial_teste_defeito_reclamado"
CAMPO_SOLUCAO = "manutencao_filial_teste_solucao"
CAMPO_TECNICO_RESPONSAVEL = "manutencao_filial_teste_tecnico_responsavel"
FLAG_RESET_CAMPOS = "manutencao_filial_teste_reset_campos"
FLAG_LANCAMENTO_SALVO = "manutencao_filial_teste_lancamento_salvo"
TEXT_INPUT_KEYS = [
    CAMPO_NOVO_ID_CONTRATO,
    CAMPO_NOVO_CONTRATO,
    CAMPO_NOVO_ID_OPERADORA,
    CAMPO_NOVA_OPERADORA,
    CAMPO_NOVO_COD_EQUIPAMENTO,
    CAMPO_NOVO_EQUIPAMENTO,
    CAMPO_NUMERO_SERIE,
    CAMPO_DEFEITO_ENCONTRADO,
    CAMPO_DEFEITO_RECLAMADO,
    CAMPO_SOLUCAO,
    CAMPO_TECNICO_RESPONSAVEL,
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


@st.cache_data
def _carregar_opcoes_defeito(caminho: str) -> list[str]:
    arquivo = Path(caminho)
    if not arquivo.exists():
        return []

    df = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            df = pd.read_csv(arquivo, sep=";", dtype=str, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue

    if df is None or df.empty or len(df.columns) < 2:
        return []

    codigo_coluna, descricao_coluna = df.columns[:2]
    opcoes = []
    for _, linha in df.iterrows():
        codigo = _normalizar_texto(linha.get(codigo_coluna))
        descricao = _normalizar_texto(linha.get(descricao_coluna))
        if codigo and descricao:
            opcoes.append(f"{codigo} - {descricao}")
        elif descricao:
            opcoes.append(descricao)
        elif codigo:
            opcoes.append(codigo)

    return list(dict.fromkeys(opcoes))


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
    df_aux = df_aux.sort_values("_data_ref", ascending=False, na_position="last").head(
        limite
    )

    percentual = pd.to_numeric(df_aux["percentual"], errors="coerce").fillna(0)
    tabela = pd.DataFrame(
        {
            "Status": "🟢 Inserido",
            "Data": df_aux["_data_ref"].dt.strftime("%d/%m/%Y").fillna(""),
            "Contrato": _serie_texto(df_aux, "contrato"),
            "Operadora": _serie_texto(df_aux, "operadora"),
            "Equipamento": _serie_texto(df_aux, "equipamento"),
            "Frota": pd.to_numeric(df_aux["frota"], errors="coerce")
            .fillna(0)
            .astype(int),
            "Qtd manutencao": pd.to_numeric(df_aux["qtd"], errors="coerce")
            .fillna(0)
            .astype(int),
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
    coluna_periodo = (
        "data_competencia" if "data_competencia" in df_aux.columns else "data_ref"
    )
    df_aux["_mes_ref"] = pd.to_datetime(
        df_aux[coluna_periodo],
        errors="coerce",
    ).dt.to_period("M")

    mascara = (
        df_aux["_mes_ref"].eq(data_ref_periodo)
        & _serie_texto(df_aux, "contrato")
        .str.lower()
        .eq(_normalizar_texto(contrato).lower())
        & _serie_texto(df_aux, "operadora")
        .str.lower()
        .eq(_normalizar_texto(operadora).lower())
        & _serie_texto(df_aux, "equipamento")
        .str.lower()
        .eq(_normalizar_texto(equipamento).lower())
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
    data_atual = datetime.now(FUSO_HORARIO_APLICACAO).date()
    if st.session_state.pop(FLAG_RESET_CAMPOS, False):
        st.session_state[CAMPO_DATA_REF] = data_atual
        st.session_state[CAMPO_FROTA] = 0
        st.session_state[CAMPO_CONTEXTO_FROTA] = ""
        for campo in TEXT_INPUT_KEYS:
            st.session_state[campo] = ""
        for campo in CHECKBOX_INPUT_KEYS:
            st.session_state[campo] = False

    st.session_state.setdefault(CAMPO_DATA_REF, data_atual)
    st.session_state.setdefault(CAMPO_FROTA, 0)
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


def _normalizar_selectbox_sessao(chave: str, opcoes: list[str]) -> None:
    if st.session_state.get(chave) not in opcoes:
        st.session_state[chave] = opcoes[0] if opcoes else ""


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
) -> list[str]:
    erros = []
    if not contrato:
        erros.append("Informe o nome do contrato.")
    if not operadora:
        erros.append("Informe o nome da operadora.")
    if not equipamento:
        erros.append("Informe o nome do equipamento.")
    if frota == 0:
        erros.append("Informe uma frota maior que zero.")

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


def salvar_lancamento_manutencao_filial_teste(dados: dict[str, object]) -> None:
    insert_sql = text("""
        insert into base_historica_manutencao_filial_teste (
            data_ref,
            data_competencia,
            id_contrato,
            contrato,
            id_operadora,
            operadora,
            cod_equipamento,
            equipamento,
            numero_serie,
            frota,
            qtd,
            percentual,
            defeito_encontrado,
            defeito_reclamado,
            solucao,
            tecnico_responsavel
        )
        values (
            :data_ref,
            :data_competencia,
            :id_contrato,
            :contrato,
            :id_operadora,
            :operadora,
            :cod_equipamento,
            :equipamento,
            :numero_serie,
            :frota,
            :qtd,
            :percentual,
            :defeito_encontrado,
            :defeito_reclamado,
            :solucao,
            :tecnico_responsavel
        )
        """)

    with get_engine().begin() as conn:
        conn.execute(text("""
                create table if not exists public.base_historica_manutencao_filial_teste
                    (like public.base_historica_manutencao including defaults)
                """))
        conn.execute(text("""
                alter table public.base_historica_manutencao_filial_teste
                    add column if not exists data_competencia date
                """))
        conn.execute(text("""
                alter table public.base_historica_manutencao_filial_teste
                    add column if not exists defeito_encontrado text,
                    add column if not exists defeito_reclamado text,
                    add column if not exists solucao text,
                    add column if not exists tecnico_responsavel text,
                    add column if not exists numero_serie text
                """))
        conn.execute(insert_sql, dados)


def render_manutencao_filial_teste(df_base: pd.DataFrame) -> None:
    st.subheader("Manutencao Filial - Teste")
    st.caption(
        "Esta tela usa codigo e tabela de teste separados: "
        f"`{TABELA_MANUTENCAO_FILIAL_TESTE}`."
    )
    _preparar_campos()

    if st.session_state.pop(FLAG_LANCAMENTO_SALVO, False):
        st.success("Lancamento de teste salvo com sucesso.")

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

    col_operadora, col_frota = st.columns([2, 1])
    with col_operadora:
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
        st.info(
            "A nova operadora sera vinculada ao contrato quando o lancamento for salvo."
        )
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

    col_data, col_equipamento, col_numero_serie = st.columns([1, 2, 1])
    with col_data:
        data_ref = st.date_input("Data de referencia", key=CAMPO_DATA_REF)
    with col_equipamento:
        equipamento_selecionado = _render_selectbox_existente(
            "Equipamento",
            equipamentos,
            "Nenhum equipamento cadastrado",
        )
    with col_numero_serie:
        numero_serie = st.text_input("Número de série", key=CAMPO_NUMERO_SERIE)

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

    with col_frota:
        frota = st.number_input("Frota", min_value=0, step=1, key=CAMPO_FROTA)
        if ultima_frota is not None:
            st.caption(f"Ultima frota cadastrada: {ultima_frota}")

    opcoes_defeito_reclamado = _carregar_opcoes_defeito(
        str(LISTA_DEFEITOS_RECLAMADOS_PATH)
    )
    opcoes_defeito_encontrado = _carregar_opcoes_defeito(
        str(LISTA_DEFEITOS_ENCONTRADOS_PATH)
    )
    opcoes_defeito_reclamado = ["", *opcoes_defeito_reclamado]
    opcoes_defeito_encontrado = ["", *opcoes_defeito_encontrado]
    _normalizar_selectbox_sessao(CAMPO_DEFEITO_RECLAMADO, opcoes_defeito_reclamado)
    _normalizar_selectbox_sessao(CAMPO_DEFEITO_ENCONTRADO, opcoes_defeito_encontrado)

    col_defeito_reclamado, col_defeito_encontrado = st.columns(2)
    with col_defeito_reclamado:
        defeito_reclamado = st.selectbox(
            "Defeito reclamado",
            opcoes_defeito_reclamado,
            key=CAMPO_DEFEITO_RECLAMADO,
        )
    with col_defeito_encontrado:
        defeito_encontrado = st.selectbox(
            "Defeito encontrado",
            opcoes_defeito_encontrado,
            key=CAMPO_DEFEITO_ENCONTRADO,
        )

    col_solucao, col_tecnico = st.columns([2, 1])
    with col_solucao:
        solucao = st.text_input(
            "Solução",
            key=CAMPO_SOLUCAO,
        )
    with col_tecnico:
        tecnico_responsavel = st.text_input(
            "Técnico responsável",
            key=CAMPO_TECNICO_RESPONSAVEL,
        )

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
        "data_competencia": pd.Timestamp(data_ref).to_period("M").to_timestamp().date(),
        "id_contrato": id_contrato,
        "contrato": contrato,
        "id_operadora": id_operadora,
        "operadora": operadora,
        "cod_equipamento": cod_equipamento,
        "equipamento": equipamento,
        "numero_serie": _normalizar_texto(numero_serie),
        "frota": int(frota),
        "qtd": 1,
        "percentual": _calcular_percentual(1, int(frota)),
        "defeito_encontrado": _normalizar_texto(defeito_encontrado),
        "defeito_reclamado": _normalizar_texto(defeito_reclamado),
        "solucao": _normalizar_texto(solucao),
        "tecnico_responsavel": _normalizar_texto(tecnico_responsavel),
    }

    try:
        salvar_lancamento_manutencao_filial_teste(dados)
    # Fronteira da UI para falhas de configuracao, conexao, transacao e SQL.
    except Exception as error:  # noqa: BLE001
        st.error(f"Erro ao salvar lancamento: {error}")
        return

    st.session_state[FLAG_RESET_CAMPOS] = True
    st.session_state[FLAG_LANCAMENTO_SALVO] = True
    st.rerun()


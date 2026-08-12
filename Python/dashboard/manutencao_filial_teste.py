from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from dashboard.config import SERVICOS_MANUTENCAO_FILIAL_LABEL
from dashboard.data import (
    carregar_servicos_executados_manutencao_filial,
    limpar_cache_servicos_executados,
)
from dashboard.servicos_manutencao_filial import (
    PREFIXO_NUMERO_OS,
    TABELA_SERVICOS_MANUTENCAO_FILIAL,
    formatar_numero_os,
    salvar_servico_manutencao_filial,
)

TITULO_PAGINA = SERVICOS_MANUTENCAO_FILIAL_LABEL
FUSO_HORARIO_APLICACAO = ZoneInfo("America/Sao_Paulo")
ORACLE_DIR = Path(__file__).resolve().parents[1] / "Oracle"
LISTA_DEFEITOS_RECLAMADOS_PATH = ORACLE_DIR / "LISTA DRs.csv"
LISTA_DEFEITOS_ENCONTRADOS_PATH = ORACLE_DIR / "LISTA_DEs.csv"

CAMPO_DATA_REF = "manutencao_filial_data_ref"
CAMPO_NUMERO_SERIE = "manutencao_filial_numero_serie"
CAMPO_DEFEITO_ENCONTRADO = "manutencao_filial_defeito_encontrado"
CAMPO_DEFEITO_RECLAMADO = "manutencao_filial_defeito_reclamado"
CAMPO_SOLUCAO = "manutencao_filial_solucao"
CAMPO_TECNICO_RESPONSAVEL = "manutencao_filial_tecnico_responsavel"
CAMPO_CADASTRAR_NOVO_CONTRATO = "manutencao_filial_novo_contrato"
CAMPO_CADASTRAR_NOVA_OPERADORA = "manutencao_filial_nova_operadora"
CAMPO_CADASTRAR_NOVO_EQUIPAMENTO = "manutencao_filial_novo_equipamento"
CAMPO_CADASTRAR_NOVO_SERVICO = "manutencao_filial_novo_servico"
CAMPO_NOVO_ID_CONTRATO = "manutencao_filial_novo_id_contrato"
CAMPO_NOVO_CONTRATO = "manutencao_filial_nome_novo_contrato"
CAMPO_NOVO_ID_OPERADORA = "manutencao_filial_novo_id_operadora"
CAMPO_NOVA_OPERADORA = "manutencao_filial_nome_nova_operadora"
CAMPO_NOVO_ID_EQUIPAMENTO = "manutencao_filial_novo_id_equipamento"
CAMPO_NOVO_EQUIPAMENTO = "manutencao_filial_nome_novo_equipamento"
CAMPO_NOVO_ID_SERVICO = "manutencao_filial_novo_id_servico"
CAMPO_NOVO_SERVICO = "manutencao_filial_nome_novo_servico"
CAMPO_SERVICO_SELECIONADO = "manutencao_filial_servico_selecionado"
FLAG_RESET_CAMPOS = "manutencao_filial_reset_campos"
CAMPO_ULTIMA_OS_SALVA = "manutencao_filial_ultima_os_salva"

TEXT_INPUT_KEYS = (
    CAMPO_NUMERO_SERIE,
    CAMPO_SOLUCAO,
    CAMPO_TECNICO_RESPONSAVEL,
    CAMPO_NOVO_ID_CONTRATO,
    CAMPO_NOVO_CONTRATO,
    CAMPO_NOVO_ID_OPERADORA,
    CAMPO_NOVA_OPERADORA,
    CAMPO_NOVO_ID_EQUIPAMENTO,
    CAMPO_NOVO_EQUIPAMENTO,
    CAMPO_NOVO_ID_SERVICO,
    CAMPO_NOVO_SERVICO,
)
CHECKBOX_INPUT_KEYS = (
    CAMPO_CADASTRAR_NOVO_CONTRATO,
    CAMPO_CADASTRAR_NOVA_OPERADORA,
    CAMPO_CADASTRAR_NOVO_EQUIPAMENTO,
    CAMPO_CADASTRAR_NOVO_SERVICO,
)


def _normalizar_texto(valor: object) -> str:
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def _serie_texto(df: pd.DataFrame, coluna: str) -> pd.Series:
    if coluna not in df.columns:
        return pd.Series("", index=df.index, dtype="object")
    return df[coluna].fillna("").astype(str).str.strip()


def _opcoes_unicas(df: pd.DataFrame, coluna: str) -> list[str]:
    if df.empty or coluna not in df.columns:
        return []
    return sorted(valor for valor in _serie_texto(df, coluna).unique() if valor)


def _primeiro_valor(df: pd.DataFrame, coluna: str) -> str:
    valores = _serie_texto(df, coluna)
    valores = valores[valores.ne("")]
    return str(valores.iloc[0]) if not valores.empty else ""


def _filtrar_texto(df: pd.DataFrame, coluna: str, valor: str) -> pd.DataFrame:
    if df.empty or coluna not in df.columns or not valor:
        return df.iloc[0:0].copy()
    return df[_serie_texto(df, coluna).eq(_normalizar_texto(valor))].copy()


def _montar_catalogo_codigo_nome(
    df: pd.DataFrame,
    coluna_codigo: str,
    coluna_nome: str,
) -> dict[str, tuple[str, str]]:
    if df.empty:
        return {}

    catalogo: dict[str, tuple[str, str]] = {}
    registros = pd.DataFrame(
        {
            "codigo": _serie_texto(df, coluna_codigo),
            "nome": _serie_texto(df, coluna_nome),
        }
    ).drop_duplicates()
    registros = registros[registros["codigo"].ne("") | registros["nome"].ne("")]
    registros = registros.sort_values(["nome", "codigo"])

    for registro in registros.itertuples(index=False):
        codigo = str(registro.codigo)
        nome = str(registro.nome)
        rotulo = f"{codigo} - {nome}" if codigo and nome else codigo or nome
        catalogo.setdefault(rotulo, (codigo, nome))

    return catalogo


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

    _codigo_coluna, _descricao_coluna = df.columns[:2]
    opcoes = []
    for registro in df.itertuples(index=False, name=None):
        codigo = _normalizar_texto(registro[0])
        descricao = _normalizar_texto(registro[1])
        if codigo and descricao:
            opcoes.append(f"{codigo} - {descricao}")
        elif codigo or descricao:
            opcoes.append(codigo or descricao)

    return list(dict.fromkeys(opcoes))


def _preparar_campos() -> None:
    data_atual = datetime.now(FUSO_HORARIO_APLICACAO).date()
    if st.session_state.pop(FLAG_RESET_CAMPOS, False):
        st.session_state[CAMPO_DATA_REF] = data_atual
        st.session_state[CAMPO_DEFEITO_RECLAMADO] = ""
        st.session_state[CAMPO_DEFEITO_ENCONTRADO] = ""
        for campo in TEXT_INPUT_KEYS:
            st.session_state[campo] = ""
        for campo in CHECKBOX_INPUT_KEYS:
            st.session_state[campo] = False

    st.session_state.setdefault(CAMPO_DATA_REF, data_atual)
    st.session_state.setdefault(CAMPO_DEFEITO_RECLAMADO, "")
    st.session_state.setdefault(CAMPO_DEFEITO_ENCONTRADO, "")
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


def _render_campos_codigo_nome(
    label_codigo: str,
    label_nome: str,
    key_codigo: str,
    key_nome: str,
) -> tuple[str, str]:
    col_codigo, col_nome = st.columns([1, 2])
    with col_codigo:
        codigo = st.text_input(label_codigo, key=key_codigo, placeholder="Opcional")
    with col_nome:
        nome = st.text_input(label_nome, key=key_nome)
    return _normalizar_texto(codigo), _normalizar_texto(nome)


def _normalizar_selectbox_sessao(chave: str, opcoes: list[str]) -> None:
    if st.session_state.get(chave) not in opcoes:
        st.session_state[chave] = opcoes[0] if opcoes else ""


def _validar_servico(
    contrato: str,
    operadora: str,
    equipamento: str,
    servico_executado: str,
) -> list[str]:
    erros = []
    if not contrato:
        erros.append("Informe o contrato/filial.")
    if not operadora:
        erros.append("Informe a operadora.")
    if not equipamento:
        erros.append("Informe o equipamento.")
    if not servico_executado:
        erros.append("Informe o serviço executado.")
    return erros


def _montar_tabela_ultimos_servicos(
    df_servicos: pd.DataFrame,
    contrato: str,
    operadora: str,
    equipamento: str,
    limite: int = 10,
) -> pd.DataFrame:
    colunas_saida = [
        "Data",
        "Número da OS",
        "Contrato/Filial",
        "Operadora",
        "Equipamento",
        "Número de série",
        "Serviço executado",
        "Técnico",
    ]
    if df_servicos.empty:
        return pd.DataFrame(columns=colunas_saida)

    df_aux = df_servicos.copy()
    for coluna, valor in {
        "contrato": contrato,
        "operadora": operadora,
        "equipamento": equipamento,
    }.items():
        if valor:
            df_aux = df_aux[_serie_texto(df_aux, coluna).eq(valor)]

    if df_aux.empty:
        return pd.DataFrame(columns=colunas_saida)

    df_aux["_data_ref"] = pd.to_datetime(df_aux["data_ref"], errors="coerce")
    df_aux["_id"] = pd.to_numeric(_serie_texto(df_aux, "id"), errors="coerce")
    df_aux = df_aux.sort_values(
        ["_data_ref", "_id"],
        ascending=[False, False],
        na_position="last",
    ).head(limite)
    tabela = pd.DataFrame(
        {
            "Data": df_aux["_data_ref"].dt.strftime("%d/%m/%Y").fillna(""),
            "Número da OS": _serie_texto(df_aux, "numero_os"),
            "Contrato/Filial": _serie_texto(df_aux, "contrato"),
            "Operadora": _serie_texto(df_aux, "operadora"),
            "Equipamento": _serie_texto(df_aux, "equipamento"),
            "Número de série": _serie_texto(df_aux, "numero_serie"),
            "Serviço executado": _serie_texto(df_aux, "servico_executado"),
            "Técnico": _serie_texto(df_aux, "tecnico_responsavel"),
        }
    )
    return tabela[colunas_saida].reset_index(drop=True)


def _render_ultimos_servicos(
    contrato: str,
    operadora: str,
    equipamento: str,
) -> None:
    try:
        df_servicos = carregar_servicos_executados_manutencao_filial()
    except Exception as error:  # noqa: BLE001
        st.warning(f"Não foi possível consultar os serviços da filial: {error}")
        return

    tabela = _montar_tabela_ultimos_servicos(
        df_servicos,
        contrato,
        operadora,
        equipamento,
    )
    with st.expander("Últimas OS registradas na filial", expanded=True):
        if tabela.empty:
            st.info("Nenhuma OS da filial registrada para a seleção atual.")
            return
        st.dataframe(tabela, use_container_width=True, hide_index=True)


def render_manutencao_filial_teste(df_servicos_oracle: pd.DataFrame) -> None:
    st.subheader(TITULO_PAGINA)
    st.caption(
        "Os cadastros exibidos abaixo usam os serviços normalizados do Oracle como "
        f"referência. Cada lançamento representa uma OS identificada por `{PREFIXO_NUMERO_OS}` "
        "mais sua numeração e é salvo separadamente em "
        f"`{TABELA_SERVICOS_MANUTENCAO_FILIAL}` e aparece junto aos dados Oracle "
        'na consulta "Serviços executados".'
    )
    _preparar_campos()

    numero_os_salva = st.session_state.pop(CAMPO_ULTIMA_OS_SALVA, "")
    if numero_os_salva:
        st.success(f"OS {numero_os_salva} salva com sucesso.")

    contratos = _opcoes_unicas(df_servicos_oracle, "contrato")
    contrato_selecionado = _render_selectbox_existente(
        "Contrato/Filial (referência Oracle)",
        contratos,
        "Nenhum contrato/filial encontrado no Oracle",
    )
    novo_contrato = _render_checkbox_cadastro(
        "Cadastrar contrato/filial não encontrado no Oracle",
        CAMPO_CADASTRAR_NOVO_CONTRATO,
        forcar=not bool(contratos),
    )
    if novo_contrato:
        id_contrato, contrato = _render_campos_codigo_nome(
            "ID do contrato/filial",
            "Nome do contrato/filial",
            CAMPO_NOVO_ID_CONTRATO,
            CAMPO_NOVO_CONTRATO,
        )
        df_contrato = df_servicos_oracle.iloc[0:0].copy()
    else:
        contrato = contrato_selecionado
        df_contrato = _filtrar_texto(df_servicos_oracle, "contrato", contrato)
        id_contrato = _primeiro_valor(df_contrato, "id_contrato")

    operadoras = _opcoes_unicas(df_contrato, "operadora")
    operadora_selecionada = _render_selectbox_existente(
        "Operadora (referência Oracle)",
        operadoras,
        "Nenhuma operadora encontrada no Oracle",
    )
    nova_operadora = _render_checkbox_cadastro(
        "Cadastrar operadora não encontrada no Oracle",
        CAMPO_CADASTRAR_NOVA_OPERADORA,
        forcar=not bool(operadoras),
    )
    if nova_operadora:
        id_operadora, operadora = _render_campos_codigo_nome(
            "ID da operadora",
            "Nome da operadora",
            CAMPO_NOVO_ID_OPERADORA,
            CAMPO_NOVA_OPERADORA,
        )
        df_operadora = df_contrato.iloc[0:0].copy()
    else:
        operadora = operadora_selecionada
        df_operadora = _filtrar_texto(df_contrato, "operadora", operadora)
        id_operadora = _primeiro_valor(df_operadora, "id_operadora")

    equipamentos = _opcoes_unicas(df_operadora, "equipamento")
    col_data, col_equipamento, col_serie = st.columns([1, 2, 1])
    with col_data:
        data_ref = st.date_input("Data do serviço", key=CAMPO_DATA_REF)
    with col_equipamento:
        equipamento_selecionado = _render_selectbox_existente(
            "Equipamento (referência Oracle)",
            equipamentos,
            "Nenhum equipamento encontrado no Oracle",
        )
    with col_serie:
        numero_serie = st.text_input("Número de série", key=CAMPO_NUMERO_SERIE)

    novo_equipamento = _render_checkbox_cadastro(
        "Cadastrar equipamento não encontrado no Oracle",
        CAMPO_CADASTRAR_NOVO_EQUIPAMENTO,
        forcar=not bool(equipamentos),
    )
    if novo_equipamento:
        id_equipamento, equipamento = _render_campos_codigo_nome(
            "ID do equipamento",
            "Nome do equipamento",
            CAMPO_NOVO_ID_EQUIPAMENTO,
            CAMPO_NOVO_EQUIPAMENTO,
        )
        df_equipamento = df_operadora.iloc[0:0].copy()
    else:
        equipamento = equipamento_selecionado
        df_equipamento = _filtrar_texto(
            df_operadora,
            "equipamento",
            equipamento,
        )
        id_equipamento = _primeiro_valor(df_equipamento, "id_equipamento")

    catalogo_servicos = _montar_catalogo_codigo_nome(
        df_servicos_oracle,
        "id_servico_executado",
        "servico_executado",
    )
    opcoes_servico = list(catalogo_servicos)
    _normalizar_selectbox_sessao(CAMPO_SERVICO_SELECIONADO, opcoes_servico)
    servico_selecionado = ""
    if opcoes_servico:
        servico_selecionado = str(
            st.selectbox(
                "Serviço executado (referência Oracle)",
                opcoes_servico,
                key=CAMPO_SERVICO_SELECIONADO,
            )
        )
    else:
        st.selectbox(
            "Serviço executado (referência Oracle)",
            ["Nenhum serviço encontrado no Oracle"],
            disabled=True,
        )

    novo_servico = _render_checkbox_cadastro(
        "Cadastrar serviço não encontrado no Oracle",
        CAMPO_CADASTRAR_NOVO_SERVICO,
        forcar=not bool(opcoes_servico),
    )
    if novo_servico:
        id_servico_executado, servico_executado = _render_campos_codigo_nome(
            "ID do serviço",
            "Descrição do serviço executado",
            CAMPO_NOVO_ID_SERVICO,
            CAMPO_NOVO_SERVICO,
        )
    else:
        id_servico_executado, servico_executado = catalogo_servicos.get(
            servico_selecionado,
            ("", ""),
        )

    opcoes_defeito_reclamado = [
        "",
        *_carregar_opcoes_defeito(str(LISTA_DEFEITOS_RECLAMADOS_PATH)),
    ]
    opcoes_defeito_encontrado = [
        "",
        *_carregar_opcoes_defeito(str(LISTA_DEFEITOS_ENCONTRADOS_PATH)),
    ]
    _normalizar_selectbox_sessao(CAMPO_DEFEITO_RECLAMADO, opcoes_defeito_reclamado)
    _normalizar_selectbox_sessao(CAMPO_DEFEITO_ENCONTRADO, opcoes_defeito_encontrado)

    col_reclamado, col_encontrado = st.columns(2)
    with col_reclamado:
        defeito_reclamado = st.selectbox(
            "Defeito reclamado",
            opcoes_defeito_reclamado,
            key=CAMPO_DEFEITO_RECLAMADO,
        )
    with col_encontrado:
        defeito_encontrado = st.selectbox(
            "Defeito encontrado",
            opcoes_defeito_encontrado,
            key=CAMPO_DEFEITO_ENCONTRADO,
        )
    col_solucao, col_tecnico = st.columns([2, 1])
    with col_solucao:
        solucao = st.text_input("Solução / observação", key=CAMPO_SOLUCAO)
    with col_tecnico:
        tecnico_responsavel = st.text_input(
            "Técnico responsável",
            key=CAMPO_TECNICO_RESPONSAVEL,
        )

    praca = _primeiro_valor(df_equipamento, "praca")
    nome_praca = _primeiro_valor(df_equipamento, "nome_praca")
    coordenacao = _primeiro_valor(df_equipamento, "coordenacao")
    localizacao = " / ".join(valor for valor in [coordenacao, nome_praca] if valor)
    if localizacao:
        st.caption(f"Localização herdada do Oracle: {localizacao}")

    st.caption(
        f"O número da OS será gerado automaticamente com o prefixo {PREFIXO_NUMERO_OS}"
    )

    salvar = st.button("Salvar OS", type="primary")
    _render_ultimos_servicos(contrato, operadora, equipamento)
    if not salvar:
        return

    erros = _validar_servico(
        contrato,
        operadora,
        equipamento,
        servico_executado,
    )
    if erros:
        for erro in erros:
            st.error(erro)
        return

    dados = {
        "data_ref": data_ref,
        "data_competencia": pd.Timestamp(data_ref).to_period("M").start_time.date(),
        "id_contrato": id_contrato,
        "contrato": contrato,
        "id_operadora": id_operadora,
        "operadora": operadora,
        "id_equipamento": id_equipamento,
        "equipamento": equipamento,
        "numero_serie": _normalizar_texto(numero_serie),
        "id_servico_executado": id_servico_executado,
        "servico_executado": servico_executado,
        "defeito_reclamado": _normalizar_texto(defeito_reclamado),
        "defeito_encontrado": _normalizar_texto(defeito_encontrado),
        "solucao": _normalizar_texto(solucao),
        "tecnico_responsavel": _normalizar_texto(tecnico_responsavel),
        "praca": praca,
        "nome_praca": nome_praca,
        "coordenacao": coordenacao,
    }

    try:
        novo_id = salvar_servico_manutencao_filial(dados)
    except Exception as error:  # noqa: BLE001
        st.error(f"Erro ao salvar a OS: {error}")
        return

    limpar_cache_servicos_executados()
    st.session_state[FLAG_RESET_CAMPOS] = True
    st.session_state[CAMPO_ULTIMA_OS_SALVA] = formatar_numero_os(novo_id)
    st.rerun()

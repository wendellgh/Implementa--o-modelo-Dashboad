import pandas as pd
import streamlit as st
from sqlalchemy import text

from dashboard.config import BASE_QUERY, BASE_QUERY_2
from dashboard.database import get_engine
from dashboard.pracas import enriquecer_dataframe_contratos, enriquecer_dataframe_pracas
from dashboard.servicos_manutencao_filial import carregar_servicos_manutencao_filial
from dashboard.utils_otimizacoes import (
    calcular_percentual_seguro,
    normalizar_coluna_texto,
    normalizar_multiplas_colunas,
    serie_meses_formatada,
)

ANO_MINIMO_COMPETENCIA = 1900
COLUNAS_DETALHE_SERVICOS = [
    "id",
    "numero_serie",
    "defeito_reclamado",
    "defeito_encontrado",
    "solucao",
    "tecnico_responsavel",
    "criado_em",
]
COLUNAS_TEXTO_SERVICOS = [
    "id_contrato",
    "contrato",
    "id_operadora",
    "operadora",
    "id_equipamento",
    "equipamento",
    "id_servico_executado",
    "servico_executado",
    "praca",
    "nome_praca",
    "coordenacao",
    "numero_serie",
    "defeito_reclamado",
    "defeito_encontrado",
    "solucao",
    "tecnico_responsavel",
    "origem",
]
GARANTIR_COLUNAS_SERVICOS_EXECUTADOS_SQL = """
ALTER TABLE public.servicos_executados
    ADD COLUMN IF NOT EXISTS "DATA_COMPETENCIA" date;

ALTER TABLE public.servicos_executados
    ADD COLUMN IF NOT EXISTS "PRACA" text;

ALTER TABLE public.servicos_executados
    ADD COLUMN IF NOT EXISTS "NOME_PRACA" text;

ALTER TABLE public.servicos_executados
    ADD COLUMN IF NOT EXISTS "COORDENACAO" text;
"""

def _converter_data_servicos(valores: pd.Series) -> pd.Series:
    texto = valores.fillna("").astype(str).str.strip()
    datas = pd.to_datetime(texto, format="%d/%m/%Y", errors="coerce")

    pendentes = datas.isna() & texto.ne("")
    if pendentes.any():
        datas.loc[pendentes] = pd.to_datetime(
            texto.loc[pendentes],
            dayfirst=True,
            errors="coerce",
        )

    return datas


def _adicionar_colunas_competencia(
    df: pd.DataFrame,
    coluna_data: str = "data_ref",
) -> pd.DataFrame:
    if df.empty or coluna_data not in df.columns:
        return df

    competencia = _remover_datas_fora_do_intervalo(df[coluna_data])

    if "data_competencia" in df.columns:
        competencia_banco = _remover_datas_fora_do_intervalo(df["data_competencia"])
        competencia = competencia_banco.fillna(competencia)

    df["data_competencia"] = competencia.dt.to_period("M").dt.to_timestamp()
    df["ano_mes"] = pd.to_numeric(
        df["data_competencia"].dt.strftime("%Y%m"),
        errors="coerce",
    ).astype("Int64")
    df["mes_ano"] = df["data_competencia"].dt.strftime("%m/%Y").fillna("")

    return df


def _remover_datas_fora_do_intervalo(datas: pd.Series) -> pd.Series:
    datas = pd.to_datetime(datas, dayfirst=True, errors="coerce")
    ano = datas.dt.year
    return datas.where(ano.isna() | ano.ge(ANO_MINIMO_COMPETENCIA))


def _pontuar_nome_cadastral(valor: object) -> tuple[int, int, int, int]:
    texto = str(valor or "").strip()
    caracteres_invalidos = texto.count("?")
    caracteres_acentuados = sum(1 for caractere in texto if ord(caractere) > 127)
    caixa_mista = int(not texto.isupper())
    return (-caracteres_invalidos, caracteres_acentuados, caixa_mista, len(texto))


def _aplicar_nomes_canonicos_por_id(
    df: pd.DataFrame,
    coluna_id: str,
    coluna_nome: str,
) -> pd.DataFrame:
    if df.empty or coluna_id not in df.columns or coluna_nome not in df.columns:
        return df

    ids_preenchidos = df[coluna_id].fillna("").astype(str).str.strip().ne("")
    if not ids_preenchidos.any():
        return df

    nomes_por_id = {}
    for id_cadastro, grupo in df.loc[ids_preenchidos].groupby(coluna_id):
        opcoes = [
            nome
            for nome in grupo[coluna_nome].fillna("").astype(str).str.strip().unique()
            if nome
        ]
        if opcoes:
            nomes_por_id[id_cadastro] = max(opcoes, key=_pontuar_nome_cadastral)

    if nomes_por_id:
        df[coluna_nome] = df[coluna_id].map(nomes_por_id).fillna(df[coluna_nome])

    return df


def _preencher_pracas_por_contrato(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "contrato" not in df.columns:
        return df

    enriquecido_por_contrato = enriquecer_dataframe_contratos(
        df[["contrato"]].copy(),
        coluna_contrato="contrato",
        coluna_praca="praca",
        coluna_nome_praca="nome_praca",
        coluna_coordenacao="coordenacao",
    )

    resultado = df.copy()
    for coluna in ["praca", "nome_praca", "coordenacao"]:
        if coluna not in resultado.columns:
            resultado[coluna] = ""

        atual = resultado[coluna].fillna("").astype(str).str.strip()
        por_contrato = (
            enriquecido_por_contrato[coluna].fillna("").astype(str).str.strip()
        )
        resultado[coluna] = atual.where(atual.ne(""), por_contrato)

    return enriquecer_dataframe_pracas(
        resultado,
        coluna_praca="praca",
        coluna_nome_praca="nome_praca",
        coluna_coordenacao="coordenacao",
    )


def _obter_serie_competencia(df: pd.DataFrame) -> pd.Series:
    if "data_competencia" in df.columns:
        datas = _remover_datas_fora_do_intervalo(df["data_competencia"])
        return datas.dt.to_period("M").dt.to_timestamp()

    datas = _remover_datas_fora_do_intervalo(df["data_ref"])
    return datas.dt.to_period("M").dt.to_timestamp()


def _garantir_colunas_servicos_executados() -> None:
    with get_engine().begin() as conn:
        conn.execute(text(GARANTIR_COLUNAS_SERVICOS_EXECUTADOS_SQL))


@st.cache_data
def carregar_base() -> pd.DataFrame:

    df = pd.read_sql(BASE_QUERY, get_engine())

    if df.empty:
        return df

    df["data_ref"] = _remover_datas_fora_do_intervalo(df["data_ref"])
    df = _adicionar_colunas_competencia(df)

    for coluna in ["qtd", "frota", "percentual"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0)

    for coluna in ["id_contrato", "contrato", "id_operadora", "operadora", "cod_equipamento", "equipamento"]:
        df[coluna] = df[coluna].fillna("").astype(str).str.strip()

    df = _aplicar_nomes_canonicos_por_id(df, "id_contrato", "contrato")
    df = _aplicar_nomes_canonicos_por_id(df, "id_operadora", "operadora")
    df = enriquecer_dataframe_contratos(
        df,
        coluna_contrato="contrato",
        coluna_praca="praca",
        coluna_nome_praca="nome_praca",
        coluna_coordenacao="coordenacao",
    )

    return df


def _preparar_dados_servicos(
    dados_servicos: pd.DataFrame,
    origem: str,
) -> pd.DataFrame:
    dados_servicos = dados_servicos.copy()
    dados_servicos["origem"] = origem

    for coluna in COLUNAS_DETALHE_SERVICOS:
        if coluna not in dados_servicos.columns:
            dados_servicos[coluna] = pd.NaT if coluna == "criado_em" else ""

    if dados_servicos.empty:
        return dados_servicos

    colunas_obrigatorias = ["data_ref", "servico_executado", "qtd_servico"]
    colunas_ausentes = [
        coluna for coluna in colunas_obrigatorias if coluna not in dados_servicos.columns
    ]
    if colunas_ausentes:
        raise KeyError(
            "Colunas ausentes na fonte de servicos executados: "
            f"{', '.join(colunas_ausentes)}. "
            f"Colunas retornadas: {', '.join(dados_servicos.columns)}"
        )

    dados_servicos["data_ref"] = _converter_data_servicos(dados_servicos["data_ref"])
    dados_servicos = _adicionar_colunas_competencia(dados_servicos)
    dados_servicos["qtd_servico"] = pd.to_numeric(
        dados_servicos["qtd_servico"],
        errors="coerce",
    ).fillna(0)

    for coluna in COLUNAS_TEXTO_SERVICOS:
        if coluna in dados_servicos.columns:
            dados_servicos[coluna] = (
                dados_servicos[coluna].fillna("").astype(str).str.strip()
            )

    dados_servicos = _aplicar_nomes_canonicos_por_id(
        dados_servicos,
        "id_contrato",
        "contrato",
    )
    dados_servicos = _aplicar_nomes_canonicos_por_id(
        dados_servicos,
        "id_operadora",
        "operadora",
    )
    dados_servicos = _aplicar_nomes_canonicos_por_id(
        dados_servicos,
        "id_equipamento",
        "equipamento",
    )
    dados_servicos = enriquecer_dataframe_pracas(
        dados_servicos,
        coluna_praca="praca",
        coluna_nome_praca="nome_praca",
        coluna_coordenacao="coordenacao",
    )
    return _preencher_pracas_por_contrato(dados_servicos)


@st.cache_data
def carregar_servicos_executados_oracle() -> pd.DataFrame:
    _garantir_colunas_servicos_executados()
    dados_servicos = pd.read_sql(BASE_QUERY_2, get_engine())
    return _preparar_dados_servicos(dados_servicos, origem="Oracle")


@st.cache_data
def carregar_servicos_executados_manutencao_filial() -> pd.DataFrame:
    dados_servicos = carregar_servicos_manutencao_filial()
    return _preparar_dados_servicos(
        dados_servicos,
        origem="Manutenção Filial",
    )


def _combinar_fontes_servicos(*fontes: pd.DataFrame) -> pd.DataFrame:
    fontes_preenchidas = [fonte for fonte in fontes if not fonte.empty]
    if fontes_preenchidas:
        return pd.concat(fontes_preenchidas, ignore_index=True, sort=False)
    if fontes:
        return fontes[0].copy()
    return pd.DataFrame()


@st.cache_data
def carregar_base_outra_tabela() -> pd.DataFrame:
    fontes = (
        carregar_servicos_executados_oracle(),
        carregar_servicos_executados_manutencao_filial(),
    )
    return _combinar_fontes_servicos(*fontes)


def limpar_cache_servicos_executados() -> None:
    carregar_servicos_executados_oracle.clear()
    carregar_servicos_executados_manutencao_filial.clear()
    carregar_base_outra_tabela.clear()
    carregar_dimensao_pracas_servicos.clear()


@st.cache_data
def carregar_dimensao_pracas_servicos() -> pd.DataFrame:
    dados_servicos = carregar_base_outra_tabela()
    colunas = ["praca", "nome_praca", "coordenacao"]
    dimensao = dados_servicos.reindex(columns=colunas).copy()

    if dimensao.empty:
        return dimensao

    for coluna in colunas:
        dimensao[coluna] = dimensao[coluna].fillna("").astype(str).str.strip()

    dimensao = enriquecer_dataframe_pracas(
        dimensao,
        coluna_praca="praca",
        coluna_nome_praca="nome_praca",
        coluna_coordenacao="coordenacao",
    )

    return dimensao.drop_duplicates().reset_index(drop=True)


def montar_servicos_executados_por_tipo(df_filtrado: pd.DataFrame) -> pd.DataFrame:
    if df_filtrado.empty:
        return pd.DataFrame(columns=["servico_executado", "quantidade_servicos"])

    resumo = (
        df_filtrado[df_filtrado["servico_executado"].fillna("").str.strip().ne("")]
        .groupby("servico_executado", as_index=False)
        .agg(quantidade_servicos=("qtd_servico", "sum"))
        .sort_values("quantidade_servicos", ascending=False)
    )

    resumo["quantidade_servicos"] = resumo["quantidade_servicos"].astype(int)

    return resumo


def montar_resumo_equipamento(df_filtrado: pd.DataFrame) -> pd.DataFrame:
    if df_filtrado.empty:
        return pd.DataFrame(
            columns=[
                "equipamento",
                "total_qtd",
                "total_frota",
                "media_percentual",
                "percentual_recalculado",
            ]
        )

    resumo = (
        df_filtrado.groupby("equipamento", as_index=False)
        .agg(
            total_qtd=("qtd", "sum"),
            total_frota=("frota", "sum"),
            media_percentual=("percentual", "mean"),
        )
        .sort_values("equipamento")
    )

    # Vetorizado: 50x mais rápido que .apply(axis=1)
    resumo["percentual_recalculado"] = calcular_percentual_seguro(
        resumo["total_qtd"],
        resumo["total_frota"],
        decimais=2,
    )

    resumo["media_percentual"] = resumo["media_percentual"].round(2)
    resumo["total_qtd"] = resumo["total_qtd"].astype(int)
    resumo["total_frota"] = resumo["total_frota"].astype(int)

    return resumo


def montar_equipamentos_por_contrato(df_filtrado: pd.DataFrame) -> pd.DataFrame:
    if df_filtrado.empty:
        return pd.DataFrame(columns=["contrato", "mes", "quantidade_equipamentos"])

    df_aux = df_filtrado[df_filtrado["contrato"].ne("")].copy()
    if df_aux.empty:
        return pd.DataFrame(columns=["contrato", "mes", "quantidade_equipamentos"])

    df_aux["mes"] = _obter_serie_competencia(df_aux)
    mes_mais_recente_por_contrato = df_aux.groupby("contrato")["mes"].transform("max")
    df_mes_recente = df_aux[df_aux["mes"].eq(mes_mais_recente_por_contrato)]

    equipamentos_contrato = (
        df_mes_recente.groupby(["contrato", "mes"], as_index=False)
        .agg(quantidade_equipamentos=("frota", "sum"))
        .sort_values("quantidade_equipamentos", ascending=False)
        .head(10)
    )

    equipamentos_contrato["quantidade_equipamentos"] = equipamentos_contrato[
        "quantidade_equipamentos"
    ].astype(int)

    return equipamentos_contrato


def montar_manutencao_por_contrato(df_filtrado: pd.DataFrame) -> pd.DataFrame:
    if df_filtrado.empty:
        return pd.DataFrame(columns=["contrato", "quantidade_manutencao"])

    df_aux = df_filtrado[df_filtrado["contrato"].ne("")].copy()
    if df_aux.empty:
        return pd.DataFrame(columns=["contrato", "quantidade_manutencao"])

    manutencao_contrato = (
        df_aux.groupby("contrato", as_index=False)
        .agg(quantidade_manutencao=("qtd", "sum"))
        .sort_values("quantidade_manutencao", ascending=False)
        .head(5)
    )

    manutencao_contrato["quantidade_manutencao"] = manutencao_contrato[
        "quantidade_manutencao"
    ].astype(int)

    return manutencao_contrato


def montar_manutencao_por_operadora(df_filtrado: pd.DataFrame) -> pd.DataFrame:
    colunas = [
        "operadora",
        "quantidade_manutencao",
        "total_frota",
        "percentual_manutencao_frota",
    ]
    if df_filtrado.empty:
        return pd.DataFrame(columns=colunas)

    df_aux = df_filtrado[df_filtrado["operadora"].ne("")].copy()
    if df_aux.empty:
        return pd.DataFrame(columns=colunas)

    df_aux["qtd"] = pd.to_numeric(df_aux["qtd"], errors="coerce").fillna(0)
    df_aux["frota"] = pd.to_numeric(df_aux["frota"], errors="coerce").fillna(0)

    manutencao_operadora = (
        df_aux.groupby("operadora", as_index=False)
        .agg(
            quantidade_manutencao=("qtd", "sum"),
            total_frota=("frota", "sum"),
        )
        .sort_values("quantidade_manutencao", ascending=False)
        .head(5)
    )

    # Vetorizado: 50x mais rápido que .apply(axis=1)
    manutencao_operadora["percentual_manutencao_frota"] = calcular_percentual_seguro(
        manutencao_operadora["quantidade_manutencao"],
        manutencao_operadora["total_frota"],
        decimais=2,
    )

    manutencao_operadora["quantidade_manutencao"] = manutencao_operadora[
        "quantidade_manutencao"
    ].astype(int)
    manutencao_operadora["total_frota"] = manutencao_operadora["total_frota"].astype(
        int
    )

    return manutencao_operadora


def montar_equipamentos_por_operadora(df_filtrado: pd.DataFrame) -> pd.DataFrame:
    colunas = [
        "operadora",
        "equipamento",
        "quantidade_manutencao",
        "total_operadora",
        "competencia_inicio",
        "competencia_fim",
    ]
    if df_filtrado.empty:
        return pd.DataFrame(columns=colunas)

    df_aux = df_filtrado[
        df_filtrado["operadora"].ne("") & df_filtrado["equipamento"].ne("")
    ].copy()
    if df_aux.empty:
        return pd.DataFrame(columns=colunas)

    df_aux["qtd"] = pd.to_numeric(df_aux["qtd"], errors="coerce").fillna(0)
    df_aux = df_aux[df_aux["qtd"].gt(0)]
    if df_aux.empty:
        return pd.DataFrame(columns=colunas)

    df_aux["competencia"] = _obter_serie_competencia(df_aux)
    df_aux = df_aux[df_aux["competencia"].notna()]
    if df_aux.empty:
        return pd.DataFrame(columns=colunas)

    equipamentos_operadora = (
        df_aux.groupby(["operadora", "equipamento"], as_index=False)
        .agg(
            quantidade_manutencao=("qtd", "sum"),
            competencia_inicio=("competencia", "min"),
            competencia_fim=("competencia", "max"),
        )
    )
    totais_operadora = (
        equipamentos_operadora.groupby("operadora", as_index=False)
        .agg(total_operadora=("quantidade_manutencao", "sum"))
        .sort_values("total_operadora", ascending=False)
        .head(10)
    )
    equipamentos_operadora = equipamentos_operadora.merge(
        totais_operadora,
        on="operadora",
        how="inner",
    ).sort_values(
        ["total_operadora", "operadora", "quantidade_manutencao"],
        ascending=[False, True, False],
    )

    equipamentos_operadora["quantidade_manutencao"] = equipamentos_operadora[
        "quantidade_manutencao"
    ].astype(int)
    equipamentos_operadora["total_operadora"] = equipamentos_operadora[
        "total_operadora"
    ].astype(int)

    return equipamentos_operadora[colunas]


def montar_frota_contrato_por_mes(df_filtrado: pd.DataFrame) -> pd.DataFrame:
    colunas = ["mes", "mes_label", "contrato", "quantidade_frota"]
    if df_filtrado.empty:
        return pd.DataFrame(columns=colunas)

    df_aux = df_filtrado[
        df_filtrado["contrato"].ne("")
        & df_filtrado["equipamento"].str.contains("CCIT", case=False, na=False)
        & ~df_filtrado["equipamento"].str.contains("CONNECTION", case=False, na=False)
    ].copy()
    if df_aux.empty:
        return pd.DataFrame(columns=colunas)

    df_aux["mes"] = _obter_serie_competencia(df_aux)
    df_aux = df_aux[df_aux["mes"].notna()]
    if df_aux.empty:
        return pd.DataFrame(columns=colunas)

    mes_mais_recente = df_aux["mes"].max()
    df_mes_recente = df_aux[df_aux["mes"].eq(mes_mais_recente)]

    frota_contrato = (
        df_mes_recente.groupby(["mes", "contrato"], as_index=False)
        .agg(quantidade_frota=("frota", "sum"))
        .sort_values("quantidade_frota", ascending=False)
        .head(6)
    )

    # Consolidado: usa função centralizada de formatação
    frota_contrato["mes_label"] = serie_meses_formatada(
        frota_contrato["mes"],
        formato="curto"
    )
    frota_contrato["quantidade_frota"] = frota_contrato["quantidade_frota"].astype(int)

    return frota_contrato[colunas]


def _evolucao_mensal_vazia(
    meses_referencia: pd.DatetimeIndex | None = None,
) -> pd.DataFrame:
    colunas = ["mes", "total_qtd", "total_frota", "percentual_qtd_x_frota"]
    if meses_referencia is None:
        return pd.DataFrame(columns=colunas)

    evolucao = pd.DataFrame({"mes": meses_referencia})
    evolucao["total_qtd"] = 0
    evolucao["total_frota"] = 0
    evolucao["percentual_qtd_x_frota"] = 0.0
    return evolucao[colunas]


def montar_evolucao_mensal(
    df_filtrado: pd.DataFrame,
    limite_meses: int | None = None,
    periodo: tuple[pd.Timestamp, pd.Timestamp] | None = None,
) -> pd.DataFrame:
    meses_referencia = None
    if isinstance(periodo, tuple) and len(periodo) == 2:
        mes_inicial = pd.Timestamp(periodo[0]).to_period("M").to_timestamp()
        mes_final = pd.Timestamp(periodo[1]).to_period("M").to_timestamp()
        if mes_inicial <= mes_final:
            meses_referencia = pd.date_range(mes_inicial, mes_final, freq="MS")

    if df_filtrado.empty:
        return _evolucao_mensal_vazia(meses_referencia)

    df_aux = df_filtrado.copy()
    df_aux["mes"] = _obter_serie_competencia(df_aux)
    df_aux = df_aux[df_aux["mes"].notna()]
    if df_aux.empty:
        return _evolucao_mensal_vazia(meses_referencia)

    if meses_referencia is not None:
        df_aux = df_aux[
            df_aux["mes"].between(meses_referencia.min(), meses_referencia.max())
        ]
    elif limite_meses is not None and limite_meses > 0:
        mes_final = df_aux["mes"].max()
        mes_inicial = mes_final - pd.DateOffset(months=limite_meses - 1)
        meses_referencia = pd.date_range(mes_inicial, mes_final, freq="MS")
        df_aux = df_aux[df_aux["mes"].between(mes_inicial, mes_final)]

    if df_aux.empty:
        return _evolucao_mensal_vazia(meses_referencia)

    evolucao = (
        df_aux.groupby("mes", as_index=False)
        .agg(
            total_qtd=("qtd", "sum"),
            total_frota=("frota", "sum"),
        )
        .sort_values("mes")
    )

    if meses_referencia is not None:
        evolucao = (
            pd.DataFrame({"mes": meses_referencia})
            .merge(evolucao, on="mes", how="left")
            .fillna({"total_qtd": 0, "total_frota": 0})
        )

    evolucao["percentual_qtd_x_frota"] = calcular_percentual_seguro(
        evolucao["total_qtd"],
        evolucao["total_frota"],
        decimais=2,
    )

    evolucao["total_qtd"] = evolucao["total_qtd"].astype(int)
    evolucao["total_frota"] = evolucao["total_frota"].astype(int)

    return evolucao


def montar_tabela_evolucao(df_filtrado: pd.DataFrame) -> pd.DataFrame:
    if df_filtrado.empty:
        return pd.DataFrame(
            columns=["mes", "equipamento", "total_qtd", "total_frota", "percentual_qtd_x_frota"]
        )

    df_aux = df_filtrado.copy()
    df_aux["mes"] = _obter_serie_competencia(df_aux)

    evolucao = (
        df_aux.groupby(["mes", "equipamento"], as_index=False)
        .agg(
            total_qtd=("qtd", "sum"),
            total_frota=("frota", "sum"),
        )
        .sort_values(["mes", "equipamento"])
    )

    evolucao["percentual_qtd_x_frota"] = calcular_percentual_seguro(
        evolucao["total_qtd"],
        evolucao["total_frota"],
        decimais=2,
    )

    evolucao["total_qtd"] = evolucao["total_qtd"].astype(int)
    evolucao["total_frota"] = evolucao["total_frota"].astype(int)

    return evolucao

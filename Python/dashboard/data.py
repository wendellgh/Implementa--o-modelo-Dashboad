import pandas as pd
import streamlit as st

from dashboard.config import BASE_QUERY, BASE_QUERY_2
from dashboard.database import get_engine


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

    competencia = pd.to_datetime(df[coluna_data], dayfirst=True, errors="coerce")

    if "data_competencia" in df.columns:
        competencia_banco = pd.to_datetime(
            df["data_competencia"],
            dayfirst=True,
            errors="coerce",
        )
        competencia = competencia_banco.fillna(competencia)

    df["data_competencia"] = competencia.dt.to_period("M").dt.to_timestamp()
    df["ano_mes"] = pd.to_numeric(
        df["data_competencia"].dt.strftime("%Y%m"),
        errors="coerce",
    ).astype("Int64")
    df["mes_ano"] = df["data_competencia"].dt.strftime("%m/%Y").fillna("")

    return df


def _obter_serie_competencia(df: pd.DataFrame) -> pd.Series:
    if "data_competencia" in df.columns:
        return (
            pd.to_datetime(df["data_competencia"], dayfirst=True, errors="coerce")
            .dt.to_period("M")
            .dt.to_timestamp()
        )

    return (
        pd.to_datetime(df["data_ref"], dayfirst=True, errors="coerce")
        .dt.to_period("M")
        .dt.to_timestamp()
    )


@st.cache_data
def carregar_base() -> pd.DataFrame:

    df = pd.read_sql(BASE_QUERY, get_engine())

    if df.empty:
        return df

    df["data_ref"] = pd.to_datetime(df["data_ref"], errors="coerce")
    df = _adicionar_colunas_competencia(df)

    for coluna in ["qtd", "frota", "percentual"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0)

    for coluna in ["id_contrato", "contrato", "id_operadora", "operadora", "cod_equipamento", "equipamento"]:
        df[coluna] = df[coluna].fillna("").astype(str).str.strip()

    return df

@st.cache_data
def carregar_base_outra_tabela() -> pd.DataFrame:
    dados_servicos = pd.read_sql(BASE_QUERY_2, get_engine())

    if dados_servicos.empty: 
        return dados_servicos
    
    colunas_obrigatorias = ["data_ref", "servico_executado", "qtd_servico"]
    colunas_ausentes = [
        coluna for coluna in colunas_obrigatorias if coluna not in dados_servicos.columns
    ]
    if colunas_ausentes:
        raise KeyError(
            "Colunas ausentes na consulta BASE_QUERY_2: "
            f"{', '.join(colunas_ausentes)}. "
            f"Colunas retornadas: {', '.join(dados_servicos.columns)}"
        )

    dados_servicos["data_ref"] = _converter_data_servicos(dados_servicos["data_ref"])
    dados_servicos = _adicionar_colunas_competencia(dados_servicos)
    dados_servicos["qtd_servico"] = pd.to_numeric(
        dados_servicos["qtd_servico"],
        errors="coerce"
    ).fillna(0)
    
    return dados_servicos


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

    resumo["percentual_recalculado"] = resumo.apply(
        lambda row: (row["total_qtd"] / row["total_frota"] * 100) if row["total_frota"] else 0.0,
        axis=1,
    )

    resumo["media_percentual"] = resumo["media_percentual"].round(2)
    resumo["percentual_recalculado"] = resumo["percentual_recalculado"].round(2)
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

    frota_contrato["mes_label"] = frota_contrato["mes"].apply(
        lambda mes: f"{meses_pt[mes.month]}/{mes:%y}"
    )
    frota_contrato["quantidade_frota"] = frota_contrato["quantidade_frota"].astype(int)

    return frota_contrato[colunas]


def montar_evolucao_mensal(
    df_filtrado: pd.DataFrame,
    limite_meses: int | None = None,
) -> pd.DataFrame:
    if df_filtrado.empty:
        return pd.DataFrame(
            columns=["mes", "total_qtd", "total_frota", "percentual_qtd_x_frota"]
        )

    df_aux = df_filtrado.copy()
    df_aux["mes"] = _obter_serie_competencia(df_aux)
    df_aux = df_aux[df_aux["mes"].notna()]
    if df_aux.empty:
        return pd.DataFrame(
            columns=["mes", "total_qtd", "total_frota", "percentual_qtd_x_frota"]
        )

    meses_referencia = None
    if limite_meses is not None and limite_meses > 0:
        mes_final = df_aux["mes"].max()
        mes_inicial = mes_final - pd.DateOffset(months=limite_meses - 1)
        meses_referencia = pd.date_range(mes_inicial, mes_final, freq="MS")
        df_aux = df_aux[df_aux["mes"].between(mes_inicial, mes_final)]

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

    evolucao["percentual_qtd_x_frota"] = evolucao.apply(
        lambda row: (row["total_qtd"] / row["total_frota"] * 100) if row["total_frota"] else 0.0,
        axis=1,
    ).round(2)

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

    evolucao["percentual_qtd_x_frota"] = evolucao.apply(
        lambda row: (row["total_qtd"] / row["total_frota"] * 100) if row["total_frota"] else 0.0,
        axis=1,
    ).round(2)

    evolucao["total_qtd"] = evolucao["total_qtd"].astype(int)
    evolucao["total_frota"] = evolucao["total_frota"].astype(int)

    return evolucao

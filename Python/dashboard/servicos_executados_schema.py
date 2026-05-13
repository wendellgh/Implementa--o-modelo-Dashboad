from __future__ import annotations

from collections.abc import Iterable
from typing import Any
import unicodedata

import pandas as pd

ANO_DATA_MINIMO = 1900
ANO_DATA_MAXIMO = 2100

COLUNAS_SERVICOS_EXECUTADOS = [
    "DATA",
    "DATA_COMPETENCIA",
    "ID_CONTRATO",
    "CONTRATO",
    "ID_EQUIPAMENTO",
    "EQUIPAMENTO",
    "ID_OPERADORA",
    "OPERADORA",
    "ID_SERVICO_EXECUTADO",
    "SERVIC_EXECUTADO",
    "QTD_SERVICO",
]

COLUNAS_SERVICOS_OBRIGATORIAS = [
    coluna for coluna in COLUNAS_SERVICOS_EXECUTADOS if coluna != "DATA_COMPETENCIA"
]

ALIASES_SERVICOS_EXECUTADOS = {
    "DATA": ["DATA", "DT", "DATA_REF"],
    "DATA_COMPETENCIA": ["DATA_COMPETENCIA", "COMPETENCIA", "DATA COMPETENCIA"],
    "ID_CONTRATO": ["ID_CONTRATO", "ID CONTRATO", "COD_CONTRATO", "COD CLIETE"],
    "CONTRATO": ["CONTRATO", "NOME_CONTRATO"],
    "ID_EQUIPAMENTO": ["ID_EQUIPAMENTO", "ID EQUIPAMENTO", "COD_EQUIPAMENTO", "PRODUTO"],
    "EQUIPAMENTO": ["EQUIPAMENTO", "DESCRICAO", "SERIE_PRODUTO"],
    "ID_OPERADORA": ["ID_OPERADORA", "ID OPERADORA", "COD_OPERADORA"],
    "OPERADORA": ["OPERADORA", "NOME_OPERADORA"],
    "ID_SERVICO_EXECUTADO": [
        "ID_SERVICO_EXECUTADO",
        "ID SERVICO EXECUTADO",
        "ID SERVIÇO EXECUTADO",
        "SERVICO_EXEC",
    ],
    "SERVIC_EXECUTADO": [
        "SERVIC_EXECUTADO",
        "SERVICO EXECUTADO",
        "SERVIÇO EXECUTADO",
        "SERVICO_EXECUTADO",
        "ABA_DESCSE",
        "ABA_DESCRI",
        "AAG_DESCRI",
    ],
    "QTD_SERVICO": ["QTD_SERVICO", "QTD SERVICO", "QTD SERVIÇO", "ABA_QUANT"],
}


def normalizar_nome_coluna(nome: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(nome).strip().upper())
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    partes = []
    for caractere in texto:
        partes.append(caractere if caractere.isalnum() else "_")
    return "_".join(parte for parte in "".join(partes).split("_") if parte)


def _indice_colunas(df: pd.DataFrame) -> dict[str, list[str]]:
    indice: dict[str, list[str]] = {}
    for coluna in df.columns:
        indice.setdefault(normalizar_nome_coluna(coluna), []).append(str(coluna))
    return indice


def _serie_vazia(df: pd.DataFrame) -> pd.Series:
    return pd.Series("", index=df.index, dtype="object")


def _primeira_coluna_preenchida(
    df: pd.DataFrame,
    indice: dict[str, list[str]],
    aliases: Iterable[str],
) -> pd.Series:
    resultado = _serie_vazia(df)

    for alias in aliases:
        for coluna in indice.get(normalizar_nome_coluna(alias), []):
            valores = df[coluna].fillna("").astype(str).str.strip()
            resultado = resultado.where(resultado.astype(str).str.strip().ne(""), valores)

    return resultado


def colunas_ausentes_servicos(df: pd.DataFrame) -> list[str]:
    indice = _indice_colunas(df)
    ausentes = []
    for coluna in COLUNAS_SERVICOS_OBRIGATORIAS:
        aliases = ALIASES_SERVICOS_EXECUTADOS[coluna]
        if not any(normalizar_nome_coluna(alias) in indice for alias in aliases):
            ausentes.append(coluna)
    return ausentes


def converter_datas_servicos(valores: pd.Series) -> pd.Series:
    texto = valores.fillna("").astype(str).str.strip()
    texto = texto.mask(texto.str.lower().isin(["", "nan", "nat", "none", "null"]), "")

    datas = pd.to_datetime(texto, format="%d/%m/%Y", errors="coerce")

    pendentes = datas.isna() & texto.ne("")
    if pendentes.any():
        datas.loc[pendentes] = pd.to_datetime(
            texto.loc[pendentes],
            format="%Y-%m-%d",
            errors="coerce",
        )

    pendentes = datas.isna() & texto.ne("")
    if pendentes.any():
        data_numerica = pd.to_numeric(texto.loc[pendentes], errors="coerce")
        datas.loc[pendentes] = pd.to_datetime(
            data_numerica,
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )

    pendentes = datas.isna() & texto.ne("")
    if pendentes.any():
        datas.loc[pendentes] = pd.to_datetime(
            texto.loc[pendentes],
            dayfirst=True,
            errors="coerce",
        )

    anos_invalidos = (
        datas.notna()
        & ~datas.dt.year.between(ANO_DATA_MINIMO, ANO_DATA_MAXIMO)
    )
    return datas.mask(anos_invalidos)


def competencia_mensal_formatada(valores: pd.Series) -> pd.Series:
    competencia = converter_datas_servicos(valores).dt.to_period("M").dt.to_timestamp()
    competencia_formatada = competencia.dt.strftime("%d/%m/%Y")
    return competencia_formatada.where(competencia.notna(), None)


def competencia_mensal_date(valores: pd.Series) -> pd.Series:
    competencia = converter_datas_servicos(valores).dt.to_period("M").dt.to_timestamp()
    return competencia.dt.date.where(competencia.notna(), None)


def normalizar_servicos_executados(
    df: pd.DataFrame,
    *,
    exigir_colunas: bool = True,
) -> pd.DataFrame:
    ausentes = colunas_ausentes_servicos(df)
    if exigir_colunas and ausentes:
        raise ValueError(
            "Colunas ausentes para normalizar servicos_executados: "
            f"{', '.join(ausentes)}. "
            f"Colunas recebidas: {', '.join(str(coluna) for coluna in df.columns)}"
        )

    if df.empty:
        return pd.DataFrame(columns=COLUNAS_SERVICOS_EXECUTADOS)

    indice = _indice_colunas(df)
    normalizado = pd.DataFrame(index=df.index)
    for coluna in COLUNAS_SERVICOS_EXECUTADOS:
        normalizado[coluna] = _primeira_coluna_preenchida(
            df,
            indice,
            ALIASES_SERVICOS_EXECUTADOS[coluna],
        )

    datas = converter_datas_servicos(normalizado["DATA"])
    normalizado["DATA"] = datas.dt.strftime("%d/%m/%Y").where(datas.notna(), None)

    competencia_existente = converter_datas_servicos(normalizado["DATA_COMPETENCIA"])
    competencia = competencia_existente.fillna(datas)
    competencia = competencia.dt.to_period("M").dt.to_timestamp()
    normalizado["DATA_COMPETENCIA"] = (
        competencia.dt.strftime("%d/%m/%Y").where(competencia.notna(), None)
    )

    for coluna in COLUNAS_SERVICOS_EXECUTADOS:
        if coluna in {"DATA", "DATA_COMPETENCIA", "QTD_SERVICO"}:
            continue
        normalizado[coluna] = normalizado[coluna].fillna("").astype(str).str.strip()

    normalizado["QTD_SERVICO"] = (
        pd.to_numeric(
            normalizado["QTD_SERVICO"].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        )
        .fillna(0)
        .round()
        .astype(int)
        .astype(str)
    )

    return normalizado[COLUNAS_SERVICOS_EXECUTADOS].reset_index(drop=True)

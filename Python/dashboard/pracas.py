from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd

COORDENACAO_SEM_MAPEAMENTO = "SEM COORDENACAO"
COORDENACAO_INATIVA = "INATIVA"
NOME_PRACA_DESATIVADA = "PRACA DESATIVADA"

PRACAS_POR_COORDENACAO = {
    "BRASILIA": {
        "ALI": "SANTO ANTONIO DO DESCOBERTO",
        "BSB": "BRASILIA",
        "CTD": "LUZIANIA CATEDRAL",
        "LZA": "LUZIANIA",
        "ROT": "NOVO GAMA DF",
        "TAG": "TAGUATUR",
        "UTB": "UTB",
    },
    "ESPIRITO SANTO": {
        "VIX": "VITORIA",
    },
    "NORDESTE": {
        "CE": "CEARA",
        "FOR": "FORTALEZA",
        "FRA": "FEIRA DE SANTANA",
        "IOS": "ILHEUS",
        "MCZ": "MACEIO",
        "MZC": "MACEIO",
        "REC": "RECIFE",
        "SSA": "SALVADOR",
        "THE": "TERESINA",
        "TIM": "TIMON",
    },
    "SUDESTE": {
        "BH": "BELO HORIZONTE",
        "BHZ": "BELO HORIZONTE",
        "CGN": "CONGONHAS",
        "CTG": "CONTAGEM",
        "DIV": "DIVINOPOLIS",
        "GOV": "GOVERNADOR VALADARES",
        "JDR": "SAO JOAO DEU REY",
        "MG": "MINAS GERAIS",
        "NLA": "NOVA LIMA",
        "OBR": "OURO BRANCO",
        "OPR": "OURO PRETO",
        "PNV": "PONTE NOVA",
        "SUP": "SINDIPAUTRAS",
        "TFL": "TEOFILO OTONI",
        "TRR": "TRANSA TRANSPORTES",
        "UDI": "UBERLANDIA",
    },
    "SUL": {
        "FLE": "METROPOLITADO FLORIANOPOLIS ESTRELA",
        "FLN": "FLORIANOPOLIS",
        "POA": "PORTO ALEGRE",
    },
}


PRACAS_POR_SIGLA = {
    sigla: {
        "nome_praca": nome_praca,
        "coordenacao": coordenacao,
    }
    for coordenacao, pracas in PRACAS_POR_COORDENACAO.items()
    for sigla, nome_praca in pracas.items()
}

PRACA_POR_CONTRATO = {
    "AC TRANSPORTES": "LZA",
    "ALAGOINHAS": "SSA",
    "ARAGUARINA": "BSB",
    "BRT SSA": "SSA",
    "CAMACARI SSA": "SSA",
    "CATEDRAL": "CTD",
    "CBTU": "BHZ",
    "CIDADE DAS AGUAS": "BSB",
    "COOTRAPS CE": "FOR",
    "DIVPASS": "DIV",
    "FLORIANOPOLIS": "FLN",
    "GOV VALADARES": "GOV",
    "GVBUS": "VIX",
    "MARIANA": "BHZ",
    "METRO BAHIA": "SSA",
    "METRO BH": "BHZ",
    "METROFOR": "FOR",
    "METROPOLITANO BAHIA": "SSA",
    "MMC MACEIO": "MZC",
    "OURO BRANCO": "OBR",
    "ROSA TURISMO": "FRA",
    "ROTA DO SOL": "ROT",
    "SAO JOAO": "FRA",
    "SAO JOAO DEL REI": "JDR",
    "SAO JORGE": "PNV",
    "SETUT": "THE",
    "SINDPAUTRAS": "SUP",
    "TAGUATUR": "TAG",
    "TAGUATUR PM NOVO": "ALI",
    "TEU": "POA",
    "TRANSCARD": "SSA",
    "TRANSFACIL": "BHZ",
    "TRANSUPLE": "SUP",
    "TRENSURB": "POA",
    "TURIN CONGONHAS": "CGN",
    "TURIN OURO PRETO MG": "OPR",
    "UTB": "UTB",
    "VALE DO MUCURY": "TFL",
    "VIA OURO": "NLA",
}

CONTRATOS_PRACA_DESATIVADA = {
    "SINTRAM V3000",
    "SINTRAM V4000",
    "SINTRAM DMX200S",
    "SINTRAM PDM03",
}


def normalizar_nome_contrato(valor: Any) -> str:
    if valor is None or pd.isna(valor):
        return ""

    texto = unicodedata.normalize("NFKD", str(valor).strip().upper())
    texto = "".join(
        caractere for caractere in texto if not unicodedata.combining(caractere)
    )
    texto = re.sub(r"[^A-Z0-9]+", " ", texto)
    return " ".join(texto.split())


PRACA_POR_CONTRATO_NORMALIZADO = {
    normalizar_nome_contrato(contrato): sigla
    for contrato, sigla in PRACA_POR_CONTRATO.items()
}

CONTRATOS_PRACA_DESATIVADA_NORMALIZADOS = {
    normalizar_nome_contrato(contrato)
    for contrato in CONTRATOS_PRACA_DESATIVADA
}


def normalizar_sigla_praca(valor: Any) -> str:
    if valor is None or pd.isna(valor):
        return ""

    texto = str(valor).strip().upper()
    if texto.lower() in {"nan", "nat", "none", "null"}:
        return ""

    return re.sub(r"[^A-Z0-9]", "", texto)


def obter_nome_praca(sigla: Any) -> str:
    sigla_normalizada = normalizar_sigla_praca(sigla)
    if not sigla_normalizada:
        return ""

    metadados = PRACAS_POR_SIGLA.get(sigla_normalizada)
    if metadados is None:
        return sigla_normalizada

    return metadados["nome_praca"]


def obter_coordenacao_praca(sigla: Any) -> str:
    sigla_normalizada = normalizar_sigla_praca(sigla)
    if not sigla_normalizada:
        return ""

    metadados = PRACAS_POR_SIGLA.get(sigla_normalizada)
    if metadados is None:
        return COORDENACAO_SEM_MAPEAMENTO

    return metadados["coordenacao"]


def obter_praca_por_contrato(contrato: Any) -> str:
    contrato_normalizado = normalizar_nome_contrato(contrato)
    if not contrato_normalizado:
        return ""

    return PRACA_POR_CONTRATO_NORMALIZADO.get(contrato_normalizado, "")


def obter_nome_praca_por_contrato(contrato: Any) -> str:
    contrato_normalizado = normalizar_nome_contrato(contrato)
    if contrato_normalizado in CONTRATOS_PRACA_DESATIVADA_NORMALIZADOS:
        return NOME_PRACA_DESATIVADA

    return obter_nome_praca(obter_praca_por_contrato(contrato))


def obter_coordenacao_por_contrato(contrato: Any) -> str:
    contrato_normalizado = normalizar_nome_contrato(contrato)
    if contrato_normalizado in CONTRATOS_PRACA_DESATIVADA_NORMALIZADOS:
        return COORDENACAO_INATIVA

    sigla = obter_praca_por_contrato(contrato)
    return obter_coordenacao_praca(sigla) if sigla else ""


def enriquecer_dataframe_contratos(
    df: pd.DataFrame,
    *,
    coluna_contrato: str,
    coluna_praca: str,
    coluna_nome_praca: str,
    coluna_coordenacao: str,
) -> pd.DataFrame:
    if df.empty or coluna_contrato not in df.columns:
        return df

    enriquecido = df.copy()
    contratos = enriquecido[coluna_contrato]
    enriquecido[coluna_praca] = contratos.map(obter_praca_por_contrato)
    enriquecido[coluna_nome_praca] = contratos.map(obter_nome_praca_por_contrato)
    enriquecido[coluna_coordenacao] = contratos.map(obter_coordenacao_por_contrato)
    return enriquecido


def enriquecer_dataframe_pracas(
    df: pd.DataFrame,
    *,
    coluna_praca: str,
    coluna_nome_praca: str,
    coluna_coordenacao: str,
) -> pd.DataFrame:
    if df.empty or coluna_praca not in df.columns:
        return df

    enriquecido = df.copy()
    praca = enriquecido[coluna_praca].map(normalizar_sigla_praca)
    enriquecido[coluna_praca] = praca

    nome_atual = (
        enriquecido[coluna_nome_praca].fillna("").astype(str).str.strip()
        if coluna_nome_praca in enriquecido.columns
        else pd.Series("", index=enriquecido.index, dtype="object")
    )
    coordenacao_atual = (
        enriquecido[coluna_coordenacao].fillna("").astype(str).str.strip()
        if coluna_coordenacao in enriquecido.columns
        else pd.Series("", index=enriquecido.index, dtype="object")
    )

    nome_mapeado = praca.map(obter_nome_praca)
    coordenacao_mapeada = praca.map(obter_coordenacao_praca)

    enriquecido[coluna_nome_praca] = nome_mapeado.where(
        nome_mapeado.ne(""),
        nome_atual,
    )
    enriquecido[coluna_coordenacao] = coordenacao_mapeada.where(
        coordenacao_mapeada.ne(""),
        coordenacao_atual,
    )

    return enriquecido

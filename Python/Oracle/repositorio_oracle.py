import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from Oracle.conexao_oracle import get_oracle_connection
from Oracle.consultas_oracle import (
    QUERY_DESTBOAD,
    QUERY_DESTBOAD_COM_FILTRO_ABERTURA_OS,
)

ORACLE_DIR = Path(__file__).resolve().parent
DEFAULT_DESTBOAD_CSV = ORACLE_DIR / "saida_oracle_destboad.csv"


def validar_select(sql: str) -> None:
    sql_limpo = sql.strip().lower()

    comandos_bloqueados = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "merge",
        "create",
    ]

    if not sql_limpo.startswith("select"):
        raise ValueError("Somente consultas SELECT sao permitidas no Oracle.")

    for comando in comandos_bloqueados:
        if comando in sql_limpo:
            raise ValueError(f"Comando bloqueado no Oracle: {comando}")


def limpar_registro(registro: dict) -> dict:
    registro_limpo = {}

    for chave, valor in registro.items():
        if isinstance(valor, str):
            registro_limpo[chave] = valor.strip()
        else:
            registro_limpo[chave] = valor

    return registro_limpo


def limpar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df_limpo = df.copy()
    colunas_texto = df_limpo.select_dtypes(include=["object", "string"]).columns

    for coluna in colunas_texto:
        df_limpo[coluna] = df_limpo[coluna].map(
            lambda valor: valor.strip() if isinstance(valor, str) else valor
        )

    return df_limpo


def _normalizar_data_oracle(valor: date | datetime) -> str:
    if isinstance(valor, datetime):
        valor = valor.date()
    return valor.strftime("%Y%m%d")


def _montar_consulta_destboad(
    data_inicio: date | datetime | None = None,
) -> tuple[str, dict[str, object] | None]:
    if data_inicio is None:
        return QUERY_DESTBOAD, None

    return (
        QUERY_DESTBOAD_COM_FILTRO_ABERTURA_OS,
        {"data_inicio": _normalizar_data_oracle(data_inicio)},
    )


def consultar_oracle_dataframe(
    sql: str,
    params: dict[str, object] | None = None,
) -> pd.DataFrame:
    validar_select(sql)

    conexao = get_oracle_connection()

    try:
        df = pd.read_sql(sql, conexao, params=params)

        if df.empty:
            return df

        return limpar_dataframe(df)

    finally:
        conexao.close()


def consultar_oracle_json(
    sql: str,
    params: dict[str, object] | None = None,
) -> list[dict]:
    df = consultar_oracle_dataframe(sql, params=params)

    if df.empty:
        return []

    json_texto = df.to_json(
        orient="records",
        date_format="iso",
        force_ascii=False,
    )

    resultado = json.loads(json_texto)

    return [limpar_registro(item) for item in resultado]


def consultar_destboad_json(
    data_inicio: date | datetime | None = None,
) -> list[dict]:
    sql, params = _montar_consulta_destboad(data_inicio)
    return consultar_oracle_json(sql, params=params)


def consultar_destboad_dataframe(
    data_inicio: date | datetime | None = None,
) -> pd.DataFrame:
    sql, params = _montar_consulta_destboad(data_inicio)
    return consultar_oracle_dataframe(sql, params=params)


def gerar_destboad_csv(
    caminho_saida: str | Path | None = None,
    data_inicio: date | datetime | None = None,
) -> Path:
    caminho = Path(caminho_saida) if caminho_saida else DEFAULT_DESTBOAD_CSV
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df = consultar_destboad_dataframe(data_inicio=data_inicio)
    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    return caminho

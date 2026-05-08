import json
import pandas as pd

from Oracle.conexao_oracle import get_oracle_connection
from Oracle.consultas_oracle import QUERY_DESTBOAD


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
        "create"
    ]

    if not sql_limpo.startswith("select"):
        raise ValueError("Somente consultas SELECT são permitidas no Oracle.")

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


def consultar_oracle_json(sql: str) -> list[dict]:
    validar_select(sql)

    conexao = get_oracle_connection()

    try:
        df = pd.read_sql(sql, conexao)

        if df.empty:
            return []

        # Converte datas e tipos especiais para JSON válido
        json_texto = df.to_json(
            orient="records",
            date_format="iso",
            force_ascii=False
        )

        resultado = json.loads(json_texto)

        return [limpar_registro(item) for item in resultado]

    finally:
        conexao.close()


def consultar_destboad_json() -> list[dict]:
    return consultar_oracle_json(QUERY_DESTBOAD)

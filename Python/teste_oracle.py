import os
import json
from datetime import date, datetime
from decimal import Decimal

import oracledb
from dotenv import load_dotenv


# ============================================================
# CARREGAR VARIÁVEIS DO .ENV
# ============================================================

load_dotenv()


# ============================================================
# CONFIGURAÇÕES DO ORACLE
# ============================================================

ORACLE_USER = os.getenv("ORACLE_USER")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")

ORACLE_HOST = os.getenv("ORACLE_HOST", "172.32.51.127")
ORACLE_PORT = os.getenv("ORACLE_PORT", "1521")
ORACLE_SERVICE_NAME = os.getenv(
    "ORACLE_SERVICE_NAME",
    "sg01.tacvcnredepriva.bhzvcn.oraclevcn.com"
)

# Caminho correto do Oracle Instant Client
ORACLE_CLIENT_LIB_DIR = r"C:\oracle\instantclient_19_30"


# ============================================================
# QUERY DE TESTE
# ============================================================

QUERY_TESTE = """
SELECT *
FROM "SIGA"."DESTBOAD"
WHERE ROWNUM <= 5
"""


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def validar_variaveis() -> None:
    if not ORACLE_USER:
        raise ValueError("ORACLE_USER não foi configurado no arquivo .env")

    if not ORACLE_PASSWORD:
        raise ValueError("ORACLE_PASSWORD não foi configurado no arquivo .env")

    if not ORACLE_HOST:
        raise ValueError("ORACLE_HOST não foi configurado no arquivo .env")

    if not ORACLE_PORT:
        raise ValueError("ORACLE_PORT não foi configurado no arquivo .env")

    if not ORACLE_SERVICE_NAME:
        raise ValueError("ORACLE_SERVICE_NAME não foi configurado no arquivo .env")


def iniciar_oracle_client() -> None:
    """
    Inicia o Oracle Client em Thick Mode.
    """

    if not os.path.exists(ORACLE_CLIENT_LIB_DIR):
        raise FileNotFoundError(
            f"A pasta do Oracle Instant Client não foi encontrada: {ORACLE_CLIENT_LIB_DIR}"
        )

    oci_dll = os.path.join(ORACLE_CLIENT_LIB_DIR, "oci.dll")

    if not os.path.exists(oci_dll):
        raise FileNotFoundError(
            f"Arquivo oci.dll não encontrado em: {oci_dll}"
        )

    oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB_DIR)


def montar_dsn() -> str:
    return f"""
    (DESCRIPTION =
        (ADDRESS_LIST =
            (ADDRESS =
                (PROTOCOL = TCP)
                (HOST = {ORACLE_HOST})
                (PORT = {ORACLE_PORT})
            )
        )
        (CONNECT_DATA =
            (SERVICE_NAME = {ORACLE_SERVICE_NAME})
            (SERVER = DEDICATED)
        )
    )
    """


def converter_valor_json(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()

    if isinstance(valor, Decimal):
        return float(valor)

    if isinstance(valor, bytes):
        return valor.decode("utf-8", errors="ignore")

    return valor


def validar_select(sql: str) -> None:
    sql_limpo = sql.strip().lower()

    if not sql_limpo.startswith("select"):
        raise ValueError("Somente consultas SELECT são permitidas neste teste.")

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

    for comando in comandos_bloqueados:
        if comando in sql_limpo:
            raise ValueError(f"Comando bloqueado encontrado na query: {comando}")


def executar_consulta_json(sql: str) -> list[dict]:
    validar_select(sql)

    dsn = montar_dsn()

    conexao = oracledb.connect(
        user=ORACLE_USER,
        password=ORACLE_PASSWORD,
        dsn=dsn
    )

    try:
        cursor = conexao.cursor()
        cursor.execute(sql)

        colunas = [coluna[0] for coluna in cursor.description]
        registros = cursor.fetchall()

        resultado = []

        for linha in registros:
            item = {}

            for coluna, valor in zip(colunas, linha):
                item[coluna] = converter_valor_json(valor)

            resultado.append(item)

        cursor.close()

        return resultado

    finally:
        conexao.close()


# ============================================================
# EXECUÇÃO DO TESTE
# ============================================================

def main() -> None:
    print("=" * 80)
    print("TESTE DE CONEXÃO ORACLE - THICK MODE")
    print("=" * 80)

    try:
        print("Validando variáveis do .env...")
        validar_variaveis()

        print("Iniciando Oracle Instant Client...")
        print(f"Caminho usado: {ORACLE_CLIENT_LIB_DIR}")
        iniciar_oracle_client()

        print(f"Modo Thin ativo? {oracledb.is_thin_mode()}")
        print("Se aparecer False, está em Thick Mode.")
        print()

        print("Testando conexão com:")
        print(f"HOST: {ORACLE_HOST}")
        print(f"PORTA: {ORACLE_PORT}")
        print(f"SERVICE_NAME: {ORACLE_SERVICE_NAME}")
        print(f"USUÁRIO: {ORACLE_USER}")
        print()

        print("Executando query de teste:")
        print(QUERY_TESTE)

        dados = executar_consulta_json(QUERY_TESTE)

        print()
        print("Consulta realizada com sucesso.")
        print(f"Registros retornados: {len(dados)}")
        print()

        print("Resultado em JSON:")
        print(json.dumps(dados, indent=4, ensure_ascii=False))

    except Exception as erro:
        print()
        print("ERRO NO TESTE ORACLE")
        print("-" * 80)
        print(type(erro).__name__)
        print(erro)
        print("-" * 80)


if __name__ == "__main__":
    main()
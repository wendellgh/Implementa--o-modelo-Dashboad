"""Lista as tabelas do usuario conectado ao Oracle."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Permite executar este arquivo diretamente a partir de qualquer pasta.
PYTHON_DIR = Path(__file__).resolve().parents[1]
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

# O .env do projeto usa o caminho do container Linux. Ao executar no Windows,
# aproveita o Instant Client local ja utilizado pelos outros testes do projeto.
load_dotenv()
WINDOWS_ORACLE_CLIENT = Path(r"C:\oracle\instantclient_19_30")
client_configurado = os.getenv("ORACLE_CLIENT_LIB_DIR")
if (
    os.name == "nt"
    and WINDOWS_ORACLE_CLIENT.exists()
    and (not client_configurado or not Path(client_configurado).exists())
):
    os.environ["ORACLE_CLIENT_LIB_DIR"] = str(WINDOWS_ORACLE_CLIENT)

from Oracle.conexao_oracle import get_oracle_connection

# No Oracle, esta consulta e o equivalente a SHOW TABLES.
QUERY_LISTAR_TABELAS = """
SELECT TABLE_NAME
FROM USER_TABLES
ORDER BY TABLE_NAME
"""

LIMITE_EXIBICAO = 100


def listar_tabelas() -> list[str]:
    conexao = get_oracle_connection()

    try:
        with conexao.cursor() as cursor:
            cursor.execute(QUERY_LISTAR_TABELAS)
            return [linha[0] for linha in cursor.fetchall()]
    finally:
        conexao.close()


def main() -> None:
    print("Consultando as tabelas do usuario conectado ao Oracle...")
    print(QUERY_LISTAR_TABELAS.strip())
    print()

    try:
        tabelas = listar_tabelas()
    except Exception as erro:  # Script diagnostico: exibe a falha retornada pelo Oracle.
        print(f"Erro ao consultar o Oracle: {type(erro).__name__}: {erro}")
        raise SystemExit(1) from erro

    if not tabelas:
        print("Nenhuma tabela foi encontrada para o usuario conectado.")
        return

    exibir_todas = "--todos" in sys.argv[1:]
    tabelas_exibidas = tabelas if exibir_todas else tabelas[:LIMITE_EXIBICAO]

    print(f"{len(tabelas)} tabela(s) encontrada(s):")
    for tabela in tabelas_exibidas:
        print(f"- {tabela}")

    quantidade_oculta = len(tabelas) - len(tabelas_exibidas)
    if quantidade_oculta:
        print()
        print(f"... {quantidade_oculta} tabela(s) nao exibida(s).")
        print("Execute novamente com --todos para mostrar a lista completa.")


if __name__ == "__main__":
    main()

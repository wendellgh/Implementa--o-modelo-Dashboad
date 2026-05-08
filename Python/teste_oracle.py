import oracledb
import os
from dotenv import load_dotenv


load_dotenv()


user = os.getenv("ORACLE_USER")
password = os.getenv("ORACLE_PASSWORD")
host = os.getenv("ORACLE_HOST")
port = os.getenv("ORACLE_PORT", "1521")
service_name = os.getenv("ORACLE_SERVICE_NAME")

dsn = f"{host}:{port}/{service_name}"

print("Testando conexão Oracle...")
print(f"DSN: {dsn}")

try:
    conexao = oracledb.connect(
        user=user,
        password=password,
        dsn=dsn
    )

    print("Conexão realizada com sucesso!")

    cursor = conexao.cursor()

    cursor.execute("""
        SELECT *
        FROM "SIGA"."DESTBOAD"
        WHERE ROWNUM <= 5
    """)

    colunas = [coluna[0] for coluna in cursor.description]
    print("Colunas encontradas:")
    print(colunas)

    print("Registros:")
    for linha in cursor.fetchall():
        print(dict(zip(colunas, linha)))

    cursor.close()
    conexao.close()

except Exception as erro:
    print("Erro ao conectar ou consultar Oracle:")
    print(erro)
import os
import oracledb
from dotenv import load_dotenv


load_dotenv()


def get_oracle_connection():
    user = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_PASSWORD")
    host = os.getenv("ORACLE_HOST")
    port = os.getenv("ORACLE_PORT", "1521")
    service_name = os.getenv("ORACLE_SERVICE_NAME")

    if not user:
        raise ValueError("ORACLE_USER não foi configurado no .env")

    if not password:
        raise ValueError("ORACLE_PASSWORD não foi configurado no .env")

    if not host:
        raise ValueError("ORACLE_HOST não foi configurado no .env")

    if not service_name:
        raise ValueError("ORACLE_SERVICE_NAME não foi configurado no .env")

    dsn = f"{host}:{port}/{service_name}"

    return oracledb.connect(
        user=user,
        password=password,
        dsn=dsn
    )
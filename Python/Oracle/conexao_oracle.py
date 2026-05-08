import os
import oracledb
from dotenv import load_dotenv


load_dotenv()

_ORACLE_CLIENT_INICIADO = False


def iniciar_oracle_client() -> None:
    global _ORACLE_CLIENT_INICIADO

    if _ORACLE_CLIENT_INICIADO or not oracledb.is_thin_mode():
        return

    client_lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
    if not client_lib_dir:
        return

    if not os.path.exists(client_lib_dir):
        raise FileNotFoundError(
            f"A pasta do Oracle Instant Client nao foi encontrada: {client_lib_dir}"
        )

    oci_dll = os.path.join(client_lib_dir, "oci.dll")
    if not os.path.exists(oci_dll):
        raise FileNotFoundError(f"Arquivo oci.dll nao encontrado em: {oci_dll}")

    oracledb.init_oracle_client(lib_dir=client_lib_dir)
    _ORACLE_CLIENT_INICIADO = True


def get_oracle_connection():
    iniciar_oracle_client()

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

    dsn = oracledb.makedsn(host, int(port), service_name=service_name)

    return oracledb.connect(
        user=user,
        password=password,
        dsn=dsn
    )

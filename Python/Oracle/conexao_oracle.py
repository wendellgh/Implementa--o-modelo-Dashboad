import os
import oracledb
from dotenv import load_dotenv

try:
    import streamlit as st
    from streamlit.errors import StreamlitSecretNotFoundError
except ImportError:
    st = None


load_dotenv()

_ORACLE_CLIENT_INICIADO = False


def _get_secret_value(path: str) -> str | None:
    if st is None:
        return None

    parts = path.split(".")
    try:
        current = st.secrets
        for part in parts:
            current = current[part]
        return str(current)
    except (KeyError, TypeError, StreamlitSecretNotFoundError):
        return None


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value is None:
            continue

        text = str(value).strip()
        if text:
            return text

    return None


def _get_oracle_config() -> dict[str, str | None]:
    return {
        "user": _first_non_empty(
            _get_secret_value("oracle.user") or _get_secret_value("ORACLE_USER"),
            os.getenv("ORACLE_USER"),
        ),
        "password": _first_non_empty(
            _get_secret_value("oracle.password") or _get_secret_value("ORACLE_PASSWORD"),
            os.getenv("ORACLE_PASSWORD"),
        ),
        "host": _first_non_empty(
            _get_secret_value("oracle.host") or _get_secret_value("ORACLE_HOST"),
            os.getenv("ORACLE_HOST"),
        ),
        "port": _first_non_empty(
            _get_secret_value("oracle.port") or _get_secret_value("ORACLE_PORT"),
            os.getenv("ORACLE_PORT"),
            "1521",
        ),
        "service_name": _first_non_empty(
            _get_secret_value("oracle.service_name")
            or _get_secret_value("ORACLE_SERVICE_NAME"),
            os.getenv("ORACLE_SERVICE_NAME"),
        ),
        "client_lib_dir": _first_non_empty(
            _get_secret_value("oracle.client_lib_dir")
            or _get_secret_value("ORACLE_CLIENT_LIB_DIR"),
            os.getenv("ORACLE_CLIENT_LIB_DIR"),
        ),
    }


def iniciar_oracle_client() -> None:
    global _ORACLE_CLIENT_INICIADO

    if _ORACLE_CLIENT_INICIADO or not oracledb.is_thin_mode():
        return

    client_lib_dir = _get_oracle_config()["client_lib_dir"]
    if not client_lib_dir:
        return

    if not os.path.exists(client_lib_dir):
        raise FileNotFoundError(
            f"A pasta do Oracle Instant Client nao foi encontrada: {client_lib_dir}"
        )

    client_library = "oci.dll" if os.name == "nt" else "libclntsh.so"
    client_library_path = os.path.join(client_lib_dir, client_library)
    if not os.path.exists(client_library_path):
        raise FileNotFoundError(
            f"Biblioteca do Oracle Instant Client nao encontrada: {client_library_path}"
        )

    oracledb.init_oracle_client(lib_dir=client_lib_dir)
    _ORACLE_CLIENT_INICIADO = True


def get_oracle_connection():
    iniciar_oracle_client()

    cfg = _get_oracle_config()
    user = cfg["user"]
    password = cfg["password"]
    host = cfg["host"]
    port = cfg["port"]
    service_name = cfg["service_name"]

    if not user:
        raise ValueError(
            "ORACLE_USER nao foi configurado em Secrets ou variavel de ambiente"
        )

    if not password:
        raise ValueError(
            "ORACLE_PASSWORD nao foi configurado em Secrets ou variavel de ambiente"
        )

    if not host:
        raise ValueError(
            "ORACLE_HOST nao foi configurado em Secrets ou variavel de ambiente"
        )

    if not service_name:
        raise ValueError(
            "ORACLE_SERVICE_NAME nao foi configurado em Secrets ou variavel de ambiente"
        )

    dsn = oracledb.makedsn(host, int(str(port)), service_name=service_name)

    return oracledb.connect(
        user=user,
        password=password,
        dsn=dsn,
    )

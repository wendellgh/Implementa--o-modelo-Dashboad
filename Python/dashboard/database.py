import os

import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

from dashboard.config import DB_SETTINGS


def _get_secret_value(path: str) -> str | None:
    parts = path.split(".")
    current = st.secrets
    try:
        for part in parts:
            current = current[part]
        return str(current)
    except Exception:
        return None


def _get_db_config() -> dict[str, str | None]:
    database_url = (
        _get_secret_value("database.url")
        or _get_secret_value("DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )

    if database_url:
        return {"database_url": database_url}

    return {
        "usuario": (
            _get_secret_value("database.user")
            or _get_secret_value("DB_USER")
            or os.getenv("DB_USER")
            or DB_SETTINGS["usuario"]
        ),
        "senha": (
            _get_secret_value("database.password")
            or _get_secret_value("DB_PASSWORD")
            or os.getenv("DB_PASSWORD")
            or DB_SETTINGS["senha"]
        ),
        "host": (
            _get_secret_value("database.host")
            or _get_secret_value("DB_HOST")
            or os.getenv("DB_HOST")
            or DB_SETTINGS["host"]
        ),
        "porta": (
            _get_secret_value("database.port")
            or _get_secret_value("DB_PORT")
            or os.getenv("DB_PORT")
            or DB_SETTINGS["porta"]
        ),
        "banco": (
            _get_secret_value("database.name")
            or _get_secret_value("DB_NAME")
            or os.getenv("DB_NAME")
            or DB_SETTINGS["banco"]
        ),
        "sslmode": (
            _get_secret_value("database.sslmode")
            or _get_secret_value("DB_SSLMODE")
            or os.getenv("DB_SSLMODE")
        ),
    }


@st.cache_resource
def get_engine() -> Engine:
    cfg = _get_db_config()
    engine_kwargs = {"pool_pre_ping": True}

    if cfg.get("database_url"):
        return create_engine(str(cfg["database_url"]), **engine_kwargs)

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=str(cfg["usuario"]),
        password=str(cfg["senha"]),
        host=str(cfg["host"]),
        port=int(str(cfg["porta"])),
        database=str(cfg["banco"]),
    )

    if cfg.get("sslmode"):
        engine_kwargs["connect_args"] = {"sslmode": str(cfg["sslmode"])}

    return create_engine(url, **engine_kwargs)

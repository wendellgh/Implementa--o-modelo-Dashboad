import os

import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import ArgumentError
from streamlit.errors import StreamlitSecretNotFoundError

from dashboard.config import DB_SETTINGS


def _get_secret_value(path: str) -> str | None:
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


def _normalize_database_url(url: str) -> str:
    trimmed = url.strip()
    if trimmed.startswith("postgres://"):
        return "postgresql://" + trimmed[len("postgres://") :]
    return trimmed


def _get_db_config() -> dict[str, str | None]:
    database_url = _first_non_empty(
        _get_secret_value("database.url")
        or _get_secret_value("DATABASE_URL"),
        _get_secret_value("database.neon_url"),
        _get_secret_value("database.neon_database_url"),
        _get_secret_value("NEON_DATABASE_URL"),
        _get_secret_value("connections.postgresql.url"),
        _get_secret_value("connections.db.url"),
        os.getenv("DATABASE_URL"),
        os.getenv("NEON_DATABASE_URL"),
    )

    if database_url:
        return {"database_url": _normalize_database_url(database_url)}

    return {
        "usuario": _first_non_empty(
            _get_secret_value("database.user")
            or _get_secret_value("DB_USER"),
            _get_secret_value("connections.postgresql.user"),
            _get_secret_value("connections.postgresql.username"),
            _get_secret_value("connections.db.user"),
            _get_secret_value("connections.db.username"),
            os.getenv("DB_USER"),
            DB_SETTINGS["usuario"],
        ),
        "senha": _first_non_empty(
            _get_secret_value("database.password")
            or _get_secret_value("DB_PASSWORD"),
            _get_secret_value("connections.postgresql.password"),
            _get_secret_value("connections.db.password"),
            os.getenv("DB_PASSWORD"),
            DB_SETTINGS["senha"],
        ),
        "host": _first_non_empty(
            _get_secret_value("database.host")
            or _get_secret_value("DB_HOST"),
            _get_secret_value("connections.postgresql.host"),
            _get_secret_value("connections.db.host"),
            os.getenv("DB_HOST"),
            DB_SETTINGS["host"],
        ),
        "porta": _first_non_empty(
            _get_secret_value("database.port")
            or _get_secret_value("DB_PORT"),
            _get_secret_value("connections.postgresql.port"),
            _get_secret_value("connections.db.port"),
            os.getenv("DB_PORT"),
            DB_SETTINGS["porta"],
        ),
        "banco": _first_non_empty(
            _get_secret_value("database.name")
            or _get_secret_value("DB_NAME"),
            _get_secret_value("connections.postgresql.database"),
            _get_secret_value("connections.postgresql.dbname"),
            _get_secret_value("connections.db.database"),
            _get_secret_value("connections.db.dbname"),
            os.getenv("DB_NAME"),
            DB_SETTINGS["banco"],
        ),
        "sslmode": _first_non_empty(
            _get_secret_value("database.sslmode")
            or _get_secret_value("DB_SSLMODE"),
            _get_secret_value("connections.postgresql.sslmode"),
            _get_secret_value("connections.postgresql.query.sslmode"),
            _get_secret_value("connections.db.sslmode"),
            _get_secret_value("connections.db.query.sslmode"),
            os.getenv("DB_SSLMODE"),
        ),
    }


def get_db_target_label() -> str:
    cfg = _get_db_config()

    if cfg.get("database_url"):
        try:
            parsed = make_url(str(cfg["database_url"]))
            host = parsed.host or "host-indefinido"
            port = f":{parsed.port}" if parsed.port else ""
            database = parsed.database or "db-indefinido"
            return f"{host}{port}/{database}"
        except ArgumentError:
            return "url-invalida"

    return f"{cfg.get('host')}:{cfg.get('porta')}/{cfg.get('banco')}"


def get_db_target_kind() -> str:
    cfg = _get_db_config()
    host = ""

    if cfg.get("database_url"):
        try:
            host = str(make_url(str(cfg["database_url"])).host or "")
        except ArgumentError:
            return "unknown"
    else:
        host = str(cfg.get("host") or "")

    host = host.lower()
    if "neon.tech" in host:
        return "neon"
    if host in {"localhost", "127.0.0.1", "::1", "postgres", "host.docker.internal"}:
        return "local"
    return "remote"


def _is_local_db_host(host: str | None) -> bool:
    normalized = str(host or "").strip().lower()
    return normalized in {"localhost", "127.0.0.1", "::1", "postgres", "host.docker.internal"}


def get_db_target_info() -> dict[str, str]:
    kind = get_db_target_kind()
    titles = {
        "neon": "Neon ativo",
        "local": "Banco local",
        "remote": "Banco remoto",
        "unknown": "Banco indefinido",
    }
    return {
        "kind": kind,
        "title": titles.get(kind, "Banco"),
        "label": get_db_target_label(),
    }


def get_db_diagnostics() -> dict[str, bool]:
    return {
        "secret_DATABASE_URL": bool(_first_non_empty(_get_secret_value("DATABASE_URL"), _get_secret_value("database.url"))),
        "secret_NEON_DATABASE_URL": bool(_first_non_empty(_get_secret_value("NEON_DATABASE_URL"), _get_secret_value("database.neon_url"), _get_secret_value("database.neon_database_url"))),
        "secret_DB_HOST": bool(_get_secret_value("DB_HOST") or _get_secret_value("database.host")),
        "secret_connections_postgresql_host": bool(_get_secret_value("connections.postgresql.host")),
        "env_DATABASE_URL": bool(os.getenv("DATABASE_URL")),
        "env_NEON_DATABASE_URL": bool(os.getenv("NEON_DATABASE_URL")),
        "env_DB_HOST": bool(os.getenv("DB_HOST")),
    }


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

    if cfg.get("sslmode") and not _is_local_db_host(str(cfg.get("host") or "")):
        engine_kwargs["connect_args"] = {"sslmode": str(cfg["sslmode"])}

    return create_engine(url, **engine_kwargs)

import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from dashboard.config import DB_SETTINGS


@st.cache_resource
def get_engine() -> Engine:
    connection_url = (
        "postgresql+psycopg2://"
        f"{DB_SETTINGS['usuario']}:{DB_SETTINGS['senha']}"
        f"@{DB_SETTINGS['host']}:{DB_SETTINGS['porta']}/{DB_SETTINGS['banco']}"
    )
    return create_engine(connection_url)


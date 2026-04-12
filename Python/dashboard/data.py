import pandas as pd
import streamlit as st

from dashboard.config import EVOLUCAO_QUERY, RESUMO_QUERY
from dashboard.database import get_engine


@st.cache_data
def carregar_resumo() -> pd.DataFrame:
    return pd.read_sql(RESUMO_QUERY, get_engine())


@st.cache_data
def carregar_evolucao() -> pd.DataFrame:
    df = pd.read_sql(EVOLUCAO_QUERY, get_engine())
    if not df.empty:
        df["mes"] = pd.to_datetime(df["mes"], errors="coerce")
    return df


def carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame]:
    return carregar_resumo(), carregar_evolucao()


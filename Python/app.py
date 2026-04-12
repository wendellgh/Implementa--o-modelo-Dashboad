import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

st.set_page_config(
    page_title="Dashboard de Serviços Executados",
    page_icon="📊",
    layout="wide"
)

# -----------------------------
# CONEXÃO COM POSTGRESQL
# -----------------------------
DB_USER = "app_user"
DB_PASSWORD = "app123"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "app_db"

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# -----------------------------
# FUNÇÃO DE CARGA
# -----------------------------
@st.cache_data
def carregar_dados():
    query = '''
        SELECT
            "DATA",
            "ID_CONTRATO",
            "CONTRATO",
            "ID_EQUIPAMENTO",
            "EQUIPAMENTO",
            "ID_OPERADORA",
            "OPERADORA",
            "ID_SERVICO_EXECUTADO",
            "SERVIC_EXECUTADO",
            "QTD_SERVICO"
        FROM servicos_executados
    '''
    df = pd.read_sql(query, engine)

    # Tratamentos
    df["DATA"] = pd.to_datetime(df["DATA"], format="%d/%m/%Y", errors="coerce")
    df["QTD_SERVICO"] = pd.to_numeric(df["QTD_SERVICO"], errors="coerce").fillna(0).astype(int)

    texto_cols = [
        "ID_CONTRATO", "CONTRATO", "ID_EQUIPAMENTO", "EQUIPAMENTO",
        "ID_OPERADORA", "OPERADORA", "ID_SERVICO_EXECUTADO", "SERVIC_EXECUTADO"
    ]

    for col in texto_cols:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df

df = carregar_dados()

# -----------------------------
# SIDEBAR - FILTROS
# -----------------------------
st.sidebar.header("Filtros")

data_min = df["DATA"].min()
data_max = df["DATA"].max()

periodo = st.sidebar.date_input(
    "Período",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max
)

contratos = sorted([x for x in df["CONTRATO"].dropna().unique() if x])
equipamentos = sorted([x for x in df["EQUIPAMENTO"].dropna().unique() if x])
servicos = sorted([x for x in df["SERVIC_EXECUTADO"].dropna().unique() if x])
operadoras = sorted([x for x in df["OPERADORA"].dropna().unique() if x])

filtro_contrato = st.sidebar.multiselect("Contrato", contratos)
filtro_equipamento = st.sidebar.multiselect("Equipamento", equipamentos)
filtro_servico = st.sidebar.multiselect("Serviço Executado", servicos)
filtro_operadora = st.sidebar.multiselect("Operadora", operadoras)

df_filtrado = df.copy()

if isinstance(periodo, tuple) and len(periodo) == 2:
    data_ini = pd.to_datetime(periodo[0])
    data_fim = pd.to_datetime(periodo[1])
    df_filtrado = df_filtrado[
        (df_filtrado["DATA"] >= data_ini) &
        (df_filtrado["DATA"] <= data_fim)
    ]

if filtro_contrato:
    df_filtrado = df_filtrado[df_filtrado["CONTRATO"].isin(filtro_contrato)]

if filtro_equipamento:
    df_filtrado = df_filtrado[df_filtrado["EQUIPAMENTO"].isin(filtro_equipamento)]

if filtro_servico:
    df_filtrado = df_filtrado[df_filtrado["SERVIC_EXECUTADO"].isin(filtro_servico)]

if filtro_operadora:
    df_filtrado = df_filtrado[df_filtrado["OPERADORA"].isin(filtro_operadora)]

# -----------------------------
# TÍTULO
# -----------------------------
st.title("📊 Dashboard de Serviços Executados")
st.markdown("Análise dos dados importados do PostgreSQL")

# -----------------------------
# MÉTRICAS
# -----------------------------
total_registros = len(df_filtrado)
total_servicos = df_filtrado["QTD_SERVICO"].sum()
qtd_contratos = df_filtrado["CONTRATO"].nunique()
qtd_equipamentos = df_filtrado["EQUIPAMENTO"].nunique()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total de Registros", f"{total_registros:,}".replace(",", "."))
col2.metric("Total de Serviços", f"{total_servicos:,}".replace(",", "."))
col3.metric("Contratos Únicos", f"{qtd_contratos:,}".replace(",", "."))
col4.metric("Equipamentos Únicos", f"{qtd_equipamentos:,}".replace(",", "."))

# -----------------------------
# GRÁFICO 1 - SERVIÇOS MAIS FREQUENTES
# -----------------------------
servicos_top = (
    df_filtrado.groupby("SERVIC_EXECUTADO", as_index=False)["QTD_SERVICO"]
    .sum()
    .sort_values("QTD_SERVICO", ascending=False)
    .head(10)
)

fig_servicos = px.bar(
    servicos_top,
    x="SERVIC_EXECUTADO",
    y="QTD_SERVICO",
    title="Top 10 Serviços Executados",
    text_auto=True
)
fig_servicos.update_layout(xaxis_title="Serviço", yaxis_title="Quantidade")

# -----------------------------
# GRÁFICO 2 - EVOLUÇÃO NO TEMPO
# -----------------------------
evolucao = (
    df_filtrado.groupby("DATA", as_index=False)["QTD_SERVICO"]
    .sum()
    .sort_values("DATA")
)

fig_evolucao = px.line(
    evolucao,
    x="DATA",
    y="QTD_SERVICO",
    markers=True,
    title="Evolução de Serviços por Data"
)
fig_evolucao.update_layout(xaxis_title="Data", yaxis_title="Quantidade")

# -----------------------------
# GRÁFICO 3 - POR CONTRATO
# -----------------------------
contrato_top = (
    df_filtrado.groupby("CONTRATO", as_index=False)["QTD_SERVICO"]
    .sum()
    .sort_values("QTD_SERVICO", ascending=False)
    .head(10)
)

fig_contratos = px.bar(
    contrato_top,
    x="CONTRATO",
    y="QTD_SERVICO",
    title="Top 10 Contratos por Quantidade de Serviços",
    text_auto=True
)
fig_contratos.update_layout(xaxis_title="Contrato", yaxis_title="Quantidade")

# -----------------------------
# LAYOUT DOS GRÁFICOS
# -----------------------------
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.plotly_chart(fig_servicos, use_container_width=True)

with col_graf2:
    st.plotly_chart(fig_contratos, use_container_width=True)

st.plotly_chart(fig_evolucao, use_container_width=True)

# -----------------------------
# TABELA DETALHADA
# -----------------------------
st.subheader("📋 Dados detalhados")

df_exibicao = df_filtrado.copy()
df_exibicao["DATA"] = df_exibicao["DATA"].dt.strftime("%d/%m/%Y")

st.dataframe(df_exibicao, use_container_width=True, height=400)

# -----------------------------
# DOWNLOAD CSV
# -----------------------------
csv = df_filtrado.copy()
csv["DATA"] = csv["DATA"].dt.strftime("%d/%m/%Y")
csv_bytes = csv.to_csv(index=False, sep=";").encode("utf-8-sig")

st.download_button(
    label="Baixar dados filtrados em CSV",
    data=csv_bytes,
    file_name="servicos_executados_filtrados.csv",
    mime="text/csv"
)
import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path

ARQUIVO_CSV = r"D:\Code\Python\Implementação modelo Dashboad\Importacoes\bsa_serv_exce.csv"

USUARIO = "app_user"
SENHA = "app123"
HOST = "localhost"
PORTA = "5432"
BANCO = "app_db"
TABELA = "servicos_executados"
CHUNKSIZE = 5000

engine = create_engine(
    f"postgresql+psycopg2://{USUARIO}:{SENHA}@{HOST}:{PORTA}/{BANCO}"
)

caminho_csv = Path(ARQUIVO_CSV)

if not caminho_csv.exists():
    raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_CSV}")

with engine.connect() as conn:
    print("Conexão OK")
    print(conn.execute(text("SELECT current_database();")).fetchone())

# teste de leitura antes de limpar a tabela
teste = pd.read_csv(
    ARQUIVO_CSV,
    sep=";",
    encoding="cp1252",
    nrows=5
)

teste.columns = teste.columns.str.strip()

print("Colunas encontradas no CSV:")
print(teste.columns.tolist())

colunas_csv_esperadas = [
    "DATA",
    "ID CONTRATO",
    "CONTRATO",
    "ID EQUIPAMENTO",
    "EQUIPAMENTO",
    "ID OPERADORA",
    "OPERADORA",
    "ID SERVICO EXECUTADO",
    "SERVICO EXECUTADO",
    "QTD SERVICO"
]

faltantes_csv = [col for col in colunas_csv_esperadas if col not in teste.columns]
if faltantes_csv:
    raise ValueError(f"Colunas ausentes no CSV: {faltantes_csv}")

with engine.begin() as conn:
    conn.execute(text(f'TRUNCATE TABLE {TABELA};'))
    print("Tabela limpa com sucesso.")

total_linhas = 0
total_datas_invalidas = 0

for chunk in pd.read_csv(
    ARQUIVO_CSV,
    sep=";",
    encoding="cp1252",
    chunksize=CHUNKSIZE,
    dtype=str
):
    chunk.columns = chunk.columns.str.strip()

    chunk = chunk.rename(columns={
        "DATA": "DATA",
        "ID CONTRATO": "ID_CONTRATO",
        "CONTRATO": "CONTRATO",
        "ID EQUIPAMENTO": "ID_EQUIPAMENTO",
        "EQUIPAMENTO": "EQUIPAMENTO",
        "ID OPERADORA": "ID_OPERADORA",
        "OPERADORA": "OPERADORA",
        "ID SERVICO EXECUTADO": "ID_SERVICO_EXECUTADO",
        "SERVICO EXECUTADO": "SERVIC_EXECUTADO",
        "QTD SERVICO": "QTD_SERVICO"
    })

    colunas_destino = [
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
    ]

    faltantes_destino = [col for col in colunas_destino if col not in chunk.columns]
    if faltantes_destino:
        raise ValueError(f"Colunas ausentes após rename: {faltantes_destino}")

    chunk = chunk[colunas_destino].copy()

    for col in [
        "ID_CONTRATO",
        "CONTRATO",
        "ID_EQUIPAMENTO",
        "EQUIPAMENTO",
        "ID_OPERADORA",
        "OPERADORA",
        "ID_SERVICO_EXECUTADO",
        "SERVIC_EXECUTADO"
    ]:
        chunk[col] = chunk[col].fillna("").astype(str).str.strip()

    chunk["QTD_SERVICO"] = (
        pd.to_numeric(chunk["QTD_SERVICO"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    data_numerica = pd.to_numeric(chunk["DATA"], errors="coerce")

    datas_convertidas = pd.to_datetime(
        data_numerica,
        unit="D",
        origin="1899-12-30",
        errors="coerce"
    )

    datas_invalidas_lote = datas_convertidas.isna().sum()
    total_datas_invalidas += int(datas_invalidas_lote)

    chunk["DATA"] = datas_convertidas.dt.strftime("%d/%m/%Y")
    chunk["DATA"] = chunk["DATA"].where(pd.notnull(chunk["DATA"]), None)

    chunk.to_sql(
        TABELA,
        engine,
        if_exists="append",
        index=False,
        method="multi"
    )

    total_linhas += len(chunk)
    print(f"{len(chunk)} linhas enviadas para o banco")

print("Importação concluída com sucesso.")
print(f"Total de linhas importadas: {total_linhas}")
print(f"Total de datas inválidas: {total_datas_invalidas}")
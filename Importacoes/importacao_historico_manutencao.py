import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path

ARQUIVO_CSV = Path(__file__).with_name("Basehistorica.csv")

USUARIO = "app_user"
SENHA = "app123"
HOST = "localhost"
PORTA = "5432"
BANCO = "app_db"
TABELA = "base_historica_manutencao"

engine = create_engine(
    f"postgresql+psycopg2://{USUARIO}:{SENHA}@{HOST}:{PORTA}/{BANCO}"
)

with engine.connect() as conn:
    print("Conexão OK")
    print(conn.execute(text("SELECT current_database();")).fetchone())

for chunk in pd.read_csv(
    ARQUIVO_CSV,
    sep=";",
    encoding="cp1252",
    chunksize=5000
):
    chunk = chunk.rename(columns={
        "DATA": "data_ref",
        "ID CONTRATO": "id_contrato",
        "CONTRATO": "contrato",
        "ID OPERADORA": "id_operadora",
        "OPERADORA": "operadora",
        "COD EQUIPAMENTO": "cod_equipamento",
        "EQUIPAMENTO": "equipamento",
        "FROTA": "frota",
        "QTD": "qtd",
        "%": "percentual"
    })

    chunk["data_ref"] = pd.to_datetime(
        chunk["data_ref"],
        unit="D",
        origin="1899-12-30",
        errors="coerce"
    ).dt.date

    chunk["percentual"] = (
        chunk["percentual"]
        .astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    chunk["percentual"] = pd.to_numeric(chunk["percentual"], errors="coerce")

    chunk["frota"] = pd.to_numeric(chunk["frota"], errors="coerce").fillna(0).astype(int)
    chunk["qtd"] = pd.to_numeric(chunk["qtd"], errors="coerce").fillna(0).astype(int)

    for col in [
        "id_contrato", "contrato", "id_operadora",
        "operadora", "cod_equipamento", "equipamento"
    ]:
        chunk[col] = chunk[col].astype(str).str.strip()

    chunk.to_sql(
        TABELA,
        engine,
        if_exists="append",
        index=False
    )

    print(f"{len(chunk)} linhas enviadas para o banco")

print("Importação concluída com sucesso.")

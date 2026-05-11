import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ARQUIVO_CSV = Path(__file__).with_name("bsa_serv_exce.csv")
PYTHON_DIR = Path(__file__).resolve().parents[1] / "Python"
sys.path.insert(0, str(PYTHON_DIR))

from dashboard.database import get_db_target_label, get_engine

TABELA = "servicos_executados"
CHUNKSIZE = 5000

engine = get_engine()

GARANTIR_COLUNAS_AUXILIARES_SQL = f"""
ALTER TABLE public.{TABELA}
    ADD COLUMN IF NOT EXISTS "DATA_COMPETENCIA" date;

UPDATE public.{TABELA}
SET "DATA_COMPETENCIA" = date_trunc(
    'month',
    CASE
        WHEN trim("DATA") ~ '^[0-9]{{2}}/[0-9]{{2}}/[0-9]{{4}}$'
            THEN to_date(trim("DATA"), 'DD/MM/YYYY')
        WHEN trim("DATA") ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'
            THEN trim("DATA")::date
        ELSE NULL
    END
)::date
WHERE "DATA" IS NOT NULL
  AND trim("DATA") <> ''
  AND (
      "DATA_COMPETENCIA" IS NULL
      OR "DATA_COMPETENCIA" <> date_trunc(
          'month',
          CASE
              WHEN trim("DATA") ~ '^[0-9]{{2}}/[0-9]{{2}}/[0-9]{{4}}$'
                  THEN to_date(trim("DATA"), 'DD/MM/YYYY')
              WHEN trim("DATA") ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'
                  THEN trim("DATA")::date
              ELSE NULL
          END
      )::date
  );
"""


def garantir_colunas_auxiliares() -> None:
    with engine.begin() as conn:
        conn.execute(text(GARANTIR_COLUNAS_AUXILIARES_SQL))


def converter_datas(valores: pd.Series) -> pd.Series:
    texto = valores.fillna("").astype(str).str.strip()
    datas = pd.to_datetime(texto, format="%d/%m/%Y", errors="coerce")

    pendentes = datas.isna() & texto.ne("")
    if pendentes.any():
        data_numerica = pd.to_numeric(texto.loc[pendentes], errors="coerce")
        datas.loc[pendentes] = pd.to_datetime(
            data_numerica,
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )

    pendentes = datas.isna() & texto.ne("")
    if pendentes.any():
        datas.loc[pendentes] = pd.to_datetime(
            texto.loc[pendentes],
            dayfirst=True,
            errors="coerce",
        )

    return datas


def converter_para_competencia_mensal(datas: pd.Series) -> pd.Series:
    competencia = datas.dt.to_period("M").dt.to_timestamp()
    return competencia.dt.date.where(competencia.notna(), None)

caminho_csv = Path(ARQUIVO_CSV)

if not caminho_csv.exists():
    raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_CSV}")

with engine.connect() as conn:
    print(f"Destino: {get_db_target_label()}")
    print("Conexão OK")
    print(conn.execute(text("SELECT current_database();")).fetchone())

garantir_colunas_auxiliares()

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
        "DATA_COMPETENCIA",
        "QTD_SERVICO"
    ]

    colunas_origem = [
        coluna for coluna in colunas_destino if coluna != "DATA_COMPETENCIA"
    ]
    faltantes_destino = [col for col in colunas_origem if col not in chunk.columns]
    if faltantes_destino:
        raise ValueError(f"Colunas ausentes após rename: {faltantes_destino}")

    chunk = chunk[colunas_origem].copy()

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

    datas_convertidas = converter_datas(chunk["DATA"])

    datas_invalidas_lote = datas_convertidas.isna().sum()
    total_datas_invalidas += int(datas_invalidas_lote)

    chunk["DATA_COMPETENCIA"] = converter_para_competencia_mensal(datas_convertidas)
    chunk["DATA"] = datas_convertidas.dt.strftime("%d/%m/%Y")
    chunk["DATA"] = chunk["DATA"].where(pd.notnull(chunk["DATA"]), None)
    chunk = chunk[colunas_destino]

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

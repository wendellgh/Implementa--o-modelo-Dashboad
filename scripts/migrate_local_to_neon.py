from __future__ import annotations
import argparse
import os
import sys
from collections.abc import Iterable

import pandas as pd
from sqlalchemy import inspect
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

DEFAULT_LOCAL_DATABASE_URL = "postgresql+psycopg2://app_user:app123@localhost:5432/app_db"



TABLES = [
    "base_historica_manutencao",
    "servicos_executados",
]

CREATE_SCHEMA_SQL = """
CREATE SEQUENCE IF NOT EXISTS public.base_historica_manutencao_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.base_historica_manutencao (
    id bigint NOT NULL DEFAULT nextval('public.base_historica_manutencao_id_seq'::regclass),
    data_ref date,
    data_competencia date,
    id_contrato character varying(50),
    contrato character varying(150),
    id_operadora character varying(50),
    operadora character varying(150),
    cod_equipamento character varying(50),
    equipamento character varying(100),
    frota integer,
    qtd integer,
    percentual numeric(10,2)
);

ALTER SEQUENCE public.base_historica_manutencao_id_seq
    OWNED BY public.base_historica_manutencao.id;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'base_historica_manutencao_pkey'
    ) THEN
        ALTER TABLE ONLY public.base_historica_manutencao
            ADD CONSTRAINT base_historica_manutencao_pkey PRIMARY KEY (id);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.servicos_executados (
    "DATA" text,
    "DATA_COMPETENCIA" date,
    "ID_CONTRATO" text,
    "CONTRATO" text,
    "ID_EQUIPAMENTO" text,
    "EQUIPAMENTO" text,
    "ID_OPERADORA" text,
    "OPERADORA" text,
    "ID_SERVICO_EXECUTADO" text,
    "SERVIC_EXECUTADO" text,
    "QTD_SERVICO" text
);

ALTER TABLE public.base_historica_manutencao
    ADD COLUMN IF NOT EXISTS data_competencia date;

ALTER TABLE public.servicos_executados
    ADD COLUMN IF NOT EXISTS "DATA_COMPETENCIA" date;

UPDATE public.base_historica_manutencao
SET data_competencia = date_trunc('month', data_ref)::date
WHERE data_ref IS NOT NULL
  AND (
      data_competencia IS NULL
      OR data_competencia <> date_trunc('month', data_ref)::date
  );

UPDATE public.servicos_executados
SET "DATA_COMPETENCIA" = date_trunc(
    'month',
    CASE
        WHEN trim("DATA") ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'
            THEN to_date(trim("DATA"), 'DD/MM/YYYY')
        WHEN trim("DATA") ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
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
              WHEN trim("DATA") ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'
                  THEN to_date(trim("DATA"), 'DD/MM/YYYY')
              WHEN trim("DATA") ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                  THEN trim("DATA")::date
              ELSE NULL
          END
      )::date
  );

CREATE INDEX IF NOT EXISTS idx_base_historica_manutencao_data_competencia
    ON public.base_historica_manutencao (data_competencia);

CREATE INDEX IF NOT EXISTS idx_servicos_executados_data_competencia
    ON public.servicos_executados ("DATA_COMPETENCIA");
"""

SYNC_SEQUENCE_SQL = """
SELECT setval(
    'public.base_historica_manutencao_id_seq',
    GREATEST(
        COALESCE((SELECT max(id) FROM public.base_historica_manutencao), 1),
        1
    ),
    true
);
"""




def normalize_database_url(database_url: str) -> str:
    trimmed = database_url.strip()
    if trimmed.startswith("postgres://"):
        return "postgresql://" + trimmed[len("postgres://") :]
    return trimmed


def label_database_url(database_url: str) -> str:
    parsed = make_url(database_url)
    host = parsed.host or "host-indefinido"
    port = f":{parsed.port}" if parsed.port else ""
    database = parsed.database or "db-indefinido"
    return f"{host}{port}/{database}"


def prepare_neon_migration_url(database_url: str) -> str:
    parsed = make_url(database_url)
    host = (parsed.host or "").lower()
    if "..." in host:
        raise ValueError(
            "A URL do Neon ainda parece ser um exemplo com reticencias. "
            "Copie a connection string real no Neon Console, sem '...'."
        )
    if "neon.tech" in host and "-pooler" in host:
        print(
            "Aviso: URL pooler detectada. O script vai usar a URL informada. "
            "Se houver erro de migracao, copie a URL direta no Neon Console."
        )

    return database_url


def make_engine(database_url: str) -> Engine:
    return create_engine(normalize_database_url(database_url), pool_pre_ping=True)


def count_rows(engine: Engine, table: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(f"SELECT count(*) FROM public.{table}")).scalar_one())


def count_rows_if_exists(engine: Engine, table: str) -> int | None:
    if not inspect(engine).has_table(table, schema="public"):
        return None
    return count_rows(engine, table)


def ensure_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(CREATE_SCHEMA_SQL))


def truncate_target_tables(engine: Engine, tables: Iterable[str]) -> None:
    joined_tables = ", ".join(f"public.{table}" for table in tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {joined_tables} RESTART IDENTITY;"))


def sync_sequence(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(SYNC_SEQUENCE_SQL))


def migrate_table(
    local_engine: Engine,
    neon_engine: Engine,
    table: str,
    chunksize: int,
) -> int:
    total_rows = 0
    query = f"SELECT * FROM public.{table}"

    for chunk in pd.read_sql_query(query, local_engine, chunksize=chunksize):
        chunk.to_sql(
            table,
            neon_engine,
            schema="public",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=chunksize,
        )
        total_rows += len(chunk)

    return total_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Substitui as tabelas do Neon pelos dados do Postgres local. "
            "Para apenas acrescentar o que falta, use append_missing_local_to_neon.py."
        )
    )
    parser.add_argument(
        "--local-url",
        default=os.getenv("LOCAL_DATABASE_URL", DEFAULT_LOCAL_DATABASE_URL),
        help="Connection string do Postgres local. Padrao: localhost app_db.",
    )
    parser.add_argument(
        "--neon-url",
        default=os.getenv("NEON_DATABASE_URL") or os.getenv("DATABASE_URL"),
        help="Connection string direta do Neon. Tambem aceita NEON_DATABASE_URL.",
    )
    parser.add_argument(
        "--substituir-tabelas-neon",
        "--substituir_tabelas_neon",
        "--replace-neon-tables",
        dest="replace_neon_tables",
        action="store_true",
        help=(
            "Trunca as tabelas alvo no Neon antes de copiar os dados locais. "
            "Use quando quiser recarregar tudo, nao para acrescentar meses novos."
        ),
    )
    parser.add_argument(
        "--executar",
        "--yes",
        dest="yes",
        action="store_true",
        help="Executa a migracao. Sem isto, o script apenas mostra contagens.",
    )
    parser.add_argument("--chunksize", type=int, default=5000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.neon_url:
        print("Erro: informe --neon-url ou defina NEON_DATABASE_URL.", file=sys.stderr)
        return 2

    local_url = normalize_database_url(args.local_url)
    neon_url = prepare_neon_migration_url(normalize_database_url(args.neon_url))

    local_engine = make_engine(local_url)
    neon_engine = make_engine(neon_url)

    print(f"Origem local: {label_database_url(local_url)}")
    print(f"Destino Neon: {label_database_url(neon_url)}")
    print("")
    print("Contagens antes da migracao:")
    for table in TABLES:
        local_count = count_rows(local_engine, table)
        neon_count = count_rows_if_exists(neon_engine, table)
        neon_label = "tabela ausente" if neon_count is None else str(neon_count)
        print(f"- {table}: local={local_count} neon={neon_label}")

    if not args.yes:
        print("")
        print(
            "Dry run: nada foi alterado. Para substituir tudo no Neon, use "
            "--executar --substituir-tabelas-neon."
            " Para acrescentar somente ausentes, "
            "rode scripts\\append_missing_local_to_neon.py --adicionar-dados."
        )
        return 0

    if not args.replace_neon_tables:
        print(
            "Erro: para evitar duplicidade, a migracao real exige "
            "--substituir-tabelas-neon.",
            file=sys.stderr,
        )
        return 2

    print("")
    print("Garantindo schema local...")
    ensure_schema(local_engine)

    print("Garantindo schema no Neon...")
    ensure_schema(neon_engine)

    print("Limpando tabelas no Neon...")
    truncate_target_tables(neon_engine, TABLES)

    print("Copiando dados...")
    for table in TABLES:
        rows = migrate_table(local_engine, neon_engine, table, args.chunksize)
        print(f"- {table}: {rows} linhas copiadas")

    sync_sequence(neon_engine)

    print("")
    print("Contagens depois da migracao:")
    for table in TABLES:
        local_count = count_rows(local_engine, table)
        neon_count = count_rows(neon_engine, table)
        print(f"- {table}: local={local_count} neon={neon_count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

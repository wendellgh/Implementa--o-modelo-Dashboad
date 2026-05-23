from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

sys.path.append(str(Path(__file__).resolve().parent))

from migrate_local_to_neon import (
    DEFAULT_LOCAL_DATABASE_URL,
    TABLES,
    ensure_schema,
    label_database_url,
    make_engine,
    normalize_database_url,
    prepare_neon_migration_url,
    sync_sequence,
    truncate_target_tables,
    count_rows_if_exists,
)


def migrate_table(
    neon_engine: Engine,
    local_engine: Engine,
    table: str,
    chunksize: int,
) -> int:
    total_rows = 0
    query = f"SELECT * FROM public.{table}"

    for chunk in pd.read_sql_query(query, neon_engine, chunksize=chunksize):
        chunk.to_sql(
            table,
            local_engine,
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
            "Migra os dados do Neon para o Postgres local do dashboard."
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
        "--replace-local-tables",
        action="store_true",
        help="Trunca as tabelas locais antes de copiar os dados do Neon.",
    )
    parser.add_argument(
        "--yes",
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

    print(f"Origem Neon: {label_database_url(neon_url)}")
    print(f"Destino local: {label_database_url(local_url)}")
    print("")
    print("Contagens antes da migracao:")
    for table in TABLES:
        local_count = count_rows_if_exists(local_engine, table) or 0
        neon_count = count_rows_if_exists(neon_engine, table) or 0
        print(f"- {table}: neon={neon_count} local={local_count}")

    if not args.yes:
        print("")
        print("Dry run: nada foi alterado. Para migrar, use --yes --replace-local-tables.")
        return 0

    if not args.replace_local_tables:
        print(
            "Erro: para evitar duplicidade, a migracao real exige --replace-local-tables.",
            file=sys.stderr,
        )
        return 2

    print("")
    print("Garantindo schema local...")
    ensure_schema(local_engine)

    print("Garantindo schema no Neon...")
    ensure_schema(neon_engine)

    print("Limpando tabelas locais...")
    truncate_target_tables(local_engine, TABLES)

    print("Copiando dados do Neon para o local...")
    for table in TABLES:
        rows = migrate_table(neon_engine, local_engine, table, args.chunksize)
        print(f"- {table}: {rows} linhas copiadas")

    sync_sequence(local_engine)

    print("")
    print("Contagens depois da migracao:")
    for table in TABLES:
        local_count = count_rows_if_exists(local_engine, table) or 0
        neon_count = count_rows_if_exists(neon_engine, table) or 0
        print(f"- {table}: neon={neon_count} local={local_count}")

    print("")
    print("Migracao completa. O banco local agora reflete os dados do Neon.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

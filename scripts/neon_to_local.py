from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

if __package__:
    from .migrate_local_to_neon import (
        DEFAULT_LOCAL_DATABASE_URL,
        TABLES,
        count_rows_if_exists,
        ensure_schema,
        label_database_url,
        load_project_dotenv,
        make_engine,
        normalize_database_url,
        prepare_neon_migration_url,
        sync_sequence,
        truncate_target_tables,
    )
else:
    from migrate_local_to_neon import (
        DEFAULT_LOCAL_DATABASE_URL,
        TABLES,
        count_rows_if_exists,
        ensure_schema,
        label_database_url,
        load_project_dotenv,
        make_engine,
        normalize_database_url,
        prepare_neon_migration_url,
        sync_sequence,
        truncate_target_tables,
    )

from sqlalchemy.engine import URL, Engine


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def build_database_url_from_parts(args: argparse.Namespace) -> str | None:
    values = {
        "DB_HOST": args.db_host,
        "DB_PORT": args.db_port,
        "DB_NAME": args.db_name,
        "DB_USER": args.db_user,
        "DB_PASSWORD": args.db_password,
    }

    required_without_defaults = [
        args.db_host,
        args.db_name,
        args.db_user,
        args.db_password,
    ]
    if not any(_first_non_empty(value) for value in required_without_defaults):
        return None

    missing = [name for name, value in values.items() if not _first_non_empty(value)]
    if missing:
        raise ValueError(
            "parametros DB incompletos: preencha "
            + ", ".join(missing)
            + " ou informe --neon-url."
        )

    query = {}
    sslmode = _first_non_empty(args.db_sslmode)
    if sslmode:
        query["sslmode"] = sslmode

    return URL.create(
        drivername="postgresql+psycopg2",
        username=str(args.db_user).strip(),
        password=str(args.db_password).strip(),
        host=str(args.db_host).strip(),
        port=int(str(args.db_port).strip()),
        database=str(args.db_name).strip(),
        query=query,
    ).render_as_string(hide_password=False)


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
            "Substitui os dados locais pelos dados do Neon. "
            "Use quando quiser espelhar o banco remoto no Postgres local."
        )
    )
    parser.add_argument(
        "--local-url",
        default=os.getenv("LOCAL_DATABASE_URL") or DEFAULT_LOCAL_DATABASE_URL,
        help="Connection string do Postgres local. Padrao: localhost app_db.",
    )
    parser.add_argument(
        "--neon-url",
        default=os.getenv("NEON_DATABASE_URL") or os.getenv("DATABASE_URL"),
        help="Connection string direta do Neon. Tambem aceita NEON_DATABASE_URL.",
    )
    parser.add_argument("--db-host", default=os.getenv("DB_HOST"))
    parser.add_argument("--db-port", default=os.getenv("DB_PORT") or "5432")
    parser.add_argument("--db-name", default=os.getenv("DB_NAME"))
    parser.add_argument("--db-user", default=os.getenv("DB_USER"))
    parser.add_argument("--db-password", default=os.getenv("DB_PASSWORD"))
    parser.add_argument("--db-sslmode", default=os.getenv("DB_SSLMODE") or "require")
    parser.add_argument(
        "--substituir-tabelas-local",
        "--substituir_tabelas_local",
        "--replace-local-tables",
        dest="replace_local_tables",
        action="store_true",
        help=(
            "Trunca as tabelas locais antes de copiar os dados do Neon. "
            "Use quando quiser recarregar tudo no local."
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
    load_project_dotenv()
    args = parse_args()
    neon_url_arg = _first_non_empty(args.neon_url)
    if not neon_url_arg:
        try:
            neon_url_arg = build_database_url_from_parts(args)
        except ValueError as error:
            print(f"Erro: {error}", file=sys.stderr)
            return 2

    if not neon_url_arg:
        print(
            "Erro: informe --neon-url, defina NEON_DATABASE_URL/DATABASE_URL "
            "ou preencha DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD.",
            file=sys.stderr,
        )
        return 2

    local_url = normalize_database_url(args.local_url)
    neon_url = prepare_neon_migration_url(normalize_database_url(neon_url_arg))

    local_engine = make_engine(local_url)
    neon_engine = make_engine(neon_url)

    print(f"Origem Neon: {label_database_url(neon_url)}")
    print(f"Destino local: {label_database_url(local_url)}")
    print()
    print("Contagens antes da migracao:")
    for table in TABLES:
        local_count = count_rows_if_exists(local_engine, table) or 0
        neon_count = count_rows_if_exists(neon_engine, table) or 0
        print(f"- {table}: neon={neon_count} local={local_count}")

    if not args.yes:
        print()
        print(
            "Dry run: nada foi alterado. Para substituir tudo no local, use "
            "--executar --substituir-tabelas-local."
        )
        return 0

    if not args.replace_local_tables:
        print(
            "Erro: para evitar duplicidade, a migracao real exige "
            "--substituir-tabelas-local.",
            file=sys.stderr,
        )
        return 2

    print()
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

    print()
    print("Contagens depois da migracao:")
    for table in TABLES:
        local_count = count_rows_if_exists(local_engine, table) or 0
        neon_count = count_rows_if_exists(neon_engine, table) or 0
        print(f"- {table}: neon={neon_count} local={local_count}")

    print()
    print("Migracao completa. O banco local agora reflete os dados do Neon.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

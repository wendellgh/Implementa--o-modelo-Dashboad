from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from collections.abc import Hashable
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

sys.path.append(str(Path(__file__).resolve().parent))

from migrate_local_to_neon import (  # noqa: E402
    DEFAULT_LOCAL_DATABASE_URL,
    TABLES,
    ensure_schema,
    label_database_url,
    make_engine,
    normalize_database_url,
    prepare_neon_migration_url,
    sync_sequence,
)


COMPARE_COLUMNS = {
    "base_historica_manutencao": [
        "data_ref",
        "data_competencia",
        "id_contrato",
        "contrato",
        "id_operadora",
        "operadora",
        "cod_equipamento",
        "equipamento",
        "frota",
        "qtd",
        "percentual",
    ],
    "servicos_executados": [
        "DATA",
        "DATA_COMPETENCIA",
        "ID_CONTRATO",
        "CONTRATO",
        "ID_EQUIPAMENTO",
        "EQUIPAMENTO",
        "ID_OPERADORA",
        "OPERADORA",
        "ID_SERVICO_EXECUTADO",
        "SERVIC_EXECUTADO",
        "QTD_SERVICO",
    ],
}


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def normalize_value(value: object) -> Hashable | None:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()  # dates and timestamps compare cleanly as text
    return value  # type: ignore[return-value]


def read_table(engine: Engine, table: str, columns: list[str]) -> pd.DataFrame:
    column_sql = ", ".join(quote_ident(column) for column in columns)
    query = f"SELECT {column_sql} FROM public.{quote_ident(table)}"
    return pd.read_sql_query(query, engine)


def row_key(row: pd.Series, columns: list[str]) -> tuple[Hashable | None, ...]:
    return tuple(normalize_value(row[column]) for column in columns)


def build_missing_rows(
    local_df: pd.DataFrame,
    neon_df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    local_counts = Counter(row_key(row, columns) for _, row in local_df.iterrows())
    neon_counts = Counter(row_key(row, columns) for _, row in neon_df.iterrows())

    remaining = {
        key: local_count - neon_counts.get(key, 0)
        for key, local_count in local_counts.items()
        if local_count > neon_counts.get(key, 0)
    }

    if not remaining:
        return local_df.iloc[0:0].copy()

    indexes: list[int] = []
    for index, row in local_df.iterrows():
        key = row_key(row, columns)
        count = remaining.get(key, 0)
        if count <= 0:
            continue
        indexes.append(index)
        remaining[key] = count - 1

    return local_df.loc[indexes, columns].copy()


def append_rows(
    neon_engine: Engine,
    table: str,
    missing_df: pd.DataFrame,
    chunksize: int,
) -> None:
    if missing_df.empty:
        return

    missing_df.to_sql(
        table,
        neon_engine,
        schema="public",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=chunksize,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Adiciona no Neon as linhas que existem no Postgres local, "
            "mas ainda nao existem no Neon. Nao apaga nem substitui dados."
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
        "--adicionar-dados",
        "--adicionar_dados",
        "--executar",
        "--yes",
        dest="yes",
        action="store_true",
        help=(
            "Executa a adicao dos dados ausentes no Neon, sem apagar o restante "
            "das tabelas. Sem isto, apenas mostra o que seria inserido."
        ),
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

    ensure_schema(local_engine)
    ensure_schema(neon_engine)
    sync_sequence(neon_engine)

    planned: list[tuple[str, pd.DataFrame]] = []

    print(
        "Modo acrescentar somente ausentes: compara local x Neon e insere "
        "apenas o que ainda nao existe no destino."
    )
    print("Linhas planejadas para adicionar sem apagar dados:")
    for table in TABLES:
        columns = COMPARE_COLUMNS[table]
        local_df = read_table(local_engine, table, columns)
        neon_df = read_table(neon_engine, table, columns)
        missing_df = build_missing_rows(local_df, neon_df, columns)
        planned.append((table, missing_df))
        print(
            f"- {table}: local={len(local_df)} neon={len(neon_df)} "
            f"adicionar={len(missing_df)}"
        )

    if not args.yes:
        print("")
        print(
            "Dry run: nada foi alterado. Para inserir somente ausentes sem "
            "apagar dados, use --adicionar-dados."
        )
        return 0

    print("")
    print("Inserindo apenas as linhas ausentes no Neon...")
    for table, missing_df in planned:
        append_rows(neon_engine, table, missing_df, args.chunksize)
        print(f"- {table}: {len(missing_df)} linhas adicionadas")

    sync_sequence(neon_engine)

    print("")
    print("Concluido. Os dados que ja estavam no Neon foram preservados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

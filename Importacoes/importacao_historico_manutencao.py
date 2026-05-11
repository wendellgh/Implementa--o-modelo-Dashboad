import argparse
import importlib
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import bindparam, text

ARQUIVO_CSV = Path(__file__).with_name("Basehistorica.csv")
PYTHON_DIR = Path(__file__).resolve().parents[1] / "Python"


TABELA = "base_historica_manutencao"
CHUNKSIZE = 5000

COLUNAS_CSV_ESPERADAS = [
    "DATA",
    "ID CONTRATO",
    "CONTRATO",
    "ID OPERADORA",
    "OPERADORA",
    "COD EQUIPAMENTO",
    "EQUIPAMENTO",
    "FROTA",
    "QTD",
    "%",
]

COLUNAS_DESTINO = [
    "data_ref",
    "id_contrato",
    "contrato",
    "id_operadora",
    "operadora",
    "cod_equipamento",
    "equipamento",
    "frota",
    "qtd",
    "percentual",
]

RENOMEAR_COLUNAS = {
    "DATA": "data_ref",
    "ID CONTRATO": "id_contrato",
    "CONTRATO": "contrato",
    "ID OPERADORA": "id_operadora",
    "OPERADORA": "operadora",
    "COD EQUIPAMENTO": "cod_equipamento",
    "EQUIPAMENTO": "equipamento",
    "FROTA": "frota",
    "QTD": "qtd",
    "%": "percentual",
}


def carregar_dependencias_banco():
    if str(PYTHON_DIR) not in sys.path:
        sys.path.insert(0, str(PYTHON_DIR))

    database = importlib.import_module("dashboard.database")
    return database.get_db_target_label, database.get_engine


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

    return datas.dt.date.where(datas.notna(), None)


def validar_csv(caminho_csv: Path) -> None:
    if not caminho_csv.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho_csv}")

    teste = pd.read_csv(
        caminho_csv,
        sep=";",
        encoding="cp1252",
        nrows=5,
        dtype=str,
    )
    teste.columns = teste.columns.str.strip()

    faltantes = [
        coluna for coluna in COLUNAS_CSV_ESPERADAS if coluna not in teste.columns
    ]
    if faltantes:
        raise ValueError(f"Colunas ausentes no CSV: {faltantes}")


def preparar_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    chunk.columns = chunk.columns.str.strip()
    chunk = chunk.rename(columns=RENOMEAR_COLUNAS)

    faltantes = [
        coluna for coluna in COLUNAS_DESTINO if coluna not in chunk.columns
    ]
    if faltantes:
        raise ValueError(f"Colunas ausentes apos rename: {faltantes}")

    chunk = chunk[COLUNAS_DESTINO].copy()
    chunk["data_ref"] = converter_datas(chunk["data_ref"])

    chunk["percentual"] = (
        chunk["percentual"]
        .fillna("")
        .astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )
    chunk["percentual"] = pd.to_numeric(chunk["percentual"], errors="coerce")

    chunk["frota"] = pd.to_numeric(
        chunk["frota"], errors="coerce"
    ).fillna(0).astype(int)
    chunk["qtd"] = pd.to_numeric(
        chunk["qtd"], errors="coerce"
    ).fillna(0).astype(int)

    for coluna in [
        "id_contrato",
        "contrato",
        "id_operadora",
        "operadora",
        "cod_equipamento",
        "equipamento",
    ]:
        chunk[coluna] = chunk[coluna].fillna("").astype(str).str.strip()

    return chunk


def ler_datas_csv(caminho_csv: Path) -> list[object]:
    datas: set[object] = set()
    for chunk in pd.read_csv(
        caminho_csv,
        sep=";",
        encoding="cp1252",
        chunksize=CHUNKSIZE,
        dtype=str,
        usecols=["DATA"],
    ):
        chunk.columns = chunk.columns.str.strip()
        datas.update(data for data in converter_datas(chunk["DATA"]).dropna().tolist())

    return sorted(datas)


def carregar_csv(
    caminho_csv: Path,
    substituir_tabela: bool,
    substituir_periodos_csv: bool,
    chunksize: int,
) -> int:
    validar_csv(caminho_csv)

    get_db_target_label, get_engine = carregar_dependencias_banco()
    engine = get_engine()
    with engine.connect() as conn:
        print(f"Destino: {get_db_target_label()}")
        print("Conexao OK")
        print(conn.execute(text("SELECT current_database();")).fetchone())

    if substituir_tabela:
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE public.{TABELA} RESTART IDENTITY;"))
        print(f"Tabela public.{TABELA} limpa com sucesso.")
    elif substituir_periodos_csv:
        datas_para_substituir = ler_datas_csv(caminho_csv)
        if datas_para_substituir:
            delete_sql = text(
                f"DELETE FROM public.{TABELA} WHERE data_ref IN :datas"
            ).bindparams(bindparam("datas", expanding=True))
            with engine.begin() as conn:
                conn.execute(delete_sql, {"datas": datas_para_substituir})
            print(
                "Periodos substituidos na tabela: "
                f"{len(datas_para_substituir)} data(s)."
            )

    total_linhas = 0
    total_datas_invalidas = 0

    for chunk in pd.read_csv(
        caminho_csv,
        sep=";",
        encoding="cp1252",
        chunksize=chunksize,
        dtype=str,
    ):
        chunk = preparar_chunk(chunk)
        total_datas_invalidas += int(chunk["data_ref"].isna().sum())

        chunk.to_sql(
            TABELA,
            engine,
            schema="public",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=chunksize,
        )

        total_linhas += len(chunk)
        print(f"{len(chunk)} linhas enviadas para o banco")

    print("Importacao concluida com sucesso.")
    print(f"Total de linhas importadas: {total_linhas}")
    print(f"Total de datas invalidas: {total_datas_invalidas}")
    return total_linhas


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importa Basehistorica.csv para base_historica_manutencao."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=ARQUIVO_CSV,
        help=f"Caminho do CSV. Padrao: {ARQUIVO_CSV}",
    )
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument(
        "--append",
        action="store_true",
        help="Adiciona as linhas do CSV sem apagar dados existentes.",
    )
    modo.add_argument(
        "--replace-table",
        action="store_true",
        help="Trunca public.base_historica_manutencao antes da carga.",
    )
    modo.add_argument(
        "--replace-periods",
        action="store_true",
        help="Remove da tabela apenas as datas presentes no CSV antes da carga.",
    )
    parser.add_argument("--chunksize", type=int, default=CHUNKSIZE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    carregar_csv(
        args.csv,
        substituir_tabela=args.replace_table,
        substituir_periodos_csv=args.replace_periods,
        chunksize=args.chunksize,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

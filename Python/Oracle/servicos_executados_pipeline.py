from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Hashable
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

PYTHON_DIR = Path(__file__).resolve().parents[1]
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from dashboard.servicos_executados_schema import (
    COLUNAS_SERVICOS_EXECUTADOS,
    competencia_mensal_date,
    normalizar_servicos_executados,
)
from dashboard.pracas import enriquecer_dataframe_pracas


ORACLE_DIR = Path(__file__).resolve().parent
CSV_DESTBOAD_BRUTO = ORACLE_DIR / "saida_oracle_destboad.csv"
CSV_SERVICOS_EXECUTADOS = ORACLE_DIR / "servicos_executados.csv"
TABELA_DESTINO = "servicos_executados"
CHUNKSIZE = 5000
ANO_DATA_MINIMO = 1900
ANO_DATA_MAXIMO = 2100

COLUNAS_DESTINO = COLUNAS_SERVICOS_EXECUTADOS

GARANTIR_COLUNAS_AUXILIARES_SQL = f"""
ALTER TABLE public.{TABELA_DESTINO}
    ADD COLUMN IF NOT EXISTS "DATA_COMPETENCIA" date;

ALTER TABLE public.{TABELA_DESTINO}
    ADD COLUMN IF NOT EXISTS "PRACA" text;

ALTER TABLE public.{TABELA_DESTINO}
    ADD COLUMN IF NOT EXISTS "NOME_PRACA" text;

ALTER TABLE public.{TABELA_DESTINO}
    ADD COLUMN IF NOT EXISTS "COORDENACAO" text;

UPDATE public.{TABELA_DESTINO}
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

COLUNAS_ORACLE_MINIMAS = [
    "COD_CLIETE",
    "NOME",
    "PRODUTO",
    "SERVICO_EXEC",
    "ABA_QUANT",
]

COLUNAS_CHAVE_DEDUPLICACAO = [
    coluna
    for coluna in COLUNAS_DESTINO
    if coluna not in {"PRACA", "NOME_PRACA", "COORDENACAO"}
]


def _normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df_normalizado = df.copy()
    df_normalizado.columns = [
        str(coluna).strip().upper() for coluna in df_normalizado.columns
    ]
    return df_normalizado


def _texto(df: pd.DataFrame, coluna: str, padrao: str = "") -> pd.Series:
    if coluna not in df.columns:
        return pd.Series(padrao, index=df.index, dtype="object")

    return df[coluna].fillna(padrao).astype(str).str.strip()


def _primeira_coluna_preenchida(
    df: pd.DataFrame,
    colunas: list[str],
    padrao: str = "",
) -> pd.Series:
    resultado = pd.Series(padrao, index=df.index, dtype="object")

    for coluna in colunas:
        if coluna not in df.columns:
            continue

        valores = _texto(df, coluna)
        resultado = resultado.where(resultado.astype(str).str.strip().ne(""), valores)

    return resultado


def _limpar_texto_data(valores: pd.Series) -> pd.Series:
    texto = valores.fillna("").astype(str).str.strip()
    texto = texto.mask(texto.str.lower().isin(["", "nan", "nat", "none", "null"]), "")

    anos = pd.to_numeric(
        texto.str.extract(r"(?<!\d)(\d{4})(?!\d)", expand=False),
        errors="coerce",
    )
    anos_invalidos = anos.notna() & ~anos.between(ANO_DATA_MINIMO, ANO_DATA_MAXIMO)

    return texto.mask(anos_invalidos, "")


def _converter_texto_para_data(
    valores: pd.Series,
    formato: str | None = None,
) -> pd.Series:
    texto = _limpar_texto_data(valores)

    if formato:
        datas = pd.to_datetime(texto, format=formato, errors="coerce")
    else:
        datas = pd.to_datetime(
            texto,
            format="mixed",
            dayfirst=True,
            errors="coerce",
        )

    anos_invalidos = (
        datas.notna()
        & ~datas.dt.year.between(ANO_DATA_MINIMO, ANO_DATA_MAXIMO)
    )
    return datas.mask(anos_invalidos)


def _datas_mes_ano(df: pd.DataFrame) -> pd.Series:
    if "MES" not in df.columns or "ANO" not in df.columns:
        return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")

    mes = pd.to_numeric(_texto(df, "MES"), errors="coerce")
    ano = pd.to_numeric(_texto(df, "ANO"), errors="coerce")
    valores_validos = (
        mes.between(1, 12)
        & ano.between(ANO_DATA_MINIMO, ANO_DATA_MAXIMO)
    )

    data_texto = pd.Series("", index=df.index, dtype="object")
    data_texto.loc[valores_validos] = (
        "01/"
        + mes.loc[valores_validos].astype("Int64").astype(str).str.zfill(2)
        + "/"
        + ano.loc[valores_validos].astype("Int64").astype(str)
    )

    return _converter_texto_para_data(data_texto, formato="%d/%m/%Y")


def _converter_datas(df: pd.DataFrame, agrupar_por_mes: bool) -> pd.Series:
    datas = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")

    for coluna in ["FECHAMENTO_OS", "ABERTURA_OS"]:
        if coluna not in df.columns:
            continue

        datas_coluna = _converter_texto_para_data(_texto(df, coluna))
        datas = datas.fillna(datas_coluna)

    datas = datas.fillna(_datas_mes_ano(df))

    if agrupar_por_mes:
        datas = datas.dt.to_period("M").dt.to_timestamp()

    datas_formatadas = datas.dt.strftime("%d/%m/%Y")
    return datas_formatadas.where(datas.notna(), None)


def ler_csv_destboad(caminho_csv: str | Path) -> pd.DataFrame:
    return pd.read_csv(
        caminho_csv,
        sep=None,
        engine="python",
        encoding="utf-8-sig",
        dtype=str,
    )


def _detectar_encoding_csv(caminho_csv: str | Path) -> str:
    for encoding in ["utf-8-sig", "cp1252"]:
        try:
            pd.read_csv(
                caminho_csv,
                sep=";",
                encoding=encoding,
                nrows=5,
                dtype=str,
            )
            return encoding
        except UnicodeDecodeError:
            continue

    return "utf-8-sig"


def validar_colunas_destboad(df_destboad: pd.DataFrame) -> None:
    faltantes = [
        coluna for coluna in COLUNAS_ORACLE_MINIMAS if coluna not in df_destboad.columns
    ]
    if faltantes:
        raise ValueError(f"Colunas ausentes no CSV Oracle: {faltantes}")

    tem_data_os = "FECHAMENTO_OS" in df_destboad.columns or "ABERTURA_OS" in df_destboad.columns
    tem_mes_ano = "MES" in df_destboad.columns and "ANO" in df_destboad.columns
    if not tem_data_os and not tem_mes_ano:
        raise ValueError(
            "CSV Oracle sem coluna de data esperada. Informe FECHAMENTO_OS, "
            "ABERTURA_OS ou MES/ANO."
        )


def transformar_destboad_em_servicos_executados(
    df_destboad: pd.DataFrame,
    agrupar_por_mes: bool = True,
) -> pd.DataFrame:
    df_oracle = _normalizar_colunas(df_destboad)

    if df_oracle.empty:
        return pd.DataFrame(columns=COLUNAS_DESTINO)

    validar_colunas_destboad(df_oracle)

    quantidade = pd.to_numeric(
        _texto(df_oracle, "ABA_QUANT").str.replace(",", ".", regex=False),
        errors="coerce",
    ).fillna(0)

    contrato_id = _texto(df_oracle, "COD_CLIETE")
    contrato = _texto(df_oracle, "NOME")

    df_servicos = pd.DataFrame(
        {
            "DATA": _converter_datas(df_oracle, agrupar_por_mes=False),
            "DATA_COMPETENCIA": _converter_datas(
                df_oracle,
                agrupar_por_mes=True,
            ),
            "ID_CONTRATO": contrato_id,
            "CONTRATO": contrato,
            "ID_EQUIPAMENTO": _texto(df_oracle, "PRODUTO"),
            "EQUIPAMENTO": _primeira_coluna_preenchida(
                df_oracle,
                ["DESCRICAO", "SERIE_PRODUTO"],
            ),
            "ID_OPERADORA": contrato_id,
            "OPERADORA": contrato,
            "ID_SERVICO_EXECUTADO": _texto(df_oracle, "SERVICO_EXEC"),
            "SERVIC_EXECUTADO": _primeira_coluna_preenchida(
                df_oracle,
                ["ABA_DESCSE", "ABA_DESCRI", "AAG_DESCRI"],
            ),
            "QTD_SERVICO": quantidade,
            "PRACA": _texto(df_oracle, "A1_PRACA"),
        }
    )

    df_servicos = enriquecer_dataframe_pracas(
        df_servicos,
        coluna_praca="PRACA",
        coluna_nome_praca="NOME_PRACA",
        coluna_coordenacao="COORDENACAO",
    )

    df_servicos = df_servicos[
        df_servicos["ID_SERVICO_EXECUTADO"].str.strip().ne("")
        | df_servicos["SERVIC_EXECUTADO"].str.strip().ne("")
    ].copy()

    if agrupar_por_mes and not df_servicos.empty:
        colunas_agrupamento = [
            coluna for coluna in COLUNAS_DESTINO if coluna not in {"DATA", "QTD_SERVICO"}
        ]
        df_servicos = (
            df_servicos.groupby(colunas_agrupamento, dropna=False, as_index=False)
            .agg(QTD_SERVICO=("QTD_SERVICO", "sum"))
        )
        df_servicos["DATA"] = df_servicos["DATA_COMPETENCIA"]

    return normalizar_servicos_executados(df_servicos)


def salvar_servicos_executados_csv(
    df_servicos: pd.DataFrame,
    caminho_csv: str | Path = CSV_SERVICOS_EXECUTADOS,
) -> Path:
    caminho = Path(caminho_csv)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df_servicos = normalizar_servicos_executados(df_servicos)
    df_servicos.to_csv(caminho, sep=";", index=False, encoding="utf-8-sig")
    return caminho


def transformar_destboad_csv(
    caminho_entrada: str | Path = CSV_DESTBOAD_BRUTO,
    caminho_saida: str | Path = CSV_SERVICOS_EXECUTADOS,
    agrupar_por_mes: bool = True,
) -> tuple[Path, int]:
    df_destboad = ler_csv_destboad(caminho_entrada)
    df_servicos = transformar_destboad_em_servicos_executados(
        df_destboad,
        agrupar_por_mes=agrupar_por_mes,
    )
    caminho = salvar_servicos_executados_csv(df_servicos, caminho_saida)
    return caminho, len(df_servicos)


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def normalizar_valor_chave(valor: object) -> Hashable | None:
    if pd.isna(valor):
        return None
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return valor  # type: ignore[return-value]


def _valor_para_date(valor: object) -> date | None:
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    convertido = pd.to_datetime(valor, errors="coerce")
    if pd.isna(convertido):
        return None
    return convertido.date()


def obter_ultima_data_servicos_executados() -> date | None:
    from dashboard.database import get_engine

    engine = get_engine()
    tabela_sql = f"public.{quote_ident(TABELA_DESTINO)}"

    with engine.connect() as conn:
        tabela_existe = conn.execute(
            text("SELECT to_regclass(:nome_tabela);"),
            {"nome_tabela": f"public.{TABELA_DESTINO}"},
        ).scalar()
        if tabela_existe is None:
            return None

        colunas = set(
            conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = :tabela
                    """
                ),
                {"tabela": TABELA_DESTINO},
            ).scalars()
        )

        if "DATA" in colunas:
            ultima_data = conn.execute(
                text(
                    f"""
                    SELECT MAX(
                        CASE
                            WHEN "DATA" IS NULL THEN NULL
                            WHEN trim("DATA"::text) ~ '^[0-9]{{2}}/[0-9]{{2}}/[0-9]{{4}}$'
                                THEN to_date(trim("DATA"::text), 'DD/MM/YYYY')
                            WHEN trim("DATA"::text) ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'
                                THEN trim("DATA"::text)::date
                            ELSE NULL
                        END
                    )
                    FROM {tabela_sql}
                    """
                )
            ).scalar()
            ultima_data_convertida = _valor_para_date(ultima_data)
            if ultima_data_convertida is not None:
                return ultima_data_convertida

        if "DATA_COMPETENCIA" in colunas:
            ultima_data = conn.execute(
                text(f'SELECT MAX("DATA_COMPETENCIA") FROM {tabela_sql}')
            ).scalar()
            return _valor_para_date(ultima_data)

    return None


def chave_linha(row: pd.Series, colunas: list[str]) -> tuple[Hashable | None, ...]:
    return tuple(normalizar_valor_chave(row[coluna]) for coluna in colunas)


def ler_contagem_linhas_existentes(engine: Engine) -> Counter[tuple[Hashable | None, ...]]:
    colunas_sql = ", ".join(quote_ident(coluna) for coluna in COLUNAS_CHAVE_DEDUPLICACAO)
    query = f"SELECT {colunas_sql} FROM public.{quote_ident(TABELA_DESTINO)}"
    existentes = pd.read_sql_query(query, engine)
    return Counter(
        chave_linha(row, COLUNAS_CHAVE_DEDUPLICACAO)
        for _, row in existentes.iterrows()
    )


def manter_apenas_linhas_ausentes(
    chunk: pd.DataFrame,
    contagem_existente: Counter[tuple[Hashable | None, ...]],
) -> pd.DataFrame:
    indices_para_inserir: list[int] = []

    for index, row in chunk.iterrows():
        chave = chave_linha(row, COLUNAS_CHAVE_DEDUPLICACAO)
        if contagem_existente.get(chave, 0) > 0:
            contagem_existente[chave] -= 1
            continue

        indices_para_inserir.append(index)

    return chunk.loc[indices_para_inserir].copy()


def carregar_servicos_executados_csv(
    caminho_csv: str | Path = CSV_SERVICOS_EXECUTADOS,
    substituir_tabela: bool = False,
    substituir_periodos_csv: bool = False,
    chunksize: int = CHUNKSIZE,
) -> int:
    caminho = Path(caminho_csv)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho}")

    encoding = _detectar_encoding_csv(caminho)
    teste = pd.read_csv(caminho, sep=";", encoding=encoding, nrows=5, dtype=str)
    teste.columns = teste.columns.str.strip()
    normalizar_servicos_executados(teste)

    from dashboard.database import get_db_target_label, get_engine

    engine = get_engine()
    with engine.connect() as conn:
        print(f"Destino: {get_db_target_label()}")
        print("Conexao OK")
        print(conn.execute(text("SELECT current_database();")).fetchone())

    with engine.begin() as conn:
        conn.execute(text(GARANTIR_COLUNAS_AUXILIARES_SQL))

    if substituir_tabela:
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE public.{TABELA_DESTINO};"))
            print(f"Tabela public.{TABELA_DESTINO} limpa com sucesso.")
        contagem_existente = Counter()
    elif substituir_periodos_csv:
        datas_csv = pd.read_csv(
            caminho,
            sep=";",
            encoding=encoding,
            dtype=str,
        )
        datas_csv = normalizar_servicos_executados(datas_csv)
        datas_para_substituir = sorted(
            data
            for data in competencia_mensal_date(datas_csv["DATA_COMPETENCIA"])
            .dropna()
            .tolist()
        )

        if datas_para_substituir:
            delete_sql = text(
                f"""
                DELETE FROM public.{TABELA_DESTINO}
                WHERE "DATA_COMPETENCIA" IN :datas
                """
            ).bindparams(bindparam("datas", expanding=True))
            with engine.begin() as conn:
                conn.execute(delete_sql, {"datas": datas_para_substituir})
            print(
                "Periodos substituidos na tabela: "
                f"{len(datas_para_substituir)} data(s)."
            )
        contagem_existente = Counter()
    else:
        print(
            "Modo acrescentar somente ausentes: o CSV sera comparado com o banco "
            "e apenas linhas que ainda nao existem serao inseridas."
        )
        contagem_existente = ler_contagem_linhas_existentes(engine)

    total_linhas = 0
    total_linhas_ja_existentes = 0
    for chunk in pd.read_csv(
        caminho,
        sep=";",
        encoding=encoding,
        chunksize=chunksize,
        dtype=str,
    ):
        chunk.columns = chunk.columns.str.strip()
        chunk = normalizar_servicos_executados(chunk)

        for coluna in COLUNAS_DESTINO:
            chunk[coluna] = chunk[coluna].fillna("").astype(str).str.strip()
        chunk["DATA_COMPETENCIA"] = competencia_mensal_date(chunk["DATA_COMPETENCIA"])

        if not substituir_tabela and not substituir_periodos_csv:
            linhas_antes_filtro = len(chunk)
            chunk = manter_apenas_linhas_ausentes(chunk, contagem_existente)
            total_linhas_ja_existentes += linhas_antes_filtro - len(chunk)

            if chunk.empty:
                print(
                    f"{linhas_antes_filtro} linhas ja existentes ignoradas; "
                    "nada novo neste bloco"
                )
                continue

        chunk.to_sql(
            TABELA_DESTINO,
            engine,
            schema="public",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=chunksize,
        )
        total_linhas += len(chunk)
        print(f"{len(chunk)} linhas enviadas para o banco")

    print(f"Total de linhas ja existentes ignoradas: {total_linhas_ja_existentes}")
    return total_linhas


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Exporta DESTBOAD do Oracle, gera CSV no formato servicos_executados "
            "e opcionalmente carrega a tabela PostgreSQL."
        )
    )
    parser.add_argument(
        "--from-csv",
        type=Path,
        help="Usa um CSV bruto ja existente e pula a consulta Oracle.",
    )
    parser.add_argument(
        "--raw-csv",
        type=Path,
        default=CSV_DESTBOAD_BRUTO,
        help=f"Caminho do CSV bruto DESTBOAD. Padrao: {CSV_DESTBOAD_BRUTO}",
    )
    parser.add_argument(
        "--target-csv",
        type=Path,
        default=CSV_SERVICOS_EXECUTADOS,
        help=f"Caminho do CSV final. Padrao: {CSV_SERVICOS_EXECUTADOS}",
    )
    parser.add_argument(
        "--sem-agrupar-mes",
        action="store_true",
        help="Mantem as linhas detalhadas do Oracle em vez de agregar por mes.",
    )
    parser.add_argument(
        "--load-db",
        action="store_true",
        help=(
            "Carrega o CSV final na tabela servicos_executados, inserindo por "
            "padrao apenas linhas ausentes."
        ),
    )
    modo_carga = parser.add_mutually_exclusive_group()
    modo_carga.add_argument(
        "--adicionar-dados",
        "--adicionar_dados",
        "--append",
        dest="append",
        action="store_true",
        help=(
            "Acrescenta dados sem apagar o restante da tabela. Compara o CSV "
            "com o banco e insere somente registros ausentes. Este ja e o "
            "padrao quando --load-db e usado sem modo de substituicao."
        ),
    )
    modo_carga.add_argument(
        "--replace-table",
        action="store_true",
        help="Trunca public.servicos_executados antes da carga.",
    )
    modo_carga.add_argument(
        "--replace-periods",
        action="store_true",
        help=(
            "Substitui somente os meses presentes no CSV: apaga esses periodos "
            "no banco e insere novamente."
        ),
    )
    parser.add_argument("--chunksize", type=int, default=CHUNKSIZE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.from_csv:
        csv_bruto = Path(args.from_csv)
        print(f"Usando CSV bruto existente: {csv_bruto}")
    else:
        from Oracle.repositorio_oracle import gerar_destboad_csv

        csv_bruto = gerar_destboad_csv(args.raw_csv)
        print(f"CSV bruto Oracle salvo em: {csv_bruto}")

    csv_servicos, total_servicos = transformar_destboad_csv(
        csv_bruto,
        args.target_csv,
        agrupar_por_mes=not args.sem_agrupar_mes,
    )
    print(f"CSV servicos_executados salvo em: {csv_servicos}")
    print(f"Linhas prontas para carga: {total_servicos}")

    if args.load_db:
        total_carregado = carregar_servicos_executados_csv(
            csv_servicos,
            substituir_tabela=args.replace_table,
            substituir_periodos_csv=args.replace_periods,
            chunksize=args.chunksize,
        )
        print(f"Total de linhas carregadas: {total_carregado}")
    else:
        print("Carga no banco nao executada. Use --load-db para carregar a tabela.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

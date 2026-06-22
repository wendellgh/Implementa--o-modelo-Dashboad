from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
import html
from pathlib import Path
import re
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.auth import usuario_eh_admin
from dashboard.pracas import enriquecer_dataframe_contratos, enriquecer_dataframe_pracas
from dashboard.styles import tema_claro_ativo

STATUS_COMPATIVEL = "Compatível"
STATUS_PARCIAL = "Parcial"
STATUS_DIVERGENTE = "Divergente"
STATUS_SEM_ENCONTRADO = "Sem encontrado"
STATUS_SEM_RECLAMADO = "Sem reclamado"

STATUS_ORDEM = [
    STATUS_COMPATIVEL,
    STATUS_PARCIAL,
    STATUS_DIVERGENTE,
    STATUS_SEM_ENCONTRADO,
    STATUS_SEM_RECLAMADO,
]

STATUS_CORES = {
    STATUS_COMPATIVEL: "#17803d",
    STATUS_PARCIAL: "#a16207",
    STATUS_DIVERGENTE: "#d92d20",
    STATUS_SEM_ENCONTRADO: "#6d28d9",
    STATUS_SEM_RECLAMADO: "#0b5ed7",
}

ORACLE_DESTBOAD_CSV = (
    Path(__file__).resolve().parents[1] / "Oracle" / "saida_oracle_destboad.csv"
)
ORACLE_DIR = ORACLE_DESTBOAD_CSV.parent
LISTA_DRS_CANDIDATOS = (
    ORACLE_DIR / "LISTA_DRs.csv",
    ORACLE_DIR / "LISTA DRs.csv",
    ORACLE_DIR / "lista_drs.csv",
    ORACLE_DIR / "lista drs.csv",
)

COLUNAS_ORACLE_MINIMAS = [
    "OS",
    "DEF_RECLAMADO",
    "DEF_ENCONTRADO",
]

ANO_DATA_MINIMO = 1900
ANO_DATA_MAXIMO = 2100

FALHAS_MES_INICIO_KEY = "falhas_mes_inicio"
FALHAS_MES_FIM_KEY = "falhas_mes_fim"
FALHAS_COORDENACAO_KEY = "falhas_coordenacao"
FALHAS_CONTRATO_KEY = "falhas_contrato"
FALHAS_OPERADORA_KEY = "falhas_operadora"
FALHAS_EQUIPAMENTO_KEY = "falhas_equipamento"
FALHAS_STATUS_KEY = "falhas_status"
FALHAS_OS_KEY = "falhas_os"
FALHAS_BUSCA_GERAL_KEY = "falhas_busca_geral"
FALHAS_DETALHE_PAGINA_KEY = "falhas_detalhe_pagina"
FALHAS_OS_POR_PAGINA = 10

STOPWORDS_DEFEITO = {
    "A",
    "AS",
    "COM",
    "DA",
    "DAS",
    "DE",
    "DO",
    "DOS",
    "E",
    "EM",
    "NA",
    "NO",
    "O",
    "OS",
    "PARA",
    "POR",
    "SEM",
}


@dataclass(frozen=True)
class DefeitoComparacao:
    label: str
    texto_normalizado: str
    codigo_numero: str


def _format_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _format_percent(value: float) -> str:
    return f"{value:.2f}%"


def _texto(valor: object) -> str:
    if valor is None or pd.isna(valor):
        return ""

    texto = str(valor).strip()
    if texto.lower() in {"nan", "nat", "none", "null"}:
        return ""

    return texto


def _normalizar_nome_coluna(nome: object) -> str:
    texto = unicodedata.normalize("NFKD", str(nome).strip().upper())
    texto = "".join(
        caractere for caractere in texto if not unicodedata.combining(caractere)
    )
    texto = re.sub(r"[^A-Z0-9]+", "_", texto)
    return "_".join(parte for parte in texto.split("_") if parte)


def _normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    normalizado = df.copy()
    normalizado.columns = [_normalizar_nome_coluna(coluna) for coluna in df.columns]
    return normalizado


def _serie_texto(df: pd.DataFrame, coluna: str) -> pd.Series:
    if coluna not in df.columns:
        return pd.Series("", index=df.index, dtype="object")

    return (
        df[coluna]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace({"nan": "", "NaN": "", "None": "", "NULL": ""})
    )


def _primeira_coluna_preenchida(df: pd.DataFrame, colunas: list[str]) -> pd.Series:
    resultado = pd.Series("", index=df.index, dtype="object")

    for coluna in colunas:
        if coluna not in df.columns:
            continue

        valores = _serie_texto(df, coluna)
        resultado = resultado.where(resultado.astype(str).str.strip().ne(""), valores)

    return resultado


def normalizar_texto_defeito(valor: object) -> str:
    texto = _texto(valor)
    if not texto:
        return ""

    texto = unicodedata.normalize("NFKD", texto.upper())
    texto = "".join(
        caractere for caractere in texto if not unicodedata.combining(caractere)
    )
    texto = re.sub(r"[^A-Z0-9]+", " ", texto)
    tokens = [
        token
        for token in texto.split()
        if len(token) > 1 and token not in STOPWORDS_DEFEITO
    ]
    return " ".join(tokens)


def _tokens_defeito(texto_normalizado: str) -> set[str]:
    return {
        token
        for token in texto_normalizado.split()
        if len(token) > 2 and token not in {"NAO", "DEF", "DEFEITO", "EQUIPAMENTO"}
    }


def _extrair_numero_codigo(valor: object) -> str:
    texto = _texto(valor).upper()
    encontrado = re.search(r"\bD[ER]\s*-?\s*0*([0-9]+)\b", texto)
    if not encontrado:
        return ""

    return encontrado.group(1)


def _eh_codigo_defeito(texto_normalizado: str) -> bool:
    return bool(re.fullmatch(r"D[ER]\s*[0-9]+", texto_normalizado.replace("_", " ")))


def _formatar_defeito(codigo: object, descricao: object) -> str:
    codigo_texto = _texto(codigo)
    descricao_texto = _texto(descricao)

    if descricao_texto and codigo_texto and descricao_texto != codigo_texto:
        return f"{descricao_texto} ({codigo_texto})"
    if descricao_texto:
        return descricao_texto
    return codigo_texto


def _defeito_reclamado(
    codigo: object,
    motivo: object,
    descricoes_drs: dict[str, str] | None = None,
) -> DefeitoComparacao | None:
    numero_codigo = _extrair_numero_codigo(codigo)
    descricao_dr = (descricoes_drs or {}).get(numero_codigo, "")
    label = _formatar_defeito(codigo, descricao_dr or motivo)
    if not label:
        return None

    texto_base = _texto(descricao_dr) or _texto(motivo) or _texto(codigo)
    return DefeitoComparacao(
        label=label,
        texto_normalizado=normalizar_texto_defeito(texto_base),
        codigo_numero=numero_codigo,
    )


def _defeito_encontrado(codigo: object, descricao: object) -> DefeitoComparacao | None:
    label = _formatar_defeito(codigo, descricao)
    if not label:
        return None

    texto_base = _texto(descricao) or _texto(codigo)
    return DefeitoComparacao(
        label=label,
        texto_normalizado=normalizar_texto_defeito(texto_base),
        codigo_numero=_extrair_numero_codigo(codigo),
    )


def _deduplicar_defeitos(
    defeitos: list[DefeitoComparacao | None],
) -> list[DefeitoComparacao]:
    vistos: set[tuple[str, str]] = set()
    unicos: list[DefeitoComparacao] = []

    for defeito in defeitos:
        if defeito is None:
            continue

        chave = (defeito.texto_normalizado, defeito.codigo_numero)
        if chave in vistos:
            continue

        vistos.add(chave)
        unicos.append(defeito)

    return unicos


def _defeitos_correspondem(
    reclamado: DefeitoComparacao,
    encontrado: DefeitoComparacao,
) -> bool:
    rec_texto = reclamado.texto_normalizado
    enc_texto = encontrado.texto_normalizado

    if rec_texto and enc_texto and rec_texto == enc_texto:
        return True

    if not rec_texto or not enc_texto:
        return False

    if _eh_codigo_defeito(rec_texto) or _eh_codigo_defeito(enc_texto):
        return False

    tokens_rec = _tokens_defeito(rec_texto)
    tokens_enc = _tokens_defeito(enc_texto)
    if tokens_rec and tokens_enc:
        intersecao = tokens_rec & tokens_enc
        uniao = tokens_rec | tokens_enc
        if len(intersecao) >= 2 or len(intersecao) / len(uniao) >= 0.65:
            return True

    return SequenceMatcher(None, rec_texto, enc_texto).ratio() >= 0.82


def _classificar_comparacao(
    reclamados: list[DefeitoComparacao],
    encontrados: list[DefeitoComparacao],
) -> str:
    if not reclamados and encontrados:
        return STATUS_SEM_RECLAMADO
    if reclamados and not encontrados:
        return STATUS_SEM_ENCONTRADO
    if not reclamados and not encontrados:
        return STATUS_DIVERGENTE

    reclamados_com_match: set[int] = set()
    encontrados_com_match: set[int] = set()

    for indice_rec, reclamado in enumerate(reclamados):
        for indice_enc, encontrado in enumerate(encontrados):
            if _defeitos_correspondem(reclamado, encontrado):
                reclamados_com_match.add(indice_rec)
                encontrados_com_match.add(indice_enc)

    if not reclamados_com_match:
        return STATUS_DIVERGENTE

    menor_lado_coberto = (
        len(reclamados_com_match) == len(reclamados)
        or len(encontrados_com_match) == len(encontrados)
    )
    if menor_lado_coberto:
        return STATUS_COMPATIVEL

    return STATUS_PARCIAL


def _limpar_texto_data(valores: pd.Series) -> pd.Series:
    texto = valores.fillna("").astype(str).str.strip()
    texto = texto.mask(texto.str.lower().isin(["", "nan", "nat", "none", "null"]), "")

    anos = pd.to_numeric(
        texto.str.extract(r"(?<!\d)(\d{4})(?!\d)", expand=False),
        errors="coerce",
    )
    anos_invalidos = anos.notna() & ~anos.between(ANO_DATA_MINIMO, ANO_DATA_MAXIMO)

    return texto.mask(anos_invalidos, "")


def _converter_texto_para_data(valores: pd.Series) -> pd.Series:
    texto = _limpar_texto_data(valores)
    datas = pd.to_datetime(texto, format="%d/%m/%Y", errors="coerce")

    pendentes = datas.isna() & texto.ne("")
    if pendentes.any():
        datas.loc[pendentes] = pd.to_datetime(
            texto.loc[pendentes],
            dayfirst=True,
            errors="coerce",
        )

    anos_invalidos = (
        datas.notna()
        & ~datas.dt.year.between(ANO_DATA_MINIMO, ANO_DATA_MAXIMO)
    )
    datas = datas.mask(anos_invalidos)

    return pd.to_datetime(datas, errors="coerce")


def _converter_datas_destboad(df: pd.DataFrame) -> pd.Series:
    datas = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")

    for coluna in ["FECHAMENTO_OS", "ABERTURA_OS"]:
        if coluna not in df.columns:
            continue

        valores = _converter_texto_para_data(_serie_texto(df, coluna))
        datas = datas.fillna(valores)

    if "MES" in df.columns and "ANO" in df.columns:
        mes = pd.to_numeric(_serie_texto(df, "MES"), errors="coerce")
        ano = pd.to_numeric(_serie_texto(df, "ANO"), errors="coerce")
        validos = mes.between(1, 12) & ano.between(ANO_DATA_MINIMO, ANO_DATA_MAXIMO)
        datas_mes = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
        datas_mes.loc[validos] = pd.to_datetime(
            {
                "year": ano.loc[validos].astype(int),
                "month": mes.loc[validos].astype(int),
                "day": 1,
            },
            errors="coerce",
        )
        datas = datas.fillna(datas_mes)

    return datas


def _normalizar_os(valor: object) -> str:
    texto = _texto(valor)
    if not texto:
        return ""

    if re.fullmatch(r"\d+", texto):
        return str(int(texto))

    return texto


def _juntar_labels(defeitos: list[DefeitoComparacao]) -> str:
    return " | ".join(defeito.label for defeito in defeitos)


def _validar_colunas_oracle(df: pd.DataFrame) -> None:
    faltantes = [coluna for coluna in COLUNAS_ORACLE_MINIMAS if coluna not in df.columns]
    if faltantes:
        raise ValueError(
            "Colunas ausentes na base Oracle para Análise de Falhas: "
            f"{', '.join(faltantes)}. "
            f"Colunas recebidas: {', '.join(df.columns)}"
        )


def _ler_csv_destboad(caminho_csv: Path) -> pd.DataFrame:
    return pd.read_csv(
        caminho_csv,
        sep=None,
        engine="python",
        encoding="utf-8-sig",
        dtype=str,
    )


def _resolver_lista_drs_csv() -> Path | None:
    for caminho in LISTA_DRS_CANDIDATOS:
        if caminho.exists():
            return caminho
    return None


def _detectar_encoding_csv(caminho_csv: Path) -> str:
    for encoding in ["utf-8-sig", "cp1252", "latin1"]:
        try:
            pd.read_csv(
                caminho_csv,
                sep=None,
                engine="python",
                encoding=encoding,
                nrows=5,
                dtype=str,
            )
            return encoding
        except UnicodeDecodeError:
            continue

    return "cp1252"


def _carregar_descricoes_drs(caminho_csv: Path | None) -> dict[str, str]:
    if caminho_csv is None or not caminho_csv.exists():
        return {}

    df_drs = pd.read_csv(
        caminho_csv,
        sep=None,
        engine="python",
        encoding=_detectar_encoding_csv(caminho_csv),
        dtype=str,
    )
    if df_drs.empty or len(df_drs.columns) < 2:
        return {}

    df_drs = _normalizar_colunas(df_drs)
    coluna_codigo = next(
        (
            coluna
            for coluna in df_drs.columns
            if "CODIGO" in coluna or "OCORRENCIA" in coluna
        ),
        df_drs.columns[0],
    )
    coluna_descricao = next(
        (
            coluna
            for coluna in df_drs.columns
            if "DESCRICAO" in coluna or "DEFEITO" in coluna
        ),
        df_drs.columns[1],
    )

    descricoes: dict[str, str] = {}
    for codigo, descricao in zip(
        _serie_texto(df_drs, coluna_codigo),
        _serie_texto(df_drs, coluna_descricao),
    ):
        numero_codigo = _extrair_numero_codigo(codigo)
        descricao = _texto(descricao)
        if numero_codigo and descricao:
            descricoes[numero_codigo] = descricao

    return descricoes


@st.cache_data(show_spinner="Carregando Análise de Falhas...")
def carregar_analise_falhas_por_os(
    caminho_csv: str,
    mtime: float,
    caminho_lista_drs: str | None = None,
    mtime_lista_drs: float = 0.0,
) -> pd.DataFrame:
    del mtime, mtime_lista_drs

    caminho = Path(caminho_csv)
    df_oracle = _normalizar_colunas(_ler_csv_destboad(caminho))
    descricoes_drs = _carregar_descricoes_drs(
        Path(caminho_lista_drs) if caminho_lista_drs else None
    )
    return montar_analise_falhas_por_os(df_oracle, descricoes_drs=descricoes_drs)


def montar_analise_falhas_por_os(
    df_oracle: pd.DataFrame,
    descricoes_drs: dict[str, str] | None = None,
) -> pd.DataFrame:
    colunas_resultado = [
        "os",
        "equipamento",
        "defeitos_reclamados_lista",
        "defeitos_encontrados_lista",
        "defeitos_reclamados_agrupados",
        "defeitos_encontrados_agrupados",
        "qtd_reclamados",
        "qtd_encontrados",
        "status_comparacao",
        "data",
        "coordenacao",
        "contrato",
        "operadora",
        "contrato_operadora",
    ]
    df = _normalizar_colunas(df_oracle)

    if df.empty:
        return pd.DataFrame(columns=colunas_resultado)

    _validar_colunas_oracle(df)

    os_chaves = _serie_texto(df, "OS").map(_normalizar_os)
    datas_os = _converter_datas_destboad(df)
    contratos = _primeira_coluna_preenchida(df, ["NOME", "CONTRATO"])
    operadoras = _primeira_coluna_preenchida(df, ["OPERADORA", "NOME"])
    pracas = _primeira_coluna_preenchida(df, ["A1_PRACA", "PRACA"])
    coordenacoes = _primeira_coluna_preenchida(df, ["COORDENACAO", "COORDENAÇÃO"])

    contexto_pracas = pd.DataFrame(
        {
            "praca": pracas,
            "nome_praca": "",
            "coordenacao": coordenacoes,
        },
        index=df.index,
    )
    contexto_pracas = enriquecer_dataframe_pracas(
        contexto_pracas,
        coluna_praca="praca",
        coluna_nome_praca="nome_praca",
        coluna_coordenacao="coordenacao",
    )
    contexto_contratos = enriquecer_dataframe_contratos(
        pd.DataFrame({"contrato": contratos}, index=df.index),
        coluna_contrato="contrato",
        coluna_praca="praca",
        coluna_nome_praca="nome_praca",
        coluna_coordenacao="coordenacao",
    )
    coordenacoes = _serie_texto(contexto_pracas, "coordenacao").where(
        _serie_texto(contexto_pracas, "coordenacao").ne(""),
        _serie_texto(contexto_contratos, "coordenacao"),
    )

    equipamentos = _primeira_coluna_preenchida(
        df,
        ["DESCRICAO", "SERIE_PRODUTO", "EQUIPAMENTO", "PRODUTO"],
    )
    codigos_reclamados = _serie_texto(df, "DEF_RECLAMADO")
    motivos = _serie_texto(df, "MOTIVO")
    codigos_encontrados = _serie_texto(df, "DEF_ENCONTRADO")
    descricoes_encontradas = _serie_texto(df, "AAG_DESCRI")

    agrupados: dict[str, dict[str, object]] = {}
    for (
        os_chave,
        data_os,
        contrato,
        operadora,
        coordenacao,
        equipamento,
        codigo_reclamado,
        motivo,
        codigo_encontrado,
        descricao_encontrada,
    ) in zip(
        os_chaves,
        datas_os,
        contratos,
        operadoras,
        coordenacoes,
        equipamentos,
        codigos_reclamados,
        motivos,
        codigos_encontrados,
        descricoes_encontradas,
    ):
        if not os_chave:
            continue

        grupo = agrupados.setdefault(
            os_chave,
            {
                "contrato": "",
                "operadora": "",
                "coordenacao": "",
                "equipamento": "",
                "data": pd.NaT,
                "reclamados": [],
                "encontrados": [],
            },
        )

        if not grupo["contrato"] and contrato:
            grupo["contrato"] = contrato
        if not grupo["operadora"] and operadora:
            grupo["operadora"] = operadora
        if not grupo["coordenacao"] and coordenacao:
            grupo["coordenacao"] = coordenacao
        if not grupo["equipamento"] and equipamento:
            grupo["equipamento"] = equipamento

        data_atual = grupo["data"]
        if pd.notna(data_os) and (pd.isna(data_atual) or data_os > data_atual):
            grupo["data"] = data_os

        grupo["reclamados"].append(
            _defeito_reclamado(codigo_reclamado, motivo, descricoes_drs)
        )
        grupo["encontrados"].append(
            _defeito_encontrado(codigo_encontrado, descricao_encontrada)
        )

    if not agrupados:
        return pd.DataFrame(columns=colunas_resultado)

    linhas: list[dict[str, object]] = []
    for os_chave, grupo in agrupados.items():
        reclamados = _deduplicar_defeitos(grupo["reclamados"])
        encontrados = _deduplicar_defeitos(grupo["encontrados"])
        contrato = _texto(grupo["contrato"])
        operadora = _texto(grupo["operadora"])
        coordenacao = _texto(grupo["coordenacao"])
        linhas.append(
            {
                "os": os_chave,
                "equipamento": _texto(grupo["equipamento"]),
                "defeitos_reclamados_lista": [
                    defeito.label for defeito in reclamados
                ],
                "defeitos_encontrados_lista": [
                    defeito.label for defeito in encontrados
                ],
                "defeitos_reclamados_agrupados": _juntar_labels(reclamados),
                "defeitos_encontrados_agrupados": _juntar_labels(encontrados),
                "qtd_reclamados": len(reclamados),
                "qtd_encontrados": len(encontrados),
                "status_comparacao": _classificar_comparacao(
                    reclamados,
                    encontrados,
                ),
                "data": grupo["data"],
                "coordenacao": coordenacao,
                "contrato": contrato,
                "operadora": operadora,
                "contrato_operadora": (
                    contrato
                    if contrato == operadora or not operadora
                    else f"{contrato} / {operadora}"
                ),
            }
        )

    resultado = pd.DataFrame(linhas)
    resultado["data"] = pd.to_datetime(resultado["data"], errors="coerce")
    return resultado.sort_values("data", ascending=False, na_position="last")


def _obter_mtime_csv(caminho_csv: Path) -> float:
    return caminho_csv.stat().st_mtime if caminho_csv.exists() else 0.0


def _formatar_mes(data_mes: pd.Timestamp) -> str:
    meses_pt = {
        1: "JANEIRO",
        2: "FEVEREIRO",
        3: "MARCO",
        4: "ABRIL",
        5: "MAIO",
        6: "JUNHO",
        7: "JULHO",
        8: "AGOSTO",
        9: "SETEMBRO",
        10: "OUTUBRO",
        11: "NOVEMBRO",
        12: "DEZEMBRO",
    }
    return f"{meses_pt[data_mes.month]}/{data_mes:%y}"


def _criar_opcoes_mensais_com_dados(datas: pd.Series) -> list[pd.Timestamp]:
    meses = (
        pd.to_datetime(datas, errors="coerce")
        .dropna()
        .dt.to_period("M")
        .dt.to_timestamp()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    if meses:
        return meses

    return [pd.Timestamp(date.today()).to_period("M").to_timestamp()]


def _obter_periodo_padrao(meses: list[pd.Timestamp]) -> tuple[pd.Timestamp, pd.Timestamp]:
    mes_anterior = (
        pd.Timestamp(date.today()).to_period("M").to_timestamp()
        - pd.DateOffset(months=1)
    )
    mes_padrao = next((mes for mes in reversed(meses) if mes <= mes_anterior), None)
    if mes_padrao is None:
        mes_padrao = meses[-1]

    return mes_padrao, mes_padrao


def _indice_mes(meses: list[pd.Timestamp], mes_procurado: pd.Timestamp) -> int:
    for indice, mes in enumerate(meses):
        if mes == mes_procurado:
            return indice
    return 0


def _normalizar_mes_sessao(
    chave: str,
    meses: list[pd.Timestamp],
    mes_padrao: pd.Timestamp,
) -> pd.Timestamp:
    if chave not in st.session_state:
        return mes_padrao

    valor = st.session_state.get(chave, mes_padrao)
    try:
        mes = pd.Timestamp(valor).to_period("M").to_timestamp()
    except (TypeError, ValueError):
        mes = mes_padrao

    if mes not in meses:
        mes = mes_padrao
        st.session_state[chave] = mes

    return mes


def _normalizar_multiselect_sessao(chave: str, opcoes: list[object]) -> None:
    if chave not in st.session_state:
        return

    valores = st.session_state.get(chave, [])
    if not isinstance(valores, list):
        valores = []

    opcoes_set = set(opcoes)
    valores_validos = [valor for valor in valores if valor in opcoes_set]
    if valores_validos != valores:
        st.session_state[chave] = valores_validos


def _status_slug(status: object) -> str:
    texto = normalizar_texto_defeito(status).lower().replace(" ", "-")
    return texto or "indefinido"


def _status_classe(status: object) -> str:
    slug = _status_slug(status)
    if slug == "compativel":
        return "status-compativel"
    if slug == "parcial":
        return "status-parcial"
    if slug == "divergente":
        return "status-divergente"
    if slug == "sem-encontrado":
        return "status-sem-encontrado"
    if slug == "sem-reclamado":
        return "status-sem-reclamado"
    return "status-indefinido"


def _aplicar_estilos_analise_falhas() -> None:
    st.markdown(
        """
        <style>
            .falhas-page-header {
                margin: 0.15rem 0 0.95rem 0;
            }

            .falhas-page-title {
                color: var(--tacom-text);
                font-size: clamp(1.45rem, 1.8vw, 2rem);
                font-weight: 780;
                line-height: 1.2;
            }

            .falhas-page-subtitle {
                margin-top: 0.3rem;
                color: var(--tacom-muted);
                font-size: 0.92rem;
                font-weight: 520;
            }

            .falhas-source-note {
                margin: -0.25rem 0 0.85rem 0;
                color: var(--tacom-muted);
                font-size: 0.74rem;
            }

            .falhas-section-title {
                margin: 0 0 0.85rem 0;
                color: var(--tacom-text);
                font-size: 1rem;
                font-weight: 780;
                line-height: 1.25;
            }

            .falhas-pagination-label {
                display: flex;
                min-height: 2.4rem;
                align-items: center;
                justify-content: center;
                color: var(--tacom-text);
                font-size: 0.82rem;
                font-weight: 800;
                line-height: 1;
                white-space: nowrap;
            }

            .falhas-kpi-card {
                position: relative;
                min-height: 98px;
                padding: 0.95rem 0.95rem 0.85rem 0.95rem;
                border: 1px solid var(--tacom-border);
                border-left: 4px solid var(--status-color);
                border-radius: 8px;
                background: var(--tacom-panel);
                box-shadow: 0 10px 28px rgba(17, 24, 39, 0.06);
            }

            .falhas-kpi-top {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.6rem;
                margin-bottom: 0.55rem;
            }

            .falhas-kpi-title {
                color: var(--tacom-muted);
                font-size: 0.74rem;
                font-weight: 700;
                line-height: 1.2;
            }

            .falhas-kpi-icon {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 1.9rem;
                height: 1.9rem;
                border-radius: 8px;
                background: color-mix(in srgb, var(--status-color) 14%, transparent);
                color: var(--status-color);
                font-size: 0.72rem;
                font-weight: 800;
            }

            .falhas-kpi-value {
                color: var(--tacom-text);
                font-size: clamp(1.35rem, 1.7vw, 1.85rem);
                font-weight: 800;
                line-height: 1;
            }

            .falhas-os-table {
                width: min(100%, 1340px);
                max-width: 1340px;
                margin: 0 auto;
                overflow-x: auto;
                overflow-y: hidden;
                border: 1px solid var(--tacom-border);
                border-radius: 8px;
                background: var(--tacom-panel);
                box-shadow: 0 12px 32px rgba(17, 24, 39, 0.05);
            }

            .falhas-os-table-header,
            .falhas-os-row {
                display: grid;
                grid-template-columns: 380px 330px 130px 330px 70px;
                column-gap: 16px;
                align-items: center;
                width: 1340px;
                min-width: 1340px;
                max-width: 1340px;
                box-sizing: border-box;
            }

            .falhas-os-table-header {
                min-height: 2.35rem;
                padding: 0 0.85rem;
                border-bottom: 1px solid var(--tacom-border);
                background: color-mix(in srgb, var(--tacom-bg-soft) 74%, var(--tacom-panel));
                color: var(--tacom-muted);
                font-size: 0.68rem;
                font-weight: 800;
                align-items: center;
            }

            .falhas-os-table-header > span {
                display: flex;
                min-width: 0;
                height: 100%;
                align-items: center;
                justify-content: flex-start;
                line-height: 1.1;
                text-align: left;
            }

            .falhas-os-table-header > span:nth-child(1) {
                padding-left: calc(2rem + 0.65rem);
            }

            .falhas-os-table-header > span:nth-child(3),
            .falhas-os-table-header > span:nth-child(5) {
                justify-content: center;
                text-align: center;
            }

            .falhas-os-table-header > .falhas-header-defeitos-encontrados,
            .falhas-cell-title.falhas-title-defeitos-encontrados {
                justify-content: flex-end;
                text-align: right;
            }

            .falhas-os-row-details {
                width: 1340px;
                min-width: 1340px;
                max-width: 1340px;
                margin: 0;
                border-bottom: 1px solid var(--tacom-border);
                box-sizing: border-box;
            }

            .falhas-os-row-details:last-child {
                border-bottom: 0;
            }

            .falhas-os-row-details > summary {
                display: block;
                list-style: none;
                cursor: pointer;
            }

            .falhas-os-row-details > summary::-webkit-details-marker {
                display: none;
            }

            .falhas-os-row {
                min-height: 4.75rem;
                padding: 0.72rem 0.85rem;
                transition: background 0.18s ease;
            }

            .falhas-os-row:hover {
                background: color-mix(in srgb, var(--tacom-bg-soft) 58%, transparent);
            }

            .falhas-os-identity {
                display: flex;
                min-width: 0;
                align-items: center;
                gap: 0.65rem;
                overflow-wrap: anywhere;
            }

            .falhas-os-icon {
                display: inline-flex;
                flex: 0 0 auto;
                align-items: center;
                justify-content: center;
                width: 2rem;
                height: 2rem;
                border: 1px solid color-mix(in srgb, var(--tacom-muted) 28%, var(--tacom-border));
                border-radius: 8px;
                color: var(--tacom-muted);
                font-size: 0.58rem;
                font-weight: 900;
                letter-spacing: 0;
            }

            .falhas-os-text {
                display: inline-flex;
                min-width: 0;
                flex-direction: column;
                gap: 0.22rem;
                overflow-wrap: anywhere;
            }

            .falhas-os-link {
                color: var(--tacom-primary);
                font-size: 0.84rem;
                font-weight: 850;
                line-height: 1.15;
                overflow-wrap: anywhere;
                white-space: nowrap;
            }

            .falhas-os-subtitle {
                color: var(--tacom-text);
                font-size: 0.72rem;
                font-weight: 520;
                line-height: 1.2;
                overflow-wrap: anywhere;
            }

            .falhas-os-cell {
                display: inline-flex;
                min-width: 0;
                flex-direction: column;
                gap: 0.4rem;
                overflow-wrap: anywhere;
            }

            .falhas-cell-title {
                color: var(--tacom-muted);
                font-size: 0.66rem;
                font-weight: 800;
                line-height: 1;
                 display: flex;
                flex-wrap: wrap;
                gap: 0.38rem;
            }

            .falhas-os-card {
                margin-bottom: 0.75rem;
                padding: 0.95rem;
                border: 1px solid var(--tacom-border);
                border-radius: 8px;
                background: var(--tacom-panel);
                box-shadow: 0 12px 32px rgba(17, 24, 39, 0.06);
            }

            .falhas-os-top {
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 0.8rem;
                margin-bottom: 0.75rem;
                padding-bottom: 0.75rem;
                border-bottom: 1px solid var(--tacom-border);
            }

            .falhas-os-title {
                color: var(--tacom-text);
                font-size: 0.98rem;
                font-weight: 800;
                line-height: 1.2;
            }

            .falhas-os-equipment {
                margin-top: 0.22rem;
                color: var(--tacom-muted);
                font-size: 0.78rem;
                font-weight: 560;
            }

            .falhas-os-grid {
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
                gap: 0.8rem;
                align-items: center;
            }

            .falhas-side-title {
                margin-bottom: 0.45rem;
                color: var(--tacom-muted);
                font-size: 0.72rem;
                font-weight: 800;
                text-transform: uppercase;
            }

            .falhas-chip-row {
                display: flex;
                flex-wrap: wrap;
                gap: 0.38rem;
                
            }

            .falhas-chip {
                display: inline-flex;
                max-width: 100%;
                padding: 0.28rem 0.47rem;
                border: 1px solid var(--chip-border);
                border-radius: 8px;
                background: var(--chip-bg);
                color: var(--chip-color);
                font-size: 0.7rem;
                font-weight: 750;
                line-height: 1.2;
                overflow-wrap: anywhere;
            }

            .falhas-chip-reclamado {
                --chip-bg: color-mix(in srgb, #ff5a5f 14%, transparent);
                --chip-border: color-mix(in srgb, #d92d20 22%, var(--tacom-border));
                --chip-color: #d92d20;
            }

            .falhas-chip-encontrado {
                --chip-bg: color-mix(in srgb, #22c55e 14%, transparent);
                --chip-border: color-mix(in srgb, #17803d 22%, var(--tacom-border));
                --chip-color: #17803d;
                justify-content: flex-end;
                text-align: right;
            }

            .falhas-chip-row:has(.falhas-chip-encontrado) {
                justify-content: flex-end;
                text-align: right;
            }

            .falhas-os-identity,
            .falhas-os-text,
            .falhas-os-cell,
            .falhas-chip-row,
            .falhas-chip {
                min-width: 0;
                box-sizing: border-box;
            }

            .falhas-os-subtitle,
            .falhas-chip {
                white-space: normal;
                overflow-wrap: anywhere;
                word-break: normal;
            }

            .falhas-os-link {
                white-space: nowrap;
            }

            .falhas-status-cell {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                width: 130px;
                min-width: 130px;
                max-width: 130px;
                justify-self: center;
                position: relative;
                box-sizing: border-box;
            }

            .falhas-status-rail {
                position: absolute;
                top: 50%;
                width: 24px;
                max-width: 24px;
                flex: 0 0 24px;
                border-top: 1px dashed color-mix(in srgb, var(--tacom-muted) 55%, transparent);
                transform: translateY(-50%);
                pointer-events: none;
            }

            .falhas-status-rail:first-child {
                right: calc(50% + 39px);
            }

            .falhas-status-rail:last-child {
                left: calc(50% + 39px);
            }

            .falhas-status-rail::after {
                content: "";
                position: absolute;
                top: -0.23rem;
                width: 0.42rem;
                height: 0.42rem;
                border-radius: 50%;
                background: color-mix(in srgb, var(--tacom-muted) 70%, var(--tacom-panel));
            }

            .falhas-status-rail:first-child::after {
                right: -0.12rem;
            }

            .falhas-status-rail:last-child::after {
                left: -0.12rem;
            }

            .falhas-status-flow {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-width: 142px;
                gap: 0.35rem;
            }

            .falhas-flow-line {
                width: 100%;
                height: 1px;
                background: linear-gradient(90deg, transparent, var(--status-color), transparent);
            }

            .falhas-status-badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-height: 1.62rem;
                min-width: 4.6rem;
                padding: 0.28rem 0.65rem;
                border: 1px solid color-mix(in srgb, var(--status-color) 38%, var(--tacom-border));
                border-radius: 8px;
                background: color-mix(in srgb, var(--status-color) 14%, var(--tacom-panel));
                color: var(--status-color);
                font-size: 0.7rem;
                font-weight: 800;
                text-align: center;
                white-space: nowrap;
            }

            .status-compativel {
                --status-color: #17803d;
            }

            .status-parcial {
                --status-color: #a16207;
            }

            .status-divergente {
                --status-color: #d92d20;
            }

            .status-sem-encontrado {
                --status-color: #6d28d9;
            }

            .status-sem-reclamado {
                --status-color: #0b5ed7;
            }

            .status-indefinido {
                --status-color: #526071;
            }

            .falhas-details {
                margin-top: 0.75rem;
                padding-top: 0.75rem;
                border-top: 1px solid var(--tacom-border);
                color: var(--tacom-muted);
                font-size: 0.76rem;
                line-height: 1.5;
            }

            .falhas-details summary {
                cursor: pointer;
                color: var(--tacom-primary);
                font-weight: 800;
            }

            .falhas-flow-arrow {
                color: #000000;
                font-size: 1rem;
                font-weight: 800;
                line-height: 1;
            }

            .falhas-action-cell {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 0.28rem;
                width: 70px;
                min-width: 70px;
                max-width: 70px;
                justify-self: center;
                box-sizing: border-box;
            }

            .falhas-action-button {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 2rem;
                height: 1.8rem;
                border: 1px solid var(--tacom-border);
                border-radius: 8px;
                background: var(--tacom-panel);
                color: var(--tacom-text);
                box-shadow: 0 8px 18px rgba(17, 24, 39, 0.04);
            }

            .falhas-eye-icon {
                position: relative;
                display: inline-flex;
                width: 0.95rem;
                height: 0.58rem;
                border: 1.5px solid currentColor;
                border-radius: 999px / 70%;
            }

            .falhas-eye-icon::after {
                content: "";
                position: absolute;
                left: 50%;
                top: 50%;
                width: 0.24rem;
                height: 0.24rem;
                border-radius: 50%;
                background: currentColor;
                transform: translate(-50%, -50%);
            }

            .falhas-action-chevron {
                color: var(--tacom-muted);
                font-size: 0.88rem;
                font-weight: 900;
                transition: transform 0.18s ease;
            }

            .falhas-os-row-details[open] .falhas-action-chevron {
                transform: rotate(180deg);
            }

            .falhas-row-detail-panel {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0.65rem;
                width: 1340px;
                min-width: 1340px;
                max-width: 1340px;
                padding: 0.75rem 0.95rem 0.9rem 3.6rem;
                border-top: 1px solid color-mix(in srgb, var(--tacom-border) 70%, transparent);
                background: color-mix(in srgb, var(--tacom-bg-soft) 45%, transparent);
                box-sizing: border-box;
            }

            .falhas-row-detail-item {
                display: flex;
                flex-direction: column;
                gap: 0.18rem;
                min-width: 0;
                color: var(--tacom-text);
                font-size: 0.76rem;
                font-weight: 700;
                overflow-wrap: anywhere;
            }

            .falhas-row-detail-label {
                color: var(--tacom-muted);
                font-size: 0.64rem;
                font-weight: 800;
            }

            .falhas-top-subtitle {
                margin: 0 0 0.65rem 0;
                color: var(--tacom-primary);
                font-size: 0.76rem;
                font-weight: 850;
            }

            .falhas-top-list {
                display: flex;
                flex-direction: column;
                gap: 0.56rem;
                padding: 0.05rem 0 0.25rem 0;
            }

            .falhas-top-item {
                display: grid;
                grid-template-columns: minmax(8rem, 1fr) minmax(5.5rem, 1.25fr) 2.35rem;
                gap: 0.58rem;
                align-items: center;
            }

            .falhas-top-label {
                min-width: 0;
                color: var(--tacom-text);
                font-size: 0.74rem;
                font-weight: 700;
                line-height: 1.2;
                overflow-wrap: anywhere;
            }

            .falhas-top-bar-track {
                width: 100%;
                height: 0.26rem;
                overflow: hidden;
                border-radius: 999px;
                background: color-mix(in srgb, var(--tacom-primary) 10%, var(--tacom-border));
            }

            .falhas-top-bar-fill {
                height: 100%;
                border-radius: inherit;
                background: #5ca9f8;
            }

            .falhas-top-count {
                color: var(--tacom-text);
                font-size: 0.72rem;
                font-weight: 800;
                text-align: right;
            }

            @media (max-width: 900px) {
                .falhas-os-table {
                    width: 100%;
                    max-width: 100%;
                }

                .falhas-os-table-header,
                .falhas-os-row {
                    grid-template-columns: 330px 290px 130px 290px 60px;
                    column-gap: 14px;
                    width: 1200px;
                    min-width: 1200px;
                    max-width: 1200px;
                }

                .falhas-os-row-details,
                .falhas-row-detail-panel {
                    width: 1200px;
                    min-width: 1200px;
                    max-width: 1200px;
                }

                .falhas-action-cell {
                    width: 60px;
                    min-width: 60px;
                    max-width: 60px;
                }

                .falhas-row-detail-panel {
                    grid-template-columns: 1fr;
                    padding-left: 0.95rem;
                }

                .falhas-top-item {
                    grid-template-columns: minmax(0, 1fr) minmax(5rem, 1fr) 2.2rem;
                }

                .falhas-flow-line {
                    display: none;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _html_escape(valor: object) -> str:
    return html.escape(_texto(valor))


def _obter_lista_defeitos(row: pd.Series, coluna_lista: str, coluna_texto: str) -> list[str]:
    valores = row.get(coluna_lista, [])
    if isinstance(valores, list):
        return [_texto(valor) for valor in valores if _texto(valor)]

    texto = _texto(row.get(coluna_texto, ""))
    if not texto:
        return []

    return [parte.strip() for parte in texto.split(" | ") if parte.strip()]


def _render_chips(defeitos: list[str], classe: str) -> str:
    if not defeitos:
        return f'<span class="falhas-chip {classe}">Sem registro</span>'

    return "".join(
        f'<span class="falhas-chip {classe}">{_html_escape(defeito)}</span>'
        for defeito in defeitos
    )


def _preparar_download_detalhamento_os(df_os: pd.DataFrame) -> pd.DataFrame:
    colunas = [
        "OS",
        "Equipamento",
        "Defeitos reclamados",
        "Status",
        "Defeitos encontrados",
        "Data",
        "Contrato/operadora",
        "Qtd. reclamados",
        "Qtd. encontrados",
    ]
    linhas: list[dict[str, object]] = []

    for _, row in df_os.iterrows():
        reclamados = _obter_lista_defeitos(
            row,
            "defeitos_reclamados_lista",
            "defeitos_reclamados_agrupados",
        )
        encontrados = _obter_lista_defeitos(
            row,
            "defeitos_encontrados_lista",
            "defeitos_encontrados_agrupados",
        )
        data = pd.to_datetime(row.get("data"), errors="coerce")
        qtd_reclamados = row.get("qtd_reclamados", 0)
        qtd_encontrados = row.get("qtd_encontrados", 0)

        linhas.append(
            {
                "OS": _texto(row.get("os")),
                "Equipamento": _texto(row.get("equipamento")),
                "Defeitos reclamados": " | ".join(reclamados) or "Sem registro",
                "Status": _texto(row.get("status_comparacao")),
                "Defeitos encontrados": " | ".join(encontrados) or "Sem registro",
                "Data": data.strftime("%Y-%m-%d") if pd.notna(data) else "",
                "Contrato/operadora": _texto(row.get("contrato_operadora")),
                "Qtd. reclamados": (
                    int(qtd_reclamados) if pd.notna(qtd_reclamados) else 0
                ),
                "Qtd. encontrados": (
                    int(qtd_encontrados) if pd.notna(qtd_encontrados) else 0
                ),
            }
        )

    return pd.DataFrame(linhas, columns=colunas)


def _limpar_filtros_analise_falhas() -> None:
    for chave in [
        FALHAS_MES_INICIO_KEY,
        FALHAS_MES_FIM_KEY,
        FALHAS_COORDENACAO_KEY,
        FALHAS_CONTRATO_KEY,
        FALHAS_OPERADORA_KEY,
        FALHAS_EQUIPAMENTO_KEY,
        FALHAS_STATUS_KEY,
        FALHAS_OS_KEY,
        FALHAS_BUSCA_GERAL_KEY,
        FALHAS_DETALHE_PAGINA_KEY,
    ]:
        st.session_state.pop(chave, None)


def render_filtros_analise_falhas(df_os: pd.DataFrame) -> dict[str, object]:
    datas_validas = pd.to_datetime(df_os["data"], errors="coerce").dropna()
    meses_disponiveis = _criar_opcoes_mensais_com_dados(datas_validas)
    periodo_padrao = _obter_periodo_padrao(meses_disponiveis)

    with st.container(border=True):
        col_titulo, col_limpar = st.columns([3, 0.8])
        with col_titulo:
            st.markdown(
                '<div class="filters-title">Filtros aplicados</div>',
                unsafe_allow_html=True,
            )
        with col_limpar:
            if st.button(
                "Limpar filtros",
                icon=":material/filter_alt_off:",
                width="stretch",
                key="falhas_limpar_filtros",
            ):
                _limpar_filtros_analise_falhas()
                st.rerun()

        col_inicio, col_fim, col_os, col_equipamento = st.columns(
            [0.85, 0.85, 0.75, 1.4],
        )
        col_coordenacao, col_contrato, col_status, col_busca = st.columns(
            [1.15, 1.25, 1.05, 1.45]
        )

        with col_inicio:
            inicio_sessao = _normalizar_mes_sessao(
                FALHAS_MES_INICIO_KEY,
                meses_disponiveis,
                periodo_padrao[0],
            )
            mes_inicio = st.selectbox(
                "Mes inicial",
                options=meses_disponiveis,
                index=_indice_mes(meses_disponiveis, inicio_sessao),
                format_func=_formatar_mes,
                key=FALHAS_MES_INICIO_KEY,
            )
        with col_fim:
            meses_finais = [mes for mes in meses_disponiveis if mes >= mes_inicio]
            fim_padrao = (
                periodo_padrao[1]
                if periodo_padrao[1] >= mes_inicio
                else mes_inicio
            )
            fim_sessao = _normalizar_mes_sessao(
                FALHAS_MES_FIM_KEY,
                meses_finais,
                fim_padrao,
            )
            mes_fim = st.selectbox(
                "Mes final",
                options=meses_finais,
                index=_indice_mes(meses_finais, fim_sessao),
                format_func=_formatar_mes,
                key=FALHAS_MES_FIM_KEY,
            )

        contratos = sorted(
            [x for x in df_os["contrato"].dropna().unique().tolist() if x]
        )
        coordenacoes = sorted(
            [x for x in df_os["coordenacao"].dropna().unique().tolist() if x]
        )
        equipamentos = sorted(
            [x for x in df_os["equipamento"].dropna().unique().tolist() if x]
        )

        _normalizar_multiselect_sessao(FALHAS_COORDENACAO_KEY, coordenacoes)
        _normalizar_multiselect_sessao(FALHAS_CONTRATO_KEY, contratos)
        _normalizar_multiselect_sessao(FALHAS_EQUIPAMENTO_KEY, equipamentos)
        _normalizar_multiselect_sessao(FALHAS_STATUS_KEY, STATUS_ORDEM)

        with col_os:
            filtro_os = st.text_input(
                "OS",
                placeholder="Nº da OS",
                key=FALHAS_OS_KEY,
            )
        with col_equipamento:
            filtro_equipamento = st.multiselect(
                "Equipamento",
                equipamentos,
                placeholder="Selecione os equipamentos",
                key=FALHAS_EQUIPAMENTO_KEY,
            )
        with col_coordenacao:
            filtro_coordenacao = st.multiselect(
                "Coordenação",
                coordenacoes,
                placeholder="Selecione as coordenações",
                key=FALHAS_COORDENACAO_KEY,
            )
        with col_contrato:
            filtro_contrato = st.multiselect(
                "Contrato",
                contratos,
                placeholder="Selecione os contratos",
                key=FALHAS_CONTRATO_KEY,
            )
        with col_status:
            filtro_status = st.multiselect(
                "Status",
                STATUS_ORDEM,
                placeholder="Selecione os status",
                key=FALHAS_STATUS_KEY,
            )
        with col_busca:
            filtro_busca_geral = st.text_input(
                "Busca geral",
                placeholder="OS ou defeito",
                key=FALHAS_BUSCA_GERAL_KEY,
            )

    inicio_mes = pd.Timestamp(mes_inicio)
    fim_mes = pd.Timestamp(mes_fim) + pd.offsets.MonthEnd(0)

    return {
        "periodo": (inicio_mes, fim_mes),
        "filtro_coordenacao": filtro_coordenacao,
        "filtro_contrato": filtro_contrato,
        "filtro_equipamento": filtro_equipamento,
        "filtro_status": filtro_status,
        "filtro_os": filtro_os,
        "filtro_busca_geral": filtro_busca_geral,
    }


def aplicar_filtros_analise_falhas(
    df_os: pd.DataFrame,
    filtros: dict[str, object],
) -> pd.DataFrame:
    filtrado = df_os.copy()

    periodo = filtros.get("periodo")
    if isinstance(periodo, tuple) and len(periodo) == 2:
        inicio = pd.to_datetime(periodo[0])
        fim = pd.to_datetime(periodo[1])
        datas = pd.to_datetime(filtrado["data"], errors="coerce")
        filtrado = filtrado[datas.between(inicio, fim, inclusive="both")]

    filtro_coordenacao = filtros.get("filtro_coordenacao", [])
    if filtro_coordenacao:
        filtrado = filtrado[filtrado["coordenacao"].isin(filtro_coordenacao)]

    filtro_contrato = filtros.get("filtro_contrato", [])
    if filtro_contrato:
        filtrado = filtrado[filtrado["contrato"].isin(filtro_contrato)]

    filtro_equipamento = filtros.get("filtro_equipamento", [])
    if filtro_equipamento:
        filtrado = filtrado[filtrado["equipamento"].isin(filtro_equipamento)]

    filtro_status = filtros.get("filtro_status", [])
    if filtro_status:
        filtrado = filtrado[filtrado["status_comparacao"].isin(filtro_status)]

    filtro_os = _normalizar_os(filtros.get("filtro_os", ""))
    if filtro_os:
        filtrado = filtrado[
            filtrado["os"].fillna("").astype(str).str.contains(
                re.escape(filtro_os),
                case=False,
                na=False,
            )
        ]

    filtro_busca_geral = normalizar_texto_defeito(filtros.get("filtro_busca_geral", ""))
    if filtro_busca_geral:
        texto_busca = (
            filtrado["os"].fillna("").astype(str)
            + " "
            + filtrado["defeitos_reclamados_agrupados"].fillna("").astype(str)
            + " "
            + filtrado["defeitos_encontrados_agrupados"].fillna("").astype(str)
            + " "
            + filtrado["equipamento"].fillna("").astype(str)
        ).map(normalizar_texto_defeito)
        filtrado = filtrado[texto_busca.str.contains(re.escape(filtro_busca_geral), na=False)]

    return filtrado


def calcular_kpis_analise_falhas(
    df_os: pd.DataFrame,
) -> dict[str, int | float]:
    total_os = len(df_os)
    contagem_status = df_os["status_comparacao"].value_counts()
    divergentes = int(contagem_status.get(STATUS_DIVERGENTE, 0))
    percentual_divergencia = (divergentes / total_os * 100) if total_os else 0.0

    return {
        "total_os": total_os,
        "compativeis": int(contagem_status.get(STATUS_COMPATIVEL, 0)),
        "divergentes": divergentes,
        "parciais": int(contagem_status.get(STATUS_PARCIAL, 0)),
        "sem_encontrado": int(contagem_status.get(STATUS_SEM_ENCONTRADO, 0)),
        "percentual_divergencia": percentual_divergencia,
    }


def _render_card(
    titulo: str,
    valor: str,
    icone: str,
    status_classe: str = "status-indefinido",
) -> None:
    st.markdown(
        f"""
        <div class="falhas-kpi-card {status_classe}">
            <div class="falhas-kpi-top">
                <div class="falhas-kpi-title">{_html_escape(titulo)}</div>
                <div class="falhas-kpi-icon">{_html_escape(icone)}</div>
            </div>
            <div class="falhas-kpi-value">{_html_escape(valor)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis_analise_falhas(kpis: dict[str, int | float]) -> None:
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        _render_card(
            "OS analisadas",
            _format_int(int(kpis["total_os"])),
            "OS",
            "status-indefinido",
        )
    with c2:
        _render_card(
            "Compatíveis",
            _format_int(int(kpis["compativeis"])),
            "OK",
            "status-compativel",
        )
    with c3:
        _render_card(
            "Parciais",
            _format_int(int(kpis["parciais"])),
            "PR",
            "status-parcial",
        )
    with c4:
        _render_card(
            "Divergentes",
            _format_int(int(kpis["divergentes"])),
            "DG",
            "status-divergente",
        )
    with c5:
        _render_card(
            "Sem encontrado",
            _format_int(int(kpis["sem_encontrado"])),
            "SE",
            "status-sem-encontrado",
        )
    with c6:
        _render_card(
            "% divergência",
            _format_percent(float(kpis["percentual_divergencia"])),
            "%",
            "status-divergente",
        )


def _cor_texto_tema() -> str:
    return "#1f2937" if tema_claro_ativo() else "#E0E0E0"


def _cor_grade_tema() -> str:
    return "rgba(31,41,55,0.16)" if tema_claro_ativo() else "rgba(224,224,224,0.18)"


def _estilizar_figura(fig):
    text_color = _cor_texto_tema()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": text_color},
        title={"font": {"color": text_color}},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        legend={
            "font": {"color": text_color},
            "orientation": "h",
            "yanchor": "top",
            "y": -0.18,
            "xanchor": "center",
            "x": 0.5,
        },
    )
    axis_font = {"color": text_color}
    fig.update_xaxes(
        showgrid=False,
        tickfont=axis_font,
        title_font=axis_font,
    )
    fig.update_yaxes(
        gridcolor=_cor_grade_tema(),
        tickfont=axis_font,
        title_font=axis_font,
    )
    return fig


def _mostrar_rotulos_barras(fig, template: str = "%{text}") -> None:
    fig.update_traces(
        texttemplate=template,
        textposition="inside",
        insidetextanchor="middle",
        constraintext="none",
        cliponaxis=False,
        textfont={"color": _cor_texto_tema(), "size": 12},
        insidetextfont={"color": _cor_texto_tema(), "size": 12},
        selector={"type": "bar"},
    )
    fig.update_layout(uniformtext={"minsize": 10, "mode": "show"})


def _formatar_mes_curto(data_mes: pd.Timestamp) -> str:
    meses_pt = {
        1: "Jan",
        2: "Fev",
        3: "Mar",
        4: "Abr",
        5: "Mai",
        6: "Jun",
        7: "Jul",
        8: "Ago",
        9: "Set",
        10: "Out",
        11: "Nov",
        12: "Dez",
    }
    data_mes = pd.Timestamp(data_mes)
    return f"{meses_pt[data_mes.month]}/{data_mes:%y}"


def _contar_defeitos(df_os: pd.DataFrame, coluna_lista: str) -> pd.DataFrame:
    contagem: dict[str, int] = {}
    for _, row in df_os.iterrows():
        defeitos = _obter_lista_defeitos(
            row,
            coluna_lista,
            (
                "defeitos_reclamados_agrupados"
                if "reclamados" in coluna_lista
                else "defeitos_encontrados_agrupados"
            ),
        )
        for defeito in defeitos:
            contagem[defeito] = contagem.get(defeito, 0) + 1

    if not contagem:
        return pd.DataFrame(columns=["defeito", "quantidade"])

    return (
        pd.DataFrame(
            [{"defeito": defeito, "quantidade": quantidade} for defeito, quantidade in contagem.items()]
        )
        .sort_values("quantidade", ascending=False)
        .head(8)
    )


def _render_lista_top_defeitos(df_defeitos: pd.DataFrame) -> None:
    if df_defeitos.empty:
        st.info("Sem defeitos para os filtros selecionados.")
        return

    maior_quantidade = int(df_defeitos["quantidade"].max()) or 1
    itens_lista: list[str] = []
    for _, row in df_defeitos.iterrows():
        quantidade = int(row["quantidade"])
        largura_barra = max(5.0, quantidade / maior_quantidade * 100)
        itens_lista.append(
            '<div class="falhas-top-item">'
            f'<div class="falhas-top-label">{_html_escape(row["defeito"])}</div>'
            '<div class="falhas-top-bar-track">'
            f'<div class="falhas-top-bar-fill" style="width: {largura_barra:.1f}%;"></div>'
            "</div>"
            f'<div class="falhas-top-count">{_format_int(quantidade)}</div>'
            "</div>"
        )

    itens = "".join(itens_lista)
    st.markdown(f'<div class="falhas-top-list">{itens}</div>', unsafe_allow_html=True)


def render_graficos_analise_falhas(df_os: pd.DataFrame) -> None:
    if df_os.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    col_status, col_top = st.columns([1, 1.45])

    with col_status:
        with st.container(border=True):
            st.markdown(
                '<div class="falhas-section-title">Status da Comparação</div>',
                unsafe_allow_html=True,
            )
            status_df = (
                df_os["status_comparacao"]
                .value_counts()
                .reindex(STATUS_ORDEM, fill_value=0)
                .rename_axis("status_comparacao")
                .reset_index(name="quantidade_os")
            )
            status_df = status_df[status_df["quantidade_os"].gt(0)]
            fig_status = px.pie(
                status_df,
                title = " ",
                names="status_comparacao",
                values="quantidade_os",
                hole=0.58,
                color_discrete_map=STATUS_CORES,
                color="status_comparacao",
                labels={
                    "status_comparacao": "Status",
                    "quantidade_os": "Quantidade de OS",
                },
            )
            fig_status.update_traces(
                textinfo="percent+label",
                hovertemplate="%{label}<br>OS=%{value}<extra></extra>",
            )
            fig_status.update_layout(
                showlegend=False,
                margin={"l": 8, "r": 8, "t": 8, "b": 8},
            )
            st.plotly_chart(_estilizar_figura(fig_status), use_container_width=True)

    with col_top:
        with st.container(border=True):
            st.markdown(
                '<div class="falhas-section-title">Top Defeitos</div>',
                unsafe_allow_html=True,
            )
            col_rec, col_enc = st.columns(2)
            with col_rec:
                st.markdown(
                    '<div class="falhas-top-subtitle">Mais frequentes reclamados</div>',
                    unsafe_allow_html=True,
                )
                _render_lista_top_defeitos(
                    _contar_defeitos(df_os, "defeitos_reclamados_lista")
                )
            with col_enc:
                st.markdown(
                    '<div class="falhas-top-subtitle">Mais frequentes encontrados</div>',
                    unsafe_allow_html=True,
                )
                _render_lista_top_defeitos(
                    _contar_defeitos(df_os, "defeitos_encontrados_lista")
                )


def render_tabela_analise_falhas(df_os: pd.DataFrame) -> None:
    with st.container(border=True):
        st.markdown(
            '<div class="falhas-section-title">Detalhamento por OS</div>',
            unsafe_allow_html=True,
        )

        if df_os.empty:
            st.info("Sem OS para os filtros selecionados.")
            return

        df_ordenado = df_os.sort_values("data", ascending=False, na_position="last")
        total_os = len(df_ordenado)
        total_paginas = max(1, (total_os + FALHAS_OS_POR_PAGINA - 1) // FALHAS_OS_POR_PAGINA)
        pagina_atual = int(st.session_state.get(FALHAS_DETALHE_PAGINA_KEY, 1))
        pagina_atual = min(max(1, pagina_atual), total_paginas)
        st.session_state[FALHAS_DETALHE_PAGINA_KEY] = pagina_atual
        df_download = _preparar_download_detalhamento_os(df_ordenado)
        csv_download = df_download.to_csv(sep=";", index=False).encode("utf-8-sig")

        col_info, col_download, col_pagina = st.columns([2.1, 0.9, 0.95])
        with col_download:
            st.download_button(
                "Baixar CSV",
                data=csv_download,
                file_name="analise_falhas_detalhamento_os.csv",
                mime="text/csv",
                key="falhas_download_detalhamento_os_csv",
            )
        with col_pagina:
            col_anterior, col_rotulo, col_proxima = st.columns([0.28, 0.44, 0.28])
            with col_anterior:
                voltar = st.button(
                    "‹",
                    help="Página anterior",
                    disabled=pagina_atual <= 1,
                    key="falhas_pagina_anterior",
                    width="stretch",
                )
            with col_proxima:
                avancar = st.button(
                    "›",
                    help="Próxima página",
                    disabled=pagina_atual >= total_paginas,
                    key="falhas_pagina_proxima",
                    width="stretch",
                )

            if voltar:
                pagina_atual = max(1, pagina_atual - 1)
            elif avancar:
                pagina_atual = min(total_paginas, pagina_atual + 1)

            st.session_state[FALHAS_DETALHE_PAGINA_KEY] = pagina_atual
            with col_rotulo:
                st.markdown(
                    f'<div class="falhas-pagination-label">{pagina_atual} de {total_paginas}</div>',
                    unsafe_allow_html=True,
                )
        with col_info:
            inicio_exibicao = (pagina_atual - 1) * FALHAS_OS_POR_PAGINA + 1
            fim_exibicao = min(pagina_atual * FALHAS_OS_POR_PAGINA, total_os)
            st.caption(
                f"Exibindo {inicio_exibicao}-{fim_exibicao} de {total_os} OS filtradas"
            )

        inicio = (int(pagina_atual) - 1) * FALHAS_OS_POR_PAGINA
        fim = inicio + FALHAS_OS_POR_PAGINA
        df_view = df_ordenado.iloc[inicio:fim]

        linhas_html: list[str] = []
        for _, row in df_view.iterrows():
            status = _texto(row.get("status_comparacao", ""))
            status_classe = _status_classe(status)
            reclamados = _obter_lista_defeitos(
                row,
                "defeitos_reclamados_lista",
                "defeitos_reclamados_agrupados",
            )
            encontrados = _obter_lista_defeitos(
                row,
                "defeitos_encontrados_lista",
                "defeitos_encontrados_agrupados",
            )
            data = pd.to_datetime(row.get("data"), errors="coerce")
            data_texto = data.strftime("%Y-%m-%d") if pd.notna(data) else "Sem data"
            qtd_reclamados = row.get("qtd_reclamados", 0)
            qtd_encontrados = row.get("qtd_encontrados", 0)
            qtd_reclamados = int(qtd_reclamados) if pd.notna(qtd_reclamados) else 0
            qtd_encontrados = int(qtd_encontrados) if pd.notna(qtd_encontrados) else 0

            linhas_html.append(
                '<details class="falhas-os-row-details '
                f'{status_classe}"><summary><span class="falhas-os-row">'
                '<span class="falhas-os-identity">'
                '<span class="falhas-os-icon">OS</span>'
                '<span class="falhas-os-text">'
                f'<span class="falhas-os-link">OS {_html_escape(row.get("os"))}</span>'
                f'<span class="falhas-os-subtitle">Equipamento: {_html_escape(row.get("equipamento"))}</span>'
                "</span></span>"
                '<span class="falhas-os-cell">'
                '<span class="falhas-cell-title">Defeitos reclamados</span>'
                f'<span class="falhas-chip-row">{_render_chips(reclamados, "falhas-chip-reclamado")}</span>'
                "</span>"
                '<span class="falhas-status-cell">'
                '<span class="falhas-status-rail"></span>'
                f'<span class="falhas-status-badge">{_html_escape(status)}</span>'
                '<span class="falhas-status-rail"></span>'
                "</span>"
                '<span class="falhas-os-cell">'
                '<span class="falhas-cell-title falhas-title-defeitos-encontrados">'
                "Defeitos encontrados</span>"
                f'<span class="falhas-chip-row">{_render_chips(encontrados, "falhas-chip-encontrado")}</span>'
                "</span>"
                '<span class="falhas-action-cell">'
                '<span class="falhas-action-button" title="Ver detalhes"><span class="falhas-eye-icon"></span></span>'
                '<span class="falhas-action-chevron">v</span>'
                "</span>"
                "</span></summary>"
                '<div class="falhas-row-detail-panel">'
                '<div class="falhas-row-detail-item">'
                '<span class="falhas-row-detail-label">Data</span>'
                f'<span>{_html_escape(data_texto)}</span>'
                "</div>"
                '<div class="falhas-row-detail-item">'
                '<span class="falhas-row-detail-label">Contrato/operadora</span>'
                f'<span>{_html_escape(row.get("contrato_operadora"))}</span>'
                "</div>"
                '<div class="falhas-row-detail-item">'
                '<span class="falhas-row-detail-label">Qtd. reclamados</span>'
                f'<span>{_format_int(qtd_reclamados)}</span>'
                "</div>"
                '<div class="falhas-row-detail-item">'
                '<span class="falhas-row-detail-label">Qtd. encontrados</span>'
                f'<span>{_format_int(qtd_encontrados)}</span>'
                "</div>"
                "</div></details>"
            )

        st.markdown(
            '<div class="falhas-os-table">'
            '<div class="falhas-os-table-header">'
            "<span>OS / Equipamento</span>"
            "<span>Defeitos reclamados</span>"
            "<span>Status</span>"
            '<span class="falhas-header-defeitos-encontrados">Defeitos encontrados</span>'
            "<span>Ações</span>"
            "</div>"
            f'{"".join(linhas_html)}</div>',
            unsafe_allow_html=True,
        )


def _carregar_mock_analise_falhas() -> pd.DataFrame:
    dados = [
        {
            "os": "20260125",
            "equipamento": "Validador V300",
            "defeitos_reclamados_lista": ["Não liga", "Sem comunicação"],
            "defeitos_encontrados_lista": ["Fonte queimada"],
            "status_comparacao": STATUS_PARCIAL,
            "data": "2026-01-25",
            "coordenacao": "COORDENAÇÃO DEMO",
            "contrato": "Contrato Demo",
            "operadora": "Operadora Demo",
        },
        {
            "os": "20260140",
            "equipamento": "Console C10",
            "defeitos_reclamados_lista": ["Tela apagada"],
            "defeitos_encontrados_lista": ["Display danificado"],
            "status_comparacao": STATUS_COMPATIVEL,
            "data": "2026-01-26",
            "coordenacao": "COORDENAÇÃO DEMO",
            "contrato": "Contrato Demo",
            "operadora": "Operadora Demo",
        },
        {
            "os": "20260152",
            "equipamento": "GPS G8",
            "defeitos_reclamados_lista": ["Sem sinal"],
            "defeitos_encontrados_lista": ["Antena rompida", "Conector solto"],
            "status_comparacao": STATUS_PARCIAL,
            "data": "2026-01-29",
            "coordenacao": "COORDENAÇÃO DEMO",
            "contrato": "Contrato Demo",
            "operadora": "Operadora Demo",
        },
        {
            "os": "20260166",
            "equipamento": "Validador V300",
            "defeitos_reclamados_lista": ["Erro no cartão"],
            "defeitos_encontrados_lista": ["Placa leitora queimada"],
            "status_comparacao": STATUS_DIVERGENTE,
            "data": "2026-02-03",
            "coordenacao": "COORDENAÇÃO DEMO",
            "contrato": "Contrato Demo",
            "operadora": "Operadora Demo",
        },
    ]
    df_mock = pd.DataFrame(dados)
    df_mock["defeitos_reclamados_agrupados"] = df_mock[
        "defeitos_reclamados_lista"
    ].str.join(" | ")
    df_mock["defeitos_encontrados_agrupados"] = df_mock[
        "defeitos_encontrados_lista"
    ].str.join(" | ")
    df_mock["qtd_reclamados"] = df_mock["defeitos_reclamados_lista"].str.len()
    df_mock["qtd_encontrados"] = df_mock["defeitos_encontrados_lista"].str.len()
    df_mock["data"] = pd.to_datetime(df_mock["data"], errors="coerce")
    df_mock["contrato_operadora"] = df_mock["contrato"] + " / " + df_mock["operadora"]
    return df_mock.sort_values("data", ascending=False, na_position="last")


def _consultar_oracle_e_salvar_csv() -> int:
    from Oracle.repositorio_oracle import consultar_destboad_dataframe

    df_destboad = consultar_destboad_dataframe()
    ORACLE_DESTBOAD_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_destboad.to_csv(ORACLE_DESTBOAD_CSV, index=False, encoding="utf-8-sig")
    carregar_analise_falhas_por_os.clear()
    return len(df_destboad)


def render_analise_falhas() -> None:
    _aplicar_estilos_analise_falhas()
    lista_drs_csv = _resolver_lista_drs_csv()
    st.markdown(
        """
        <div class="falhas-page-header">
            <div class="falhas-page-title">Análise de Falhas</div>
            <div class="falhas-page-subtitle">
                Comparativo entre defeitos reclamados e defeitos encontrados por OS
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_origem, col_acao = st.columns([2.8, 1])
    with col_origem:
        if ORACLE_DESTBOAD_CSV.exists():
            st.markdown(
                f'<div class="falhas-source-note">Origem atual: {_html_escape(ORACLE_DESTBOAD_CSV)}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="falhas-source-note">Usando dados mockados para o template visual.</div>',
                unsafe_allow_html=True,
            )
        if lista_drs_csv is not None:
            st.markdown(
                f'<div class="falhas-source-note">Relação DR carregada: {_html_escape(lista_drs_csv)}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning(
                "LISTA_DRs.csv não encontrada. A comparação usará apenas o código DR "
                "como fallback para o defeito reclamado."
            )
    with col_acao:
        if usuario_eh_admin():
            if st.button(
                "Atualizar Oracle",
                icon=":material/sync:",
                width="stretch",
                type="secondary",
            ):
                try:
                    total = _consultar_oracle_e_salvar_csv()
                    st.success(f"Oracle atualizado. Registros carregados: {total}")
                    st.rerun()
                except Exception as erro:
                    st.error("Erro ao consultar Oracle para Análise de Falhas.")
                    st.exception(erro)
        else:
            st.caption("Atualização Oracle disponível apenas para administradores.")

    if not ORACLE_DESTBOAD_CSV.exists():
        df_os = _carregar_mock_analise_falhas()
    else:
        try:
            df_os = carregar_analise_falhas_por_os(
                str(ORACLE_DESTBOAD_CSV),
                _obter_mtime_csv(ORACLE_DESTBOAD_CSV),
                str(lista_drs_csv) if lista_drs_csv is not None else None,
                _obter_mtime_csv(lista_drs_csv) if lista_drs_csv is not None else 0.0,
            )
        except Exception as erro:
            st.error("Erro ao carregar Análise de Falhas.")
            st.exception(erro)
            return

    if df_os.empty:
        st.warning("Sem OS válidas na base Oracle para Análise de Falhas.")
        return

    filtros = render_filtros_analise_falhas(df_os)
    df_filtrado = aplicar_filtros_analise_falhas(df_os, filtros)

    render_kpis_analise_falhas(calcular_kpis_analise_falhas(df_filtrado))
    st.write("")
    render_graficos_analise_falhas(df_filtrado)
    render_tabela_analise_falhas(df_filtrado)

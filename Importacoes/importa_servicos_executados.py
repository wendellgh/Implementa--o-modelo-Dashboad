import sys
from pathlib import Path
import argparse

ARQUIVO_CSV = Path(__file__).with_name("bsa_serv_exce.csv")
PYTHON_DIR = Path(__file__).resolve().parents[1] / "Python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from Oracle.servicos_executados_pipeline import carregar_servicos_executados_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importa bsa_serv_exce.csv para servicos_executados."
    )
    parser.add_argument(
        "--replace-table",
        action="store_true",
        help="Limpa toda a tabela antes de importar. Use apenas quando quiser recarregar tudo.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Apenas adiciona os registros, sem remover periodos existentes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not ARQUIVO_CSV.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {ARQUIVO_CSV}")

    total_linhas = carregar_servicos_executados_csv(
        ARQUIVO_CSV,
        substituir_tabela=args.replace_table,
        substituir_periodos_csv=not args.replace_table and not args.append,
    )
    print("Importacao concluida com sucesso.")
    print(f"Total de linhas importadas: {total_linhas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

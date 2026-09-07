import argparse
import sys
from pathlib import Path

ARQUIVO_CSV = Path(__file__).with_name("bsa_serv_exce.csv")
PYTHON_DIR = Path(__file__).resolve().parents[1] / "Python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from Oracle.servicos_executados_pipeline import carregar_servicos_executados_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Importa bsa_serv_exce.csv para servicos_executados. "
            "Por padrao, acrescenta somente registros ausentes no banco."
        )
    )
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument(
        "--adicionar-dados",
        "--adicionar_dados",
        "--append",
        dest="append",
        action="store_true",
        help=(
            "Acrescenta dados sem apagar o restante da tabela. Compara o CSV "
            "com o banco e insere somente registros ausentes. Este ja e o "
            "padrao; mantenha para deixar a intencao explicita."
        ),
    )
    modo.add_argument(
        "--replace-periods",
        action="store_true",
        help=(
            "Substitui somente os meses presentes no CSV: apaga esses periodos "
            "no banco e insere novamente."
        ),
    )
    modo.add_argument(
        "--replace-table",
        action="store_true",
        help="Limpa toda a tabela antes de importar. Use apenas quando quiser recarregar tudo.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not ARQUIVO_CSV.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {ARQUIVO_CSV}")

    total_linhas = carregar_servicos_executados_csv(
        ARQUIVO_CSV,
        substituir_tabela=args.replace_table,
        substituir_periodos_csv=args.replace_periods,
    )
    print("Importacao concluida com sucesso.")
    print(f"Total de linhas importadas: {total_linhas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

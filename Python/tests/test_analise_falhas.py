import unittest

import pandas as pd

from dashboard.analise_falhas import _converter_datas_destboad


class DatasAnaliseFalhasTest(unittest.TestCase):
    def test_considera_exclusivamente_data_de_abertura(self) -> None:
        dados = pd.DataFrame(
            {
                "ABERTURA_OS": ["10/08/2026", "", "data inválida"],
                "FECHAMENTO_OS": ["02/09/2026", "12/08/2026", "13/08/2026"],
                "MES": ["09", "08", "08"],
                "ANO": ["2026", "2026", "2026"],
            }
        )

        resultado = _converter_datas_destboad(dados)

        self.assertEqual(resultado.iloc[0], pd.Timestamp("2026-08-10"))
        self.assertTrue(pd.isna(resultado.iloc[1]))
        self.assertTrue(pd.isna(resultado.iloc[2]))


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd

from Oracle.consultas_oracle import QUERY_OS_NO_PERIODO
from dashboard.data import carregar_os_no_periodo, montar_os_por_cliente
from dashboard.filters import aplicar_filtros
from dashboard.visualizations import _agrupar_os_unicas


class OsPorClienteTest(unittest.TestCase):
    def tearDown(self) -> None:
        carregar_os_no_periodo.clear()

    def test_consulta_filtra_item_um_sem_restringir_status(self) -> None:
        consulta = " ".join(QUERY_OS_NO_PERIODO.split())

        self.assertIn('TRIM("ABA_ITEM") IN (\'1\', \'01\')', consulta)
        self.assertNotIn('"STATUS"', consulta)
        self.assertIn('TRIM("OS") AS "numero_os"', consulta)
        self.assertIn('TRIM("PRODUTO") AS "id_equipamento"', consulta)
        self.assertIn('TRIM("A1_PRACA") AS "praca"', consulta)
        self.assertIn("BETWEEN :data_inicio AND :data_fim", consulta)

    @patch(
        "Oracle.repositorio_oracle.consultar_os_no_periodo_dataframe"
    )
    def test_carregamento_preserva_dimensoes_dos_filtros(self, consultar) -> None:
        consultar.return_value = pd.DataFrame(
            [
                {
                    "CODIGO_CLIENTE": " 002 ",
                    "CLIENTE": " Cliente B ",
                    "NUMERO_OS": " OS-2 ",
                    "ID_EQUIPAMENTO": " EQ-1 ",
                    "EQUIPAMENTO": " Validador ",
                    "PRACA": " BHZ ",
                    "DATA_REF": "15/08/2026",
                },
            ]
        )
        data_inicio = date(2026, 8, 1)
        data_fim = date(2026, 8, 31)

        resultado = carregar_os_no_periodo(data_inicio, data_fim)

        consultar.assert_called_once_with(data_inicio, data_fim)
        self.assertEqual(resultado.loc[0, "contrato"], "Cliente B")
        self.assertEqual(resultado.loc[0, "operadora"], "Cliente B")
        self.assertEqual(resultado.loc[0, "equipamento"], "Validador")
        self.assertEqual(resultado.loc[0, "numero_os"], "OS-2")
        self.assertIn("coordenacao", resultado.columns)

    def test_resumo_conta_os_unicas_depois_dos_filtros(self) -> None:
        filtrado = pd.DataFrame(
            [
                {"codigo_cliente": "001", "cliente": "Cliente A", "numero_os": "1"},
                {"codigo_cliente": "001", "cliente": "Cliente A", "numero_os": "1"},
                {"codigo_cliente": "001", "cliente": "Cliente A", "numero_os": "2"},
                {"codigo_cliente": "002", "cliente": "Cliente B", "numero_os": "3"},
            ]
        )

        resultado = montar_os_por_cliente(filtrado)

        self.assertEqual(resultado["cliente"].tolist(), ["Cliente A", "Cliente B"])
        self.assertEqual(resultado["quantidade_os"].tolist(), [2, 1])

    def test_os_do_grafico_aceitam_todos_os_filtros_da_tela(self) -> None:
        dados = pd.DataFrame(
            [
                {
                    "data_ref": pd.Timestamp("2026-08-10"),
                    "contrato": "Cliente A",
                    "operadora": "Operadora A",
                    "equipamento": "Validador",
                    "coordenacao": "SUDESTE",
                    "praca": "BHZ",
                },
                {
                    "data_ref": pd.Timestamp("2026-08-10"),
                    "contrato": "Cliente B",
                    "operadora": "Operadora B",
                    "equipamento": "Câmera",
                    "coordenacao": "NORDESTE",
                    "praca": "SSA",
                },
            ]
        )
        filtros_base = {
            "periodo": (pd.Timestamp("2026-08-01"), pd.Timestamp("2026-08-31")),
            "filtro_contrato": [],
            "filtro_operadora": [],
            "filtro_equipamento": [],
            "filtro_coordenacao": [],
            "filtro_praca": [],
        }
        casos = {
            "filtro_contrato": "Cliente A",
            "filtro_operadora": "Operadora A",
            "filtro_equipamento": "Validador",
            "filtro_coordenacao": "SUDESTE",
            "filtro_praca": "BHZ",
        }

        for filtro, valor in casos.items():
            with self.subTest(filtro=filtro):
                resultado = aplicar_filtros(dados, {**filtros_base, filtro: [valor]})
                self.assertEqual(len(resultado), 1)
                self.assertEqual(resultado.iloc[0]["contrato"], "Cliente A")

    def test_drill_down_agrupa_os_unicas_por_operadora_e_equipamento(self) -> None:
        dados = pd.DataFrame(
            [
                {"operadora": "A", "equipamento": "Validador", "numero_os": "1"},
                {"operadora": "A", "equipamento": "Validador", "numero_os": "1"},
                {"operadora": "A", "equipamento": "Câmera", "numero_os": "2"},
                {"operadora": "B", "equipamento": "Validador", "numero_os": "3"},
            ]
        )

        operadoras = _agrupar_os_unicas(dados, "operadora")
        equipamentos = _agrupar_os_unicas(
            dados[dados["operadora"].eq("A")],
            "equipamento",
        )

        self.assertEqual(operadoras["operadora"].tolist(), ["A", "B"])
        self.assertEqual(operadoras["quantidade_os"].tolist(), [2, 1])
        self.assertEqual(equipamentos["quantidade_os"].sum(), 2)


if __name__ == "__main__":
    unittest.main()

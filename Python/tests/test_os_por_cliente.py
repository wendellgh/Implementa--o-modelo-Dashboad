import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd

from dashboard.data import carregar_os_no_periodo, montar_os_por_cliente
from dashboard.filters import aplicar_filtros
from dashboard.visualizations import _agrupar_os_unicas


class OsPorClienteTest(unittest.TestCase):
    def tearDown(self) -> None:
        carregar_os_no_periodo.clear()

    @patch("Oracle.repositorio_oracle.carregar_destboad_csv_dataframe")
    def test_csv_filtra_item_um_e_periodo_sem_restringir_status(
        self,
        carregar_csv,
    ) -> None:
        carregar_csv.return_value = pd.DataFrame(
            [
                {
                    "COD_CLIETE": "001",
                    "NOME": "Cliente A",
                    "OS": "OS-1",
                    "PRODUTO": "EQ-1",
                    "DESCRICAO": "Validador",
                    "A1_PRACA": "BHZ",
                    "ABERTURA_OS": "10/08/2026",
                    "ABA_ITEM": "01",
                    "STATUS": "ENCERRADO",
                },
                {
                    "COD_CLIETE": "001",
                    "NOME": "Cliente A",
                    "OS": "OS-2",
                    "PRODUTO": "EQ-1",
                    "DESCRICAO": "Validador",
                    "A1_PRACA": "BHZ",
                    "ABERTURA_OS": "11/08/2026",
                    "ABA_ITEM": "01",
                    "STATUS": "EM ABERTO",
                },
                {
                    "COD_CLIETE": "001",
                    "NOME": "Cliente A",
                    "OS": "OS-3",
                    "PRODUTO": "EQ-1",
                    "DESCRICAO": "Validador",
                    "A1_PRACA": "BHZ",
                    "ABERTURA_OS": "12/08/2026",
                    "ABA_ITEM": "02",
                    "STATUS": "ENCERRADO",
                },
                {
                    "COD_CLIETE": "001",
                    "NOME": "Cliente A",
                    "OS": "OS-4",
                    "PRODUTO": "EQ-1",
                    "DESCRICAO": "Validador",
                    "A1_PRACA": "BHZ",
                    "ABERTURA_OS": "31/07/2026",
                    "ABA_ITEM": "01",
                    "STATUS": "ENCERRADO",
                },
            ]
        )

        resultado = carregar_os_no_periodo(date(2026, 8, 1), date(2026, 8, 31))

        self.assertEqual(resultado["numero_os"].tolist(), ["OS-1", "OS-2"])

    @patch("Oracle.repositorio_oracle.carregar_destboad_csv_dataframe")
    def test_carregamento_preserva_dimensoes_dos_filtros(self, carregar_csv) -> None:
        carregar_csv.return_value = pd.DataFrame(
            [
                {
                    "COD_CLIETE": " 002 ",
                    "NOME": " Cliente B ",
                    "OS": " OS-2 ",
                    "PRODUTO": " EQ-1 ",
                    "DESCRICAO": " Validador ",
                    "A1_PRACA": " BHZ ",
                    "ABERTURA_OS": "15/08/2026",
                    "ABA_ITEM": "01",
                },
            ]
        )
        data_inicio = date(2026, 8, 1)
        data_fim = date(2026, 8, 31)

        resultado = carregar_os_no_periodo(data_inicio, data_fim)

        carregar_csv.assert_called_once()
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

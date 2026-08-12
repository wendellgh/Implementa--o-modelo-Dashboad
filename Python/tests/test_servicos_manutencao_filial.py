import unittest

import pandas as pd

from dashboard.data import _combinar_fontes_servicos, _preparar_dados_servicos
from dashboard.manutencao_filial_teste import (
    TITULO_PAGINA,
    _montar_catalogo_codigo_nome,
    _montar_tabela_ultimos_servicos,
    _validar_servico,
)
from dashboard.servicos_manutencao_filial import (
    CONSULTAR_SERVICOS_SQL,
    CRIAR_TABELA_SQL,
    INSERIR_SERVICO_SQL,
    formatar_numero_os,
)


class ServicosManutencaoFilialTest(unittest.TestCase):
    def test_titulo_padronizado(self) -> None:
        self.assertEqual(
            TITULO_PAGINA,
            "Serviços Executados – Manutenção Filial",
        )

    def test_catalogo_de_servicos_usa_referencia_oracle(self) -> None:
        oracle = pd.DataFrame(
            [
                {
                    "id_servico_executado": "SE-01",
                    "servico_executado": "Troca de equipamento",
                },
                {
                    "id_servico_executado": "SE-01",
                    "servico_executado": "Troca de equipamento",
                },
            ]
        )

        catalogo = _montar_catalogo_codigo_nome(
            oracle,
            "id_servico_executado",
            "servico_executado",
        )

        self.assertEqual(
            catalogo,
            {"SE-01 - Troca de equipamento": ("SE-01", "Troca de equipamento")},
        )

    def test_servico_valido_nao_depende_de_frota_ou_duplicidade_mensal(self) -> None:
        erros = _validar_servico(
            contrato="AC TRANSPORTES",
            operadora="CT EXPRESSO BSB",
            equipamento="DMX200L JI21 SEM BATERIA",
            servico_executado="Troca de equipamento",
        )

        self.assertEqual(erros, [])

    def test_fonte_manual_fica_compativel_com_consulta_oracle(self) -> None:
        manual = pd.DataFrame(
            [
                {
                    "id": 1,
                    "numero_os": "MF-00000001",
                    "data_ref": "2026-08-11",
                    "data_competencia": "2026-08-01",
                    "id_contrato": "COT37",
                    "contrato": "AC TRANSPORTES",
                    "id_operadora": "OP144",
                    "operadora": "CT EXPRESSO BSB",
                    "id_equipamento": "EQ39",
                    "equipamento": "DMX200L JI21 SEM BATERIA",
                    "numero_serie": "SERIE-001",
                    "id_servico_executado": "SE-01",
                    "servico_executado": "Troca de equipamento",
                    "qtd_servico": 1,
                    "defeito_reclamado": "DR-11",
                    "defeito_encontrado": "DE-125",
                    "solucao": "Equipamento substituído",
                    "tecnico_responsavel": "Técnico Teste",
                    "praca": "",
                    "nome_praca": "",
                    "coordenacao": "",
                    "criado_em": "2026-08-11 10:00:00-03:00",
                }
            ]
        )

        preparado = _preparar_dados_servicos(manual, origem="Manutenção Filial")

        self.assertEqual(preparado.loc[0, "origem"], "Manutenção Filial")
        self.assertEqual(preparado.loc[0, "numero_os"], "MF-00000001")
        self.assertEqual(preparado.loc[0, "qtd_servico"], 1)
        self.assertEqual(preparado.loc[0, "numero_serie"], "SERIE-001")
        self.assertEqual(preparado.loc[0, "servico_executado"], "Troca de equipamento")

        tabela = _montar_tabela_ultimos_servicos(
            preparado,
            "AC TRANSPORTES",
            "CT EXPRESSO BSB",
            "DMX200L JI21 SEM BATERIA",
        )
        self.assertEqual(len(tabela), 1)
        self.assertEqual(tabela.loc[0, "Número da OS"], "MF-00000001")
        self.assertEqual(tabela.loc[0, "Número de série"], "SERIE-001")
        self.assertNotIn("Qtd", tabela.columns)

    def test_numero_os_usa_prefixo_e_id_sem_exigir_sequencia_contigua(self) -> None:
        self.assertEqual(formatar_numero_os(1), "MF-00000001")
        self.assertEqual(formatar_numero_os(42), "MF-00000042")
        self.assertEqual(formatar_numero_os(100_000_000), "MF-100000000")
        self.assertIn("AS numero_os", CONSULTAR_SERVICOS_SQL)
        self.assertIn("qtd_servico", CONSULTAR_SERVICOS_SQL)

    def test_ultimas_os_do_mesmo_dia_usam_id_mais_recente(self) -> None:
        servicos = pd.DataFrame(
            [
                {
                    "id": id_registro,
                    "numero_os": formatar_numero_os(id_registro),
                    "data_ref": "2026-08-11",
                    "contrato": "AC TRANSPORTES",
                    "operadora": "CT EXPRESSO BSB",
                    "equipamento": "DMX200L JI21 SEM BATERIA",
                }
                for id_registro in range(1, 13)
            ]
        )

        tabela = _montar_tabela_ultimos_servicos(
            servicos,
            "AC TRANSPORTES",
            "CT EXPRESSO BSB",
            "DMX200L JI21 SEM BATERIA",
        )

        self.assertEqual(
            tabela["Número da OS"].tolist(),
            [formatar_numero_os(id_registro) for id_registro in range(12, 2, -1)],
        )

    def test_nova_os_usa_quantidade_um_por_default_do_banco(self) -> None:
        self.assertIn("qtd_servico integer NOT NULL DEFAULT 1", CRIAR_TABELA_SQL)
        self.assertNotIn("qtd_servico", INSERIR_SERVICO_SQL)

    def test_fonte_oracle_sem_numero_os_recebe_valor_vazio(self) -> None:
        oracle = pd.DataFrame(
            [
                {
                    "data_ref": "2026-08-11",
                    "servico_executado": "Atualização",
                    "qtd_servico": 1,
                }
            ]
        )

        preparado = _preparar_dados_servicos(oracle, origem="Oracle")

        self.assertEqual(preparado.loc[0, "numero_os"], "")

    def test_consulta_unificada_preserva_as_duas_origens(self) -> None:
        oracle = pd.DataFrame(
            [{"servico_executado": "Atualização", "qtd_servico": 2, "origem": "Oracle"}]
        )
        filial = pd.DataFrame(
            [
                {
                    "servico_executado": "Troca de equipamento",
                    "qtd_servico": 1,
                    "origem": "Manutenção Filial",
                }
            ]
        )

        combinado = _combinar_fontes_servicos(oracle, filial)

        self.assertEqual(len(combinado), 2)
        self.assertEqual(set(combinado["origem"]), {"Oracle", "Manutenção Filial"})
        self.assertEqual(int(combinado["qtd_servico"].sum()), 3)


if __name__ == "__main__":
    unittest.main()

PAGE_CONFIG = {
    "page_title": "Dashboard de Manutencao",
    "page_icon": ":bar_chart:",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

APP_TITLE = "Dashboard de Manutencao das Filiais"

MENU_ITEMS = ["Dashboard", "Resumo", "Tabela"]

DB_SETTINGS = {
    "usuario": "app_user",
    "senha": "app123",
    "host": "localhost",
    "porta": "5432",
    "banco": "app_db",
}

BASE_QUERY = """
select
    data_ref,
    id_contrato,
    contrato,
    id_operadora,
    operadora,
    cod_equipamento,
    equipamento,
    frota,
    qtd,
    percentual
from base_historica_manutencao
"""

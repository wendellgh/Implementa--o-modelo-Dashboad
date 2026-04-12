PAGE_CONFIG = {
    "page_title": "Dashboard de Manutencao",
    "layout": "wide",
}

APP_TITLE = "Dashboard de Manutencao das Filiais"

DB_SETTINGS = {
    "usuario": "app_user",
    "senha": "app123",
    "host": "localhost",
    "porta": "5432",
    "banco": "app_db",
}

RESUMO_QUERY = "select * from vw_dashboard_resumo order by equipamento"
EVOLUCAO_QUERY = "select * from vw_dashboard_evolucao_mensal order by mes, equipamento"


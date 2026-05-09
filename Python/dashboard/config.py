PAGE_CONFIG = {
    "page_title": "Dashboard de Manutencao",
    "page_icon": ":bar_chart:",
    "layout": "wide",
    "initial_sidebar_state": "auto",
}

APP_TITLE = "Dashboard de Manutencao das Filiais"

MENU_ITEMS = ["Dashboard", "Resumo", "Tabela", "Contando Frota - Teste", "Serviços Executados - Teste", "Oracle DESTBOAD"]

PERFIL_ADMIN = "admin"
PERFIL_USUARIO = "usuario"

USUARIOS_APP = {
    "admin": {
        "senha": "admin123",
        "nome": "Administrador",
        "perfil": PERFIL_ADMIN,
        "prioridade": 100,
    },
    
    "usuario": {
        "senha": "usuario123",
        "nome": "Usuario Padrao",
        "perfil": PERFIL_USUARIO,
        "prioridade": 10,
    },
    "Wendell":{
        "senha": "201915",
        "nome": "Wendell Mendes - Master",
        "perfil": PERFIL_ADMIN,
        "prioridade": 100,
    }
    
}

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

BASE_QUERY_2 = """
select
    "DATA" as data_ref,
    "ID_CONTRATO" as id_contrato,
    "CONTRATO" as contrato,
    "ID_EQUIPAMENTO" as id_equipamento,
    "EQUIPAMENTO" as equipamento,
    "ID_OPERADORA" as id_operadora,
    "OPERADORA" as operadora,
    "ID_SERVICO_EXECUTADO" as id_servico_executado,
    "SERVIC_EXECUTADO" as servico_executado,
    "QTD_SERVICO" as qtd_servico
from servicos_executados
"""

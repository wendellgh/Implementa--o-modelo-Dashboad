QUERY_DESTBOAD = """
SELECT *
FROM "SIGA"."DESTBOAD"
"""

QUERY_DESTBOAD_COM_FILTRO_ABERTURA_OS = """
SELECT *
FROM "SIGA"."DESTBOAD"
WHERE CASE
    WHEN REGEXP_LIKE(TRIM("ABERTURA_OS"), '^(0[1-9]|[12][[:digit:]]|3[01])/(0[1-9]|1[0-2])/[[:digit:]]{4}$')
        THEN SUBSTR(TRIM("ABERTURA_OS"), 7, 4)
            || SUBSTR(TRIM("ABERTURA_OS"), 4, 2)
            || SUBSTR(TRIM("ABERTURA_OS"), 1, 2)
    WHEN REGEXP_LIKE(TRIM("ABERTURA_OS"), '^[[:digit:]]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][[:digit:]]|3[01])$')
        THEN SUBSTR(TRIM("ABERTURA_OS"), 1, 4)
            || SUBSTR(TRIM("ABERTURA_OS"), 6, 2)
            || SUBSTR(TRIM("ABERTURA_OS"), 9, 2)
END >= :data_inicio
"""


QUERY_OS_NO_PERIODO = """
SELECT DISTINCT
    TRIM("COD_CLIETE") AS "codigo_cliente",
    TRIM("NOME") AS "cliente",
    TRIM("OS") AS "numero_os",
    TRIM("PRODUTO") AS "id_equipamento",
    NVL(TRIM("DESCRICAO"), TRIM("SERIE_PRODUTO")) AS "equipamento",
    TRIM("A1_PRACA") AS "praca",
    TRIM("ABERTURA_OS") AS "data_ref"
FROM "SIGA"."DESTBOAD"
WHERE TRIM("ABA_ITEM") IN ('1', '01')
  AND CASE
      WHEN REGEXP_LIKE(TRIM("ABERTURA_OS"), '^(0[1-9]|[12][[:digit:]]|3[01])/(0[1-9]|1[0-2])/[[:digit:]]{4}$')
          THEN SUBSTR(TRIM("ABERTURA_OS"), 7, 4)
              || SUBSTR(TRIM("ABERTURA_OS"), 4, 2)
              || SUBSTR(TRIM("ABERTURA_OS"), 1, 2)
      WHEN REGEXP_LIKE(TRIM("ABERTURA_OS"), '^[[:digit:]]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][[:digit:]]|3[01])$')
          THEN SUBSTR(TRIM("ABERTURA_OS"), 1, 4)
              || SUBSTR(TRIM("ABERTURA_OS"), 6, 2)
              || SUBSTR(TRIM("ABERTURA_OS"), 9, 2)
  END BETWEEN :data_inicio AND :data_fim
"""


QUERY_OS_BHZ = """
SELECT *
FROM "SIGA"."OS_STATUS_FILIAL"
"""

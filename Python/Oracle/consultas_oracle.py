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


QUERY_OS_BHZ = """
SELECT *
FROM "SIGA"."OS_STATUS_FILIAL"
"""

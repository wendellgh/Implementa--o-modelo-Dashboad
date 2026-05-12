BEGIN;

ALTER TABLE public.base_historica_manutencao
    ADD COLUMN IF NOT EXISTS data_competencia date;

UPDATE public.base_historica_manutencao
SET data_competencia = date_trunc('month', data_ref)::date
WHERE data_ref IS NOT NULL
  AND (
      data_competencia IS NULL
      OR data_competencia <> date_trunc('month', data_ref)::date
  );

WITH removidas AS (
    DELETE FROM public.base_historica_manutencao
    WHERE data_ref IS NULL
      AND data_competencia IS NULL
      AND NULLIF(btrim(coalesce(id_contrato, '')), '') IS NULL
      AND NULLIF(btrim(coalesce(contrato, '')), '') IS NULL
      AND NULLIF(btrim(coalesce(id_operadora, '')), '') IS NULL
      AND NULLIF(btrim(coalesce(operadora, '')), '') IS NULL
      AND NULLIF(btrim(coalesce(cod_equipamento, '')), '') IS NULL
      AND NULLIF(btrim(coalesce(equipamento, '')), '') IS NULL
      AND coalesce(frota, 0) = 0
      AND coalesce(qtd, 0) = 0
      AND coalesce(percentual, 0) = 0
    RETURNING 1
)
SELECT count(*) AS linhas_vazias_removidas
FROM removidas;

WITH duplicadas AS (
    SELECT
        id,
        row_number() OVER (
            PARTITION BY
                data_ref,
                data_competencia,
                btrim(coalesce(id_contrato, '')),
                btrim(coalesce(contrato, '')),
                btrim(coalesce(id_operadora, '')),
                btrim(coalesce(operadora, '')),
                btrim(coalesce(cod_equipamento, '')),
                btrim(coalesce(equipamento, '')),
                frota,
                qtd,
                percentual
            ORDER BY id
        ) AS ordem
    FROM public.base_historica_manutencao
),
removidas AS (
    DELETE FROM public.base_historica_manutencao AS base
    USING duplicadas
    WHERE base.id = duplicadas.id
      AND duplicadas.ordem > 1
    RETURNING base.id
)
SELECT count(*) AS duplicadas_exatas_removidas
FROM removidas;

SELECT setval(
    'public.base_historica_manutencao_id_seq',
    greatest(
        coalesce((SELECT max(id) FROM public.base_historica_manutencao), 1),
        1
    ),
    true
);

COMMIT;

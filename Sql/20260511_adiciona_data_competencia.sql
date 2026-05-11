ALTER TABLE public.base_historica_manutencao
    ADD COLUMN IF NOT EXISTS data_competencia date;

ALTER TABLE public.servicos_executados
    ADD COLUMN IF NOT EXISTS "DATA_COMPETENCIA" date;

UPDATE public.base_historica_manutencao
SET data_competencia = date_trunc('month', data_ref)::date
WHERE data_ref IS NOT NULL
  AND (
      data_competencia IS NULL
      OR data_competencia <> date_trunc('month', data_ref)::date
  );

UPDATE public.servicos_executados
SET "DATA_COMPETENCIA" = date_trunc(
    'month',
    CASE
        WHEN trim("DATA") ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'
            THEN to_date(trim("DATA"), 'DD/MM/YYYY')
        WHEN trim("DATA") ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
            THEN trim("DATA")::date
        ELSE NULL
    END
)::date
WHERE "DATA" IS NOT NULL
  AND trim("DATA") <> ''
  AND (
      "DATA_COMPETENCIA" IS NULL
      OR "DATA_COMPETENCIA" <> date_trunc(
          'month',
          CASE
              WHEN trim("DATA") ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'
                  THEN to_date(trim("DATA"), 'DD/MM/YYYY')
              WHEN trim("DATA") ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                  THEN trim("DATA")::date
              ELSE NULL
          END
      )::date
  );

CREATE INDEX IF NOT EXISTS idx_base_historica_manutencao_data_competencia
    ON public.base_historica_manutencao (data_competencia);

CREATE INDEX IF NOT EXISTS idx_servicos_executados_data_competencia
    ON public.servicos_executados ("DATA_COMPETENCIA");

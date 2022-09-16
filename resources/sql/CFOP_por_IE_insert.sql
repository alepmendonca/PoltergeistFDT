INSERT INTO GIA_CFOP
SELECT DISTINCT
   IE::BIGINT,
   ('01/' || SUBSTRING(APURACAO,5,2) || '/' || SUBSTRING(APURACAO,1,4))::DATE,
   CFOP6::INTEGER/100,
   REPLACE(REPLACE(Valor_Contabil, '.', ''), ',', '.') :: NUMERIC(12,2),
   REPLACE(REPLACE(Valor_BC_ICMS, '.', ''), ',', '.') :: NUMERIC(12,2),
   REPLACE(REPLACE(Valor_ICMS, '.', ''), ',', '.') :: NUMERIC(12,2),
   REPLACE(REPLACE(Valor_ISENTO, '.', ''), ',', '.') :: NUMERIC(12,2),
   REPLACE(REPLACE(Valor_OUTROS, '.', ''), ',', '.') :: NUMERIC(12,2),
   REPLACE(REPLACE(Valor_ICMS_ST, '.', ''), ',', '.') :: NUMERIC(12,2)
FROM GIA_CFOP_TEMP;
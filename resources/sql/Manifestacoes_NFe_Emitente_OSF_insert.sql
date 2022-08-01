INSERT INTO NFE_MDF
SELECT DISTINCT
   Chave
  ,Desc_Evento
  ,substring(Desc_Justificativa, 100)
  ,CASE WHEN LENGTH(Ind_Origem) = 0 THEN NULL ELSE Ind_Origem::INT END
  ,REGEXP_REPLACE(Ind_Autor, '[^0-9]+', '', 'g')::bigint::varchar
FROM NFE_MDF_TEMP
WHERE CHAVE IN (SELECT CHAVE FROM NFE)
AND length(trim(desc_evento)) > 0
ON CONFLICT DO NOTHING;
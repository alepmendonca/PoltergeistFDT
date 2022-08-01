/**
 * Insere primeiro Itens Emitente
 */
INSERT INTO NFE_ITEM 
SELECT
   Chave
  ,REGEXP_REPLACE(CNPJ_Emit, '[^0-9]+', '', 'g')
  ,CAST(Item AS INTEGER)
  ,Desc_Produto
  ,Cod_Produto
  ,CASE WHEN LENGTH(REGEXP_REPLACE(GTIN, '[^0-9]+', '', 'g')) = 0 THEN NULL ELSE REGEXP_REPLACE(GTIN, '[^0-9]+', '', 'g') :: BIGINT END
  ,CAST(NCM AS INTEGER)
  ,CASE WHEN LENGTH(TRIM(CEST)) = 0 OR TRIM(CEST)::BIGINT = 0 THEN NULL ELSE substring(REPLACE(TO_CHAR(TRIM(CEST)::BIGINT, '00:000:00'), ':', '.'), 2) END
  ,CAST(CFOP AS INTEGER)
  ,(CASE WHEN LENGTH(Origem_Mercadoria) = 0 THEN 0 ELSE Origem_Mercadoria::INTEGER END)*100 + CASE WHEN LENGTH(Codigo_Tributacao) = 0 THEN 0 ELSE Codigo_Tributacao::INTEGER END
  ,CASE WHEN LENGTH(REGEXP_REPLACE(CSOSN, '[^0-9]+', '', 'g')) = 0 THEN NULL ELSE REGEXP_REPLACE(CSOSN, '[^0-9]+', '', 'g') :: INTEGER END
  ,CASE WHEN LENGTH(Quantidade) = 0 THEN 0.0 ELSE REPLACE(REPLACE(Quantidade, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,TRIM(Unidade)
  ,REPLACE(REPLACE(Valor_Produto, '.', ''), ',', '.') :: NUMERIC(12,2)
  ,CASE WHEN LENGTH(Valor_Desconto) = 0 THEN 0.0 ELSE REPLACE(REPLACE(Valor_Desconto, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(Valor_Outro) = 0 THEN 0.0 ELSE REPLACE(REPLACE(Valor_Outro, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(ICMS_BC) = 0 THEN 0.0 ELSE REPLACE(REPLACE(ICMS_BC, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(ICMS_Aliquota) = 0 THEN 0.0 ELSE REPLACE(REPLACE(ICMS_Aliquota, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(ICMS_BC_Percentual_Red) = 0 THEN 0.0 ELSE REPLACE(REPLACE(ICMS_BC_Percentual_Red, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(ICMS) = 0 THEN 0.0 ELSE REPLACE(REPLACE(ICMS, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(ICMSST_BC) = 0 THEN 0.0 ELSE REPLACE(REPLACE(ICMSST_BC, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(ICMSST_Aliquota) = 0 THEN 0.0 ELSE REPLACE(REPLACE(ICMSST_Aliquota, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(ICMSST_BC_Percentual_Red) = 0 THEN 0.0 ELSE REPLACE(REPLACE(ICMSST_BC_Percentual_Red, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(ICMSST) = 0 THEN 0.0 ELSE REPLACE(REPLACE(ICMSST, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(ICMSST_BC_Retido_Op_Anterior) = 0 THEN 0.0 ELSE REPLACE(REPLACE(ICMSST_BC_Retido_Op_Anterior, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(ICMSST_Retido_Op_Anterior) = 0 THEN 0.0 ELSE REPLACE(REPLACE(ICMSST_Retido_Op_Anterior, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(IPI) = 0 THEN 0.0 ELSE REPLACE(REPLACE(IPI, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(PIS) = 0 THEN 0.0 ELSE REPLACE(REPLACE(PIS, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(COFINS) = 0 THEN 0.0 ELSE REPLACE(REPLACE(COFINS, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,DI
  ,FCI
  ,CASE WHEN LENGTH(Indicador_Modalidade_Frete) = 0 THEN NULL ELSE CAST(Indicador_Modalidade_Frete AS INTEGER) END
  ,CASE WHEN LENGTH(Valor_Frete) = 0 THEN 0.0 ELSE REPLACE(REPLACE(Valor_Frete, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(Valor_Seguro) = 0 THEN 0.0 ELSE REPLACE(REPLACE(Valor_Seguro, '.', ''), ',', '.') :: NUMERIC(10,2) END
  ,CASE WHEN LENGTH(Data_Desembaraco) = 0 THEN NULL ELSE CAST(Data_Desembaraco AS DATE) END
  ,UF_Desembaraco
  ,Descricao_Texto
  ,CASE WHEN length(CPF_Dest) = 0 THEN NULL ELSE REGEXP_REPLACE(CPF_Dest, '[^0-9]+', '', 'g') END
  ,CASE WHEN LENGTH(TRIM(CNAE)) = 0 THEN NULL ELSE 
  		CASE WHEN REGEXP_REPLACE(TRIM(CNAE), '[^0-9]+', '', 'g')::INTEGER NOT IN (SELECT CODIGO FROM CNAE WHERE CODIGO = REGEXP_REPLACE(TRIM(CNAE), '[^0-9]+', '', 'g')::INTEGER) 
  		THEN NULL ELSE REGEXP_REPLACE(TRIM(CNAE), '[^0-9]+', '', 'g')::INTEGER END END
  ,CASE WHEN LENGTH(Codigo_Tributacao) = 0 THEN 0 ELSE Codigo_Tributacao::INTEGER END
  ,CASE WHEN LENGTH(Origem_Mercadoria) = 0 THEN 0 ELSE Origem_Mercadoria::INTEGER END
  ,0.0 --Não faz sentido falar em Credito SN quando é nota do emitente
  ,0.0 --Não faz sentido falar em Credito SN quando é nota do emitente
FROM NFE_ITEM_EMIT_TEMP t 
WHERE CHAVE IN (SELECT CHAVE FROM NFE)
ON CONFLICT DO NOTHING;

/**
 * Adiciona uns CNAE Destinatario quando vier informacao no NF-e Item
 */
UPDATE NFE SET (CNAE_DEST) = (SELECT DISTINCT ON (CHAVE) CNAE FROM NFE_ITEM WHERE NFE.CHAVE = NFE_ITEM.CHAVE AND cnae IS NOT NULL)
WHERE NFE.CNAE_DEST IS NULL;
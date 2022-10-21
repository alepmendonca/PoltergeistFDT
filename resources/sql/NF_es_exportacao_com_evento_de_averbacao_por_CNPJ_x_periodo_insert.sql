INSERT INTO EXPORTACAO
	SELECT CHAVE, AVERBACAO_TOTAL = 'S', REPLACE(REPLACE(VALOR_NAO_EXPORTADO, '.', ''), ',', '.')::NUMERIC(10,2)
	FROM EXPORTACAO_TEMP;

INSERT INTO EXPORTACAO_ITEM
	SELECT CHAVE, ITEM::INTEGER, CFOP::INTEGER, NCM::INTEGER, AVERBACAO_TOTAL_ITEM = 'S', 
		CASE WHEN LENGTH(AVERBACAO) = 0 THEN NULL ELSE AVERBACAO::DATE END,
		REPLACE(REPLACE(QTD_TRIBUTAVEL, '.', ''), ',', '.')::NUMERIC(10,2),
		REPLACE(REPLACE(QTD_TRIBUTAVEL_NAO_EXPORTADA, '.', ''), ',', '.')::NUMERIC(10,2),
		DESCRICAO_AVERBACAO
	FROM EXPORTACAO_ITEM_TEMP;

UPDATE EXPORTACAO_ITEM
	SET DUE = TEMP.DUE, DUE_ITEM = TEMP.ITEM_DUE::INTEGER
	FROM EXPORTACAO_ITEM_DUE_TEMP AS TEMP
	WHERE TEMP.CHAVE = EXPORTACAO_ITEM.CHAVE AND TEMP.ITEM::INTEGER = EXPORTACAO_ITEM.ITEM;
	
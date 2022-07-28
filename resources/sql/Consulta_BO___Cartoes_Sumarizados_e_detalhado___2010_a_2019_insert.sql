INSERT INTO TRANSACAO_CARTAO
SELECT 
	cnpj,
	emissor,
	emissao::DATE,
	tipo_operacao,
	transacao,
	creddeb,
	REPLACE(REPLACE(valor, '.', ''), ',', '.')::NUMERIC(10,2)
FROM TRANSACAO_CARTAO_TEMP;
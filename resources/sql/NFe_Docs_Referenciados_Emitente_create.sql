/**
 * Relacionamento entre documentos fiscais
 * Relatorios Launchpad
 * 		NFe Docs Referenciados Emitente
 * 		NFe Docs Referenciados Destinatario
 */
CREATE TABLE IF NOT EXISTS NFE_x_NFE (
	CHAVE_REFERENTE		CHAR(44) NOT NULL REFERENCES NFE(CHAVE),
	CHAVE_REFERENCIADA	CHAR(44) NOT NULL REFERENCES NFE(CHAVE),
	PRIMARY KEY (CHAVE_REFERENTE, CHAVE_REFERENCIADA)
);

CREATE TEMP TABLE IF NOT EXISTS NFE_REFS_TEMP (
	CNPJ_EMITENTE	VARCHAR
	,NFE_REFERENTE	VARCHAR
	,NFE_REFERENCIADA	VARCHAR
	,CTE_REFERENCIADA	VARCHAR
	,CNPJ_EMIT_RURAL	VARCHAR
	,CPF_EMIT_RURAL		VARCHAR
	,IE_EMIT_RURAL		VARCHAR
	,MODELO_RURAL		VARCHAR
	,SERIE_RURAL		VARCHAR
	,NUMERO_RURAL		VARCHAR
	,CNPJ_EMIT_MOD1		VARCHAR
	,MODELO_MOD1		VARCHAR
	,SERIE_MOD1			VARCHAR
	,NUMERO_MOD1		VARCHAR
	,REF_MES_EMISSAO	VARCHAR
	,MODELO_ECF			VARCHAR
	,ORDEM_ECF			VARCHAR
	,ORDEM_OPER_ECF		VARCHAR
	,CNPJ_DESTINATARIO	VARCHAR
	,CPF_DESTINATARIO	VARCHAR
	,EMISSAO			VARCHAR
);
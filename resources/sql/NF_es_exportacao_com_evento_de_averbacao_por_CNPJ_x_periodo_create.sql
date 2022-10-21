CREATE TABLE IF NOT EXISTS EXPORTACAO (
	CHAVE			VARCHAR(44) NOT NULL REFERENCES NFE(CHAVE) PRIMARY KEY,
	IS_EXPORTACAO_TOTAL	BOOLEAN,
	VALOR_NAO_EXPORTADO	NUMERIC(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS EXPORTACAO_ITEM (
	CHAVE				VARCHAR(44) NOT NULL,
	ITEM				INTEGER NOT NULL,
	CFOP				INTEGER NOT NULL REFERENCES CFOP(CODIGO),
	NCM				INTEGER NOT NULL REFERENCES NCM(CODIGO),
	IS_EXPORTACAO_TOTAL		BOOLEAN,
	DATA_AVERBACAO			DATE,
	QTD_TRIBUTAVEL			NUMERIC(10,2) NOT NULL,
	QTD_TRIBUTAVEL_NAO_EXPORTADA	NUMERIC(10,2) NOT NULL,
	ULTIMO_EVENTO			VARCHAR(100),
	DUE				VARCHAR(14),
	DUE_ITEM			INTEGER,
	FOREIGN KEY (CHAVE, ITEM) REFERENCES NFE_ITEM(CHAVE, ITEM)
);

CREATE TEMP TABLE EXPORTACAO_TEMP (
	CHAVE VARCHAR
	,EMISSAO VARCHAR
	,CNPJ_EMITENTE VARCHAR
	,AVERBACAO_TOTAL VARCHAR
	,TOTAL_NFE VARCHAR
	,VALOR_NAO_EXPORTADO VARCHAR
	,NATUREZA_OP VARCHAR
	,NUMERO VARCHAR
	,OUTRA_NF_AVERBADA VARCHAR);

CREATE TEMP TABLE EXPORTACAO_ITEM_TEMP (
	CHAVE VARCHAR
	,ITEM VARCHAR
	,CNPJ_EMITENTE VARCHAR
	,NCM VARCHAR
	,NUMERO VARCHAR
	,EMISSAO_ZOADA VARCHAR
	,CFOP VARCHAR
	,AVERBACAO VARCHAR
	,AVERBACAO_TOTAL_ITEM VARCHAR
	,AVERBACAO_TOTAL_NFE VARCHAR
	,VALOR_NAO_EXPORTADO VARCHAR
	,QTD_ITEM_AVERBACAO VARCHAR
	,QTD_TRIBUTAVEL VARCHAR
	,QTD_TRIBUTAVEL_NAO_EXPORTADA VARCHAR
	,TOTAL_NFE VARCHAR
	,EMISSAO VARCHAR
	,ID_EVENTO VARCHAR
	,ULTIMO_EVENTO_CANCELAMENTO VARCHAR
	,DESCRICAO_AVERBACAO VARCHAR);

CREATE TEMP TABLE EXPORTACAO_ITEM_DUE_TEMP (
	CHAVE VARCHAR
	,AVERBACAO VARCHAR
	,DUE VARCHAR
	,ITEM_DUE VARCHAR
	,ITEM VARCHAR
	,QTD_ITEM VARCHAR
	,IND_MOTIVO_ALTERACAO VARCHAR
	,EMISSAO VARCHAR
	,CNPJ_EMITENTE VARCHAR
	,AVERBACAO_TOTAL_ITEM VARCHAR
	,SITUACAO_DOCUMENTO VARCHAR
	,CHAVE_REPETIDA VARCHAR
	,DATA_EVENTO VARCHAR);

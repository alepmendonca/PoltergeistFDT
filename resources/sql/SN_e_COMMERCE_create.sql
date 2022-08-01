CREATE TABLE IF NOT EXISTS INTERMEDIARIO_ARQUIVO (
	ID			INTEGER NOT NULL PRIMARY KEY,
	CNPJ			CHAR(14) NOT NULL,
	REFERENCIA		CHAR(6) NOT NULL,
	RAZAO_SOCIAL		VARCHAR(100),
	DT_TRANSMISSAO		TIMESTAMP,
	ATIVO			BOOLEAN,
	NOME_ARQUIVO		VARCHAR(100)
);
CREATE TABLE IF NOT EXISTS INTERMEDIARIO_TRANSACAO (
	CNPJ			CHAR(14) NOT NULL,
	EMISSAO			DATE NOT NULL,
	TRANSACAO		VARCHAR NOT NULL,
	VALOR			NUMERIC(10,2) NOT NULL,
	ID_ARQUIVO		INTEGER NOT NULL REFERENCES INTERMEDIARIO_ARQUIVO(ID),
	QTD_INTERMEDIACAO	INTEGER,
	TIPO			CHAR(2),
	PRIMARY KEY (CNPJ, TRANSACAO, ID_ARQUIVO)
);
CREATE INDEX IF NOT EXISTS INTERMEDIARIO_TRANSACAO_emissao_idx ON INTERMEDIARIO_TRANSACAO (cnpj, emissao, transacao);
CREATE INDEX IF NOT EXISTS INTERMEDIARIO_TRANSACAO_valor_idx ON INTERMEDIARIO_TRANSACAO (valor);

CREATE TEMP TABLE INTERMEDIARIO_ARQUIVO_TEMP (ID_ARQUIVO VARCHAR, CNPJ VARCHAR, REFERENCIA VARCHAR, NOME VARCHAR, TRANSMISSAO VARCHAR, ATIVO VARCHAR, ARQUIVO VARCHAR);
CREATE TEMP TABLE INTERMEDIARIO_IC_TEMP (ID_ARQUIVO VARCHAR, CNPJ_IC VARCHAR, NOME VARCHAR, TRANSMISSAO VARCHAR, IE VARCHAR, EMISSAO VARCHAR, MESREFERENCIA VARCHAR, ANOREFERENCIA VARCHAR, TRANSACAO VARCHAR, VALOR VARCHAR, QTD VARCHAR, CNPJ_CLIENTE VARCHAR, REFERENCIA VARCHAR);
CREATE TEMP TABLE INTERMEDIARIO_IF_TEMP (ID_ARQUIVO VARCHAR, CNPJ_IF VARCHAR, NOME VARCHAR, TRANSMISSAO VARCHAR, CNPJ_CLIENTE VARCHAR, IE VARCHAR, EMISSAO VARCHAR, MESREFERENCIA VARCHAR, ANOREFERENCIA VARCHAR, TRANSACAO VARCHAR, VALOR VARCHAR, QTD VARCHAR, REFERENCIA VARCHAR);
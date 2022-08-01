CREATE TABLE IF NOT EXISTS transacao_cartao (
	cnpj		char(14)	not null,
	emissor		varchar(100)	NOT NULL,
	emissao		date		not null,
	tipo		VARCHAR(100)	NOT NULL,
	identificador	VARCHAR(50)	NOT NULL,
	natureza	VARCHAR(50)	NOT NULL,
	valor		numeric(10,2)	NOT NULL
);
CREATE INDEX IF NOT EXISTS transacao_cartao_emissao on TRANSACAO_CARTAO USING BTREE(cnpj, emissao);
CREATE UNIQUE INDEX IF NOT EXISTS transacao_cartao_unq on TRANSACAO_CARTAO (cnpj, emissao, identificador, valor);

CREATE TEMP TABLE transacao_cartao_temp (
	cnpj		VARCHAR,
	emissor		VARCHAR,
	emissao		VARCHAR,
	tipo_operacao	VARCHAR,
	cod_tipo	VARCHAR,
	valor		VARCHAR,
	transacao	VARCHAR,
	cod_creddeb	VARCHAR,
	creddeb		VARCHAR
);
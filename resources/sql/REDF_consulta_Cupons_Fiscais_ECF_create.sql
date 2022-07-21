CREATE TABLE IF NOT EXISTS redf (
	cnpj		char(14)	not null,	
	ie		bigint		not null,
	ecf_serie	char(20)	not null,
	ecf_fabr	VARCHAR(20),
	ecf_modelo	varchar(30),
	emissao		date		not null,
	coo		integer		not null,
	valor		numeric(8,2),
	PRIMARY KEY (ecf_serie, coo)
);
CREATE INDEX redf_emissao_idx ON redf (emissao,valor);

CREATE TEMP TABLE redf_temp (
	cnpj		VARCHAR,
	ie 			VARCHAR,
	ecf_serie	VARCHAR,
	ecf_fabr	VARCHAR,
	ecf_modelo	VARCHAR,
	emissao		VARCHAR,
	coo			VARCHAR,
	valor		VARCHAR
);
CREATE TABLE IF NOT EXISTS sat_cupom (
	ie		bigint		not null,
	sat_serie	integer		not null,
	emissao		date		not null,
	cancelado	char(1),
	cupom		varchar(50)	not null,
	numero		integer		not null,
	emissao_hora	char(6),
	recepcao	date		not null,
	valor		numeric(10,2),
	icms		numeric(10,2),
	valor_produtos	numeric(10,2),
	valor_desconto	numeric(10,2),
	pis		numeric(10,2),
	cofins		numeric(10,2),
	pis_st		numeric(10,2),
	cofins_st	numeric(10,2),
	valor_outros	numeric(10,2),
	acres_desconto	numeric(10,2),
	tributos_estim	numeric(10,2),
	PRIMARY KEY	(ie, cupom)
);
CREATE INDEX IF NOT EXISTS sat_cupom_ie on SAT_CUPOM USING HASH(IE);
CREATE INDEX IF NOT EXISTS sat_cupom_emissao ON sat_cupom (emissao,valor);

CREATE TEMP TABLE sat_cupom_temp (
	ie		varchar,
	sat_serie	varchar,
	emissao		varchar,
	cancelado	varchar,
	cupom		varchar,
	numero		varchar,
	emissao_hora	varchar,
	recepcao	varchar,
	valor		varchar,
	icms		varchar,
	valor_produtos	varchar,
	valor_desconto	varchar,
	pis		varchar,
	cofins		varchar,
	pis_st		varchar,
	cofins_st	varchar,
	valor_outros	varchar,
	acres_desconto	varchar,
	tributos_estim	varchar,
	possui_destinatario varchar
);
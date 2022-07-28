/** Insere NFe_Destinatario da UF SP */
INSERT INTO NFE
SELECT
	Chave,
	CAST(Numero AS INTEGER),
	CAST(Serie AS INTEGER),
	CAST(Modelo AS INTEGER),
	CAST(Emissao AS DATE),
	Razao_Social_Emit,
	REGEXP_REPLACE(CNPJ_Emit, '[^0-9]+', '', 'g'),
	CAST(IE_Emit AS BIGINT),
	CRT,
	DRT_Emit,
	UF_Emit,
	Razao_Social_Dest,
	REGEXP_REPLACE(CNPJ_Dest, '[^0-9]+', '', 'g'),
	CASE WHEN LENGTH(TRIM(REGEXP_REPLACE(IE_Dest, '[^0-9]+', '', 'g'))) = 0 THEN NULL ELSE CAST(REGEXP_REPLACE(IE_Dest, '[^0-9]+', '', 'g') AS BIGINT) END,
	DRT_Dest,
	UF_Dest,
	Tipo_Doc_Fiscal,
	Natureza_Operacao,
	0.0, -- sumiu do arquivo CASE WHEN LENGTH(Peso_Liquido) = 0 THEN 0.0 ELSE REPLACE(REPLACE(Peso_Liquido, '.', ''), ',', '.') :: NUMERIC(10,2) END,
	0.0, -- sumiu do arquivo CASE WHEN LENGTH(Peso_Bruto) = 0 THEN 0.0 ELSE REPLACE(REPLACE(Peso_Bruto, '.', ''), ',', '.') :: NUMERIC(10,2) END,
	Info_Interesse_Fisco,
	Info_Complementares_Interesse_Contribuinte,
	CASE WHEN length(indicador_modalidade_frete) = 0 THEN 0 ELSE Indicador_Modalidade_Frete::INTEGER END,
	CAST(Situacao_Documento AS INTEGER),
	CAST(NULL AS DATE), -- sumiu do arquivo  CAST(Dt_Cancelamento AS DATE),
	0.0, --sumiu Mercadoria_Valor do arquivo   REPLACE(REPLACE(Mercadoria_Valor, '.', ''), ',', '.') :: NUMERIC(10,2),
	Razao_Social_Transp,
	CASE WHEN length(REGEXP_REPLACE(CNPJ_Transp, '[^0-9]+', '', 'g')) = 0 THEN NULL ELSE REGEXP_REPLACE(CNPJ_Transp, '[^0-9]+', '', 'g') END,
	CASE WHEN LENGTH(REGEXP_REPLACE(IE_Transp, '[^0-9]+', '', 'g')) = 0 THEN NULL ELSE REGEXP_REPLACE(IE_Transp, '[^0-9]+', '', 'g') :: BIGINT END,
	CASE WHEN length(Placa_Veiculo_Transp) = 0 THEN NULL ELSE placa_veiculo_transp END,
	CASE WHEN length(UF_Veiculo_Transp) = 0 THEN NULL ELSE uf_veiculo_transp END,
	REPLACE(REPLACE(Total_BC_ICMS, '.', ''), ',', '.') :: NUMERIC(10,2),
	REPLACE(REPLACE(Total_ICMS, '.', ''), ',', '.') :: NUMERIC(10,2),
	REPLACE(REPLACE(Total_BC_ICMSST, '.', ''), ',', '.') :: NUMERIC(10,2),
	REPLACE(REPLACE(Total_ICMSST, '.', ''), ',', '.') :: NUMERIC(10,2),
	REPLACE(REPLACE(Total_NFe, '.', ''), ',', '.') :: NUMERIC(12,2),
	REPLACE(REPLACE(Valor_Total_Frete, '.', ''), ',', '.') :: NUMERIC(10,2),
	REPLACE(REPLACE(Valor_Total_Seguro, '.', ''), ',', '.') :: NUMERIC(10,2),
	REPLACE(REPLACE(Total_Produtos, '.', ''), ',', '.') :: NUMERIC(10,2),
	CASE WHEN LENGTH(REGEXP_REPLACE(Total_ICMS_Inter_UF_Dest, '[^0-9]+', '', 'g')) = 0 THEN NULL ELSE REPLACE(REPLACE(Total_ICMS_Inter_UF_Dest, '.', ''), ',', '.') :: NUMERIC(10,2) END,
	CASE WHEN LENGTH(REGEXP_REPLACE(Total_ICMS_Inter_UF_Emit, '[^0-9]+', '', 'g')) = 0 THEN NULL ELSE REPLACE(REPLACE(Total_ICMS_Inter_UF_Emit, '.', ''), ',', '.') :: NUMERIC(10,2) END
FROM NFE_dest_temp
WHERE Chave NOT IN (SELECT chave FROM NFE);

/** Insere NFe_Destinatario de outras UFs */
INSERT INTO NFE 
SELECT DISTINCT
	Chave,
	CAST(Numero AS INTEGER),
	CAST(Serie AS INTEGER),
	CAST(Modelo AS INTEGER),
	CAST(Emissao AS DATE),
	Razao_Social_Emit,
	REGEXP_REPLACE(CNPJ_Emit, '[^0-9]+', '', 'g'),
	CASE WHEN LENGTH(REGEXP_REPLACE(IE_Emit, '[^0-9]+', '', 'g')) = 0 THEN NULL ELSE REGEXP_REPLACE(IE_Emit, '[^0-9]+', '', 'g') :: BIGINT END,
	CRT,
	DRT_Emit,
	UF_Emit,
	Razao_Social_Dest,
	REGEXP_REPLACE(CNPJ_Dest, '[^0-9]+', '', 'g'),
	CASE WHEN LENGTH(TRIM(REGEXP_REPLACE(IE_Dest, '[^0-9]+', '', 'g'))) = 0 THEN NULL ELSE CAST(REGEXP_REPLACE(IE_Dest, '[^0-9]+', '', 'g') AS BIGINT) END,
	DRT_Dest,
	UF_Dest,
	Tipo_Doc_Fiscal,
	Natureza_Operacao,
	0.0, -- sumiu do arquivo CASE WHEN LENGTH(Peso_Liquido) = 0 THEN 0.0 ELSE REPLACE(REPLACE(Peso_Liquido, '.', ''), ',', '.') :: NUMERIC(10,2) END,
	0.0, -- sumiu do arquivo CASE WHEN LENGTH(Peso_Bruto) = 0 THEN 0.0 ELSE REPLACE(REPLACE(Peso_Bruto, '.', ''), ',', '.') :: NUMERIC(10,2) END,
	Info_Interesse_Fisco,
	Info_Complementares_Interesse_Contribuinte,
	CASE WHEN length(indicador_modalidade_frete) = 0 THEN 0 ELSE Indicador_Modalidade_Frete::INTEGER END,
	CAST(Situacao_Documento AS INTEGER),
	CAST(NULL AS DATE), -- sumiu do arquivo  CAST(Dt_Cancelamento AS DATE),
	0.0, --sumiu Mercadoria_Valor do arquivo   REPLACE(REPLACE(Mercadoria_Valor, '.', ''), ',', '.') :: NUMERIC(10,2),
	Razao_Social_Transp,
	CASE WHEN length(REGEXP_REPLACE(CNPJ_Transp, '[^0-9]+', '', 'g')) = 0 THEN NULL ELSE REGEXP_REPLACE(CNPJ_Transp, '[^0-9]+', '', 'g') END,
	CASE WHEN LENGTH(REGEXP_REPLACE(IE_Transp, '[^0-9]+', '', 'g')) = 0 THEN NULL ELSE REGEXP_REPLACE(IE_Transp, '[^0-9]+', '', 'g') :: BIGINT END,
	CASE WHEN length(Placa_Veiculo_Transp) = 0 THEN NULL ELSE placa_veiculo_transp END,
	CASE WHEN length(UF_Veiculo_Transp) = 0 THEN NULL ELSE uf_veiculo_transp END,
	REPLACE(REPLACE(Total_BC_ICMS, '.', ''), ',', '.') :: NUMERIC(10,2),
	REPLACE(REPLACE(Total_ICMS, '.', ''), ',', '.') :: NUMERIC(10,2),
	REPLACE(REPLACE(Total_BC_ICMSST, '.', ''), ',', '.') :: NUMERIC(10,2),
	REPLACE(REPLACE(Total_ICMSST, '.', ''), ',', '.') :: NUMERIC(10,2),
	REPLACE(REPLACE(Total_NFe, '.', ''), ',', '.') :: NUMERIC(12,2),
	REPLACE(REPLACE(Valor_Total_Frete, '.', ''), ',', '.') :: NUMERIC(10,2),
	REPLACE(REPLACE(Valor_Total_Seguro, '.', ''), ',', '.') :: NUMERIC(10,2),
	REPLACE(REPLACE(Total_Produtos, '.', ''), ',', '.') :: NUMERIC(10,2),
	CASE WHEN LENGTH(REGEXP_REPLACE(Total_ICMS_Inter_UF_Dest, '[^0-9]+', '', 'g')) = 0 THEN NULL ELSE REPLACE(REPLACE(Total_ICMS_Inter_UF_Dest, '.', ''), ',', '.') :: NUMERIC(10,2) END,
	CASE WHEN LENGTH(REGEXP_REPLACE(Total_ICMS_Inter_UF_Emit, '[^0-9]+', '', 'g')) = 0 THEN NULL ELSE REPLACE(REPLACE(Total_ICMS_Inter_UF_Emit, '.', ''), ',', '.') :: NUMERIC(10,2) END
FROM NFE_dest_outras_ufs_temp
WHERE Chave NOT IN (SELECT chave FROM NFE);
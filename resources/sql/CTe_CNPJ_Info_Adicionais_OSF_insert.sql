INSERT INTO cte_nfe 
SELECT c.chave, c.nf_chave FROM CTE_ADICIONAL_TEMP c JOIN nfe ON c.nf_chave = nfe.chave
UNION
SELECT c.chave, c.nf2_chave FROM CTE_ADICIONAL_TEMP c JOIN nfe ON c.nf2_chave = nfe.chave
ON CONFLICT DO NOTHING;

UPDATE cte SET 
	Veiculo_Placa = CASE WHEN length(trim(REGEXP_REPLACE(temp.placa, '[A-Za-z0-9]+', '', 'g'))) = 0 THEN NULL ELSE REGEXP_REPLACE(temp.placa, '[A-Za-z0-9]+', '', 'g') END,
	Veiculo_Renavam = CASE WHEN length(trim(temp.renavam)) = 0 THEN NULL ELSE trim(temp.renavam)::NUMERIC(15,0) END,
  	Veiculo_UF = CASE WHEN length(trim(temp.uf_veiculo)) = 0 THEN NULL ELSE trim(temp.uf_veiculo) END,
	Veiculo_CPF_Proprietario = CASE WHEN length(trim(temp.cpf_proprietario)) = 0 THEN NULL ELSE trim(temp.cpf_proprietario) END,
  	Veiculo_CNPJ_Proprietario = CASE WHEN length(trim(temp.cnpj_proprietario)) = 0 THEN NULL ELSE trim(temp.cnpj_proprietario) END,
 	Valor_Carga = CASE WHEN LENGTH(TRIM(REGEXP_REPLACE(temp.valor_carga, '[^0-9]+', '', 'g'))) = 0 THEN 0.0 ELSE REPLACE(REPLACE(temp.valor_carga, '.', ''), ',', '.') :: NUMERIC(10,2) END,
 	Informacoes_Adicionais = CASE WHEN LENGTH(temp.Obs_Gerais || temp.info_adicional_desc) = 0 THEN NULL ELSE temp.Obs_Gerais || temp.info_adicional_desc END,
 	Informacoes_Fisco = CASE WHEN LENGTH(temp.info_interesse_fisco || temp.info_adicional_desc) = 0 THEN NULL ELSE temp.info_interesse_fisco || temp.info_adicional_desc END,
	Produto_Predominante = temp.Desc_Produto_Predominante,
	Situacao_Documento = temp.situacao::int
FROM cte_adicional_temp AS temp
WHERE temp.chave = cte.chave;
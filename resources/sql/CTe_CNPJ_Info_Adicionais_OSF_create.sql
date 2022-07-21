CREATE TABLE IF NOT EXISTS CTE_NFE (
	cte_chave						VARCHAR(44) NOT NULL REFERENCES cte(chave),
	nfe_chave						VARCHAR(44) NOT NULL REFERENCES nfe(chave),
	PRIMARY KEY (cte_chave, nfe_chave)
);

CREATE TEMP TABLE CTE_ADICIONAL_TEMP (
   Chave                                             VARCHAR
  ,Serie                                             VARCHAR
  ,Numero                                            VARCHAR
  ,CNPJ_Emit                                         VARCHAR
  ,Emissao											 VARCHAR
  ,Razao_Social_Emit                                 VARCHAR
  ,UF_Emit                                           VARCHAR
  ,CNPJ_Tom                                          VARCHAR
  ,Razao_Social_Tom                                  VARCHAR
  ,UF_Tom                                            VARCHAR
  ,CNPJ_Remet                                        VARCHAR
  ,Razao_Social_Remet                                VARCHAR
  ,UF_Remet                                          VARCHAR
  ,CNPJ_Dest                                         VARCHAR
  ,Razao_Social_Dest                                 VARCHAR
  ,UF_Dest                                           VARCHAR
  ,CNPJ_Exped                                        VARCHAR
  ,UF_Exped                                          VARCHAR
  ,CNPJ_Receb                                        VARCHAR
  ,UF_Receb                                          VARCHAR
  ,Tipo_Doc_Fiscal                                   VARCHAR
  ,Obs_Gerais						 VARCHAR
  ,info_interesse_fisco					VARCHAR
  ,Desc_Produto_Predominante				 VARCHAR
  ,valor_carga						 VARCHAR 
  ,NF_numero						 VARCHAR
  ,NF_serie						 VARCHAR
  ,NF_emissao						 VARCHAR
  ,valor_produto_nf					 VARCHAR 
  ,NF_chave						 VARCHAR
  ,Placa						 VARCHAR
  ,Renavam						 VARCHAR
  ,UF_Veiculo						 VARCHAR
  ,CPF_Proprietario					 VARCHAR
  ,CNPJ_Proprietario					 VARCHAR
  ,NF2_chave						 VARCHAR
  ,NF2_emissao						 VARCHAR
  ,NF2_numero						 VARCHAR
  ,NF2_serie						 VARCHAR 
  ,valor_produtos					 VARCHAR
  ,situacao						VARCHAR
  ,info_adicional_id					VARCHAR
  ,info_adicional_desc					VARCHAR
  ,info_fisco_id					VARCHAR
  ,info_fisco_desc					VARCHAR
);
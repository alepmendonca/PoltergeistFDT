/**
 * 
 * NFE ITEM 
 * 
 **/
CREATE TABLE IF NOT EXISTS NFE_ITEM (
   Chave                                               VARCHAR(44) NOT NULL REFERENCES NFE(Chave) ON DELETE CASCADE
  ,CNPJ_Emit                                           CHAR(14) NOT NULL
  ,Item                                                INTEGER  NOT NULL
  ,Desc_Produto                                        VARCHAR(120) NOT NULL
  ,Cod_Produto                                         VARCHAR(60) NOT NULL
  ,GTIN                                                BIGINT 
  ,NCM                                                 INTEGER  NOT NULL
  ,CEST												   CHAR(9)
  ,CFOP                                                INTEGER  NOT NULL REFERENCES CFOP(Codigo)
  ,CST                                                 INTEGER 
  ,CSOSN                                               INTEGER 
  ,Quantidade                                          NUMERIC(10,2) NOT NULL
  ,Unidade                                             VARCHAR(20) NOT NULL
  ,Valor_Produto                                       NUMERIC(12,2) NOT NULL
  ,Valor_Desconto                                      NUMERIC(10,2)
  ,Valor_Outro                                         NUMERIC(10,2)
  ,ICMS_BC                                             NUMERIC(10,2)
  ,ICMS_Aliquota                                       NUMERIC(10,2) 
  ,ICMS_BC_Percentual_Red                              NUMERIC(10,2)
  ,ICMS                                                NUMERIC(10,2)
  ,ICMSST_BC                                           NUMERIC(10,2)
  ,ICMSST_Aliquota                                     NUMERIC(10,2)
  ,ICMSST_BC_Percentual_Red                            NUMERIC(10,2)
  ,ICMSST                                              NUMERIC(10,2)
  ,ICMSST_BC_Retido_Op_Anterior                        NUMERIC(10,2)
  ,ICMSST_Retido_Op_Anterior                           NUMERIC(10,2)
  ,IPI                                                 NUMERIC(10,2)
  ,PIS                                                 NUMERIC(10,2)
  ,COFINS                                              NUMERIC(10,2)
  ,DI                                                  VARCHAR
  ,FCI                                                 VARCHAR(50)
  ,Indicador_Modalidade_Frete                          INTEGER
  ,Valor_Frete                                         NUMERIC(10,2)
  ,Valor_Seguro                                        NUMERIC(10,2)
  ,Data_Desembaraco                                    DATE
  ,UF_Desembaraco                                      CHAR(2)
  ,Descricao_Texto                                     VARCHAR
  ,CPF_Dest                                            CHAR(11)
  ,CNAE                                                INTEGER REFERENCES CNAE(CODIGO)
  ,Codigo_Tributacao                                   INTEGER
  ,Origem_Mercadoria								   INTEGER
  ,Percent_Aliq_Cred_SN								   NUMERIC(10,2)
  ,Valor_Cred_SN								 	   NUMERIC(10,2)
  ,PRIMARY KEY (Chave, Item)
);
CREATE INDEX IF NOT EXISTS nfe_item_cfop ON NFE_ITEM (CNPJ_Emit, CFOP);

CREATE TEMP TABLE IF NOT EXISTS NFE_ITEM_DEST_TEMP (
   Chave                                               VARCHAR
  ,Data_Emissao                                        VARCHAR
  ,CNPJ_Emit                                           VARCHAR
  ,Razao_Social_Emit                                   VARCHAR
  ,IE_Emit                                             VARCHAR
  ,UF_Emit                                             VARCHAR
  ,CNPJ_Dest                                           VARCHAR
  ,UF_Dest                                             VARCHAR
  ,Razao_Social_Dest                                   VARCHAR
  ,IE_Dest                                             VARCHAR
  ,Numero                                              VARCHAR
  ,Modelo                                              VARCHAR
  ,Serie                                               VARCHAR
  ,DRT_Emit                                            VARCHAR
  ,DRT_Dest                                            VARCHAR
  ,Situacao                                            VARCHAR
  ,Item                                                VARCHAR
  ,Cod_Produto                                         VARCHAR
  ,Desc_Produto                                        VARCHAR
  ,GTIN                                                VARCHAR 
  ,NCM                                                 VARCHAR
  ,Unidade                                             VARCHAR
  ,Quantidade                                          VARCHAR
  ,Valor_Produto                                       VARCHAR
  ,Valor_Desconto                                      VARCHAR
  ,Valor_Outro                                         VARCHAR
  ,ICMS_BC                                             VARCHAR
  ,ICMS                                                VARCHAR
  ,IPI                                                 VARCHAR
  ,ICMSST_BC_Retido_Op_Anterior                        VARCHAR
  ,ICMSST_Retido_Op_Anterior                           VARCHAR
  ,ICMSST_BC                                           VARCHAR
  ,ICMSST                                              VARCHAR
  ,PIS                                                 VARCHAR
  ,COFINS                                              VARCHAR
  ,Valor_Frete                                         VARCHAR
  ,Valor_Seguro                                        VARCHAR
  ,CPF_Dest                                            VARCHAR
  ,CNAE                                                VARCHAR
  ,CFOP                                                VARCHAR
  ,Origem_Mercadoria                                   VARCHAR
  ,Codigo_Tributacao                                   VARCHAR
  ,ICMS_BC_Percentual_Red                              VARCHAR
  ,ICMS_Aliquota                                       VARCHAR
  ,ICMSST_Aliquota                                     VARCHAR
  ,ICMSST_BC_Percentual_Red                            VARCHAR
  ,Indicador_Modalidade_Frete                          VARCHAR
  ,Descricao_Texto                                     VARCHAR
  ,DI                                                  VARCHAR
  ,UF_Desembaraco                                      VARCHAR
  ,Data_Desembaraco                                    VARCHAR
  ,FCI                                                 VARCHAR
  ,Tipo_Doc_Fiscal                                     VARCHAR
  ,CSOSN                                               VARCHAR 
  ,CPF_Emit											   VARCHAR
  ,Percent_Aliq_Cred_SN								   VARCHAR
  ,Valor_Cred_SN								 	   VARCHAR
  ,FCP_ICMS_BC										   VARCHAR
  ,FCP_ICMS_Aliquota								   VARCHAR
  ,FCP_ICMS											   VARCHAR
  ,FCP_ICMS_ST_BC									   VARCHAR
  ,FCP_ICMS_ST_Aliquota								   VARCHAR
  ,FCP_ICMS_ST										   VARCHAR
  ,CEST												   VARCHAR
);

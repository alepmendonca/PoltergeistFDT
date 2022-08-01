CREATE TABLE IF NOT EXISTS CTE (
   Chave                                             VARCHAR(44) NOT NULL PRIMARY KEY
  ,Numero                                            INTEGER  NOT NULL
  ,Serie                                             INTEGER  NOT NULL
  ,Emissao                                           DATE  NOT NULL
  ,Razao_Social_Emit                                 VARCHAR(100) NOT NULL
  ,CNPJ_Emit                                         CHAR(14) NOT NULL
  ,IE_Emit                                           BIGINT
  ,UF_Emit                                           CHAR(2)
  ,Razao_Social_Tom                                  VARCHAR(100) NOT NULL
  ,CNPJ_Tom                                          CHAR(14) 
  ,IE_Tom                                            BIGINT 
  ,UF_Tom                                            VARCHAR(2)
  ,Razao_Social_Remet                                VARCHAR(100) NOT NULL
  ,CNPJ_Remet                                        CHAR(14)
  ,UF_Remet                                          VARCHAR(2)
  ,Razao_Social_Dest                                 VARCHAR(100) NOT NULL
  ,CNPJ_Dest                                         CHAR(14)
  ,UF_Dest                                           VARCHAR(2)
  ,CNPJ_Exped                                        CHAR(14)
  ,UF_Exped                                          VARCHAR(2)
  ,CNPJ_Receb                                        CHAR(14)
  ,UF_Receb                                          VARCHAR(2)
  ,Tipo_Doc_Fiscal                                   VARCHAR(50) NOT NULL
  ,Natureza_Operacao                                 VARCHAR(60) NOT NULL
  ,Descr_Modal                                       VARCHAR(100)
  ,Descr_Servico                                     VARCHAR(100)
  ,Municipio_Ini                                     VARCHAR(100)
  ,UF_Ini                                            VARCHAR(2) NOT NULL
  ,Municipio_Fim                                     VARCHAR(100)
  ,UF_Fim                                            VARCHAR(2) NOT NULL
  ,CFOP                                              INTEGER REFERENCES CFOP(CODIGO)
  ,Descr_CST                                         VARCHAR(100)
  ,Total_CTe                                         NUMERIC(10,2)
  ,Total_Creditos                                    NUMERIC(10,2)
  ,ICMS_BC                                           NUMERIC(10,2)
  ,ICMS_Aliquota                                     NUMERIC(10,2) 
  ,ICMS_BC_Percentual_Red                            NUMERIC(10,2)
  ,ICMS                                              NUMERIC(10,2)
  ,ICMSST_BC_Retido_Op_Anterior                      NUMERIC(10,2)
  ,ICMSST_Retido_Op_Anterior                         NUMERIC(10,2)
  ,ICMS_Outras_UFs                                   NUMERIC(10,2)
  ,Indicador_Tom_Serv                                VARCHAR(50)
  ,Indicador_SN                                      VARCHAR(50)
  ,Veiculo_Placa									 VARCHAR(15)
  ,Veiculo_Renavam									 NUMERIC(15,0)
  ,Veiculo_UF										 CHAR(2)
  ,Veiculo_CPF_Proprietario							 CHAR(11)
  ,Veiculo_CNPJ_Proprietario						 CHAR(14)
  ,Valor_Carga										 NUMERIC(10,2)
  ,Situacao_Documento								 INTEGER NOT NULL
  ,Informacoes_Adicionais							 VARCHAR
  ,Informacoes_Fisco								 VARCHAR
  ,Produto_Predominante								 VARCHAR
);

CREATE INDEX IF NOT EXISTS cte_cnpj_emit ON CTE USING HASH(CNPJ_Emit);
CREATE INDEX IF NOT EXISTS cte_cnpj_dest ON CTE USING HASH(CNPJ_Dest);
CREATE INDEX IF NOT EXISTS cte_cnpj_tom  ON CTE USING HASH(CNPJ_Tom);
CREATE INDEX IF NOT EXISTS cte_cnpj_remet ON CTE USING HASH(CNPJ_Remet);
CREATE INDEX IF NOT EXISTS cte_emissao ON CTE USING BTREE(Emissao);
CREATE INDEX IF NOT EXISTS cte_numero_idx ON cte (numero,serie);
ALTER TABLE cte ADD CONSTRAINT cte_check CHECK (RAZAO_SOCIAL_DEST IS NOT NULL OR CNPJ_DEST IS NOT NULL OR CNPJ_EXPED IS NOT NULL OR CNPJ_RECEB IS NOT NULL);

/** 
 * CTe_CNPJ_Emitente_Tomador_Remetente_Destinatario_OSF
 */
CREATE TEMP TABLE CTE_TEMP (
   Chave                                             VARCHAR
  ,Serie                                             VARCHAR
  ,Numero                                            VARCHAR
  ,CNPJ_Emit                                         VARCHAR
  ,IE_Emit                                           VARCHAR
  ,Emissao                                           VARCHAR
  ,Razao_Social_Emit                                 VARCHAR
  ,UF_Emit                                           VARCHAR
  ,CNPJ_Tom                                          VARCHAR
  ,IE_Tom                                            VARCHAR
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
  ,Total_CTe                                         VARCHAR
  ,ICMS                                              VARCHAR
  ,ICMS_BC                                           VARCHAR
  ,CFOP                                              VARCHAR
  ,Municipio_Ini                                     VARCHAR
  ,UF_Ini                                            VARCHAR
  ,Municipio_Fim                                     VARCHAR
  ,UF_Fim                                            VARCHAR
  ,Natureza_Operacao                                 VARCHAR
  ,Descr_Modal                                       VARCHAR
  ,Descr_Servico                                     VARCHAR
  ,Descr_CST                                         VARCHAR
  ,ICMS_Aliquota                                     VARCHAR
  ,ICMS_BC_Percentual_Red                            VARCHAR
  ,ICMSST_BC_Retido_Op_Anterior                      VARCHAR
  ,ICMSST_Retido_Op_Anterior                         VARCHAR 
  ,ICMS_Outras_UFs                                   VARCHAR
  ,Total_Creditos                                    VARCHAR  
  ,Indicador_Tom_Serv                                VARCHAR
  ,Indicador_SN                                      VARCHAR
  ,Qtd_Eventos_CCE                                   VARCHAR
  ,Qtd_Eventos_Prest_Serv_Desacordo                  VARCHAR
  ,Situacao_Documento				     VARCHAR
);
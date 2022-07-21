CREATE TABLE IF NOT EXISTS NFE (
   Chave                                             VARCHAR(44) NOT NULL PRIMARY KEY
  ,Numero                                            INTEGER  NOT NULL
  ,Serie                                             INTEGER  NOT NULL
  ,Modelo                                            INTEGER  NOT NULL
  ,Emissao                                           DATE  NOT NULL
  ,Razao_Social_Emit                                 VARCHAR(100) NOT NULL
  ,CNPJ_Emit                                         CHAR(14) NOT null
  ,IE_Emit                                           BIGINT
  ,CRT                                               VARCHAR(5)
  ,DRT_Emit                                          VARCHAR(15)
  ,UF_Emit                                           CHAR(2)
  ,Razao_Social_Dest                                 VARCHAR(100) NOT NULL
  ,CNPJ_Dest                                         CHAR(14)
  ,IE_Dest                                           BIGINT 
  ,DRT_Dest                                          VARCHAR(15)
  ,UF_Dest                                           VARCHAR(2)
  ,Tipo_Doc_Fiscal                                   VARCHAR(10) NOT NULL
  ,Natureza_Operacao                                 VARCHAR(60) NOT NULL
  ,Peso_Liquido                                      NUMERIC(10,2)
  ,Peso_Bruto                                        NUMERIC(10,2)
  ,Info_Interesse_Fisco                              VARCHAR
  ,Info_Complementares_Interesse_Contribuinte        VARCHAR
  ,Indicador_Modalidade_Frete                        INTEGER  NOT NULL
  ,Situacao_Documento                                INT  NOT NULL
  ,Dt_Cancelamento                                   DATE 
  ,Mercadoria_Valor                                  NUMERIC(10,2) NOT NULL
  ,Razao_Social_Transp                               VARCHAR(100)
  ,CNPJ_Transp                                       CHAR(14)
  ,IE_Transp                                         BIGINT
  ,Placa_Veiculo_Transp                              CHAR(8)
  ,UF_Veiculo_Transp                                 CHAR(2)
  ,Total_BC_ICMS                                    NUMERIC(10,2) NOT NULL
  ,Total_ICMS                                       NUMERIC(10,2) NOT NULL
  ,Total_BC_ICMSST                                  NUMERIC(10,2) NOT NULL
  ,Total_ICMSST                                     NUMERIC(10,2) NOT NULL
  ,Total_NFe                                        NUMERIC(12,2) NOT NULL
  ,Valor_Total_Frete                                NUMERIC(10,2) NOT NULL
  ,Valor_Total_Seguro                               NUMERIC(10,2) NOT NULL
  ,Total_Produtos                                   NUMERIC(12,2)
  ,Total_ICMS_Inter_UF_Dest							NUMERIC(10,2)
  ,Total_ICMS_Inter_UF_Emit							NUMERIC(10,2)
  ,CNAE_Dest										INTEGER REFERENCES CNAE(CODIGO)
);

CREATE INDEX IF NOT EXISTS nfe_cnpj_emit ON NFE USING HASH(CNPJ_Emit);
CREATE INDEX IF NOT EXISTS nfe_cnpj_dest ON NFE USING HASH(CNPJ_Dest);
CREATE INDEX IF NOT EXISTS nfe_emissao ON NFE USING BTREE(Emissao);
CREATE INDEX IF NOT EXISTS nfe_numero_idx ON nfe (numero,serie);
CREATE INDEX IF NOT EXISTS nfe_valor_idx ON nfe (total_nfe);

/**
 * Primeira parte da listagem do arquivo, NFe de SP
 */
CREATE TEMP TABLE IF NOT EXISTS NFE_DEST_TEMP (
   Chave                                             VARCHAR UNIQUE
  ,Emissao                                           VARCHAR
  ,CNPJ_Emit                                         VARCHAR
  ,Razao_Social_Emit                                 VARCHAR
  ,IE_Emit                                           VARCHAR
  ,CNPJ_Dest                                         VARCHAR
  ,UF_Dest                                           VARCHAR
  ,Razao_Social_Dest                                 VARCHAR
  ,IE_Dest                                           VARCHAR 
  ,Tipo_Doc_Fiscal                                   VARCHAR
  ,Numero                                            VARCHAR
  ,Modelo                                            VARCHAR
  ,Serie                                             VARCHAR
  ,DRT_Emit                                          VARCHAR
  ,CNPJ_Transp                                       VARCHAR
  ,DRT_Dest                                          VARCHAR
  ,Razao_Social_Transp                               VARCHAR
  ,IE_Transp                                         VARCHAR
  ,Placa_Veiculo_Transp                              VARCHAR
  ,UF_Veiculo_Transp                                 VARCHAR
  ,Total_NFe                                         VARCHAR
  ,Info_Interesse_Fisco                              VARCHAR
  ,Info_Complementares_Interesse_Contribuinte        VARCHAR
  ,Valor_Total_Frete                                 VARCHAR
  ,Valor_Total_Seguro                                VARCHAR
  ,Indicador_Modalidade_Frete                        VARCHAR
  ,Natureza_Operacao                                 VARCHAR
  ,Total_ICMS                                        VARCHAR
  ,Total_BC_ICMS                                     VARCHAR
  ,Total_BC_ICMSST                                   VARCHAR
  ,Total_ICMSST                                      VARCHAR
  ,Total_Produtos                                    VARCHAR
  ,Situacao_Documento                                VARCHAR
  ,CRT                                               VARCHAR
  ,UF_Emit                                           VARCHAR
  ,CPF_Emit                                          VARCHAR
  ,Total_ICMS_Inter_UF_Dest                          VARCHAR
  ,Total_ICMS_Inter_UF_Emit                          VARCHAR
);

/**
 * Aparentemente inventaram mais uma seção no relatorio NFe_Destinatario_OSF, onde estao NFe de outras UFs, bem diferente das de SP
 */
CREATE TEMP TABLE IF NOT EXISTS NFE_DEST_OUTRAS_UFS_TEMP (
   Chave                                             VARCHAR UNIQUE
  ,CNPJ_Dest                                         VARCHAR
  ,DRT_Emit                                          VARCHAR
  ,UF_Emit                                           VARCHAR
  ,UF_Dest                                           VARCHAR
  ,Modelo                                            VARCHAR
  ,Serie                                             VARCHAR
  ,Emissao                                           VARCHAR
  ,Natureza_Operacao                                 VARCHAR
  ,Tipo_Doc_Fiscal                                   VARCHAR
  ,Indicador_Modalidade_Frete                        VARCHAR
  ,Situacao_Documento                                VARCHAR
  ,Info_Complementares_Interesse_Contribuinte        VARCHAR
  ,Info_Interesse_Fisco                              VARCHAR
  ,Razao_Social_Dest                                 VARCHAR
  ,Razao_Social_Emit                                 VARCHAR
  ,IE_Emit                                           VARCHAR
  ,IE_Dest                                           VARCHAR 
  ,IE_Transp                                         VARCHAR
  ,UF_Veiculo_Transp                                 VARCHAR
  ,CNPJ_Emit                                         VARCHAR
  ,CNPJ_Transp                                       VARCHAR
  ,Numero                                            VARCHAR
  ,Placa_Veiculo_Transp                              VARCHAR
  ,Total_BC_ICMS                                     VARCHAR
  ,Total_BC_ICMSST                                   VARCHAR
  ,Total_ICMS                                        VARCHAR
  ,Total_ICMSST                                      VARCHAR
  ,Total_Produtos                                    VARCHAR
  ,Valor_Total_Frete                                 VARCHAR
  ,Total_NFe                                         VARCHAR
  ,Valor_Total_Seguro                                VARCHAR
  ,DRT_Dest                                          VARCHAR
  ,Razao_Social_Transp                               VARCHAR
  ,CRT                                               VARCHAR
  ,CPF_Emit                                          VARCHAR
  ,Total_ICMS_Inter_UF_Dest                          VARCHAR
  ,Total_ICMS_Inter_UF_Emit                          VARCHAR
);
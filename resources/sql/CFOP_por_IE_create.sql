CREATE TABLE IF NOT EXISTS GIA_CFOP (
  IE                                BIGINT NOT NULL
  ,Apuracao                         DATE NOT NULL
  ,CFOP                             INTEGER NOT NULL REFERENCES CFOP(CODIGO)
  ,Valor_Contabil                   NUMERIC(12,2)
  ,ICMS_BC                          NUMERIC(12,2)
  ,ICMS                             NUMERIC(12,2)
  ,Valor_Isento                     NUMERIC(12,2)
  ,Valor_Outros                     NUMERIC(12,2)
  ,ICMS_ST                          NUMERIC(12,2)
);
CREATE UNIQUE INDEX IF NOT EXISTS gia_cfop_apuracao ON GIA_CFOP USING BTREE(IE, Apuracao, CFOP);

CREATE TEMP TABLE GIA_CFOP_TEMP (
   IE                                                VARCHAR
  ,NOME						 VARCHAR
  ,APURACAO                                          VARCHAR
  ,ID_CFOP					VARCHAR
  ,CFOP6                                             VARCHAR
  ,VALOR_CONTABIL                                    VARCHAR
  ,VALOR_BC_ICMS                                     VARCHAR
  ,VALOR_ICMS                                        VARCHAR
  ,VALOR_ISENTO                                      VARCHAR
  ,VALOR_OUTROS                                      VARCHAR
  ,VALOR_ICMS_ST                                     VARCHAR
  ,VALOR_OUTROS_ICMS_ST				 VARCHAR
);
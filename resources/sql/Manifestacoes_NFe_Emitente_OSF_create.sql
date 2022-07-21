/** NFE MDF 
 */
CREATE TABLE IF NOT EXISTS NFE_MDF (
    Chave                                              VARCHAR(44) NOT NULL REFERENCES NFE(Chave) ON DELETE CASCADE
   ,Desc_Evento                                        VARCHAR(100) NOT NULL
   ,Desc_Justificativa								   VARCHAR(100)
   ,Origem											   INT
   ,Autor											   CHAR(14)
   ,PRIMARY KEY (Chave, Desc_Evento)
);

/**
 * Tabela conforme consulta Manifestações_NFe_Emitente_OSF 
 */
CREATE TEMP TABLE IF NOT EXISTS NFE_MDF_TEMP (
    CHAVE VARCHAR,
    CNPJ_EMITENTE VARCHAR,
    SERIE VARCHAR,
    NUMERO VARCHAR,
    DT_EMISSAO VARCHAR,
    VALOR_NF VARCHAR,
    ICMS_NF VARCHAR,
    TIPO_NF VARCHAR,
    CNPJ_DESTINATARIO VARCHAR,
    RAZAO_SOCIAL_DESTINATARIO VARCHAR,
    DESC_EVENTO VARCHAR,
    DESC_JUSTIFICATIVA VARCHAR,
    IND_ORIGEM VARCHAR,
    IND_AUTOR VARCHAR
);
/**
 * Função pra dizer último dia de um mês
 */
CREATE OR REPLACE FUNCTION end_of_month(date)
returns date as
$$
select (date_trunc('month', $1) + interval '1 month' - interval '1 day')::date;
$$ language 'sql'
immutable strict;

CREATE OR REPLACE FUNCTION cnpj_base(_cnpj float)
RETURNS float AS
$$
SELECT substring(_cnpj::TEXT, 1, length(_cnpj::TEXT)-6)::FLOAT;
$$ LANGUAGE 'sql'
immutable strict;

/**
 * Função para checar se um CPF é válido
 */
CREATE OR REPLACE FUNCTION is_cpf(text)
	RETURNS BOOLEAN AS $$
SELECT CASE WHEN length(translate($1, './- ', '')) <= 11 THEN
(
-- verifica se os dígitos coincidem com os especificados
  SELECT
      substr(lpad(translate($1, './- ', ''), 11, '0'), 10, 1) = CAST(digit1 AS text) AND
      substr(lpad(translate($1, './- ', ''), 11, '0'), 11, 1) = CAST(digit2 AS text)
  FROM
  (
    -- calcula o segundo dígito verificador (digit2)
    SELECT
        -- se o resultado do módulo for 0 ou 1 temos 0
        -- senão temos a subtração de 11 pelo resultado do módulo
        CASE res2
        WHEN 0 THEN 0
        WHEN 1 THEN 0
        ELSE 11 - res2
        END AS digit2,
        digit1
    FROM
    (
      -- soma da multiplicação dos primeiros 9 dígitos por 11, 10, ..., 4, 3
      -- obtemos o módulo da soma por 11
      SELECT
          MOD(SUM(m * CAST(substr(lpad(translate($1, './- ', ''), 11, '0'), 12 - m, 1) AS integer)) + digit1 * 2, 11) AS res2,
          digit1
      FROM
      generate_series(11, 3, -1) AS m,
      (
        -- calcula o primeiro dígito verificador (digit1)
        SELECT
            -- se o resultado do módulo for 0 ou 1 temos 0
            -- senão temos a subtração de 11 pelo resultado do módulo
            CASE res1
            WHEN 0 THEN 0
            WHEN 1 THEN 0
            ELSE 11 - res1
            END AS digit1
        FROM
        (
          -- soma da multiplicação dos primeiros 9 dígitos por 10, 9, ..., 3, 2
          -- obtemos o módulo da soma por 11
          SELECT
              MOD(SUM(n * CAST(substr(lpad(translate($1, './- ', ''), 11, '0'), 11 - n, 1) AS integer)), 11) AS res1
          FROM generate_series(10, 2, -1) AS n
        ) AS sum1
      ) AS first_digit
      GROUP BY digit1
    ) AS sum2
  ) AS first_sec_digit
) ELSE FALSE END;
$$ LANGUAGE 'sql' IMMUTABLE STRICT;

/**
 * Função para checar se um CNPJ é válido
 */
CREATE OR REPLACE FUNCTION is_cnpj(text)
  RETURNS boolean AS
$BODY$
DECLARE
 v_string text := $1;
 v_caldv1 int4;
 v_caldv2 int4;
 v_dv1 int4;
 v_dv2 int4;
 v_array1 text[] ;
 v_array2 text[] ;
 v_tst_string int4;
BEGIN
 v_string := lpad(translate(v_string, './- ', ''), 14, '0');

  SELECT INTO v_array1 '{5,4,3,2,9,8,7,6,5,4,3,2}';
  SELECT INTO v_array2 '{6,5,4,3,2,9,8,7,6,5,4,3,2}';
  v_dv1 := (substring(v_string, 13, 1))::int4;
  v_dv2 := (substring(v_string, 14, 1))::int4;
  /* COLETA DIG VER 1 CNPJ */
  v_caldv1 := 0;
  FOR va IN 1..12 LOOP
   v_caldv1 := v_caldv1 + ((SELECT substring(v_string, va, 1))::int4 * (v_array1[va]::int4));
  END LOOP;
  v_caldv1 := v_caldv1 % 11;
   IF (v_caldv1 = 0) OR (v_caldv1 = 1) THEN
    v_caldv1 := 0;
   ELSE
    v_caldv1 := 11 - v_caldv1;
   END IF;
  /* COLETA DIG VER 2 CNPJ */
  v_caldv2 := 0;
  FOR va IN 1..13 LOOP
   v_caldv2 := v_caldv2 + ((SELECT substring(v_string || v_caldv1::text, va, 1))::int4 * (v_array2[va]::int4));
  END LOOP;
  v_caldv2 := v_caldv2 % 11;
   IF (v_caldv2 = 0) OR (v_caldv2 = 1) THEN
    v_caldv2 := 0;
   ELSE
    v_caldv2 := 11 - v_caldv2;
   END IF;
  /* TESTA */
  IF (v_caldv1 = v_dv1) AND (v_caldv2 = v_dv2) THEN
   RETURN TRUE;
  ELSE
   RETURN FALSE;
  END IF;
END;

$BODY$
  LANGUAGE 'plpgsql' IMMUTABLE
  COST 100;

CREATE OR REPLACE FUNCTION cnpj_cpf_formatted(double precision)
RETURNS VARCHAR AS $$
	SELECT CASE WHEN $1 IS NULL OR $1 = 0 THEN '' ELSE CASE WHEN is_cpf($1::TEXT) THEN TRIM(REPLACE(to_char($1, '000:000:000-00'),':','.')) ELSE TRIM(REPLACE(to_char($1, '00:000:000/0000-00'),':','.')) END END;
$$ language 'sql'
immutable strict;


/**
 * Função para dizer total de créditos de ICMS (verifica dados de Simples Nacional)
 */
CREATE OR REPLACE FUNCTION nfe_icms(_chave text)
	RETURNS NUMERIC
LANGUAGE PLPGSQL AS
$BODY$
DECLARE 
	v_info_contr text;
	v_regex		 text := '(?i)(?:r[S|$|$]\s*)?([\d\.\,]+\d{2})';
	v_dados		 RECORD;
BEGIN
	SELECT regime."Descr Regime Apuração" as regime, nfe."Valor Total ICMS" AS total_icms, 
		ni."Informações Complementares" AS info_complementares, ni."Informações Fisco" AS info_fisco,
		SUM(COALESCE(nfe_item."Valor ICMS", 0)) AS icms_item, csosn."Tributação" as tribut_sn
		INTO v_dados 
	FROM "NFE" AS nfe 
		JOIN "NFE-Detalhe" AS nfe_item 
			LEFT JOIN "Tabela CSOSN" csosn ON nfe_item."Código CSOSN" = csosn."Codigo CSOSN"
		ON nfe."Código Chave NFE" = nfe_item."Código Chave NFE"
		JOIN "NFE Chave" AS nc ON nfe."Código Chave NFE" = nc."Código Chave NFE"
		LEFT JOIN "NFE Informações" ni ON nfe."Código Chave NFE" = ni."Código Chave NFE"
		LEFT JOIN "CADESP-Fornec_Regime" AS cadesp_regime 
			LEFT JOIN "Tabela Regime Apuracao" AS regime ON cadesp_regime."Cod Regime Apuração - H" = regime."Cod Regime Apuração"
		ON (
			(nfe."Número CNPJ Emitente" = cadesp_regime."Num CNPJ" AND nfe."Número CNPJ Emitente" != cnpj_auditoria()) 
			OR (nfe."Número CNPJ Destinatário" = cadesp_regime."Num CNPJ" AND nfe."Número CNPJ Destinatário" != cnpj_auditoria())
		)
	WHERE nc."Chave NFE" = _chave
	AND nfe."Data Emissão" BETWEEN COALESCE(cadesp_regime."Data Início Validade Regime - H",'1-1-2000') AND COALESCE(cadesp_regime."Data Fim Validade Regime - H", now())
	GROUP BY 1, 2, 3, 4, 6;

	IF v_dados.total_icms > 0 OR v_dados.regime != 'SIMPLES NACIONAL' THEN 
		RETURN v_dados.total_icms;
	END IF;
	IF v_dados.icms_item > 0 THEN 
		RETURN v_dados.icms_item;
	END IF;

	v_info_contr := COALESCE(v_dados.info_complementares, '') || ' ' || COALESCE(v_dados.info_fisco, '');
	IF v_dados.tribut_sn ~* 'com permissão de crédito' THEN 
		RETURN REGEXP_REPLACE(COALESCE(SUBSTRING(v_info_contr FROM v_regex), '0'), '[\.,]', '')::NUMERIC/100;
	END IF;

	RETURN 0;
END;
$BODY$;


/**
 * Função para dizer créditos de ICMS para DIFAL Entrada 
 * Segue regras do art. 117 do RICMS/00, especialmente §5º, item 1 para SN - mas ignora casos de 4%
 */
CREATE OR REPLACE FUNCTION nfe_icms_difal_entrada(_chave text, _item int)
	RETURNS NUMERIC
LANGUAGE PLPGSQL AS
$BODY$
DECLARE 
	v_info_contr text;
	v_info_fisco text;
	v_dados		 RECORD;
BEGIN
	SELECT nfe_item.icms, info_complementares_interesse_contribuinte, info_interesse_fisco, 
		nfe_item.valor_produto + nfe_Item.valor_frete + nfe_Item.valor_seguro + nfe_item.valor_outro + nfe_item.ipi - nfe_item.valor_desconto AS bc_icms
		INTO v_dados 
	FROM nfe 
		JOIN nfe_item 
			JOIN cfop ON nfe_item.cfop = cfop.codigo
		ON nfe.chave = nfe_item.chave
		JOIN icms_aliq_inter_ufs aliq ON (nfe.uf_emit != 'SP' AND nfe.tipo_doc_fiscal = 'Saída' AND nfe.uf_emit = aliq.uf_origem AND nfe.uf_dest = aliq.uf_destino) 
			OR (nfe.uf_dest != 'SP' AND nfe.tipo_doc_fiscal = 'Entrada' AND nfe.uf_dest = aliq.uf_origem AND nfe.uf_emit = aliq.uf_destino)
	WHERE nfe.chave = _chave AND nfe_item.item = _item;

	v_info_contr := v_dados.info_complementares_interesse_contribuinte;
	v_info_fisco := v_dados.info_interesse_fisco;

	IF (v_info_contr ~* 'simples\s+nacional' OR v_info_fisco ~* 'simples\s+nacional') AND v_info_contr !~* '(n[aã]o\s+permite\s+[o\s]*aproveitamento|n[aã]o gera direito a cr[eé]dito)' THEN
		RETURN round(v_dados.bc_icms*0.12, 2);
	ELSE 
		RETURN v_dados.icms;
	END IF;
END;
$BODY$;


/**
 * Função para dizer qual é a alíquota para um NCM em uma data se for saida interna,
 * 		ou alíquota interestadual para saída externa
 * Se não houver alíquota informada na tabela icms_aliqs_sp, considera 18%
 */
CREATE OR REPLACE FUNCTION aliquota(_ncm bigint, _saida date, _ufdestino varchar)
	RETURNS NUMERIC
LANGUAGE PLPGSQL AS
$BODY$
DECLARE 
	v_aliq		 numeric;
	v_dados		 RECORD;
BEGIN
	IF _ufdestino != 'SP' THEN 
		SELECT aliq_uf
			INTO v_aliq 
		FROM "Aliq_UF"
		WHERE uf = _ufdestino;
	ELSE 
		SELECT "Alíquota"*100
			INTO v_aliq
		FROM "ALIQUOTA SP - NCM"
		WHERE (_ncm/10^(8-"Nr_Carac_NCM"))::INT = "NCM_num";
	END IF;
	RETURN ROUND(COALESCE(v_aliq, 18), 2);
END;
$BODY$;
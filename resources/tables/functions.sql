/**
 * Função para dizer total de créditos de ICMS (verifica dados de Simples Nacional)
 */
CREATE OR REPLACE FUNCTION nfe_icms(_chave text)
	RETURNS NUMERIC
LANGUAGE PLPGSQL AS
$BODY$
DECLARE 
	v_info_contr text;
	v_regex		 text := '(?i)aproveitamento\s+d[e|o]\s+(?:cr[é|e]dito|cr[é|e]dito\s+fiscal)\s+d[e|o]\s+ICMS\s+(?:no\s+valor\s+)(?:de\s+)?(?:r[S|$|$]\s*)?([\d\.\,]+\d{2})';
	v_dados		 RECORD;
BEGIN
	SELECT cadesp_regime.regime, total_icms, info_complementares_interesse_contribuinte, info_interesse_fisco, 
		sum(COALESCE(nfe_item.icms, 0) + COALESCE(nfe_item.valor_cred_sn, 0)) AS icms_item 
		INTO v_dados 
	FROM nfe 
		JOIN nfe_item ON nfe.chave = nfe_item.chave
		LEFT JOIN cadesp 
			LEFT JOIN cadesp_regime ON cadesp.ie = cadesp_regime.ie
		ON cadesp.ie = nfe.ie_emit 
	WHERE nfe.chave = _chave
	AND nfe.emissao BETWEEN COALESCE(cadesp_regime.inicio_regime,'1-1-2000') AND COALESCE(cadesp_regime.fim_regime, now())
	GROUP BY 1, 2, 3, 4;

	IF v_dados.total_icms > 0 OR v_dados.regime != 'Simples Nacional' THEN 
		RETURN v_dados.total_icms;
	END IF;
	IF v_dados.icms_item > 0 THEN 
		RETURN v_dados.icms_item;
	END IF;

	v_info_contr := v_dados.info_complementares_interesse_contribuinte || ' ' || v_dados.info_interesse_fisco;
	IF v_info_contr ~* 'aproveitamento' AND v_info_contr !~* '(n[aã]o\s+permite\s+[o\s]*aproveitamento|n[aã]o gera direito a cr[eé]dito)' THEN 
		RETURN TO_NUMBER(COALESCE(SUBSTRING(v_info_contr FROM v_regex), '0'), 'FM999G999G999D99');
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
CREATE OR REPLACE FUNCTION aliquota(_ncm int, _saida date, _ufdestino varchar)
	RETURNS NUMERIC
LANGUAGE PLPGSQL AS
$BODY$
DECLARE 
	v_aliq		 numeric;
	v_dados		 RECORD;
BEGIN
	IF _ufdestino != 'SP' THEN 
		SELECT aliquota
			INTO v_aliq 
		FROM icms_aliq_inter_ufs 
		WHERE uf_origem = 'SP' AND uf_destino = _ufdestino;
	ELSE 
		SELECT aliquota
			INTO v_aliq
		FROM icms_aliqs_sp
		WHERE _ncm BETWEEN ncm_inicial AND ncm_final AND _saida BETWEEN data_inicio AND COALESCE(data_fim, now());
	END IF;
	RETURN ROUND(COALESCE(v_aliq, 18), 2);
END;
$BODY$;
INSERT INTO nfe_x_nfe 
	SELECT DISTINCT nfe_referente, nfe_referenciada
	FROM NFE_REFS_TEMP, nfe AS nfe1, nfe AS nfe2
	WHERE length(nfe_referenciada) > 0
	AND nfe1.chave = nfe_referente
	AND nfe2.chave = nfe_referenciada
	ON CONFLICT DO NOTHING;
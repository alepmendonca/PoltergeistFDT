/** Cria alguns indices nas views para facilitar queries
*/
UPDATE reg_0000 SET cnpj = cnpj::NUMERIC::varchar;
ALTER TABLE reg_0000 ALTER COLUMN ie TYPE int8 USING ie::BIGINT;
UPDATE reg_0150 SET cnpj = CASE WHEN length(cnpj) = 0 THEN NULL ELSE cnpj::NUMERIC::varchar END;
ALTER TABLE reg_0200 ALTER COLUMN cod_ncm TYPE int USING CASE WHEN length(trim(cod_ncm)) = 0 THEN NULL ELSE cod_ncm::int END;
UPDATE reg_0200 SET cod_ncm = NULL WHERE cod_ncm < 1000;
UPDATE reg_0200 SET cod_ncm = de_para.codigo_existente
	FROM (
		WITH heuristica AS (
			WITH ncms_estranhos AS (
				SELECT reg_0200.* 
				FROM reg_0200 WHERE cod_ncm NOT IN (SELECT codigo FROM ncm) AND cod_ncm IS NOT NULL
			) SELECT codigo, cod_ncm, cod_ncm - codigo AS diferenca FROM ncm, ncms_estranhos WHERE codigo/100000 = cod_ncm/100000 AND cod_ncm - codigo > 0
		)
		SELECT h2.codigo AS codigo_existente, h2.cod_ncm AS codigo_errado
			FROM (SELECT cod_ncm, min(diferenca) AS diferenca FROM heuristica GROUP BY 1) AS h1, heuristica AS h2
			WHERE h1.cod_ncm = h2.cod_ncm AND h1.diferenca = h2.diferenca
	) AS de_para
	WHERE reg_0200.cod_ncm = de_para.codigo_errado;
ALTER TABLE reg_0200 ADD CONSTRAINT reg_0200_fk FOREIGN KEY (cod_ncm) REFERENCES public.ncm(codigo);
ALTER TABLE reg_c100 ALTER COLUMN num_doc TYPE int USING num_doc::int;
CREATE INDEX reg_c100_num_doc_idx ON reg_c100 (num_doc);
CREATE INDEX reg_c100_chv_nfe_idx ON reg_c100 (chv_nfe);
ALTER TABLE reg_c100 ALTER COLUMN ind_oper TYPE int USING ind_oper::int;
ALTER TABLE reg_c100 ALTER COLUMN ind_emit TYPE int USING ind_emit::int;
ALTER TABLE reg_c170 ALTER COLUMN cfop TYPE int USING cfop::int;
ALTER TABLE reg_c170 ALTER COLUMN cst_icms TYPE int USING cst_icms::int;
UPDATE reg_c170 SET unid = trim(unid);
CREATE INDEX reg_c170_cfop_idx ON reg_c170 (id_pai, cfop);
ALTER TABLE reg_c190 ALTER COLUMN cfop TYPE int USING cfop::int;
ALTER TABLE reg_c190 ADD CONSTRAINT reg_c190_fk FOREIGN KEY (cfop) REFERENCES cfop(codigo);
ALTER TABLE reg_c190 ALTER COLUMN cst_icms TYPE int USING cst_icms::int;
CREATE INDEX reg_c190_cfop_idx ON reg_c190 (cfop, cst_icms);
CREATE INDEX reg_c190_pai_idx ON reg_c190 (id_pai, efd);
ALTER TABLE reg_c490 ALTER COLUMN cfop TYPE int USING cfop::int;
ALTER TABLE reg_c490 ADD CONSTRAINT reg_c490_fk FOREIGN KEY (cfop) REFERENCES cfop(codigo);
ALTER TABLE reg_c490 ALTER COLUMN cst_icms TYPE int USING cst_icms::int;
CREATE INDEX reg_c490_cfop_idx ON reg_c490 (cfop, cst_icms);
ALTER TABLE reg_c590 ALTER COLUMN cfop TYPE int USING cfop::int;
ALTER TABLE reg_c590 ADD CONSTRAINT reg_c590_fk FOREIGN KEY (cfop) REFERENCES cfop(codigo);
ALTER TABLE reg_c590 ALTER COLUMN cst_icms TYPE int USING cst_icms::int;
CREATE INDEX reg_c590_cfop_idx ON reg_c590 (cfop, cst_icms);
ALTER TABLE reg_d100 ALTER COLUMN num_doc TYPE int USING num_doc::int;
CREATE INDEX reg_d100_num_doc_idx ON reg_d100 (num_doc);
CREATE INDEX reg_d100_chv_cte_idx ON reg_d100 (chv_cte);
UPDATE reg_d100 SET chv_cte = NULL WHERE length(chv_cte) = 0;
ALTER TABLE reg_d100 ALTER COLUMN ind_oper TYPE int USING ind_oper::int;
ALTER TABLE reg_d100 ALTER COLUMN ind_emit TYPE int USING ind_emit::int;
ALTER TABLE reg_d190 ALTER COLUMN cfop TYPE int USING cfop::int;
ALTER TABLE reg_d190 ADD CONSTRAINT reg_d190_fk FOREIGN KEY (cfop) REFERENCES cfop(codigo);
ALTER TABLE reg_d190 ALTER COLUMN cst_icms TYPE int USING cst_icms::int;
CREATE INDEX reg_d190_cfop_idx ON reg_d190 (cfop, cst_icms);
ALTER TABLE reg_d590 ALTER COLUMN cfop TYPE int USING cfop::int;
ALTER TABLE reg_d590 ADD CONSTRAINT reg_d590_fk FOREIGN KEY (cfop) REFERENCES cfop(codigo);
ALTER TABLE reg_d590 ALTER COLUMN cst_icms TYPE int USING cst_icms::int;
CREATE INDEX reg_d590_cfop_idx ON reg_d590 (cfop, cst_icms);
ALTER TABLE reg_c850 ALTER COLUMN cfop TYPE int USING cfop::int;
ALTER TABLE reg_c850 ADD CONSTRAINT reg_c850_fk FOREIGN KEY (cfop) REFERENCES cfop(codigo);
ALTER TABLE reg_c850 ALTER COLUMN cst_icms TYPE int USING cst_icms::int;
CREATE INDEX reg_c850_cfop_idx ON reg_c850 (cfop, cst_icms);
ALTER TABLE reg_g130 ALTER COLUMN num_doc TYPE int USING num_doc::int;
UPDATE reg_h010 SET unid = trim(unid);
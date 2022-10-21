CREATE TABLE IF NOT EXISTS icms_aliq_intra_ufs (
	uf bpchar(2) NOT NULL,
	aliquota numeric(10, 2) NOT NULL,
	CONSTRAINT icms_aliq_intra_ufs_pkey PRIMARY KEY (uf)
);
CREATE INDEX IF NOT EXISTS icms_aliq_int_uf ON icms_aliq_intra_ufs USING btree (uf);

INSERT INTO icms_aliq_intra_ufs (uf,aliquota) VALUES
	 ('AL',12.00),
	 ('RO',17.50),
	 ('AC',17.00),
	 ('ES',17.00),
	 ('GO',17.00),
	 ('MT',17.00),
	 ('MS',17.00),
	 ('PA',17.00),
	 ('RR',17.00),
	 ('SC',17.00) ON CONFLICT DO NOTHING;
INSERT INTO icms_aliq_intra_ufs (uf,aliquota) VALUES
	 ('AM',18.00),
	 ('AP',18.00),
	 ('BA',18.00),
	 ('CE',18.00),
	 ('DF',18.00),
	 ('MA',18.00),
	 ('MG',18.00),
	 ('PB',18.00),
	 ('PR',18.00),
	 ('PE',18.00) ON CONFLICT DO NOTHING;
INSERT INTO icms_aliq_intra_ufs (uf,aliquota) VALUES
	 ('PI',18.00),
	 ('RN',18.00),
	 ('RS',18.00),
	 ('RJ',18.00),
	 ('SP',18.00),
	 ('SE',18.00),
	 ('TO',18.00) ON CONFLICT DO NOTHING;

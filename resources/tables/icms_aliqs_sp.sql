CREATE TABLE IF NOT EXISTS icms_aliqs_sp (
	ncm_inicial int4 NOT NULL,
	ncm_final int4 NOT NULL,
	data_inicio date NOT NULL,
	data_fim date NULL,
	aliquota numeric(5, 3),
	legislacao varchar NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS icms_aliqs_sp_uq ON icms_aliqs_sp (ncm_inicial, ncm_final, data_inicio, aliquota);

INSERT INTO icms_aliqs_sp (ncm_inicial,ncm_final,data_inicio,data_fim,aliquota,legislacao) VALUES
	 (40141000,40141000,'2008-02-23','2021-01-14',7.000,'Art. 53-A, I'),
	 (40141000,40141000,'2021-01-15','2023-01-14',9.400,'Art. 53-A, I'),
	 (40141000,40141000,'2023-01-15',NULL,7.000,'Art. 53-A, I'),
	 (4081100,4089900,'2008-02-23',NULL,7.000,'Art. 53-A, II'),
	 (4081100,4089900,'2021-01-15','2023-01-14',9.400,'Art. 53-A, II'),
	 (4081100,4089900,'2023-01-15',NULL,7.000,'Art. 53-A, II'),
	 (19012099,19012099,'2000-01-01','2021-01-14',12.000,'Art. 54, III'),
	 (37059010,37059010,'2014-04-01','2021-01-14',12.000,'Art. 54, V, SF-31/08, item 1'),
	 (69091220,69091220,'2014-04-01','2021-01-14',12.000,'Art. 54, V, SF-31/08, item 2'),
	 (69091920,69091920,'2014-04-01','2021-01-14',12.000,'Art. 54, V, SF-31/08, item 2') ON CONFLICT DO NOTHING;
INSERT INTO icms_aliqs_sp (ncm_inicial,ncm_final,data_inicio,data_fim,aliquota,legislacao) VALUES
	 (71162020,71162020,'2014-04-01','2021-01-14',12.000,'Art. 54, V, SF-31/08, item 3'),
	 (84099140,84099140,'2014-04-01','2021-01-14',12.000,'Art. 54, V, SF-31/08, item 4'),
	 (72131000,72131000,'2000-01-01','2021-01-14',12.000,'Art. 54, VII, §1º, 1, a'),
	 (72132000,72132000,'2000-01-01','2021-01-14',12.000,'Art. 54, VII, §1º, 1, b'),
	 (72142000,72142000,'2000-01-01','2021-01-14',12.000,'Art. 54, VII, §1º, 2, a'),
	 (72149100,72149100,'2000-01-01','2021-01-14',12.000,'Art. 54, VII, §1º, 2, b'),
	 (72149910,72149910,'2000-01-01','2021-01-14',12.000,'Art. 54, VII, §1º, 2, b'),
	 (44101900,44101900,'2000-01-01','2021-01-14',12.000,'Art. 54, IX'),
	 (44111100,44111100,'2000-01-01','2021-01-14',12.000,'Art. 54, IX'),
	 (44111900,44111900,'2000-01-01','2021-01-14',12.000,'Art. 54, IX') ON CONFLICT DO NOTHING;
INSERT INTO icms_aliqs_sp (ncm_inicial,ncm_final,data_inicio,data_fim,aliquota,legislacao) VALUES
	 (44112100,44112100,'2000-01-01','2021-01-14',12.000,'Art. 54, IX'),
	 (44112900,44112900,'2000-01-01','2021-01-14',12.000,'Art. 54, IX'),
	 (87012002,87012002,'2000-01-01','2021-01-14',12.000,'Art. 54, XI'),
	 (87012099,87012099,'2000-01-01','2021-01-14',12.000,'Art. 54, XI'),
	 (87021001,87021001,'2000-01-01','2021-01-14',12.000,'Art. 54, XI'),
	 (87021099,87021099,'2000-01-01','2021-01-14',12.000,'Art. 54, XI'),
	 (87042101,87042101,'2000-01-01','2021-01-14',12.000,'Art. 54, XI'),
	 (87042201,87042201,'2000-01-01','2021-01-14',12.000,'Art. 54, XI'),
	 (87042301,87042301,'2000-01-01','2021-01-14',12.000,'Art. 54, XI'),
	 (87043101,87043101,'2000-01-01','2021-01-14',12.000,'Art. 54, XI') ON CONFLICT DO NOTHING;
INSERT INTO icms_aliqs_sp (ncm_inicial,ncm_final,data_inicio,data_fim,aliquota,legislacao) VALUES
	 (87043201,87043201,'2000-01-01','2021-01-14',12.000,'Art. 54, XI'),
	 (87043299,87043299,'2000-01-01','2021-01-14',12.000,'Art. 54, XI'),
	 (87060001,87060002,'2000-01-01','2021-01-14',12.000,'Art. 54, XI'),
	 (94010000,94011999,'2000-01-01','2021-01-14',12.000,'Art. 54, XIII, a'),
	 (94012001,94019999,'2000-01-01','2021-01-14',12.000,'Art. 54, XIII, a'),
	 (94030000,94039999,'2000-01-01','2021-01-14',12.000,'Art. 54, XIII, b'),
	 (94041000,94041099,'2000-01-01','2021-01-14',12.000,'Art. 54, XIII, c'),
	 (94042000,94042999,'2000-01-01','2021-01-14',12.000,'Art. 54, XIII, d'),
	 (39219010,39219019,'2000-01-01','2021-01-14',12.000,'Art. 54, XIV, a'),
	 (39219090,39219099,'2000-01-01','2021-01-14',12.000,'Art. 54, XIV, a') ON CONFLICT DO NOTHING;
INSERT INTO icms_aliqs_sp (ncm_inicial,ncm_final,data_inicio,data_fim,aliquota,legislacao) VALUES
	 (48113120,48113120,'2000-01-01','2021-01-14',12.000,'Art. 54, XIV, b'),
	 (84281000,84281099,'2000-01-01','2021-01-14',12.000,'Art. 54, XV, a'),
	 (84284000,84284099,'2000-01-01','2021-01-14',12.000,'Art. 54, XV, b'),
	 (84313100,84313199,'2000-01-01','2021-01-14',12.000,'Art. 54, XV, c'),
	 (90183119,90183119,'2000-01-01','2021-01-14',12.000,'Art. 54, XV, d'),
	 (90183219,90183219,'2000-01-01','2021-01-14',12.000,'Art. 54, XV, b'),
	 (19051000,19051099,'2005-05-01','2021-01-14',12.000,'Art. 54, XVI'),
	 (19052000,19052099,'2005-05-01','2021-01-14',12.000,'Art. 54, XVI'),
	 (19054000,19054099,'2005-05-01','2021-01-14',12.000,'Art. 54, XVI (apenas pão torrado, torradas ou semelhantes)'),
	 (19059000,19059099,'2005-05-01','2021-01-14',12.000,'Art. 54, XVI') ON CONFLICT DO NOTHING;
INSERT INTO icms_aliqs_sp (ncm_inicial,ncm_final,data_inicio,data_fim,aliquota,legislacao) VALUES
	 (30049099,30049099,'2004-06-22','2021-01-14',12.000,'Art. 54, XVII (verificar lista)'),
	 (33061000,33061000,'2006-06-10','2021-01-14',12.000,'Art. 54, XVIII'),
	 (96032100,96032100,'2006-06-10','2021-01-14',12.000,'Art. 54, XVIII (exceto escovas elétricas)'),
	 (19012099,19012099,'2021-01-15',NULL,13.300,'Art. 54, III'),
	 (37059010,37059010,'2021-01-15',NULL,13.300,'Art. 54, V, SF-31/08, item 1'),
	 (69091220,69091220,'2021-01-15',NULL,13.300,'Art. 54, V, SF-31/08, item 2'),
	 (69091920,69091920,'2021-01-15',NULL,13.300,'Art. 54, V, SF-31/08, item 2'),
	 (71162020,71162020,'2021-01-15',NULL,13.300,'Art. 54, V, SF-31/08, item 3'),
	 (84099140,84099140,'2021-01-15',NULL,13.300,'Art. 54, V, SF-31/08, item 4'),
	 (72131000,72131000,'2021-01-15',NULL,13.300,'Art. 54, VII, §1º, 1, a') ON CONFLICT DO NOTHING;
INSERT INTO icms_aliqs_sp (ncm_inicial,ncm_final,data_inicio,data_fim,aliquota,legislacao) VALUES
	 (72132000,72132000,'2021-01-15',NULL,13.300,'Art. 54, VII, §1º, 1, b'),
	 (72142000,72142000,'2021-01-15',NULL,13.300,'Art. 54, VII, §1º, 2, a'),
	 (72149100,72149100,'2021-01-15',NULL,13.300,'Art. 54, VII, §1º, 2, b'),
	 (72149910,72149910,'2021-01-15',NULL,13.300,'Art. 54, VII, §1º, 2, b'),
	 (44101900,44101900,'2021-01-15',NULL,13.300,'Art. 54, IX'),
	 (44111100,44111100,'2021-01-15',NULL,13.300,'Art. 54, IX'),
	 (44111900,44111900,'2021-01-15',NULL,13.300,'Art. 54, IX'),
	 (44112100,44112100,'2021-01-15',NULL,13.300,'Art. 54, IX'),
	 (44112900,44112900,'2021-01-15',NULL,13.300,'Art. 54, IX'),
	 (87012002,87012002,'2021-01-15',NULL,13.300,'Art. 54, XI') ON CONFLICT DO NOTHING;
INSERT INTO icms_aliqs_sp (ncm_inicial,ncm_final,data_inicio,data_fim,aliquota,legislacao) VALUES
	 (87012099,87012099,'2021-01-15',NULL,13.300,'Art. 54, XI'),
	 (87021001,87021001,'2021-01-15',NULL,13.300,'Art. 54, XI'),
	 (87021099,87021099,'2021-01-15',NULL,13.300,'Art. 54, XI'),
	 (87042101,87042101,'2021-01-15',NULL,13.300,'Art. 54, XI'),
	 (87042201,87042201,'2021-01-15',NULL,13.300,'Art. 54, XI'),
	 (87042301,87042301,'2021-01-15',NULL,13.300,'Art. 54, XI'),
	 (87043101,87043101,'2021-01-15',NULL,13.300,'Art. 54, XI'),
	 (87043201,87043201,'2021-01-15',NULL,13.300,'Art. 54, XI'),
	 (87043299,87043299,'2021-01-15',NULL,13.300,'Art. 54, XI'),
	 (87060001,87060002,'2021-01-15',NULL,13.300,'Art. 54, XI') ON CONFLICT DO NOTHING;
INSERT INTO icms_aliqs_sp (ncm_inicial,ncm_final,data_inicio,data_fim,aliquota,legislacao) VALUES
	 (94010000,94011999,'2021-01-15',NULL,13.300,'Art. 54, XIII, a'),
	 (94012001,94019999,'2021-01-15',NULL,13.300,'Art. 54, XIII, a'),
	 (94030000,94039999,'2021-01-15',NULL,13.300,'Art. 54, XIII, b'),
	 (94041000,94041099,'2021-01-15',NULL,13.300,'Art. 54, XIII, c'),
	 (94042000,94042999,'2021-01-15',NULL,13.300,'Art. 54, XIII, d'),
	 (39219010,39219019,'2021-01-15',NULL,13.300,'Art. 54, XIV, a'),
	 (39219090,39219099,'2021-01-15',NULL,13.300,'Art. 54, XIV, a'),
	 (48113120,48113120,'2021-01-15',NULL,13.300,'Art. 54, XIV, b'),
	 (84281000,84281099,'2021-01-15',NULL,13.300,'Art. 54, XV, a'),
	 (84284000,84284099,'2021-01-15',NULL,13.300,'Art. 54, XV, b') ON CONFLICT DO NOTHING;
INSERT INTO icms_aliqs_sp (ncm_inicial,ncm_final,data_inicio,data_fim,aliquota,legislacao) VALUES
	 (84313100,84313199,'2021-01-15',NULL,13.300,'Art. 54, XV, c'),
	 (90183119,90183119,'2021-01-15',NULL,13.300,'Art. 54, XV, d'),
	 (90183219,90183219,'2021-01-15',NULL,13.300,'Art. 54, XV, b'),
	 (19051000,19051099,'2021-01-15',NULL,13.300,'Art. 54, XVI'),
	 (19052000,19052099,'2021-01-15',NULL,13.300,'Art. 54, XVI'),
	 (19054000,19054099,'2021-01-15',NULL,13.300,'Art. 54, XVI (apenas pão torrado, torradas ou semelhantes)'),
	 (19059000,19059099,'2021-01-15',NULL,13.300,'Art. 54, XVI'),
	 (30049099,30049099,'2021-01-15',NULL,13.300,'Art. 54, XVII (verificar lista)'),
	 (33061000,33061000,'2021-01-15',NULL,13.300,'Art. 54, XVIII'),
	 (96032100,96032100,'2021-01-15',NULL,13.300,'Art. 54, XVIII (exceto escovas elétricas)') ON CONFLICT DO NOTHING;
INSERT INTO icms_aliqs_sp (ncm_inicial,ncm_final,data_inicio,data_fim,aliquota,legislacao) VALUES
	 (22030000,22039999,'2016-02-23',NULL,20.000,'Art. 54-A'),
	 (22040000,22049999,'2000-01-01',NULL,25.000,'Art. 55, II'),
	 (22050000,22059999,'2000-01-01',NULL,25.000,'Art. 55, II'),
	 (22080000,22084001,'2000-01-01',NULL,25.000,'Art. 55, II'),
	 (22084004,22089999,'2000-01-01',NULL,25.000,'Art. 55, II'),
	 (24000000,24999999,'2000-01-01','2016-02-22',25.000,'Art. 55, III'),
	 (33030000,33049999,'2000-01-01',NULL,25.000,'Art. 55, IV (exceto preparações anti-solares e bronzeadores)'),
	 (33050000,33050999,'2000-01-01',NULL,25.000,'Art. 55, IV'),
	 (33051100,33059999,'2000-01-01',NULL,25.000,'Art. 55, IV'),
	 (33070000,33071000,'2000-01-01',NULL,25.000,'Art. 55, IV') ON CONFLICT DO NOTHING;
INSERT INTO icms_aliqs_sp (ncm_inicial,ncm_final,data_inicio,data_fim,aliquota,legislacao) VALUES
	 (33071002,33071999,'2000-01-01',NULL,25.000,'Art. 55, IV'),
	 (33072100,33079004,'2000-01-01',NULL,25.000,'Art. 55, IV'),
	 (33079006,33079999,'2000-01-01',NULL,25.000,'Art. 55, IV'),
	 (24000000,24999999,'2016-02-23',NULL,30.000,'Art. 55-A'),
	 (73143900,73143900,'2000-01-01','2021-01-14',12.000,'Art. 54, VII, §1º, 6, b'),
	 (73144100,73144100,'2000-01-01','2021-01-14',12.000,'Art. 54, VII, §1º, 7, a'),
	 (39181000,39181000,'2006-01-10','2021-01-14',12.000,'Art. 54, VIII, §2º, 22'),
	 (73170020,73170020,'2000-01-01','2021-01-14',12.000,'Art. 54, VII, §1º, 10'),
	 (73170090,73170090,'2000-01-01','2021-01-14',12.000,'Art. 54, VII, §1º, 11') ON CONFLICT DO NOTHING;

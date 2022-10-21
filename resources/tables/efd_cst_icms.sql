CREATE TABLE IF NOT EXISTS efd_cst_icms (
	codigo int4,
	descricao varchar NOT NULL,
	dt_ini date NOT NULL,
	dt_fim date NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS efd_cst_codigo ON efd_cst_icms (codigo, dt_ini);

INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (0,'Nacional - Tributada integralmente','2009-01-01','2012-12-31'),
	 (10,'Nacional - Tributada e com cobrança do ICMS por substituição tributária','2009-01-01','2012-12-31'),
	 (20,'Nacional - Com redução de base de cálculo','2009-01-01','2012-12-31'),
	 (30,'Nacional - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2009-01-01','2012-12-31'),
	 (40,'Nacional - Isenta','2009-01-01','2012-12-31'),
	 (41,'Nacional - Não tributada','2009-01-01','2012-12-31'),
	 (50,'Nacional - Suspensão','2009-01-01','2012-12-31'),
	 (51,'Nacional - Diferimento','2009-01-01','2012-12-31'),
	 (60,'Nacional - ICMS cobrado anteriormente por substituição tributária','2009-01-01','2012-12-31'),
	 (70,'Nacional - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2009-01-01','2012-12-31') ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (90,'Nacional - Outras','2009-01-01','2012-12-31'),
	 (100,'Estrangeira - Importação direta - Tributada integralmente','2009-01-01','2012-12-31'),
	 (110,'Estrangeira - Importação direta - Tributada e com cobrança do ICMS por substituição tributária','2009-01-01','2012-12-31'),
	 (120,'Estrangeira - Importação direta - Com redução de base de cálculo','2009-01-01','2012-12-31'),
	 (130,'Estrangeira - Importação direta - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2009-01-01','2012-12-31'),
	 (140,'Estrangeira - Importação direta - Isenta','2009-01-01','2012-12-31'),
	 (141,'Estrangeira - Importação direta - Não tributada','2009-01-01','2012-12-31'),
	 (150,'Estrangeira - Importação direta - Suspensão','2009-01-01','2012-12-31'),
	 (151,'Estrangeira - Importação direta - Diferimento','2009-01-01','2012-12-31'),
	 (160,'Estrangeira - Importação direta - ICMS cobrado anteriormente por substituição tributária','2009-01-01','2012-12-31') ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (170,'Estrangeira - Importação direta - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2009-01-01','2012-12-31'),
	 (190,'Estrangeira - Importação direta - Outras','2009-01-01','2012-12-31'),
	 (200,'Estrangeira - Adquirida no mercado interno - Tributada integralmente','2009-01-01','2012-12-31'),
	 (210,'Estrangeira - Adquirida no mercado interno - Tributada e com cobrança do ICMS por substituição tributária','2009-01-01','2012-12-31'),
	 (220,'Estrangeira - Adquirida no mercado interno - Com redução de base de cálculo','2009-01-01','2012-12-31'),
	 (230,'Estrangeira - Adquirida no mercado interno - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2009-01-01','2012-12-31'),
	 (240,'Estrangeira - Adquirida no mercado interno - Isenta','2009-01-01','2012-12-31'),
	 (241,'Estrangeira - Adquirida no mercado interno - Não tributada','2009-01-01','2012-12-31'),
	 (250,'Estrangeira - Adquirida no mercado interno - Suspensão','2009-01-01','2012-12-31'),
	 (251,'Estrangeira - Adquirida no mercado interno - Diferimento','2009-01-01','2012-12-31') ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (260,'Estrangeira - Adquirida no mercado interno - ICMS cobrado anteriormente por substituição tributária','2009-01-01','2012-12-31'),
	 (270,'Estrangeira - Adquirida no mercado interno - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2009-01-01','2012-12-31'),
	 (290,'Estrangeira - Adquirida no mercado interno - Outras','2009-01-01','2012-12-31'),
	 (101,'Simples Nacional - Tributada pelo Simples Nacional com permissão de crédito','2010-10-01',NULL),
	 (102,'Simples Nacional - Tributada pelo Simples Nacional sem permissão de crédito','2010-10-01',NULL),
	 (103,'Simples Nacional - Isenção do ICMS no Simples Nacional para faixa de receita bruta','2010-10-01',NULL),
	 (201,'Simples Nacional - Tributada pelo Simples Nacional com permissão de crédito e com cobrança do ICMS por substituição tributária','2010-10-01',NULL),
	 (202,'Simples Nacional - Tributada pelo Simples Nacional sem permissão de crédito e com cobrança do ICMS por substituição tributária','2010-10-01',NULL),
	 (203,'Simples Nacional - Isenção do ICMS no Simples Nacional para faixa de receita bruta e com cobrança do ICMS por substituição tributária','2010-10-01',NULL),
	 (300,'Simples Nacional - Imune','2010-10-01','2012-12-31') ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (400,'Simples Nacional - Não tributada pelo Simples Nacional','2010-10-01','2012-12-31'),
	 (500,'Simples Nacional - ICMS cobrado anteriormente por substituição tributária (substituído) ou por antecipação','2010-10-01','2012-12-31'),
	 (900,'Simples Nacional - Outros','2010-10-01',NULL),
	 (0,'Nacional, exceto as indicadas nos códigos 3 a 5 da Tabela A - Tributada integralmente','2013-01-01','2013-07-31'),
	 (10,'Nacional, exceto as indicadas nos códigos 3 a 5 da Tabela A - Tributada e com cobrança do ICMS por substituição tributária','2013-01-01','2013-07-31'),
	 (20,'Nacional, exceto as indicadas nos códigos 3 a 5 da Tabela A - Com redução de base de cálculo','2013-01-01','2013-07-31'),
	 (30,'Nacional, exceto as indicadas nos códigos 3 a 5 da Tabela A - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2013-01-01','2013-07-31'),
	 (40,'Nacional, exceto as indicadas nos códigos 3 a 5 da Tabela A - Isenta','2013-01-01','2013-07-31'),
	 (41,'Nacional, exceto as indicadas nos códigos 3 a 5 da Tabela A - Não tributada','2013-01-01','2013-07-31'),
	 (50,'Nacional, exceto as indicadas nos códigos 3 a 5 da Tabela A - Suspensão','2013-01-01','2013-07-31') ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (51,'Nacional, exceto as indicadas nos códigos 3 a 5 da Tabela A - Diferimento','2013-01-01','2013-07-31'),
	 (60,'Nacional, exceto as indicadas nos códigos 3 a 5 da Tabela A - ICMS cobrado anteriormente por substituição tributária','2013-01-01','2013-07-31'),
	 (70,'Nacional, exceto as indicadas nos códigos 3 a 5 da Tabela A - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2013-01-01','2013-07-31'),
	 (90,'Nacional, exceto as indicadas nos códigos 3 a 5 da Tabela A - Outras','2013-01-01','2013-07-31'),
	 (0,'Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 da Tabela A - Tributada integralmente','2013-08-01',NULL),
	 (10,'Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 da Tabela A - Tributada e com cobrança do ICMS por substituição tributária','2013-08-01',NULL),
	 (20,'Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 da Tabela A - Com redução de base de cálculo','2013-08-01',NULL),
	 (30,'Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 da Tabela A - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2013-08-01',NULL),
	 (40,'Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 da Tabela A - Isenta','2013-08-01',NULL),
	 (41,'Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 da Tabela A - Não tributada','2013-08-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (50,'Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 da Tabela A - Suspensão','2013-08-01',NULL),
	 (51,'Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 da Tabela A - Diferimento','2013-08-01',NULL),
	 (60,'Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 da Tabela A - ICMS cobrado anteriormente por substituição tributária','2013-08-01',NULL),
	 (70,'Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 da Tabela A - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2013-08-01',NULL),
	 (90,'Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8 da Tabela A - Outras','2013-08-01',NULL),
	 (100,'Estrangeira - Importação direta, exceto a indicada no código 6 da Tabela A - Tributada integralmente','2013-01-01',NULL),
	 (110,'Estrangeira - Importação direta, exceto a indicada no código 6 da Tabela A - Tributada e com cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (120,'Estrangeira - Importação direta, exceto a indicada no código 6 da Tabela A - Com redução de base de cálculo','2013-01-01',NULL),
	 (130,'Estrangeira - Importação direta, exceto a indicada no código 6 da Tabela A - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (140,'Estrangeira - Importação direta, exceto a indicada no código 6 da Tabela A - Isenta','2013-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (141,'Estrangeira - Importação direta, exceto a indicada no código 6 da Tabela A - Não tributada','2013-01-01',NULL),
	 (150,'Estrangeira - Importação direta, exceto a indicada no código 6 da Tabela A - Suspensão','2013-01-01',NULL),
	 (151,'Estrangeira - Importação direta, exceto a indicada no código 6 da Tabela A - Diferimento','2013-01-01',NULL),
	 (160,'Estrangeira - Importação direta, exceto a indicada no código 6 da Tabela A - ICMS cobrado anteriormente por substituição tributária','2013-01-01',NULL),
	 (170,'Estrangeira - Importação direta, exceto a indicada no código 6 da Tabela A - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (190,'Estrangeira - Importação direta, exceto a indicada no código 6 da Tabela A - Outras','2013-01-01',NULL),
	 (200,'Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 da Tabela A - Tributada integralmente','2013-01-01',NULL),
	 (210,'Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 da Tabela A - Tributada e com cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (220,'Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 da Tabela A - Com redução de base de cálculo','2013-01-01',NULL),
	 (230,'Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 da Tabela A - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2013-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (240,'Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 da Tabela A - Isenta','2013-01-01',NULL),
	 (241,'Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 da Tabela A - Não tributada','2013-01-01',NULL),
	 (250,'Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 da Tabela A - Suspensão','2013-01-01',NULL),
	 (251,'Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 da Tabela A - Diferimento','2013-01-01',NULL),
	 (260,'Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 da Tabela A - ICMS cobrado anteriormente por substituição tributária','2013-01-01',NULL),
	 (270,'Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 da Tabela A - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (290,'Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7 da Tabela A - Outras','2013-01-01',NULL),
	 (300,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a  40% (quarenta por cento) - Tributada integralmente','2013-01-01','2013-07-31'),
	 (310,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a  40% (quarenta por cento) - Tributada e com cobrança do ICMS por substituição tributária','2013-01-01','2013-07-31'),
	 (320,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a  40% (quarenta por cento) - Com redução de base de cálculo','2013-01-01','2013-07-31') ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (330,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a  40% (quarenta por cento) - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2013-01-01','2013-07-31'),
	 (340,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a  40% (quarenta por cento) - Isenta','2013-01-01','2013-07-31'),
	 (341,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a  40% (quarenta por cento) - Não tributada','2013-01-01','2013-07-31'),
	 (350,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a  40% (quarenta por cento) - Suspensão','2013-01-01','2013-07-31'),
	 (351,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a  40% (quarenta por cento) - Diferimento','2013-01-01','2013-07-31'),
	 (360,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a  40% (quarenta por cento) - ICMS cobrado anteriormente por substituição tributária','2013-01-01','2013-07-31'),
	 (370,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a  40% (quarenta por cento) - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2013-01-01','2013-07-31'),
	 (390,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a  40% (quarenta por cento) - Outras','2013-01-01','2013-07-31'),
	 (300,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% (quarenta por cento) e inferior ou igual a 70% (setenta por cento) - Tributada integralmente','2013-08-01',NULL),
	 (310,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% (quarenta por cento) e inferior ou igual a 70% (setenta por cento) - Tributada e com cobrança do ICMS por substituição tributária','2013-08-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (320,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% (quarenta por cento) e inferior ou igual a 70% (setenta por cento) - Com redução de base de cálculo','2013-08-01',NULL),
	 (330,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% (quarenta por cento) e inferior ou igual a 70% (setenta por cento) - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2013-08-01',NULL),
	 (340,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% (quarenta por cento) e inferior ou igual a 70% (setenta por cento) - Isenta','2013-08-01',NULL),
	 (341,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% (quarenta por cento) e inferior ou igual a 70% (setenta por cento) - Não tributada','2013-08-01',NULL),
	 (350,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% (quarenta por cento) e inferior ou igual a 70% (setenta por cento) - Suspensão','2013-08-01',NULL),
	 (351,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% (quarenta por cento) e inferior ou igual a 70% (setenta por cento) - Diferimento','2013-08-01',NULL),
	 (360,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% (quarenta por cento) e inferior ou igual a 70% (setenta por cento) - ICMS cobrado anteriormente por substituição tributária','2013-08-01',NULL),
	 (370,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% (quarenta por cento) e inferior ou igual a 70% (setenta por cento) - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2013-08-01',NULL),
	 (390,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 40% (quarenta por cento) e inferior ou igual a 70% (setenta por cento) - Outras','2013-08-01',NULL),
	 (750,'Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista de Resolução CAMEX - Suspensão','2013-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (400,'Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam o Decreto-Lei nº 288/67, e as Leis nºs 8.248/91, 8.387/91, 10.176/01 e 11.484/07 - Tributada integralmente','2013-01-01',NULL),
	 (410,'Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam o Decreto-Lei nº 288/67, e as Leis nºs 8.248/91, 8.387/91, 10.176/01 e 11.484/08 - Tributada e com cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (420,'Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam o Decreto-Lei nº 288/67, e as Leis nºs 8.248/91, 8.387/91, 10.176/01 e 11.484/09 - Com redução de base de cálculo','2013-01-01',NULL),
	 (430,'Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam o Decreto-Lei nº 288/67, e as Leis nºs 8.248/91, 8.387/91, 10.176/01 e 11.484/10 - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (440,'Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam o Decreto-Lei nº 288/67, e as Leis nºs 8.248/91, 8.387/91, 10.176/01 e 11.484/11 - Isenta','2013-01-01',NULL),
	 (441,'Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam o Decreto-Lei nº 288/67, e as Leis nºs 8.248/91, 8.387/91, 10.176/01 e 11.484/12 - Não tributada','2013-01-01',NULL),
	 (450,'Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam o Decreto-Lei nº 288/67, e as Leis nºs 8.248/91, 8.387/91, 10.176/01 e 11.484/13 - Suspensão','2013-01-01',NULL),
	 (451,'Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam o Decreto-Lei nº 288/67, e as Leis nºs 8.248/91, 8.387/91, 10.176/01 e 11.484/14 - Diferimento','2013-01-01',NULL),
	 (460,'Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam o Decreto-Lei nº 288/67, e as Leis nºs 8.248/91, 8.387/91, 10.176/01 e 11.484/15 - ICMS cobrado anteriormente por substituição tributária','2013-01-01',NULL),
	 (470,'Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam o Decreto-Lei nº 288/67, e as Leis nºs 8.248/91, 8.387/91, 10.176/01 e 11.484/16 - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2013-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (490,'Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos de que tratam o Decreto-Lei nº 288/67, e as Leis nºs 8.248/91, 8.387/91, 10.176/01 e 11.484/17 - Outras','2013-01-01',NULL),
	 (500,'Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% (quarenta por cento) - Tributada integralmente','2013-01-01',NULL),
	 (510,'Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% (quarenta por cento) - Tributada e com cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (520,'Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% (quarenta por cento) - Com redução de base de cálculo','2013-01-01',NULL),
	 (530,'Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% (quarenta por cento) - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (540,'Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% (quarenta por cento) - Isenta','2013-01-01',NULL),
	 (541,'Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% (quarenta por cento) - Não tributada','2013-01-01',NULL),
	 (550,'Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% (quarenta por cento) - Suspensão','2013-01-01',NULL),
	 (551,'Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% (quarenta por cento) - Diferimento','2013-01-01',NULL),
	 (560,'Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% (quarenta por cento) - ICMS cobrado anteriormente por substituição tributária','2013-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (570,'Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% (quarenta por cento) - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (590,'Nacional, mercadoria ou bem com Conteúdo de Importação inferior ou igual a 40% (quarenta por cento) - Outras','2013-01-01',NULL),
	 (600,'Estrangeira - Importação direta, sem similar nacional, constante em lista de Resolução CAMEX - Tributada integralmente','2013-01-01',NULL),
	 (610,'Estrangeira - Importação direta, sem similar nacional, constante em lista de Resolução CAMEX - Tributada e com cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (620,'Estrangeira - Importação direta, sem similar nacional, constante em lista de Resolução CAMEX - Com redução de base de cálculo','2013-01-01',NULL),
	 (630,'Estrangeira - Importação direta, sem similar nacional, constante em lista de Resolução CAMEX - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (640,'Estrangeira - Importação direta, sem similar nacional, constante em lista de Resolução CAMEX - Isenta','2013-01-01',NULL),
	 (641,'Estrangeira - Importação direta, sem similar nacional, constante em lista de Resolução CAMEX - Não tributada','2013-01-01',NULL),
	 (650,'Estrangeira - Importação direta, sem similar nacional, constante em lista de Resolução CAMEX - Suspensão','2013-01-01',NULL),
	 (651,'Estrangeira - Importação direta, sem similar nacional, constante em lista de Resolução CAMEX - Diferimento','2013-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (660,'Estrangeira - Importação direta, sem similar nacional, constante em lista de Resolução CAMEX - ICMS cobrado anteriormente por substituição tributária','2013-01-01',NULL),
	 (670,'Estrangeira - Importação direta, sem similar nacional, constante em lista de Resolução CAMEX - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (690,'Estrangeira - Importação direta, sem similar nacional, constante em lista de Resolução CAMEX - Outras','2013-01-01',NULL),
	 (700,'Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista de Resolução CAMEX - Tributada integralmente','2013-01-01',NULL),
	 (710,'Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista de Resolução CAMEX - Tributada e com cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (720,'Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista de Resolução CAMEX - Com redução de base de cálculo','2013-01-01',NULL),
	 (730,'Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista de Resolução CAMEX - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (740,'Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista de Resolução CAMEX - Isenta','2013-01-01',NULL),
	 (741,'Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista de Resolução CAMEX - Não tributada','2013-01-01',NULL),
	 (751,'Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista de Resolução CAMEX - Diferimento','2013-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (760,'Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista de Resolução CAMEX - ICMS cobrado anteriormente por substituição tributária','2013-01-01',NULL),
	 (770,'Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista de Resolução CAMEX - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2013-01-01',NULL),
	 (790,'Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista de Resolução CAMEX - Outras','2013-01-01',NULL),
	 (800,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70% (setenta por cento) - Tributada integralmente','2013-08-01',NULL),
	 (810,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70% (setenta por cento) - Tributada e com cobrança do ICMS por substituição tributária','2013-08-01',NULL),
	 (820,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70% (setenta por cento) - Com redução de base de cálculo','2013-08-01',NULL),
	 (830,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70% (setenta por cento) - Isenta ou não tributada e com cobrança do ICMS por substituição tributária','2013-08-01',NULL),
	 (840,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70% (setenta por cento) - Isenta','2013-08-01',NULL),
	 (841,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70% (setenta por cento) - Não tributada','2013-08-01',NULL),
	 (850,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70% (setenta por cento) - Suspensão','2013-08-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_cst_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 (851,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70% (setenta por cento) - Diferimento','2013-08-01',NULL),
	 (860,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70% (setenta por cento) - ICMS cobrado anteriormente por substituição tributária','2013-08-01',NULL),
	 (870,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70% (setenta por cento) - Com redução de base de cálculo e cobrança do ICMS por substituição tributária','2013-08-01',NULL),
	 (890,'Nacional, mercadoria ou bem com Conteúdo de Importação superior a 70% (setenta por cento) - Outras','2013-08-01',NULL) ON CONFLICT DO NOTHING;

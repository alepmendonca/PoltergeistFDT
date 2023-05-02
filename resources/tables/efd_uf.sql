DROP TABLE efd_uf;
CREATE TABLE efd_uf (
	codigo int NOT NULL,
	uf varchar NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS efd_uf_uf ON efd_uf USING btree (codigo);

INSERT INTO efd_uf (codigo,uf) VALUES
	 (12,'AC'),
	 (27,'AL'),
	 (16,'AP'),
	 (13,'AM'),
	 (29,'BA'),
	 (23,'CE'),
	 (53,'DF'),
	 (32,'ES'),
	 (52,'GO'),
	 (21,'MA') ON CONFLICT DO NOTHING;
INSERT INTO efd_uf (codigo,uf) VALUES
	 (51,'MT'),
	 (50,'MS'),
	 (31,'MG'),
	 (15,'PA'),
	 (25,'PB'),
	 (41,'PR'),
	 (26,'PE'),
	 (22,'PI'),
	 (33,'RJ'),
	 (24,'RN') ON CONFLICT DO NOTHING;
INSERT INTO efd_uf (codigo,uf) VALUES
	 (43,'RS'),
	 (11,'RO'),
	 (14,'RR'),
	 (42,'SC'),
	 (35,'SP'),
	 (28,'SE'),
	 (17,'TO') ON CONFLICT DO NOTHING;

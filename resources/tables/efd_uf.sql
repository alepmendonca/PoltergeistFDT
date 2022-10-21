CREATE TABLE IF NOT EXISTS efd_uf (
	codigo varchar NOT NULL,
	uf varchar NULL,
	dt_inicio varchar NOT NULL,
	dt_fim varchar NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS efd_uf_uf ON efd_uf USING btree (codigo);

INSERT INTO efd_uf (codigo,uf,dt_inicio,dt_fim) VALUES
	 ('12','AC','01012009',''),
	 ('27','AL','01012009',''),
	 ('16','AP','01012009',''),
	 ('13','AM','01012009',''),
	 ('29','BA','01012009',''),
	 ('23','CE','01012009',''),
	 ('53','DF','01012009',''),
	 ('32','ES','01012009',''),
	 ('52','GO','01012009',''),
	 ('21','MA','01012009','') ON CONFLICT DO NOTHING;
INSERT INTO efd_uf (codigo,uf,dt_inicio,dt_fim) VALUES
	 ('51','MT','01012009',''),
	 ('50','MS','01012009',''),
	 ('31','MG','01012009',''),
	 ('15','PA','01012009',''),
	 ('25','PB','01012009',''),
	 ('41','PR','01012009',''),
	 ('26','PE','01012009',''),
	 ('22','PI','01012009',''),
	 ('33','RJ','01012009',''),
	 ('24','RN','01012009','') ON CONFLICT DO NOTHING;
INSERT INTO efd_uf (codigo,uf,dt_inicio,dt_fim) VALUES
	 ('43','RS','01012009',''),
	 ('11','RO','01012009',''),
	 ('14','RR','01012009',''),
	 ('42','SC','01012009',''),
	 ('35','SP','01012009',''),
	 ('28','SE','01012009',''),
	 ('17','TO','01012009','') ON CONFLICT DO NOTHING;

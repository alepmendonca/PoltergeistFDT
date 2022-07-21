/** 
 * Altera nomes dos esquemas pra ficar mais legivel
 */
DO LANGUAGE PLPGSQL $$
DECLARE 
	esquema			RECORD;
	comando			TEXT := '';
BEGIN 
	<<esquemas>>
	FOR esquema IN EXECUTE
	    format(
	      'SELECT esquema.schema_name, %L || %L || cpf_cnpj || %L || to_char(datainicial, %L) as novonome FROM information_schema.schemata AS esquema, escrituracaofiscal AS efds WHERE schema_name = efds.nomebd',
	      'efd', '-', '-', 'yyyy-mm'
	    )
  	LOOP
		EXECUTE format('ALTER SCHEMA %I RENAME TO %I', esquema.schema_name, esquema.novonome);
	END LOOP esquemas;
END;
$$

/**
 * Elimina tabelas existentes
 */
DO LANGUAGE PLPGSQL $$
DECLARE 
	tabela			RECORD;
BEGIN 
	FOR tabela IN SELECT table_name FROM information_schema.columns c WHERE table_schema = current_schema() AND column_name = 'efd'
  	LOOP
		EXECUTE format('DROP TABLE %I', tabela.table_name);
	END LOOP;
END;
$$
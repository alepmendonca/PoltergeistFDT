-- Cria tabelas agregadoras de dados das EFDs 
DO LANGUAGE PLPGSQL $$
DECLARE
  nome 			TEXT := current_schema();
  tabela        RECORD;
  table_name   TEXT := '';
  esquema       RECORD;
  sql           TEXT := '';
  coluna        RECORD;
  coluna_schema RECORD;
  colunas_lst   TEXT := '';
  colunas_sch   TEXT := '';
  achou_tabela  TEXT := '';
  achou_coluna  TEXT := '';
  execucoes     INT := 0;
  insercoes     NUMERIC;
  colunas_new	CURSOR (tabela varchar) FOR
  	SELECT a.column_name, a.data_type FROM (
	     		SELECT DISTINCT ON (lower(coluna1.attname)) lower(coluna1.attname) AS column_name, coluna1.attnum AS ordinal_position, tipo1.typname AS data_type, min(c1.ato_cotepe) OVER (PARTITION BY coluna1.attname) AS ato_cotepe
	     		FROM pg_catalog.pg_namespace AS esquema1, pg_catalog.pg_class AS tabela1, pg_catalog.pg_attribute AS coluna1, pg_catalog.pg_type AS tipo1, escrituracaofiscal as c1
	     		WHERE esquema1.oid = tabela1.relnamespace AND coluna1.attrelid = tabela1.oid AND coluna1.atttypid = tipo1.oid AND coluna1.attnum > 0
	     		AND esquema1.nspname = 'efd-' || cnpj_auditoria() || '-' || to_char(c1.datainicial, 'yyyy-mm') 
	     		AND tabela1.relname = tabela
     		) a ORDER BY a.ato_cotepe, a.ordinal_position;
begin
  <<tabelas>>
  FOR tabela IN EXECUTE
    format(
        'SELECT DISTINCT table_name FROM information_schema.tables WHERE table_schema LIKE %L AND table_name LIKE %L',-- AND table_name NOT IN (SELECT table_name FROM information_schema.tables where table_schema = %L)',
        'efd-' || cnpj_auditoria() || '%', 'reg_%'--, nome
    )

  LOOP
      table_name := tabela.table_name;
      EXIT WHEN execucoes > 50;
      
      sql := '';
      SELECT to_regclass(table_name) INTO achou_tabela;
      CONTINUE WHEN achou_tabela IS NOT NULL;

      colunas_lst := '(';
      OPEN colunas_new(table_name);
      <<colunas_agregado>>
	  LOOP
	  	FETCH colunas_new INTO coluna;
	  	EXIT WHEN NOT FOUND;
	    colunas_lst := colunas_lst || coluna.column_name || ',';
      END LOOP colunas_agregado;
      
	  <<esquemas>>
	  FOR esquema IN EXECUTE
        format(
          'SELECT schema_name FROM information_schema.schemata, information_schema.tables WHERE schema_name LIKE %L and schema_name = table_schema and table_name = %L',
          'efd-' || cnpj_auditoria() || '%',
          table_name
        )
      LOOP
      	  colunas_sch = '';
	      MOVE BACKWARD ALL IN colunas_new;
	      <<colunas>>
		  LOOP
			FETCH colunas_new INTO coluna_schema;
			EXIT WHEN NOT FOUND;
			EXECUTE format('SELECT column_name FROM information_schema.columns WHERE table_schema = %L AND table_name = %L AND column_name = %L LIMIT 1',
				CASE WHEN achou_tabela IS NOT NULL THEN nome ELSE esquema.schema_name END, 
				table_name,
				coluna_schema.column_name
			) INTO achou_coluna;
		  	IF achou_coluna IS NOT NULL THEN
			    colunas_sch := colunas_sch || '"' || coluna_schema.column_name || '",';
			ELSE
			    colunas_sch := colunas_sch || 'NULL::' || coluna_schema.data_type || ',';
			END IF;
	      END LOOP colunas;
          sql := sql || 'SELECT ' || colunas_sch || format('''%s'' AS EFD FROM %I.%I UNION ALL ', esquema.schema_name, esquema.schema_name, table_name);
      END LOOP esquemas;
	  CLOSE colunas_new;
	  colunas_lst := colunas_lst || 'EFD)';

      sql := format('CREATE TABLE %I.%I %s AS ', nome, table_name, colunas_lst) || left(sql, -11);
      RAISE NOTICE 'Criando tabela %', table_name;
      execucoes := execucoes + 1;
      EXECUTE sql;
  END LOOP tabelas;
END;
$$
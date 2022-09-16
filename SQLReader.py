import datetime
import re

import pandas as pd
import psycopg2
from psycopg2 import sql
from pathlib import Path

import GeneralConfiguration
import GeneralFunctions


class QueryAnalysisException(Exception):
    pass


def _get_dtypes_from_oids(oids: list) -> list:
    oid_catalog = {
        20: 'BIGINT',
        23: 'BIGINT',
        25: 'TEXT',
        701: 'BIGINT',
        1042: 'TEXT',
        1043: 'TEXT',
        1082: 'DATE',
        1114: 'DATE',
        1700: 'NUMERIC'
    }
    dtypes = {
        'BIGINT': 'Int64',
        'BOOL': 'bool',
        'TEXT': 'object',
        'NUMERIC': 'float64',
        'DATE': 'datetime64[ns]'
    }
    try:
        return [dtypes[pg_tipo] for pg_tipo in [oid_catalog[oid] for oid in oids]]
    except KeyError as ex:
        raise QueryAnalysisException(f'Consulta no banco não soube verificar tipo de dados retornado'
                                     f' para o {oids.index(ex.args[0])}º argumento: {ex.args[0]}')


class SQLReader:
    def __init__(self, schema: str = None, config=GeneralConfiguration.get()):
        try:
            self._conn = psycopg2.connect(host=config.postgres_address, port=config.postgres_port,
                                          dbname=config.postgres_dbname,
                                          user=config.postgres_user, password=config.postgres_pass)
            self._cursor = self._conn.cursor()
            if schema:
                self._schema = schema.lower()
                self._cursor.execute(f"SET search_path = '{self._schema}', public;")
        except Exception as e:
            if str(e).find('Connection refused') >= 0:
                raise QueryAnalysisException('Conexão ao Postgres recusada. Verifique se ele está funcionando, '
                                             'usando as configurações definidas nas Propriedades.')
            else:
                GeneralFunctions.logger.exception(f'Erro no acesso ao banco de dados Postgres: {e}')
                raise e

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._cursor:
            self._cursor.close()
        if self._conn:
            self._conn.rollback()
            self._conn.close()

    def executa_consulta(self, query: str, quantidade=None, argumentos: tuple = None) -> (int, pd.DataFrame):
        try:
            self._cursor.execute(query, argumentos)
        except psycopg2.Error as e:
            raise Exception(e.pgerror)
        total = self._cursor.rowcount
        colunas = [coluna.name for coluna in self._cursor.description]
        oids = [coluna.type_code for coluna in self._cursor.description]
        dtypes = {coluna: dtype for coluna, dtype in zip(colunas, _get_dtypes_from_oids(oids))}
        if quantidade:
            resultado = self._cursor.fetchmany(quantidade)
        else:
            resultado = self._cursor.fetchall()
        df = pd.DataFrame(data=resultado, columns=colunas)
        df = df.astype(dtypes)
        return total, df

    def does_schema_exist(self, schema_name: str) -> bool:
        if not schema_name:
            return False
        try:
            self._cursor.execute('select 1 from information_schema.schemata where lower(schema_name)=%s;',
                                 (schema_name.lower(),))
        except psycopg2.Error as e:
            raise Exception(e.pgerror)
        return bool(len(self._cursor.fetchall()))

    def has_return_set(self, sql_string: str, sql_args: tuple = None) -> bool:
        try:
            self._cursor.execute(sql_string, sql_args)
        except psycopg2.Error as e:
            raise Exception(e.pgerror)
        return bool(len(self._cursor.fetchmany(size=1)))

    def does_table_exist(self, table_name: str) -> bool:
        return self.has_return_set('SELECT 1 FROM information_schema.tables '
                                   'WHERE table_schema = %s AND table_name = %s;',
                                   (self._schema, table_name))

    def is_efd_unified(self) -> bool:
        return self.does_table_exist('reg_k990')


class SQLWriter(SQLReader):
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._cursor:
            self._cursor.close()
        if self._conn:
            self._conn.commit()
            self._conn.close()

    def executa_transacao(self, query: str, sql_args: tuple = None):
        try:
            self._cursor.execute(query, sql_args)
        except psycopg2.Error as e:
            self._conn.rollback()
            raise Exception(e.pgerror)

    def drop_master_schema(self):
        if not self.does_schema_exist('master'):
            return
        self.executa_transacao('DROP SCHEMA master CASCADE;')
        self._conn.commit()

    def run_ddl(self, sql_script_name: str):
        scripts_path = Path('resources') / 'sql'
        self._cursor.execute((scripts_path / sql_script_name).open(mode='r', encoding='UTF-8').read())
        self._conn.commit()

    def import_dump_file(self, file: Path, temp_table: str):
        try:
            self._cursor.copy_expert(f"COPY {temp_table} FROM STDIN DELIMITER ',' CSV HEADER ENCODING 'UTF-8';",
                                     file.open(mode='r', encoding='UTF-8'))
            self._conn.commit()
        except psycopg2.errors.BadCopyFileFormat:
            raise QueryAnalysisException(f'Erro na importação do arquivo {str(file)}: ele está num formato '
                                         f'inesperado para importar na tabela temporária {temp_table}! '
                                         'Contatar desenvolvedor para corrigir!')

    def prepare_table_escrituracaofiscal(self):
        try:
            self._cursor.execute('DROP TABLE IF EXISTS escrituracaofiscal;')
            self._cursor.execute('CREATE TABLE escrituracaofiscal AS ' +
                                 'SELECT * FROM master.escrituracaofiscal ' +
                                 "WHERE cpf_cnpj LIKE '%' || cnpj_auditoria();")
            self._cursor.execute('ALTER TABLE escrituracaofiscal ' +
                                 'ALTER COLUMN cpf_cnpj TYPE char(14) USING cpf_cnpj::NUMERIC::varchar;')
            self._cursor.execute('ALTER TABLE escrituracaofiscal ALTER COLUMN ie TYPE int8 USING ie::int8;')
            self._conn.commit()
        except psycopg2.Error as e:
            self._conn.rollback()
            raise Exception(e.pgerror)

    def unify_efd_tables(self, cnpj: str, dicEfds: dict):
        novos_nomes_schemas = list(map(
            lambda efd: (efd['bd'], GeneralFunctions.efd_schema_name(cnpj, efd['referencia'])),
            dicEfds['efds']))
        try:
            for tupla in novos_nomes_schemas:
                if self.does_schema_exist(tupla[0]):
                    self._cursor.execute(
                        sql.SQL('ALTER SCHEMA {0} RENAME TO {1}').format(
                            sql.Identifier(tupla[0]), sql.Identifier(tupla[1])))
            self._conn.commit()
            self._cursor.execute(
                "SELECT table_name FROM information_schema.columns " +
                "WHERE table_schema = %s and column_name = 'efd'",
                (self._schema,))
            for tabela in self._cursor.fetchall():
                self._cursor.execute(f'DROP TABLE {tabela[0]};')
            self._conn.commit()
            qtd_tabelas = 0
            while not self.is_efd_unified():
                self.run_ddl("efd_unify_tables.sql")
                # script tem o número 50 definido para ir criando aos poucos,
                # e evitar dar um out of memory
                qtd_tabelas += 50
                GeneralFunctions.logger.info(f'Criadas {qtd_tabelas} tabelas de EFD no banco de dados central...')
            GeneralFunctions.logger.info('Todas as tabelas de EFD foram criadas no banco de dados central, '
                                         'ajustando tipos de dados e índices...')
            self.run_ddl("efd_alter_tables.sql")
            GeneralFunctions.logger.info('Apagando esquemas temporários de EFD no banco de dados central...')
            self._cursor.execute(
                "SELECT DISTINCT schema_name FROM information_schema.schemata, escrituracaofiscal "
                f"WHERE schema_name LIKE '%{int(cnpj)}%'")
            for esquema in self._cursor.fetchall():
                self._cursor.execute(f'DROP SCHEMA %s CASCADE', (esquema, ))
                self._conn.commit()
        except psycopg2.Error as e:
            self._conn.rollback()
            raise Exception(e.pgerror)

    def create_efd_schema(self, schema_name: str, sql_file: Path):
        try:
            self._cursor.execute(f'CREATE SCHEMA {schema_name}')
            self._cursor.execute(f'SET search_path = {schema_name};')
            script = sql_file.open(mode='r').read()
            # remove a parte de scripting que atrapalha no PGSql
            script = script.replace('SET @saved_cs_client     = @@character_set_client;', '')
            script = script.replace('SET character_set_client = utf8;', '')
            script = script.replace('SET character_set_client = @saved_cs_client;', '')
            script = script.replace('collate latin1_general_ci', '')
            # incongruências de tipagem entre MySQL e PGSql
            script = re.sub(r'bigint\(\d+\)', 'numeric', script)
            script = re.sub(r'int\(\d+\)', 'integer', script)
            script = script.replace('varchar(255)', 'varchar(1000)')
            script = script.replace('unsigned', '')
            # remove as criações de indices, depois cria nas tabelas centralizadas
            script = re.sub(r',\s+KEY.*\),', ',', script)
            script = re.sub(r',\s+KEY.*\)', '', script)
            script = script.replace('DROP TABLE', 'COMMIT;\nDROP TABLE')
            self._cursor.execute(script)
            self._conn.commit()
        except psycopg2.Error as e:
            self._conn.rollback()
            raise Exception(e.pgerror)

    def create_audit_schema(self, schema_name: str, cnpj: str, ie: int, inicio: datetime.date, fim: datetime.date):
        # TODO fazer a criação de todas as tabelas pra não dar erros nas queries
        try:
            self._cursor.execute(f'CREATE SCHEMA IF NOT EXISTS {schema_name};')
            self._cursor.execute(f'SET search_path = {schema_name}, public;')
            self._cursor.execute("CREATE OR REPLACE FUNCTION cnpj_auditoria() RETURNS varchar AS " +
                                 f"$$ SELECT '{int(cnpj)}' $$ LANGUAGE SQL IMMUTABLE;")
            self._cursor.execute("CREATE OR REPLACE FUNCTION ie_auditoria() RETURNS bigint AS " +
                                 f"$$ SELECT {ie} $$ LANGUAGE SQL IMMUTABLE;")
            self._cursor.execute("CREATE OR REPLACE FUNCTION inicio_auditoria() RETURNS date AS " +
                                 f"$$ SELECT '{inicio.strftime('%d-%m-%Y')}'::DATE $$ LANGUAGE SQL IMMUTABLE;")
            self._cursor.execute("CREATE OR REPLACE FUNCTION fim_auditoria() RETURNS date AS " +
                                 f"$$ SELECT '{fim.strftime('%d-%m-%Y')}'::DATE $$ LANGUAGE SQL IMMUTABLE;")
            self._conn.commit()
        except psycopg2.Error as e:
            self._conn.rollback()
            raise Exception(e.pgerror)


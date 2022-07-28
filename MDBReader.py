import datetime
import re

import pyodbc
import pandas as pd
from GeneralFunctions import logger
from pathlib import Path


class MDBReader:
    def __init__(self):
        drivers = [x for x in pyodbc.drivers() if x == 'Microsoft Access Driver (*.mdb)']
        if len(drivers) == 0:
            logger.critical(
                'Não encontrei o driver ODBC pra Access de 32-bits! ' \
                'Pode ser que esteja rodando Python 64bits, ' \
                'ou pode ser que não esteja instalado o ODBC Access antigo!')
            raise Exception('Impossível ler banco de dados do AIIM2003')

        path = Path.home() / 'Documents'
        # serve para pegar a última versão instalada do AIIM 2003 ICMS
        mdb = sorted(path.glob('*ICMS/Aiim.mdb'), reverse=True)[0]
        pwd = 'c4e1s3s2'
        url_con = 'DRIVER={};DBQ={};PWD={}'.format(drivers[0], mdb, pwd)
        logger.debug(f'Conectando ao Access do AIIM2003 existente em {mdb}')

        # connect to db
        self.con = pyodbc.connect(url_con)
        self.cur = self.con.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cur:
            self.cur.close()
        if self.con:
            self.con.close()

    def get_last_selic_stored(self):
        resultado = self.cur.execute('select max(anomes) from selic;').fetchone()[0]
        return datetime.date(int(resultado[:4]), int(resultado[-2:]), 1)

    def insert_selics(self, df: pd.DataFrame):
        for mes, valor in df.iterrows():
            self.cur.execute('insert into selic (AnoMes, Valor) values (?,?);', f'{mes.year}{mes.month:02}', valor['selic'])
            logger.info(f'Cadastrada SELIC de {mes.strftime("%m/%Y")}: {valor["selic"]}')
        self.cur.commit()

    def get_last_ufesp_stored(self):
        return self.cur.execute('select valor from ufesp where data in (select max(data) from ufesp);').fetchone()[0]

    def get_year_of_last_ufesp_stored(self):
        resultado = self.cur.execute('select max(data) from ufesp;').fetchone()[0]
        return resultado.year

    # Retorna a posição do AIIM na lista de consulta do AIIM2003
    # Se retornar zero, AIIM não foi localizado
    def get_aiim_position(self, aiim_number: int) -> int:
        exists = self.cur.execute(f'select 1 from Auto where Numero=?;', aiim_number)
        if len(exists.fetchall()) != 1:
            return 0
        return self.cur.execute(
            f'select count(*) from Auto where Numero>=?;', aiim_number).fetchone()[0]

    def is_aiim_open_to_edition(self, aiim_number: int) -> bool:
        result = self.cur.execute(f'select Impressao_Relato from Auto where Numero=?;', aiim_number).fetchone()
        return result is None or not bool(result[0])

    # Retorna o ID do último item criado pro AIIM
    # Melhor usar ID que o número do item, que pode mudar se mexer na ordem dos itens
    def get_last_aiim_item_created(self, aiim_number: int) -> int:
        valor = self.cur.execute(
            f'select max(item.id_auto_item) from auto_item as item, Auto '
            f'where item.id_Auto = Auto.id_Auto '
            f'and Auto.Numero=?;', aiim_number).fetchall()
        if len(valor) == 0:
            return 0
        else:
            return valor[0][0]

    # Retorna AIIMs em aberto relacionados a uma OSF
    def get_aiims_for_osf(self, osf: str) -> list:
        valores = self.cur.execute(
            f'select numero, serie from Auto '
            f'where OF_Exp = ? '
            f'and Impressao_Relato = 0;', osf
        ).fetchall()
        return [f'{numero:7_.0f}-{serie}'.replace('_', '.') for numero, serie in valores]

    def insert_operations(self, aiim_number: int, operations: pd.DataFrame):
        auto_id = self.cur.execute('select id_auto from Auto where numero = ?;', aiim_number).fetchone()[0]
        self.cur.execute('delete from valor_total_operacoes where id_auto = ?;', auto_id)
        i = 0
        for index, op in operations.iterrows():
            self.cur.execute('insert into valor_total_operacoes (id_auto, anomes, valor_total_operacoes) '
                             'values (?, ?, ?);',
                             auto_id, str(op[1]) + str(op[0]).zfill(2),
                             float(op[2].replace('.', '').replace(',', '.')))
            logger.info(f'Cadastrada operação de {index.date()} do AIIM {aiim_number} no AIIM2003')
            i += 1
            if i == 12:
                break
        self.cur.commit()

    def insert_observations(self, aiim_number: int, observations: list[str]):
        auto_id = self.cur.execute('select id_auto from Auto where numero = ?;', aiim_number).fetchone()[0]
        self.cur.execute('delete from Auto_Observacao where id_Auto = ?;', auto_id)
        sql = 'insert into Auto_Observacao (id_Auto, Descricao) values (?, ?);'
        self.cur.setinputsizes([(pyodbc.SQL_INTEGER,), (pyodbc.SQL_LONGVARCHAR,)])
        self.cur.executemany(sql, [(auto_id, obs) for obs in observations])
        self.cur.commit()
        logger.info(f'Cadastradas observações do AIIM {aiim_number} no AIIM2003')

    def is_sonegation_aiim(self, aiim_number: int) -> bool:
        valor = self.cur.execute(
            f"select Sonegacao from Auto where Auto.Numero=?;", aiim_number).fetchall()
        if len(valor) == 0:
            return False
        else:
            return bool(valor[0][0])

    # TODO pesquisa de teste apenas
    def get_relatos(self, inciso, alinea) -> list:
        return self.cur.execute(
            f'select cap.cd_item_obra, cap.legislacaoespecial, item.relato '
            f'from auto_item item, multa, alinea, inciso, artigo, auto_cap_infra_ttp cap '
            f'where item.id_multa = multa.id_multa '
            f'and multa.id_alinea = alinea.id_alinea '
            f'and alinea.id_inciso = inciso.id_inciso '
            f'and inciso.id_artigo = artigo.id_artigo '
            f'and item.id_auto_item = cap.id_auto_item '
            f'and inciso.inciso = ? and alinea.alinea = ?;', inciso, alinea
        ).fetchall()

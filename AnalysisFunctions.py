import os
import re
import time
from datetime import date
from datetime import datetime
from datetime import timedelta

import numpy as np
import pandas as pd

# Arquivo com funções a serem chamadas por "reflexão"
# Apenas serão chamadas quando tiver um arquivo em resources/verificacoes
# em que tenha um atributo chamado "funcao", com um dicionário da forma abaixo
# sendo que "nome" é o nome de uma função no presente modulo
# A função não tem argumentos, e deve retornar uma tupla: (quantidade registros, dataframe com o resultado)
#
# Ex: "funcao": {
#       "nome": "verifica_omissao_efds",
#       "descricao": "texto que aparece na tela de análises"
#   }
#
# É necessário também criar uma função com mesmo nome, mas final "_ddf", que
# recebe uma lista com valores gerados pala função principal e
# retorna um DDF apropriado para inserção no AIIM2003
import requests

import Audit
import Controller
import GeneralFunctions
import WebScraper
from Audit import get_current_audit
from ConfigFiles import Infraction
from SQLReader import SQLWriter
from WebScraper import SeleniumWebScraper


class AnalysisFunctionException(Exception):
    pass


def verifica_omissao_efds() -> (int, pd.DataFrame):
    periodos_fiscalizacao = get_current_audit().get_periodos_da_fiscalizacao()
    periodos_com_EFD = []
    regex = re.compile(r'SpedEFD-\d{14}-ie_clean-\d{1}-(\d{6}).*\.txt$'.replace('ie_clean',
                                                                                get_current_audit().ie_only_digits()))
    for _, _, arquivos in os.walk(os.path.join(get_current_audit().path(), 'Dados')):
        for arquivo in arquivos:
            achado = regex.match(arquivo)
            if achado:
                periodos_com_EFD.append(datetime.strptime(achado.group(1) + '01', '%Y%m%d').date())

    omissos = []
    for periodo_fiscalizacao in periodos_fiscalizacao:
        for referencia in pd.date_range(periodo_fiscalizacao[0], periodo_fiscalizacao[1], freq='MS'):
            if referencia.date() not in periodos_com_EFD:
                omissos.append(referencia)
    df = pd.DataFrame(omissos, columns=['Referencia'])
    return len(omissos), df


def verifica_omissao_efds_ddf(infraction: Infraction, df: pd.DataFrame) -> pd.DataFrame:
    if infraction.filename.find('LRI') >= 0 or (infraction.nome is not None and infraction.nome.find('LRI') >= 0):
        anos = GeneralFunctions.get_dates_from_df(df, freq='Y')
        return pd.DataFrame({'Livros': ['1'], 'Meses': [str(len(anos))]})
    else:
        return pd.DataFrame({'Livros': ['1'], 'Meses': [str(len(df))]})


def periodo_sn_lri() -> (int, pd.DataFrame):
    periodos_fiscalizacao = get_current_audit().get_periodos_da_fiscalizacao(rpa=False)
    omissos = []
    for periodo_fiscalizacao in periodos_fiscalizacao:
        for referencia in pd.date_range(periodo_fiscalizacao[0], periodo_fiscalizacao[1], freq='Y'):
            omissos.append(referencia.replace(month=2, day=28))
    df = pd.DataFrame(omissos, columns=['Referencia'])
    return len(omissos), df


def periodo_sn_lri_ddf(infraction: Infraction, df: pd.DataFrame) -> pd.DataFrame:
    return verifica_omissao_efds_ddf(infraction, df)


def verifica_divergencia_pgdas() -> (int, pd.DataFrame):
    periodos_fiscalizacao = get_current_audit().get_periodos_da_fiscalizacao(rpa=False)
    periodos = None
    for i in [pd.date_range(p[0], p[1], freq='M') for p in periodos_fiscalizacao]:
        if periodos is None:
            periodos = i
        else:
            periodos = periodos.union(i)
    periodos = periodos.to_series(name='Referência')

    planilha_divergencias = pd.read_excel(
        os.path.join(get_current_audit().path(), 'Dados',
                     Controller.launchpad_download_filename("SN-Receita Bruta Declarada x Apurada")),
        sheet_name='RB DECL x RB APURADA - ANÁLISE')
    planilha_divergencias = planilha_divergencias.iloc[:, [2, 3, 5, 7, 9, 12, 13]]
    planilha_divergencias.columns = ['Referência', 'Receita Declarada - Mercado Interno',
                                     'Receita Declarada - Mercado Externo',
                                     'Receita Apurada - Mercado Interno',
                                     'Receita Apurada - Mercado Externo',
                                     'Divergências - Mercado Interno',
                                     'Divergências - Mercado Externo']
    planilha_divergencias = planilha_divergencias[planilha_divergencias['Referência'].map(lambda ref: type(ref) == int)]
    planilha_divergencias['Referência'] = planilha_divergencias['Referência'].apply(
        lambda r: GeneralFunctions.last_day_of_month(datetime.strptime(str(r), '%Y%m')))
    planilha_divergencias = planilha_divergencias.merge(periodos, on='Referência')
    planilha_divergencias = planilha_divergencias[
        (planilha_divergencias['Divergências - Mercado Interno'] < 0) |
        (planilha_divergencias['Divergências - Mercado Externo'] < 0)
        ]
    planilha_divergencias.iloc[:, 1:] = planilha_divergencias.iloc[:, 1:].astype(np.float64)
    planilha_divergencias = planilha_divergencias.reset_index()
    return len(planilha_divergencias), planilha_divergencias.iloc[:, 1:]


def verifica_divergencia_pgdas_ddf(infraction: Infraction, df: pd.DataFrame) -> pd.DataFrame:
    # nao foi feito nada com relação a este caso, por ser SN
    return pd.DataFrame()


# busca na base da RFB os dados básicos dos CNPJs fora do Cadesp,
# e levanta no Portal do SN os períodos em que foram enquadrados
# grava tudo nas tabelas cnpj e cnpj_regime
def levanta_consumidores_finais(query: pd.DataFrame):
    try:
        cnpjs_sem_informacao = query.iloc[:, [6, 9]]
        cnpjs_sem_informacao = cnpjs_sem_informacao.drop_duplicates()
        cnpjs_sem_informacao = cnpjs_sem_informacao[cnpjs_sem_informacao['CNAE'].isna()].iloc[:, 0]
        cnpjs_sem_informacao = list(cnpjs_sem_informacao.apply(lambda cnpj: str(int(re.sub(r'[^\d]', '', cnpj)))))

        if not cnpjs_sem_informacao:
            return

        GeneralFunctions.logger.info('Levantando informações das empresas da base do CNPJ')
        for cnpj in cnpjs_sem_informacao:
            # prineiro, busca dados do CNPJ
            with SQLWriter(database=Audit.get_current_audit().database,
                           schema=Audit.get_current_audit().schema) as postgres:
                if not postgres.has_return_set('select 1 from cnpj where cnpj = %s;', (cnpj,)):
                    GeneralFunctions.logger.info(f'Buscando informações da empresa {cnpj} na base do CNPJ ('
                                                 f'{cnpjs_sem_informacao.index(cnpj) + 1}/{len(cnpjs_sem_informacao)}')
                    try:
                        resposta = WebScraper.get_cnpj_data(cnpj.zfill(14))
                    except requests.exceptions.HTTPError as excesso:
                        if excesso.response.reason == 'Too Many Requests':
                            GeneralFunctions.logger.warning(
                                'Esperando 1 min para continuar os acessos à consulta de CNPJ...')
                            time.sleep(60)
                            resposta = WebScraper.get_cnpj_data(cnpj)
                        else:
                            raise excesso
                    postgres.executa_transacao("""
                        INSERT INTO CNPJ (CNPJ, RAZAO_SOCIAL, INICIO_ATIVIDADES, SITUACAO, INICIO_SITUACAO, UF)
                        VALUES (%s, %s, %s::DATE, %s, %s::DATE, %s)
                        ON CONFLICT (CNPJ) DO 
                            UPDATE SET RAZAO_SOCIAL = EXCLUDED.RAZAO_SOCIAL, SITUACAO = EXCLUDED.SITUACAO, 
                                INICIO_SITUACAO = EXCLUDED.INICIO_SITUACAO, UF = EXCLUDED.UF 
                    """, (cnpj, resposta['nome'], resposta['abertura'], resposta['situacao'],
                          resposta['data_situacao'], resposta['uf']))
                    cnae_principal = int(re.sub(r'[.-]', '', resposta['atividade_principal'][0]['code']))
                    postgres.executa_transacao('DELETE FROM CNPJ_CNAE WHERE CNPJ = %s', (cnpj,))
                    if cnae_principal > 0:
                        postgres.executa_transacao(
                            'INSERT INTO CNPJ_CNAE (CNPJ, CNAE, PRINCIPAL) VALUES (%s, %s, %s)',
                            (cnpj, cnae_principal, True))
                    for secundario in resposta['atividades_secundarias']:
                        cnae_secundario = int(re.sub(r'[.-]', '', secundario['code']))
                        if cnae_secundario > 0:
                            postgres.executa_transacao(
                                'INSERT INTO CNPJ_CNAE (CNPJ, CNAE, PRINCIPAL) VALUES (%s, %s, %s) '
                                'ON CONFLICT DO NOTHING',
                                (cnpj, cnae_secundario, False))
    except (IOError, requests.exceptions.HTTPError):
        GeneralFunctions.logger.exception('Falha na consulta de CNPJ na base da RFB')
        raise AnalysisFunctionException('Falha na consulta de CNPJ na base da RFB')

    try:
        # depois, busca dados do Simples Nacional
        GeneralFunctions.logger.info(
            'Levantando histórico do Simples Nacional das empresas que podem ser consumidoras finais')
        retorno = []
        with SeleniumWebScraper(None) as ws:
            retorno = ws.consulta_historico_simples_nacional(cnpjs_sem_informacao)
        GeneralFunctions.logger.info('Inserindo históricos do SN e RPA das empresas que podem ser consumidoras finais')
        with SQLWriter(database=Audit.get_current_audit().database,
                       schema=Audit.get_current_audit().schema) as postgres:
            for cnpj in cnpjs_sem_informacao:
                postgres.executa_transacao('DELETE FROM cnpj_regime WHERE cnpj = %s and fim_regime IS NULL', (cnpj,))
            for historico in retorno:
                if historico['fim']:
                    postgres.executa_transacao("INSERT INTO cnpj_regime (cnpj, regime, inicio_regime, fim_regime)"
                                               " VALUES (%s, 'Simples Nacional', %s::DATE, %s::DATE) "
                                               "ON CONFLICT DO NOTHING",
                                               (historico['cnpj'], historico['inicio'], historico['fim']))
                else:
                    postgres.executa_transacao("INSERT INTO cnpj_regime (cnpj, regime, inicio_regime)"
                                               " VALUES (%s, 'Simples Nacional', %s::DATE)",
                                               (historico['cnpj'], historico['inicio'], historico['fim']))
            # realiza acerto de "furos" no histórico
            for cnpj in cnpjs_sem_informacao:
                _, df = postgres.executa_consulta("""
                        SELECT inicio_atividades, inicio_regime, fim_regime 
                        FROM cnpj LEFT JOIN cnpj_regime ON cnpj.cnpj = cnpj_regime.cnpj
                        WHERE cnpj.cnpj = %s 
                        ORDER BY inicio_regime
                    """, argumentos=(cnpj,))
                ultimo_inicio = None
                ultimo_fim = None
                inicio_atividades = None
                for _, row in df.iterrows():
                    inicio_atividades = row['inicio_atividades'].date()
                    if row['inicio_regime'] is not pd.NaT:
                        inicio_regime = row['inicio_regime'].date()
                        if ultimo_inicio is None and inicio_regime > inicio_atividades:
                            postgres.executa_transacao(
                                "INSERT INTO cnpj_regime (cnpj, regime, inicio_regime, fim_regime) "
                                "VALUES (%s, 'RPA', %s::DATE, %s::DATE) ON CONFLICT DO NOTHING",
                                (cnpj, inicio_atividades.strftime('%d/%m/%Y'),
                                 (inicio_regime + timedelta(-1)).strftime('%d/%m/%Y')))
                        elif ultimo_fim and ultimo_fim.date() + timedelta(1) < inicio_regime:
                            postgres.executa_transacao(
                                "INSERT INTO cnpj_regime (cnpj, regime, inicio_regime, fim_regime) "
                                "VALUES (%s, 'RPA', %s::DATE, %s::DATE) ON CONFLICT DO NOTHING",
                                (cnpj, (ultimo_fim.date() + timedelta(1)).strftime('%d/%m/%Y'),
                                 (inicio_regime + timedelta(-1)).strftime('%d/%m/%Y')))
                        ultimo_inicio = inicio_regime
                        ultimo_fim = row['fim_regime']
                if ultimo_fim:
                    postgres.executa_transacao("""
                        INSERT INTO cnpj_regime (cnpj, regime, inicio_regime)
                        VALUES (%s, 'RPA', %s::DATE) ON CONFLICT DO NOTHING""",
                                               (cnpj, (ultimo_fim.date() + timedelta(1)).strftime('%d/%m/%Y')))
                elif not ultimo_inicio and not ultimo_fim:
                    postgres.executa_transacao("""
                        INSERT INTO cnpj_regime (cnpj, regime, inicio_regime)
                        VALUES (%s, 'RPA', %s::DATE) ON CONFLICT DO NOTHING""",
                                               (cnpj, inicio_atividades.strftime('%d/%m/%Y')))
    except Exception:
        GeneralFunctions.logger.exception('Falha na consulta de histórico no portal do Simples Nacional')
        raise AnalysisFunctionException('Falha na consulta de histórico no portal do Simples Nacional')


def verifica_notificacao_atraso_efd() -> dict:
    with SeleniumWebScraper() as ws:
        data_entrega = ws.consulta_dec_existe_notificacao(get_current_audit().cnpj_only_digits(),
                                                          categoria='Notificação', tributo='ICMS',
                                                          tipo='Fiscalização',
                                                          assunto='Advertência para Escrituração Fiscal Digital (EFD)',
                                                          data_inicial='01/02/2016')
    if data_entrega:
        return {'decisão': 'Infração', 'mensagem': 'Contribuinte já recebeu aviso para não entregar EFD em atraso, '
                                                   'nos termos do Ofício Circular 03/2016.\n'
                                                   f'Aviso entregue em {data_entrega}, considerar para AIIM '
                                                   f'apenas períodos posteriores.'}
    else:
        return {'decisão': 'Notificação', 'mensagem': 'Contribuinte nunca recebeu um aviso para não entregar EFD em '
                                                      'atraso, nos termos do Ofício Circular 03/2016.\n'
                                                      'Apenas envie a notificação, não será gerada infração.'}

import concurrent
import concurrent.futures
import os
import re
import subprocess
import threading
import time
import zipfile

import pandas as pd
import PySimpleGUI as sg

from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from datetime import date
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from pathlib import Path

import Audit
import CSVProcessing
import GUIFunctions
import GeneralConfiguration
import GeneralFunctions
import MDBReader
import PDFExtractor
import WordReport
import WebScraper

from AIIMAutoIt import AIIMAutoIt
from CSVProcessing import CSVProcessingMissingPrerequisite
from ConfigFiles import Analysis, Infraction
from Audit import AiimItem, PossibleInfraction, get_current_audit
from EFDPVAReversed import EFDPVAReversed, EFDPVAInstaller
from SQLReader import SQLReader, SQLWriter, QueryAnalysisException
from GeneralFunctions import logger
from WebScraper import SeleniumWebScraper, launchpad_report_options

LAUNCHPAD_REPORT_WITHOUT_BREAKS = 1000

data_groups = {
    'EFD': {'nome': 'EFD', 'progressos': [
        ('DOWNLOAD', 'Download Arquivos Digitais'),
        ('PVA', 'Importação no EFD PVA ICMS-IPI'),
        ('BD', 'Importação no Banco de Dados'),
        ('UNIFY', 'Unificação das EFDs no Banco de Dados')
    ]},
    'GIA': {'nome': 'GIA', 'progressos': [
        ('DOWNLOAD', 'Download Launchpad'),
        ('IMPORT', 'Importação no Banco de Dados')
    ]},
    'COMEX': {'nome': 'SISCOMEX', 'progressos': [
        ('DOWNLOAD', 'Download Launchpad'),
        ('IMPORT', 'Importação no Banco de Dados')
    ]},
    'Cartao': {'nome': 'Administradoras de Cartões', 'progressos': [
        ('DOWNLOAD', 'Download Launchpad'),
        ('IMPORT', 'Importação no Banco de Dados')
    ]},
    'CTe': {'nome': 'Conhecimento de Transporte', 'progressos': [
        ('DOWNLOAD', 'Download Launchpad'),
        ('IMPORT', 'Importação no Banco de Dados')
    ]},
    'NFeDest': {'nome': 'NF-e Destinatário', 'progressos': [
        ('DOWNLOAD', 'Download Launchpad'),
        ('IMPORT', 'Importação no Banco de Dados')
    ]},
    'NFeEmit': {'nome': 'NF-e Emitente', 'progressos': [
        ('DOWNLOAD', 'Download Launchpad'),
        ('IMPORT', 'Importação no Banco de Dados')
    ]},
    'NFeDestItens': {'nome': 'NF-e Destinatário - Itens', 'progressos': [
        ('DOWNLOAD', 'Download Launchpad'),
        ('IMPORT', 'Importação no Banco de Dados')
    ]},
    'NFeEmitItens': {'nome': 'NF-e Emitente - Itens', 'progressos': [
        ('DOWNLOAD', 'Download Launchpad'),
        ('IMPORT', 'Importação no Banco de Dados')
    ]},
    'SAT': {'nome': 'SAT Cupom', 'progressos': [
        ('DOWNLOAD', 'Download Launchpad'),
        ('IMPORT', 'Importação no Banco de Dados')
    ]},
    'SATItens': {'nome': 'SAT Cupom - Itens', 'progressos': [
        ('DOWNLOAD', 'Download Launchpad'),
        ('IMPORT', 'Importação no Banco de Dados')
    ]},
    'SN': {'nome': 'Simples Nacional - Dados', 'progressos': [
        ('DOWNLOAD', 'Download Launchpad'),
        ('IMPORT', 'Importação no Banco de Dados')
    ]}
}
dadosAFR = {}
is_downloading_reports = False


class AIIMGeneratorUserWarning(Exception):
    pass


def get_dados_osf():
    if get_current_audit():
        return get_current_audit().get_dados_osf()
    return {}


def get_local_dados_osf_up_to_date_with_aiim2003():
    if get_current_audit().aiim_number:
        with MDBReader.AIIM2003MDBReader() as aiim2003:
            is_open = aiim2003.is_aiim_open_to_edition(get_current_audit().aiim_number_no_digit())
            get_current_audit().is_aiim_open = is_open
    get_current_audit().save()


def update_dados_osf(osf: str):
    osf_file = get_current_audit().path() / 'OSF Completa.pdf'
    if not osf_file.is_file():
        if osf is None:
            logger.error('Não foi informado número da OSF para buscar, busca cancelada.')
            return
        logger.info('Não foi localizada OSF completa, baixarei do PGSF')
        with SeleniumWebScraper(get_current_audit().path(), hidden=True) as ws:
            ws.get_full_OSF(osf, 'OSF Completa.pdf')

    logger.info('Capturando dados da Ordem de Serviço Fiscal...')
    linhas = PDFExtractor.parse_pdf(osf_file)

    # inicio e fim fiscalizacao podem simplesmente não estar na OSF
    inicio_auditoria = fim_auditoria = None
    if linhas.index('Até:') >= 0 and re.match(r'\d{2}/\d{4}', linhas[linhas.index('Até:') + 1]):
        inicio_auditoria = linhas[76]
        fim_auditoria = linhas[77]
    else:
        for linha in linhas[linhas.index('Origem do Trabalho Fiscal:'):linhas.index('OBSERVAÇÕES')]:
            periodo = re.match(r'.*(\d{2}/\d{4}).*(\d{2}/\d{4})', linha)
            if periodo:
                if int(periodo.group(1)[:2]) <= 12 and int(periodo.group(1)[3:]) > 2000 \
                        and int(periodo.group(2)[:2]) <= 12 and int(periodo.group(2)[3:]) > 2000 \
                        and datetime.strptime(periodo.group(1), '%m/%Y') <= datetime.strptime(periodo.group(2),
                                                                                              '%m/%Y'):
                    inicio_auditoria = periodo.group(1)
                    fim_auditoria = periodo.group(2)
                    break

    audit = Audit.get_current_audit()
    audit.osf = linhas[1]
    audit.empresa = linhas[24]
    audit.logradouro = linhas[25]
    audit.numero = linhas[29]
    audit.bairro = linhas[26]
    audit.cidade = linhas[27]
    audit.cep = linhas[28]
    audit.ie = linhas[30].strip()
    audit.cnpj = linhas[31].strip()
    audit.cnae = linhas[35]
    if inicio_auditoria:
        audit.inicio_auditoria = inicio_auditoria
        audit.fim_auditoria = fim_auditoria

    baixaCadesp = False
    cadesp_file = get_current_audit().path() / 'Cadesp.pdf'
    if not cadesp_file.is_file():
        baixaCadesp = True
        logger.info('Vai baixar extrato do Cadesp do contribuinte, para verificar endereço atual completo')
    else:
        ti_m = cadesp_file.stat().st_mtime
        if (time.time() - ti_m) / 60 / 60 / 24 >= 30:
            baixaCadesp = True
            logger.info('Vai baixar de novo extrato do Cadesp do contribuinte, '
                        'última vez que viu faz mais de 30 dias...')

    if baixaCadesp:
        with SeleniumWebScraper(get_current_audit().path()) as ws:
            ws.get_full_cadesp(get_current_audit().ie, cadesp_file)

    logger.info('Capturando dados do PDF com extrato do Cadesp...')
    linhas = PDFExtractor.parse_pdf(cadesp_file)

    audit = get_current_audit()
    audit.inicio_situacao = [s for s in linhas if 'Início da Situação' in s][0][-10:]
    audit.empresa = [s for s in linhas if 'Nome Empresarial' in s][-1][17:]
    audit.situacao = [s for s in linhas if s.startswith('Situação:')][-1][9:].strip()
    audit.inicio_inscricao = [s for s in linhas if 'Data da Inscrição no Estado' in s][0][-10:]
    audit.logradouro = linhas[linhas.index('Endereço do Estabelecimento') + 2][11:]
    audit.numero = linhas[linhas.index('Endereço do Estabelecimento') + 3][3:]
    audit.complemento = linhas[linhas.index('Endereço do Estabelecimento') + 4][12:].strip()
    audit.bairro = linhas[linhas.index('Endereço do Estabelecimento') + 6][7:].strip()
    audit.cidade = linhas[linhas.index('Endereço do Estabelecimento') + 11][10:].strip()
    audit.uf = linhas[linhas.index('Endereço do Estabelecimento') + 12][3:].strip()
    audit.cep = linhas[linhas.index('Endereço do Estabelecimento') + 5][4:].strip()

    historicos_txt = linhas[linhas.index('Histórico de Regime Estadual') + 7:
                            linhas.index('Histórico de Participantes') - 1]
    historicos = []
    for idx in range(0, len(historicos_txt), 5):
        inicio = historicos_txt[idx]
        fim = historicos_txt[idx + 1]
        regime = historicos_txt[idx + 2]
        historicos.append([inicio, fim, regime])
    audit.historico_regime = historicos
    get_current_audit().save()
    logger.info('Dados da fiscalização extraídos dos sistemas com sucesso!')

    if get_current_audit().is_aiim_open and is_aiim_on_AIIM2003():
        logger.info('Atualizando dados do contribuinte no AIIM...')
        AIIMAutoIt().atualiza_aiim(get_current_audit().aiim_number,
                                   __get_aiim_position_in_aiim2003(get_current_audit().aiim_number),
                                   get_current_audit())


def is_aiim_on_AIIM2003() -> bool:
    try:
        __get_aiim_position_in_aiim2003(get_current_audit().aiim_number)
    except AIIMNotExistsException:
        return False
    return True


def get_aiims_for_osf() -> list:
    with SeleniumWebScraper(hidden=True) as ws:
        return ws.get_aiims_for_osf(get_current_audit().osf)


def generate_aiim_number(osf: str) -> str:
    with SeleniumWebScraper(hidden=True) as ws:
        return ws.create_aiim_for_osf(osf)


def get_notification_data_for_analysis(analysis: Analysis):
    return [v for v in get_current_audit().notificacoes if v.verificacao == analysis][0]


def print_sheet(notification: PossibleInfraction, max_size: int = 0) -> list[Path]:
    pdf_path = Path('tmp') / (notification.verificacao.notification_attachments + '.pdf')
    pdf_path = pdf_path.absolute()
    get_current_audit().get_sheet().imprime_planilha(notification.planilha, pdf_path)
    paths = PDFExtractor.split_pdf(pdf_path, max_size)
    if notification.planilha_detalhe is not None:
        pdf_path = Path('tmp') / f'{notification.verificacao.notification_attachments}-detalhe.pdf'
        pdf_path = pdf_path.absolute()
        get_current_audit().get_sheet().imprime_planilha(notification.planilha_detalhe, pdf_path)
        paths.extend(PDFExtractor.split_pdf(pdf_path, max_size))
    return paths


def print_sheet_and_open(notification: PossibleInfraction):
    try:
        pdf_paths = print_sheet(notification)
        for pdf_path in pdf_paths:
            subprocess.Popen(f"{GeneralFunctions.get_default_windows_app('.pdf')} {pdf_path}")
    except Exception as e:
        logger.exception('Falha na criação e abertura de PDF')
        raise e


def send_notification(notification: PossibleInfraction, title: str, contents: str):
    try:
        logger.info('Gerando textos para notificação...')
        titulo_ajustado = notification.notificacao_titulo(title)
        conteudo_ajustado = notification.notificacao_corpo(contents)
        anexos_paths: list = []
        dec_num: str
        if notification.verificacao.has_notification_any_attachments():
            # DEC tem limitação de anexos de 5Mb
            logger.info('Gerando anexos da notificação...')
            anexos_paths = print_sheet(notification, 5)
        with SeleniumWebScraper(Path.home()) as ws:
            if notification.verificacao.notification_subject:
                dec_num = ws.send_notification(get_current_audit().cnpj, titulo_ajustado,
                                               conteudo_ajustado, anexos_paths,
                                               assunto=notification.verificacao.notification_subject)
            else:
                dec_num = ws.send_notification(get_current_audit().cnpj, titulo_ajustado, conteudo_ajustado,
                                               anexos_paths)

        if dec_num:
            # muda nas configurações da fiscalização a notificação para a aba de AIIMs
            return move_analysis_from_notification_to_aiim(notification, dec_num)
        else:
            return None
    except Exception as e:
        if not str(e).startswith('Falha no Excel'):
            logger.exception(f'Erro no envio de notificação da análise {notification.verificacao}, título {title}')
        raise e


def get_available_analysis():
    return sorted([verification for verification in Analysis.get_all_analysis(
        Audit.get_current_audit().path() if Audit.get_current_audit() else None)
                   if verification not in [notif.verificacao for notif in get_possible_infractions_osf()] and
                   verification not in [infraction.analysis for infraction in get_infractions_osf()]])


def get_possible_infractions_osf() -> list[PossibleInfraction]:
    if get_current_audit():
        return sorted(get_current_audit().notificacoes)
    else:
        return []


def add_analysis_to_audit(analysis: Analysis, planilha=None, df: pd.DataFrame = None, planilha_detalhe=None):
    notificacao = Audit.PossibleInfraction(analysis, planilha, df, planilha_detalhe)
    get_current_audit().notificacoes.append(notificacao)
    get_current_audit().save()
    resultado = analysis.choose_between_notification_and_infraction()
    if not analysis.notification_title or (resultado is not None and resultado['decisão'] == 'Infração'):
        move_analysis_from_notification_to_aiim(notificacao)
    if resultado is not None:
        raise AIIMGeneratorUserWarning(resultado['mensagem'])


def move_analysis_from_notification_to_aiim(notification: PossibleInfraction, num_dec: str = None) -> str:
    full_path = None

    for infraction in notification.verificacao.infractions:
        if not notification.verificacao.must_choose_between_notification_and_infraction():
            if notification.planilha and infraction.has_filtro():
                planilha = infraction.sheet_extended_name(notification.planilha)
            else:
                planilha = notification.planilha
            # apenas cria itens na auditoria se forem criadas planilhas
            # isso porque filtros podem ter gerado listagens vazias
            if notification.df is not None or \
                    (planilha and planilha in get_current_audit().get_sheet().get_sheet_names()):
                aiim_item = Audit.AiimItem(infraction.filename, notification.verificacao, 0, num_dec, None,
                                           planilha, notification.df, notification.planilha_detalhe)
                full_path = aiim_item.notification_response_path()
                get_current_audit().aiim_itens.append(aiim_item)
    remove_notification(notification)

    # cria pasta da notificação
    # exceto se a análise for do tipo notifica ou penaliza
    if full_path and not notification.verificacao.must_choose_between_notification_and_infraction():
        os.makedirs(full_path, exist_ok=True)
    return str(full_path) if full_path else None


def create_aiim():
    aiim_number = generate_aiim_number(get_current_audit().osf)
    link_aiim_to_audit(aiim_number)


def create_aiim_item(aiim_item: AiimItem):
    item_number = AIIMAutoIt().cria_item(*__get_open_aiim_data_from_aiim2003(), aiim_item)
    if item_number == 0:
        raise Exception('Falha no salvamento do item no AIIM2003')
    else:
        aiim_item.item = item_number
        get_current_audit().save()
    cria_ddf(aiim_item)


def __get_open_aiim_data_from_aiim2003() -> (str, int):
    with MDBReader.AIIM2003MDBReader() as aiim2003:
        aiim_number = get_current_audit().aiim_number
        numero_sem_serie = get_current_audit().aiim_number_no_digit()
        if not aiim2003.is_aiim_open_to_edition(numero_sem_serie):
            raise Exception(f'Não é possível alterar o AIIM {aiim_number}, reabra-o primeiro!')
    return aiim_number, __get_aiim_position_in_aiim2003(aiim_number)


def cria_ddf(aiim_item: AiimItem):
    ddf = get_ddf_for_infraction(aiim_item.infracao)
    AIIMAutoIt().preenche_ddf(*__get_open_aiim_data_from_aiim2003(), aiim_item.item, ddf)


def aiim_item_cria_anexo(aiim_item: AiimItem):
    GeneralFunctions.clean_tmp_folder()
    provas = []
    capa_path = Path('tmp') / f'capa{aiim_item.item}.pdf'
    WordReport.cria_capa_para_anexo(f'ANEXO DO ITEM {aiim_item.item}', capa_path)
    if capa_path.is_file():
        provas = [capa_path]
    with SeleniumWebScraper() as ws:
        with EFDPVAReversed() as pva:
            provas.extend([item
                           for sublist in [proof.generate_proof(aiim_item, ws, pva)
                                           for proof in aiim_item.infracao.provas]
                           for item in sublist])
            provas.extend(aiim_item.generate_notification_proof(ws))
    logger.info('Juntando arquivos de provas em um anexo...')
    PDFExtractor.merge_pdfs(get_current_audit().aiim_path() / f'Anexo do Item {aiim_item.item}.pdf',
                            provas, remove_original_pdfs=False)
    PDFExtractor.split_pdf(get_current_audit().aiim_path() / f'Anexo do Item {aiim_item.item}.pdf',
                           max_size=GeneralConfiguration.get().max_epat_attachment_size)


def update_ddf(aiim_item: AiimItem):
    cria_ddf(aiim_item)


def update_aiim_item_notification_response(aiim_item: AiimItem, response: str):
    aiim_item.notificacao_resposta = response
    get_current_audit().save()


def update_aiim_item_number(aiim_item: AiimItem, new_number: int = 0):
    aiim_item.item = new_number
    if new_number > 0 and aiim_item.planilha is not None:
        get_current_audit().get_sheet().update_number_in_subtotals(aiim_item.planilha, aiim_item.item)
    get_current_audit().save()


def remove_notification(notification: PossibleInfraction):
    get_current_audit().notificacoes.remove(notification)
    get_current_audit().save()


def remove_aiim_item(aiim_item: AiimItem):
    if aiim_item.has_aiim_item_number():
        item_number = aiim_item.item
        update_aiim_item_number(aiim_item)
        AIIMAutoIt().remove_aiim_item(*__get_open_aiim_data_from_aiim2003(), item_number)
    get_current_audit().aiim_itens.remove(aiim_item)
    get_current_audit().save()


def link_aiim_to_audit(aiim_number: str):
    if not aiim_number:
        raise Exception('Não foi gerado um número de AIIM válido, tente novamente mais tarde!')
    get_current_audit().aiim_number = aiim_number
    get_current_audit().is_aiim_open = True
    with MDBReader.AIIM2003MDBReader() as aiim2003:
        posicao = aiim2003.get_aiim_position(get_current_audit().aiim_number_no_digit())
        if posicao == 0:
            AIIMAutoIt().cria_aiim(aiim_number, get_current_audit())
        else:
            AIIMAutoIt().atualiza_aiim(aiim_number, posicao, get_current_audit())
    get_current_audit().save()


def get_infractions_osf() -> list[Infraction]:
    if get_current_audit():
        return sorted([item.infracao for item in get_current_audit().aiim_itens])
    else:
        return []


def get_infraction_data_for_analysis_and_infraction(infraction: Infraction) -> Audit.AiimItem:
    return [v for v in get_current_audit().aiim_itens if v.infracao == infraction][0]


def get_ddf_for_infraction(infraction: Infraction):
    aiim_item = get_infraction_data_for_analysis_and_infraction(infraction)
    logger.info(f'Gerando DDF para inciso {infraction.inciso}, alínea {infraction.alinea}')
    if aiim_item.planilha:
        return get_current_audit().get_sheet().get_ddf_from_sheet(aiim_item.planilha, infraction, aiim_item.item)
    else:
        return {'infracao': infraction,
                'mensal': True,
                'ddf': aiim_item.verificacao.function_ddf(infraction, aiim_item.df)}


def send_notification_with_files_digital_receipt():
    if get_current_audit().receipt_digital_files:
        raise Exception(f'Já foi gerado recibo de entrega de arquivos digitais: '
                        f'{get_current_audit().receipt_digital_files}!')

    notification_subject = f'OSF {get_current_audit().osf} - Recibo de Entrega de Arquivos Digitais'
    notification_body = f'No âmbito da Ordem de Serviço Fiscal {get_current_audit().osf} e em atenção às respostas às ' \
                        f'notificações fiscais a ela vinculadas, segue juntado recibo de entrega de arquivos digitais.'
    logger.info('Gerando códigos hash dos arquivos digitais recebidos...')
    hashes = get_current_audit().get_digital_files_hashes()
    recibo_path = get_current_audit().path() / 'Recibo de Entrega de Arquivos Digitais.pdf'
    WordReport.cria_recibo_entrega_arquivos_digitais(get_current_audit().cnpj, get_current_audit().ie,
                                                     get_current_audit().empresa, get_current_audit().osf,
                                                     hashes, recibo_path)
    with SeleniumWebScraper() as ws:
        dec_num = ws.send_notification(get_current_audit().cnpj,
                                       notification_subject, notification_body,
                                       anexos_paths=[recibo_path],
                                       is_tipo_outros=True)
    if dec_num:
        get_current_audit().receipt_digital_files = dec_num
        get_current_audit().save()
    else:
        raise Exception('Ocorreu um erro na geração da notificação do recibo.')


def __update_ufesp_on_aiim2003():
    with MDBReader.AIIM2003MDBReader() as m:
        last_ufesp_stored = m.get_year_of_last_ufesp_stored()
        if last_ufesp_stored < date.today().year:
            # antes de dar pau, vê se acha as UFESPs mais recentes...
            ufesps = WebScraper.get_latest_ufesps_from(last_ufesp_stored)
            for ano, valor in ufesps:
                AIIMAutoIt().cadastra_ufesp(ano, valor)
            if ano != date.today().year:
                raise Exception('AIIM2003 está com a UFESP desatualizada. Verifique as últimas UFESPs no site da Sefaz')


def __update_selic_on_aiim2003():
    with MDBReader.AIIM2003MDBReader() as m:
        ultima = m.get_last_selic_stored()
        # apenas atualiza SELIC se não tem cadastrado ainda a taxa do mês passado
        if ultima < GeneralFunctions.first_day_of_month_before(date.today()):
            tabela_selic = WebScraper.get_selic_last_years()
            # apenas insere as taxas que surgiram após a última data cadastrada
            m.insert_selics(tabela_selic[ultima.strftime('%m/%Y'):].sort_index()[1:])

        # verifica se cadastrou todas as Selics necessárias
        if m.get_last_selic_stored() < GeneralFunctions.first_day_of_month_before(date.today()):
            raise Exception('Não foi possível cadastrar todas as SELICs'
                            ' necessárias para rodar o AIIM2003! Verifique manualmente!')


class AIIMNotExistsException(Exception):
    pass


def __get_aiim_position_in_aiim2003(aiim_number: str) -> int:
    with MDBReader.AIIM2003MDBReader() as aiim2003:
        numero_sem_serie = int(re.sub(r'[^\d]', '', aiim_number)[:-1])
        posicao = aiim2003.get_aiim_position(numero_sem_serie)
        if posicao == 0:
            raise AIIMNotExistsException(f'Não existe AIIM de número {aiim_number} cadastrado!')
        return posicao


def print_aiim_reports():
    __update_ufesp_on_aiim2003()
    __update_selic_on_aiim2003()
    aiim_number = get_current_audit().aiim_number
    numero_sem_serie = get_current_audit().aiim_number_no_digit()
    declare_observations_in_aiim()
    aiim2003 = AIIMAutoIt()
    aiim2003.gera_relatorios(aiim_number, __get_aiim_position_in_aiim2003(aiim_number))

    aiim_path = get_current_audit().aiim_path()
    GeneralFunctions.move_downloaded_file(aiim2003.get_reports_path(), f'Relato_A{numero_sem_serie}.pdf',
                                          aiim_path, 30, replace=True)
    GeneralFunctions.move_downloaded_file(aiim2003.get_reports_path(), f'Quadro1_A{numero_sem_serie}.pdf',
                                          aiim_path, 30, replace=True)
    GeneralFunctions.move_downloaded_file(aiim2003.get_reports_path(), f'Quadro2_A{numero_sem_serie}.pdf',
                                          aiim_path, 30, replace=True)
    get_current_audit().get_sheet().gera_quadro_3(aiim_path / f'Quadro1_A{numero_sem_serie}.pdf')


def generate_custom_report():
    logger.info('Atualizando relatório circunstanciado...')
    get_current_audit().update_report()


def generate_general_proofs_attachment():
    logger.info('Atualizando anexo de Provas Gerais...')
    get_current_audit().update_general_proofs()


def print_efd(book: str, refs: list[date]):
    with EFDPVAReversed() as pva:
        for ref in refs:
            filename = get_current_audit().aiim_path() / f'{book}{ref.year}{str(ref.month).zfill(2)}.pdf'
            match book:
                case 'lre':
                    pva.print_LRE(ref, filename)
                case 'lrs':
                    pva.print_LRS(ref, filename)
                case 'lri':
                    pva.print_LRI(ref, filename)
                case 'lraicms':
                    pva.print_LRAICMS(ref, filename)
                case _:
                    raise Exception(f'Não implementada impressão deste tipo de EFD: {book}')


def reopen_aiim():
    aiim_number = get_current_audit().aiim_number
    aex_path = get_current_audit().aiim_path() / f'{aiim_number.replace(".", "")}.aex'
    if not aex_path.is_file():
        raise Exception(f'Não é possível reeditar AIIM {aiim_number}, não localizei arquivo .aex correspondente!')
    logger.info(f'Realizando recuperação do AIIM {aiim_number} pelo arquivo {aex_path}')
    aiim2003 = AIIMAutoIt()
    try:
        position_in_list = __get_aiim_position_in_aiim2003(aiim_number)
        aiim2003.exclui_aiim(aiim_number, position_in_list)
    except AIIMNotExistsException:
        pass
    aiim2003.importa(aiim_number, aex_path)
    get_current_audit().is_aiim_open = True
    get_current_audit().save()


def export_aiim():
    aiim_number = get_current_audit().aiim_number
    aiim2003 = AIIMAutoIt()
    aiim2003.exporta(aiim_number, __get_aiim_position_in_aiim2003(aiim_number),
                     get_current_audit().aiim_path())


def upload_aiim():
    __update_ufesp_on_aiim2003()
    __update_selic_on_aiim2003()
    aiim2003 = AIIMAutoIt()
    aiim_number = get_current_audit().aiim_number
    # para evitar não conseguir mais editar o AIIM...
    export_aiim()
    aiim2003.gera_transmissao(aiim_number, __get_aiim_position_in_aiim2003(aiim_number),
                              get_current_audit().aiim_path())
    get_current_audit().is_aiim_open = False
    get_current_audit().save()


def generate_audit_schema():
    with SQLWriter() as postgres:
        if not postgres.does_schema_exist(get_current_audit().schema):
            logger.info(
                f'Criando schema chamado {get_current_audit().schema} no banco de dados central para a auditoria...')
            postgres.create_audit_schema(get_current_audit().schema,
                                         get_current_audit().cnpj_only_digits(),
                                         int(get_current_audit().ie_only_digits()),
                                         get_current_audit().inicio_auditoria,
                                         get_current_audit().fim_auditoria)
            logger.warning(f'Schema {get_current_audit().schema} criado com sucesso!')


def gia_apuracao_is_populated():
    with SQLReader(get_current_audit().schema) as postgres:
        return postgres.does_table_exist('gia_apuracao')


def gia_apuracao_download(ws: SeleniumWebScraper, window: sg.Window, evento: threading.Event) -> list[dict]:
    window.write_event_value('-DATA-EXTRACTION-STATUS-', ['GIA-DOWNLOAD', 'BEGIN'])
    try:
        resultado = ws.get_gias_apuracao(
            get_current_audit().ie, get_current_audit().inicio_auditoria,
            get_current_audit().fim_auditoria, evento)
        if evento.is_set():
            window.write_event_value('-DATA-EXTRACTION-STATUS-', ['GIA-DOWNLOAD', 'STOP'])
        else:
            window.write_event_value('-DATA-EXTRACTION-STATUS-', ['GIA-DOWNLOAD', 'END'])
        return resultado
    except Exception as e:
        window.write_event_value('-DATA-EXTRACTION-STATUS-', ['GIA-DOWNLOAD', 'FAILURE'])
        raise e


def gia_populate_database(gias: list, evento: threading.Event):
    if evento.is_set():
        return
    with SQLWriter(get_current_audit().schema) as postgres:
        postgres.executa_transacao('DROP TABLE IF EXISTS GIA_APURACAO;')
        postgres.executa_transacao("""
            CREATE TABLE GIA_APURACAO (
                IE BIGINT NOT NULL,
                REFERENCIA DATE NOT NULL,
                TIPO VARCHAR(30) NOT NULL,
                ENTREGA TIMESTAMP NOT NULL,
                SAIDAS_COM_DEBITO NUMERIC(15,2),
                OUTROS_DEBITOS NUMERIC(15,2),
                ESTORNO_CREDITO NUMERIC(15,2),
                ENTRADAS_COM_CREDITO NUMERIC(15,2),
                OUTROS_CREDITOS NUMERIC(15,2),
                ESTORNO_DEBITO NUMERIC(15,2),
                SALDO_CREDOR_ANTERIOR NUMERIC(15,2),
                SALDO_DEVEDOR NUMERIC(15,2),
                SALDO_CREDOR_A_TRANSPORTAR NUMERIC(15,2)
            );""")
        postgres.executa_transacao(
            'CREATE UNIQUE INDEX gia_apuracao_ie_idx ON GIA_APURACAO (ie,referencia,entrega, tipo);')
        for gia in gias:
            postgres.executa_transacao('INSERT INTO GIA_APURACAO VALUES (%s, %s::DATE, %s, %s::TIMESTAMP, %s, %s, %s, '
                                       '%s, %s, %s, %s, %s, %s);',
                                       (int(get_current_audit().ie_only_digits()),
                                        '01/' + gia['referencia'],
                                        gia['tipo'],
                                        gia['entrega'],
                                        float(gia['saidas_debito'].replace('.', '').replace(',', '.')),
                                        float(gia['outros_debitos'].replace('.', '').replace(',', '.')),
                                        float(gia['estorno_credito'].replace('.', '').replace(',', '.')),
                                        float(gia['entradas_credito'].replace('.', '').replace(',', '.')),
                                        float(gia['outros_creditos'].replace('.', '').replace(',', '.')),
                                        float(gia['estorno_debito'].replace('.', '').replace(',', '.')),
                                        float(gia['saldo_credor_anterior'].replace('.', '').replace(',', '.')),
                                        float(gia['saldo_devedor'].replace('.', '').replace(',', '.')),
                                        float(gia['saldo_credor_a_transportar'].replace('.', '').replace(',', '.')),
                                        ))


def nfe_inutilizados_is_populated():
    with SQLReader(get_current_audit().schema) as postgres:
        return postgres.does_table_exist('nfe_inutilizacao')


def nfe_inutilizados_download(ws: SeleniumWebScraper, window: sg.Window, evento: threading.Event) -> list[dict]:
    window.write_event_value('-DATA-EXTRACTION-STATUS-', ['NFeEmit-DOWNLOAD', 'BEGIN'])
    try:
        resultado = ws.get_nfe_inutilizacoes(get_current_audit().cnpj,
                                             get_current_audit().inicio_auditoria.year,
                                             get_current_audit().fim_auditoria.year + 1)
        if evento.is_set():
            window.write_event_value('-DATA-EXTRACTION-STATUS-', ['NFeEmit-DOWNLOAD', 'STOP'])
        else:
            window.write_event_value('-DATA-EXTRACTION-STATUS-', ['NFeEmit-DOWNLOAD', 'END'])
        return resultado
    except Exception as e:
        window.write_event_value('-DATA-EXTRACTION-STATUS-', ['NFeEmit-DOWNLOAD', 'FAILURE'])
        raise e


def nfe_inutilizados_populate_database(inutilizacoes: list, evento: threading.Event):
    if evento.is_set():
        return
    with SQLWriter(get_current_audit().schema) as postgres:
        postgres.executa_transacao('DROP TABLE IF EXISTS NFE_INUTILIZACAO;')
        postgres.executa_transacao("""
            CREATE TABLE NFE_INUTILIZACAO (
                SERIE INT NOT NULL,
                INICIO INT NOT NULL,
                FIM INT NOT NULL,
                INUTILIZACAO DATE NOT NULL
            );""")
        for inutilizacao in inutilizacoes:
            postgres.executa_transacao('INSERT INTO NFE_INUTILIZACAO VALUES (%s, %s, %s, %s);',
                                       (int(inutilizacao['serie']),
                                        int(inutilizacao['inicio']),
                                        int(inutilizacao['fim']),
                                        datetime.strptime(inutilizacao['timestamp'].split()[0], '%d/%m/%Y')
                                        ))


def sat_has_equipment(ws: SeleniumWebScraper) -> bool:
    if get_current_audit().has_sat_equipment is None:
        value = ws.verify_sat_equipment(get_current_audit().cnpj)
        get_current_audit().has_sat_equipment = value
        get_current_audit().save()
    return get_current_audit().has_sat_equipment


def efd_files_download(ws: SeleniumWebScraper, window: sg.Window, evento: threading.Event) -> list[dict]:
    # apenas baixa arquivos enviados posteriormente ao último download, para ter um efeito "resume"
    downloaded_files_reception = sorted(list(map(
        lambda f: datetime.strptime(re.match(r'.*-(\d+)$', f.stem).group(1), '%d%m%Y%H%M%S'),
        get_current_audit().reports_path().glob('SPED*.txt')
    )))
    last_time_sent = datetime.today() - timedelta(2000) \
        if len(downloaded_files_reception) == 0 \
        else downloaded_files_reception[-1]
    window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-DOWNLOAD', 'BEGIN'])
    try:
        lista = []
        for periodoRPA in get_current_audit().get_periodos_da_fiscalizacao():
            inicio = periodoRPA[0]
            fim = periodoRPA[1]
            if fim == get_current_audit().fim_auditoria:
                # se o último mês do período calhar com o fim da fiscalização,
                # tenta baixar também 2 meses extras, para verificações de LRE
                fim += timedelta(40)
            lista.extend(ws.get_efds_for_osf(get_current_audit().osf, inicio, fim, last_time_sent, evento))
        if evento.is_set():
            window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-DOWNLOAD', 'STOP'])
        else:
            window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-DOWNLOAD', 'END'])
        return lista
    except Exception as e:
        window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-DOWNLOAD', 'FAILURE'])
        raise e


def efd_populate_database(window: sg.Window, result: list[dict], evento: threading.Event):
    if evento.is_set():
        return
    with EFDPVAReversed() as pva:
        efd_files_import_PVA(pva, window, evento)
        efd_files_import_SGBD(pva, window, evento)
        efd_generate_unified_tables(window, evento)
    efd_populate_table_with_file_delivery(result, window, evento)


def efd_references_imported_PVA() -> list[datetime.date]:
    with EFDPVAReversed() as pva:
        arquivos = pva.list_imported_files(get_current_audit().cnpj)
    return sorted([date(int(t[-44:-40]), int(t[-40:-38]), 1) for t in arquivos])


def efd_files_import_PVA(pva: EFDPVAReversed, window: sg.Window, evento: threading.Event) -> bool:
    # não vai inserir na base todos os arquivos SPED encontrados,
    # pois exclui aqueles que já estão na base do PVA
    # Fazendo em ordem alfabética, caso tenha arquivos substitutos,
    # eles serão importados posteriormente aos originais
    sped_files = get_current_audit().reports_path().glob('SPED*.txt')
    sped_files_imported = list(
        map(lambda f: Path(f).stem + Path(f).suffix, pva.list_imported_files(get_current_audit().cnpj)))
    sped_files_to_import = list(filter(
        lambda sped_path: (sped_path.stem + sped_path.suffix) not in sped_files_imported,
        sped_files))
    window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-PVA', f'TOTAL{sum(1 for _ in sped_files_to_import)}'])
    if len(sped_files_to_import) == 0:
        logger.warning('Todos os arquivos SPED EFD já foram importados no EFD PVA ICMS anteriormente!')
        return False
    try:
        for sped_file in sped_files_to_import:
            pva.import_efd(sped_file, window, evento)
        logger.warning('Arquivos SPED EFD importados no EFD PVA ICMS com sucesso!')
    except:
        window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-PVA', 'FAILURE'])
        logger.exception('Ocorreu erro na importação de arquivos SPED para o EFD PVA.')
    return True


def efd_files_import_SGBD(pva: EFDPVAReversed, window: sg.Window, evento: threading.Event):
    # TODO aqui poderia fazer a pesquisa direto né
    dic = GeneralFunctions.get_dados_efds(get_current_audit().path())
    efds = dic['efds']
    # adicionando banco master, que tem a tabela com todas as escrituracoes
    efds.append({'referencia': 'lista de escriturações', 'bd': 'master'})

    # verifica se já não estão importados todos os bancos de dados
    with SQLReader(schema=get_current_audit().schema) as postgres:
        # TODO tem alguma coisa aqui errada que não lembro mais o que queria fazer :O)
        if postgres.does_table_exist('reg_0000') and \
                postgres.has_return_set('select 1 from reg_0000 where dt_ini::varchar not in '):
            logger.warning('Importação das EFDs já realizada anteriormente a partir do EFD PVA ICMS IPI')
            return

    window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-BD', f'TOTAL{sum(1 for _ in efds)}'])

    try:
        with SQLWriter() as postgres:
            postgres.drop_master_schema()
            for efd in efds:
                if evento.is_set():
                    window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-BD', 'STOP'])
                    return
                window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-BD', 'BEGIN'])
                if not postgres.does_schema_exist(efd['bd']) and \
                        not postgres.does_schema_exist(
                            GeneralFunctions.efd_schema_name(get_current_audit().cnpj, efd['referencia'])):
                    dump_file = Path('tmp') / f"{efd['bd']}.sql"
                    logger.info(f'Exportando banco da referência {efd["referencia"]} do EFD PVA ICMS IPI...')
                    pva.dump_db(efd['bd'], dump_file)
                    if not dump_file.is_file():
                        window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-BD', 'FAILURE'])
                        logger.error(
                            f'Falha na exportação de arquivo EFD da referência {efd["referencia"]} '
                            f'do EFD PVA ICMS IPI, arquivo gerado não localizado.')
                        return
                    logger.info(f'Importando banco da referência {efd["referencia"]} no banco de dados central...')
                    postgres.create_efd_schema(efd['bd'], dump_file)
                    dump_file.unlink()
                else:
                    logger.info(
                        f'Arquivo SPED de {efd["referencia"]} já tinha sido importado no banco de dados central')
                window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-BD', 'END'])
            logger.warning('Bancos de dados do EFD PVA ICMS IPI importados com sucesso no banco de dados central!')
    except:
        logger.exception('Ocorreu erro na migração dos bancos do EFD PVA para o banco de dados central.')
        window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-BD', 'FAILURE'])


def efd_generate_unified_tables(window: sg.Window, evento: threading.Event):
    if evento.is_set():
        return
    with SQLWriter(get_current_audit().schema) as postgres:
        dic = GeneralFunctions.get_dados_efds(get_current_audit().path())
        efdsBD = list(map(lambda efd:
                          (efd['bd'], GeneralFunctions.efd_schema_name(get_current_audit().cnpj, efd['referencia'])),
                          dic['efds']))
        if next(filter(lambda efd: not postgres.does_schema_exist(efd[0])
                                   and not postgres.does_schema_exist(efd[1]), efdsBD), None):
            logger.error('Erro na geração das tabelas de EFD no banco de dados central: '
                         'ainda faltam EFDs a serem importadas do EFD PVA')
            window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-UNIFY', 'FAILURE'])
            return
        window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-UNIFY', 'BEGIN'])
        try:
            logger.info('Iniciando criação de tabelas de EFD no banco de dados central...')
            postgres.prepare_table_escrituracaofiscal()
            postgres.unify_efd_tables(get_current_audit().cnpj, dic)
            window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-UNIFY', 'END'])
            logger.warning('Tabelas de EFD criadas com sucesso no banco de dados central!')
        except Exception:
            window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-UNIFY', 'FAILURE'])
            logger.exception('Erro na unificação de tabelas no banco de dados central')


def efd_populate_table_with_file_delivery(efds: list[dict], window: sg.Window, evento: threading.Event):
    if evento.is_set():
        return
    with SQLWriter(get_current_audit().schema) as postgres:
        postgres.executa_transacao('DROP TABLE IF EXISTS escrituracaofiscal_entrega;')
        postgres.executa_transacao("""
                    CREATE TABLE escrituracaofiscal_entrega (
                        datainicial DATE NOT NULL,
                        tipo VARCHAR NOT NULL,
                        entrega TIMESTAMP NOT NULL);""")
        for efd in efds:
            postgres.executa_transacao('INSERT INTO escrituracaofiscal_entrega (datainicial, tipo, entrega)'
                                       ' VALUES (%s::DATE, %s, %s::TIMESTAMP);',
                                       (efd['referencia'].strftime('%d/%m/%Y'),
                                        efd['tipo'],
                                        efd['entrega'].strftime('%d/%m/%Y %H:%M:%S'),
                                        ))


def populate_database(groups: list, window: sg.Window, evento: threading.Event):
    generate_audit_schema()

    with SeleniumWebScraper(get_current_audit().reports_path()) as ws:
        with ThreadPoolExecutor(thread_name_prefix='PopulaDadosPrincipal') as tex:
            if 'EFD' in groups:
                result = efd_files_download(ws, window, evento)
                tex.submit(efd_populate_database, window, result, evento)
            if evento.is_set():
                return
            if 'GIA' in groups:
                if not gia_apuracao_is_populated():
                    result = gia_apuracao_download(ws, window, evento)
                    gia_populate_database(result, evento)
            if evento.is_set():
                return
            if 'NFeEmit' in groups:
                if not nfe_inutilizados_is_populated():
                    result = nfe_inutilizados_download(ws, window, evento)
                    nfe_inutilizados_populate_database(result, evento)

            if 'SAT' in groups or 'SATItens' in groups:
                if not sat_has_equipment(ws):
                    if 'SAT' in groups:
                        groups.remove('SAT')
                        window.write_event_value('-DATA-EXTRACTION-STATUS-', ['SAT-DOWNLOAD', 'END'])
                        window.write_event_value('-DATA-EXTRACTION-STATUS-', ['SAT-IMPORT', 'END'])
                    if 'SATItens' in groups:
                        groups.remove('SATItens')
                        window.write_event_value('-DATA-EXTRACTION-STATUS-', ['SATItens-DOWNLOAD', 'END'])
                        window.write_event_value('-DATA-EXTRACTION-STATUS-', ['SATItens-IMPORT', 'END'])

            if evento.is_set():
                return

            relatorios = []
            for group in groups:
                # ordena os relatorios no grupo para primeiro executar aqueles que geram estimativas
                relatorios.extend([k for k, v in WebScraper.launchpad_report_options.items()
                                   if v['Grupo'] == group and v.get('Principal', False)])
                relatorios.extend([k for k, v in WebScraper.launchpad_report_options.items()
                                   if v['Grupo'] == group and not v.get('Principal', False)])
            tex.submit(launchpad_relatorios_download, relatorios, ws, window, evento)
            tex.submit(launchpad_relatorios_import, relatorios, window, evento)


def declare_operations_in_aiim():
    # apenas busca o relatório se ele não estiver baixado,
    # ou se estiver sido executado no mês anterior
    ops = get_current_audit().get_sheet().get_operations_for_aiim(
        get_current_audit().reports_path() / 'Valor_Total_Documentos_Fiscais_x_GIA.xlsx')
    if get_current_audit().situacao == 'Ativo':
        last_expected_activity = GeneralFunctions.first_day_of_month_before(datetime.today())
    else:
        last_expected_activity = get_current_audit().inicio_situacao - timedelta(days=1)
        last_expected_activity = date(last_expected_activity.year, last_expected_activity.month, 1)
    with SeleniumWebScraper(get_current_audit().reports_path(), hidden=False) as ws:
        while len(ops) < 12 or (len(ops) > 0 and ops.index[0].date() < last_expected_activity):
            # roda relatório com período de 1 ano pra tentar pegar 12 meses de movimento
            # se nao for suficiente, roda mais um ano até o inicio da auditoria pra encontrar
            # esses 12 meses
            if len(ops) > 0 and ops.index[0].date() < last_expected_activity:
                fim = last_expected_activity
                inicio = ops.index[0].date()
            else:
                fim = last_expected_activity
                inicio = max(fim - timedelta(365), get_current_audit().inicio_auditoria)
            if inicio >= fim:
                break
            relatorio = 'Valor Total Documentos Fiscais x GIA'
            parametros = [get_current_audit().cnpj_only_digits(), inicio.strftime('%Y%m'), fim.strftime('%Y%m')]
            operacoes_xls = ws.get_launchpad_report(relatorio,
                                                    'Valor_Total_Documentos_Fiscais_x_GIA.xlsx',
                                                    threading.Event(), None, *parametros)
            ops = get_current_audit().get_sheet().get_operations_for_aiim(operacoes_xls)
    with MDBReader.AIIM2003MDBReader() as aiim2003:
        logger.info('Cadastrando operações direto no banco do AIIM2003')
        aiim2003.insert_operations(get_current_audit().aiim_number_no_digit(), ops)


def declare_observations_in_aiim():
    obs_configs = GeneralFunctions.get_dados_observacoes_aiim()
    obs = []
    with MDBReader.AIIM2003MDBReader() as aiim2003:
        logger.info('Cadastrando observações direto no banco do AIIM2003')
        for dic in obs_configs:
            revised_text = dic['descricao']
            revised_text = revised_text.replace('<osf>', get_current_audit().osf)
            if dic.get('sonegacao'):
                if aiim2003.is_sonegation_aiim(get_current_audit().aiim_number_no_digit()):
                    obs.append(revised_text)
            elif dic.get('glosa'):
                if any([item.infracao.inciso == 'II' for item in get_current_audit().aiim_itens]):
                    obs.append(revised_text)
            else:
                obs.append(revised_text)
        aiim2003.insert_observations(get_current_audit().aiim_number_no_digit(), obs)


def launchpad_relatorios_download(relatorios: list, ws: SeleniumWebScraper, window: sg.Window, evento: threading.Event):
    # isso faz com que todos os relatórios da lista sejam executados,
    # com no máximo LAUNCHPAD_MAX_CONCURRENT_REPORTS simultaneamente
    # é feita quebra de relatórios em diferentes períodos, conforme estimativa feita
    global is_downloading_reports
    resultados = {}
    with ThreadPoolExecutor(thread_name_prefix='LaunchpadDownload',
                            initializer=GeneralFunctions.initializePythonCom) as executor:
        is_downloading_reports = True
        for relatorio in relatorios:
            resultados[relatorio] = __run_report(relatorio, evento, ws, executor, window)
    # apenas continua quando todos os futuros estão completados
    # (podem ser encerrados antecipadamente setando o evento)
    is_downloading_reports = False
    revised_groups = []
    # muda a periodicidade de download de arquivos, caso algum grupo tenha dado timeout
    for relatorio, execucoes in resultados.items():
        group = launchpad_report_options[relatorio]['Grupo']
        if group not in revised_groups:
            for execucao in execucoes:
                exception = execucao.exception()
                if exception and isinstance(exception, WebScraper.WebScraperTimeoutException):
                    # aumentar a periodicidade dos relatorios, pra proxima tentativa
                    __revisa_periodicidade_relatorio(relatorio)
                    revised_groups.append(group)
                    break
    logger.info('Encerrado levantamento de dados no Launchpad!')


def __run_report(relatorio: str, evento: threading.Event, ws: SeleniumWebScraper,
                 executor: ThreadPoolExecutor, window: sg.Window) -> list[Future]:
    parametros = __parametros_para_launchpad(relatorio)
    periodos = __estima_periodicidades_relatorio(relatorio, parametros)
    execucoes = []
    if evento.is_set():
        return execucoes
    report = launchpad_report_options[relatorio]
    if len(periodos) == 0:
        window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                 [f"{launchpad_report_options[relatorio]['Grupo']}-DOWNLOAD", 'TOTAL1'])
        execucoes.append(executor.submit(ws.get_launchpad_report, relatorio,
                                         launchpad_download_filename(relatorio,
                                                                     (get_current_audit().inicio_auditoria,
                                                                      get_current_audit().fim_auditoria)),
                                         evento, window, *parametros))
    else:
        window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                 [f"{launchpad_report_options[relatorio]['Grupo']}-DOWNLOAD", f'TOTAL{len(periodos)}'])
        execucao_anterior = None
        for periodicidade in periodos:
            parametros_cp = parametros.copy()
            if 'inicio' in report['Parametros']:
                parametros_cp[report['Parametros'].index('inicio')] = \
                    periodicidade[0].strftime('%d/%m/%Y')
                parametros_cp[report['Parametros'].index('fim')] = \
                    periodicidade[1].strftime('%d/%m/%Y')
            # cria um "enfileiramento" de relatorios, para evitar que relatórios com mesmo nome
            # sejam executados simultaneamente e dê sobrecarga ou Selenium não encontre a aba certa
            execucao_anterior = executor.submit(ws.get_launchpad_report, relatorio,
                                                launchpad_download_filename(relatorio, periodicidade),
                                                evento, window,
                                                *parametros_cp, relatorio_anterior=execucao_anterior)
            execucoes.append(execucao_anterior)
    return execucoes


def launchpad_download_filename(nome_relatorio: str, periodicidade=None) -> str:
    modo_exportacao = launchpad_report_options[nome_relatorio]
    tipo_arquivo = modo_exportacao.get('Formato', '.csv')
    if tipo_arquivo == 'PDF':
        tipo_arquivo = '.pdf'
    elif tipo_arquivo.startswith('Excel'):
        tipo_arquivo = '.xlsx'
    elif tipo_arquivo == 'Texto':
        tipo_arquivo = '.txt'

    if periodicidade:
        return f'{nome_relatorio.replace(" ", "_")}_' \
               f"{periodicidade[0].strftime('%d%m%Y')}_" \
               f"{periodicidade[1].strftime('%d%m%Y')}" \
               f'{tipo_arquivo}'
    else:
        return f'{nome_relatorio.replace(" ", "_")}_' \
               f'{get_current_audit().inicio_auditoria.strftime("%d%m%Y")}_' \
               f'{get_current_audit().fim_auditoria.strftime("%d%m%Y")}' \
               f'{tipo_arquivo}'


def __parametros_para_launchpad(nome_relatorio: str):
    nomes_parametros = launchpad_report_options[nome_relatorio]['Parametros']
    parametros = []
    for par in nomes_parametros:
        if par == 'cnpj':
            parametros.append(get_current_audit().cnpj_only_digits())
        elif par == 'cnpjBase':
            parametros.append(get_current_audit().cnpj_only_digits().zfill(14)[:8])
        elif par == 'ie':
            parametros.append(get_current_audit().ie_only_digits())
        elif par == 'osf':
            parametros.append(get_current_audit().osf_only_digits())
        elif par == 'inicio':
            parametros.append(get_current_audit().inicio_auditoria.strftime('%d/%m/%Y'))
        elif par == 'fim':
            parametros.append(get_current_audit().fim_auditoria.strftime('%d/%m/%Y'))
        elif par == 'inicioAAAAMM':
            parametros.append(get_current_audit().inicio_auditoria.strftime('%Y%m'))
        elif par == 'fimAAAAMM':
            parametros.append(get_current_audit().fim_auditoria.strftime('%Y%m'))
        elif par == 'inicioAAAA':
            parametros.append(get_current_audit().inicio_auditoria.strftime('%Y'))
        elif par == 'fimAAAA':
            parametros.append(get_current_audit().fim_auditoria.strftime('%Y'))
        elif par == 'situacao':
            # TODO pode ser que mude a situacao conforme a fiscalizacao?
            if nome_relatorio.find('Dest') > 0:
                parametros.append('0')
            else:
                parametros.append("0;1;2")
        elif par == '':
            parametros.append('')
        elif par == 'chaves':
            # caso especial, nao pega dados da OSF, tem que preencher por fora
            return
        else:
            raise Exception(f'Foi encontrado tipo de parametro na consulta que eu nao sei tratar: {par}')
    return parametros


def __estima_periodicidades_relatorio(nome_relatorio: str, parametros: list) -> list:
    nomes_parametros = launchpad_report_options[nome_relatorio]['Parametros']
    if 'inicio' not in nomes_parametros:
        # nao tem necessidade de quebrar relatorios que ja sao consolidados
        logger.info(f'Relatório {nome_relatorio} é agrupado, não será feito download em partes')
        return []

    inicio = datetime.strptime(parametros[nomes_parametros.index('inicio')], '%d/%m/%Y').date()
    fim = datetime.strptime(parametros[nomes_parametros.index('fim')], '%d/%m/%Y').date()

    # tenta inicialmente pegar a periodicidade já gravada nos dados da auditoria
    if get_current_audit().reports.get(launchpad_report_options[nome_relatorio]['Grupo'], None) is not None:
        periodicidade_str = get_current_audit().reports[launchpad_report_options[nome_relatorio]['Grupo']]
        if periodicidade_str[-1] == 'd':
            periodicidade = timedelta(int(periodicidade_str[:-1]))
        elif periodicidade_str[-1] == 'm':
            periodicidade = relativedelta(months=int(periodicidade_str[:-1]))
        elif periodicidade_str[-1] == 'y':
            periodicidade = relativedelta(years=int(periodicidade_str[:-1]))
        else:
            periodicidade = LAUNCHPAD_REPORT_WITHOUT_BREAKS
    else:
        # se nao encontrou estimativa guardada, aí considera que é um ano por padrão,
        # já que a velocidade de geração de relatório no Launchpad não parece ter muita
        # relação com o período de download
        periodicidade = relativedelta(years=1)

        if periodicidade == LAUNCHPAD_REPORT_WITHOUT_BREAKS:
            logger.info(f'Será baixado o período todo de uma vez para {nome_relatorio}')
            get_current_audit().reports[launchpad_report_options[nome_relatorio]['Grupo']] = 'Agrupado'
        else:
            if isinstance(periodicidade, timedelta):
                tempo = f'{periodicidade.days} dias'
                get_current_audit().reports[
                    launchpad_report_options[nome_relatorio]['Grupo']] = f'{periodicidade.days}d'
            else:
                if periodicidade.years == 0:
                    tempo = f'{periodicidade.months} mes(es)'
                    get_current_audit().reports[
                        launchpad_report_options[nome_relatorio]['Grupo']] = f'{periodicidade.months}m'
                else:
                    tempo = f'{periodicidade.years} ano(s)'
                    get_current_audit().reports[
                        launchpad_report_options[nome_relatorio]['Grupo']] = f'{periodicidade.years}y'
            logger.warning(
                f'{nome_relatorio} será baixado em blocos de {tempo}')
        get_current_audit().save()

    periodos = []
    i = inicio
    while i < fim:
        if isinstance(periodicidade, relativedelta):
            periodos.append((i, min(fim, i + periodicidade + timedelta(-1))))
        elif periodicidade == LAUNCHPAD_REPORT_WITHOUT_BREAKS:
            periodos.append((inicio, fim))
        else:
            periodos.append((i, min(fim, i + periodicidade + timedelta(-1), GeneralFunctions.last_day_of_month(i))))
        i = periodos[-1][1] + timedelta(1)
    return periodos


def __revisa_periodicidade_relatorio(nome_relatorio: str):
    nome_grupo = launchpad_report_options[nome_relatorio]['Grupo']
    atual = get_current_audit().reports.get(nome_grupo, 'Agrupado')
    nomes_parametros = launchpad_report_options[nome_relatorio]['Parametros']
    if 'inicio' not in nomes_parametros:
        # não há como revisar, o relatório já é agrupado
        return
    texto = None
    match atual:
        case 'Agrupado':
            novo = '1y'
            texto = 'anual'
        case '1y':
            novo = '6m'
            texto = 'semestral'
        case '6m':
            novo = '3m'
            texto = 'trimestral'
        case '3m':
            novo = '1m'
            texto = 'mensal'
        case '1m':
            # 16 para sempre ter 2 periodicidades em um mês, independentemente da qtd dias do mês
            novo = '16d'
            texto = 'quinzenal'
        case '16d':
            # para ter 3 periodicidades em um mês
            novo = '11d'
            texto = 'semanal'
        case _:
            # se não souber o que fazer, não atualiza
            novo = None
    if novo:
        logger.warning(f'Periodicidade de download dos relatórios do grupo "{nome_grupo}" diminuída para {texto}')
        get_current_audit().reports[nome_grupo] = novo
        get_current_audit().save()


def launchpad_relatorios_import(relatorios: list, window: sg.Window, evento: threading.Event):
    with ThreadPoolExecutor(thread_name_prefix='BDImport') as bdex:
        with ThreadPoolExecutor(thread_name_prefix='LaunchpadImport') as tex:
            if evento.is_set():
                return

            try:
                main_report = None
                for relatorio in relatorios:
                    if launchpad_report_options[relatorio].get('Principal', False):
                        main_report = __import_report_initialize(relatorio, evento, window, tex, bdex)
                    else:
                        __import_report_initialize(relatorio, evento, window, tex, bdex, main_report)
            except Exception as e:
                logger.exception('Erro na submissão de relatório do Launchpad')
                raise e
    logger.info('Encerrada importação de relatórios do Launchpad no banco de dados central!')


def __import_report_initialize(relatorio: str, evento: threading.Event, window: sg.Window,
                               tex: ThreadPoolExecutor, bdex: ThreadPoolExecutor, predecessor: Future = None) -> Future:
    # apenas inicia a importação quando todos os períodos foram baixados
    relatorio_nome_inicio = relatorio.replace(' ', '_')
    relatorio_opcoes = launchpad_report_options[relatorio]
    relatorio_nome_extensao = relatorio_opcoes.get('Formato', '.csv')
    if relatorio_nome_extensao != '.csv':
        logger.warning(f'Relatório {relatorio} não é CSV, não será importado na base de dados central...')
        return None
    return tex.submit(__check_reports_completed,
                      relatorio_nome_inicio, relatorio_opcoes, evento, window, bdex, predecessor)


def __check_reports_completed(relatorio_nome_inicio: str, relatorio_opcoes: dict,
                              evento: threading.Event, window: sg.Window,
                              bdex: ThreadPoolExecutor, predecessor: Future = None):
    inicio = get_current_audit().inicio_auditoria
    fim = get_current_audit().fim_auditoria
    periodo_total = (fim - inicio).days + 1
    index = len(relatorio_nome_inicio)
    # aguarda até que todos os períodos do relatório estejam baixados, e que o predecessor tenha terminado
    while True:
        acabou_predecessor = False
        if not predecessor:
            acabou_predecessor = True
        else:
            try:
                # retorna se deu exception ou não, mas desde que tenha finalizado
                result = predecessor.exception(timeout=1)
                # mas se deu exception, desiste
                if result:
                    raise concurrent.futures.CancelledError
                logger.debug(f'Liberada importação do relatório {relatorio_nome_inicio},'
                             f' pois importação de tabela principal acabou')
                acabou_predecessor = True
            except concurrent.futures.CancelledError:
                logger.debug(f'Desistiu de importar relatório {relatorio_nome_inicio},'
                             f' pois importação de tabela principal deu falha')
                return
            except concurrent.futures.TimeoutError:
                if evento.is_set():
                    if window:
                        window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                                 [f"{relatorio_opcoes['Grupo']}-IMPORT", 'STOP'])
                    return
                # volta a verificar o status da thread predecessora antes de ver a próxima condicao
                continue

        if 'inicio' in relatorio_opcoes['Parametros']:
            total_baixado = sum(map(lambda file: (datetime.strptime(file.stem[index + 10:index + 19], '%d%m%Y').date() -
                                                  datetime.strptime(file.stem[index + 1:index + 9],
                                                                    '%d%m%Y').date()).days + 1,
                                    get_current_audit().reports_path().glob(f'{relatorio_nome_inicio}_*.csv')))
            baixou_tudo = total_baixado >= periodo_total
        else:
            baixou_tudo = (get_current_audit().reports_path() /
                           f'{relatorio_nome_inicio}_{inicio.strftime("%d%m%Y")}_{fim.strftime("%d%m%Y")}.csv').is_file()

        if evento.is_set():
            window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                     [f"{relatorio_opcoes['Grupo']}-IMPORT", 'STOP'])
            return

        if not baixou_tudo and not is_downloading_reports:
            logger.info(
                f'Encerrada a tentativa de importação do relatório {relatorio_nome_inicio}, '
                f'pois não está mais baixando os relatórios necessários...')
            window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                     [f"{relatorio_opcoes['Grupo']}-IMPORT", 'STOP'])
            return

        if not baixou_tudo or not acabou_predecessor:
            time.sleep(10)
        else:
            logger.info(
                f'Todos os períodos do relatório {relatorio_nome_inicio} foram baixados, iniciando importação...')
            break
    # se saiu do bloco infinito, inicia importação
    __import_report(relatorio_nome_inicio, relatorio_opcoes, window, bdex)


def __import_report(relatorio_nome_inicio: str, relatorio_opcoes: dict, window: sg.Window, bdex: ThreadPoolExecutor):
    try:
        window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                 [f"{relatorio_opcoes['Grupo']}-IMPORT", 'BEGIN'])
        importacao = bdex.submit(CSVProcessing.import_report,
                                 relatorio_nome_inicio, get_current_audit().reports_path(),
                                 get_current_audit().schema)
        importacao.result()
    except CSVProcessingMissingPrerequisite as e:
        window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                 [f"{relatorio_opcoes['Grupo']}-IMPORT", 'FAILURE'])
        logger.exception(e)
        raise e
    except QueryAnalysisException as e:
        window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                 [f"{relatorio_opcoes['Grupo']}-IMPORT", 'FAILURE'])
        logger.exception(e)
        raise e
    except Exception as e:
        window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                 [f"{relatorio_opcoes['Grupo']}-IMPORT", 'FAILURE'])
        logger.exception(f'Ocorreu erro na importação do relatório {relatorio_nome_inicio} '
                         f'na base de dados central: {e}')
        raise e
    else:
        window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                 [f"{relatorio_opcoes['Grupo']}-IMPORT", 'END'])
        logger.warning(f'Importação do relatório {relatorio_nome_inicio} na base de dados central feita com sucesso!')


def executa_consulta_BD(sql: str, max_linhas=None) -> (int, pd.DataFrame):
    with SQLReader(get_current_audit().schema) as query:
        return query.executa_consulta(sql, max_linhas)


def existing_open_aiims_for_osf() -> list:
    with MDBReader.AIIM2003MDBReader() as aiim2003:
        return aiim2003.get_aiims_for_osf(get_current_audit().osf_only_digits())


def generate_custom_report_cover(texto: str, caminho: Path):
    WordReport.cria_capa_para_anexo(texto.upper(), caminho)


def set_proxy():
    WebScraper.set_proxy()


def install_efd_pva(efd_path: Path, efd_port: int):
    logger.info('Instalando EFD PVA...')
    arquivo = WebScraper.get_efd_pva_version()
    EFDPVAInstaller.upgrade_efd_pva(arquivo, efd_path, efd_port)


def update_efd_pva_version():
    GUIFunctions.update_splash('Verificando versão mais atualizada do EFD PVA ICMS...')
    try:
        with EFDPVAReversed() as pva:
            versao = pva.get_efd_pva_current_version()
        if versao is not None:
            GUIFunctions.update_splash(f'Baixando versão {versao} do EFD PVA ICMS...')
            arquivo = WebScraper.get_efd_pva_version(versao)
            GUIFunctions.update_splash(f'Instalando versão {versao} do EFD PVA ICMS...')
            EFDPVAInstaller.upgrade_efd_pva(arquivo, GeneralConfiguration.get().efd_path,
                                            GeneralConfiguration.get().efd_port)
            GUIFunctions.update_splash(f'EFD PVA ICMS atualizado!')
    except:
        logger.exception('Falha na atualização do EFD PVA ICMS')
        GUIFunctions.update_splash('Falha na atualização do EFD PVA ICMS, tentarei depois...')


def update_cadesp(zip_path: Path):
    ultima_atualizacao = GeneralConfiguration.get().cadesp_last_update
    data_arquivo = GeneralConfiguration.get().cadesp_date_from_file(zip_path)
    if ultima_atualizacao < data_arquivo:
        logger.info('Extraindo arquivos do zip...')
        with zipfile.ZipFile(zip_path, "r") as f:
            arquivos = f.namelist()
            if len(list(filter(lambda a: a.startswith('CadSefaz'), arquivos))) == 0:
                raise Exception('Arquivo de Cadesp não continha arquivo de texto começando por CadSefaz!')
            if len(list(filter(lambda a: a.startswith('CadRegimes'), arquivos))) == 0:
                raise Exception('Arquivo de Cadesp não continha arquivo de texto começando por CadRegimes!')
            f.extractall(GeneralFunctions.get_tmp_path())
        try:
            with SQLWriter() as postgres:
                logger.info('Criando tabelas do Cadesp...')
                postgres.create_cadesp_tables()

                cadastro = list(filter(lambda a: a.startswith('CadSefaz'), arquivos))[0]
                logger.info(f'Carregando arquivo de Cadastro do Cadesp...')
                postgres.import_dump_file(GeneralFunctions.get_tmp_path() / cadastro, 'cadesp_temp',
                                          delimiter='|', encoding='ISO-8859-1',
                                          null_string="Nihil", quote_char="E'\\b'")
                # apaga a primeira linha carregada, que é com metadados
                postgres.executa_transacao("DELETE FROM cadesp_temp WHERE IE = 'xxxxxxxxxxxxxx' OR IE IS NULL")
                importados = 0
                limite = 500000
                total = postgres.table_rowcount('cadesp_temp')
                while importados < total:
                    importados += postgres.insert_cadesp(importados, limite)
                    logger.info(f'Importados {100 * importados / total:.2f}% registros de Cadesp...')

                regimes = list(filter(lambda a: a.startswith('CadRegimes'), arquivos))[0]
                logger.info(f'Carregando arquivo de Regimes do Cadesp...')
                postgres.import_dump_file(GeneralFunctions.get_tmp_path() / regimes, 'cad_reg_temp',
                                          delimiter='|', encoding='ISO-8859-1')
                importados = 0
                limite = 500000
                ultima_importacao = -1
                total = postgres.table_rowcount('cad_reg_temp')
                while ultima_importacao != 0:
                    ultima_importacao = postgres.insert_cadesp_regime(importados, limite)
                    importados += limite
                    logger.info(f'Importados {100 * importados / total:.2f}% registros de Cadesp Regime...')
            GeneralConfiguration.get().cadesp_last_update = data_arquivo
            GeneralConfiguration.get().save()
        finally:
            for arq in arquivos:
                (GeneralFunctions.get_tmp_path() / arq).unlink(missing_ok=True)
    else:
        raise Exception(f'Banco de dados do Cadesp já estava atualizado até {data_arquivo.strftime("%m/%Y")}!')


def update_gias(zip_path: Path):
    ultima_atualizacao = GeneralConfiguration.get().gia_last_update
    data_arquivo = GeneralConfiguration.get().gia_date_from_file(zip_path)
    if ultima_atualizacao < data_arquivo:
        logger.info('Extraindo arquivos do zip...')
        with zipfile.ZipFile(zip_path, "r") as f:
            arquivos = f.namelist()
            f.extractall(GeneralFunctions.get_tmp_path())
        try:
            with SQLWriter() as postgres:
                logger.info('Criando tabela de GIAs...')
                postgres.create_gias_table()
                for arquivo in sorted(arquivos):
                    ano = int(arquivo[5:9])
                    logger.info(f'Carregando arquivo de GIAs do ano {ano}...')
                    postgres.import_dump_file(GeneralFunctions.get_tmp_path() / arquivo, 'gia_temp',
                                              delimiter='|', encoding='ISO-8859-1')
                    importados = 0
                    limite = 100000
                    total = postgres.table_rowcount('gia_temp')
                    while importados < total:
                        importados += postgres.insert_gia(ano, importados, limite)
                        logger.info(f'Importados {100 * importados / total:.2f}% registros de GIA de {ano}...')
            GeneralConfiguration.get().gia_last_update = data_arquivo
            GeneralConfiguration.get().save()
        finally:
            for arq in arquivos:
                (GeneralFunctions.get_tmp_path() / arq).unlink(missing_ok=True)
    else:
        raise Exception(f'Banco de dados de GIAs já estava atualizado até {data_arquivo.strftime("%m/%Y")}!')


def update_inidoneos(zip_path: Path):
    ultima_atualizacao = GeneralConfiguration.get().inidoneos_last_update
    data_arquivo = GeneralConfiguration.get().inidoneos_date_from_file(zip_path)
    if ultima_atualizacao < data_arquivo:
        logger.info('Extraindo arquivos do zip...')
        with zipfile.ZipFile(zip_path, "r") as f:
            arquivos = f.namelist()
            mdb_file = list(filter(lambda arq: Path(arq).suffix == '.mdb', arquivos))
            if len(mdb_file) == 0:
                raise Exception(f'Não foi encontrado arquivo Access de inidôneos dentro do arquivo {zip_path.name}!')
            f.extractall(GeneralFunctions.get_tmp_path())
        try:
            with SQLWriter() as postgres:
                logger.info('Criando tabela de inidoneo...')
                postgres.create_inidoneos_table()
                with MDBReader.InidoneosMDBImporter(GeneralFunctions.get_tmp_path() / mdb_file[0]) as mdb:
                    i = 0
                    for linha in mdb.get_inidoneos_table():
                        if i % 1000 == 0:
                            logger.info(f'Importados {i} registros de inidôneos...')
                        postgres.insert_inidoneo(linha)
                        i += 1
            GeneralConfiguration.get().inidoneos_last_update = data_arquivo
            GeneralConfiguration.get().save()
        finally:
            for arq in arquivos:
                (GeneralFunctions.get_tmp_path() / arq).unlink(missing_ok=True)
    else:
        raise Exception(f'Banco de dados de inidôneos já estava atualizado até {data_arquivo.strftime("%m/%Y")}!')


def prepare_database():
    with SQLWriter() as postgres:
        postgres.prepare_database()

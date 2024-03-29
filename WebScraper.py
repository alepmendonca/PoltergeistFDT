import base64
import concurrent.futures
import datetime
import gzip
import json
import os
import re
import socket
import sys
import threading
import time
import urllib
import zipfile
from concurrent.futures import Future
from multiprocessing import Process
from os import path
from typing import TypeVar
from urllib.error import URLError
from urllib.request import urlopen, install_opener
from urllib.request import urlopen

import pandas as pd
import PySimpleGUI as sg
import pepe
import requests
import autoit
import selenium
from autoit import AutoItError
from bs4 import BeautifulSoup
from pathlib import Path

from pepe.sistemas.pfe import GIARelatorio, GIASubRelatorio
from pepe.sistemas.pgsf import PgsfSituacaoOSF
from selenium import webdriver
from selenium.webdriver.chromium.webdriver import ChromiumDriver
from selenium.common.exceptions import StaleElementReferenceException, \
    NoAlertPresentException, TimeoutException, NoSuchElementException, WebDriverException, NoSuchWindowException, \
    UnexpectedAlertPresentException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from win32com.client import Dispatch

import GeneralConfiguration
import GeneralFunctions
import PDFExtractor
from GeneralFunctions import logger, wait_downloaded_file, move_downloaded_file

# Monkey Patching para não abrir shell em modo release!
selenium.webdriver.common.service.subprocess.Popen = GeneralFunctions.PopenWindows

LAUNCHPAD_MAX_TIME_WAIT_SECONDS = 1800
LAUNCHPAD_MAX_CONCURRENT_REPORTS = 4
LAUNCHPAD_TIME_WAIT_SECONDS = 15
LAUNCHPAD_TIME_REPORT_MINUTES = 2

proxy_srv = "proxyservidores.lbintra.fazenda.sp.gov.br"
proxy_port = 8080
launchpad_url = "https://teste:teste@srvbo-v42.intra.fazenda.sp.gov.br/BOE/BI"
project_releases_url = "https://api.github.com/repos/alepmendonca/PoltergeistFDT/releases/latest"
pgsf_url = "https://portal60.sede.fazenda.sp.gov.br/"
nfe_consulta_url = "https://nfe.fazenda.sp.gov.br/ConsultaNFe/consulta/publica/ConsultarNFe.aspx#tabConsInut"
pfe_url = "https://www3.fazenda.sp.gov.br/CAWEB/Account/Login.aspx"
cadesp_url = "https://www.cadesp.fazenda.sp.gov.br/"
arquivos_digitais_url = "https://www10.fazenda.sp.gov.br/ArquivosDigitais/Account/Login.aspx"
dec_url = "https://sefaznet11.intra.fazenda.sp.gov.br/DEC/UCLogin/login.aspx"
pgsf_produtividade_url = "https://sefaznet11.intra.fazenda.sp.gov.br/pgsf.net/Account/Login.aspx"
sem_papel_url = "https://www.documentos.spsempapel.sp.gov.br/siga/public/app/login"
sat_consulta_url = "https://satsp.fazenda.sp.gov.br/COMSAT/Public/ConsultaPublica/ConsultaPublicaCfe.aspx"

launchpad_report_options = {
    "CFOP_por_IE": {'Parametros': ['inicioAAAAMM', 'fimAAAAMM', 'ie'],
                    'Tipo': "Dados", "Relatorios": [], 'Grupo': 'GIA'},
    "Consulta Ingresso Suframa": {
        'Pesquisa': 'Suframa',
        'Parametros': ['cnpj', 'inicioAAAAMM', 'fimAAAAMM', 'osf'],
        'Tipo': "Dados", 'Relatorios': ["SIEX"], 'Grupo': 'COMEX'},
    "Consulta_DI_por_CNPJ": {
        'Parametros': ['cnpj', '', 'inicioAAAAMM', 'fimAAAAMM', 'osf'],
        'Tipo': "Dados", 'Relatorios': ["Consulta 1 com SIEX", "Consulta 2 com SIEX"], 'Grupo': 'COMEX'},
    "CTe_CNPJ_Emitente_Tomador_Remetente_Destinatario_OSF": {
        'Parametros': ['cnpj', 'inicio', 'fim', 'situacao', 'osf'],
        'Tipo': "Dados", 'Relatorios': ["CTe"], 'Grupo': 'CTe', 'Principal': True},
    "CTe_CNPJ_Info_Adicionais_OSF": {
        'Parametros': ['cnpj', 'inicio', 'fim', 'situacao', 'osf'],
        'Tipo': "Dados", 'Relatorios': ["CT-e"], 'Grupo': 'CTe'},
    "DACTE_versão_3.0": {
        'ID': 2795177, 'Abas_IDs': [553],
        'Pesquisa': 'DACTE', 'Parametros': ['chaves'],
        'Tipo': "Relatórios", "Relatorios": ["DACTE Rodoviário MOC 3.00"],
        "Formato": "PDF", 'Grupo': 'Prova', 'Modelo': 57},
    "DANFE Unificado – Lista de Chaves de Acesso": {
        'ID': 435320, 'Abas_IDs': [42934],
        'Pesquisa': 'DANFE', 'Parametros': ['chaves'],
        'Tipo': 'Relatórios', 'Relatorios': ['DANFE'],
        'Formato': "PDF", 'Grupo': 'Prova', 'Modelo': 55},
    "Manifestações_NFe_Destinatário_OSF": {
        'Pesquisa': 'Manifestações',
        'Parametros': ['inicio', 'fim', 'cnpj', 'osf'],
        'Tipo': "Dados", 'Relatorios': ["Nota Fiscal Eletronica"], 'Grupo': 'NFeDest'},
    "Manifestações_NFe_Emitente_OSF": {
        'Pesquisa': 'Manifestações',
        'Parametros': ['inicio', 'fim', 'cnpj', 'osf'],
        'Tipo': "Dados", 'Relatorios': ["Nota Fiscal Eletronica"], 'Grupo': 'NFeEmit'},
    "NF-es exportação com evento de averbação por CNPJ X periodo": {
        'Pesquisa': 'NF-es exportação',
        'Parametros': ['cnpj', '', 'inicioAAAAMM', 'fimAAAAMM', 'osf'],
        'Tipo': "Dados", 'Relatorios': ['Consulta 1 com SIEX', 'Consulta 2 com SIEX',
                                        'Consulta 3 com Nota Fiscal Eletronica'],
        'Grupo': 'COMEX'},
    "NFe Docs Referenciados Destinatário": {
        'Pesquisa': 'Referenciados',
        'Parametros': ['cnpj', 'inicioAAAAMM', 'fimAAAAMM'],
        'Tipo': "Dados", 'Relatorios': ['NFe SP', 'NFe UF'], 'Grupo': 'NFeDest'},
    "NFe Docs Referenciados Emitente": {
        'Pesquisa': 'Referenciados',
        'Parametros': ['cnpj', 'inicioAAAAMM', 'fimAAAAMM'],
        'Tipo': "Dados", 'Relatorios': ['NFe SP', 'NFe UF'], 'Grupo': 'NFeEmit'},
    "NFe Escrituração EFD Lista de Chaves de Acesso Emitente": {
        'ID': 658907, 'Abas_IDs': [5, 6],
        'Parametros': ['chaves', 'cnpj', 'inicioAAAAMM'],
        'Tipo': 'Relatorios',
        'Relatorios': ['EFD Destinatário'],
        'Formato': "PDF", 'Grupo': 'Prova'},
    "NFe_Destinatario_OSF": {
        'Parametros': ['cnpj', 'inicio', 'fim', 'situacao', 'osf'],
        'Tipo': "Dados", 'Relatorios': ['NFe SP', 'NFe UF'],
        'Grupo': 'NFeDest', 'Principal': True},
    "NFe_Destinatario_Itens_OSF": {
        'Parametros': ['cnpj', 'inicio', 'fim', 'situacao', 'osf'],
        'Tipo': "Dados", 'Relatorios': ['NFe SP', 'NFe UF'],
        'Grupo': 'NFeDestItens', 'Principal': True},
    "NFe_Emitente_Itens_OSF": {
        'Parametros': ['cnpj', 'inicio', 'fim', 'situacao', 'osf'],
        'Tipo': "Dados", 'Relatorios': ['NFe SP'],
        'Grupo': 'NFeEmitItens', 'Principal': True},
    "NFe_Emitente_OSF": {
        'ID': 210366,
        'Parametros': ['cnpj', 'inicio', 'fim', 'situacao', 'osf'],
        'Tipo': "Dados", 'Relatorios': ["NFe SP"],
        'Grupo': 'NFeEmit', 'Principal': True},
    "SAT - CuponsEmitidosPorContribuinteCNPJ_OSF": {
        'Pesquisa': 'SAT',
        'Parametros': ['cnpj', 'inicio', 'fim', 'osf'],
        'Tipo': "Dados", 'Relatorios': ['SAT CFe'],
        'Grupo': 'SAT', 'Principal': True},
    "REDF consulta Cupons Fiscais ECF": {
        'Pesquisa': 'REDF',
        'Parametros': ['cnpj', 'inicio', 'fim', 'osf'],
        'Tipo': "Dados", 'Relatorios': ['NFP - Documentos Fiscais em Papel'],
        'Grupo': 'SAT'},
    "SAT - ItensDeCuponsCNPJ_OSF": {
        'Pesquisa': 'SAT',
        'Parametros': ['cnpj', 'inicio', 'fim', 'osf'],
        'Tipo': "Dados", 'Relatorios': ['SAT CFe'],
        'Grupo': 'SATItens', 'Principal': True},
    "SN-Receita Bruta Declarada x Apurada": {
        'Pesquisa': 'Bruta', 'ID': 444338,
        'Parametros': ['cnpjBase', 'inicioAAAAMM', 'fimAAAAMM'],
        'Tipo': 'Relatórios', 'Relatorios': [],
        'Formato': 'Excel (.xlsx)', 'Grupo': 'SN'},
    "SN-e-COMMERCE": {
        'Pesquisa': 'commerce', 'ID': 489152,
        'Parametros': ['cnpjBase', 'inicioAAAA', 'fimAAAA'],
        'Tipo': 'Dados', 'Relatorios': ['SISCOM-IF', 'SISCOM-IC', 'SISCOM-ARQS'],
        'Grupo': 'SN'},
    "Valor Total Documentos Fiscais x GIA": {
        'Pesquisa': 'Total',
        'Parametros': ['cnpj', 'inicioAAAAMM', 'fimAAAAMM'],
        'Tipo': "Relatórios", 'Relatorios': [],
        'Formato': 'Excel (.xlsx)', 'Grupo': 'Prova'},
    "Consulta BO - Cartões Sumarizados e detalhado - 2010 a 2019": {
        'Pesquisa': 'cartões',
        'Parametros': ['cnpj', 'inicioAAAAMM', 'fimAAAAMM', 'osf'],
        'Tipo': "Dados", 'Relatorios': ['Consulta 2 com Operadoras de Cartão'],
        'Grupo': 'Cartao', 'Principal': True
    }
}


def check_if_port_is_open(remote_server_host: str, port: int):
    sock = None
    try:
        logger.debug(f"Buscando servidor {remote_server_host}...")
        remote_server_ip = socket.gethostbyname(remote_server_host)
        logger.debug(f"Acessando porta {port} do servidor {remote_server_host}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        result = sock.connect_ex((remote_server_ip, port))
        return result == 0
    except socket.gaierror:
        logger.debug(f'Não consegui descobrir que endereço é esse: {remote_server_host}')
        return False
    except socket.error:
        logger.debug(f'Não consegui conectar nesta porta: {remote_server_host}:{port}')
        return False
    finally:
        if sock is not None:
            sock.close()


def does_environment_need_proxy() -> bool:
    return check_if_port_is_open(proxy_srv, proxy_port)


def set_proxy():
    # Proxy setup para rede interna Sefaz, apenas se fizer sentido...
    if does_environment_need_proxy():
        logger.info('Ajustando proxy da Sefaz-SP...')
        proxy_sefaz = f'http://{proxy_srv}:{proxy_port}'
        os.environ["http_proxy"] = proxy_sefaz
        os.environ["HTTP_PROXY"] = proxy_sefaz
        os.environ["https_proxy"] = proxy_sefaz
        os.environ["HTTPS_PROXY"] = proxy_sefaz
        os.environ["ftp_proxy"] = proxy_sefaz
        os.environ["FTP_PROXY"] = proxy_sefaz
        os.environ["no_proxy"] = "fazenda.sp.gov.br, localhost"

        # reseta o cache de proxy
        install_opener(None)
        try:
            urlopen('https://www.gov.br', timeout=5)
            logger.info('Acesso ao proxy funcionando...')
        except URLError as e:
            raise WebScraperException(f'Conexão com a Internet está inoperante, mesmo com proxy Sefaz: {e}')
    else:
        logger.info('Não está no ambiente interno Sefaz, não precisa definir proxy...')


last_progress = None


def get_efd_pva_version(pva_version: str = None, log_function=GeneralFunctions.logger.info) -> Path:
    if pva_version is None:
        url = "http://www.sped.fazenda.gov.br/SpedFiscalServer/WSConsultasPVA/WSConsultasPVA.asmx"
        headers = {'content-type': 'text/xml'}
        body = """<?xml version="1.0" encoding="utf-8"?>
            <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
            xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
              <soap12:Body>
                <consultarVersaoAtualPVA xmlns="http://br.gov.serpro.spedfiscalserver/consulta" />
              </soap12:Body>
            </soap12:Envelope>"""
        response = requests.post(url, data=body, headers=headers)
        pva_version = re.match(r'.*<consultarVersaoAtualPVAResult>(.*)</consultarVersaoAtualPVAResult>',
                               response.text).group(1)

    html = urlopen('https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/'
                   'declaracoes-e-demonstrativos/sped-sistema-publico-de-escrituracao-digital/'
                   'escrituracao-fiscal-digital-efd/escrituracao-fiscal-digital-efd')
    bs = BeautifulSoup(html, 'html.parser')
    linhas = bs.find_all('a', {'class': 'external-link'})
    global last_progress
    last_progress = time.process_time()

    def _progress(blocknum, bs, size):
        now = time.process_time()
        global last_progress
        if now - last_progress > 0.05:
            msg = f'Baixando versão {pva_version} do EFD PVA ICMS ({blocknum * bs / size:.2%})'
            log_function(msg)
            last_progress = now

    for tag in linhas:
        link = tag.attrs['href']
        if link.find(pva_version) > 0 and link.find('.exe') > 0:
            download_path = Path('tmp') / tag.text
            log_function(f'Iniciando download de EFD PVA ICMS')
            urllib.request.urlretrieve(link, download_path, _progress)
            log_function('Encerrado download de EFD PVA ICMS')
            return download_path
    raise WebScraperException(f'Não localizei arquivo da versão {pva_version} pra baixar!')


def get_selic_last_years():
    html = urlopen(
        'https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/'
        'pagamentos-e-parcelamentos/taxa-de-juros-selic')
    bs = BeautifulSoup(html, 'html.parser')
    linhas = bs.find_all('tr', {'class': ['even', 'odd']})
    lista = [td.text for tr in linhas for td in tr.findChildren('td') if td.text != '']
    anos, mes, selic = [], [], []
    ano_atual, mes_atual = 0, 0
    preenchendo_anos = False
    for i in lista:
        if i == 'Mês/Ano':
            preenchendo_anos = True
        elif i.isdigit() and preenchendo_anos:
            if datetime.date.today().year - int(i) >= 10:
                break
            anos.append(int(i))
        elif i.strip(' ') == '' and preenchendo_anos:
            preenchendo_anos = False
        elif i.capitalize() in GeneralFunctions.meses:
            mes_atual = GeneralFunctions.meses.index(i)
            ano_atual = 0
        else:
            referencia = datetime.date(anos[ano_atual], mes_atual + 1, 1)
            mes.append(referencia)
            selic.append(i.rstrip('%').replace(',', '.'))
            ano_atual = ano_atual + 1
    return pd.DataFrame(data=selic, index=pd.to_datetime(mes), columns=['selic'], dtype='float')


def get_latest_ufesps_from(ano: int):
    html = urlopen('https://legislacao.fazenda.sp.gov.br/Paginas/ValoresDaUFESP.aspx')
    bs = BeautifulSoup(html, 'html.parser')
    bs.prettify()
    linhas = bs.findAll('tr', {'class': ['sefazTableEvenRow-pagina2', 'sefazTableOddRow-pagina2']})
    tuplas = [(tr.next, tr.next.nextSibling) for tr in linhas][:10]
    tuplas.reverse()
    return [(int(t[0].text[-4:]), float(t[1].text[-5:].replace(',', '.'))) for t in tuplas if int(t[0].text[-4:]) > ano]


def get_latest_version_link_and_notes() -> (str, str, str):
    try:
        resposta = requests.get(project_releases_url, timeout=5)
        resposta.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.exception('Falha no acesso ao GitHub')
        raise WebScraperException(f'Falha no acesso ao GitHub: {err}')
    dados = resposta.json()
    return re.sub(r'[a-zA-Z]', '', dados['tag_name']), dados['html_url'], dados['body']


def get_cnpj_data(cnpj: str):
    # Token alepmendonca@gmail.com: b51c37f39a1c25463ccdd8e16dfc0cea1622fe874606d0a714b1447c8de6a8ae
    # Token apmendonca@fazenda.sp.gov.br: 57649b8e0b1f8b95429ae19ed5c7fd8143aa947afcf74735bf8f74d1371e7456
    ws_url = f'https://www.receitaws.com.br/v1/cnpj/{cnpj}/days/90'
    ws_public_url = f'https://www.receitaws.com.br/v1/cnpj/{cnpj}'
    try:
        resposta = requests.get(ws_url, headers={
            'Authorization': 'Bearer 57649b8e0b1f8b95429ae19ed5c7fd8143aa947afcf74735bf8f74d1371e7456',
            'Content-Type': 'application/json'
        }, timeout=10)
        resposta.raise_for_status()
    except requests.exceptions.HTTPError as payerr:
        if payerr.response.status_code == 402 and payerr.response.reason == 'Payment Required':
            resposta = requests.get(ws_public_url, headers={
                'Content-Type': 'application/json'
            }, timeout=10)
            resposta.raise_for_status()
        else:
            logger.exception('Falha no acesso ao ReceitaWS')
            raise WebScraperException(f'Falha no acesso ao ReceitaWS: {payerr}')
    return resposta.json()


def choose_right_client_certificate(parte_titulo: str, nome_procurado: str):
    window_cert = '[CLASS:#32770;TITLE:Certificado]'
    window_browser = f"[CLASS:Chrome_WidgetWin_1; REGEXPTITLE:(?i)(.*{parte_titulo}.*)]"
    ultimo_nome_encontrado = ''
    achou = False
    while not achou:
        autoit.win_activate(window_browser)
        if ultimo_nome_encontrado == '':
            autoit.send('{TAB}{SPACE}')
        else:
            for i in range(0, 4):
                autoit.send('{TAB}')
            autoit.send('{DOWN}{TAB}{SPACE}')
        try:
            autoit.win_wait(window_cert, 1)
            autoit.win_activate(window_cert)
        except AutoItError:
            logger.debug('Não encontrou janela de certificado, já deve ter o certificado na sessão')
            return

        nome_encontrado = autoit.control_get_text(window_cert, '[CLASS:RICHEDIT50W;INSTANCE:1]')
        if ultimo_nome_encontrado == nome_encontrado:
            autoit.control_click(window_cert, '[CLASS:Button;INSTANCE:5]')
            raise WebScraperException(f'Não encontrei o certificado de {nome_procurado}!')
        if nome_procurado == nome_encontrado:
            ultimo_texto = ''
            texto_encontrado = '1'
            autoit.send('{TAB}{RIGHT}{TAB}{TAB}')
            while ultimo_texto != texto_encontrado or not achou:
                texto_encontrado = autoit.control_get_text(window_cert, '[CLASS:RICHEDIT50W;INSTANCE:1]')
                if texto_encontrado.find('O = ICP-Brasil') > 0:
                    achou = True
                autoit.control_send(window_cert, '[CLASS:SysListView32;INSTANCE:1]', '{DOWN}')
                ultimo_texto = texto_encontrado
            autoit.control_click(window_cert, '[CLASS:Button;INSTANCE:3]')
        else:
            autoit.control_click(window_cert, '[CLASS:Button;INSTANCE:5]')
        ultimo_nome_encontrado = nome_encontrado
        autoit.win_activate(window_browser)
        if achou:
            autoit.send('{TAB}{SPACE}')
            break


def set_password_for_certificate_in_browser(password: str, timeout=5):
    popup_senha = "[CLASS:#32770; TITLE:Introduzir PIN]"
    try:
        autoit.win_wait(popup_senha, timeout)
    except AutoItError:
        # acredita que já passaram o PIN no popup, segue o jogo
        logger.debug('Não localizou pop-up de certificado digital, confia que já preencheram a senha e desiste')
        return

    try:
        autoit.win_activate(popup_senha)
        logger.debug('Achou pop-up de certificado digital')
        autoit.control_focus(popup_senha, "[CLASS:RICHEDIT50W; INSTANCE:1]")
        logger.debug('Tenta colocar senha ')
        autoit.control_send(popup_senha, "[CLASS:RICHEDIT50W; INSTANCE:1]", password)
        autoit.control_click(popup_senha, "[CLASS:Button; INSTANCE:1]")
    except Exception:
        logger.exception('Falha no preenchimento de senha no pop-up de certificado digital')
        raise

    # verifica se não reapareceu a janela - se apareceu, melhor desistir pra não bloquear smartcard
    try:
        time.sleep(1)
        autoit.win_wait(popup_senha, 2)
    except AutoItError as e:
        logger.debug(
            'Não achei de novo o pop-up de certificado digital, acredita que deu certo a senha passada antes')
        return

    texto = autoit.control_get_text(popup_senha, '[CLASS:Static; INSTANCE:2]')
    autoit.control_click(popup_senha, '[CLASS:Button; INSTANCE:2]')
    if texto == 'PIN incorreto':
        raise WebScraperException('Senha incorreta para certificado!')
    else:
        raise WebScraperException("O pop-up de senha do smartcard não foi fechado! Verificar manualmente!")


def set_password_in_browser(parte_titulo: str, username: str, password: str):
    navegador = f"[CLASS:Chrome_WidgetWin_1; REGEXPTITLE:(?i)(.*{parte_titulo}.*)]"
    try:
        autoit.win_wait(navegador, 5)
        autoit.win_activate(navegador)
        autoit.send(username + "{TAB}")
        senha_corrigida = re.sub(r"([!#+^{}])", r"{\1}", password)
        autoit.send(senha_corrigida + "{ENTER}")

        # dá 2 chances pra mudar o título da janela (sinal que fez login)
        time.sleep(2)
        autoit.win_wait(navegador, 1)
        time.sleep(2)
        autoit.win_wait(navegador, 1)
        raise WebScraperException("O pop-up de login/senha do Chrome não foi fechado! "
                                  "Talvez usuário e senha estejam incorretos!")
    except AutoItError:
        pass


class WebScraperException(Exception):
    pass


class WebScraperTimeoutException(WebScraperException):
    pass


_T = TypeVar('T')


class _PepeSingleton:
    _instances = {}
    _lock: threading.Lock = threading.Lock()
    _login_cert = [pepe.Cadesp, pepe.ContaFiscalICMS, pepe.Pfe]

    @classmethod
    def get(cls, pepe_class: type[_T]) -> _T:
        # versão thread safe do singleton
        with cls._lock:
            if pepe_class not in cls._instances or not cls._instances[pepe_class].autenticado():
                instance = pepe_class()
                logger.info(f"Autenticando no sistema {pepe_class.__name__}...")
                try:
                    if pepe_class == pepe.LaunchPad:
                        instance.login_lpad(GeneralConfiguration.get().intranet_login,
                                            GeneralConfiguration.get().intranet_pass)
                    elif pepe_class == pepe.SpSemPapel:
                        instance.login(GeneralConfiguration.get().sigadoc_login,
                                       GeneralConfiguration.get().sigadoc_pass)
                    elif pepe_class in cls._login_cert:
                        t = GeneralFunctions.ThreadWithReturnValue(target=set_password_for_certificate_in_browser,
                                                                   args=[GeneralConfiguration.get().certificado_pass,
                                                                         10])
                        t.start()
                        instance.login_cert(GeneralConfiguration.get().certificado)
                    else:
                        instance.login(GeneralConfiguration.get().intranet_login,
                                       GeneralConfiguration.get().intranet_pass)
                except pepe.AuthenticationError as aerr:
                    raise WebScraperException(f"Erro de autenticação no sistema {pepe_class}: {aerr}")
                cls._instances[pepe_class] = instance
        return cls._instances[pepe_class]


def get_launchpad_report(report_name: str, report_id: int, sheets: list[str], data: list[str],
                         download_path: Path, parameters: dict):
    ws = _PepeSingleton.get(pepe.LaunchPad)
    logger.info(f'Baixando relatório {report_name}, params {parameters}...')
    ws.baixar_relatorio_ldap(report_id, str(download_path.absolute()), parameters,
                             sheets if sheets else None,
                             data if data else None,
                             csv_column_separator=",",
                             timeout_relatorio=int(LAUNCHPAD_MAX_TIME_WAIT_SECONDS / 60))
    logger.info(f'Relatório {report_name} baixado, params {parameters}')


def get_osfs_em_execucao() -> list[str]:
    try:
        pgsf = _PepeSingleton.get(pepe.Pgsf)
        logger.info('Acessando PGSF para listar OSFs em execução...')
        osfs = pgsf.listar_osfs(situacao=PgsfSituacaoOSF.SITUACAO_EM_EXEC)
        return [f'{osf["osf"]} - {osf["ie"]} - {osf["razao_social"]} - {osf["forma_acionamento"]}'
                for osf in osfs]
    except Exception as e:
        logger.exception("Erro ao listar OSFs no PGSF")
        raise WebScraperException(f"Erro ao listar OSFs no PGSF: {e}")


class SeleniumWebScraper:

    def __init__(self, download_path: Path = None, hidden=False):
        # Main path setup
        if getattr(sys, "frozen", False):
            self.script_path = Path(path.dirname(sys.executable))
        else:
            self.script_path = Path(path.dirname(path.abspath(__file__)))
        self.tmp_path = self.script_path / 'tmp'
        self.download_path = download_path if download_path else self.tmp_path

        self.driver = None
        self.hidden = hidden
        self.launchpad_lock = threading.Lock()
        self.running_launchpad = False

        os.makedirs(str(self.tmp_path), exist_ok=True)
        if self.download_path:
            os.makedirs(str(self.download_path), exist_ok=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self.driver is not None:
            try:
                self.__get_driver().close()
            except:
                pass
            self.__get_driver().quit()
            self.driver = None

    def __get_driver(self) -> ChromiumDriver:
        if self.driver is None:
            # self.initialize_edge_driver(self.hidden)
            self.initialize_chrome_driver(self.hidden)
        return self.driver

    def initialize_chrome_driver(self, headless=False):
        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        parser = Dispatch("Scripting.FileSystemObject")
        chrome_full_version = parser.GetFileVersion(chrome_path)
        chrome_major_version = chrome_full_version.split(".")[0]
        (self.script_path / "driver").mkdir(exist_ok=True)
        driver_zip_path = self.script_path / "driver" / ("chromedriver_" + chrome_major_version + ".zip")

        # baixa nova versão do chromedriver apenas se não baixou o zip da última versão
        if not driver_zip_path.is_file():
            # apaga chromedrivers antigos
            for old_zip in (x for x in os.listdir(path.join(self.script_path, 'driver')) if
                            x.startswith('chromedriver_') and x.endswith('zip')):
                (self.script_path / 'driver' / old_zip).unlink()

            driver_version_url = (
                    "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_"
                    + chrome_major_version
            )
            driver_version = requests.get(driver_version_url).text
            driver_zip_url = (
                    "https://chromedriver.storage.googleapis.com/"
                    + driver_version
                    + "/chromedriver_win32.zip"
            )
            urllib.request.urlretrieve(driver_zip_url, driver_zip_path)

            with zipfile.ZipFile(driver_zip_path, "r") as f:
                driver_exe_path = path.join(self.script_path, "driver")
                f.extract("chromedriver.exe", driver_exe_path)

        # Webdriver setup
        options = webdriver.chrome.options.Options()
        options.add_argument("--log-level=3")  # minimal logging
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--kiosk-printing")
        options.add_argument("--enable-print-browser")
        # apenas rola imprimir PDF em modo headless, o que nao eh muito bom pra debug...
        if headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
        print_settings = {
            "recentDestinations": [{
                "id": "Save as PDF",
                "origin": "local",
                "account": ""
            }],
            "selectedDestinationId": "Save as PDF",
            "version": 2,
        }
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": str(self.tmp_path),
                "savefile.default_directory": str(self.tmp_path),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "printing.print_preview_sticky_settings.appState": json.dumps(print_settings)
            },
        )  # removes DevTools msg
        options.add_experimental_option(
            "excludeSwitches", ["enable-logging", "enable-automation"]
        )
        options.add_experimental_option("useAutomationExtension", False)
        driver_path = path.join(self.script_path, "driver", "chromedriver.exe")
        self.driver = webdriver.Chrome(driver_path, options=options)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.driver.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/83.0.4103.53 Safari/537.36"
            },
        )
        self.driver.implicitly_wait(1)

    def __login_certificado_digital(self, parte_titulo: str, config=GeneralConfiguration.get()):
        choose_right_client_certificate(parte_titulo, config.certificado)
        set_password_for_certificate_in_browser(config.certificado_pass)

    def __pgsf_login(self):
        try:
            self.__get_driver().get(pgsf_url)
        except WebDriverException as we:
            if we.msg.find('ERR_NAME_NOT_RESOLVED') >= 0:
                raise WebScraperException('Não foi possível acessar o site do PGSF! '
                                          'Verifique se o computador está conectado na rede da Sefaz.')

        input_username = self.__get_driver().find_element(By.ID, "userID2")
        input_username.clear()
        input_username.send_keys(GeneralConfiguration.get().intranet_login)
        input_password = self.__get_driver().find_element(By.ID, "password")
        input_password.clear()
        input_password.send_keys(GeneralConfiguration.get().intranet_pass + Keys.RETURN)

        try:
            WebDriverWait(self.__get_driver(), 2).until_not(EC.visibility_of_element_located((By.ID, "userID2")))
        except TimeoutException:
            try:
                msg = self.__get_driver().find_element(By.CLASS_NAME, 'wpsFieldErrorText').text
                raise WebScraperException(f'Falha no acesso ao PGSF: {msg}')
            except NoSuchElementException:
                pass

    def __pgsf_go_to_submenu(self, nome: str):
        resultado = self.__get_driver().find_element(By.XPATH, f'//script[contains(., \"{nome}\")]')
        resultado_text = resultado.get_attribute("innerHTML").strip()
        relative_link = re.search('"/(.+?)/"', resultado_text).group(1)
        absolute_link = pgsf_url + "/" + relative_link
        self.__get_driver().get(absolute_link)

    def __save_as_pdf(self, download_path: Path):
        # serve para garantir que a renderização de PDF siga o CSS de tela, não de impressão
        command_url = f'/session/{self.driver.session_id}/chromium/send_command'
        self.__get_driver().command_executor._commands["send_command"] = ("POST", command_url)
        params = {'cmd': 'Emulation.setEmulatedMedia', 'params': {'media': 'screen'}}
        self.__get_driver().execute('send_command', params)

        if self.hidden:
            a = self.__get_driver().execute_cdp_cmd(
                "Page.printToPDF", {"path": download_path.name, "format": 'A4'})
            bytes_pdf = base64.b64decode(a['data'], validate=True)
            if bytes_pdf != b'%PDF':
                raise WebScraperException('Arquivo de impressão PDF gerado com falha!')
            with download_path.open('wb') as f:
                f.write(bytes_pdf)
        else:
            download_path.unlink(missing_ok=True)
            self.__get_driver().execute_script("window.print();")
            move_downloaded_file(self.tmp_path, f'{self.__get_driver().title}.pdf', download_path)

    def __sigadoc_login(self, config=GeneralConfiguration.get()):
        self.__get_driver().get(sem_papel_url)

        input_username = self.__get_driver().find_element(By.ID, "username")
        input_username.clear()
        input_username.send_keys(config.sigadoc_login)
        input_password = self.__get_driver().find_element(By.ID, "password")
        input_password.clear()
        input_password.send_keys(config.sigadoc_pass + Keys.RETURN)

        try:
            WebDriverWait(self.__get_driver(), 2).until_not(EC.visibility_of_element_located((By.ID, "username")))
        except TimeoutException:
            try:
                msg = self.__get_driver().find_element(By.CLASS_NAME, 'alert-danger').text
                raise WebScraperException(f'Falha no acesso ao Sem Papel: {msg}')
            except NoSuchElementException:
                pass

    def get_full_OSF(self, osf: str, filename='EmissaoOSF.pdf'):
        try:
            pgsf = _PepeSingleton.get(pepe.Pgsf)
            logger.info('Acessando PGSF para pegar OSF completa...')
            with open(filename, mode='wb') as f:
                f.write(pgsf.obter_pdf_osf(osf, completa=True))
            logger.warn('Realizado download da OSF completa!')
        except Exception as e:
            logger.exception("Erro ao baixar PDF da OSF " + osf + " no PGSF")
            raise WebScraperException(f"Erro ao baixar PDF da OSF {osf} no PGSF: {e}")

    def get_simple_OSF(self, osf: str, filename: str):
        try:
            pgsf = _PepeSingleton.get(pepe.Pgsf)
            logger.info('Acessando PGSF para pegar OSF do contribuinte...')
            with open(filename, mode='wb') as f:
                f.write(pgsf.obter_pdf_osf(osf, completa=False))
            logger.warn('Realizado download da OSF do contribuinte!')
        except Exception as e:
            logger.exception("Erro ao baixar PDF da OSF " + osf + " no PGSF")
            raise WebScraperException(f"Erro ao baixar PDF da OSF {osf} no PGSF: {e}")

    def create_aiim_for_osf(self, osf: str) -> str:
        logger.info(f'Acessando PGSF para criar número de AIIM relacionado à OSF {osf}')
        self.__pgsf_login()
        try:
            self.__pgsf_go_to_submenu('Geração de Número')
            logger.info('Login realizado com sucesso')

            # Switch to inner frame
            iframe = self.__get_driver().find_element(By.NAME, "PC_Z7_TBK0BB1A0GT000I7RN0S7C10U0000000_AIIM_Geracao")
            self.__get_driver().switch_to.frame(iframe)

            logger.info('Solicitando novo número de AIIM...')
            self.__get_driver().get("https://portal60.sede.fazenda.sp.gov.br/AIIMWeb/menu.do?path=preparaGeracaoOSF")
            self.__get_driver().find_element(By.NAME, "dsDoc1").send_keys(osf)
            self.__get_driver().find_element(By.ID, "button1").click()

            bs = BeautifulSoup(self.__get_driver().page_source, 'html.parser')
            linhas = [re.sub(r'[\s\n]', '', td.text) for td in bs.find_all('td', {'class': 'texto1'})]
            if linhas[-1] == '' and len(bs.find_all('td', {'class': 'mensErro'})) > 1:
                raise WebScraperException(bs.find_all('td', {'class': 'mensErro'})[1].text.replace('\n', ''))
            else:
                logger.warning(f'Número novo de AIIM {linhas[-1]} obtido!')
                return linhas[-1]
        except Exception as e:
            logger.exception("Erro ao gerar AIIM para OSF " + osf + " no PGSF")
            raise WebScraperException(f"Erro ao gerar AIIM para OSF {osf} no PGSF: {e}")

    def get_aiims_for_osf(self, osf: str) -> list:
        logger.info(f'Acessando PGSF para verificar AIIMs gerados para OSF {osf}')
        self.__pgsf_login()
        try:
            # Access "AIIM -> Geração de Número" page directly
            self.__pgsf_go_to_submenu('Geração de Número')
            logger.info('Login realizado com sucesso')

            # Switch to inner frame
            iframe = self.__get_driver().find_element(By.NAME, "PC_Z7_TBK0BB1A0GT000I7RN0S7C10U0000000_AIIM_Geracao")
            self.__get_driver().switch_to.frame(iframe)

            self.__get_driver().get('https://portal60.sede.fazenda.sp.gov.br/AIIMWeb/menu.do?path=devolucaoLista')
            logger.info('Processando informações da lista de AIIMs gerados')
            bs = BeautifulSoup(self.__get_driver().page_source, 'html.parser')
            linhas = [re.sub(r'[\s\n]', '', td.text) for td in bs.find_all('td', {'class': 'texto6'})]
            valores = [valor for valor in linhas if
                       (valor.startswith('4.') and linhas[linhas.index(valor) - 1] == osf)]
            valores.sort()
            return valores
        except Exception as e:
            logger.exception("Erro ao consultar AIIMs da OSF " + osf + " no PGSF")
            raise WebScraperException(f"Erro ao consultar AIIMs da OSF {osf} no PGSF: {e}")

    def print_sat_cupom(self, cupons: list) -> list[Path]:
        logger.info("Consultando cupons SAT")
        try:
            self.__get_driver().get(sat_consulta_url)

            paths = []
            for cupom in cupons:
                self.__get_driver().find_element(By.ID, "conteudo_txtChaveAcesso").click()
                self.__get_driver().find_element(By.ID, "conteudo_txtChaveAcesso").clear()
                self.__get_driver().find_element(By.ID, "conteudo_txtChaveAcesso").send_keys(cupom)
                time.sleep(1)
                try:
                    recaptcha_frame = self.driver.find_element(By.XPATH,
                                                               '//*[@id="ReCaptchContainer"]/div/div/iframe')
                    self.__get_driver().switch_to.frame(recaptcha_frame)
                    self.__get_driver().find_element(By.CLASS_NAME, 'recaptcha-checkbox-unchecked').click()
                    try:
                        self.__get_driver().find_element(By.ID, 'lblMensagemCaptcha')
                    except NoSuchElementException:
                        logger.warning("MOSTRE QUE VOCÊ NÃO É UM ROBÔ NO SITE DE CONSULTA SAT!!!")
                        WebDriverWait(self.__get_driver(), 60).until(
                            EC.visibility_of_element_located((By.CLASS_NAME, "recaptcha-checkbox-checked")))
                    self.__get_driver().switch_to.parent_frame()
                except TimeoutException:
                    raise WebScraperException('Você não clicou no captcha do site do SAT, '
                                              'não consigo fazer tudo sozinho...')
                try:
                    element = self.__get_driver().find_element(By.ID, 'dialog-modal')
                    if element.text.startswith('As consultas a partir de sua faixa de IP estão bloqueadas'):
                        logger.warning(
                            f'Site de consulta SAT bloqueou acessos. Apenas consegui baixar {len(paths)} amostras')
                        break
                except NoSuchElementException:
                    pass
                self.__get_driver().find_element(By.ID, "conteudo_btnConsultar").click()
                pdf_file = self.tmp_path / f'{cupom}.pdf'
                cupom_element = self.__get_driver().find_element(By.ID, "divTelaImpressao")
                self.__save_as_pdf(pdf_file)
                paths.append(pdf_file)
                self.__get_driver().find_element(By.ID, 'conteudo_btnSair').click()
            return paths
        except Exception as e:
            logger.exception("Erro ao consultar cupons SAT na consulta pública")
            raise WebScraperException(f"Erro ao consultar cupons SAT na consulta pública: {e}")

    def get_nfe_inutilizacoes(self, cnpj: str, ano_inicial: int, ano_final: int, print=False) -> list[dict | Path]:
        logger.info("Consultando NF-e Inutilizações")
        self.__get_driver().get(nfe_consulta_url)

        inutilizacoes = []
        try:
            for ano in range(ano_inicial, ano_final + 1):
                self.__get_driver().find_element(By.XPATH, '/html/body/div[2]/form/div[3]/ul/li[2]/a').click()
                self.__get_driver().find_element(By.ID, 'ContentMain_tbxCnpjNFe').send_keys(re.sub(r'\D', '', cnpj))
                try:
                    Select(self.__get_driver().find_element(By.ID, 'ContentMain_ddlAno')).select_by_value(
                        str(ano - 2000))
                except NoSuchElementException as nse:
                    if nse.msg.startswith('Cannot locate option'):
                        # está pedindo um ano que a consulta já não disponibiliza mais
                        logger.warning(f'Não estão disponíveis para consulta as inutilizações de {ano}.')
                        continue
                    else:
                        raise nse
                logger.warning("MOSTRE QUE VOCÊ NÃO É UM ROBÔ NO SITE DE CONSULTA NF-E INUTILIZAÇÕES!!!")
                try:
                    recaptcha_frame = self.driver.find_element(By.XPATH,
                                                               '//*[@id="ContentMain_divReCaptcha"]/div/div/div/iframe')
                    self.__get_driver().switch_to.frame(recaptcha_frame)
                    self.driver.find_element(By.CLASS_NAME, 'recaptcha-checkbox-unchecked').click()
                    WebDriverWait(self.__get_driver(), 60).until(
                        EC.visibility_of_element_located((By.CLASS_NAME, "recaptcha-checkbox-checked")))
                    self.__get_driver().switch_to.parent_frame()
                except TimeoutException:
                    raise WebScraperException('Você não clicou no captcha do site NF-e Inutilizações, '
                                              'não consigo fazer tudo sozinho...')
                self.__get_driver().find_element(By.ID, "btConsultaInut").click()

                tabela = self.__get_driver().find_element(By.CLASS_NAME, "gridViewTable")
                if len(tabela.find_elements(By.XPATH, './/tbody/tr')) == 1 \
                        and tabela.find_element(By.XPATH, './/tbody/tr/td').text == 'Nenhum registro encontrado':
                    if print:
                        pdf_file = self.tmp_path / f'sem_inutilizacoes_{ano}.pdf'
                        self.__save_as_pdf(pdf_file)
                        inutilizacoes.append(pdf_file)
                    continue
                try:
                    paginador = self.__get_driver().find_element(By.CLASS_NAME, "gridViewPager")
                    paginas = len(paginador.find_elements(By.XPATH, '//td/table/tbody/tr/td'))
                except NoSuchElementException:
                    paginas = 1
                for pagina in range(1, paginas + 1):
                    linhas = self.__get_driver().find_elements(By.CLASS_NAME, 'gridViewRow')
                    linhas.extend(self.__get_driver().find_elements(By.CLASS_NAME, 'gridViewRowAlternate'))
                    if print:
                        pdf_file = self.tmp_path / f'inutilizacoes_{ano}_{pagina}.pdf'
                        self.__save_as_pdf(pdf_file)
                        inutilizacoes.append(pdf_file)
                    else:
                        inutilizacoes.extend(
                            {
                                'serie': linha.find_elements(By.TAG_NAME, 'td')[1].text,
                                'inicio': linha.find_elements(By.TAG_NAME, 'td')[2].text,
                                'fim': linha.find_elements(By.TAG_NAME, 'td')[3].text,
                                'timestamp': linha.find_elements(By.TAG_NAME, 'td')[5].text
                            } for linha in linhas)
                    if pagina < paginas:
                        self.__get_driver().find_element(
                            By.XPATH, f'//*[@class="gridViewPager"]/td/table/tbody/tr/td[{pagina + 1}]').click()
                        WebDriverWait(self.__get_driver(), 10).until(
                            EC.element_to_be_clickable((By.XPATH,
                                                        f'//*[@class="gridViewPager"]/td/table/tbody/tr/td[{pagina}]/a')))
                self.__get_driver().find_element(By.ID, 'ContentMain_btnNovaConsulta').click()
            return inutilizacoes
        except Exception as e:
            logger.exception("Erro ao consultar inutilizações de NF-e do CNPJ " + cnpj + " na consulta pública")
            raise WebScraperException(f"Erro ao consultar inutilizações de NF-e do CNPJ {cnpj} "
                                      f"na consulta pública: {e}")

    def get_full_cadesp(self, ie: str, filename: Path):
        cadesp = _PepeSingleton.get(pepe.Cadesp)
        logger.info(f'Baixando no Cadesp extrato de {ie}...')
        cadesp.baixar_pdf_estabelecimento(ie, str(filename.absolute()))

    def get_conta_fiscal(self, ie: str, ano_inicio: int, ano_fim: int, filename: Path):
        # caso o saldo do último mês do ano_fim seja credor, pega outros anos até ficar negativo
        tmp_files = []
        try:
            cf = _PepeSingleton.get(pepe.ContaFiscalICMS)
            ano = ano_inicio
            cf_credora = False
            while ano <= ano_fim or (ano <= datetime.date.today().year and cf_credora):
                logger.info(f"Consultando Conta Fiscal de {ano}...")
                html = cf.consulta_conta_fiscal_icms_declarado(ie=ie, referencia=ano, recolhimentos_especiais=True)
                if ano >= ano_fim:
                    soup = BeautifulSoup(html, features='lxml')
                    meses_existentes_tags = soup.find_all("input", {
                        "name": re.compile(
                            r"ctl00\$MainContent\$rptContaFiscalMes\$ctl\d+\$gdvResultadoDetalhe\$ctl\d+\$hdfReferencia")
                    })
                    ultimo_mes = int(sorted(set([t['value'] for t in meses_existentes_tags]))[-1][:2])
                    tag_id_ultimo_mes = \
                        [t['id'] for t in meses_existentes_tags if
                         t['value'] == f'{str(ultimo_mes).zfill(2)}{str(ano)[-2:]}'][0]
                    id_ultimo_mes = re.search(r'.*_\d+_', tag_id_ultimo_mes).group(0)
                    tags_texto_ultimo_mes = soup.find_all("span", {"id": re.compile(rf"{id_ultimo_mes}.*")})
                    cf_credora = any([t.text.find('SALDO CREDOR') >= 0 for t in tags_texto_ultimo_mes])
                novo_nome = self.tmp_path / f'Conta Fiscal {ano}.pdf'
                logger.info(f"Gerando impressão da Conta Fiscal de {ano}...")
                cf.imprime_conta_fiscal_icms_declarado(html, str(novo_nome.absolute()))
                tmp_files.append(novo_nome)
                ano += 1
            PDFExtractor.merge_pdfs(filename, tmp_files)
        except Exception as e:
            logger.exception("Erro ao baixar Conta Fiscal da IE " + ie)
            raise WebScraperException(f"Erro ao baixar Conta Fiscal da IE {ie}: {e}")

    def get_gias_apuracao(self, ie: str, inicio: datetime.date, fim: datetime.date,
                          evento: threading.Event | None = None,
                          apenas_ultima_entregue=False) \
            -> list[dict]:
        try:
            logger.info("Acessando apuração de GIA")
            pfe = _PepeSingleton.get(pepe.Pfe)
            dados_gias = []
            if evento.is_set():
                return []
            return pfe.listar_gias(ie, inicio, fim, incluir_recusadas=False,
                                   apenas_ultima_entregue=apenas_ultima_entregue)
        except Exception as e:
            logger.exception("Erro ao coletar dados de apuração da GIA da IE " + ie)
            raise WebScraperException(f"Erro ao coletar dados de apuração da GIA da IE {ie}: {e}")

    def __print_gia_apuracao_subpage(self, ie: str, apuracoes: list[datetime.date],
                                     relatorio: GIARelatorio, subrelatorios: list[GIASubRelatorio]) -> list[Path]:
        try:
            dados_gias = self.get_gias_apuracao(ie, apuracoes[0], apuracoes[-1],
                                                apenas_ultima_entregue=True)

            pfe = _PepeSingleton.get(pepe.Pfe)
            referencias = [d.strftime('%m/%Y') for d in apuracoes]
            paths = {}
            for gia in dados_gias:
                if gia['referencia'] not in referencias:
                    continue
                logger.info(f'Imprimindo GIA {relatorio.value} da referência {gia["referencia"]}...')

                referencia = f'{gia["referencia"][3:]}{gia["referencia"[:2]]}'
                path_apuracao = self.tmp_path / f'giaapuracao{referencia}.pdf'
                pfe.baixar_pdf_gia(ie, gia['protocolo'], gia['controle'],
                                   str(path_apuracao.absolute()), GIARelatorio.GIA_RELATORIO_APURACAO_PROPRIA)
                paths[referencia] = [path_apuracao]
                for subrelatorio in subrelatorios:
                    try:
                        pdf_file = self.tmp_path / f'giadetalhe{subrelatorio.value}-{referencia}.pdf'
                        pfe.baixar_pdf_gia(ie, gia['protocolo'], gia['controle'],
                                           str(path_apuracao.absolute()),
                                           GIARelatorio.GIA_RELATORIO_APURACAO_PROPRIA,
                                           subrelatorio)
                        paths[referencia].append(pdf_file)
                    except KeyError:
                        # a página de detalhe não tem conteúdo, então desiste dela
                        pass
            return [pdf for k in sorted(paths.keys()) for pdf in paths[k]]
        except Exception as e:
            logger.exception("Erro ao coletar dados de apuração da GIA da IE " + ie)
            raise WebScraperException(f"Erro ao coletar dados de apuração da GIA da IE {ie}: {e}")

    def print_gia_entregas(self, ie: str, inicio: datetime.date, fim: datetime.date) -> list[Path]:
        try:
            logger.info(f'Imprimindo extrato de GIAs entregues pela IE {ie}...')
            # TODO resolver
            relatorio = self.tmp_path / 'giaentregas.pdf'
            self.__save_as_pdf(relatorio)
            return [relatorio]
        except Exception as e:
            logger.exception("Erro ao levantar GIAs da IE " + ie)
            raise WebScraperException(f"Erro ao levantar GIAs da IE {ie}: {e}")

    def print_gia_apuracao(self, ie: str, apuracoes: list[datetime.date]) -> list[Path]:
        return self.__print_gia_apuracao_subpage(ie, apuracoes, GIARelatorio.GIA_RELATORIO_APURACAO_PROPRIA, [])

    def print_gia_outros_debitos(self, ie: str, apuracoes: list[datetime.date]) -> list[Path]:
        return self.__print_gia_apuracao_subpage(ie, apuracoes, GIARelatorio.GIA_RELATORIO_APURACAO_PROPRIA,
                                                 [GIASubRelatorio.GIA_RELATORIO_APURACAO_OUTROS_DEBITOS,
                                                  GIASubRelatorio.GIA_RELATORIO_APURACAO_ESTORNO_CREDITO])

    def print_gia_outros_creditos(self, ie: str, apuracoes: list[datetime.date]) -> list[Path]:
        return self.__print_gia_apuracao_subpage(ie, apuracoes, GIARelatorio.GIA_RELATORIO_APURACAO_PROPRIA,
                                                 [GIASubRelatorio.GIA_RELATORIO_APURACAO_OUTROS_CREDITOS,
                                                  GIASubRelatorio.GIA_RELATORIO_APURACAO_ESTORNO_DEBITO])

    # levanta dados pessoais do AFR via PGSF Produtividade
    def get_dados_afr(self, config):
        logger.info("Acessando DEC para ver dados AFR")
        try:
            self.__get_driver().get(dec_url)
        except WebDriverException as we:
            if we.msg.find('ERR_NAME_NOT_RESOLVED') >= 0:
                raise WebScraperException('Não foi possível acessar o site do PGSF Produtividade! '
                                          'Verifique se o computador está conectado na rede da Sefaz.')

        # Click on "Certificado Digital"
        # Cria thread para preencher popup de senha, pois essa página trava thread do Selenium
        t = GeneralFunctions.ThreadWithReturnValue(target=self.__login_certificado_digital,
                                                   args=[self.__get_driver().title, config])
        try:
            input_certificado = self.__get_driver().find_element(By.ID,
                                                                 "ConteudoPagina_btnCertificacao"
                                                                 )
            t.start()
            input_certificado.click()
        except StaleElementReferenceException:
            input_certificado = self.__get_driver().find_element(By.ID,
                                                                 "ConteudoPagina_btnCertificacao"
                                                                 )
            t.start()
            input_certificado.click()
        t.join()

        config.intranet_login = self.__get_driver().find_element(By.ID, "ConteudoPagina_lblLogin").text
        config.nome = self.__get_driver().find_element(By.ID, "ConteudoPagina_lblNome").text
        config.email = self.__get_driver().find_element(By.ID, "ConteudoPagina_lblEmail").text
        funcional = self.__get_driver().find_element(By.ID, "ConteudoPagina_lblIdentidadeFuncional").text
        config.funcional = f"{funcional[:2]}.{funcional[2:5]}-{funcional[-1]}"

        logger.info('Acessando PGSF Produtividade para dados de FDT')
        self.__get_driver().get(pgsf_produtividade_url)

        # Acessa via login/senha porque por algum motivo a thread não continua após clicar no botão de certificado,
        # como ocorre em outros sites
        self.__get_driver().find_element(By.ID, "ctl00_MainContent_btnSTSPassivoWindows").click()
        set_password_in_browser("identityprd", config.intranet_login, config.intranet_pass)

        self.__get_driver().get("https://sefaznet11.intra.fazenda.sp.gov.br/pgsf.net/Telas/Relatorios.aspx")
        Select(self.__get_driver().find_element(By.ID, "ctl00_MainContent_ddlRelatorios")).select_by_index(1)
        wait_driver = WebDriverWait(self.__get_driver(), 10)
        wait_driver.until(EC.visibility_of_element_located((By.ID, "ctl00_MainContent_filtroCombos_ddlDrt")))

        unidades = self.__get_driver().find_element(By.ID, "ctl00_MainContent_filtroCombos_ddlUnidade")
        seletor = Select(unidades)
        if seletor.first_selected_option.text == 'Selecione':
            if any([opcao.text.startswith('FDT DRT') for opcao in seletor.options]):
                seletor.select_by_visible_text(
                    [opcao.text for opcao in seletor.options if opcao.text.startswith('FDT DRT')][0])
                wait_driver.until(EC.text_to_be_present_in_element(
                    (By.ID, "ctl00_MainContent_filtroCombos_ddlDrt"), "DRT"))
            else:
                raise WebScraperException('Não foi encontrada opção de FDT em DRT no PGSF, para pegar a DRT do AFRE!')

        config.drt_sigla = self.__get_driver().find_element(By.ID, "ctl00_MainContent_filtroCombos_ddlDrt").text
        config.equipe_fiscal = self.__get_driver().find_element(By.ID,
                                                                "ctl00_MainContent_filtroCombos_ddlTeamLeader").text

        logger.info("Acessando Sem Papel para confirmar login/senha")
        self.__sigadoc_login(config)

    def is_dec_enabled(self, cnpj: str) -> bool:
        logger.info("Acessando consulta pública do DEC")
        try:
            self.__get_driver().get("https://sefaznet11.intra.fazenda.sp.gov.br/DEC/UCConsultaPublica/Consulta.aspx")
            cnpj_digits = re.sub(r"[^\d]", "", cnpj)
            self.__get_driver().find_element(By.ID, "ConteudoPagina_txtEstabelecimentoBusca").send_keys(cnpj_digits)
            self.__get_driver().find_element(By.ID, "ConteudoPagina_btnBuscarPorEstabelecimento").click()
            resposta = self.__get_driver().find_element(By.ID, "ConteudoPagina_lblSituacaoDEC").text
            return resposta.find("ESTABELECIMENTO EST") >= 0
        except Exception as e:
            logger.exception("Erro ao verificar habilitacao no DEC do CNPJ " + cnpj)
            raise WebScraperException(f"Erro ao verificar habilitacao no DEC do CNPJ {cnpj}: {e}")

    def send_notification(self, cnpj: str, titulo: str, conteudo: str, anexos_paths: list[Path] = [],
                          assunto="Notificação para a prestação de informações e entrega de documentos fiscais",
                          is_tipo_outros=False) -> str:
        logger.info('Acessando DEC para enviar notificação')
        janela_principal = None
        try:
            self.__get_driver().get(dec_url)
        except WebDriverException as we:
            if we.msg.find('ERR_NAME_NOT_RESOLVED') >= 0:
                raise WebScraperException('Não foi possível acessar o site do DEC! '
                                          'Verifique se o computador está conectado na rede da Sefaz.')
        try:
            janela_principal = self.__get_driver().current_window_handle
            # Click on "Certificado Digital"
            # Cria thread para preencher popup de senha, pois essa página trava thread do Selenium
            t = GeneralFunctions.ThreadWithReturnValue(target=self.__login_certificado_digital,
                                                       args=[self.__get_driver().title])
            try:
                input_certificado = self.__get_driver().find_element(By.ID,
                                                                     "ConteudoPagina_btnCertificacao"
                                                                     )
                t.start()
                input_certificado.click()
            except StaleElementReferenceException:
                input_certificado = self.__get_driver().find_element(By.ID,
                                                                     "ConteudoPagina_btnCertificacao"
                                                                     )
                t.start()
                input_certificado.click()
            t.join()

            if len(self.__get_driver().window_handles) > 1:
                for handle in self.__get_driver().window_handles:
                    if handle != janela_principal:
                        self.__get_driver().switch_to.window(handle)
                        self.__get_driver().close()
                self.__get_driver().switch_to.window(janela_principal)

            self.__get_driver().find_element(By.ID, "ConteudoPagina_btnContinuar").click()
            self.__get_driver().get("https://sefaznet11.intra.fazenda.sp.gov.br/DEC/UCGeraMensagem/GeraMensagem.aspx")

            # Não vincula a mensagem anterior
            self.__get_driver().find_element(By.ID, "ConteudoPagina_btnTipoMensagem").click()

            # Escolhe Categoria, Tributo, Tipo e Assunto da mensagem
            Select(self.__get_driver().find_element(By.ID, "ConteudoPagina_lstCategoria")) \
                .select_by_visible_text("Notificação")
            Select(self.__get_driver().find_element(By.ID, "ConteudoPagina_lstTributo")) \
                .select_by_visible_text("ICMS")
            if is_tipo_outros:
                Select(self.__get_driver().find_element(By.ID, "ConteudoPagina_lstTipoMensagem")) \
                    .select_by_visible_text("Outros")
                Select(self.__get_driver().find_element(By.ID, "ConteudoPagina_lstAssunto")) \
                    .select_by_visible_text("Outros")
            else:
                Select(self.__get_driver().find_element(By.ID, "ConteudoPagina_lstTipoMensagem")) \
                    .select_by_visible_text("Fiscalização")
                try:
                    Select(self.__get_driver().find_element(By.ID, "ConteudoPagina_lstAssunto")) \
                        .select_by_visible_text(assunto)
                except NoSuchElementException:
                    raise WebScraperException(f'Assunto {assunto} não foi encontrado no DEC. '
                                              f'Verifique a configuração da análise.')

            Select(self.__get_driver().find_element(By.ID, "ConteudoPagina_lstTipoDestinatario")) \
                .select_by_visible_text("Pessoa Jurídica")
            cnpj_digits = re.sub(r"[^\d]", "", cnpj)
            self.__get_driver().find_element(By.ID, "ConteudoPagina_txtDoc").send_keys(cnpj_digits)
            try:
                self.__get_driver().find_element(By.ID, "ConteudoPagina_btnDadosMensagem").click()
                self.__get_driver().find_element(By.ID, "ConteudoPagina_btnDadosEstabelecimento").click()
            except UnexpectedAlertPresentException:
                alert = self.__get_driver().switch_to.alert
                alert_text = alert.text
                alert.accept()
                self.__get_driver().switch_to.default_content()
                if 'estado impeditivo' in alert_text:
                    raise WebScraperException('Contribuinte está com situação cadastral que impede uso do DEC!'
                                              ' Atualize os dados da Fiscalizada no menu Editar!')
                else:
                    raise WebScraperException(f'Ocorreu problema inesperado no DEC: {alert_text}')

            # Preenchidos os metadados da notificação, enxerta o HTML da notificação diretamente
            # Relembrando HTML...
            # <b> é negrito, <i> é itálico, <br> é CR/LF
            # <ul> abre tópicos, <li> pra cada tópico
            logger.info("Preenchendo título e conteúdo da notificação...")
            self.__get_driver().find_element(By.ID, "ConteudoPagina_txtComplementoAssunto").send_keys(titulo)
            iframe = self.__get_driver().find_element(By.ID, "ConteudoPagina_CorpoMensagem_ctl02_ctl00")
            self.__get_driver().switch_to.frame(iframe)
            self.__get_driver().execute_script(
                "arguments[0].innerHTML = arguments[1]",
                self.driver.find_element(By.XPATH, '//body'),
                conteudo)
            self.__get_driver().switch_to.parent_frame()
            # a mexida no HTML direito deixa perdido, precisa clicar num item e esperar um tempo
            # pro ajax permitir salvar direito
            self.__get_driver().find_element(By.ID, "ConteudoPagina_txtComplementoAssunto").send_keys(Keys.ENTER)
            time.sleep(2)
            self.__get_driver().find_element(By.ID, "ConteudoPagina_btnCorpoMensagem").click()

            # Juntando anexos
            if anexos_paths:
                self.__get_driver().find_element(By.ID, "ConteudoPagina_btnOpcaoAnexosSim").click()
                for anexo_path in anexos_paths:
                    self.__get_driver().find_element(By.ID, "ConteudoPagina_cmdCarregarArquivo").click()
                    logger.info(f"Anexando arquivo {anexo_path.name} à notificação...")
                    self.__get_driver().find_element(By.ID, "ConteudoPagina_txtFile") \
                        .send_keys(str(anexo_path.absolute()))
                    self.__get_driver().find_element(By.ID, "ConteudoPagina_cmdUpload").click()
                    anexo_path.unlink(missing_ok=True)
                self.__get_driver().find_element(By.ID, "ConteudoPagina_btnCadastroAnexos").click()
            else:
                self.__get_driver().find_element(By.ID, "ConteudoPagina_btnOpcaoAnexosNao").click()

            # Mandando notificacao!!!
            logger.warning("QUANDO A NOTIFICAÇÃO ESTIVER OK, CLIQUE EM ENVIAR E AGUARDE! "
                           "PARA DESISTIR, APAGUE A NOTIFICAÇÃO E FECHE O NAVEGADOR.")
            while True:
                try:
                    WebDriverWait(self.__get_driver(), 5).until(
                        EC.presence_of_element_located((By.ID, "ConteudoPagina_lblSucessoEnvio")))
                    break
                except UnexpectedAlertPresentException:
                    # pode acontecer do usuário estar tentando apagar a notificação
                    pass
                except TimeoutException:
                    try:
                        # Apenas para verificar se a página está aberta
                        p = self.__get_driver().page_source
                    except NoSuchWindowException as e:
                        raise e
                    except WebDriverException:
                        pass
                except WebDriverException | NoSuchWindowException:
                    raise WebScraperException('Envio de notificação cancelada pelo usuário! '
                                              'A notificação ficará como rascunho no DEC, se você não tiver apagado!')
            mensagem = self.__get_driver().find_element(By.ID, "ConteudoPagina_lblSucessoEnvio").text
            notificacao = re.match(r'.*(IC.*\d)', mensagem).group(1)
            logger.info(f'Notificação {notificacao} enviada!')
            return notificacao
        except WebScraperException:
            pass
        except Exception as e:
            logger.exception(f"Erro ao enviar notificação DEC para CNPJ {cnpj}, título '{titulo}'")
            raise WebScraperException(f"Erro ao enviar notificação DEC para CNPJ {cnpj}, título '{titulo}': {e}")
        finally:
            try:
                if janela_principal and self.__get_driver().current_window_handle != janela_principal:
                    self.__get_driver().close()
                    self.__get_driver().switch_to.window(janela_principal)
            except WebDriverException:
                # usuário fechou janelas
                pass

    # tenta baixar a notificação DEC e salva como o primeiro caminho (incluindo nome do arquivo)
    # se tiver anexos, baixa eles na segunda pasta indicada
    # retorna true apenas se baixou
    # baixa apenas se já tiver ciência, caso opção esteja usada (por padrão)
    def get_notification(self, numero_dec: str, notification_path: Path, notification_attachment_path: Path,
                         only_after_received=True) -> bool:
        logger.info(f"Acessando DEC para tentar baixar DEC {numero_dec}"
                    f"{' se tiverem tomado ciência' if only_after_received else ''}")
        janela_principal = None
        try:
            self.__get_driver().get(dec_url)
        except WebDriverException as we:
            if we.msg.find('ERR_NAME_NOT_RESOLVED') >= 0:
                raise WebScraperException('Não foi possível acessar o site do DEC! '
                                          'Verifique se o computador está conectado na rede da Sefaz.')
        try:
            janela_principal = self.__get_driver().current_window_handle
            # Click on "Certificado Digital"
            # Cria thread para preencher popup de senha, pois essa página trava thread do Selenium
            t = GeneralFunctions.ThreadWithReturnValue(target=self.__login_certificado_digital,
                                                       args=[self.__get_driver().title])
            try:
                input_certificado = self.__get_driver().find_element(By.ID,
                                                                     "ConteudoPagina_btnCertificacao"
                                                                     )
                t.start()
                input_certificado.click()
            except StaleElementReferenceException:
                input_certificado = self.__get_driver().find_element(By.ID,
                                                                     "ConteudoPagina_btnCertificacao"
                                                                     )
                t.start()
                input_certificado.click()
            t.join()

            if len(self.__get_driver().window_handles) > 1:
                for handle in self.__get_driver().window_handles:
                    if handle != janela_principal:
                        self.__get_driver().switch_to.window(handle)
                        self.__get_driver().close()
                self.__get_driver().switch_to.window(janela_principal)

            self.__get_driver().find_element(By.ID, "ConteudoPagina_btnContinuar").click()
            self.__get_driver().get(
                "https://sefaznet11.intra.fazenda.sp.gov.br/DEC/UCConsultaMensagem/ConsultaMensagens.aspx?Tipo=All")
            self.__get_driver().find_element(By.ID, "ConteudoPagina_txtDataEnvioIniBusca").clear()
            self.__get_driver().find_element(By.ID, "ConteudoPagina_txtDataEnvioIniBusca").send_keys(
                f"01/01/{numero_dec[-4:]}")
            if int(numero_dec[-4:]) != datetime.date.today().year:
                self.__get_driver().find_element(By.ID, "ConteudoPagina_txtDataEnvioFimBusca").clear()
                self.__get_driver().find_element(By.ID, "ConteudoPagina_txtDataEnvioFimBusca").send_keys(
                    f"31/12/{numero_dec[-4:]}")
            self.__get_driver().find_element(By.ID, "ConteudoPagina_txtIdentificacao").send_keys(numero_dec)
            self.__get_driver().find_element(By.ID, "ConteudoPagina_btnBuscar").click()
            try:
                self.__get_driver().switch_to.alert.dismiss()
                logger.warning(f'Não foi localizada notificação DEC {numero_dec}.')
                return False
            except NoAlertPresentException:
                # se não encontrou alerta de DEC não localizado, então deu certo
                pass
            if only_after_received:
                if len(self.__get_driver().find_element(By.ID,
                                                        "ConteudoPagina_gvMensagens_lblDataCiencia_0").text) == 0:
                    # se até achou a notificação, mas ainda não há ciência, retorna False
                    logger.info(f'Notificação DEC {numero_dec} ainda sem ciência...')
                    return False
            self.__get_driver().find_element(By.ID, "ConteudoPagina_gvMensagens_LinkConsultarMsg_0").click()
            logger.info(f'Tentarei baixar o PDF da notificação DEC {numero_dec}')
            time.sleep(1)
            self.__get_driver().switch_to.window(self.__get_driver().window_handles[1])

            # primeiro baixa a notificação em si
            Select(self.__get_driver().find_element(By.ID, "ReportViewer1_ctl01_ctl05_ctl00")).select_by_visible_text(
                "PDF")
            self.__get_driver().find_element(By.ID, "ReportViewer1_ctl01_ctl05_ctl01").click()
            move_downloaded_file(self.tmp_path, 'Mensagem.pdf', notification_path, replace=True)

            # depois baixa os anexos, se existirem
            for link in self.__get_driver().find_elements(By.XPATH, '//*[@id="ListaAnexos"]/tbody/tr/td/a'):
                anexo_name = link.text
                link.click()
                move_downloaded_file(self.tmp_path, anexo_name, notification_attachment_path, replace=True)
            logger.info(f'PDF da Notificação DEC {numero_dec} e anexos baixados!')
            return True
        except Exception as e:
            logger.exception("Erro ao baixar PDF da notificação DEC " + numero_dec)
            raise WebScraperException(f"Erro ao baixar PDF da notificação DEC {numero_dec}: {e}")
        finally:
            if janela_principal is not None and self.__get_driver().current_window_handle != janela_principal:
                self.__get_driver().close()
                self.__get_driver().switch_to.window(janela_principal)

    def verify_sat_equipment(self, cnpj: str):
        logger.info('Acessando SAT Retaguarda para verificar se empresa tem equipamento SAT')
        self.__get_driver().get('https://satsp.fazenda.sp.gov.br/COMSAT/Account/LoginSSL.aspx?ReturnUrl=%2fCOMSAT%2f')
        self.__get_driver().find_element(By.ID, 'conteudo_rbtFazendarioGeral').click()
        # Click on Certificado Digital
        t = GeneralFunctions.ThreadWithReturnValue(target=self.__login_certificado_digital,
                                                   args=[self.__get_driver().title])
        t.start()
        self.__get_driver().find_element(By.ID, 'conteudo_imgCertificado').click()
        t.join()

        self.__get_driver().get('https://satsp.fazenda.sp.gov.br/COMSAT/Private/PesquisarVinculacaoDeEquipamento/'
                                'PesquisarVinculacaoDeEquipamento.aspx')
        self.__get_driver().find_element(By.ID, 'conteudo_txtCnpj').send_keys(cnpj)
        self.__get_driver().find_element(By.ID, 'conteudo_btnPesquisar').click()

        try:
            self.__get_driver().find_element(By.ID, 'conteudo_grvPesquisaVinculacao')
            return True
        except NoSuchElementException:
            if self.__get_driver().find_element(By.ID, 'dialog-modal').text.find('Nenhum registro encontrado') >= 0:
                return False
        return True

    def consulta_historico_simples_nacional(self, cnpjs: list):
        logger.info(f"Acessando Portal do Simples para consultar opção")
        self.__get_driver().get('https://www10.receita.fazenda.gov.br/login/publico/bemvindo/')
        # Click on Certificado Digital
        t = GeneralFunctions.ThreadWithReturnValue(target=self.__login_certificado_digital,
                                                   args=[self.__get_driver().title])
        t.start()
        self.__get_driver().find_element(By.ID, "linkFormSubmit").click()
        t.join()
        self.__get_driver().get('https://www10.receita.fazenda.gov.br/entessn/aplicacoes.aspx?id=7')
        opcoes = []
        for cnpj in cnpjs:
            self.__get_driver().switch_to.frame('frame')
            self.__get_driver().find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtCNPJ').clear()
            self.__get_driver().find_element(By.ID, 'ctl00_ContentPlaceHolder1_txtCNPJ').send_keys(cnpj.zfill(14))
            self.__get_driver().find_element(By.ID, 'ctl00_ContentPlaceHolder1_btnPesquisar').click()
            WebDriverWait(self.__get_driver(), 10).until(
                EC.visibility_of_element_located(
                    (By.ID, '__tab_ctl00_ContentPlaceHolder1_tcPrincipal_Sinac_tcSinac_SinacOpcao')))
            self.__get_driver().find_element(By.ID,
                                             '__tab_ctl00_ContentPlaceHolder1_tcPrincipal_Sinac_tcSinac_SinacOpcao').click()
            tabela = self.__get_driver().find_element(By.ID,
                                                      'ctl00_ContentPlaceHolder1_tcPrincipal_Sinac_tcSinac_SinacOpcao_wsSinacOpcao_gvSinacOpcao')
            # pega linhas da tabela, ignorando o cabeçalho
            linhas = tabela.find_elements(By.CSS_SELECTOR, 'tr')[1:]
            for linha in linhas:
                celulas = linha.find_elements(By.CSS_SELECTOR, 'td')
                opcoes.append({'cnpj': cnpj, 'inicio': celulas[1].text,
                               'fim': celulas[2].text if celulas[2].text.strip() else None})
            self.__get_driver().back()
        return opcoes

    # apenas faz download de EFDs que tenham referencia entre inicio e fim,
    # além de apenas pegar a última remessa de cada referencia
    # retorna lista de todas as efds (originais e substitutas) e datas de entrega
    def get_efds_for_osf(self, osf: str, inicio: datetime.date, fim: datetime.date,
                         last_reception: datetime.datetime, evento: threading.Event) -> list[dict]:
        try:
            if evento.is_set():
                return []
            logger.info(f"Acessando o site de Arquivos Digitais para "
                        f"baixar EFDs entre {inicio.strftime('%m/%Y')} e {fim.strftime('%m/%Y')}")
            self.__get_driver().get(arquivos_digitais_url)

            # Click on "Certificado Digital"
            t = GeneralFunctions.ThreadWithReturnValue(target=self.__login_certificado_digital,
                                                       args=[self.__get_driver().title])
            try:
                input_certificado = self.__get_driver().find_element(By.ID,
                                                                     "ctl00_ConteudoPagina_btn_Login_Certificado_WebForms")
                input_certificado.click()
            except StaleElementReferenceException:
                input_certificado = self.__get_driver().find_element(By.ID,
                                                                     "ctl00_ConteudoPagina_btn_Login_Certificado_WebForms")
                input_certificado.click()
            t.start()
            t.join()

            self.__get_driver().get(
                'https://www10.fazenda.sp.gov.br/ArquivosDigitais/Pages/DownloadArquivoDigital.aspx')
            self.__get_driver().find_element(By.ID, 'ctl00_ConteudoPagina_usrControlOSF_txtOSF').send_keys(osf)
            self.__get_driver().find_element(By.ID, 'ctl00_ConteudoPagina_btnPesquisar').click()
            try:
                tabela = self.__get_driver().find_element(By.CLASS_NAME, 'GridView')
            except NoSuchElementException as ex:
                try:
                    erros = self.__get_driver().find_element(By.ID, "ctl00_ConteudoPagina_ListaInconsistencia_ListErro")
                    raise WebScraperException(erros.text)
                except NoSuchElementException:
                    raise ex
            # pega linhas da tabela, ignorando o cabeçalho
            logger.info("Definindo quais EFDs serão baixadas...")
            todos_arquivos = []
            arquivos = {}
            linhas = tabela.find_elements(By.CSS_SELECTOR, 'tr')[1:]
            for linha in linhas:
                celulas = linha.find_elements(By.CSS_SELECTOR, 'td')
                if celulas[1].text == 'EFD-SP':
                    ref = datetime.datetime.strptime('01/' + celulas[3].text, '%d/%m/%Y').date()
                    hora_recepcao = re.findall(r'(\d+)\.(?:txt|TXT)\.(?:gz|GZ)$', celulas[5].text)[0]
                    recepcao = datetime.datetime.strptime(hora_recepcao, '%d%m%Y%H%M%S')
                    finalidade = celulas[4].text
                    todos_arquivos.append({'referencia': ref, 'tipo': finalidade, 'entrega': recepcao})
                    if inicio <= ref <= fim and recepcao > last_reception:
                        if (not arquivos.__contains__(ref)) or arquivos[ref]['recepcao'] < recepcao:
                            arquivos[ref] = {'index': linhas.index(linha),
                                             'recepcao': recepcao}

            if len(arquivos) == 0:
                logger.info('Não havia novos arquivos SPED EFD a serem baixados')
                return todos_arquivos

            for valores in arquivos.values():
                nome_checkbox = f'ctl00_ConteudoPagina_grid_ctl{valores["index"] + 2:02d}_CheckBox1'
                self.__get_driver().find_element(By.ID, nome_checkbox).click()

            if evento.is_set():
                return todos_arquivos
            self.__get_driver().find_element(By.ID, 'ctl00_ConteudoPagina_btnDownload').click()
            time.sleep(1)
            logger.info("Baixando arquivos EFD...")
            self.__get_driver().find_element(By.ID, 'ctl00_ConteudoPagina_btnCiente').click()

            wait_downloaded_file(self.tmp_path, "Base_de_Arquivos_Digitais.zip", 30)
            # logger.info('Apagando arquivos EFD existentes anteriormente...')
            # for sped_file in self.download_path.glob('SPED*.txt'):
            #    (self.download_path / sped_file).unlink()

            logger.info("Descompactando arquivos EFD...")
            with zipfile.ZipFile(path.join(self.tmp_path, "Base_de_Arquivos_Digitais.zip"), "r") as f:
                for arquivo in f.namelist():
                    f.extract(arquivo, path=str(self.tmp_path))
                    with gzip.open(path.join(self.tmp_path, arquivo), 'rb') as gz:
                        with open(path.join(self.download_path, arquivo[:-3]), 'wb') as out:
                            out.write(gz.read())
            return todos_arquivos

        except Exception as e:
            logger.exception(
                f"Erro ao baixar EFDs da OSF {osf} entre {inicio.strftime('%m/%Y')} e {fim.strftime('%m/%Y')}")
            raise WebScraperException(f"Erro ao baixar EFDs da OSF {osf} entre {inicio.strftime('%m/%Y')} e "
                                      f"{fim.strftime('%m/%Y')}: {e}")
        finally:
            try:
                if path.isfile(path.join(self.tmp_path, "Base_de_Arquivos_Digitais.zip")):
                    os.remove(path.join(self.tmp_path, "Base_de_Arquivos_Digitais.zip"))
                for gz in (x for x in os.listdir(str(self.tmp_path)) if x.endswith('gz')):
                    os.remove(path.join(self.tmp_path, gz))
            except Exception:
                pass  # se não apagar arquivos temporarios, deixa quieto

    def get_launchpad_report(self, report_name: str, downloaded_file_name: str, evento: threading.Event | None,
                             window: sg.Window | None, parametros: list,
                             relatorio_anterior: Future = None) -> Path | None:
        try:
            modo_exportacao = launchpad_report_options[report_name]
            if window:
                window.write_event_value('-DATA-EXTRACTION-STATUS-', [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'BEGIN'])
            tipo_arquivo = modo_exportacao.get('Formato', '.csv')
            if tipo_arquivo == 'PDF':
                tipo_arquivo = '.pdf'
            elif tipo_arquivo.startswith('Excel'):
                tipo_arquivo = '.xlsx'
            elif tipo_arquivo == 'Texto':
                tipo_arquivo = '.txt'

            original_report_filename = report_name.replace(" ", "_") + tipo_arquivo

            # verifica se o período do relatório já foi baixado (pode ser num arquivo de mesmo período),
            # ou entre arquivos de períodos diferentes
            # se sim, encerra
            arquivos = self.download_path.glob(f'{report_name.replace(" ", "_")}*{tipo_arquivo}')
            for file in arquivos:
                if 'inicio' in modo_exportacao['Parametros']:
                    index = len(report_name)
                    inicio_arquivo = datetime.datetime.strptime(file.stem[index + 1:index + 9], '%d%m%Y').date()
                    fim_arquivo = datetime.datetime.strptime(file.stem[index + 10:index + 19], '%d%m%Y').date()

                    inicio_consulta = datetime.datetime.strptime(
                        parametros[modo_exportacao["Parametros"].index("inicio")], "%d/%m/%Y").date()
                    fim_consulta = datetime.datetime.strptime(
                        parametros[modo_exportacao["Parametros"].index("fim")], "%d/%m/%Y").date()

                    if inicio_arquivo <= inicio_consulta and fim_arquivo >= fim_consulta:
                        logger.info(f'Relatório {report_name} '
                                    f'(período {parametros[modo_exportacao["Parametros"].index("inicio")]} a '
                                    f'{parametros[modo_exportacao["Parametros"].index("fim")]})'
                                    f' já estava baixado, resolvido!')
                        if window:
                            window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                                     [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'END'])
                        return file
                else:
                    logger.info(f'Relatório {report_name} já estava baixado, resolvido!')
                    if window:
                        window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                                 [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'END'])
                    return file

            # se existe algum processo a ser encerrado antes, espera dar um resultado
            if relatorio_anterior:
                while True:
                    try:
                        # retorna se deu exception ou não, mas desde que tenha finalizado
                        resultado = relatorio_anterior.exception(timeout=LAUNCHPAD_TIME_WAIT_SECONDS)
                        if not resultado or not isinstance(resultado, WebScraperTimeoutException):
                            logger.debug(f'Iniciando execução do relatório {report_name},'
                                         f' pois execução de período anterior acabou')
                            break
                    except concurrent.futures.CancelledError:
                        logger.debug(f'Desistiu de executar relatório {report_name},'
                                     f' pois execução de período anterior foi cancelada')
                        return None
                    except concurrent.futures.TimeoutError:
                        if evento.is_set():
                            if window:
                                window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                                         [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'STOP'])
                            return None

            if modo_exportacao.get('ID') is not None:
                result = self.__get_launchpad_report_through_pepe(report_name, original_report_filename,
                                                                  evento, window, parametros)
            else:
                result = self.__get_launchpad_report_through_selenium(report_name, evento, window, parametros)

            if not result:
                return None
            if downloaded_file_name:
                move_downloaded_file(self.tmp_path, original_report_filename,
                                     self.download_path / downloaded_file_name,
                                     30)
            if 'inicio' in modo_exportacao['Parametros']:
                logger.warning(f'Relatório {report_name} '
                               f'(período {parametros[modo_exportacao["Parametros"].index("inicio")]} a '
                               f'{parametros[modo_exportacao["Parametros"].index("fim")]})'
                               f' baixado com sucesso!')
            else:
                logger.warning(f'Relatório {report_name} baixado com sucesso!')
            if window:
                window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                         [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'END'])
            return self.download_path / downloaded_file_name
        except WebScraperException as wse:
            raise wse
        except Exception as e:
            logger.exception(f'Ocorreu um problema na execução de relatório {report_name} no Launchpad: {e}')
            raise WebScraperException(f'Erro inesperado na execução de relatório {report_name} no Launchpad: {e}') \
                from e

    def __get_launchpad_report_through_pepe(self, report_name: str, original_report_filename: str,
                                            evento: threading.Event, window: sg.Window, parametros: list) -> bool:
        modo_exportacao = launchpad_report_options[report_name]
        try:
            logger.info('Acessando Launchpad...')
            requests.get(launchpad_url)
        except requests.exceptions.ConnectionError:
            if window:
                window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                         [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'FAILURE'])
            raise WebScraperException('Não foi possível acessar o Launchpad! '
                                      'Verifique se o computador está conectado na rede da Sefaz.')
        # tempo máximo de espera para um relatório ficar pronto
        tempo_maximo = time.time() + LAUNCHPAD_MAX_TIME_WAIT_SECONDS
        ultimo_tempo_mostrado = 0
        inicio_execucao = time.time()
        p = Process(target=get_launchpad_report,
                    name=f'LaunchPadPepe_{report_name}',
                    daemon=True,
                    args=(report_name,
                          modo_exportacao["ID"],
                          modo_exportacao.get("Abas", None),
                          modo_exportacao.get("Relatorios", None),
                          self.tmp_path / original_report_filename,
                          dict(zip(list(range(0, len(parametros))), parametros))))
        p.start()
        while True:
            p.join(LAUNCHPAD_TIME_WAIT_SECONDS)
            if not p.is_alive():
                if (self.tmp_path / original_report_filename).is_file():
                    logger.info(f'Relatório {report_name} baixado!')
                    return True
                else:
                    logger.warning(f'Relatório {report_name} NÃO FOI BAIXADO, '
                                   f'talvez tenha ocorrido problema no Launchpad. Tente novamente mais tarde.')
                    return False
            else:
                # ainda não ficou pronto, vamos ver se é pra desistir
                if tempo_maximo - time.time() > 0:
                    # apenas faz print a cada LAUNCH_TIME_REPORT_MINUTES minutos
                    minutos_decorridos = int((time.time() - inicio_execucao) / 60)
                    if minutos_decorridos >= ultimo_tempo_mostrado + LAUNCHPAD_TIME_REPORT_MINUTES:
                        ultimo_tempo_mostrado = minutos_decorridos
                        logger.info(
                            f'Relatório {report_name} em execução, aguardando no máximo '
                            f'mais {int((tempo_maximo - time.time()) / 60)} minutos...')
                if evento and evento.is_set():
                    if window:
                        window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                                 [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'STOP'])
                    p.terminate()
                    return False
                if time.time() > tempo_maximo:
                    if window:
                        window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                                 [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'FAILURE'])
                    logger.warning(f'Relatório {report_name} NÃO FOI BAIXADO, '
                                   f'talvez tenha ocorrido problema no Launchpad. Tente novamente mais tarde.')
                    p.terminate()
                    raise WebScraperTimeoutException(report_name)

    def __get_launchpad_report_through_selenium(self, report_name: str, evento: threading.Event,
                                                window: sg.Window, parametros: list) -> bool:
        modo_exportacao = launchpad_report_options[report_name]
        with self.launchpad_lock:
            if not self.running_launchpad:
                logger.info('Acessando Launchpad...')

                try:
                    self.__get_driver().get(launchpad_url)
                except WebDriverException as we:
                    if we.msg.find('ERR_NAME_NOT_RESOLVED') >= 0:
                        if window:
                            window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                                     [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'FAILURE'])
                        raise WebScraperException('Não foi possível acessar o site do Launchpad! '
                                                  'Verifique se o computador está conectado na rede da Sefaz.')
                self.__get_driver().switch_to.frame("servletBridgeIframe")
                self.__get_driver().find_element(By.ID, "_id0:logon:USERNAME").send_keys(
                    GeneralConfiguration.get().intranet_login)
                self.__get_driver().find_element(By.ID, "_id0:logon:PASSWORD").send_keys(
                    GeneralConfiguration.get().intranet_pass)
                self.__get_driver().find_element(By.ID, "_id0:logon:logonButton").click()
                self.__get_driver().find_element(By.ID, "yui-gen1-button").click()
                self.running_launchpad = True

            if evento.is_set():
                if window:
                    window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                             [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'STOP'])
                return False

        while True:
            self.launchpad_lock.acquire()
            self.__get_driver().switch_to.default_content()
            self.__get_driver().switch_to.frame("servletBridgeIframe")
            abas = [tab.text for tab in self.__get_driver().find_elements(By.CLASS_NAME, 'tabItemHolder')
                    if tab.text]
            # verifica se está no limite de abas abertas (sempre tem 2 abas)
            if len(abas) < LAUNCHPAD_MAX_CONCURRENT_REPORTS + 2:
                break
            self.launchpad_lock.release()
            time.sleep(LAUNCHPAD_TIME_WAIT_SECONDS)

        try:
            self.__get_driver().switch_to.default_content()
            self.__get_driver().switch_to.frame("servletBridgeIframe")
            logger.info(f"Solicitando relatório {report_name} no Launchpad, parâmetros {parametros}...")
            self.__get_driver().find_element(By.LINK_TEXT, "Documentos").click()
            self.__get_driver().find_element(By.ID, "infoviewSearchInput").clear()
            pesquisa = modo_exportacao.get('Pesquisa', report_name)
            self.__get_driver().find_element(By.ID, "infoviewSearchInput").send_keys(pesquisa)
            self.__get_driver().find_element(By.ID, "searchButton").click()

            # localiza relatório na pagina de pesquisa
            # faz 3 tentativas, pois a atualizacao da pagina de pesquisa é por ajax
            tentativas = 0
            while tentativas < 3:
                try:
                    self.__get_driver().switch_to.default_content()
                    self.__get_driver().switch_to.frame("servletBridgeIframe")
                    subframe = list(filter(lambda f: f.rect['x'] > 0 and f.size['height'] > 0,
                                           self.__get_driver().find_elements(By.TAG_NAME, "iframe")))[0]
                    self.__get_driver().switch_to.frame(subframe)
                    ActionChains(self.__get_driver()) \
                        .double_click(
                        self.__get_driver().find_element(By.XPATH, f'//tr[@aria-label="{report_name}"]')) \
                        .perform()
                    logger.debug(f'Encontrei na pesquisa o link pra {report_name}, duplo click feito...')
                    self.__get_driver().switch_to.parent_frame()
                    aba_atual = \
                        [tab.text for tab in self.__get_driver().find_elements(By.CLASS_NAME, 'tabItemHolder')
                         if 'Active' in tab.get_attribute('class').split()][0]
                    if aba_atual == 'Documentos':
                        logger.debug('Não fez duplo clique, vamos tentar dando enter')
                        subframe = list(filter(lambda f: f.rect['x'] > 0 and f.size['height'] > 0,
                                               self.__get_driver().find_elements(By.TAG_NAME, "iframe")))[0]
                        self.__get_driver().switch_to.frame(subframe)
                        elemento_buscado = self.__get_driver().find_element(By.XPATH,
                                                                            f'//tr[@aria-label="{report_name}"]')
                        elemento_buscado.click()
                        elemento_buscado.send_keys(Keys.ENTER)
                        time.sleep(1)
                        self.__get_driver().switch_to.default_content()
                        self.__get_driver().switch_to.frame("servletBridgeIframe")
                        aba_atual = \
                            [tab.text for tab in
                             self.__get_driver().find_elements(By.CLASS_NAME, 'tabItemHolder')
                             if 'Active' in tab.get_attribute('class').split()][0]
                        if aba_atual == 'Documentos':
                            logger.debug('Insiste em não sair da página de busca, vamos retentar depois')
                            raise NoSuchElementException()
                    else:
                        break
                except NoSuchElementException:
                    tentativas = tentativas + 1
                    time.sleep(2)

            if tentativas == 3:
                raise WebScraperException(f'Não consegui localizar na busca do Launchpad '
                                          f'relatório de nome "{report_name}" - verifique se '
                                          f'não há algum erro de digitação!')

            # subframe é o frame da aba selecionada
            self.__get_driver().switch_to.default_content()
            self.__get_driver().switch_to.frame("servletBridgeIframe")
            WebDriverWait(self.__get_driver(), 20).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "spinnerMask")))
            WebDriverWait(self.__get_driver(), 20).until(
                EC.visibility_of_element_located((By.LINK_TEXT, report_name)))
            self.__get_driver().find_element(By.LINK_TEXT, report_name).click()
            subframe = list(filter(lambda f: f.rect['x'] > 0 and f.size['height'] > 0,
                                   self.__get_driver().find_elements(By.TAG_NAME, "iframe")))[0]
            self.__get_driver().switch_to.frame(subframe)
            self.__get_driver().switch_to.frame(self.__get_driver().find_element(By.ID, "webiViewFrame"))
            self.__get_driver().switch_to.frame(self.__get_driver().find_element(By.ID, "_iframeleftPaneW"))
            i = 1
            while i <= len(parametros):
                # estão usando listbox para alguns casos. vou ignorar por enquanto, pois está selecionada
                # uma opção padrão que atende (situação = 0)
                try:
                    self.__get_driver().find_element(By.ID, f"PV{i}").clear()
                    self.__get_driver().find_element(By.ID, f"PV{i}").send_keys(parametros[i - 1])
                except NoSuchElementException:
                    pass
                i = i + 1
            self.__get_driver().find_element(By.ID, "PV1").send_keys(Keys.ENTER)
            if evento.is_set():
                if window:
                    window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                             [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'STOP'])
                self.launchpad_lock.release()
                return False
            logger.info(f"Iniciada execução do relatório {report_name} no Launchpad. Aguardando resposta...")

            # faz com que vá pra janela principal, para poder verificar depois se acabou
            self.__get_driver().switch_to.default_content()
            self.__get_driver().switch_to.frame("servletBridgeIframe")
            self.launchpad_lock.release()
        except Exception as e:
            if window:
                window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                         [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'FAILURE'])
            self.launchpad_lock.release()
            raise e

        # tempo máximo de espera para um relatório ficar pronto
        tempo_maximo = time.time() + LAUNCHPAD_MAX_TIME_WAIT_SECONDS
        ultimo_tempo_mostrado = 0
        inicio_execucao = time.time()
        try:
            while True:
                # o botão que tem que procurar quando terminou a consulta
                self.launchpad_lock.acquire()
                try:
                    # muda de aba no Launchpad pra aba da thread
                    self.__get_driver().switch_to.default_content()
                    self.__get_driver().switch_to.frame("servletBridgeIframe")
                    self.__get_driver().find_element(By.LINK_TEXT, report_name).click()
                    subframe = list(filter(lambda f: f.rect['x'] > 0 and f.size['height'] > 0,
                                           self.__get_driver().find_elements(By.TAG_NAME, "iframe")))[0]
                    self.__get_driver().switch_to.frame(subframe)
                    self.__get_driver().switch_to.frame(self.__get_driver().find_element(By.ID, "webiViewFrame"))

                    # verifica se ocorreu mensagem de erro
                    try:
                        msg = self.__get_driver().find_element(By.ID, 'dlg_txt_alertDlg').text
                        if msg.find('não pode se conectar') >= 0 or msg.find('erro de banco de dados') >= 0:
                            raise WebScraperException(f'Launchpad desconectou do servidor: {msg}')
                        if msg.find('Controle Acesso OSF') >= 0:
                            raise WebScraperException('OSF não liberada no Launchpad para download de relatório. '
                                                      'Talvez entrou em execução hoje mesmo?')
                    except NoSuchElementException:
                        pass

                    WebDriverWait(self.__get_driver(), 1).until(
                        EC.invisibility_of_element_located((By.ID, "Btn_waitDlg_cancelButton")))
                    # se chegou aqui, é porque o popup de espera de execução fechou sozinho!
                    break
                except TimeoutException:
                    # ainda não ficou pronto, dorme um tempo pra ver se resolve
                    if tempo_maximo - time.time() > 0:
                        # apenas faz print a cada LAUNCH_TIME_REPORT_MINUTES minutos
                        minutos_decorridos = int((time.time() - inicio_execucao) / 60)
                        if minutos_decorridos >= ultimo_tempo_mostrado + LAUNCHPAD_TIME_REPORT_MINUTES:
                            ultimo_tempo_mostrado = minutos_decorridos
                            logger.info(
                                f'Relatório {report_name} em execução, aguardando no máximo '
                                f'mais {int((tempo_maximo - time.time()) / 60)} minutos...')
                    self.__get_driver().switch_to.default_content()
                    self.__get_driver().switch_to.frame("servletBridgeIframe")
                    self.launchpad_lock.release()
                    if evento.is_set():
                        if window:
                            window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                                     [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'STOP'])
                        return False
                    if time.time() > tempo_maximo:
                        if window:
                            window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                                     [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'FAILURE'])
                        logger.warning(f'Relatório {report_name} NÃO FOI BAIXADO, '
                                       f'talvez tenha ocorrido problema no Launchpad. Tente novamente mais tarde.')
                        raise WebScraperTimeoutException(report_name)
                    time.sleep(LAUNCHPAD_TIME_WAIT_SECONDS)

            logger.info(f'Relatório {report_name} pronto, tentarei fazer download...')

            # Nem sempre aparece uma mensagem de alerta ao encerrar o relatório
            try:
                self.__get_driver().find_element(By.ID, "RealBtn_OK_BTN_alertDlg").click()
            except NoSuchElementException:
                pass

            # hora de exportar o resultado
            self.__get_driver().find_element(By.XPATH, '//*[@title="Exportar"]/tbody/tr[1]/td[2]/div/div').click()
            if modo_exportacao.get('Tipo', 'Dados') == 'Dados':
                self.__get_driver().find_element(By.ID, "check_radioData").click()
                checkAll = "check_SelectAllData"
            else:
                checkAll = "check_SelectAllReport"
            if len(modo_exportacao['Relatorios']) > 0:
                # Tira seleção de todos ds dados a baixar, e escolhe aqueles que interessam
                self.__get_driver().find_element(By.ID, checkAll).click()

            dados_ticados = 0
            for label in self.driver.find_elements(By.XPATH,
                                                   '//table[@class="dlgContent"]/tbody/tr/td/nobr/label['
                                                   'starts-with(@id, "label_")]'):
                if label.text in modo_exportacao['Relatorios']:
                    self.__get_driver().find_element(By.ID, label.get_attribute("for")).click()
                    dados_ticados += 1
            if dados_ticados < len(modo_exportacao['Relatorios']):
                raise WebScraperException(
                    f'Não foram encontradas nas opções de exportação do relatório {report_name}'
                    f' todas as opções cadastradas para seleção. Verifique as opções no Launchpad!')

            if modo_exportacao.get('Formato', None) is not None:
                Select(self.__get_driver().find_element(By.ID, "fileTypeList")) \
                    .select_by_visible_text(modo_exportacao['Formato'])

            self.__get_driver().find_element(By.ID, "Btn_OK_BTN_idExportDlg").click()
            return True
        except WebScraperException as wse:
            raise wse
        except Exception as e:
            if window:
                window.write_event_value('-DATA-EXTRACTION-STATUS-',
                                         [f"{modo_exportacao['Grupo']}-DOWNLOAD", 'FAILURE'])
            logger.exception(f"Ocorreu um problema ao baixar relatório {report_name} no Launchpad")
            raise WebScraperException(f"Ocorreu um problema ao baixar relatório {report_name} no Launchpad: {e}") \
                from e
        finally:
            if not self.launchpad_lock.locked():
                self.launchpad_lock.acquire()
            self.__get_driver().switch_to.default_content()
            self.__get_driver().switch_to.frame("servletBridgeIframe")
            self.__get_driver().find_element(By.XPATH, f'//a[@title="{report_name}"]//parent::div/a[4]').click()
            try:
                # caso apareça alerta de página não salva
                self.__get_driver().switch_to.alert.accept()
            except NoAlertPresentException:
                pass
            self.launchpad_lock.release()

    def get_expediente_sem_papel(self, expediente: str):
        logger.info(f'Acessando Sem Papel para baixar expediente {expediente}...')
        sp = _PepeSingleton.get(pepe.SpSemPapel)
        try:
            sp.login(GeneralConfiguration.get().sigadoc_login, GeneralConfiguration.get().sigadoc_pass)
            expediente_limpo = re.sub(r'[^A-Z0-9]', '', expediente)
            file_name = self.download_path / f'{expediente_limpo}.pdf'
            sp.baixar_pdf_completo(expediente, str(file_name.absolute()))
            logger.info(f'Expediente {expediente} baixado com sucesso!')
            return file_name
        except Exception as e:
            logger.exception(f'Ocorreu um problema no download do expediente {expediente} no Sem Papel')
            raise WebScraperException(f'Ocorreu um problema no download do expediente {expediente} no Sem Papel: {e}')
        finally:
            sp.logout()

    def print_efd_obrigatoriedade(self, cnpj: str, download_path: Path):
        logger.info('Baixando relatório de obrigatoriedade de EFD')
        self.__get_driver().get(f'https://www.fazenda.sp.gov.br/sped/obrigados/obrigados.asp?CNPJLimpo={cnpj}'
                                f'&Submit=Enviar')
        self.__save_as_pdf(download_path)

    def print_efd_entregas(self, cnpj: str, inicio: datetime.date, fim: datetime.date, download_path: Path):
        try:
            logger.info('Baixando lista de entregas de EFDs no portal Arquivos Digitais')
            self.__get_driver().get(arquivos_digitais_url)
            # Click on "Certificado Digital"
            t = GeneralFunctions.ThreadWithReturnValue(target=self.__login_certificado_digital,
                                                       args=[self.__get_driver().title])
            try:
                input_certificado = self.__get_driver().find_element(By.ID,
                                                                     "ctl00_ConteudoPagina_btn_Login_Certificado_WebForms")
                input_certificado.click()
            except StaleElementReferenceException:
                input_certificado = self.__get_driver().find_element(By.ID,
                                                                     "ctl00_ConteudoPagina_btn_Login_Certificado_WebForms")
                input_certificado.click()
            t.start()
            t.join()

            self.__get_driver().get(
                'https://www10.fazenda.sp.gov.br/ArquivosDigitais/Pages/ConsultaEntregaArquivos.aspx')
            self.__get_driver().find_element(By.ID, 'ctl00_ConteudoPagina_usrControlCNPJ_txtCNPJ').send_keys(cnpj)
            self.__get_driver().find_element(By.ID, 'ctl00_ConteudoPagina_usrControlReferenciaInicial_txtReferencia'). \
                send_keys(inicio.strftime('%m/%Y'))
            self.__get_driver().find_element(By.ID, 'ctl00_ConteudoPagina_usrControlReferenciaFinal_txtReferencia'). \
                send_keys(fim.strftime('%m/%Y'))
            self.__get_driver().find_element(By.ID, 'ctl00_ConteudoPagina_btnPesquisar').click()

            WebDriverWait(self.__get_driver(), 5).until(
                EC.visibility_of_element_located((By.ID, 'ctl00_ConteudoPagina_fsEntregaPorIE')))
            self.__save_as_pdf(download_path)
        except Exception as e:
            logger.exception(f'Ocorreu um problema no download do extrato de entrega de EFD')
            raise WebScraperException(f'Ocorreu um problema no download do extrato de entrega de EFD: {e}')

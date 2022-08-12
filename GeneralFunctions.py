import base64
import hashlib
import json
import logging
import ssl
import subprocess
import threading
from io import TextIOWrapper
from logging.handlers import RotatingFileHandler
import os
import re
import shutil
import time
import winreg
from datetime import date
from datetime import datetime
from datetime import timedelta
from pathlib import Path

import pandas as pd
import pythoncom
import wincertstore as wincertstore
from cryptography import x509
from cryptography.hazmat._oid import ObjectIdentifier

project_name = 'PoltergeistFDT'
project_version = '0.1.1'
meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho',
         'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
infractions = {}


class PopenWindows(subprocess.Popen):
    # serve pra fazer monkey patch, de forma que no modo release não abra um shell
    def __init__(self, command, **popen_kwargs):
        executable = command[0] if isinstance(command, list) else command
        if executable.find('explorer.exe') >= 0 or executable.find('tika-server') >= 0:
            super().__init__(command, **popen_kwargs)
        else:
            startupinfo_windows = subprocess.STARTUPINFO()
            startupinfo_windows.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            if popen_kwargs.get('stdout', None) is None:
                popen_kwargs['stdout'] = subprocess.PIPE
            elif isinstance(popen_kwargs['stdout'], TextIOWrapper) and not Path(popen_kwargs['stdout'].name).is_file():
                popen_kwargs['stdout'] = subprocess.PIPE
            popen_kwargs['stdin'] = subprocess.PIPE
            popen_kwargs['stderr'] = subprocess.PIPE
            popen_kwargs['startupinfo'] = startupinfo_windows
#            popen_kwargs['shell'] = False
            super().__init__(command, **popen_kwargs)


class ThreadWithReturnValue(threading.Thread):
    def __init__(self, target, args=()):
        threading.Thread.__init__(self, group=None, target=target, name=None, args=args, kwargs=None, daemon=True)
        self._return = None
        self._exception = None

    def run(self):
        if self._target is not None:
            # Esse CoInitialize é pra não dar erro quando rodar qualquer comando COM dentro de uma thread
            pythoncom.CoInitialize()
            try:
                self._return = self._target(*self._args, **self._kwargs)
            except Exception as e:
                self._exception = e

    def join(self, *args):
        threading.Thread.join(self, *args)
        if self._exception:
            raise self._exception
        return self._return


def get_user_path() -> Path:
    return (Path.home() / project_name).absolute()


def get_local_dados_afr_path() -> Path:
    return get_user_path() / 'dados_afre.json'


def get_audit_json_path(home_path: Path) -> Path:
    return home_path / 'Dados' / 'dados_auditoria.json'


def get_folders_history_json_path():
    return get_user_path() / 'folders_history.json'


def get_tmp_path() -> Path:
    return Path('tmp')


logger = logging.getLogger(project_name)
logger.setLevel(logging.DEBUG)
get_user_path().mkdir(exist_ok=True)
fh = RotatingFileHandler(filename=get_user_path() / f'{project_name}.log', encoding='iso-8859-1',
                         backupCount=3, maxBytes=10485760)
fh.setLevel(logging.ERROR)
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s [%(threadName)s] - %(levelname)s - %(message)s"))
logger.addHandler(ch)


def last_day_of_month(any_day: (date | datetime)) -> date:
    next_month = any_day.replace(day=28) + timedelta(days=4)
    # subtract the number of remaining 'overage' days to get last day of current month, or said programattically
    # said, the previous day of the first of next month
    retorno = next_month - timedelta(days=next_month.day)
    return retorno.date() if isinstance(retorno, datetime) else retorno


def first_day_of_month_before(any_day: datetime.date) -> datetime.date:
    # subtract a number > 31, so every month will be contemplated
    last_month = last_day_of_month(any_day) - timedelta(days=35)
    return datetime(last_month.year, last_month.month, 1).date()


def periodos_prettyprint(referencias: list, freq='M') -> str:
    referencias = [ref.date() if isinstance(ref, datetime) else ref for ref in referencias]
    # primeiro agrupa períodos contíguos
    tmp_refs = []
    sequencia = None
    for i in range(len(referencias)):
        if i != len(referencias) - 1 and not sequencia and \
                ((freq == 'M' and referencias[i + 1].month == referencias[i].month + 1
                  and referencias[i].year == referencias[i + 1].year)
                 or (freq == 'Y' and referencias[i + 1].year == referencias[i].year + 1)):
            sequencia = [referencias[i]]
            continue
        if sequencia and (i == len(referencias) - 1 or
                          ((freq == 'M' and (referencias[i].year != referencias[i + 1].year
                                             or referencias[i + 1].month > referencias[i].month + 1))
                           or (freq == 'Y' and referencias[i + 1].year > referencias[i].year + 1))):
            sequencia.append(referencias[i])
            if first_day_of_month_before(sequencia[1]) <= sequencia[0]:
                tmp_refs.append(sequencia[0])
                tmp_refs.append(sequencia[1])
            else:
                tmp_refs.append(sequencia)
            sequencia = None
            continue
        if not sequencia:
            tmp_refs.append(referencias[i])
    referencias = tmp_refs
    texto = 'os períodos de ' if len(referencias) > 1 else 'o período de '
    all_years = list(set([ref.year if isinstance(ref, date) else ref[0].year for ref in referencias]))
    all_years.sort()

    for i in range(len(referencias)):
        i_last_year = 5000 if i == 0 else \
            referencias[i - 1][0].year if isinstance(referencias[i - 1], list) else referencias[i - 1].year
        i_year = referencias[i][0].year if isinstance(referencias[i], list) else referencias[i].year
        i_plus_year = 0 if i == len(referencias) - 1 else \
            referencias[i + 1][0].year if isinstance(referencias[i + 1], list) else referencias[i + 1].year
        if freq == 'M':
            if i > 0 and (i == len(referencias) - 1 or (i_last_year < i_year and i_year == all_years[-1]) or
                          (i_last_year == i_year and i_year < i_plus_year)):
                texto = texto[:-2] + ' e '
            if isinstance(referencias[i], list):
                if referencias[i][0].year != referencias[i][1].year:
                    texto += f'{meses[referencias[i][0].month - 1].casefold()} de {referencias[i][0].year} ' \
                             f'a {meses[referencias[i][1].month - 1].casefold()} de {referencias[i][1].year}, '
                else:
                    texto += f'{meses[referencias[i][0].month - 1].casefold()} a ' \
                             f'{meses[referencias[i][1].month - 1].casefold()}, '
                    if i_year != i_plus_year:
                        texto = texto[:-2] + f' de {referencias[i][1].year}, '
            else:
                if i == len(referencias) - 1 or i_year != i_plus_year:
                    texto += f'{meses[referencias[i].month - 1].casefold()} de {referencias[i].year}, '
                else:
                    texto += f'{meses[referencias[i].month - 1].casefold()}, '
        elif freq == 'Y':
            if i == len(referencias) - 1 and i > 0:
                texto = texto[:-2] + ' e '
            if isinstance(referencias[i], list):
                texto += f'{referencias[i][0].year} a {referencias[i][1].year}, '
            else:
                texto += f'{referencias[i].year}, '
    texto = texto[:-2]
    return texto


def get_default_name_for_business(nome_empresa: str) -> str:
    minimo = 3
    maximo = 15
    retorno = ''
    for nome in nome_empresa.upper().split():
        if minimo <= len(retorno) <= maximo:
            break
        if nome not in ('EMPRESA', 'RESTAURANTE', 'BAR', 'COM', 'COMERCIO', 'IMPORTACAO',
                        'IMPORT', 'EXPORTACAO', 'EXPORT', 'E', 'DE', 'DA', 'DO'):
            nome = re.sub(r'[^A-Z]', '', nome)
            if len([c for c in nome if c in ('A', 'E', 'I', 'O', 'U')]) == 0:
                nome = nome.upper()
            else:
                nome = nome.capitalize()
            retorno += nome
    return retorno


def get_default_windows_app(suffix):
    class_root = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, suffix)
    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'{}\shell\open\command'.format(class_root)) as key:
        command = winreg.QueryValueEx(key, '')[0]
    return re.match(r'(".*?")', command).group(1)


def get_edge_version():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Edge\BLBeacon') as key:
        return winreg.QueryValueEx(key, 'version')[0]


def efd_schema_name(cnpj: str, referencia: str) -> str:
    if referencia.find('/') < 0:
        return None
    cnpj_digitos = re.sub(r'[^\d]', '', cnpj).zfill(14)
    return f'efd-{cnpj_digitos}-{referencia[3:]}-{referencia[:2]}'


def has_local_osf(path_name: Path):
    return (path_name / 'OSF Completa.pdf').is_file()


def get_dates_from_series(serie: pd.Series) -> list:
    return serie.values.astype('datetime64[us]').tolist()


def get_list_from_df(df: pd.DataFrame) -> list:
    # necessária essa conversão apenas para mostrar como data, não inteiro, quando é apenas uma coluna de data
    if len(df.keys()) == 1 and df.dtypes[0] == 'datetime64[ns]':
        lista = [[v] for v in get_dates_from_series(df[df.keys()[0]])]
    else:
        lista = df.values.tolist()
    retorno = []
    for itens in lista:
        linha = []
        for item in itens:
            if isinstance(item, date) or isinstance(item, datetime):
                linha.append(item.strftime('%d/%m/%Y'))
            else:
                linha.append(item)
        retorno.append(linha)
    return retorno


def get_df_from_list(listing: list[list], headers: list[str]) -> pd.DataFrame:
    data_cols = []
    for i in range(0, len(listing)):
        for j in range(0, len(listing[i])):
            if isinstance(listing[i][j], str) and listing[i][j].find('/') > 0:
                data_cols.append(j)
                listing[i][j] = datetime.strptime(listing[i][j], '%d/%m/%Y').date()
    df = pd.DataFrame(data=listing, columns=headers)
    for col in set(data_cols):
        df[headers[col]] = df[headers[col]].astype('datetime64[ns]')
    return df


def get_dates_from_df(df: pd.DataFrame, freq='M') -> list:
    retorno = []
    try:
        indice_data = df.dtypes.tolist().index('datetime64[ns]')
    except ValueError:
        raise Exception(f'Não encontrei coluna de data no Dataframe da verificação!')
    serie_data = df[df.keys()[indice_data]]
    retorno = get_dates_from_series(serie_data)
    if freq == 'Y':
        retorno = sorted(set([datetime(x.year, 1, 1).date() for x in retorno]))
    return retorno


def __get_json_file(path_name: Path):
    with path_name.open(mode='r') as outfile:
        dados = json.load(outfile)
    return dados


def get_efds_json_path(path_name: Path):
    return path_name / 'Dados' / 'efds.json'


def get_dados_efds(path_name: Path):
    return __get_json_file(get_efds_json_path(path_name))


def get_conta_fiscal_json_path(path_name: Path) -> Path:
    return path_name / 'Dados' / 'cficms.json'


def get_dados_observacoes_aiim() -> list[dict]:
    return __get_json_file(Path('resources/observacoes_aiim.json'))


def get_dados_efd(path_name: Path):
    try:
        return __get_json_file(path_name / 'Dados' / 'efds.json')
    except IOError:
        return {'efds': []}


def save_dados_efd(dados: dict, path_name: Path):
    os.makedirs(str(path_name / 'Dados'), exist_ok=True)
    with (path_name / 'Dados' / 'efds.json').open(mode='w') as outfile:
        json.dump(dados, outfile, sort_keys=True, indent=3)


def get_periodos_da_fiscalizacao(dadosOSF, rpa=True):
    inicio_fiscalizacao = datetime.strptime('01/' + dadosOSF['inicio_auditoria'], '%d/%m/%Y').date()
    fim_fiscalizacao = last_day_of_month(
        datetime.strptime('01/' + dadosOSF['fim_auditoria'], '%d/%m/%Y').date())
    retorno = []
    nome_regime = 'NORMAL - REGIME PERIÓDICO DE APURAÇÃO' if rpa else 'SIMPLES NACIONAL'
    for periodo in dadosOSF['historico_regime']:
        if periodo[2] == nome_regime:
            inicio = datetime.strptime(periodo[0], '%d/%m/%Y').date()
            if periodo[1] == 'Atual':
                fim = date.today()
            else:
                fim = datetime.strptime(periodo[1], '%d/%m/%Y').date()
            if inicio <= inicio_fiscalizacao <= fim or inicio <= fim_fiscalizacao <= fim \
                    or inicio_fiscalizacao <= inicio <= fim_fiscalizacao:
                retorno.append([max(inicio_fiscalizacao, inicio), min(fim_fiscalizacao, fim)])
    return retorno


def wait_downloaded_file(tmp_path, downloaded_file, timeout=10):
    tempo = 0
    while tempo <= timeout:
        time.sleep(1)
        tamanho = 0
        if not os.path.isfile(os.path.join(tmp_path, downloaded_file + '.crdownload')):
            # apenas conta o timeout se nao existe um arquivo temporario sendo baixado
            tempo = tempo + 1
        else:
            tamanho_atual = Path(os.path.join(tmp_path, downloaded_file + '.crdownload')).stat().st_size
            logger.info(f'Arquivo {downloaded_file} ainda está sendo baixado (tamanho {tamanho_atual}...')
            if tamanho == tamanho_atual:
                # resolve contar tempo se o tamanho não está mudando...
                tempo = tempo + 1

        if os.path.isfile(os.path.join(tmp_path, downloaded_file)):
            # verifica se arquivo foi modificado no último minuto
            ti_m = os.path.getmtime(os.path.join(tmp_path, downloaded_file))
            if time.time() - ti_m <= 60:
                break

        if tempo == timeout:
            raise Exception(f"Arquivo {downloaded_file} não foi gerado...")


def move_downloaded_file(tmp_path: Path, downloaded_file: str, destination: Path, timeout=10, replace=False):
    # espera o arquivo ser gravado (máximo timeout segundos)
    wait_downloaded_file(tmp_path, downloaded_file, timeout)

    # Move downloaded file to destination
    original_path = tmp_path / downloaded_file
    if tmp_path.absolute() != destination.absolute():
        if replace:
            if destination.is_dir():
                (destination / downloaded_file).unlink(missing_ok=True)
            else:
                destination.unlink(missing_ok=True)
        shutil.move(str(original_path), str(destination))


def get_file_size_pretty_print(path: Path) -> str:
    if path.stat().st_size < 1024:
        return f'{path.stat().st_size} bytes'
    elif path.stat().st_size / 1024 < 1024:
        return f'{int(path.stat().st_size / 1024)} KB'
    elif path.stat().st_size / (1024 * 1024) < 1024:
        return f'{int(path.stat().st_size / (1024 * 1024))} MB'
    elif path.stat().st_size / (1024 * 1024 * 1024) < 1024:
        return f'{int(path.stat().st_size / (1024 * 1024 * 1024))} GB'
    else:
        return f'{path.stat().st_size} bytes'


def clean_tmp_folder():
    get_tmp_path().mkdir(exist_ok=True)
    try:
        for (path, _, files) in os.walk('tmp'):
            for file in files:
                (Path(path) / file).unlink()
    except Exception:
        pass


def get_md5(file: Path) -> str:
    md5_hash = hashlib.md5()
    with file.open(mode="rb") as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
        return md5_hash.hexdigest()


def get_sha256(file: Path) -> str:
    sha256_hash = hashlib.sha256()
    with file.open(mode="rb") as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def get_icp_certificates() -> list:
    if os.name != 'nt':
        raise Exception('Você deveria estar rodando isso em Windows... o AIIM 2003 não roda em Linux!')
    certs = []
    with wincertstore.CertSystemStore("MY") as store:
        for cert in store.itercerts(usage=wincertstore.CLIENT_AUTH):
            pem = cert.get_pem()
            encodedDer = ''.join(pem.split("\n")[1:-2])

            cert_bytes = base64.b64decode(encodedDer)
            cert_pem = ssl.DER_cert_to_PEM_cert(cert_bytes)
            cert_details = x509.load_pem_x509_certificate(cert_pem.encode('utf-8'))

            tipos = cert_details.issuer.get_attributes_for_oid(ObjectIdentifier('2.5.4.10'))
            if tipos and tipos[0].value == 'ICP-Brasil' and cert_details.not_valid_after > datetime.now():
                certs.append(cert.get_name())
    return certs


def get_project_special_files():
    return [get_audit_json_path(get_tmp_path()).name,
            get_local_dados_afr_path().name,
            get_efds_json_path(get_tmp_path()).name,
            get_conta_fiscal_json_path(get_tmp_path()).name,
            get_folders_history_json_path().name]


def is_empty_directory(path: Path) -> bool:
    if not path.is_dir():
        raise ValueError(f'{path} não é um diretório, para verificar se está vazio!')
    return not any(path.iterdir())


class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        self.setLevel('INFO')

    def emit(self, record):
        self.log_queue.put(record)


class QueueFormatter(logging.Formatter):
    def format(self, record) -> str:
        if record.exc_info:
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return super().format(record)

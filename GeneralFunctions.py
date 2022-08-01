import hashlib
import json
import logging
import os
import re
import shutil
import time
import winreg
from datetime import date
from datetime import datetime
from datetime import timedelta
from json import JSONDecodeError
from pathlib import Path

meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho',
         'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
nomes_delegacias = {
    'DRTC-I': 'DELEGACIA REGIONAL TRIBUTÁRIA DA CAPITAL-I',
    'DRTC-II': 'DELEGACIA REGIONAL TRIBUTÁRIA DA CAPITAL-II',
    'DRTC-III': 'DELEGACIA REGIONAL TRIBUTÁRIA DA CAPITAL-III',
    'DRT-2': 'DELEGACIA REGIONAL TRIBUTÁRIA DO LITORAL',
    'DRT-3': 'DELEGACIA REGIONAL TRIBUTÁRIA DO VALE DO PARAÍBA',
    'DRT-4': 'DELEGACIA REGIONAL TRIBUTÁRIA DE SOROCABA',
    'DRT-5': 'DELEGACIA REGIONAL TRIBUTÁRIA DE CAMPINAS',
    'DRT-6': 'DELEGACIA REGIONAL TRIBUTÁRIA DE RIBEIRÃO PRETO',
    'DRT-7': 'DELEGACIA REGIONAL TRIBUTÁRIA DE BAURU',
    'DRT-8': 'DELEGACIA REGIONAL TRIBUTÁRIA DE SÃO JOSÉ DO RIO PRETO',
    'DRT-9': 'DELEGACIA REGIONAL TRIBUTÁRIA DE ARAÇATUBA',
    'DRT-10': 'DELEGACIA REGIONAL TRIBUTÁRIA DE PRESIDENTE PRUDENTE',
    'DRT-11': 'DELEGACIA REGIONAL TRIBUTÁRIA DE MARÍLIA',
    'DRT-12': 'DELEGACIA REGIONAL TRIBUTÁRIA DO ABCD',
    'DRT-13': 'DELEGACIA REGIONAL TRIBUTÁRIA DE GUARULHOS',
    'DRT-14': 'DELEGACIA REGIONAL TRIBUTÁRIA DE OSASCO',
    'DRT-15': 'DELEGACIA REGIONAL TRIBUTÁRIA DE ARARAQUARA',
    'DRT-16': 'DELEGACIA REGIONAL TRIBUTÁRIA DE JUNDIAÍ'
}
infractions = {}

# TODO mover senhas para alguma configuração
login_rede = "apmendonca"
senha_rede = "y4b62B#R"
certificado_senha = "991984"
login_sempapel = "SFP30114"
senha_sempapel = "z6p$GAGa#M^G!9JfF*s2&8c2heX7PY"

logger = logging.getLogger('AIIMGenerator')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(filename='AIIMGenerator.log', encoding='iso-8859-1')
fh.setLevel(logging.WARNING)
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s [%(threadName)s] - %(levelname)s - %(message)s"))
logger.addHandler(ch)


def last_day_of_month(any_day: datetime.date) -> date:
    next_month = any_day.replace(day=28) + timedelta(days=4)
    # subtract the number of remaining 'overage' days to get last day of current month, or said programattically
    # said, the previous day of the first of next month
    return next_month - timedelta(days=next_month.day)


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
                  and referencias[i].year == referencias[i+1].year)
                 or (freq == 'Y' and referencias[i + 1].year == referencias[i].year + 1)):
            sequencia = [referencias[i]]
            continue
        if sequencia and (i == len(referencias) - 1 or
                          ((freq == 'M' and (referencias[i].year != referencias[i+1].year
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
            referencias[i-1][0].year if isinstance(referencias[i-1], list) else referencias[i-1].year
        i_year = referencias[i][0].year if isinstance(referencias[i], list) else referencias[i].year
        i_plus_year = 0 if i == len(referencias) - 1 else \
            referencias[i+1][0].year if isinstance(referencias[i+1], list) else referencias[i+1].year
        if freq == 'M':
            if i > 0 and (i == len(referencias) - 1 or (i_last_year < i_year and i_year == all_years[-1]) or
                          (i_last_year == i_year and i_year < i_plus_year)):
                texto = texto[:-2] + ' e '
            if isinstance(referencias[i], list):
                if referencias[i][0].year != referencias[i][1].year:
                    texto += f'{meses[referencias[i][0].month - 1].casefold()} de {referencias[i][0].year} '\
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


def set_df_from_list(lista: list) -> list:
    retorno = []
    for x in lista:
        if type(x) == date:
            retorno.append(x.strftime('%d/%m/%Y'))
        else:
            retorno.append(x)
    return retorno


def get_df_from_list(lista: list, freq='M') -> list:
    retorno = []
    for x in lista:
        if x.find('/') > 0:
            retorno.append(datetime.strptime(x, '%d/%m/%Y').date())
        else:
            retorno.append(x)
    if len(retorno) > 0 and type(retorno[0]) == date:
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


def has_local_dados_afr():
    os.makedirs('local', exist_ok=True)
    return os.path.isfile('local/dados_afr.json')


def get_dados_observacoes_aiim() -> list[dict]:
    return __get_json_file(Path('resources/observacoes_aiim.json'))


def get_local_dados_afr():
    return __get_json_file(Path('local/dados_afr.json'))


def save_local_dados_afr(dados: dict):
    with open('local/dados_afr.json', 'w') as outfile:
        json.dump(dados, outfile, sort_keys=True, indent=1)


def get_dados_efd(path_name: Path):
    try:
        return __get_json_file(path_name / 'Dados' / 'efds.json')
    except IOError:
        return {'efds': []}


def save_dados_efd(dados: dict, path_name: Path):
    os.makedirs(str(path_name / 'Dados'), exist_ok=True)
    with (path_name / 'Dados' / 'efds.json').open(mode='w') as outfile:
        json.dump(dados, outfile, sort_keys=True, indent=3)


def __get_default_infractions():
    infractions_path = r'resources\infracoes'
    infracao = None
    if len(infractions) == 0:
        try:
            for (path, _, infracoes) in os.walk(infractions_path):
                for infracao in infracoes:
                    if infracao.endswith('.json'):
                        dicionario_json = __get_json_file(Path(path) / infracao)
                        infractions.update({os.path.splitext(os.path.basename(infracao))[0]: dicionario_json})
        except JSONDecodeError as jex:
            infractions.clear()
            raise Exception(f'Falha ao abrir arquivo de infração {infracao}: {jex}')
    return infractions


def get_infraction_for_name(infraction_name: str) -> dict:
    return __get_default_infractions().get(infraction_name, None)


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

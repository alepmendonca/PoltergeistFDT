import datetime
import json
import re
import keyring
from pathlib import Path
import PySimpleGUI as sg
import GeneralFunctions
from MDBReader import AIIM2003MDBReader


class Configuration:
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

    def __init__(self):
        self._dicionario: dict
        self.nome: str
        try:
            with GeneralFunctions.get_local_dados_afr_path().open(mode='r') as outfile:
                self._dicionario = json.load(outfile)
        except FileNotFoundError:
            self._dicionario = {}

        self.nome = self._dicionario.get('nome')
        self._drt = self._dicionario.get('drt')
        self._equipe_fiscal = int(self._dicionario.get('equipe', 0))
        self.funcional = self._dicionario.get('funcional')
        self.email = self._dicionario.get('email')
        self.intranet_login = self._dicionario.get('intranet_login')
        self.certificado = self._dicionario.get('certificado')
        self.sigadoc_login = self._dicionario.get('sigadoc_login')
        self.postgres_address = self._dicionario.get('postgres_address', 'localhost')
        self._postgres_port = self._dicionario.get('postgres_port', 5431)  # essa é a porta do AUD-Postgres
        self.postgres_dbname = self._dicionario.get('postgres_dbname', 'postgres')
        self.postgres_user = self._dicionario.get('postgres_user', 'postgres')  # essa é o usuário do AUD-Postgres
        self.ultima_pasta = Path(self._dicionario.get('ultima_pasta', str(GeneralFunctions.get_user_path().absolute())))
        self._efd_path = Path(self._dicionario['efd_path']) if self._dicionario.get('efd_path') else Path('efd-pva')
        self._efd_port = self._dicionario.get('efd_port', 3337)  # essa é a porta padrão do EFD PVA
        self.max_epat_attachment_size = 8
        self.max_dec_attachment_size = 5
        self.cadesp_last_update = self._dicionario.get('cadesp_last_update', datetime.date(2000, 1, 1))
        self.inidoneos_last_update = self._dicionario.get('inidoneos_last_update', datetime.date(2000, 1, 1))
        self.gia_last_update = self._dicionario.get('gia_last_update', datetime.date(2000, 1, 1))

    @property
    def intranet_pass(self) -> str:
        return keyring.get_password(GeneralFunctions.get_project_name(), 'intranet')

    @intranet_pass.setter
    def intranet_pass(self, password: str):
        keyring.set_password(GeneralFunctions.get_project_name(), 'intranet', password)

    @property
    def certificado_pass(self) -> str:
        return keyring.get_password(GeneralFunctions.get_project_name(), 'certificate')

    @certificado_pass.setter
    def certificado_pass(self, password: str):
        keyring.set_password(GeneralFunctions.get_project_name(), 'certificate', password)

    @property
    def sigadoc_pass(self) -> str:
        return keyring.get_password(GeneralFunctions.get_project_name(), 'sigadoc')

    @sigadoc_pass.setter
    def sigadoc_pass(self, password: str):
        keyring.set_password(GeneralFunctions.get_project_name(), 'sigadoc', password)

    @property
    def postgres_pass(self) -> str:
        return keyring.get_password(GeneralFunctions.get_project_name(), '')

    @postgres_pass.setter
    def postgres_pass(self, password: str):
        keyring.set_password(GeneralFunctions.get_project_name(), 'postgres', password)

    @property
    def drt_sigla(self) -> str:
        return self._drt

    @drt_sigla.setter
    def drt_sigla(self, sigla):
        if sigla:
            matches = re.search(r"DRT(C[\s\-]*I+|[\s\-]*\d+)", sigla)
            if not matches or len(matches.groups()) < 1:
                raise ValueError(f'Sigla de delegacia inválida: {sigla}')
            numero = re.match(r'[\s\-]*(\d+)', matches.group(1))
            match = f'DRT{matches.group(1) if not numero else "-" + str(int(numero.group(1)))}'
            if match not in self.nomes_delegacias.keys():
                raise ValueError(f'Sigla de delegacia inválida: {match}')
            self._drt = match

    def nucleo_fiscal(self) -> int:
        return int(self.equipe_fiscal / 10)

    @property
    def equipe_fiscal(self) -> int:
        return self._equipe_fiscal

    @equipe_fiscal.setter
    def equipe_fiscal(self, valor):
        if isinstance(valor, int):
            self._equipe_fiscal = valor
        elif isinstance(valor, str):
            matches = re.search(r"(\d+)", valor)
            if not matches or len(matches.groups()) < 1:
                raise ValueError(f'Equipe fiscal inválida: {valor}')
            self._equipe_fiscal = int(matches.group(1))

    @property
    def inidoneos_last_update(self) -> datetime.date:
        return self._inidoneos_last_update

    @inidoneos_last_update.setter
    def inidoneos_last_update(self, data):
        if isinstance(data, datetime.date):
            self._inidoneos_last_update = data
        elif isinstance(data, str):
            if re.search(r'\d{2}/\d{2}/\d{4}', data):
                self._inidoneos_last_update = datetime.datetime.strptime(data, '%d/%m/%Y').date()
            else:
                raise ValueError(f'Data para atualização de inidôneos inválida: {data}')

    @staticmethod
    def inidoneos_date_from_file(arquivo: Path) -> datetime.date:
        matches = re.search(r"Inid[oô]neos (\w+)[\s-](\d+)\.(rar|zip)", arquivo.name)
        if not matches or len(matches.groups()) < 3:
            raise ValueError('Nome de arquivo de inidôneos inválido - deve ter mês e ano no nome!')
        mes = matches.group(1)
        if len(mes) == 3:
            meses = [x[:3].capitalize() for x in GeneralFunctions.meses]
        else:
            meses = GeneralFunctions.meses
        if mes.capitalize() not in meses:
            raise ValueError(f"Não localizei o mês de geração do arquivo no nome, achei que era {mes}")
        mes = meses.index(mes.capitalize()) + 1
        return datetime.date(int(matches.group(2)), mes, 1)

    @property
    def gia_last_update(self) -> datetime.date:
        return self._gia_last_update

    @gia_last_update.setter
    def gia_last_update(self, data):
        if isinstance(data, datetime.date):
            self._gia_last_update = data
        elif isinstance(data, str):
            if re.search(r'\d{2}/\d{2}/\d{4}', data):
                self._gia_last_update = datetime.datetime.strptime(data, '%d/%m/%Y').date()
            else:
                raise ValueError(f'Data para atualização de GIAs inválida: {data}')

    @staticmethod
    def gia_date_from_file(arquivo: Path) -> datetime.date:
        matches = re.search(r"GIAs.*\s(\w+)[\s-](\d+)\.(rar|zip)", arquivo.name)
        if not matches or len(matches.groups()) < 3:
            raise ValueError('Nome de arquivo de GIAs inválido - deve ter mês e ano no nome!')
        mes = matches.group(1)
        if len(mes) == 3:
            meses = [x[:3].capitalize() for x in GeneralFunctions.meses]
        else:
            meses = GeneralFunctions.meses
        if mes.capitalize() not in meses:
            raise ValueError(f"Não localizei o mês de geração do arquivo no nome, achei que era {mes}")
        mes = meses.index(mes.capitalize()) + 1
        return datetime.date(int(matches.group(2)), mes, 1)

    @property
    def cadesp_last_update(self) -> datetime.date:
        return self._cadesp_last_update

    @cadesp_last_update.setter
    def cadesp_last_update(self, data):
        if isinstance(data, datetime.date):
            self._cadesp_last_update = data
        elif isinstance(data, str):
            if re.search(r'\d{2}/\d{2}/\d{4}', data):
                self._cadesp_last_update = datetime.datetime.strptime(data, '%d/%m/%Y').date()
            else:
                raise ValueError(f'Data para atualização de Cadesp inválida: {data}')

    @staticmethod
    def cadesp_date_from_file(arquivo: Path) -> datetime.date:
        matches = re.search(r"CadSefaz.*\s(\w+)[\s-](\d+)\.(rar|zip)", arquivo.name)
        if not matches or len(matches.groups()) < 3:
            raise ValueError('Nome de arquivo de Cadesp inválido - deve ter mês e ano no nome!')
        mes = matches.group(1)
        if len(mes) == 3:
            meses = [x[:3].capitalize() for x in GeneralFunctions.meses]
        else:
            meses = GeneralFunctions.meses
        if mes.capitalize() not in meses:
            raise ValueError(f"Não localizei o mês de geração do arquivo no nome, achei que era {mes}")
        mes = meses.index(mes.capitalize()) + 1
        return datetime.date(int(matches.group(2)), mes, 1)

    @property
    def postgres_port(self) -> int:
        return self._postgres_port

    @postgres_port.setter
    def postgres_port(self, porta: int | str):
        if isinstance(porta, str):
            try:
                valor = int(porta)
            except ValueError:
                raise ValueError('Porta deve ser um número!')
        else:
            valor = porta
        if valor <= 0:
            raise ValueError('Porta deve ser um número maior que zero!')
        self._postgres_port = valor

    @property
    def drt_nome(self) -> str:
        return self.nomes_delegacias[self.drt_sigla] if self.drt_sigla else None

    @drt_nome.setter
    def drt_nome(self, nome: str):
        if nome and nome in self.nomes_delegacias.values():
            self.drt_sigla = {v: k for k, v in self.nomes_delegacias.items()}[nome]

    @property
    def efd_path(self) -> Path:
        return Path(self._efd_path) if self._efd_path else None

    @efd_path.setter
    def efd_path(self, path: str | Path):
        if isinstance(path, str):
            self._efd_path = Path(path)
        else:
            self._efd_path = path
        if not (self.efd_java_path() / 'java.exe').is_file():
            msg_erro = f'Caminho para EFD PVA ICMS inválido. É necessário que exista ' \
                       f'um arquivo java.exe' \
                       f' dentro da subpasta {self.efd_java_path()}'
            self._efd_path = None
            raise ValueError(msg_erro)

    @property
    def efd_port(self) -> int:
        return self._efd_port

    @efd_port.setter
    def efd_port(self, porta: int | str):
        if isinstance(porta, str):
            try:
                valor = int(porta)
            except ValueError:
                raise ValueError('Porta deve ser um número!')
        else:
            valor = porta
        if valor <= 0:
            raise ValueError('Porta deve ser um número maior que zero!')
        self._efd_port = valor

    def efd_java_path(self) -> Path:
        return self.efd_path / 'jre' / 'bin'

    def save(self):
        dadosAFR = self.__dict__.copy()
        dadosAFR['drt'] = self._drt
        dadosAFR['equipe'] = self._equipe_fiscal
        dadosAFR['postgres_port'] = self.postgres_port
        dadosAFR['ultima_pasta'] = str(self.ultima_pasta.absolute())
        dadosAFR['efd_path'] = str(self.efd_path.absolute())
        dadosAFR['efd_port'] = self.efd_port
        dadosAFR['inidoneos_last_update'] = self._inidoneos_last_update.strftime('%d/%m/%Y')
        dadosAFR['gia_last_update'] = self._gia_last_update.strftime('%d/%m/%Y')
        dadosAFR['cadesp_last_update'] = self._cadesp_last_update.strftime('%d/%m/%Y')
        for k in [k for k in dadosAFR.keys() if k.startswith('_') or not dadosAFR[k]]:
            dadosAFR.pop(k)
        with GeneralFunctions.get_local_dados_afr_path().open(mode='w') as outfile:
            json.dump(dadosAFR, outfile, sort_keys=True, indent=1)


_singleton: Configuration = None


def get() -> Configuration:
    global _singleton
    if not _singleton:
        if GeneralFunctions.get_local_dados_afr_path().is_file():
            _singleton = Configuration()
    return _singleton


def configuration_window():
    layout = [
        [sg.Frame(title='Dados do AFRE', layout=[
            [sg.Text("Nome Completo:"), sg.InputText(key='nome', default_text=get().nome, expand_x=True)],
            [sg.Text("E-mail:"), sg.InputText(key='email', default_text=get().email, expand_x=True)],
            [sg.Text("Delegacia Tributária:"), sg.Combo(values=list(Configuration.nomes_delegacias.values()),
                                                        key='drt_nome', default_value=get().drt_nome,
                                                        readonly=True, expand_x=True)],
            [sg.Text("Equipe Fiscal:"), sg.Input(key='equipe_fiscal', default_text=get().equipe_fiscal, expand_x=True)]
        ], expand_x=True)],
        [sg.Frame(title='Autenticação de Sistemas Sefaz', layout=[
            [sg.Text("Usuário da intranet:"), sg.Input(key='intranet_login', default_text=get().intranet_login,
                                                       expand_x=True)],
            [sg.Text("Senha da intranet:"), sg.Input(key='intranet_pass', default_text=get().intranet_pass,
                                                     password_char='*', expand_x=True)],
            [sg.Text("Certificado digital:"), sg.Combo(values=sorted(GeneralFunctions.get_icp_certificates()),
                                                       key='certificado', default_value=get().certificado,
                                                       readonly=True, expand_x=True)],
            [sg.Text("Senha do certificado digital:"),
             sg.Input(key='certificado_pass', default_text=get().certificado_pass,
                      password_char='*', expand_x=True)],
            [sg.Text("Usuário do Sem Papel (Sigadoc):"), sg.Input(key='sigadoc_login', default_text=get().sigadoc_login,
                                                                  expand_x=True)],
            [sg.Text("Senha do Sem Papel (Sigadoc):"), sg.Input(key='sigadoc_pass', default_text=get().sigadoc_pass,
                                                                password_char='*', expand_x=True)]
        ], expand_x=True)],
        [sg.Frame(title='Banco de Dados do AFRE', layout=[
            [sg.Text("Local (padrão localhost):"), sg.Input(key='postgres_address', default_text=get().postgres_address,
                                                            expand_x=True)],
            [sg.Text("Porta (padrão 5432, AUD-Postgres 5431):"),
             sg.Input(key='postgres_port', default_text=get().postgres_port,
                      expand_x=True)],
            [sg.Text("Instância (padrão postgres):"),
             sg.Input(key='postgres_dbname', default_text=get().postgres_dbname,
                      expand_x=True)],
            [sg.Text("Usuário (padrão postgres):"), sg.Input(key='postgres_user', default_text=get().postgres_user,
                                                             expand_x=True)],
            [sg.Text("Senha (padrão sem senha):"), sg.Input(key='postgres_pass', default_text=get().postgres_pass,
                                                            expand_x=True, password_char='*')],
        ], expand_x=True)],
        [sg.Frame(title='EFD PVA ICMS', layout=[
            [sg.Text("Pasta do EFD PVA ICMS:"), sg.Input(key='efd_path', default_text=get().efd_path,
                                                         disabled=True, expand_x=True),
             sg.FolderBrowse('Escolher',
                             initial_folder=str(get().efd_path if get().efd_path is not None
                                                else GeneralFunctions.get_user_path()))],
            [sg.Text("Porta (padrão EFD PVA ICMS 3337, instalação interna 3336):"),
             sg.Input(key='efd_port', default_text=get().efd_port, expand_x=True)]
        ], expand_x=True)],
        [sg.Push(), sg.Button('Salvar'), sg.Button('Cancelar'), sg.Push()]
    ]
    window = sg.Window('Propriedades do Sistema', layout, modal=True)
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Cancelar':
            break
        elif event == 'Salvar':
            try:
                for key, value in values.items():
                    if key != key.lower():
                        continue
                    if value != getattr(get(), key):
                        setattr(get(), key, value)
            except ValueError as ex:
                sg.popup_error('Erro', str(ex))
            else:
                get().save()
                break
    window.close()

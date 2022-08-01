import json
import re
from pathlib import Path
import PySimpleGUI as sg
import GeneralFunctions


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
        self.intranet_pass = self._dicionario.get('intranet_pass')
        self.certificado = self._dicionario.get('certificado')
        self.certificado_pass = self._dicionario.get('certificado_pass')
        self.sigadoc_login = self._dicionario.get('sigadoc_login')
        self.sigadoc_pass = self._dicionario.get('sigadoc_pass')
        self.ultima_pasta = Path(self._dicionario.get('ultima_pasta', str(GeneralFunctions.get_user_path().absolute())))
        self.max_epat_attachment_size = 8

    @property
    def drt_sigla(self) -> str:
        return self._drt

    @drt_sigla.setter
    def drt_sigla(self, sigla):
        if sigla:
            matches = re.search(r"(DRT[C\-\dI]+)", sigla)
            if not matches or len(matches.groups()) < 1:
                raise ValueError(f'Sigla de delegacia inválida: {sigla}')
            self._drt = matches.group(1)

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
    def drt_nome(self) -> str:
        return self.nomes_delegacias[self.drt_sigla]

    @drt_nome.setter
    def drt_nome(self, nome: str):
        if nome and nome in self.nomes_delegacias.values():
            self.drt_sigla = {v: k for k, v in self.nomes_delegacias.items()}[nome]

    def save(self):
        dadosAFR = self.__dict__.copy()
        dadosAFR['drt'] = self._drt
        dadosAFR['equipe'] = self._equipe_fiscal
        dadosAFR['ultima_pasta'] = str(self.ultima_pasta.absolute())
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
        [sg.Text("Nome Completo:"), sg.InputText(key='nome', default_text=get().nome, expand_x=True)],
        [sg.Text("E-mail:"), sg.InputText(key='email', default_text=get().email, expand_x=True)],
        [sg.Text("Delegacia Tributária:"), sg.Combo(values=list(Configuration.nomes_delegacias.values()),
                                                    key='drt_nome', default_value=get().drt_nome,
                                                    readonly=True, expand_x=True)],
        [sg.Text("Equipe Fiscal:"), sg.Input(key='equipe_fiscal', default_text=get().equipe_fiscal, expand_x=True)],
        [sg.Text("Usuário da intranet:"), sg.Input(key='intranet_login', default_text=get().intranet_login,
                                                   expand_x=True)],
        [sg.Text("Senha da intranet:"), sg.Input(key='intranet_pass', default_text=get().intranet_pass,
                                                 password_char='*', expand_x=True)],
        [sg.Text("Certificado digital:"), sg.Combo(values=sorted(GeneralFunctions.get_icp_certificates()),
                                                   key='certificado', default_value=get().certificado,
                                                   readonly=True, expand_x=True)],
        [sg.Text("Senha do certificado digital:"), sg.Input(key='certificado_pass', default_text=get().certificado_pass,
                                                            password_char='*', expand_x=True)],
        [sg.Text("Usuário do Sem Papel (Sigadoc):"), sg.Input(key='sigadoc_login', default_text=get().sigadoc_login,
                                                              expand_x=True)],
        [sg.Text("Senha do Sem Papel (Sigadoc):"), sg.Input(key='sigadoc_pass', default_text=get().sigadoc_pass,
                                                            password_char='*', expand_x=True)],
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
                    if value != getattr(get(), key):
                        setattr(get(), key, value)
            except ValueError as ex:
                sg.popup_error('Erro', str(ex))
            else:
                get().save()
                break
    window.close()

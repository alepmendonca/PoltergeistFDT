import json
import re
from pathlib import Path
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
        self._nucleo_fiscal = int(self._dicionario.get('nf', 0))
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

    @property
    def nucleo_fiscal(self) -> int:
        return self._nucleo_fiscal

    @nucleo_fiscal.setter
    def nucleo_fiscal(self, valor):
        if isinstance(valor, int):
            self._nucleo_fiscal = valor
        elif isinstance(valor, str):
            matches = re.search(r"(\d+)", valor)
            if not matches or len(matches.groups()) < 1:
                raise ValueError(f'Núcleo fiscal inválido: {valor}')
            self._nucleo_fiscal = int(matches.group(1))

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

    def drt_nome(self):
        return self.nomes_delegacias[self.drt_sigla]

    def save(self):
        dadosAFR = self.__dict__.copy()
        dadosAFR['drt'] = self._drt
        dadosAFR['nf'] = self._nucleo_fiscal
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

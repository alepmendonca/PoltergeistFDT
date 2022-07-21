import importlib
import json
import os
import re
import sys
from json import JSONDecodeError
from pathlib import Path


class ConfigFileDecoderException(Exception):
    pass


class InfractionArticle:
    def is_special(self):
        return False


class InfractionSpecialArticle(InfractionArticle):
    def __init__(self, article_data: dict):
        self.text = article_data['especial']

    def is_special(self):
        return True


class InfractionRICMSArticle(InfractionArticle):
    def __init__(self, infraction_name: str, article_data: dict):
        try:
            self.artigo = str(article_data['artigo'])
            self.inciso = str(int(str(article_data.get('inciso', '0'))))
            if int(self.inciso) <= 0:
                self.inciso = None
            self.alinea = re.sub(r'[^a-z]', '', article_data.get('alinea', ''))
            if self.alinea == '':
                self.alinea = None
            self.paragrafo = article_data.get('paragrafo', '0')
            if self.paragrafo != 'UN':
                self.paragrafo = re.sub(r'[^\d]', '', self.paragrafo)
                if len(self.paragrafo) == 0:
                    raise ConfigFileDecoderException(f'Capitulação da infração {infraction_name} '
                                                     f'possui parágrafo inválido: {self.paragrafo}')
                if int(self.paragrafo) <= 0:
                    self.paragrafo = None
            self.item = re.sub(r'[^\d]', '', article_data.get('item', '0'))
            if int(self.item) <= 0:
                self.item = None
            self.letra = re.sub(r'[^a-z]', '', article_data.get('letra', ''))
            if self.letra == '':
                self.letra = None
            self.juntar = article_data.get('juntar', 'Nenhum')
            if self.juntar not in ('Nenhum', 'C/C', 'E'):
                raise ConfigFileDecoderException(f'Capitulação da infração {infraction_name} '
                                                 f'possui opção "juntar" inválida: {self.juntar}')
        except ValueError:
            raise ConfigFileDecoderException(f'Capitulação da infração {infraction_name} '
                                             f'possui dados inválidos: {article_data}')


class InfractionCapitulation:
    def __init__(self, infraction_name: str, dicionario: dict):
        self.clear_existing_capitulation = dicionario.get('limpa', False)
        self.articles: list[InfractionArticle] = \
            [InfractionSpecialArticle(artigo) if artigo.get('especial', None)
             else InfractionRICMSArticle(infraction_name, artigo)
             for artigo in dicionario.get('artigos', [])]


class Analysis:

    _all_analysis = {}

    @classmethod
    def __get_default_analysis_dict(cls) -> dict:
        verificacoes_path = r'resources/verificacoes'
        if len(cls._all_analysis) == 0:
            try:
                for (path, _, verificacoes) in os.walk(verificacoes_path):
                    for verificacao in verificacoes:
                        if verificacao.endswith('.json'):
                            a = cls(Path(path) / verificacao)
                            cls._all_analysis.update({a.name: a})
            except ConfigFileDecoderException as ce:
                cls._all_analysis.clear()
                raise ce
        return cls._all_analysis

    @classmethod
    def get_default_analysis(cls) -> list:
        return list(cls.__get_default_analysis_dict().values())

    @classmethod
    def get_analysis_for_name(cls, name: str):
        return cls.__get_default_analysis_dict().get(name, None)

    def __init__(self, json_file: Path):
        try:
            with json_file.open(mode='r') as outfile:
                dados = json.load(outfile)
        except JSONDecodeError as jex:
            raise ConfigFileDecoderException(f'Falha ao abrir arquivo de análise {json_file}, '
                                             f'está com falha no seu conteúdo: {jex}')

        try:
            self.name = dados['verificacao']
            if "AnalysisFunctions" not in sys.modules:
                modulo = importlib.import_module("AnalysisFunctions")
            else:
                modulo = sys.modules["AnalysisFunctions"]
            self.sheet_default_name = dados.get('planilha_nome', 'Nome da Planilha')
            if dados.get('consulta', None):
                self.query = dados['consulta']
                self.query_detail = dados.get('consulta_detalhamento', None)
                self.function = None
            else:
                self.function = getattr(modulo, dados['funcao']['nome'])
                self.function_description = dados['funcao']['descricao']
                try:
                    self.function_ddf = getattr(modulo, f"{dados['funcao']['nome']}_ddf")
                except AttributeError:
                    self.function_ddf = None
                self.query = None
            self.fix_database_function = None
            if dados.get('acerto_base', None):
                self.fix_database_function = getattr(modulo, dados['acerto_base'])
            self.choose_between_notification_or_infraction_function = None
            if dados.get('manda_notificacao_ou_gera_infracao', None):
                self.choose_between_notification_or_infraction_function = \
                    getattr(modulo, dados['manda_notificacao_ou_gera_infracao'])
            self.notification_subject = dados.get('notificacao', {}).get('assunto')
            self.notification_title = dados.get('notificacao', {}).get('titulo')
            self.notification_body = dados.get('notificacao', {}).get('corpo')
            self.notification_attachments = dados.get('notificacao', {}).get('anexo')
            infracoes = dados['infracoes']
            if isinstance(infracoes, list):
                self.infractions = [Infraction(i, self, Path(r'resources/infracoes', f'{i}.json')) for i in infracoes]
            else:
                self.infractions = []
                for i, overriden_data in dict(infracoes).items():
                    infraction = Infraction(i, self, Path(r'resources/infracoes', f'{i}.json'))
                    infraction.update(overriden_data)
                    self.infractions.append(infraction)
        except KeyError as e:
            raise ConfigFileDecoderException(f'Arquivo de análise {json_file} não tem um '
                                             f'parâmetro obrigatório: {e.args}')

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __lt__(self, other):
        return self.name < other.name

    def infraction_names(self) -> list[str]:
        return [i.name for i in self.infractions]

    def get_infraction(self, searched_infraction: str):
        infractions = list(filter(lambda i: i.name == searched_infraction, self.infractions))
        if len(infractions) == 0:
            raise ConfigFileDecoderException(f'Não existe infração de nome {searched_infraction} '
                                             f'associado à verificação {self.name}')
        return infractions[0]

    def must_choose_between_notification_and_infraction(self) -> bool:
        return self.choose_between_notification_or_infraction_function is not None

    def choose_between_notification_and_infraction(self) -> dict[str]:
        if not self.must_choose_between_notification_and_infraction():
            return None
        else:
            return self.choose_between_notification_or_infraction_function()

    def is_query_based(self):
        return self.query is not None

    def has_notification_any_attachments(self) -> bool:
        return bool(self.notification_attachments)

    def filter_columns(self) -> list[str]:
        return [i.filtro_coluna for i in self.infractions if i.has_filtro()]


class AiimProof:
    proof_types = {
        'listagem': {'modulo': 'AiimProofGenerator', 'funcao': 'get_aiim_listing_from_sheet'},
        'LRE': {'modulo': 'AiimProofGenerator', 'funcao': 'get_lre', 'allows_sampling': True},
        'LRS': {'modulo': 'AiimProofGenerator', 'funcao': 'get_lrs', 'allows_sampling': True},
        'LRI': {'modulo': 'AiimProofGenerator', 'funcao': 'get_lri'},
        'LRAICMS': {'modulo': 'AiimProofGenerator', 'funcao': 'get_lraicms'},
        'DFe': {'modulo': 'AiimProofGenerator', 'funcao': 'get_dfe', 'allows_sampling': True},
        'GIA-OutrosDebitos': {'modulo': 'AiimProofGenerator', 'funcao': 'get_gia_outros_debitos', 'allows_sampling': True},
        'GIA-OutrosCreditos': {'modulo': 'AiimProofGenerator', 'funcao': 'get_gia_outros_creditos', 'allows_sampling': True},
        'EFD-Obrigatoriedade': {'modulo': 'AiimProofGenerator', 'funcao': 'get_efd_obrigatoriedade'},
        'EFD-Extrato': {'modulo': 'AiimProofGenerator', 'funcao': 'get_efd_entregas'}
    }

    @classmethod
    def generate_notification_proof(cls, aiim_item, ws) -> list[Path]:
        funcao = getattr(sys.modules['AiimProofGenerator'], 'get_notification_and_response')
        return funcao(aiim_item, ws)

    def __init__(self, dic: dict):
        self.tipo = dic.get('tipo', 'Nenhum tipo informado')
        self.descricao = dic['descricao']
        if self.tipo not in self.proof_types:
            raise ValueError(f'Tipo de prova inválido: {self.tipo}')
        if self.proof_types[self.tipo]['modulo'] not in sys.modules:
            modulo = importlib.import_module(self.proof_types[self.tipo]['modulo'])
        else:
            modulo = sys.modules[self.proof_types[self.tipo]['modulo']]
        self.sample_generation_function = getattr(modulo, "get_df_list")
        self.function = getattr(modulo, self.proof_types[self.tipo]['funcao'])
        self.sample_verification_function = getattr(modulo, "has_sample")
        self.allows_sampling = self.proof_types[self.tipo].get('allows_sampling', False)

    def is_prioritary(self) -> bool:
        return self.proof_types[self.tipo].get('initial', False)

    def generate_proof(self, aiim_item, ws, pva) -> list[Path]:
        return self.function(aiim_item, ws, pva)

    def has_sample(self, aiim_item) -> bool:
        return self.allows_sampling and self.sample_verification_function(aiim_item)


class Infraction:
    __roman_to_number = {'I': 1, 'II': 2, 'III': 3,
                         'IV': 4, 'V': 5, 'VI': 6,
                         'VII': 7, 'VIII': 8, 'IX': 9,
                         'X': 10, 'XI': 11, 'XII': 12, 'SN': 99}

    def __init__(self, infraction_name: str, analysis: Analysis, json_file: Path):
        self.filtro_coluna = None
        self.filtro_tipo = None
        self.capitulation: InfractionCapitulation
        self.name = infraction_name
        self.analysis = analysis
        self.analysis_name = analysis.name
        self.inciso = re.search(r'^[A-Z]+', self.name).group()
        self.alinea = re.search(r'[a-z]+', self.name).group()
        self.relatorio_circunstanciado = None
        self.provas: list[AiimProof] = []
        try:
            with json_file.open(mode='r') as outfile:
                dados = json.load(outfile)
        except JSONDecodeError as jex:
            raise ConfigFileDecoderException(f'Falha ao abrir arquivo de infração {json_file}, '
                                             f'está com falha no seu conteúdo: {jex}')
        except FileNotFoundError:
            raise ConfigFileDecoderException(f'Não foi localizado arquivo de infração {json_file}')

        try:
            self.report = dados['relato']
            self.report_updated = self.report
            self.ttpa = dados['ttpa']
            self.order = dados.get('ordem')
            self.operation_type = dados.get('operacao')
            if self.operation_type and self.operation_type not in ('Tributada', 'Não Tributada', 'Isenta'):
                raise ConfigFileDecoderException(f'Arquivo de infração {json_file} tem um '
                                                 f'tipo de operação inválido: {self.operation_type}')
            if dados.get('capitulacao'):
                self.capitulation = InfractionCapitulation(self.name, dados['capitulacao'])
            if dados.get('relatorio_circunstanciado'):
                self.relatorio_circunstanciado = dados['relatorio_circunstanciado']
            self.provas = [AiimProof(dic) for dic in dados.get('provas', [])]
        except KeyError as e:
            raise ConfigFileDecoderException(f'Arquivo de infração {json_file} não tem '
                                             f'um parâmetro obrigatório: {e.args}')

    def update(self, dicionario: dict):
        if dicionario.get('relato'):
            self.report = dicionario['relato']
        if dicionario.get('ordem'):
            self.order = dicionario['ordem']
        if dicionario.get('capitulacao'):
            self.capitulation = InfractionCapitulation(self.name, dicionario['capitulacao'])
        if dicionario.get('relatorio_circunstanciado'):
            self.relatorio_circunstanciado = dicionario['relatorio_circunstanciado']
        if dicionario.get('provas'):
            self.provas = [AiimProof(dic) for dic in dicionario.get('provas', [])]
        if dicionario.get('filtro_coluna'):
            self.filtro_coluna = dicionario['filtro_coluna']
            self.filtro_tipo = dicionario['filtro']
            if self.filtro_tipo not in ['positivo', 'negativo']:
                raise ConfigFileDecoderException(f'Opção inválida para filtro: {self.filtro_tipo}')
            if dicionario.get('verificacao'):
                self.analysis_name = dicionario['verificacao']

    def inciso_number(self) -> int:
        return self.__roman_to_number[self.inciso]

    def has_filtro(self) -> bool:
        return self.filtro_tipo is not None

    def is_positive_filter(self) -> bool:
        return self.filtro_tipo == 'positivo'

    def sheet_extended_name(self, sheet_name: str) -> str:
        return f'{sheet_name} - {self.inciso}{self.alinea}'

    def __lt__(self, other):
        return self.inciso_number() < other.inciso_number() or \
               (self.inciso_number() == other.inciso_number() and self.alinea < other.alinea)

    def __repr__(self):
        return f'{self.inciso},"{self.alinea}" - {self.analysis}'

    def __str__(self):
        return f'{self.inciso},"{self.alinea}" - {self.analysis}'

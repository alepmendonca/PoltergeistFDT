from __future__ import annotations
import copy
import importlib
import json
import os
import re
import sys
from json import JSONDecodeError
from pathlib import Path

import jsonschema
from jsonschema.exceptions import ValidationError

import GeneralFunctions


class ConfigFileDecoderException(Exception):
    pass


class InfractionArticle:
    def is_special(self) -> bool:
        return False


class InfractionSpecialArticle(InfractionArticle):
    def __init__(self, article_data: dict):
        self.text = article_data['especial']

    def is_special(self) -> bool:
        return True


class InfractionRICMSArticle(InfractionArticle):
    def __init__(self, infraction, article_data: dict):
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
                    raise ConfigFileDecoderException(f'Capitulação da infração {infraction} '
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
                raise ConfigFileDecoderException(f'Capitulação da infração {infraction} '
                                                 f'possui opção "juntar" inválida: {self.juntar}')
        except ValueError:
            raise ConfigFileDecoderException(f'Capitulação da infração {infraction} '
                                             f'possui dados inválidos: {article_data}')


class InfractionCapitulation:
    def __init__(self, infraction, dicionario: dict):
        self.clear_existing_capitulation = dicionario.get('limpa', False)
        self.articles: list[InfractionArticle] = \
            [InfractionSpecialArticle(artigo) if artigo.get('especial', None)
             else InfractionRICMSArticle(infraction, artigo)
             for artigo in dicionario.get('artigos', [])]


class Analysis:
    _builtin_analysis = {}
    _user_analysis = {}
    _audit_analysis = {}

    @classmethod
    def __put_analysis_from_path_in_dict(cls, directory: Path, dic: dict, validate=True):
        if len(dic) == 0 and directory:
            try:
                for (path, _, verificacoes) in os.walk(str(directory.absolute())):
                    for verificacao in verificacoes:
                        if verificacao.endswith('.json') and \
                                verificacao not in GeneralFunctions.get_project_special_files():
                            a = cls(Path(path) / verificacao, validate)
                            dic.update({a.name: a})
            except ConfigFileDecoderException as ce:
                dic.clear()
                raise ce

    @classmethod
    def __get_default_analysis_dict(cls, validate=False) -> dict[str, Analysis]:
        cls.__put_analysis_from_path_in_dict(Path(r'resources/verificacoes'), cls._builtin_analysis, validate)
        return cls._builtin_analysis

    @classmethod
    def __get_user_analysis_dict(cls) -> dict[str, Analysis]:
        cls.__put_analysis_from_path_in_dict(GeneralFunctions.get_user_path(), cls._user_analysis)
        return cls._user_analysis

    @classmethod
    def __get_audit_analysis_dict(cls, audit_path: Path = None) -> dict[str, Analysis]:
        cls.__put_analysis_from_path_in_dict(audit_path, cls._audit_analysis)
        return cls._audit_analysis

    @classmethod
    def get_all_analysis(cls, audit_path: Path = None) -> list[Analysis]:
        vls = list(cls.__get_default_analysis_dict().values())
        vls.extend(list(cls.__get_user_analysis_dict().values()))
        vls.extend(list(cls.__get_audit_analysis_dict(audit_path).values()))
        return vls

    @classmethod
    def load_audit_analysis(cls, path_home: Path):
        cls.__get_audit_analysis_dict(path_home)

    @classmethod
    def clear_audit_analysis(cls):
        cls._audit_analysis.clear()

    @classmethod
    def clear_user_analysis(cls):
        cls._user_analysis.clear()

    @classmethod
    def get_analysis_by_name(cls, audit_path: Path, name: str):
        return cls.__get_default_analysis_dict().get(
            name, cls.__get_user_analysis_dict().get(
                name, cls.__get_audit_analysis_dict(audit_path).get(name)))

    @classmethod
    def get_json_analysis_schema(cls) -> dict:
        with Path(r'resources/verificacoes-schema.json').open(mode='r') as outfile:
            return json.load(outfile)

    def __init__(self, par: Path | dict, validate: bool = True):
        if isinstance(par, Path):
            try:
                with par.open(mode='r') as outfile:
                    dados = json.load(outfile)
                # valida dados contra o JSON schema
                if validate:
                    try:
                        jsonschema.validate(dados, self.get_json_analysis_schema(),
                                            format_checker=jsonschema.draft202012_format_checker)
                    except ValidationError as ex:
                        raise ConfigFileDecoderException(f'Arquivo de análise {par.name} com formato inválido. '
                                                         f'Detalhamento dos erros encontrados:\n'
                                                         f"{ex.message}")
            except JSONDecodeError as jex:
                raise ConfigFileDecoderException(f'Falha ao abrir arquivo de análise {par}, '
                                                 f'está com falha no seu conteúdo: {jex}')
        else:
            dados = par

        try:
            self.name = dados['verificacao']
            if "AnalysisFunctions" not in sys.modules:
                modulo = importlib.import_module("AnalysisFunctions")
            else:
                modulo = sys.modules["AnalysisFunctions"]
            if dados.get('consulta', None):
                self.query = dados['consulta']
                self.query_detail = dados.get('consulta_detalhamento', None)
                self.sheet_default_name = dados.get('planilha_nome', 'Nome da Planilha')
                self.function = None
                self.function_ddf = None
                if dados.get('funcao_ddf'):
                    try:
                        self.function_ddf = getattr(modulo, f"{dados['funcao_ddf']}")
                    except AttributeError:
                        raise ValueError(f"Não existe a função {modulo.__name__}.{dados['funcao_ddf']}. "
                                         f"Verifique o cadastro da verificação {self.name}")
                self.ddf_headers = ['Referência']
            else:
                self.function_description = dados['funcao']['descricao']
                try:
                    self.function = getattr(modulo, dados['funcao']['nome'])
                except AttributeError:
                    raise ValueError(f"Não existe a função {modulo.__name__}.{dados['funcao']['nome']}. "
                                     f"Verifique o cadastro da verificação {self.name}")
                try:
                    self.function_ddf = getattr(modulo, f"{dados['funcao']['nome']}_ddf")
                except AttributeError:
                    raise ValueError(f"Não existe a função {modulo.__name__}.{dados['funcao']['nome']}_ddf. "
                                     f"Verifique o cadastro da verificação {self.name}")
                self.ddf_headers = dados['funcao'].get('cabecalho', ['Referência'])
                self.query = None
                self.query_detail = None
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
            self.infractions: list[Infraction] = []
            infracoes = dados['infracoes']
            if isinstance(infracoes, list):
                self.infractions.extend([Infraction.get_by_name(i) for i in infracoes])
                for i in self.infractions:
                    i.analysis = self
            else:
                for i, overriden_data in dict(infracoes).items():
                    infraction = Infraction.get_by_name(i)
                    infraction.analysis = self
                    infraction.update(overriden_data)
                    self.infractions.append(infraction)
        except KeyError as e:
            raise ConfigFileDecoderException(f'Arquivo de análise {par} não tem um '
                                             f'parâmetro obrigatório: {e.args}')

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __lt__(self, other):
        return self.name < other.name

    def infraction_names(self) -> list[str]:
        return [i.nome for i in self.infractions]

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
        'listagem': {'modulo': 'AiimProofGenerator', 'funcao': 'get_aiim_listing_from_sheet',
                     'nome': 'Planilha'},
        'listagem-detalhe': {'modulo': 'AiimProofGenerator', 'funcao': 'get_aiim_detailed_listing_from_sheet',
                             'nome': 'Planilha Detalhada'},
        'creditos': {'modulo': 'AiimProofGenerator', 'funcao': 'get_item_credit_sheet',
                     'nome': 'Glosa de Créditos'},
        'LRE': {'modulo': 'AiimProofGenerator', 'funcao': 'get_lre', 'allows_sampling': True,
                'nome': 'Livro de Entradas'},
        'LRS': {'modulo': 'AiimProofGenerator', 'funcao': 'get_lrs', 'allows_sampling': True,
                'nome': 'Livro de Saídas'},
        'LRI': {'modulo': 'AiimProofGenerator', 'funcao': 'get_lri',
                'nome': 'Livro de Inventário'},
        'LRAICMS': {'modulo': 'AiimProofGenerator', 'funcao': 'get_lraicms',
                    'nome': 'Livro de Apuração ICMS'},
        'DFe': {'modulo': 'AiimProofGenerator', 'funcao': 'get_dfe', 'allows_sampling': True,
                'nome': 'Documentos Fiscais'},
        'GIA-Extrato': {'modulo': 'AiimProofGenerator', 'funcao': 'get_gias_entregues',
                        'nome': 'GIA - Entregas'},
        'GIA-Apuracao': {'modulo': 'AiimProofGenerator', 'funcao': 'get_gia_apuracao',
                         'nome': 'GIA - Apuração'},
        'GIA-OutrosDebitos': {'modulo': 'AiimProofGenerator', 'funcao': 'get_gia_outros_debitos',
                              'allows_sampling': True, 'nome': 'GIA - Outros Débitos'},
        'GIA-OutrosCreditos': {'modulo': 'AiimProofGenerator', 'funcao': 'get_gia_outros_creditos',
                               'allows_sampling': True, 'nome': 'GIA - Outros Créditos'},
        'EFD-Obrigatoriedade': {'modulo': 'AiimProofGenerator', 'funcao': 'get_efd_obrigatoriedade',
                                'nome': 'EFD - Obrigatoriedade'},
        'EFD-Extrato': {'modulo': 'AiimProofGenerator', 'funcao': 'get_efd_entregas',
                        'nome': 'EFD - Entregas'},
        'NFe-Inutilizacao': {'modulo': 'AiimProofGenerator', 'funcao': 'get_nfe_inutilizacoes',
                             'nome': 'NF-e - Inutilização'}
    }

    @classmethod
    def get_proof_type_by_name(cls, nome: str) -> str:
        return [k for k, v in cls.proof_types.items() if v['nome'] == nome][0]

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

    def proof_type_name(self) -> str:
        return self.proof_types[self.tipo]['nome']

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

    __infractions = []

    @classmethod
    def all_default_infractions(cls):
        if not cls.__infractions:
            infractions_path = r'resources\infracoes'
            for (path, _, infracoes) in os.walk(infractions_path):
                for infracao in infracoes:
                    if infracao.endswith('.json'):
                        cls.__infractions.append(Infraction((Path(path) / infracao)))
            cls.__infractions.sort()
        return cls.__infractions

    @classmethod
    def get_by_name(cls, name: str):
        infracoes_com_nome = [i for i in cls.all_default_infractions() if i.filename == name]
        if len(infracoes_com_nome) != 1:
            raise ConfigFileDecoderException(f'Não foi encontrada infração com nome {name}')
        return copy.copy(infracoes_com_nome[0])

    def __init__(self, json_file: Path):
        self.filtro_coluna = None
        self.filtro_tipo = None
        self.capitulation: InfractionCapitulation = None
        self.filename = json_file.stem
        self._analysis = None
        self.planilha_titulo = None
        self.inciso = re.search(r'^[A-Z]+', self.filename).group()
        self.alinea = re.search(r'[a-z]+[1-9]*', self.filename).group()
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
            self.nome = dados.get('nome')
            self.report = dados['relato']
            self.ttpa = dados['ttpa']
            self.order = dados.get('ordem')
            self.operation_type = dados.get('operacao')
            if self.operation_type and self.operation_type not in ('Tributada', 'Não Tributada', 'Isenta'):
                raise ConfigFileDecoderException(f'Arquivo de infração {json_file} tem um '
                                                 f'tipo de operação inválido: {self.operation_type}')
            self.ddf_type = dados.get('tipo')
            if self.ddf_type and self.ddf_type not in ('Falta de solicitação', 'Solicitação após transcurso de prazo'):
                raise ConfigFileDecoderException(f'Arquivo de infração {json_file} tem um '
                                                 f'tipo de DDF inválido: {self.ddf_type}')
            if dados.get('capitulacao'):
                self.capitulation = InfractionCapitulation(self.filename, dados['capitulacao'])
            if dados.get('relatorio_circunstanciado'):
                self.relatorio_circunstanciado = dados['relatorio_circunstanciado']
            self.provas = [AiimProof(dic) for dic in dados.get('provas', [])]
        except KeyError as e:
            raise ConfigFileDecoderException(f'Arquivo de infração {json_file} não tem '
                                             f'um parâmetro obrigatório: {e.args}')

    def update(self, dicionario: dict):
        if dicionario.get('nome'):
            self.nome = dicionario['nome']
        if dicionario.get('relato'):
            self.report = dicionario['relato']
        if dicionario.get('ordem'):
            self.order = dicionario['ordem']
        if dicionario.get('tipo'):
            self.ddf_type = dicionario['tipo']
        if dicionario.get('ttpa'):
            self.ttpa = dicionario['ttpa']
        if dicionario.get('capitulacao'):
            self.capitulation = InfractionCapitulation(self, dicionario['capitulacao'])
        if dicionario.get('relatorio_circunstanciado'):
            self.relatorio_circunstanciado = dicionario['relatorio_circunstanciado']
        if dicionario.get('provas'):
            self.provas = [AiimProof(dic) for dic in dicionario.get('provas', [])]
        if dicionario.get('filtro_coluna'):
            self.filtro_coluna = dicionario['filtro_coluna']
            self.filtro_tipo = dicionario['filtro']
            if self.filtro_tipo not in ['positivo', 'negativo']:
                raise ConfigFileDecoderException(f'Opção inválida para filtro: {self.filtro_tipo}')
            if dicionario.get('planilha_titulo'):
                self.planilha_titulo = dicionario['planilha_titulo']

    @property
    def analysis(self) -> Analysis:
        return self._analysis

    @analysis.setter
    def analysis(self, a: Analysis):
        self._analysis = a
        self.planilha_titulo = a.name if a else None

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
        return self.__str__()

    def __str__(self):
        return f'{self.inciso},"{self.alinea}"' if not self.nome else f'{self.inciso},"{self.alinea}" - {self.nome}'

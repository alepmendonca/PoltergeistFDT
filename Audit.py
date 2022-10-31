import sys
from datetime import datetime, date
import json
import os
import re
from pathlib import Path

import pandas as pd

import GeneralConfiguration
import GeneralFunctions
from ConfigFiles import Analysis, Infraction, ConfigFileDecoderException, AiimProof
from ExcelDDFs import ExcelDDFs, ExcelArrazoadoAbaInexistenteException
from WordReport import WordReport


class PossibleInfraction:
    def __init__(self, analysis: Analysis, planilha: str, df: pd.DataFrame | list[list], planilha_detalhe: str):
        self.verificacao: Analysis = analysis
        self.planilha = planilha
        self.planilha_detalhe = planilha_detalhe
        if isinstance(df, pd.DataFrame) or df is None:
            self.df = df
        else:
            self.df = self.__df_as_panda(df)
        self._notificacao_titulo = ''
        self._notificacao_corpo = ''

    def toJson(self) -> dict:
        dic = self.__dict__.copy()
        dic['verificacao'] = self.verificacao.name
        dic['df'] = GeneralFunctions.get_list_from_df(self.df) if self.df is not None else None
        for k in [k for k in dic.keys() if dic[k] is None or k.startswith('_')]:
            dic.pop(k)
        return dic

    def __lt__(self, other):
        return self.verificacao < other.verificacao

    def __str__(self):
        return str(self.verificacao)

    def _personalize_text(self, text: str) -> str:
        if text is None:
            return None
        nome_aba = self.planilha
        relato = text
        try:
            planilha = get_current_audit().get_sheet()
            relato = relato.replace('<osf>', get_current_audit().osf)
            relato = relato.replace('<email>', GeneralConfiguration.get().email)
            if relato.find('<periodo>') > 0:
                # levanta os períodos indicados em "referencia"
                referencias = planilha.periodos_de_referencia(nome_aba) \
                    if nome_aba else GeneralFunctions.get_dates_from_df(self.df)
                texto = GeneralFunctions.periodos_prettyprint(referencias)
                relato = relato.replace('<periodo>', texto)
            if relato.find('<periodoAAAA>') > 0:
                # levanta os períodos em anos indicados em "referencia"
                referencias = planilha.periodos_de_referencia(nome_aba, freq='Y') \
                    if nome_aba else GeneralFunctions.get_dates_from_df(self.df, freq='Y')
                texto = GeneralFunctions.periodos_prettyprint(referencias, freq='Y')
                relato = relato.replace('<periodoAAAA>', texto)
            if relato.find('<modelos>') > 0:
                # levanta os modelos de documentos fiscais existentes na planilha
                modelos = planilha.modelos_documento_fiscal(nome_aba)
                if modelos is not None:
                    texto = 'modelos ' if len(modelos) > 1 else 'modelo '
                    for i in range(len(modelos)):
                        if i + 1 == len(modelos) and i > 0:
                            texto = texto[:-2] + ' e '
                        texto += str(int(modelos[i])) + ', '
                    texto = texto[:-2]
                else:
                    texto = ''
                relato = relato.replace('<modelos>', texto)
        except ExcelArrazoadoAbaInexistenteException:
            raise
        except Exception as e:
            GeneralFunctions.logger.exception('Falha na criação de relato para item de AIIM')
            raise e
        return relato

    def notificacao_titulo(self, texto: str = '') -> str:
        if not self._notificacao_titulo:
            self._notificacao_titulo = self._personalize_text(texto)
        return self._notificacao_titulo

    def notificacao_corpo(self, texto: str = '') -> str:
        if not self._notificacao_corpo:
            self._notificacao_corpo = self._personalize_text(texto)
        return self._notificacao_corpo

    def clear_cache(self):
        self._notificacao_titulo = ''
        self._notificacao_corpo = ''

    def __df_as_panda(self, df: list[list]) -> pd.DataFrame:
        if len(df) > 0 and len(df[0]) != len(self.verificacao.ddf_headers):
            raise ValueError(f'Dataframe da função {self.verificacao.function.__name__} '
                             f'da verificação {self.verificacao.name} '
                             f'tem {len(df[0])} colunas, mas a configuração da verificação '
                             f'tem os seguintes cabeçalhos: {self.verificacao.ddf_headers}')
        return GeneralFunctions.get_df_from_list(df, self.verificacao.ddf_headers)


class AiimItem(PossibleInfraction):

    def __init__(self, infraction_name: str, analysis: Analysis, item: int, notificacao: str,
                 notificacao_resposta: str, planilha: str, df: pd.DataFrame | list[list],
                 planilha_detalhe: str):
        super().__init__(analysis, planilha, df, planilha_detalhe)
        self._proofs_dfs_list = None
        self.infracao: Infraction
        infracao = list(filter(lambda i: i.filename == infraction_name, self.verificacao.infractions))
        if not len(infracao):
            raise ConfigFileDecoderException(f'Não existe infração {infraction_name} vinculada '
                                             f'à verificação {analysis.name}. '
                                             f'Altere manualmente o arquivo de configurações da auditoria.')
        self.infracao = infracao[0]
        self._notificacao = None
        self._notificacao_resposta = None
        self.item: int = 0
        self._relato = ''
        self._relatorio_circunstanciado = ''
        if item is not None:
            self.item = item
        if notificacao is not None:
            self.notificacao = notificacao
            if notificacao_resposta is not None:
                self.notificacao_resposta = notificacao_resposta

    @property
    def notificacao(self) -> str:
        return self._notificacao

    @notificacao.setter
    def notificacao(self, notificacao: str):
        if re.match(r'IC/N/FIS/\d+/\d{4}$', notificacao):
            numero_quebrado = notificacao.split('/')
            numero_quebrado[3] = numero_quebrado[3].zfill(9)
            self._notificacao = '/'.join(numero_quebrado)
        elif re.match(r'\d+/\d{4}\s+\d{2}\.\d\.\d{5}/\d{2}-\d$', notificacao):
            self._notificacao = notificacao
        else:
            raise ValueError(f'Número de notificação inválido: {notificacao}')

    @property
    def notificacao_resposta(self) -> str:
        return self._notificacao_resposta

    @notificacao_resposta.setter
    def notificacao_resposta(self, resposta: str):
        if re.match(r'SFP-EXP-\d{4}/\d+', resposta):
            self._notificacao_resposta = resposta
        else:
            raise ValueError(f'Número do expediente Sem Papel em resposta à notificação inválido: {resposta}')

    def has_aiim_item_number(self) -> bool:
        return self.item > 0

    def get_dfs_list_for_proof_generation(self) -> pd.DataFrame:
        if self._proofs_dfs_list is None:
            if self.infracao.provas:
                self._proofs_dfs_list = self.infracao.provas[0].sample_generation_function(self)
            else:
                self._proofs_dfs_list = pd.DataFrame()
        return self._proofs_dfs_list.copy()

    def toJson(self) -> dict:
        dic = super().toJson()
        dic['infracao'] = self.infracao.filename
        if dic['item'] <= 0 or dic['item'] is None:
            dic.pop('item')
        if self.notificacao:
            dic['notificacao'] = self.notificacao
        if self.notificacao_resposta:
            dic['notificacao_resposta'] = self.notificacao_resposta
        for k in [k for k in dic.keys() if k.startswith('_') or dic[k] is None]:
            dic.pop(k)
        return dic

    def __lt__(self, other):
        return (self.has_aiim_item_number() and
                (not other.has_aiim_item_number() or self.item < other.item)) \
               or self.infracao < other.infracao

    def __str__(self):
        return f'{self.infracao}' if not self.has_aiim_item_number() else f'{self.item} - {self.infracao}'

    def is_manual_notification(self) -> bool:
        if not self.notificacao:
            raise ValueError('Verificando se a notificação é manual, mas nem tem notificação!')
        return not self.notificacao.startswith('IC/N/FIS')

    def notification_path(self) -> Path:
        if not self.notificacao:
            return None
        folder_name = f'{self.notification_numeric_part().replace("_", "-")}'
        if self.is_manual_notification():
            folder_name += ' - MANUAL'
        # remove caracteres inválidos no Windows para nomes de arquivos
        folder_name += re.sub(r'[<>:"/\\|!?*]', '', f' - {self.verificacao.name}')
        return get_current_audit().notification_path() / folder_name

    def notification_response_path(self) -> Path:
        return self.notification_path() / 'Resposta' if self.notification_path() else None

    def notification_numeric_part(self) -> str:
        if self.is_manual_notification():
            parts = self.notificacao.split("/")
            return f'{parts[1].split()[0]}_{int(parts[0])}'
        else:
            partial_name = re.search(r"\d+", self.notificacao)[0]
            return f'{self.notificacao[-4:]}_{int(partial_name)}'

    def proofs_for_report(self) -> list[str]:
        proofs = [f'{prova.descricao}{", por amostragem" if prova.has_sample(self) else ""}'
                  for prova in self.infracao.provas]
        if self.notificacao:
            texto = f'Notificação {"Modelo 4" if self.is_manual_notification() else "DEC"} {self.notificacao}'
            if self.notificacao_resposta:
                texto += f' e resposta do contribuinte, apresentada sob expediente Sem Papel {self.notificacao_resposta}'
            else:
                if GeneralFunctions.is_empty_directory(self.notification_response_path()):
                    texto += ', sem resposta do contribuinte'
                else:
                    texto += ' e resposta do contribuinte, enviada diretamente à Fiscalização'
            proofs.append(f'{texto}')
        return proofs

    def generate_notification_proof(self, ws) -> list[Path]:
        return AiimProof.generate_notification_proof(self, ws)

    def relato(self) -> str:
        if not self._relato:
            self._relato = self._personalize_text(self.infracao.report)
        return self._relato

    def relatorio_circunstanciado(self) -> str:
        if not self._relatorio_circunstanciado:
            resposta = self._personalize_text(self.infracao.relatorio_circunstanciado)
            if self.notificacao:
                resposta += '\nO contribuinte foi notificado por meio da notificação '
                resposta += ' Modelo 4 ' if self.is_manual_notification() else ' DEC '
                if self.notificacao_resposta:
                    resposta += f'{self.notificacao}, com resposta dada no expediente {self.notificacao_resposta}' \
                                f', mas sem justificativas legais para todos os pontos questionados.'
                else:
                    resposta += self.notificacao
                    if GeneralFunctions.is_empty_directory(self.notification_response_path()):
                        resposta += ', sem apresentar resposta à fiscalização.'
                    else:
                        resposta += f', mas sem justificativas legais para todos os pontos questionados.'
            self._relatorio_circunstanciado = resposta
        return self._relatorio_circunstanciado

    def clear_cache(self):
        super().clear_cache()
        self._relato = ''
        self._relatorio_circunstanciado = ''


class Audit:

    @classmethod
    def has_local_dados_osf(cls, path_name: Path):
        json_file = GeneralFunctions.get_audit_json_path(path_name)
        json_file.parent.mkdir(exist_ok=True)
        return json_file.is_file()

    def __init__(self, path: Path):
        self._path_name = path
        self._dicionario: dict
        self._excel = None
        self._word = None
        self._empresa: str
        self.aiim_itens: list[AiimItem] = []
        Analysis.clear_audit_analysis()
        Analysis.load_audit_analysis(path)
        try:
            with GeneralFunctions.get_audit_json_path(path).open(mode='r') as outfile:
                self._dicionario = json.load(outfile)
        except FileNotFoundError:
            self._dicionario = {}

        self.aiim_number = None if not self._dicionario.get('aiim', None) \
            else self._dicionario['aiim'].get('numero', '')
        self.is_aiim_open = False if not self._dicionario.get('aiim', None) \
            else self._dicionario['aiim'].get('aberto', False)
        self.empresa = self._dicionario.get('empresa', None)
        self.logradouro = self._dicionario.get('logradouro', None)
        self.numero = self._dicionario.get('numero', None)
        self.complemento = self._dicionario.get('complemento', '')
        self.bairro = self._dicionario.get('bairro', None)
        self.cidade = self._dicionario.get('cidade', None)
        self.uf = self._dicionario.get('uf', 'SP')
        self.cep = self._dicionario.get('cep', None)
        self.cnpj = self._dicionario.get('cnpj', None)
        self.ie = self._dicionario.get('ie', None)
        self.osf = self._dicionario.get('osf', None)
        self.cnae = self._dicionario.get('cnae', None)
        self.situacao = self._dicionario.get('situacao', 'Ativo')
        self.has_sat_equipment = self._dicionario.get('has_sat_equipment', None)
        self.receipt_digital_files = self._dicionario.get('receipt_digital_files', None)
        self._inicio_auditoria = self._dicionario.get('inicio_auditoria', None)
        self._fim_auditoria = self._dicionario.get('fim_auditoria', None)
        self._inicio_situacao = self._dicionario.get('inicio_situacao', None)
        self._inicio_inscricao = self._dicionario.get('inicio_inscricao', None)

        self.historico_regime = self._dicionario.get('historico_regime', [])
        self.reports = self._dicionario.get('reports', {})
        self.notificacoes = []
        if self._dicionario.get('notificacoes', None):
            self.notificacoes = []
            for x in self._dicionario['notificacoes']:
                analysis = Analysis.get_analysis_by_name(self._path_name, x['verificacao'])
                if not analysis:
                    raise ConfigFileDecoderException(f'Não existe verificação chamada {x["verificacao"]}. '
                                                     f'Altere manualmente o arquivo de configurações da auditoria.')
                self.notificacoes.append(PossibleInfraction(analysis, x.get('planilha', None), x.get('df', None),
                                                            x.get('planilha_detalhe', None)))
        self.aiim_itens = []
        if self._dicionario.get('infracoes', None):
            self.aiim_itens = []
            for x in self._dicionario['infracoes']:
                analysis = Analysis.get_analysis_by_name(self._path_name, x['verificacao'])
                if not analysis:
                    raise ConfigFileDecoderException(f'Não existe verificação chamada {x["verificacao"]}. '
                                                     f'Altere manualmente o arquivo de configurações da auditoria.')
                self.aiim_itens.append(AiimItem(x['infracao'], analysis, x.get('item', None),
                                                x.get('notificacao', None), x.get('notificacao_resposta', None),
                                                x.get('planilha', None), x.get('df', None),
                                                x.get('planilha_detalhe', None)))

    def aiim_number_no_digit(self) -> int:
        return int(re.sub(r'[^\d]', '', self.aiim_number)[:-1])

    def path(self):
        return self._path_name

    @property
    def empresa(self) -> str:
        return self._empresa

    @empresa.setter
    def empresa(self, nome):
        self._empresa = nome
        if nome:
            self.schema = self._dicionario.get('schema',
                                               GeneralFunctions.get_default_name_for_business(nome)).lower()

    @property
    def inicio_auditoria(self) -> date:
        return datetime.strptime(self._inicio_auditoria, "%m/%Y").date() if self._inicio_auditoria else None

    @inicio_auditoria.setter
    def inicio_auditoria(self, inicio: str | date | datetime):
        inicio_date = None
        if isinstance(inicio, str):
            if not re.match(r'\d{2}/\d{4}', inicio) \
                    or not (1 <= int(inicio[:2]) <= 12) or int(inicio[3:]) <= 2000:
                raise ValueError(f'Início de auditoria em formato errado (mm/aaaa): {inicio}')
            else:
                inicio_date = datetime.strptime(inicio, "%m/%Y").date()

        if isinstance(inicio, date) or isinstance(inicio, datetime):
            inicio_date = inicio
            inicio = inicio_date.strftime('%m/%Y')

        if self.fim_auditoria is not None and inicio_date is not None and inicio_date > self.fim_auditoria:
            raise ValueError(f'Início de auditoria {inicio_date} deve ser menor que o final {self.fim_auditoria}')

        self._inicio_auditoria = inicio

    @property
    def fim_auditoria(self) -> date:
        return GeneralFunctions.last_day_of_month(
            datetime.strptime(self._fim_auditoria, "%m/%Y").date()) if self._fim_auditoria else None

    @fim_auditoria.setter
    def fim_auditoria(self, fim: str | date | datetime):
        fim_date = None
        if isinstance(fim, str):
            if not re.match(r'\d{2}/\d{4}', fim) \
                    or not (1 <= int(fim[:2]) <= 12) or int(fim[3:]) <= 2000:
                raise ValueError(f'Fim de auditoria em formato errado (mm/aaaa): {fim}')
            else:
                fim_date = datetime.strptime(fim, "%m/%Y").date()
        if isinstance(fim, date) or isinstance(fim, datetime):
            fim_date = fim
            fim = fim_date.strftime('%m/%Y')

        if self.inicio_auditoria is not None and fim_date is not None and self.inicio_auditoria > fim_date:
            raise ValueError(f'Início de auditoria {self.inicio_auditoria} deve ser maior que o final {fim_date}')
        self._fim_auditoria = fim

    @property
    def inicio_inscricao(self) -> date:
        return datetime.strptime(self._inicio_inscricao, "%d/%m/%Y").date() if self._inicio_inscricao else None

    @inicio_inscricao.setter
    def inicio_inscricao(self, d):
        if isinstance(d, date):
            self._inicio_inscricao = d.strftime('%d/%m/%Y') if d else None
        elif isinstance(d, str):
            if not re.match(r'\d{2}/\d{2}/\d{4}', d):
                raise ValueError(f'Início da inscrição em formato errado (dd/mm/aaaa): {d}')
            self._inicio_inscricao = d

    @property
    def inicio_situacao(self) -> date:
        return datetime.strptime(self._inicio_situacao, "%d/%m/%Y").date() if self._inicio_situacao else None

    @inicio_situacao.setter
    def inicio_situacao(self, d):
        if isinstance(d, date):
            self._inicio_situacao = d.strftime('%d/%m/%Y') if d else None
        elif isinstance(d, str):
            if not re.match(r'\d{2}/\d{2}/\d{4}', d):
                raise ValueError(f'Início da situação em formato errado (dd/mm/aaaa): {d}')
            self._inicio_situacao = d

    def cnpj_only_digits(self) -> str:
        return re.sub(r'[^\d]', '', self.cnpj)

    def ie_only_digits(self) -> str:
        return re.sub(r'[^\d]', '', self.ie)

    def osf_only_digits(self) -> str:
        return re.sub(r'[^\d]', '', self.osf).zfill(11)

    def endereco_completo(self) -> str:
        endereco = f'{self.logradouro}, {self.numero}'
        if self.complemento:
            endereco += f' - {self.complemento}'
        return endereco + f' - {self.bairro} - {self.cidade}/{self.uf} - CEP {self.cep}'

    def is_contribuinte_ativo(self) -> bool:
        return self.situacao == 'Ativo'

    def __eq__(self, other):
        return self._path_name == other._path_name

    def get_dados_osf(self) -> dict:
        return self._dicionario

    def toJson(self):
        dic = self.__dict__.copy()
        dic['empresa'] = dic['_empresa']
        dic['inicio_auditoria'] = dic['_inicio_auditoria']
        dic['fim_auditoria'] = dic['_fim_auditoria']
        dic['inicio_situacao'] = dic['_inicio_situacao']
        dic['inicio_inscricao'] = dic['_inicio_inscricao']
        if dic['aiim_number'] is not None:
            dic['aiim'] = {'numero': dic['aiim_number'], 'aberto': dic['is_aiim_open']}
        dic.pop('aiim_number', None)
        dic.pop('is_aiim_open', None)
        if dic.get('notificacoes', None):
            dic['notificacoes'] = [x.toJson() for x in self.notificacoes]
        if dic.get('aiim_itens', None):
            dic['infracoes'] = [x.toJson() for x in self.aiim_itens]
            dic.pop('aiim_itens')
        for k in [k for k in dic.keys()
                  if k.startswith('_') or dic[k] is None or (isinstance(dic[k], list) and len(dic[k]) == 0) or (
                    isinstance(dic[k], dict) and len(dic[k]) == 0)]:
            dic.pop(k)
        return dic

    def get_sheet(self) -> ExcelDDFs:
        if not self._excel:
            self._excel = ExcelDDFs()
        return self._excel

    def get_report(self):
        if not self._word:
            self._word = WordReport(audit=self)
        return self._word

    def update_report(self):
        self.clear_cache()
        for item in self.aiim_itens:
            self.get_report().remove_item(item.item)
            self.get_report().remove_anexo(item.item)
            if item.infracao.relatorio_circunstanciado:
                provas = item.proofs_for_report()
                self.get_report().insere_item(item.item, item.infracao.inciso_number(),
                                              item.relatorio_circunstanciado(),
                                              bool(provas))
                if provas:
                    self.get_report().insere_anexo(item.item, provas)
        self.get_report().save_report()

    def update_general_proofs(self):
        funcao = getattr(sys.modules['AiimProofGenerator'], 'generate_general_proofs_file')
        provas_gerais = funcao()
        self.get_report().atualiza_provas_gerais(provas_gerais)
        self.get_report().save_report()

    def clear_cache(self):
        self.get_sheet().clear_cache()
        for notif in self.notificacoes:
            notif.clear_cache()
        for item in self.aiim_itens:
            item.clear_cache()

    def save(self):
        os.makedirs(str(self._path_name / 'Dados'), exist_ok=True)
        with GeneralFunctions.get_audit_json_path(self._path_name).open(mode='w') as outfile:
            json.dump(self.toJson(), outfile, sort_keys=True, indent=3)

    def get_periodos_da_fiscalizacao(self, rpa=True, ate_presente=False) -> list[[date, date]]:
        retorno = []
        nome_regime = 'NORMAL' if rpa else 'SIMPLES NACIONAL'
        for periodo in self.historico_regime:
            if periodo[2].startswith(nome_regime):
                inicio = datetime.strptime(periodo[0], '%d/%m/%Y').date()
                if periodo[1] == 'Atual':
                    fim = date.today()
                else:
                    fim = datetime.strptime(periodo[1], '%d/%m/%Y').date()
                if inicio <= self.inicio_auditoria <= fim or inicio <= self.fim_auditoria <= fim \
                        or self.inicio_auditoria <= inicio <= self.fim_auditoria:
                    if ate_presente:
                        retorno.append([max(self.inicio_auditoria, inicio), fim])
                    else:
                        retorno.append([max(self.inicio_auditoria, inicio), min(self.fim_auditoria, fim)])
        return retorno

    def periodos_da_fiscalizacao_descricao(self):
        periodos = [[p[0], p[1], 'rpa'] for p in self.get_periodos_da_fiscalizacao(ate_presente=True)]
        periodos.extend([[p[0], p[1], 'sn'] for p in self.get_periodos_da_fiscalizacao(rpa=False, ate_presente=True)])
        periodos.sort(key=lambda p: p[0])
        descricao = 'O'
        for p in periodos:
            descricao += ' Posteriormente, o' if p != periodos[0] else ''
            descricao += ' contribuinte foi enquadrado no '
            descricao += 'Regime Simples Nacional' if p[2] == 'sn' else 'Regime Periódico de Apuração'
            if p == periodos[-1]:
                descricao += f' desde {p[0].strftime("%d/%m/%Y")}, permanecendo nele até o presente.'
            else:
                descricao += f' desde {p[0].strftime("%d/%m/%Y")} até {p[1].strftime("%d/%m/%Y")}.'
        return descricao

    def get_digital_files_hashes(self) -> list[dict]:
        # aqui se gera o conteúdo do recibo de entrega de arquivos digitais
        # listagem contém todos os arquivos nas pastas "Respostas", independentemente de serem notificações
        # em que haja uma infração ativa na auditoria
        # não são colocadas nas listagem eventuais arquivos do Sigadoc, ou arquivos que começam com "e-mail" ou "email"
        notifications = {}
        for (path_str, _, verificacoes) in os.walk(self.notification_path()):
            path = Path(path_str)
            is_notification = re.match(r'(\d{4})-(\d+) - ', path.parent.name)
            if path.name == 'Resposta' and is_notification:
                if '- MANUAL -' in path.parent.name:
                    notification_name = f'Notificação Modelo 4 {is_notification.group(2)}/{is_notification.group(1)}'
                else:
                    notification_name = f'Notificação DEC IC/N/FIS/{is_notification.group(2)}/{is_notification.group(1)}'
                if notifications.get(notification_name):
                    notifications[notification_name]['files'].extend(
                        [path / f for f in verificacoes if not f.startswith('SFPEXP')
                         and not f.upper().startswith('EMAIL') and not f.upper().startswith('E-MAIL')])
                else:
                    notifications[notification_name] = {'year': int(is_notification.group(1)),
                                                        'number': int(is_notification.group(2)),
                                                        'files': [path / f for f in verificacoes
                                                                  if not f.startswith('SFPEXP')
                                                                  and not f.upper().startswith('EMAIL')
                                                                  and not f.upper().startswith('E-MAIL')]
                                                        }
        notifications = {k: v for k, v in sorted(notifications.items(),
                                                 key=lambda tupla: (tupla[1]['year'], tupla[1]['number']))}
        response = []
        for notification, value in notifications.items():
            if value['files']:
                item = {'notification': notification,
                        'files': [{'file': file.name, 'size': GeneralFunctions.get_file_size_pretty_print(file),
                                   'md5': GeneralFunctions.get_md5(file), 'sha256': GeneralFunctions.get_sha256(file)
                                   } for file in sorted(value['files'])
                                  ]
                        }
                response.append(item)
        return response

    def next_manual_notification(self) -> str:
        numeros_deste_ano = [int(item.notification_numeric_part().split('_')[1]) for item in self.aiim_itens
                             if item.notificacao is not None and item.is_manual_notification()
                             and item.notification_numeric_part().startswith(str(date.today().year))]
        numeros_deste_ano.sort(reverse=True)
        proximo_numero = numeros_deste_ano[0] + 1 if numeros_deste_ano else 1
        return f'{str(proximo_numero).zfill(2)}/{date.today().year} {self.osf}'

    def notification_path(self):
        return self.path() / 'Notificações'

    def reports_path(self):
        return self.path() / 'Dados'

    def aiim_path(self):
        return self.path() / 'AIIM'

    def findings_path(self):
        return self.path() / 'Achados'


_singleton: Audit = None


def get_current_audit() -> Audit:
    return _singleton


def set_audit(path: Path = None):
    global _singleton
    if path and path.is_dir() and Audit.has_local_dados_osf(path):
        _singleton = Audit(path)
    else:
        _singleton = None


def create_new_audit(path: Path) -> Audit:
    global _singleton
    if Audit.has_local_dados_osf(path):
        set_audit(path)
    else:
        _singleton = Audit(path)
    return _singleton

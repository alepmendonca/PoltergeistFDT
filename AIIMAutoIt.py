import datetime
import glob
import os.path
import re
import time
import autoit
from pathlib import Path

import win32api
import win32con

import GeneralFunctions

from autoit import AutoItError
from Audit import Audit, AiimItem
from GeneralFunctions import logger
from MDBReader import AIIM2003MDBReader


def dismiss_browser_alert(parte_titulo: str):
    navegador = f"[CLASS:Chrome_WidgetWin_1; REGEXPTITLE:(?i)(.*{parte_titulo}.*)]"
    autoit.win_wait(navegador, 5)
    autoit.win_activate(navegador)
    autoit.send("{ESC}")


class AIIMAutoIt:
    def __init__(self):
        self.titulo_janela = "[CLASS:ThunderRT6MDIForm; TITLE:Auto de Infração e Imposição de Multa - AIIM 2003]"
        self.exec_path = sorted(glob.glob('C:/Program Files (x86)/AIIM*ICMS/AIIM2003.exe'), reverse=True)[0]
        docs_path = Path.home() / 'Documents'
        # serve para pegar a última versão instalada do AIIM 2003 ICMS
        mdb_path = sorted(docs_path.glob('*ICMS/Aiim.mdb'), reverse=True)[0].parent
        self.reports_path = mdb_path / 'Documentos'
        try:
            logger.info('Tentando acessar janela do AIIM2003')
            autoit.win_wait(self.titulo_janela, 2)
        except AutoItError:
            try:
                logger.info(f'Abrindo AIIM2003 encontrado em {self.exec_path}')
                autoit.run(self.exec_path, work_dir=os.path.dirname(self.exec_path),
                           show_flag=autoit.properties.SW_RESTORE)
                autoit.win_wait(self.titulo_janela, 5)
            except AutoItError:
                raise Exception('Falha na abertura do AIIM2003')
        time.sleep(1)
        autoit.win_set_state(self.titulo_janela, flag=autoit.properties.SW_RESTORE)

    def __focus_and_set_text(self, handle: str, nome_handle: str, texto: str, janela=None):
        window = janela if janela is not None else self.titulo_janela
        autoit.win_activate(window)

        try:
            autoit.control_focus(window, handle)
        except AutoItError:
            raise Exception(f'Não conseguiu achar caixa de texto de {nome_handle} no AIIM2003. '
                            f'Será que você não andou mexendo no computador?')
        if autoit.control_get_text(window, handle) != texto:
            autoit.control_set_text(window, handle, texto)

    def __focus_and_send(self, handle: str, nome_handle: str, texto: str, janela=None, combo=False):
        window = janela if janela is not None else self.titulo_janela
        autoit.win_activate(window)
        try:
            autoit.control_focus(window, handle)
        except AutoItError:
            raise Exception(f'Não conseguiu achar caixa de texto de {nome_handle} no AIIM2003. '
                            f'Será que você não andou mexendo no computador?')
        if combo and len(texto) > 1:
            position = autoit.control_command(window, handle, 'FindString', extra=texto)
            autoit.control_command(window, handle, 'SetCurrentSelection', extra=position)
        else:
            autoit.control_send(window, handle, texto)

    def __save_and_exit(self):
        autoit.win_activate(self.titulo_janela)
        try:
            self.__click_and_wait('[CLASS:ThunderRT6CommandButton; INSTANCE:1]', wait=False)
            logger.info('Salvando AIIM e saindo')
        except AutoItError:
            return
        self.__wait_dialog_and_click("[CLASS:#32770; TITLE:AIIM2003]", "[CLASS:Button; INSTANCE:1]")

    def __open_menu(self, menu, aiim_position=None):
        if menu not in (
                'UFESP', 'NOVO_AIIM', 'ABRE_AIIM', 'RELATORIOS', 'IMPORTAR', 'EXPORTAR', 'TRANSMITIR', 'EXCLUIR'):
            raise AutoItError('Tentou abrir menu não configurado no sistema!')
        self.__save_and_exit()

        logger.info(f'Abrindo menu {menu} no AIIM2003')
        autoit.win_activate(self.titulo_janela)
        if menu == 'UFESP':
            autoit.send('!c{DOWN 3}{ENTER}')
        elif menu == 'NOVO_AIIM':
            autoit.send('!c{RIGHT}{ENTER}')
        elif menu == 'ABRE_AIIM':
            autoit.send('!c{RIGHT}{DOWN}{ENTER}')
        elif menu == 'RELATORIOS':
            autoit.send('!c{RIGHT}{DOWN 3}{ENTER}')
        elif menu == 'EXCLUIR':
            autoit.send('!c{RIGHT}{DOWN 5}{ENTER}')
        elif menu == 'IMPORTAR':
            autoit.send('!c{RIGHT}{DOWN 6}{ENTER}')
        elif menu == 'EXPORTAR':
            autoit.send('!c{RIGHT}{DOWN 7}{ENTER}')
        elif menu == 'TRANSMITIR':
            autoit.send('!c{RIGHT}{DOWN 8}{ENTER}')
            return

        if menu != 'IMPORTAR':
            # move o controle pra ficar visível. pode rolar uma demora pra abrir, então retenta
            try:
                autoit.control_move(self.titulo_janela, '[CLASS:ThunderRT6FormDC; INSTANCE:1]', x=10, y=10)
            except AutoItError:
                time.sleep(2)
                autoit.control_move(self.titulo_janela, '[CLASS:ThunderRT6FormDC; INSTANCE:1]', x=10, y=10)

        # precisa selecionar o AIIM
        if menu in ('ABRE_AIIM', 'RELATORIOS', 'EXPORTAR', 'EXCLUIR'):
            if aiim_position >= 1:
                self.__wait_dialog_and_select_item(self.titulo_janela, '[CLASS:ListView20WndClass; INSTANCE:1]',
                                                   'Autos cadastrados', aiim_position)
            self.__click_and_wait('[CLASS:ThunderRT6CommandButton; INSTANCE:2]')
            if menu == 'RELATORIOS':
                # verifica se não deu erro por AIIM estar sem valores em DDF
                popup = '[CLASS:#32770; TITLE:AIIM2003]'
                try:
                    autoit.win_wait(popup, 2)
                except AutoItError:
                    pass
                else:
                    mensagem = autoit.control_get_text(popup, '[CLASS:Static; INSTANCE:2]')
                    self.__wait_dialog_and_click(popup, '[CLASS:Button; INSTANCE:1]')
                    raise Exception(f'Erro na geração de relatórios do AIIM: {mensagem}')
            # move o controle pra ficar visível
        if menu in ('ABRE_AIIM', 'RELATORIOS'):
            autoit.control_move(self.titulo_janela, '[CLASS:ThunderRT6FormDC; INSTANCE:1]', x=10, y=10)

    def __click_and_wait(self, handle, wait=True, janela=None, **kwargs):
        window = janela if janela is not None else self.titulo_janela
        autoit.win_activate(window)
        x_dado = kwargs.get("x")
        y_dado = kwargs.get("y")
        if x_dado:
            autoit.control_click(window, handle, x=x_dado, y=y_dado)
        else:
            autoit.control_click(window, handle)
        if wait:
            time.sleep(0.5)

    def __check_and_wait(self, handle, is_checked: bool, wait=True):
        autoit.win_activate(self.titulo_janela)
        autoit.control_command(self.titulo_janela, handle, 'Check' if is_checked else 'Uncheck')
        if wait:
            time.sleep(0.5)

    def __is_control_enabled(self, handle):
        return autoit.control_command(self.titulo_janela, handle, 'isEnabled') == '1'

    def __wait_dialog_and_set_text(self, dialogo, handle, nome_handle, texto):
        autoit.win_wait(dialogo, 5)
        autoit.win_active(dialogo)
        self.__focus_and_set_text(handle, nome_handle, texto, janela=dialogo)

    # Atributo opcao deve ser um inteiro, indicando o número do item na lista, iniciando por 1
    def __wait_dialog_and_select_item(self, dialogo, handle, nome_handle, opcao: int, wait=True):
        if wait:
            autoit.win_wait(dialogo, 5)
        autoit.win_activate(dialogo)
        try:
            autoit.control_focus(dialogo, handle)
        except AutoItError:
            raise Exception(f'Não conseguiu achar lista de {nome_handle} no AIIM2003. '
                            f'Será que você não andou mexendo no computador?')
        autoit.control_send(dialogo, handle, '{HOME}')
        for i in range(1, opcao):
            autoit.control_send(dialogo, handle, '{DOWN}')
        time.sleep(int(0.5 * opcao))

    def __wait_dialog_and_click(self, dialogo, button, wait=True):
        if wait:
            autoit.win_wait(dialogo, 5)
        autoit.win_activate(dialogo)
        autoit.control_click(dialogo, button)

    def get_reports_path(self):
        return self.reports_path

    def preenche_ddf_com_dij(self, tributo, dci, dij, davb):
        self.__focus_and_set_text("[CLASS:ThunderRT6TextBox; INSTANCE:13]", 'tributo', tributo)
        self.__focus_and_set_text("[CLASS:MSMaskWndClass; INSTANCE:2]", 'DCI', dci)
        self.__focus_and_set_text("[CLASS:MSMaskWndClass; INSTANCE:3]", 'DIJ', dij)
        autoit.send('{TAB}')
        self.__wait_dialog_and_click("[CLASS:#32770; TITLE:AIIM2003]", "[CLASS:Button; INSTANCE:1]")
        self.__focus_and_set_text("[CLASS:MSMaskWndClass; INSTANCE:4]", 'DAVB', davb)
        self.__click_and_wait("[CLASS:ThunderRT6CommandButton; INSTANCE:11]")

    def preenche_ddf_dci_davb(self, tributo, dci, davb):
        self.__focus_and_set_text("[CLASS:ThunderRT6TextBox; INSTANCE:13]", 'tributo', tributo)
        self.__focus_and_set_text("[CLASS:MSMaskWndClass; INSTANCE:2]", 'DCI', dci)
        self.__focus_and_set_text("[CLASS:MSMaskWndClass; INSTANCE:4]", 'DAVB', davb)
        self.__click_and_wait("[CLASS:ThunderRT6CommandButton; INSTANCE:11]")

    def preenche_ddf_glosa(self, tributo, dci, dij, dcm, valor_basico, davb):
        self.__check_and_wait('[CLASS:ThunderRT6CheckBox; INSTANCE:7]', not dci)
        self.__focus_and_set_text("[CLASS:ThunderRT6TextBox; INSTANCE:13]", 'tributo', tributo)
        if dci:
            self.__focus_and_set_text("[CLASS:MSMaskWndClass; INSTANCE:2]", 'DCI', dci)
            self.__focus_and_set_text("[CLASS:MSMaskWndClass; INSTANCE:3]", 'DIJ', dij)
        self.preenche_ddf_valor_basico(dcm, valor_basico, davb)

    def preenche_ddf_com_qtd(self, qtd):
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:16]', 'Quantidade', qtd)
        self.__click_and_wait("[CLASS:ThunderRT6CommandButton; INSTANCE:11]")

    def preenche_ddf_com_livros_meses(self, livros, meses):
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:16]', 'Livros', livros)
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:15]', 'Meses', meses)
        self.__click_and_wait("[CLASS:ThunderRT6CommandButton; INSTANCE:11]")

    def preenche_ddf_documentos_tipo(self, referencia, documentos, tipo):
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:16]', 'Documentos', documentos)
        self.__focus_and_set_text("[CLASS:MSMaskWndClass; INSTANCE:5]", 'Fato Gerador', referencia)
        if tipo == 'Falta de solicitação':
            item = 1
        else:
            item = 2
        self.__wait_dialog_and_select_item(self.titulo_janela, '[CLASS:ThunderRT6ComboBox; INSTANCE:5]',
                                           'Tipo de Operação', item)
        self.__click_and_wait("[CLASS:ThunderRT6CommandButton; INSTANCE:11]")

    def preenche_ddf_tipo_operacao(self, dcm, valor, atraso):
        valor_number = float(valor.replace(',', '.'))
        if atraso:
            if valor_number > 0:
                if int(atraso) <= 15:
                    self.__wait_dialog_and_select_item(self.titulo_janela, '[CLASS:ThunderRT6ComboBox; INSTANCE:5]',
                                                       'Tipo de Operação', 2)
                    self.__click_and_wait("[CLASS:ThunderRT6CommandButton; INSTANCE:11]")
                else:
                    self.__wait_dialog_and_select_item(self.titulo_janela, '[CLASS:ThunderRT6ComboBox; INSTANCE:5]',
                                                       'Tipo de Operação', 3)
                    self.preenche_ddf_valor_basico(dcm, valor, dcm)
            else:
                self.__wait_dialog_and_select_item(self.titulo_janela, '[CLASS:ThunderRT6ComboBox; INSTANCE:5]',
                                                   'Tipo de Operação', 5)
                self.__click_and_wait("[CLASS:ThunderRT6CommandButton; INSTANCE:11]")
        else:
            if valor_number > 0:
                self.__wait_dialog_and_select_item(self.titulo_janela, '[CLASS:ThunderRT6ComboBox; INSTANCE:5]',
                                                   'Tipo de Operação', 1)
                self.preenche_ddf_valor_basico(dcm, valor, dcm)
            else:
                self.__wait_dialog_and_select_item(self.titulo_janela, '[CLASS:ThunderRT6ComboBox; INSTANCE:5]',
                                                   'Tipo de Operação', 4)
                self.__click_and_wait("[CLASS:ThunderRT6CommandButton; INSTANCE:11]")

    def preenche_ddf_valor_basico(self, dcm, basico, davb):
        self.__focus_and_set_text('[CLASS:MSMaskWndClass; INSTANCE:1]', 'DCM', dcm)
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:14]', 'Valor Básico', basico)
        self.__focus_and_set_text('[CLASS:MSMaskWndClass; INSTANCE:1]', 'DCM', dcm)
        if self.__is_control_enabled("[CLASS:MSMaskWndClass; INSTANCE:4]"):
            self.__focus_and_set_text("[CLASS:MSMaskWndClass; INSTANCE:4]", 'DAVB', davb)
        self.__click_and_wait("[CLASS:ThunderRT6CommandButton; INSTANCE:11]")
        # pode aparecer um popup pra DAVB não preenchido (mas simplesmente porque estava desabilitado
        try:
            autoit.win_wait('[CLASS:#32770;TITLE:AIIM2003]', 1)
            msg = autoit.control_get_text('[CLASS:#32770; TITLE:AIIM2003]', '[CLASS:Static; INSTANCE:2]')
            if msg == 'DAVB inconsistente!':
                self.__wait_dialog_and_click('[CLASS:#32770; TITLE:AIIM2003]', '[CLASS:Button; INSTANCE:1]')
            else:
                raise Exception(f'Falha na criação de item do DDF, apareceu mensagem de erro inesperada: {msg}')
        except AutoItError:
            pass

    def limpa_ddf(self):
        # verifica se há itens no DDF clicando na primeira linha e vendo se o botão de excluir habilita
        # se sim, clica em excluir e continua recursivamente até não habilitar mais o excluir

        self.__click_and_wait('[CLASS:ListBox; INSTANCE:3]', x=100, y=25)
        if self.__is_control_enabled('[CLASS:ThunderRT6CommandButton; INSTANCE:18]'):
            logger.info('Excluindo subitem existente no DDF')
            autoit.control_click(self.titulo_janela, '[CLASS:ThunderRT6CommandButton; INSTANCE:18]')
            self.limpa_ddf()

    def limpa_capitulacao(self, janela):
        if autoit.control_get_text(janela, '[CLASS:ThunderRT6TextBox; INSTANCE:1]') != '':
            self.__click_and_wait('[CLASS:ListBox; INSTANCE:1]', x=100, y=20, janela=janela)
            autoit.control_click(janela, '[CLASS:ThunderRT6CommandButton; INSTANCE:5]')
            self.__wait_dialog_and_click('[CLASS:#32770; TITLE:AIIM 2003]',
                                         '[CLASS:Button; INSTANCE:1]')
            self.limpa_capitulacao(janela)

    def __muda_aba(self, nome_aba):
        if nome_aba == 'Infrator':
            self.__click_and_wait('[CLASS:SSTabCtlWndClass; INSTANCE:1]', x=25, y=10)
        elif nome_aba == 'Complemento':
            self.__click_and_wait('[CLASS:SSTabCtlWndClass; INSTANCE:1]', x=100, y=10)
        elif nome_aba == 'Capitulação de Multa':
            self.__click_and_wait('[CLASS:SSTabCtlWndClass; INSTANCE:1]', x=220, y=10)
        elif nome_aba == 'TTPA/Relato':
            self.__click_and_wait('[CLASS:SSTabCtlWndClass; INSTANCE:1]', x=330, y=10)
        elif nome_aba == 'DDF':
            self.__click_and_wait('[CLASS:SSTabCtlWndClass; INSTANCE:1]', x=400, y=10)
        elif nome_aba == 'Observação':
            self.__click_and_wait('[CLASS:SSTabCtlWndClass; INSTANCE:1]', x=450, y=10)

    def __abre_aiim(self, numero: str, posicao: int):
        # verifica se AIIM ja esta aberto, se não, abre
        logger.info(f'Abrindo AIIM {numero} no AIIM2003...')
        parser = re.compile(r'\D')
        try:
            autoit.win_activate(self.titulo_janela)
            # num_tela é o número do AIIM na tela
            num_tela = parser.sub('',
                                  autoit.control_get_text(self.titulo_janela, '[CLASS:ThunderRT6TextBox; INSTANCE:35]'))
            if num_tela == parser.sub('', numero):
                return
        except AutoItError:
            pass
        self.__save_and_exit()
        self.__open_menu('ABRE_AIIM', posicao)
        num_tela = parser.sub('',
                              autoit.control_get_text(self.titulo_janela, '[CLASS:ThunderRT6TextBox; INSTANCE:35]'))
        if num_tela != parser.sub('', numero):
            raise Exception(f'Aberto AIIM errado! Será que o AIIM {numero} não foi apagado?')

    def __update_relato(self, relato: str):
        # coloca relato - dá send para cada linha existente, para quebrar relato
        logger.info('Atualizando relato')
        item = self._get_item_number()
        relato = re.sub(r'Anexo \d+', f'Anexo {item}', relato)
        relato = re.sub(r'Anexo <item>', f'Anexo {item}', relato)
        linhas = relato.splitlines()
        if len(linhas) == 1:
            self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:19]', 'Relato', linhas[0])
        else:
            self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:19]', 'Relato', '')
            for linha in linhas:
                self.__focus_and_send('[CLASS:ThunderRT6TextBox; INSTANCE:19]', 'Relato', linha + '{ENTER}')
            self.__focus_and_send('[CLASS:ThunderRT6TextBox; INSTANCE:19]', 'Relato', '{BACKSPACE}')

    def cria_aiim(self, numero, audit: Audit):
        logger.info(f'Criando AIIM {numero} no AIIM2003...')
        self.__open_menu('NOVO_AIIM')
        numero_so_digitos = re.sub(r'\D', '', numero)
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:35]', 'Número AIIM', numero_so_digitos)
        # a janela está aberta, então dá pra mandar posicao=0 sem problemas
        self.atualiza_aiim(numero, 0, audit)

    def atualiza_aiim(self, numero: str, posicao: int, audit: Audit):
        self.__abre_aiim(numero, posicao)
        # verifica se o AIIM não está em modo retirrati; se estiver, desiste da atualização
        try:
            self.__wait_dialog_and_click('[CLASS:#32770;TITLE:Retificação de AIIMs]', '[CLASS:Button; INSTANCE:2]')
            return
        except AutoItError:
            pass

        logger.info(f'Atualizando dados gerais do AIIM {numero} no AIIM2003...')
        self.__muda_aba('Infrator')
        texto_ie = autoit.control_get_text(self.titulo_janela, '[CLASS:ThunderRT6TextBox; INSTANCE:26]')
        if len(texto_ie) == 0:
            self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:26]', 'IE', audit.ie)
            self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:27]', 'CNPJ', audit.cnpj)
        self.__check_and_wait('[CLASS:ThunderRT6CheckBox; INSTANCE:2]', True)
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:33]', 'Nome', audit.empresa)
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:24]', 'CNAE', audit.cnae)
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:30]', 'Endereço', audit.logradouro)
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:21]', 'Número', audit.numero)
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:22]', 'Complemento',
                                  audit.complemento[:10])
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:32]', 'Bairro', audit.bairro)
        self.__focus_and_set_text('[CLASS:ThunderRT6TextBox; INSTANCE:31]', 'CEP', audit.cep.replace('.', ''))

        self.__muda_aba('Complemento')
        self.__check_and_wait('[CLASS:ThunderRT6CheckBox; INSTANCE:20]', False)
        # serviria pra mudar o complemento - melhor que usuário altere os dados do cadastro do posto fiscal
        # self.__click_and_wait('[CLASS:ThunderRT6CommandButton; INSTANCE:33]')
        # self.__wait_dialog_and_set_text("[CLASS:ThunderRT6FormDC; TITLE:Endereço da Lavratura]",
        #                                '[CLASS:ThunderRT6TextBox; INSTANCE:2]', 'Complemento Lavratura', '3º ANDAR')
        # self.__wait_dialog_and_click("[CLASS:ThunderRT6FormDC; TITLE:Endereço da Lavratura]",
        #                             '[CLASS:ThunderRT6CommandButton; INSTANCE:2]')
        self.__check_and_wait('[CLASS:ThunderRT6CheckBox; INSTANCE:19]', True)
        self.__focus_and_set_text('[CLASS:MSMaskWndClass; INSTANCE:6]', 'OSF', audit.osf)
        self.__save_and_exit()

    def preenche_ddf(self, aiim_number: str, aiim_position: int, item: int, dicionario: dict):
        self.__abre_aiim(aiim_number, aiim_position)
        if dicionario.get('relato', None):
            self.__muda_aba('TTPA/Relato')
            self.__update_relato(dicionario['relato'])

        self.__muda_aba('DDF')
        self.__wait_dialog_and_select_item(self.titulo_janela, '[CLASS:ThunderRT6ComboBox; INSTANCE:6]',
                                           'Número Item', item)
        if int(autoit.control_get_text(self.titulo_janela, "[CLASS:ThunderRT6ComboBox; INSTANCE:6]")) != item:
            raise Exception(f'Não foi localizado o item {item} no AIIM, verifique se não foi mudado manualmente.')
        self.limpa_ddf()
        logger.info('Preenchendo DDF do item no AIIM2003')
        inciso = dicionario['infracao'].inciso
        alinea = dicionario['infracao'].alinea
        if inciso == 'I' and alinea == 'a':
            for index, row in dicionario['ddf'].iterrows():
                self.preenche_ddf_dci_davb(row['valor'], row['referencia'], row['dia_seguinte'])
        elif inciso == 'I' and alinea in ['b', 'c', 'd', 'i', 'j', 'l', 'm']:
            for index, row in dicionario['ddf'].iterrows():
                self.preenche_ddf_com_dij(row['valor'], row['referencia'], row['vencimento'], row['vencimento'])
        elif inciso == 'I' and alinea == 'e':
            for index, row in dicionario['ddf'].iterrows():
                self.preenche_ddf_dci_davb(row['valor'], row['referencia'], row['davb'])
        elif inciso == 'II' and alinea == 'b':
            for index, row in dicionario['ddf'].iterrows():
                self.preenche_ddf_glosa(row['valor'], row['dci'], row['dij'],
                                        row['dcm'], row['valor_basico'], row['referencia'])
        elif inciso == 'II' and alinea == 'j':
            for index, row in dicionario['ddf'].iterrows():
                self.preenche_ddf_glosa(row['valor'], row['dci'], row['dij'],
                                        row['dcm'], row['valor_basico'], row['davb'])
        elif inciso == 'IV' and alinea == 'b':
            for index, row in dicionario['ddf'].iterrows():
                self.preenche_ddf_valor_basico(row['referencia'], row['valor'], row['referencia'])
        elif inciso == 'IV' and alinea in ['z2', 'z3']:
            for index, row in dicionario['ddf'].iterrows():
                self.preenche_ddf_documentos_tipo(row['referencia'], row['valor'], dicionario['infracao'].ddf_type)
        elif inciso == 'V' and alinea in ['a', 'c']:
            for index, row in dicionario['ddf'].iterrows():
                if len(row) == 1:
                    self.preenche_ddf_com_qtd(row['valor'])
                else:
                    self.preenche_ddf_valor_basico(row['referencia'], row['valor'], row['referencia'])
        elif inciso == 'V' and alinea in ['g', 'h', 'j']:
            for index, row in dicionario['ddf'].iterrows():
                self.preenche_ddf_com_livros_meses(row['Livros'], row['Meses'])
        elif inciso == 'V' and alinea == 'm':
            for index, row in dicionario['ddf'].iterrows():
                self.preenche_ddf_com_qtd(row['Meses'])
        elif inciso == 'VII' and alinea == 'a':
            for index, row in dicionario['ddf'].iterrows():
                self.preenche_ddf_tipo_operacao(row['referencia'], row['valor'], row['atraso'])
        else:
            raise Exception(
                f'Não soube o que fazer com esse inciso/alínea: {dicionario["inciso"]}/{dicionario["alinea"]}')
        self.__save_and_exit()

    def _get_item_number(self):
        try:
            return int(autoit.control_get_text(
                self.titulo_janela, "[CLASS:ThunderRT6ComboBox; INSTANCE:6]"))
        except (ValueError, AutoItError):
            try:
                return int(autoit.control_get_text(
                    self.titulo_janela, "[CLASS:ThunderRT6ComboBox; INSTANCE:7]"))
            except (ValueError, AutoItError):
                try:
                    return int(autoit.control_get_text(
                        self.titulo_janela, "[CLASS:ThunderRT6ComboBox; INSTANCE:8]"))
                except (ValueError, AutoItError):
                    return 0

    def cadastra_ufesp(self, ano: int, valor: float):
        self.__open_menu('UFESP')
        self.__focus_and_set_text("[CLASS:MSMaskWndClass; INSTANCE:2]", "Data Inicial UFESP", "01/01/" + str(ano))
        self.__focus_and_set_text("[CLASS:MSMaskWndClass; INSTANCE:1]", "Data Final UFESP", "31/12/" + str(ano))
        self.__focus_and_set_text("[CLASS:ThunderRT6TextBox; INSTANCE:1]", "Valor UFESP", str(valor).replace(".", ","))
        self.__click_and_wait('[CLASS:ThunderRT6CommandButton; INSTANCE:5]')
        self.__click_and_wait('[CLASS:ThunderRT6CommandButton; INSTANCE:2]')

    def cria_item(self, aiim_number: str, aiim_position: int, aiim_item: AiimItem) -> int:
        self.__abre_aiim(aiim_number, aiim_position)

        logger.info('Criando item e definindo capitulação da multa')
        self.__muda_aba('Capitulação de Multa')
        item_anterior = self._get_item_number()
        self.__click_and_wait('[CLASS:ThunderRT6CommandButton; INSTANCE:29]')
        self.__focus_and_send('[CLASS:ThunderRT6ComboBox; INSTANCE:13]', 'Inciso',
                              str(aiim_item.infracao.inciso_number()))
        self.__focus_and_send('[CLASS:ThunderRT6ComboBox; INSTANCE:12]', 'Alínea', aiim_item.infracao.alinea, combo=True)

        if aiim_item.infracao.operation_type:
            if aiim_item.infracao.operation_type == "Tributada":
                self.__click_and_wait('[CLASS:ThunderRT6OptionButton; INSTANCE:11]')
            elif aiim_item.infracao.operation_type == "Isenta":
                self.__click_and_wait('[CLASS:ThunderRT6OptionButton; INSTANCE:13]')
            elif aiim_item.infracao.operation_type == "Não Tributada":
                self.__click_and_wait('[CLASS:ThunderRT6OptionButton; INSTANCE:12]')
        if aiim_item.infracao.order:
            autoit.control_send(self.titulo_janela, '[CLASS:ThunderRT6ComboBox; INSTANCE:14]',
                                aiim_item.infracao.order)

        # caso reclame que já tem item parecido
        try:
            autoit.win_wait('[CLASS:#32770;TITLE:AIIM2003]', 2)
            msg = autoit.control_get_text('[CLASS:#32770; TITLE:AIIM2003]', '[CLASS:Static; INSTANCE:2]')
            if msg.startswith('Já possui item igual'):
                self.__wait_dialog_and_click('[CLASS:#32770; TITLE:AIIM2003]', '[CLASS:Button; INSTANCE:1]')
        except AutoItError:
            pass

        time.sleep(1)
        if item_anterior == self._get_item_number():
            raise Exception('Ocorreu uma falha na criação de item no AIIM2003, não conseguiu criar um novo...')

        logger.info('Escolhendo tipificação de pena para o item')
        self.__muda_aba('TTPA/Relato')
        self.__click_and_wait('[CLASS:ThunderRT6CommandButton; INSTANCE:10]')
        ttpa = '[CLASS:ThunderRT6FormDC; TITLE:Escolha do T.T.P.A.]'
        self.__click_and_wait('[CLASS:TreeView20WndClass; INSTANCE:1]', wait=False, janela=ttpa, x=50, y=10)
        autoit.control_send(ttpa, '[CLASS:TreeView20WndClass; INSTANCE:1]', '{RIGHT}')
        # Na janela de TTPA, vai usando o teclado para escolher a opção certa
        # Deve-se cadastrar na infracao uma lista de números, indicando a posição do item a selecionar em
        # cada nível da árvore
        # Há alguns casos em que abre uma janela de escolha de regime: nesse caso, o cadastro não deve informar
        # simplesmente o número da posição do item, mas uma lista com 2 valores: a posição do item e a posição da
        # alternativa que deve ser selecionada
        for subnivel in aiim_item.infracao.ttpa:
            if type(subnivel) == int:
                i = subnivel
                while i > 0:
                    autoit.control_send(ttpa, '[CLASS:TreeView20WndClass; INSTANCE:1]', '{DOWN}')
                    # pode acontecer de abrir janela de escolha antes da hora.
                    # Preenche qualquer coisa e segue em frente
                    try:
                        self.__wait_dialog_and_select_item('[CLASS:ThunderRT6FormDC; TITLE:Selecione a alternativa]',
                                                           '[CLASS:ThunderRT6ListBox; INSTANCE:1]',
                                                           'Alternativa de regime fiscal',
                                                           1, wait=False)
                        self.__wait_dialog_and_click('[CLASS:ThunderRT6FormDC; TITLE:Selecione a alternativa]',
                                                     '[CLASS:ThunderRT6CommandButton; INSTANCE:1]', wait=False)
                    except AutoItError:
                        pass
                    i -= 1
                autoit.control_send(ttpa, '[CLASS:TreeView20WndClass; INSTANCE:1]', '{RIGHT}')
            else:
                posicao = subnivel[0]
                opcao_lista_regimes = subnivel[1]
                descidas = 0
                while descidas < posicao:
                    autoit.control_send(ttpa, '[CLASS:TreeView20WndClass; INSTANCE:1]', '{DOWN}')
                    self.__wait_dialog_and_select_item('[CLASS:ThunderRT6FormDC; TITLE:Selecione a alternativa]',
                                                       '[CLASS:ThunderRT6ListBox; INSTANCE:1]',
                                                       'Alternativa de regime fiscal',
                                                       opcao_lista_regimes)
                    self.__wait_dialog_and_click('[CLASS:ThunderRT6FormDC; TITLE:Selecione a alternativa]',
                                                 '[CLASS:ThunderRT6CommandButton; INSTANCE:1]')
                    descidas += 1
                autoit.control_send(ttpa, '[CLASS:TreeView20WndClass; INSTANCE:1]', '{RIGHT}')

        self.__click_and_wait('[CLASS:ThunderRT6CommandButton; INSTANCE:2]', janela=ttpa)
        self.__wait_dialog_and_click('[CLASS:#32770]', '[CLASS:Button; INSTANCE:1]')

        self.__update_relato(aiim_item.relato())

        if aiim_item.infracao.capitulation:
            logger.info('Alterando capitulação do item')
            self.__click_and_wait("[CLASS:ThunderRT6CommandButton; INSTANCE:19]")
            janela_capitulacao = '[CLASS:ThunderRT6FormDC; TITLE:Modelo de Capitulação de Infração]'
            capitulacao = aiim_item.infracao.capitulation
            if capitulacao.clear_existing_capitulation:
                self.limpa_capitulacao(janela_capitulacao)
            for artigo in capitulacao.articles:
                if artigo.is_special():
                    self.__wait_dialog_and_select_item(janela_capitulacao, '[CLASS:ThunderRT6ComboBox; INSTANCE:1]',
                                                       'Legislação', 2)
                    self.__click_and_wait('[CLASS:ThunderRT6TextBox; INSTANCE:8]', wait=False,
                                          janela=janela_capitulacao)
                    self.__wait_dialog_and_set_text(janela_capitulacao, '[CLASS:ThunderRT6TextBox; INSTANCE:2]',
                                                    'Descrição', artigo.text)
                else:
                    self.__wait_dialog_and_set_text(janela_capitulacao, '[CLASS:ThunderRT6TextBox; INSTANCE:8]',
                                                    'Artigo', artigo.artigo)
                    if artigo.inciso:
                        self.__wait_dialog_and_set_text(janela_capitulacao, '[CLASS:ThunderRT6TextBox; INSTANCE:7]',
                                                        'Inciso', artigo.inciso)
                    if artigo.alinea:
                        self.__wait_dialog_and_set_text(janela_capitulacao, '[CLASS:ThunderRT6TextBox; INSTANCE:6]',
                                                        'Alínea', artigo.alinea)
                    if artigo.paragrafo:
                        self.__wait_dialog_and_set_text(janela_capitulacao, '[CLASS:ThunderRT6TextBox; INSTANCE:3]',
                                                        'Parágrafo', artigo.paragrafo)
                    if artigo.item:
                        self.__wait_dialog_and_set_text(janela_capitulacao, '[CLASS:ThunderRT6TextBox; INSTANCE:4]',
                                                        'Item', artigo.item)
                    if artigo.letra:
                        self.__wait_dialog_and_set_text(janela_capitulacao, '[CLASS:ThunderRT6TextBox; INSTANCE:5]',
                                                        'Letra', artigo.letra)
                    self.__wait_dialog_and_click(janela_capitulacao, '[CLASS:ThunderRT6OptionButton; INSTANCE:1]')
                    if artigo.juntar:
                        if artigo.juntar == 'C/C':
                            self.__wait_dialog_and_click(janela_capitulacao,
                                                         '[CLASS:ThunderRT6OptionButton; INSTANCE:3]')
                        elif artigo.juntar == 'E':
                            self.__wait_dialog_and_click(janela_capitulacao,
                                                         '[CLASS:ThunderRT6OptionButton; INSTANCE:2]')
                self.__wait_dialog_and_click(janela_capitulacao, '[CLASS:ThunderRT6CommandButton; INSTANCE:4]')
            self.__wait_dialog_and_click(janela_capitulacao, '[CLASS:ThunderRT6CommandButton; INSTANCE:2]')

        item_numero = self._get_item_number()
        self.__save_and_exit()
        return item_numero

    def remove_aiim_item(self, aiim_number: str, aiim_posicao: int, item: int):
        self.__abre_aiim(aiim_number, aiim_posicao)
        self.__muda_aba('Capitulação de Multa')
        self.__wait_dialog_and_select_item(self.titulo_janela, '[CLASS:ThunderRT6ComboBox; INSTANCE:8]',
                                           'Número Item', item)
        if int(autoit.control_get_text(self.titulo_janela, "[CLASS:ThunderRT6ComboBox; INSTANCE:8]")) != item:
            raise Exception(f'Não foi localizado o item {item} no AIIM, verifique se não foi mudado manualmente.')
        self.__click_and_wait('[CLASS:ThunderRT6CommandButton; INSTANCE:28]')
        self.__wait_dialog_and_click('[CLASS:#32770; TITLE:Exclusão de item]', '[CLASS:Button; INSTANCE:1]')
        self.__save_and_exit()

    def gera_relatorios(self, aiim_number: str, aiim_posicao: int):
        numero_sem_serie = int(re.sub(r'\D', '', aiim_number)[:-1])
        (self.reports_path / f'Relato_A{numero_sem_serie}.pdf').unlink(missing_ok=True)
        (self.reports_path / f'Quadro1_A{numero_sem_serie}.pdf').unlink(missing_ok=True)
        (self.reports_path / f'Quadro2_A{numero_sem_serie}.pdf').unlink(missing_ok=True)

        self.__open_menu("RELATORIOS", aiim_posicao)
        logger.info('Gerando relatórios no AIIM2003...')
        self.__check_and_wait('[CLASS:ThunderRT6CheckBox; INSTANCE:1]', True)
        self.__check_and_wait('[CLASS:ThunderRT6CheckBox; INSTANCE:4]', True)
        self.__check_and_wait('[CLASS:ThunderRT6CheckBox; INSTANCE:5]', True)
        self.__click_and_wait('[CLASS:ThunderRT6CommandButton; INSTANCE:2]', wait=False)

        # Aguarda os 3 arquivos gerados aparecerem
        max_espera = 60
        GeneralFunctions.wait_downloaded_file(self.reports_path, f'Relato_A{numero_sem_serie}.pdf', max_espera)
        GeneralFunctions.wait_downloaded_file(self.reports_path, f'Quadro1_A{numero_sem_serie}.pdf', max_espera)
        GeneralFunctions.wait_downloaded_file(self.reports_path, f'Quadro2_A{numero_sem_serie}.pdf', max_espera)
        logger.info('Relatórios do AIIM2003 gerados!')

        pdf_app = GeneralFunctions.get_default_windows_app('.pdf').lower()
        if any([pdf_app.find(name) >= 0 for name in ['adobe', 'acrobat', 'acrord']]):
            # caso o AIIM2003 abra o Acrobat Reader
            try:
                autoit.win_wait("[REGEXPTITLE:(?i)(.*- Adobe.*)]", 5)
                autoit.win_close("[REGEXPTITLE:(?i)(.*- Adobe.*)]")
            except AutoItError as e:
                logger.exception('Falha ao fechar janelas do Acrobat Reader')
                raise e
            # fecha todos os popups do Acrobat
            fechou_popup1 = False
            while True:
                if not fechou_popup1:
                    popup_acrobat = '[CLASS:#32770;TITLE:Adobe Acrobat]'
                    autoit.win_wait(popup_acrobat, 1)
                    botao = autoit.control_get_text(popup_acrobat, '[CLASS:Button;INSTANCE:2]')
                    if botao.startswith('Fechar todas'):
                        # não está setada opção pra sempre fechar todas
                        self.__wait_dialog_and_click(popup_acrobat, '[CLASS:Button;INSTANCE:2]')
                        fechou_popup1 = True
                else:
                    try:
                        popup_acrobat = '[CLASS:#32770;TITLE:Acrobat Reader]'
                        autoit.win_wait(popup_acrobat, 2)
                        logger.error('Achei popup de salvar')
                        botao = autoit.control_get_text(popup_acrobat, '[CLASS:Button;INSTANCE:3]')
                        if botao == '&Não':
                            # fala que não quer salvar alterações
                            self.__wait_dialog_and_click(popup_acrobat, '[CLASS:Button;INSTANCE:3]')
                    except AutoItError as e2:
                        if str(e2).find('timeout on wait') >= 0:
                            logger.info('Fechados todos os popups do Acrobat Reader')
                            break
                        else:
                            raise e2
        else:
            # verifica tela de erro do AIIM2003 por não achar Acrobat Reader, determina fim da geração
            autoit.win_wait('[CLASS:ThunderRT6FormDC;TITLE:Erro de ambiente]', 5)
            autoit.win_activate('[CLASS:ThunderRT6FormDC;TITLE:Erro de ambiente]')
            autoit.control_send('[CLASS:ThunderRT6FormDC;TITLE:Erro de ambiente]',
                                '[CLASS:ThunderRT6CommandButton; INSTANCE:1]', '{ENTER}')

        self.__click_and_wait('[CLASS:ThunderRT6CommandButton; INSTANCE:3]', wait=True)

    def exclui_aiim(self, aiim_number: str, aiim_posicao: int):
        logger.info(f'Excluindo AIIM {aiim_number} do AIIM 2003...')
        try:
            self.__open_menu('EXCLUIR', aiim_posicao)
            self.__wait_dialog_and_click('[CLASS:#32770;TITLE:Exclusão de AIIM]', '[CLASS:Button; INSTANCE:1]')
            autoit.win_wait('[CLASS:#32770;TITLE:Exclusão de AIIM]', 10)
            msg = autoit.control_get_text('[CLASS:#32770;TITLE:Exclusão de AIIM]', '[CLASS:Static; INSTANCE:2]')
            self.__wait_dialog_and_click('[CLASS:#32770;TITLE:Exclusão de AIIM]', '[CLASS:Button; INSTANCE:1]')
            if msg != 'Operação bem sucedida!':
                logger.error(f'Falha na exclusão de AIIM: {msg}')
                raise Exception(f'Ocorreu erro na exclusão de AIIM: {msg}')
        except AutoItError as e:
            logger.exception('Falha na exclusão de AIIM')
            raise Exception(f'Ocorreu erro na exclusão de AIIM: {str(e)}')
        logger.info('Exclusão de AIIM realizada com sucesso')

    def importa(self, aiim_number: str, aex_path: Path):
        logger.info(f'Realizando importação do AIIM {aiim_number} contido em {aex_path}')
        try:
            self.__open_menu("IMPORTAR")
            self.__wait_dialog_and_set_text('[CLASS:#32770;TITLE:Abrir]', '[CLASS:Edit; INSTANCE:1]',
                                            'Diálogo para abrir arquivo AEX', str(aex_path))
            self.__wait_dialog_and_click('[CLASS:#32770;TITLE:Abrir]', '[CLASS:Button; INSTANCE:1]')
            autoit.win_wait('[CLASS:#32770;TITLE:Importar AIIM]', 10)
            msg = autoit.control_get_text('[CLASS:#32770;TITLE:Importar AIIM]', '[CLASS:Static; INSTANCE:2]')
            self.__wait_dialog_and_click('[CLASS:#32770;TITLE:Importar AIIM]', '[CLASS:Button; INSTANCE:1]')
            if msg != 'Importação bem sucedida!':
                logger.error(f'Falha na importação de AIIM: {msg}')
                raise Exception(f'Ocorreu erro na importação de AIIM: {msg}')
        except AutoItError as e:
            logger.exception('Falha na importação de AIIM')
            raise Exception(f'Ocorreu erro na importação de AIIM: {str(e)}')
        logger.info('Importação de AIIM realizada com sucesso')

    def exporta(self, aiim_number: str, aiim_posicao: int, aex_path: Path):
        (aex_path / f'{aiim_number.replace(".", "")}.aex').unlink(missing_ok=True)

        self.__open_menu("EXPORTAR", aiim_posicao)
        logger.info(f'Realizando exportação do AIIM {aiim_number} em {aex_path}')
        popup = '[CLASS:ThunderRT6FormDC;TITLE:Exportar para...]'
        autoit.control_send(popup, '[CLASS:ThunderRT6DriveListBox; INSTANCE:1]', aex_path.drive)
        for subnivel in range(1, len(aex_path.parts)):
            current_path = aex_path.parents[len(aex_path.parents) - subnivel]
            next_path = aex_path.parts[subnivel]
            dir_list = [d for d in os.listdir(current_path) if os.path.isdir(os.path.join(current_path, d))]
            visible_dir_list = []
            for d in dir_list:
                attribute = win32api.GetFileAttributes(os.path.join(current_path, d))
                if not attribute & (win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM):
                    visible_dir_list.append(d.lower())
            x = 30
            dir_position_in_list = sorted(visible_dir_list).index(next_path.lower()) + 1
            if subnivel + dir_position_in_list > 15:
                # tem que fazer scroll na lista, clica no último item que aparece
                autoit.control_send(popup, '[CLASS:ThunderRT6DirListBox; INSTANCE:1]',
                                    '{DOWN ' + f'{dir_position_in_list}' + '}')
                autoit.control_click(popup, '[CLASS:ThunderRT6DirListBox; INSTANCE:1]', clicks=2,
                                     x=x, y=220)
            else:
                y = (subnivel + dir_position_in_list) * 15 - 5
                autoit.control_click(popup, '[CLASS:ThunderRT6DirListBox; INSTANCE:1]', clicks=2,
                                     x=x, y=y)
        self.__wait_dialog_and_click(popup, '[CLASS:ThunderRT6CommandButton; INSTANCE:2]')

        # aguarda exportação
        try:
            autoit.win_wait('[CLASS:#32770;TITLE:Exportação de AIIM]', 10)
            msg = autoit.control_get_text('[CLASS:#32770;TITLE:Exportação de AIIM]', '[CLASS:Static; INSTANCE:2]')
            self.__wait_dialog_and_click('[CLASS:#32770;TITLE:Exportação de AIIM]', '[CLASS:Button; INSTANCE:1]')
            if msg != 'Operação bem sucedida!':
                logger.error(f'Falha na exportação de AIIM: {msg}')
                raise Exception(f'Ocorreu erro na exportação de AIIM: {msg}')
            if not (aex_path / f'{aiim_number.replace(".", "")}.aex').is_file():
                raise Exception('Arquivo do AIIM não foi salvo na pasta correta! Tente novamente!')
        except AutoItError as e:
            logger.exception('Falha na exportação de AIIM')
            raise Exception(f'Ocorreu erro na exportação de AIIM: {str(e)}')
        logger.info('Exportação de AIIM realizada com sucesso')

    def gera_transmissao(self, aiim_number: str, aiim_posicao: int, sfz_path: Path,
                         data_lavratura: datetime.date = None):

        numero_sem_serie = int(re.sub(r'[^\d]', '', aiim_number)[:-1])
        (sfz_path / f'A{numero_sem_serie}.sfz').unlink(missing_ok=True)

        self.__open_menu("TRANSMITIR")
        logger.info(f'Realizando transmissão do AIIM {aiim_number} em {sfz_path}')
        popup = '[CLASS:ThunderRT6FormDC;TITLE:Exportação para Entrega]'
        autoit.win_wait(popup, 5)
        self.__click_and_wait('[CLASS:ListView20WndClass; INSTANCE:1]',
                              janela=popup, x=100, y=30, wait=False)
        if aiim_posicao > 1:
            self.__wait_dialog_and_select_item(popup, '[CLASS:ListView20WndClass; INSTANCE:1]',
                                               'Autos cadastrados', aiim_posicao)
        self.__click_and_wait('[CLASS:ThunderRT6CommandButton; INSTANCE:1]', janela=popup)
        with AIIM2003MDBReader() as aiim2003:
            is_aiim_open = aiim2003.is_aiim_open_to_edition(numero_sem_serie)
        if is_aiim_open:
            if data_lavratura:
                self.__wait_dialog_and_set_text('[CLASS:ThunderRT6FormDC;TITLE:Data Lavratura',
                                                '[CLASS:MSMaskWndClass; INSTANCE:1]',
                                                'Data Lavratura', data_lavratura.strftime('%d/%m/%y'))
            self.__wait_dialog_and_click('[CLASS:ThunderRT6FormDC;TITLE:Data Lavratura]',
                                         '[CLASS:ThunderRT6CommandButton; INSTANCE:2]')

        # verifica tela de erro por não achar Adobe Reader
        pdf_app = GeneralFunctions.get_default_windows_app('.pdf')
        # TODO tem que ver o que acontece numa maquina que tem adobe...
        if pdf_app.find('adobe') == -1 or pdf_app.find('acrobat') == -1:
            autoit.win_wait('[CLASS:ThunderRT6FormDC;TITLE:Erro de ambiente]', 5)
            autoit.win_activate('[CLASS:ThunderRT6FormDC;TITLE:Erro de ambiente]')
            autoit.control_send('[CLASS:ThunderRT6FormDC;TITLE:Erro de ambiente]',
                                '[CLASS:ThunderRT6CommandButton; INSTANCE:1]', '{ENTER}')
            autoit.win_wait('[CLASS:ThunderRT6FormDC;TITLE:Erro de ambiente]', 5)
            autoit.win_activate('[CLASS:ThunderRT6FormDC;TITLE:Erro de ambiente]')
            autoit.control_send('[CLASS:ThunderRT6FormDC;TITLE:Erro de ambiente]',
                                '[CLASS:ThunderRT6CommandButton; INSTANCE:1]', '{ENTER}')

        # salvar como...
        self.__wait_dialog_and_set_text('[CLASS:#32770;TITLE:Salvar como]', '[CLASS:Edit; INSTANCE:1]',
                                        'Janela de salvar como',
                                        str(sfz_path / f'A{numero_sem_serie}.sfz'))
        self.__wait_dialog_and_click('[CLASS:#32770;TITLE:Salvar como]', '[CLASS:Button; INSTANCE:2]')
        GeneralFunctions.wait_downloaded_file(sfz_path, f'A{numero_sem_serie}.sfz', timeout=30)
        self.__wait_dialog_and_click(popup, '[CLASS:ThunderRT6CommandButton; INSTANCE:2]')

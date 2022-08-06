import datetime
import re
import sys
import threading
import time
from json import JSONDecodeError
from zipfile import BadZipFile

import PyInstaller.__main__
import PySimpleGUI as sg
import numpy as np
import pandas as pd

import Controller
import GUIFunctions
import GeneralConfiguration
import GeneralFunctions
import InitialConfigurationWizard
import QueryResultWindow
import WaitWindow
from pathlib import Path
from tkhtmlview import html_parser

from AnalysisFunctions import AnalysisFunctionException
from AnalysisWizardWindow import AnalysisWizardWindow
from Audit import Audit, AiimItem, PossibleInfraction
from Audit import get_current_audit, create_new_audit, set_audit
from ConfigFiles import ConfigFileDecoderException, Analysis
from ExcelDDFs import ExcelArrazoadoAbaInexistenteException, ExcelArrazoadoIncompletoException
from LogWindow import LogWindow
from SQLReader import QueryAnalysisException

window: sg.Window


def refresh_data_tab():
    for grupo in Controller.data_groups.keys():
        global extracoes
        extracoes = {}
        for tarefa in Controller.data_groups[grupo]['progressos']:
            window[f'-{grupo}-{tarefa[0]}-TEXT-'].update(visible=False)
            window[f'-{grupo}-{tarefa[0]}-PROGRESS-'].update(visible=False)
            window[f'-{grupo}-{tarefa[0]}-INFINITE-'].update(visible=False)
            window[f'-{grupo}-{tarefa[0]}-OK-'].update(visible=False)
            window[f'-{grupo}-{tarefa[0]}-ERROR-'].update(visible=False)
            window[f'-{grupo}-{tarefa[0]}-STOP-'].update(visible=False)

    if get_current_audit():
        window['-DATA-EXTRACTION-'].update(disabled=False)
    else:
        window['-DATA-EXTRACTION-'].update(disabled=True)


def clear_data_tab():
    checkboxes = [v for k, v in window.key_dict.items() if k.endswith('-CHECKBOX-')]
    for c in checkboxes:
        c.update(value=False)


def refresh_analysis_tab():
    try:
        window['-ANALYSIS-CHOSEN-'].update(Controller.get_available_analysis())
    except ConfigFileDecoderException as e:
        GeneralFunctions.logger.exception('Erro com arquivos de configuração')
        GUIFunctions.popup_erro(f'Impossível prosseguir, ocorreu problema com arquivos de configuração '
                                f'do sistema: {str(e)}')
    window['-SQL-'].update(value='', disabled=True)
    window['-QUERY-'].update(disabled=True)


def refresh_notifications_tab():
    window['-NOTIFICATION-CHOSEN-'].update(Controller.get_possible_infractions_osf())
    verification_chosen_for_notification(None)
    notification_prettyprint('', '')


def refresh_aiim_tab():
    window['-AIIM-ITEM-DATA-'].update(visible=False)
    window['-AIIM-CREATE-ITEM-'].update(visible=False)
    window['-AIIM-UPDATE-ITEM-'].update(visible=False)
    window['-AIIM-UPDATE-ITEM-NUMBER-'].update(visible=False)
    window['-AIIM-UPDATE-NOTIF-ANSWER-'].update(visible=False)
    window['-AIIM-REMOVE-ITEM-'].update(visible=False)
    window['-AIIM-ITEM-PROOFS-'].update(visible=False)
    if get_current_audit():
        if get_current_audit().aiim_number:
            window['-MENU-'].update(menu_definition=menu_layout('AUDITORIA_COM_AIIM'))
            window['-AIIM-FRAME-'].update(value=f'AIIM {get_current_audit().aiim_number}')
        else:
            window['-MENU-'].update(menu_definition=menu_layout('AUDITORIA_SEM_AIIM'))
            window['-AIIM-FRAME-'].update(value='AIIM')
        window['-INFRACTION-CHOSEN-'].update(sorted(get_current_audit().aiim_itens))
    else:
        window['-MENU-'].update(menu_definition=menu_layout('SEM_AUDITORIA'))
        window['-AIIM-FRAME-'].update(value='AIIM')


def __clean_tabs():
    set_audit(None)
    refresh_data_tab()
    refresh_analysis_tab()
    refresh_notifications_tab()
    refresh_aiim_tab()


def __refresh_tabs(pasta: Path):
    if Audit.has_local_dados_osf(pasta):
        try:
            Controller.get_local_dados_osf_up_to_date_with_aiim2003()
        except BadZipFile:
            GUIFunctions.popup_erro('Falha na abertura da planilha de arrazoado da fiscalizada. '
                                    'Conserte o arquivo no Excel e reabra a fiscalização.')
            return
        except JSONDecodeError as ex:
            GUIFunctions.popup_erro(f'Falha na abertura do arquivo dados_auditoria.json da fiscalizada. Verifique se '
                                    f'não foi feita nenhuma alteração manual no arquivo no seguinte trecho: '
                                    f'{str(ex)}')
            return

        window['pasta'].update(f"Pasta inicial da fiscalização: {get_current_audit().path()}")
        window['osf'].update(f'OSF: {get_current_audit().osf}')
        window['empresa'].update(f'{get_current_audit().empresa} - CNPJ {get_current_audit().cnpj} - '
                                 f'IE {get_current_audit().ie if get_current_audit() else "Não Informada"}')
        window['endereco'].update(f'Endereço: {get_current_audit().endereco_completo()}')
        window['periodo'].update(f'Período de Fiscalização: '
                                 f'{get_current_audit().inicio_auditoria.strftime("%m/%Y")} '
                                 f'a {get_current_audit().fim_auditoria.strftime("%m/%Y")}')
        window['-MENU-'].update(menu_definition=menu_layout('AUDITORIA_COM_AIIM' if get_current_audit().aiim_number
                                                            else 'AUDITORIA_SEM_AIIM'))
        refresh_data_tab()
        refresh_analysis_tab()
        refresh_notifications_tab()
        refresh_aiim_tab()


def create_audit(pasta: Path):
    audit = get_current_audit()
    ultima_pasta = audit.path() if audit else None
    if ultima_pasta == pasta:
        return
    if Audit.has_local_dados_osf(pasta) and \
            'Sim' == sg.popup('Já existem dados de uma auditoria aberta nesta pasta. Deseja abrí-la?',
                              title='Auditoria existente',
                              custom_text=('Sim', 'Não')):
        open_audit(pasta)

    __clean_tabs()
    create_new_audit(pasta)

    numosf = None
    buscar = True
    if not GeneralFunctions.has_local_osf(pasta):
        layout_popup = [[sg.Text("Será necessário carregar os dados do PGSF e Cadesp.\n"
                                 "Insira abaixo o número da OSF", auto_size_text=True)],
                        [sg.InputText(key='_INPUT_', change_submits=True, do_not_clear=True,
                                      justification='center')],
                        [sg.Button('OK', size=(10, 1), bind_return_key=True, disabled=True),
                         sg.Button('Cancelar', size=(10, 1))]]
        popup = sg.Window(title="Carregar OSF", layout=layout_popup, auto_size_text=True,
                          grab_anywhere=False, finalize=True, modal=True, no_titlebar=False,
                          element_justification='c')
        while True:
            evento, valores = popup.read()
            if evento in (None, 'Cancelar', 'Quit'):
                buscar = False
                break
            if evento == '_INPUT_':
                popup['_INPUT_'].update(re.sub(r"[^\d]", "", valores[evento])[:11])
                must_disable = len(valores['_INPUT_']) != 11
                popup['OK'].update(disabled=must_disable)
                if len(valores['_INPUT_']) == 11:
                    digitado = valores['_INPUT_']
                    popup['_INPUT_'].update(
                        f'{digitado[0:2]}.{digitado[2]}.{digitado[3:8]}/{digitado[8:10]}-{digitado[10]}')
            if evento == 'OK':
                numosf = valores['_INPUT_']
                break
        popup.close()
        del popup

    if buscar:
        WaitWindow.open_wait_window(Controller.update_dados_osf, 'Carregar dados da OSF', numosf)
        if get_current_audit().inicio_auditoria is None:
            inicio = None
            while inicio is None:
                inicio = sg.popup_get_text('Não descobri pela OSF o início da auditoria. Informe (mm/aaaa):',
                                           title='Início Auditoria',
                                           default_text=get_current_audit().inicio_inscricao.strftime('%m/%Y'))
                if inicio and not re.match(r'\d{2}/\d{4}', inicio):
                    inicio = None
            get_current_audit().inicio_auditoria = inicio
            get_current_audit().save()
        if get_current_audit().fim_auditoria is None:
            fim = None
            while fim is None:
                fim = sg.popup_get_text('Não descobri pela OSF o fim da auditoria. Informe (mm/aaaa):',
                                        title='Fim Auditoria',
                                        default_text=datetime.datetime.now().strftime('%m/%Y'))
                if fim and not re.match(r'\d{2}/\d{4}', fim):
                    fim = None
            get_current_audit().fim_auditoria = fim
            get_current_audit().save()
    __refresh_tabs(pasta)


def open_audit(pasta: Path):
    audit = get_current_audit()
    ultima_pasta = audit.path() if audit else None
    if ultima_pasta == pasta:
        return
    if not Audit.has_local_dados_osf(pasta) and \
            'Sim' == sg.popup('Não existe auditoria nesta pasta. Deseja criá-la?',
                              title='Auditoria inexistente',
                              custom_text=('Sim', 'Não')):
        create_audit(pasta)

    __clean_tabs()
    set_audit(pasta)
    __refresh_tabs(pasta)


def print_efd(book: str):
    referencias = Controller.efd_references_imported_PVA()
    referencias_txt = [f'{GeneralFunctions.meses[d.month-1]} de {d.year}' for d in referencias]
    layout = [
        [sg.VPush()],
        [sg.Text('Selecione as referências que deseja gerar PDFs.')],
        [sg.Text('As referências que aparecem são as já importadas.')],
        [sg.Text(f'Os arquivos gerados serão salvos na subpasta {get_current_audit().aiim_path().name}.')],
        [sg.Push(), sg.Listbox(values=referencias_txt, key='-EFD-PRINT-',
                               size=(30, 10),
                               select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE), sg.Push()],
        [sg.Push(), sg.Button('Gerar Livros'), sg.Push()],
        [sg.VPush()]
    ]
    match book:
        case 'lrs':
            titulo = 'Livro de Saídas'
        case 'lre':
            titulo = 'Livro de Entradas'
        case 'lri':
            titulo = 'Livro de Inventário'
        case 'lraicms':
            titulo = 'Livro de Apuração de ICMS'
        case _:
            titulo = 'EFD'
    window = sg.Window(titulo, layout=layout,
                       size=(350, 300),
                       auto_size_text=True, auto_size_buttons=True,
                       text_justification='c',
                       resizable=False, finalize=True,
                       default_element_size=(15, 1),
                       modal=True)
    event, values = window.read()
    window.close()
    if event == 'Gerar Livros':
        referencias_selecionadas = [referencias[referencias_txt.index(data_txt)] for data_txt in values['-EFD-PRINT-']]
        WaitWindow.open_wait_window(Controller.print_efd, 'Impressão de EFD',
                                    book, referencias_selecionadas)


def populate_database(groups: list, progress: dict, eventoThread: threading.Event):
    refresh_data_tab()
    progress.clear()
    Controller.populate_database(groups, window, eventoThread)


def analysis_chosen(analysis: Analysis):
    if get_current_audit() is None:
        return
    if analysis.is_query_based():
        window['query_title'].update(value='Consulta em SQL:')
        window['-SQL-'].update(value=analysis.query, disabled=True)
    else:
        window['query_title'].update(value='Verificação realizada com dados levantados dos sistemas')
        window['-SQL-'].update(value=analysis.function_description, disabled=True)
    window['-QUERY-'].update(disabled=False)


def run_query(analysis: Analysis):
    try:
        if not analysis.is_query_based():
            total, resultado_query = analysis.function()
        else:
            if analysis.fix_database_function is not None:
                _, resultado_query = Controller.executa_consulta_BD(values['-SQL-'])
                analysis.fix_database_function(resultado_query)
            total, resultado_query = Controller.executa_consulta_BD(values['-SQL-'], 100)
    except AnalysisFunctionException as e:
        GUIFunctions.popup_erro(str(e), titulo='Erro no levantamento de dados adicionais para a base de dados')
    except QueryAnalysisException as e:
        GUIFunctions.popup_erro(str(e), titulo='Erro na consulta')
    except Exception as e:
        erroSGBD = re.findall(r'ERROR:\s+(.*)\n', str(e))
        if erroSGBD:
            GUIFunctions.popup_ok(erroSGBD[0], titulo='Erro na consulta')
        else:
            GeneralFunctions.logger.exception('Erro em consulta ao BD de query para análise')
            GUIFunctions.popup_erro(str(e), titulo='Erro na consulta')
    else:
        if total == 0:
            GUIFunctions.popup_ok('Não foram encontrados resultados para esta consulta.',
                                  titulo='Consulta ao banco de dados')
        else:
            dic_query = QueryResultWindow.open_query_result_window(total, resultado_query, values['-SQL-'],
                                                                   analysis)
            if len(dic_query) > 0:
                try:
                    Controller.add_analysis_to_audit(
                        analysis,
                        planilha=dic_query.get('planilha', None), df=dic_query.get('df', None))
                except Controller.AIIMGeneratorUserWarning as e:
                    GUIFunctions.popup_erro(str(e), titulo='Aviso')
                refresh_analysis_tab()


def verification_chosen_for_notification(notification: PossibleInfraction):
    if notification and notification.verificacao.notification_title:
        window['-NOTIFICATION-EDIT-TITLE-'].update(notification.verificacao.notification_title, disabled=False)
        window['-NOTIFICATION-EDIT-'].update(notification.verificacao.notification_body, disabled=False)
        if notification.verificacao.has_notification_any_attachments():
            window['-NOTIFICATION-ATTACHMENTS-'].update(disabled=False)
        window['-NOTIFICATION-SEND-'].update(disabled=False)
        window['-NOTIFICATION-MANUAL-SEND-'].update(disabled=False)
    else:
        window['-NOTIFICATION-EDIT-TITLE-'].update('', disabled=True)
        window['-NOTIFICATION-EDIT-'].update('', disabled=True)
        window['-NOTIFICATION-ATTACHMENTS-'].update(disabled=True)
        window['-NOTIFICATION-SEND-'].update(disabled=True)
        window['-NOTIFICATION-MANUAL-SEND-'].update(disabled=True)


# ATENÇÃO: Mexendo diretamente no Widget pra fazer negrito em partes do texto
def verification_chosen_for_infraction(aiim_item: AiimItem):
    try:
        if aiim_item:
            try:
                relato = aiim_item.relato()
            except ExcelArrazoadoIncompletoException:
                relato = aiim_item.infracao.report
            infraction = aiim_item.infracao
            window['-AIIM-ITEM-DATA-'].update('Análise: ', font_for_value=('Arial', 10, 'bold'))
            window['-AIIM-ITEM-DATA-'].update(f'{aiim_item.verificacao}\n', append=True)
            window['-AIIM-ITEM-DATA-'].update(f'Capitulação: ', font_for_value=('Arial', 10, 'bold'), append=True)
            window['-AIIM-ITEM-DATA-'].update(f'Art. 85, inciso {infraction.inciso}, '
                                              f'alínea "{infraction.alinea}" da Lei 6.374/89\n',
                                              append=True)
            window['-AIIM-ITEM-DATA-'].update('Relato:\n', font_for_value=('Arial', 10, 'bold'), append=True)
            window['-AIIM-ITEM-DATA-'].update(f'{relato}\n', append=True)
            if aiim_item.planilha:
                window['-AIIM-ITEM-DATA-'].update(f'Planilha: ', font_for_value=('Arial', 10, 'bold'), append=True)
                window['-AIIM-ITEM-DATA-'].update(f'{aiim_item.planilha}\n', append=True)
            if aiim_item.has_aiim_item_number():
                window['-AIIM-ITEM-DATA-'].update('Item no AIIM 2003: ', font_for_value=('Arial', 10, 'bold'),
                                                  append=True)
                window['-AIIM-ITEM-DATA-'].update(f'{aiim_item.item}\n', append=True)
                window['-AIIM-CREATE-ITEM-'].update(visible=False)
                window['-AIIM-UPDATE-ITEM-'].update(visible=True)
                window['-AIIM-UPDATE-ITEM-NUMBER-'].update(visible=True)
                window['-AIIM-ITEM-PROOFS-'].update(visible=True)
            else:
                window['-AIIM-CREATE-ITEM-'].update(visible=True)
                window['-AIIM-UPDATE-ITEM-'].update(visible=False)
                window['-AIIM-UPDATE-ITEM-NUMBER-'].update(visible=False)
                window['-AIIM-ITEM-PROOFS-'].update(visible=False)
            if aiim_item.notificacao:
                window['-AIIM-ITEM-DATA-'].update('Notificação Fiscal associada: ',
                                                  font_for_value=('Arial', 10, 'bold'), append=True)
                window['-AIIM-ITEM-DATA-'].update(f'{aiim_item.notificacao}', append=True)
                if aiim_item.notificacao_resposta:
                    window['-AIIM-ITEM-DATA-'].update(f' (Resposta: {aiim_item.notificacao_resposta})', append=True)
                window['-AIIM-ITEM-DATA-'].update('\n', append=True)
                window['-AIIM-UPDATE-NOTIF-ANSWER-'].update(visible=not aiim_item.notificacao_resposta)
            window['-AIIM-ITEM-DATA-'].update(visible=True)
            window['-AIIM-ITEM-DATA-'].expand(True, True)
            window['-AIIM-REMOVE-ITEM-'].update(visible=True)
    except ExcelArrazoadoAbaInexistenteException:
        if GUIFunctions.popup_sim_nao(f'A aba da planilha "{aiim_item.planilha}" não existe mais. '
                                      f'Deseja remover infração?') == 'Sim':
            WaitWindow.open_wait_window(Controller.remove_aiim_item, 'Remover Item do AIIM', aiim_item)
            refresh_aiim_tab()
    except Exception as ex:
        GeneralFunctions.logger.exception('Falha no levantamento de dados da infração')
        GUIFunctions.popup_erro(f'Falha no levantamento de dados da infração: {ex}')


def notification_chosen(notification: PossibleInfraction):
    try:
        verification_chosen_for_notification(notification)
        notification_prettyprint(
            notification.notificacao_titulo(values['-NOTIFICATION-EDIT-TITLE-']),
            notification.notificacao_corpo(values['-NOTIFICATION-EDIT-'])
        )
    except ExcelArrazoadoAbaInexistenteException:
        if GUIFunctions.popup_sim_nao(f'A aba da planilha para essa notificação não existe mais. '
                                      f'Deseja remover notificação?') == 'Sim':
            Controller.remove_notification(notification)
            refresh_notifications_tab()
    except ExcelArrazoadoIncompletoException as e:
        GUIFunctions.popup_erro(str(e))


# ATENÇÃO: O visualizador de HTML depende atualmente do TK
def notification_prettyprint(titulo: str, texto: str):
    widget = window['-NOTIFICATION-PREVIEW-'].Widget
    if titulo == texto == '':
        window['-NOTIFICATION-PREVIEW-'].update('')
    else:
        nomeAFR = GeneralConfiguration.get().nome
        ifAFR = GeneralConfiguration.get().funcional
        parser = html_parser.HTMLTextParser()
        html = f'<span style="font-size: 10px"><b>Complemento do Assunto:</b><i>{titulo}</i></span><br><br><br>' \
               f'<span style="font-size: 10px">{texto}' \
               f'<br><p style="text-align:center"><b>{nomeAFR}' \
               f'<br>Identidade Funcional: {ifAFR}</b></p></span>'
        prev_state = widget.cget('state')
        widget.config(state=sg.tk.NORMAL)
        widget.delete('1.0', sg.tk.END)
        widget.tag_delete(widget.tag_names)
        parser.w_set_html(widget, html, strip=True)
        widget.config(state=prev_state)
        window.refresh()


def notification_show_attachments(notification: PossibleInfraction):
    try:
        Controller.print_sheet_and_open(notification)
    except Exception:
        GUIFunctions.popup_erro(f'Não foi possível criar anexo da análise {notification.verificacao}',
                                titulo='Falha na geração de anexo')


def notification_manual_send(notification: PossibleInfraction):
    dec_numero = sg.popup_get_text('Digite o número completo da notificação enviada via DEC para o '
                                   'contribuinte (ex: IC/N/FIS/00001234/2057):', title='Número DEC')
    if dec_numero:
        try:
            pasta_notificacao = Controller.move_analysis_from_notification_to_aiim(
                notification, dec_numero)
            sg.popup_ok(f'Os arquivos recebidos em resposta devem ser guardados na pasta:\n{pasta_notificacao}',
                        title='Notificação enviada')
            refresh_notifications_tab()
        except ValueError:
            GUIFunctions.popup_erro('Número DEC inválido!')


def notification_send(notification: PossibleInfraction, title: str, content: str):
    if GUIFunctions.popup_sim_nao('Será enviada uma notificação via DEC para o contribuinte,'
                                  'contendo as informações em tela e anexos gerados.\nConfirma?') == 'Sim':
        try:
            pasta_notificacao = WaitWindow.open_wait_window(
                Controller.send_notification, 'Enviar notificação via DEC',
                notification, title, content)
            if pasta_notificacao:
                sg.popup_ok(f'Foi enviada notificação DEC! Os arquivos recebidos'
                            f'em resposta devem ser guardados na pasta {pasta_notificacao}')
                refresh_notifications_tab()
        except Exception as e:
            GUIFunctions.popup_erro('Houve um erro no envio da notificação, '
                                    f'verifique se os arquivos anexos estão fechados: {str}')


def update_gifs():
    for v in [v for k, v in window.key_dict.items() if isinstance(k, str) and k.endswith('-INFINITE-') and v.visible]:
        v.update_animation(v.Source, time_between_frames=100)


def window_layout():
    bar_striped = b'R0lGODlhoAAUAIAAAAQCBP7+/iH/C05FVFNDQVBFMi4wAwEAAAAh+QQJCQABACwAAAAAoAAUAAAC' \
                  b'/oSPFsu9CYGbISbqLMJNH854CliJnUeWKClKrPmuYJvSp1XDs87Zu9zjYXwhXEyTAw6FFOJS2WSqLkfjD1mNJLFXaxD6gGy9T' \
                  b'+7XXCZHwRlpeJMVx6ld7Rxel+fp69Eef6Y24dQn2MZ2gzb4ccf45xho9+gXqVfJ9zQmeQmYtulpCYpZ' \
                  b'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 '
    check_img = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x1e\x00\x00\x00\x1e\x08\x06\x00\x00\x00;0\xae\xa2' \
                b'\x00\x00\x07\x1eIDATx\x9c\x9d\x97\x7f\x8cT\xd5\x15\xc7?\xe7\xde\xf7ffg\x16VDkc\x05\x0c\x91X\x11[' \
                b'\x9a\x06\xea/B5)X\xb0R\xa5Cc\x7fh\xda4\xd4(' \
                b'\xfeBT\xe4\x0f\'ccR5b)\x82\x96\xd4\x16c\xd1v\x07\xacV\xa8\xd4*F\x1b\xad\x16S-\xd0\xd5Z\x95\x08Uc' \
                b'\xa5\xc0\xb2;;\xb3\xef\xbd{N\xff\xd8\x1flw\xe5G=\xc9\xcdK^\xee{\x9f{' \
                b'\xce\xfd\x9e\xfb\xbeO8D\x94\xdb\xcb\xbe\xb6\xa0\x16\x00&\xb7WrcG\xa5\xe7\x99\x86\x0bLl\x1aj\x130F' \
                b'\x83\x08"\x9d\x08\xbb\xc4\xf1\x17D\xfe\xd0\xaa\xf5g7\xcfY\xd9;\xfc\x1d\xc3C\x0e\x07\x9d\xd9~ek(' \
                b'\xb5.T\xe4\xfb\x02\xa7\xbb\x9c\xc7\x82bAA\xado\xb2\x13\xc4;\xc4;,' \
                b'\r\x98Z\x07"\xbf\xb0T\xd7\xbc\xf8\xf5\xbb\xba\x0e\x05\x1f\x0e\x96\x8aU\xa4*U=\xfb\xb1\xc5\x17I\xe4' \
                b'\xef\xf6-\xf9SB3E{SCP@0d\xf0I\xeb\xbf\x03\x86\xe1\\>\x16_\x88\t\x8d\xe4mM\xb3%\x7f\xbex\xf9c\x15' \
                b'\xab\xb8\xaaT\xad\x7f\xf6\x08\xb0\x94\xdb\xcb\xae\xb6\xa0\x16\xcez\xf4\xfa\xdb}!\xb7\xcc\x82\x12z' \
                b'\xd3\x0c\x11\'\xe0\x0e\xb5-C\xc3@1S\x97\x8b#\x17{' \
                b'\xb2f\xfa\xe3\x97.\xbe\xfb\x96\x8aU\\\x95\xaa\xf5/r\x10,3+\x15\xff\\\xb5\x9a\x9dY\xbb\xf6gq[' \
                b'ia\xd2\xd9\x130\x13\x119*\xe0\x88\x05\x98\xa9s\xcerm%\xdf\xdc\xdf\xfd\xc0\xcb\xe5\x9f\xfc\xa0\xdc' \
                b'\xde\xeek\x0b\x16(`\x02\xd0\x7f#|\xe9\xe1\xabo\x8f\x8fm]\x96v\xd6S ' \
                b'>\x84\x04\x8e\x18"\x82C\xe8N\x1b\x04\xd3t\xccqc\xe3\xde}\xddwn\xbdt\xe5\xcd\x03,' \
                b'\x19\xd8\xfc\xe9\x0f/\x9a\x1b\x95\n\x1bC#I1\x8b\xf8\x84T\xef<\xbdYJ=mp\xde\xb8\xa9L?\xe1T\xbbo\xc7' \
                b'\xc6,j\xc9\xc7\xa1\x9e\xce{\xf9[+~Wn/{\xa1Rq3O\xff\xa8\xd8H]\x87\x8b\xfdI\x9ad\xc6\'(' \
                b'\xaf\x00\xce9:\x9bu>]:\x96+\xa7~\x8d\xf9\x93f\x00p\xc1\x86[' \
                b'tO\xd6-\x91\xca\xfb\xbeX8\xed\xc5W\x8buG\xb5\xaa=\xbd\xb20j\xcd\x8f\xcb\x9aI0\xc3\x99\x1a\xff\xcf' \
                b'\x10\x03Sco\xfd\x00\xb3\'|\x91us\x962\x7f\xd2\x0c\xba\x92\x1e\xaez\xfa\xa7\xfc\xbb\xbe\xdf\xb9\xc4' \
                b'\x82/\xe6>\x93t\xd5\xaf\xa0ZU\x99\xf0\xcb\xcb\x0b\xc7Kq\x9b\xcfG\xa7\x84$\xb3\xa3U/\xf4\xf5\x86' \
                b'\x17G\x122\x82\x05\x16O+s\xf9\x94Y\x00\xbc\xdf\xfd\x1f\xae}\xfa^\xb6\xef\xd9I[' \
                b'\xbe\x155U\x17G\x12\x92lg\\,' \
                b'L\x89>E\xfe\xcbx7)4\x12C\xc4\xd9\xe1Y\xff\x13^\x1c\x8d\xb4I).p\xe7\xf9\x8b8\xf7\xa4)\x00\xbc\xd7' \
                b'\xb5\x87\x85\x9b\x97\xb3s\xff\x07\x8c\xc9\xb7\x92\x85\x00\xe0\xb4\x99\x98\xcfE\x13\xd3z\xf3\xfc\xc8' \
                b'\x94\xb9\xce\tAQ\x11\xf3\x03\xfb%"\xa8\x19\xae\xff:<W\xef<\xf5\xa4\xc1q-m\xac\xfe\xea\xf5\x9c6v' \
                b'<\xc1\x94\xfd\xcd.\xaexr9;\xf7\xbd\xcf\xe8|\x894K\x19\xd0\xa9\x19\xeaD\x9c\xa9^\x18i\xb0\xe9d\x01' \
                b'\xb1 }\xdd% \xd0\x934\xc9G9\x1a!\xa5\x18\x17\xc84 ' \
                b'C\xca\xdb\xe8m2\xb6e4\x0f\xcc\xbd\x91\x89cN$\r\x19\xc1\x94k6\xaf\xe4\x9f{' \
                b'vsL\xa1\x954K\x07\x90\xfd\x024\xd1\xd4\x89\xa8Ns\xa66\xc1\xd2\x80\x85\xbe\x03QC`Ow\'\x97\x9d1\x9b' \
                b'\x87\xe6-\xe3\x94cNdo\xbd\x93\x08\x87\xa9\xe1\x0c\x924\xa5\xc5\xe7\xb8\x7f\xceb&\x8e9\x91$\xa4\xc4' \
                b'>\xa2\xfa\xdcZ^\xda\xfdw\xdar%\xd2,' \
                b'\x83\x11BD\xfa\xcf\xf3\xf1\xceTGY\xa6`&\xaa\x011X>\xeb*n:\xe7R&\x1f\x7f2k\xe7-\xe3\xfc\x93\xbf\xc0' \
                b'\x9e\xee\xfdx\x1c\xaaF\x9a\xa5\xdc3{\x11\x9f=n<IH\xc9\xf9\x98_\xefx\x86\xdfl\xdf\xc2\xd8\xc2h\xd2,' \
                b';T\x07\x88\x86\x80\xa9\x8dr}\xabRL\r\xd4\xd0\xa0\x1cSh\x05 ' \
                b'\t)m\x85\x12\xf7]\xb8\x84\xcb>?\x9b}\xf5\x03\xec\xabw\xb2\xf4\xdcos\xf6\xb8)\x83\xd0\xb7\xf7\xbe' \
                b'\xc7\x1d\xcf\xaf\xa3-W$d\x19\xa8\x1ef\x18\xa6*\x0e\xb3.\x0cL\xd50P\r\xfc\xf0\xb7w\xf0\xc4\x1b/\x90' \
                b'\xf31i\xc8\x10\xa0r\xde\xf7\xb8\xe6\xcc\xf9\\t\xea9|w\xeal\x82\x06\xbc\xf3\x98\x19?zv-\xf5f\x03\x8f' \
                b'\xa0\xfdI\x1cb\x18f\x98ZWdAw\x8bw\'\x98\xaa\x19"^\x1c\xc5(' \
                b'\xcf\x92M+QU\xe6M\x9eA\xa6\x19\x1e\xcf\xd5g}cD;=\xde\xf1\'\x9e\x7f\xfbU\x8e-\xb6\x91e\x1f\xfb\xcd' \
                b'\x1f\xda\r&>\x12B\xd8\xedTm+\x82Y0C\x95\x10\x02bB\xc1\xe7X\xb2i%\x8f\xeex\x8e\xc8E\x04\xd3\xc1' \
                b'\xb623\x9c8z\x92&\xf7\xbe\xb0\x9e\x82\xcf\x11\xc2\x91J\xacX0C03\xdb\xea\\\xd0M\x9a\x04A\xd5\x1d\xdc' \
                b'\xe7>\x91\x15}\x9e\x9b6\xaed\xfd\xb6-D\xce\xa3\xa6\x18\xd0W\x1ba\xfd\xf6gy\xf3\xa3]\xb4\xf8\x1c\x1a' \
                b'\x0e[\xe2~\r\xa9\xd34\x88\x05\xdd\xe4Z\\\xb2E{' \
                b'\xd3w$\xf2\x98\xaa\x0eL\xd2\xa0\x88A)*p\xf3\xc6U\xb4\xbf\xf64\x91\xf3\x04\r8\'4\xb3\x84u\xafl\xa6' \
                b'\xe8s\x84>\xa5\x1ea\xa8\x8awh#yWL\x9eq/\xddPk`\xac\x91\xc8\x8b\x05\xd3\xa1\xa5\t!\x80\x19\xa5\xa8' \
                b'\xc0\xd2\'V\xf1\xc8_\x9f"r\x1e3\xd8\xf2\xe6V\xfe\xf1\xe1\xbb\x14|\x0e\r\xe1h\xca\xac\x12G\x02\xac' \
                b'\xd9v\xe3\xaf\xea\x0eC\x1a\x05\xb9/\xebj| ' \
                b'^\xfc\xd0\xac\x07\xda\x0b3Z\xe3\x16nyb\x15\x0fm\xfd=N\x84\xf5\xafm\xc1\xc1\x91T|0[' \
                b'\'>\xed\xee\xf9\xd0\xf5\xf4\xac\xc6L\\\xb9Vvo]\xbb\xee\x00!\\%\xde\x89)a\xf8\x83\x1a\x143\xa35.p' \
                b'\xdb\x93?\xe7\x8e?>\xc8\xeb\x1f\xbcC\xde\xc5hv4e&H\xe4\xc4\x82,' \
                b'\xfa[\xf5\xf1\xfd\xe5\xda\x02\xd7o}\xfa\\\xc8\xe9\xb7\x95\xef\xf6\xa3\n\x8b\xb3\xaef*B<\xb2\x1d' \
                b'\xfaN\xdez\xd2\xa0\x98+\x1c\x95E1#\x8dF\x15\xe2\xec@sEG\xa5v\xdd\x00k\xd0\xec\r8\xcc\xc9\xd5\xf9' \
                b'\x0fF\xa5\xc2ei\xbd7\x13\xcc\xc1H7\xe2\xc4\xa1\xa6GB\xaa!\x1a\x97\xf2Q\xda\xd3\\\xf7\xfa\xad\x1b' \
                b'\xbe\xd3\x0f=h\xf6\x06\xd3\xa9T\x84jUO\xab\\\xb2\xdc\x17r\xd7k\x1a\xb0,' \
                b'd\x80;j;df@\x90\xc8G.\xf6h\x92\xae\xe8\xa8l\xb8\x8eJ\xc5Q=\xe8\xadG\x18\xfaA\xf8\xad\x97|\x13\'w' \
                b'\xf9|<N\x93\x0cM\x83!\xa6\x98\x88\xf4\xd9y\x19\x822\xc4\x0c\x13\xe7b/.\x17\x11\x92\xec_\x16\xec' \
                b'\xa67n\xdb\xf0\xc8p\xe8\xc7\x81\x01(' \
                b'\x97\xcb\xbeV\xab\x853\x96\xce\x1d\x93\xe5\xf2W\x1av\xb9\x88\x9b$N\xfa>(\xc1`\xc0\x1c\x88 ' \
                b'^\x10\xe7\x06\xc4\xf4\x968\x1e\x94\x03\xdd\xab;\xeeyj/\xe5\xb2\xa7v\xe4_\x98\x83\xf0!\xff<\x9f\xbb' \
                b'\xe1+\xa5\xa4\xd8:\x0b\xb8\xc0\x82M\x03\x1d\x8f1\n\x10D\x0e\x80\xec\xc2\xc9+\x82mv>~\xaa\xa3Z\xeb' \
                b'\x1e\xfe\x8e\xe1\xf1_\xde\x81\x01\x8dQ58\x01\x00\x00\x00\x00IEND\xaeB`\x82 '
    error_img = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x1c\x00\x00\x00\x1e\x08\x06\x00\x00\x00?\xc5~\x9f' \
                b'\x00\x00\x07%IDATx\x9c\x8d\x97[' \
                b'l\x9c\xc5\x15\x80\xbf33\xff\xaew\xd7k;\x8eS\xa8\x9d4\x88J\xb4\xa5!-\x94\xab\xe3P\n"J\x08\x97\x94v' \
                b'\xf3\xd0\x97\xbeRZ\x15"\x81(%\xc1\tB\x95E\x15\xa9\xa8R[\xa9\x0f\x95Z\xa9H1\xe2V\x97[' \
                b'\x04R1\xd8@\x9a\xaa*U\xd5\x08\x94\x10.1\x84\xc4\xeb]{' \
                b'\xd7\xf6\xfe3s\xfa\xb0\xf6\xc6v\x92\x8a#\xed\xcb\xfeg\xcewns\xfe\xf3\x0b\xe7\x90A0{' \
                b'\x07A\xf6\x11\x01N\xdf\xb1\xb9_\xa3\xdc\x16\x88\x9b\x80\x8bU\xe9\x02\x10\xa8\x18\x91\xa3"\x8c\x19' \
                b'\x91\x91\xeeg_\x1b\x05P\x90\xbd ' \
                b'\xfbh\x9e_*\xb2\xf2\x8f\x03\xa5\x92\xdd9<\x1c\x00>\xbbu`\x87\x08\xbb"\x0c\xe4\xac5A\x954*\x11\x05' \
                b'\xc0 $F\xb0"\xcc\x86\xa8F\x18\x03\xfdU\xcfs\xaf?\xb9\xd2\xd69\x81Z*Y\x19\x1e\x0eG\xb6_\xdb\xd7c\x92' \
                b'\xdf\xe4\x9c\xbd=\xa82\xe3\x03\xaa\x1a@\x04Ad\xe1\x9c\x82\xa2(' \
                b'\xa8"b\xdb\x9d%\x11\xa1\x16\xc2\x0bU\xef\x7ft\xf1\xf3\xe3\xc7\x17m\x9e\x05\\|p|[\xff\x95\x1d\x89{' \
                b'\xaa\xcd\x9au\x93\x8d4\x08 "\xf6\\\xa9_)Q5\x02\xba*\x93\xd8\xb9\x10\'\xea\xd1\x7fo\xed\xc8\xd8\xf8R' \
                b'\xa8\x01\xd0\xc1A#\xc3\xc3\xe1\xd8\xd6\xeb./&\xf6\xa0\x08\xeb&\x1b\xa97"\xf6\xf3\xc2\x00\x8c\x881' \
                b'"\xb6\x9c\xa6^\x84/\xe6\x8d}\xf9\xc3[' \
                b'\x06\xae\x91\xe1\xe1\xa0\x83\x83\x06@\x14\x0c\x830\xf1\xd6\xc0j\xe78\x9c\xb1f]\xcd\x87`\x16A\xc6,' \
                b'\xb8\x7fV\xfdW\xd0\x96\xebE\xd5\x90w\xd6\xfa\x18?\xd1\x86\\\xb1\xe6\xa5\xd1O\x001\x94J"\xfb\x88\xd1' \
                b'\xeao;2n]\xcd\x07\xbf\x0c6;\x0b\xf5\xda\x19\x83\xe7\x83\xd5k0[o\xe9\x19\x11[' \
                b'\xf7\xc1\xb7;wa\xea\xe2\xef\x05t\xb8T\x12\x01\x98\xb8m\xf3\x8dEk^\x99\xf6\xde\x83\xb8\x96\x91\xc9' \
                b'\xd3\x98-\xb7\xc1\xaan\xe2\x93\x7f\x82\xaen\x08a9\xccZ(' \
                b'Ob\xee\xfc\x01\xd4k\xc4\xe7\x9f\x86\xee\xd5\xadH\x15\xf5]I\xe2f\xd2\xf4\x96/\x8c\xbc\xf1\x82[' \
                b'\x88\xffgbEU\x11\x91f\xe0\xcc\xcdan\xde\x8e\xfd\xe9\xcf\xa1P\x80F\x83\xf8\xdc\x01\xe8Zu\x06j-L\x951' \
                b'\xdb\xef\xc4\xde}?\xcc\xcf\x81*\xf1o\x07!\x9b\x05UP$\xa8\xaa\x8f\xf2 ' \
                b'\xf0\x82\x99\xd8~\xdd\x06#\xdc0\xed\xfd\x99n\x14 ' \
                b'x\xf8\xeae\x98\xce"T\xca\xd8\x9f<\x80\xb9}\'L\x95\x9b ' \
                b'\xeb\x9a\xb0m;\xb0\xf7<\x04\xd5\n\xa6\xbd\x80\\\xba\x11b\xf3\x06A\xb3\xc3g|\xc0\x1a\xfaOl\xeb\xbf' \
                b'\xd2\xa8\x98\x1dyg\x93\x85\x96n\x15\xde\xe4\x0b|\xb4\xffQ>\xfd\xf3\x1fq\xdd\xab\xd1\xe9j\x13z\xeb' \
                b'\xf7\xa1:\x05\x952f\xeb\x1d\xd8{\x1eBk3\xb8\xeen>{' \
                b'\xf2\t>\x18z\x18\x93\xcb/k2U\x8d\x05g\xadX\xf9\xae\x13\xe4\xfa\xa8\xad\xb8\xce(' \
                b'\x01=\xab\xbby\x7f\xff#\xb8\xb66\xd6\xec\xd8IZ\x9e\xc4\xde\xf3`3u>\xc5\xee\xda\x83\xd6fH\xbaVqj\xe4' \
                b'\x19>\x19z\x98\xf5kzP\x91f:[' \
                b'"\xe2UA\xe5z\x99\xd8>p<\xb1\xf2\xa5FT\x95\x15Pk-\xb3\x8d\x06\xef\x9f\xfc\x8c\xbe\xbd\xbf\xa4\xe7' \
                b'\xd6\x1d\xa4\x95\xeaB\xa1AUI:;\x98|\xe9y>\xd8\xbd\x8b\x8bz\xba\xc9g\xb3\x84\x15\x8d\xa5\xa0\x89\x88' \
                b'\xa4Q?u\x8av\x07\x15V\xc2\x00|\x08\xe42\x19\xd6\xf7\xf4p\xfc\xd1\x07A\x95\xee\x9b\xb6\x12\xe7\xe7' \
                b'\x9b\x0ee\xb3\x9c~q\x84\x0f\xf7=\xc0\xfa\xee.\xf2\xd9,' \
                b'>\x84\xb3\x0c\tHPE`\x95\x11\xc4\x82\xaed\xb5r\xec\xbd\'_(' \
                b'\xb0\xd6@e\xe4)\x94f\xba4F\xd4\x18*\x7f}\x9a\xb5\x1a(' \
                b'\x14\x8bx\xef\xcf\xf6zY\xa4j\x8d\xa2+\xcb\xb7\x1c\xea\x12|\xf94\xedW\xf7s\xd1/\x1e\'\xa6\rL>\x8f' \
                b'-\xb4\x13\xe7\xe6Y\xff\xc8~\x8a\x037\xe0O\x9fB\x92\xe4\xff\xe0\x9aa\x19\x1fc\x10\xce\x13\xa3u0]\xc1' \
                b'|\xfd\x1b\xd8=\x8f\x11\x93\x84\xa4\xbdHu|\x94\xca\xe8\xab$\x1dE\xa2\xb5\xd8\x87\x860\xdf\xbc\n*S' \
                b'\xcd3\xe7r\\\x84\x105\x984\xc6I+\x8bo\x9b%b\x0cT\xca\xc8\xd7.\xc3\r\xeeG\x93\x0c.\x97\xa7rh\x9c\xe3' \
                b'\xbb\xef\xe5\x83=\xbb\x98\x1a{' \
                b'\r\x97/\xa0\xc6\xe0\x1e~\x0c\xd9\xf8-\x98\x9a<k\x0c*\xa8\x15\xa1\x11c\xd9\xd4R\xff\xaek\xb6\xb1.q' \
                b'\x07\x1a\xf3\xc8\x15\xd7`\xf7<\x86f\x9a\xb0\xe9\x7f\xbc\xcd\xb1\xfb\xeebm!\xcf\xba\xce\x0e\x8e\xdd' \
                b'\xffc\xaao\xbe\x8e+\xb4\xa3\xc6aw\x0f!W\x0f\xc0\xfc|\xeb\xe27\x89\xaaN`.\xf5\xef\x99\xea\xdc\xfck' \
                b'!FDd90M\xb17l\xc1^p\x01\xae\xad\x8d\xe9\x7f\x1e\xe2\xe8}w\xd1\x97M(' \
                b'\xe6\xf3\xb4\xe7r\xac+\xe48\xf6\xc0\xddT\xdf~\x03\x97\xcba{' \
                b'z\xb07nmN\xa9%@\x11QU\xa5\xda\x98\x1f\x95g/\xbfd\xe3%\xab;\x0e\xf7\xe4s6\x8d\xdaR3"\x9c\x98,' \
                b'S\xdc=D\xae\xb7\x8fw\xef\xfe!\xbdYGWG\x07\xde{' \
                b'\x00\x9csT\xa7\xa7\xf9\xa8>\xc7\x97\x7f\xfd\x07\xd2\xa92S{\xef\xa3\xaf\xab\xb3\xb5\xcc(' \
                b'\xe0\x8ch\xb9>\xa7GNU\xae\x15\x80\xd1M\x1b^\xd9\xd8\xd3\xfd\x9d\xba\x8f\x11\xc1\x02\x881\xd4ju>N' \
                b'=\xd1Xz%\xd2\xd5\xd9\x89O\xd3e\x17\xdf9Gez\x9a\x13\x11$Fz\x13K{' \
                b'\xa1\x80.\x8e6%\xe4\x9c1\xff>U\x1e\x1bx\xe3\x9d\xcd\x06\xa0:77t\xb2V\x17g\xa5U\xc8\x18#\xc5\xf6\x02' \
                b'}\xb9,\xbdNZ\x91\xc9\xf2T\xe1C\xa0\xb3X\xa4\xd7Yz\xdb2t\xb6\xb7\x13[' \
                b'\xaf&\xb0Vt\xb2>+3\x8dt\x08Ps\xa0T\xb2\xdb\x0f\xbfw\xf0\xfd\xe9\x99g\xd2\xd4;+\xe2\x17o\xa6\x0f\x81' \
                b'\xf6L\x86\xce|\xfe\x9c\x13\x84%z\x1d\xf9\x1c\xc5l\x96tAO\x01+\xe2C\xea\xdd\xd1\xea\xcc\x8b[' \
                b'\x0f\xfdw\xe4@\xa9depa\xaf\xd9|\xcd\x865\x19\xab\x87/\xea(' \
                b'\xf6e\x93$D\xd5\xcf\xbd\xcb\x9cK\x8cH\x98\xf7\xde\x1e\xafTO\xce\xc7\xc6\x157\xbd\xf9\xee\x89\xbd' \
                b'\x8b\xad\xa4\x83\x18\xd9G|\xf9\xaa\xaf\\Yp\xc9\xab\x17\x16\xf3\xc5B6\xe3A\\l\xce\xc0\xcf%\xda\x04' \
                b'!\xa8\xaf\xcd\xa7nbf\xa6>\xa7\xfe\xe6\x9b\xc6\x8f\x8c\x1d(' \
                b'aw\x0e\x13\x9a\x9b\xd4>\xe2\x81R\xc9n9t\xe4\xef\xb5\xe0\xb7\x9c\x98\xaeMT\xea\xb3\xae\x11\xbc\xb7' \
                b'"\xd1,6\xc9y~\x0b\x11aEb#x?U\x9fu\x1f\xcf\xcc\x9c\x9cI\xe3\xb6&\xacdw\x0e\x13\x16K\xd0\x92\xc5M\xf9' \
                b'\xe0\xa6K\xbf\x94\x89\xfc\xae\xe8\xdc\xb6B&C\x928\xda\xac\r\xd6\x98\xe6\x9a\xbat\x11\x06\r1\xea' \
                b'\\\x086M=\xf5F\x83i\xef\x0f\xce[{\xd7\xcd\xaf\xbfs\xf4\xbc\x8b\xf0\x19(' \
                b'-oF\xaf\xbb\xac\xa4\x1a\xeeE\xa4\xbf\x988\x9c\xb5\x18#\x08\x8b\x11+1*>F\xa6\x1b)\no\t\xfa\xf8\xf5' \
                b'\xe3\xffyb\xa5\xad\xf3\x02a\xe1c\x06T\x16266\xb0\xe1\xdbi\xd0\xdbU\xb5?\xaa^\xacHg\xb3\x13\xb5j\xe0' \
                b'\x9852fq\x7f\xd94\xfe\xafW\x17"?\xef\xc7\xcc\xff\x00\xa0\xfes4\xa9\x85\t\xcd\x00\x00\x00\x00IEND' \
                b'\xaeB`\x82 '
    warning_img = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x1e\x00\x00\x00\x1b\x08\x06\x00\x00\x00k\xfd?\x11' \
                  b'\x00\x00\x05\x84IDATx\x9c\xb5\x96o\x8cTg\x15\xc6\x7f\xe7}\xef\x9d\xb9\xb3\xb3\xd3\x99\x1d\x98\x19' \
                  b'\xd6\x02v\x17,\xbb0\xcb\xaa\x90`\x1b\x15k#i\xb3\x9bRS5D[' \
                  b'\xad\x1a\x10\x9bliC\x0b\xb614$\xd2\xd6\xfe\xc3\xf2\r?\xf4\x83_l\x9a\x94\xaa1\xd1F\x8d\xd4\xc4' \
                  b'\xa61@\xb3e7\xd1\xc2B\xa1\x15\x0bm0\xbb\xec.\xb33\xf7}\x8f\x1ff\x16\xf6/X\xa5Orson\xdes\x9es\x9e' \
                  b'\xf3>\xf7\xbd\xf0\xd1`\x1b\xf7\x9b\x80w\x80Qcx\xb4\xf1\xce|\xc4\\\xff5\x04\xb0[' \
                  b'\xb6\x10\x02G\xd7\xac\x8c\xf4\xbb\x1bs\x1e\xd0\xa6\x90\xcf\xce(' \
                  b'\xec\x9a"\x00H\x04\xe6\x01\x11\xf4\xc8Km5=\xd3Uk[' \
                  b'\x1c\xaa\x08\x07\x8d\xf9x\x88\r`\xda\xdb\xd3E\xe0\xfc\xdd\xbdY\xa7\'\xca\xde\x9f(' \
                  b'\xeb\x81\xbd\x8bc@S)\xfb\xd5\xc6\xdakJnE\xc0Z\xf6g\xd2F\xcf\xbcvc\xcd\xbf\xbdJ\xe3\xfeN\xd5\x13e' \
                  b'\xf7\xc5\xb5M\x1ex\xbb\xef\xb6\xe5\xc9F\x91rMH\x01\xb2\xd9\xf03@\xfc\xf8\xb6b\xac\xefu\xf9\x89' \
                  b'#\x9dZy\xb3S\xddPY\x0f\xbf\xd4\x16\x1bA\x13\x81y\xa8\x11\x13\\\x13bc@\x84\x83\xcb\x96$\xb4r\xb43' \
                  b'\x8e\x07V\xaa\x0e\x95UOw\xa9\x0e\xaeT=\xd5\xe5\xbf\xb31\xe7\x80\xf3mm\xe9\x12\x8d\xd1\\)\xe9\xd5,' \
                  b'`\x01\x97L\xda\xaf\xab\xb2\xfe\x99\xedE\x97\xcc\x06\xd6Z\xf8\xeb\xeb\xa3\xfc\xf2\xc5\xf3\xfc\xeb' \
                  b'\x83\x18@\x9ex\xb0\xe03i\xd3r\xfa\xf4\xd8n\x11<\xff\x87\xdc\x02\x98\xde\xde\xd6&\xe0\xe4\x97\xd7' \
                  b'\xa5\xbd\x0e\x95\x9d?\xb6J\xb7\xdf\xbb@\x01\x05t\xd1\xc2@\x8f\xfez\x99\xea\xb9\xd5~\xf7}\x05\x07' \
                  b'\xd4\x8a-aW#\xfe\x7f\xdah\x81\x00\x89\x80]\x81\x15=\xfaJ{' \
                  b'M\x8f\x97U\xff\xbeJ?\xdd\x11\xa9\x08\x9a\x8a\x8c\x02\xfa\xca\xf3K\xd4\xbf\xdb\xa5\xa3G:\xe3O~"T' \
                  b'\x11^\xbd\x9a\xbd\xe6\x93\xda\x00\xae\xad5ZZ\x8d\xd9\xb1\xf9k9_^\x9b\xb6\xd5\x11\x07\x91p\xc3\xf5' \
                  b'!\xaa\x10\xc7\x8a\x08,*\x04\xc8EO:o\xed\x93\xdb\x8aN\x95\rQd{' \
                  b'\x007\x1f\xf9|\xc4b\x04=\xf5~\xe5\xa7\x0br6\xfd\x93\x07\x8a\xea\xc7\xbc\x88\x01\x8c\xb0 ' \
                  b'W\xcf\xa5\r\xc1\xb3i\x03F\x88\x87\x1d\x9b\xee\xca\xc9M\xdd)\x1d\x1fwO\xef\xdf\xb2&\xac\xaf\x98' \
                  b'=\xef\xb9\x88-\xe0\x9a\xd2\xc1\xe7\x9d\xb2i\xf7}\x05\x97_\x9c\xb0\xbe\xe2\x11\xa9\xa7(' \
                  b'\xe6\xebn\xf1^I&\x85L\xb3\x01\xaf\xf5B\xac\x98\xe7\x1e.y\xa0\xf3\xfe\x17\xde\xdc\n\xf8\xb9\xba' \
                  b'\x9e\xb3cU\xcc\xe8h\xbc\xb7\xfc\xa9$?\xfcv\x1e7\xec\xb0\xc1\xe5\xa2/\x11+\xa4S\x86\xe6&\x03\x0e' \
                  b'\x02+\xb8\x11\xc7\xe7\xd6gd\xd3\xedY?\x11\xfb]\x1d\x1d\x99\x05\r\xf2i\\3\x89-\xe0\xa2\x84\xb9' \
                  b'\x17X\xfb\xb3\x1d%g"cqzY+\x85b\xfer\x03\x99\xb4!\x9d\xaaw\x0c ' \
                  b'"\xe8Eo\x9e\xda^\xf4M)\xb3\xf0\xd8\xb1\x0b\xbb\xe6\xb2\xd7Tb\x01\xb4\xbb;\x9b\x9b\xa8\xf9=\x1bo' \
                  b'\xc9\xf8[7\\\'n\xd8a\xad\\Z\x80W\n\xf9\xa0.;\x90\xcbX\xc2\xa4\x80\x82\x08\x18\x03n\xdc\xb3\xa4' \
                  b'#\xb2\x0f\xde\x93\xf7\xce\xb1\xb5\xd4\x92\xe8\x9c\xd9\xf5Tb#\x82\x1f\x18\x18\xfeq\x94\x94E\xcf' \
                  b'\xed,y\xad\xaa\x11\x99R\xa8\x08xh\xc9\x18T\xeb\xd26E\x06B\x83\xf7Sd\xb3\x82\x1fq\xf2\xc8\xd6\x85z' \
                  b'})H\x9c\xfdw\xf5)c\xa6o23\xe5\xee[\xf3\x89\x15\xce\xd1\xb7\xed[' \
                  b'y\xdf^NY?\xe61SJ3\x02ZU\x96.Np]\xb3!vJ\xd7\x8dI\x08\x05\xaf:\xbd\xbe\xaa\x92.\x84vO_\xd1\xa9\xd2' \
                  b'\x9bJ\xd9\xaf0\xc5^\x93\x15Xcp\xaa\xfc\xb6\xb5\x10\xf4\xfc\xe3\xf7\xcb]Sd\xac8\x90\x19FP\x0f\x92' \
                  b'\x12N\x9d\xac2pl\x82\x9e/5\xa3\x8d\xd9\xcf\xf4\x8cS\xb0\x91\xb8\xb5w\x0e\xd9\xc3\x83\x95\xb7\xfe' \
                  b'\xfc\x18kn\xd9\x8d\x07\xd40\xb9\xa1"{' \
                  b'\xbb*=On+\xba\xe6Bh\xb5\xaa\xb3H\xeb%\x82\xaf)\x7f9<\xce\xa1\xc1\x8b\x1c\x1a\xac ' \
                  b'IS\x9f\xe0Lx\x85@\xec\xde\x87K\x0eX}\xdb\x1e\xf3}\x1a\xf6\x12\xc0\xee\xdf\x82\xf9\xc1\xcf\xe9_' \
                  b'\xb7:\xd5\xf1\xc6\xcb\xed\xea*j\xec\x1c\xa4\xce)6\x17\xf0\xf4\xbes\xecx\xf6,' \
                  b'\x00\xa9\xc8\xd0\xff\xabv\x96\xb7\'\xd1\x8aN\x1b\xcd\xa5\x98\x96\xc0\xdf\xf5\xbdw8\xf0\xc7\x0b' \
                  b'\x1fvwgW\xf4\xf7\x0f\x8f\x18\xc0\xf5\xbd`\xee\x17\xa1\xf3\xf9\x9d%O ' \
                  b'f\xd2\x1a\xf3\xe1\x0f\xaf\x8fb\rd\x9b\r\x17+\x9e\xb7\x06+Hd\xa6\xcdy\x12"\x82Nx\xf3\xccC%\x1f' \
                  b'%\xa5800\xfc#\x11\xbcio\x8d\x96Vc\xff\xd8\xdd\xbdY\xbf\xee\x0b\x19\xe3F.\xdbgv\x96\xba|\x9b\xbf' \
                  b'\xd1\x82W\x18\x1e\xf5\xac\xb8!\xc1\xfa\x9b\xd3\xe8\x98\xc7\x9a\xd9q\xc6\x80\x1f\xf3\xb4\x95S\xb6' \
                  b'\xef\x9by\xef\x1c}\xad\xf9\xc4\n\x11\xe1\x17\x99&s\xcf\xc0o\x96\xb9E\xad\xa1\xd5\x89\xd9rM\x85' \
                  b'*\x84)\xc3\x1b\x87\xc69\xfen\x95\r7\xa7)\x14B\xe2\x8aG\xe6\x89S\x05\r\x84\xd1\x0b\xcew\xdd1d\xce' \
                  b'|\x10\xffN\x80\xf8\x91\xcd\x0b\xe5\xf1}K\x0cgk\x8d\xc3\xf0*\xf0@\xda@(' \
                  b'0\xe6!\x9ecK\xcfD\xacP\nyb\xe7?\xfd\xa3\xfb\xce\x99\x00\xf8\xf0\xe0\xdf\xc6J\xcf\xeey\x1f\x99\xa8' \
                  b'\x1f\x04W\xca\xa1\x00\x02\xde\xd5\x9fM\xe3k\xa5W\xe0\x9e\xfck ' \
                  b'\x14=\xf0\xa7\x11\x03\xbc\x07\xd0\x03\x9c\x04\xaa@\r\x88?\xa6\xab\xd6\xe08\x0e\xdc\xfa\x1fy\x07E' \
                  b'\x99v\xc8\xafg\x00\x00\x00\x00IEND\xaeB`\x82 '
    tab_dados = sg.Tab('Dados', [
        [sg.Column([[
            sg.Column([
                [sg.VPush()],
                [sg.Checkbox(key=f"-{group}-CHECKBOX-",
                             text=Controller.data_groups[group]['nome'],
                             size=(22, 10))],
                [sg.VPush()]
            ], expand_x=True, expand_y=True),
            sg.Column([
                [sg.Text(text=progress[1], visible=False, key=f'-{group}-{progress[0]}-TEXT-'),
                 sg.Image(data=bar_striped, size=(30, 25), visible=False, expand_x=True, expand_y=False,
                          key=f'-{group}-{progress[0]}-INFINITE-'),
                 sg.ProgressBar(max_value=100, visible=False, size=(30, 25), expand_x=True, expand_y=False,
                                key=f'-{group}-{progress[0]}-PROGRESS-')]
                for progress in Controller.data_groups[group]['progressos']
            ], element_justification='left', expand_x=True, expand_y=True),
            sg.Column([[
                sg.Image(source=error_img, size=(30, 30), visible=False, key=f'-{group}-{progress[0]}-ERROR-'),
                sg.Image(source=check_img, size=(30, 30), visible=False, key=f'-{group}-{progress[0]}-OK-'),
                sg.Image(source=warning_img, size=(30, 30), visible=False, key=f'-{group}-{progress[0]}-STOP-')
            ] for progress in Controller.data_groups[group]['progressos']])
        ] for group in groups_part
        ], expand_x=True, expand_y=True)
            for groups_part in
            np.array_split(sorted(Controller.data_groups.keys()), 2)
        ],
        [sg.Push(), sg.Button("Inicia Extração de Dados", key='-DATA-EXTRACTION-'), sg.Push()],
    ])
    tab_analise = sg.Tab('Análise', [
        [
            sg.Column([
                [sg.Text('Verificações pré-cadastradas')],
                [sg.Listbox(values=[],
                            auto_size_text=True, expand_y=True,
                            enable_events=True, key='-ANALYSIS-CHOSEN-')],
            ], expand_y=True),
            sg.Column([
                [sg.Text("Consulta em SQL:", key='query_title')],
                [sg.Multiline(expand_y=True, expand_x=True,
                              key='-SQL-', auto_size_text=True)],
                [sg.Push(),
                 sg.Button("Executa Consulta", key='-QUERY-'),
                 sg.Push()]
            ], expand_x=True, expand_y=True)
        ]
    ])
    tab_notificacoes = sg.Tab('Notificações', [
        [
            sg.Column([
                [sg.Text('Notificações não enviadas')],
                [sg.Listbox(values=[], size=(40, 15),
                            auto_size_text=True, expand_y=True,
                            enable_events=True, key='-NOTIFICATION-CHOSEN-')]
            ], expand_y=True),
            sg.Column([
                [sg.TabGroup([
                    [
                        sg.Tab('Visualização',
                               [[sg.Multiline(key='-NOTIFICATION-PREVIEW-', disabled=True,
                                              expand_y=True, expand_x=True, )]], key='-PREVIEW-TAB-'),
                        sg.Tab('Edição', [
                            [sg.Text('Título:'),
                             sg.InputText(key='-NOTIFICATION-EDIT-TITLE-', expand_x=True, disabled=True)],
                            [sg.Multiline(key='-NOTIFICATION-EDIT-', expand_x=True, expand_y=True, auto_size_text=True,
                                          disabled=True)]
                        ]),
                    ]
                ], expand_y=True, expand_x=True, enable_events=True, key='-NOTIFICATION-TAB-')],
                [
                    sg.Push(),
                    sg.Button('Visualizar Anexos', key='-NOTIFICATION-ATTACHMENTS-', disabled=True),
                    sg.Button('Enviar Notificação', key='-NOTIFICATION-SEND-', disabled=True),
                    sg.Button('Envio Manual', key='-NOTIFICATION-MANUAL-SEND-', disabled=True),
                    sg.Push()
                ]
            ], expand_y=True, expand_x=True)
        ]
    ])
    tab_aiim = sg.Tab('AIIM', [
        [
            sg.Column([
                [sg.Text('Possíveis infrações')],
                [sg.Listbox(values=[], size=(40, 15),
                            auto_size_text=True, expand_y=True,
                            enable_events=True, key='-INFRACTION-CHOSEN-')]
            ], expand_y=True, justification='left'),
            sg.Frame(layout=[
                [sg.Column([[sg.Multiline("AIIM item data", key='-AIIM-ITEM-DATA-',
                                          expand_x=True, expand_y=True,
                                          auto_size_text=True, visible=False)]], expand_x=True, expand_y=True)],
                [sg.Column([[sg.Button("Cria Item", size=(10, 1), key='-AIIM-CREATE-ITEM-', visible=False)]]),
                 sg.Column([[sg.Button("Atualiza DDF atual", size=(15, 1), key='-AIIM-UPDATE-ITEM-', visible=False)]]),
                 sg.Column([[sg.Button("Atualiza Número Item", size=(15, 1), key='-AIIM-UPDATE-ITEM-NUMBER-',
                                       visible=False)]]),
                 sg.Column([[sg.Button("Resposta Notificação", size=(15, 1), key='-AIIM-UPDATE-NOTIF-ANSWER-',
                                       visible=False)]]),
                 sg.Column([[sg.Button("Remove Item", size=(10, 1), key='-AIIM-REMOVE-ITEM-', visible=False)]]),
                 sg.Column([[sg.Button("Gera Anexo", size=(10, 1), key='-AIIM-ITEM-PROOFS-', visible=False)]])],
            ], title='AIIM', expand_x=True, element_justification='center', expand_y=True, key='-AIIM-FRAME-'),
        ]
    ])
    # Principal
    return [
        [sg.Menu(menu_layout('SEM_AUDITORIA'), tearoff=False, key='-MENU-')],
        [sg.Text(key='pasta')],
        [sg.Text(key='osf')],
        [sg.Text(key='empresa')],
        [sg.Text(key='endereco')],
        [sg.Text(key='periodo')],
        [sg.T('')],
        [
            sg.TabGroup(
                [
                    [
                        tab_dados, tab_analise, tab_notificacoes, tab_aiim
                    ]
                ],
                expand_y=True, expand_x=True, enable_events=True, key='-MAIN-TAB-')
        ],
    ]


def menu_layout(tipo_menu: str):
    match tipo_menu:
        case 'SEM_AUDITORIA':
            return [
                ['&Arquivo', ['Criar Auditoria::-MENU-CREATE-AUDIT-',
                              'Abrir Auditoria::-MENU-OPEN-AUDIT-',
                              'Sair::-MENU-EXIT-']],
                ['&Editar', ['Propriedades::-MENU-PROPERTIES-', 'Cria Análise::-MENU-CREATE-ANALYSIS-']],
                ['A&juda', ['Sobre::-MENU-ABOUT-']]
            ]
        case 'AUDITORIA_SEM_AIIM':
            return [
                ['&Arquivo', ['Criar Auditoria::-MENU-CREATE-AUDIT-',
                              'Abrir Auditoria::-MENU-OPEN-AUDIT-',
                              'Sair::-MENU-EXIT-']],
                ['&Editar', ['Propriedades::-MENU-PROPERTIES-', 'Cria Análise::-MENU-CREATE-ANALYSIS-',
                             'Atualizar Dados da Fiscalizada::-MENU-UPDATE-OSF-',
                             'Recarregar Planilha::-MENU-RELOAD-SHEET-']],
                ['E&FD', ['Imprimir LRE::-MENU-PRINT-LRE-',
                          'Imprimir LRS::-MENU-PRINT-LRS-',
                          'Imprimir LRI::-MENU-PRINT-LRI-',
                          'Imprimir LRAICMS::-MENU-PRINT-LRAICMS-']],
                ['A&IIM', ['Cria AIIM (gera número e AIIM2003)::-MENU-CREATE-AIIM-']],
                ['A&juda', ['Sobre::-MENU-ABOUT-']]
            ]
        case 'AUDITORIA_COM_AIIM':
            recibo_key = 'Envia Recibo de Arquivos Digitais::-MENU-AIIM-RECEIPT-'
            aiim_submenu = ['Gera Relato e Quadros 1 a 3::-MENU-AIIM-REPORTS-',
                            'Atualiza Relatório Circunstanciado::-MENU-AIIM-CUSTOM-REPORT-',
                            'Gera Provas Gerais::-MENU-AIIM-GENERAL-PROOFS-',
                            'Atualiza Quadro de Operações::-MENU-AIIM-OPERATIONS-',
                            'Gera Arquivo Backup AIIM2003::-MENU-AIIM-EXPORT-',
                            'Gera Arquivo Transmissão AIIM2003::-MENU-AIIM-UPLOAD-']
            if not get_current_audit().is_aiim_open:
                aiim_submenu = ['!' + item for item in aiim_submenu]
                aiim_submenu.append('Reabre AIIM2003::-MENU-AIIM-REOPEN-')
            if get_current_audit().receipt_digital_files:
                recibo_key = '!' + recibo_key
            aiim_submenu.extend(['---', recibo_key])
            return [
                ['&Arquivo', ['Criar Auditoria::-MENU-CREATE-AUDIT-',
                              'Abrir Auditoria::-MENU-OPEN-AUDIT-',
                              'Sair::-MENU-EXIT-']],
                ['&Editar', ['Propriedades::-MENU-PROPERTIES-', 'Cria Análise::-MENU-CREATE-ANALYSIS-',
                             'Atualizar Dados da Fiscalizada::-MENU-UPDATE-OSF-',
                             'Recarregar Planilha::-MENU-RELOAD-SHEET-']],
                ['E&FD', ['Imprimir LRE::-MENU-PRINT-LRE-',
                          'Imprimir LRS::-MENU-PRINT-LRS-',
                          'Imprimir LRI::-MENU-PRINT-LRI-',
                          'Imprimir LRAICMS::-MENU-PRINT-LRAICMS-']],
                ['A&IIM', aiim_submenu],
                ['A&juda', ['Sobre::-MENU-ABOUT-']]
            ]
        case unknown_command:
            raise Exception(f'Menu inválido: {unknown_command}')


# ATENCAO: Hack no SimplePyGUI acessando o TKinter
# depende completamente do layout criado em window_layout()
# serve pra alinhar melhor os itens dentro das Tab
def window_layout_fix():
    analysis_list = window.Rows[7][0].Rows[0][1].Rows[0][0].Widget
    query_column = window.Rows[7][0].Rows[0][1].Rows[0][1].Widget
    info = analysis_list.pack_info()
    info.update({'expand': 0})
    analysis_list.pack(**info, before=query_column)

    notification_list = window.Rows[7][0].Rows[0][2].Rows[0][0].Widget
    notification_edit_tab = window.Rows[7][0].Rows[0][2].Rows[0][1].Widget
    info = notification_list.pack_info()
    info.update({'expand': 0})
    notification_list.pack(**info, before=notification_edit_tab)

    aiim_list = window.Rows[7][0].Rows[0][3].Rows[0][0].Widget
    aiim_frame = window.Rows[7][0].Rows[0][3].Rows[0][1].Widget
    info = aiim_list.pack_info()
    info.update({'expand': 0})
    aiim_list.pack(**info, before=aiim_frame)


def data_extraction_progress_update(evento_progresso: str, tipo_progresso: str):
    if tipo_progresso not in extracoes.keys():
        extracoes[tipo_progresso] = {'rodando': 0, 'total': 0, 'finalizados': 0, 'ignore': False}
    dados_progresso = extracoes[tipo_progresso]

    window[f'-{tipo_progresso}-TEXT-'].update(visible=True)
    if evento_progresso == 'BEGIN':
        window[f'-{tipo_progresso}-TEXT-'].update(visible=True)
        window[f'-{tipo_progresso}-OK-'].update(visible=False)
        window[f'-{tipo_progresso}-ERROR-'].update(visible=False)
        window[f'-{tipo_progresso}-STOP-'].update(visible=False)
        dados_progresso['rodando'] += 1
        if dados_progresso['total'] == 0:
            window[f'-{tipo_progresso}-INFINITE-'].update(visible=True)
    elif evento_progresso == 'END':
        dados_progresso['finalizados'] += 1
        if dados_progresso['total'] > 0:
            if dados_progresso['finalizados'] >= dados_progresso['total']:
                window[f'-{tipo_progresso}-PROGRESS-'].update(visible=False)
                if not window[f'-{tipo_progresso}-ERROR-'].visible \
                        and not window[f'-{tipo_progresso}-STOP-'].visible:
                    window[f'-{tipo_progresso}-OK-'].update(visible=True)
            else:
                window[f'-{tipo_progresso}-PROGRESS-'].update(
                    current_count=dados_progresso['finalizados'],
                    max=dados_progresso['total'])
        else:
            window[f'-{tipo_progresso}-INFINITE-'].update(visible=False)
            window[f'-{tipo_progresso}-OK-'].update(visible=True)
    elif evento_progresso == 'FAILURE':
        window[f'-{tipo_progresso}-ERROR-'].update(visible=True)
        window[f'-{tipo_progresso}-STOP-'].update(visible=False)
        window[f'-{tipo_progresso}-OK-'].update(visible=False)
        window[f'-{tipo_progresso}-INFINITE-'].update(visible=False)
        window[f'-{tipo_progresso}-PROGRESS-'].update(visible=False)
    elif evento_progresso == 'STOP':
        window[f'-{tipo_progresso}-STOP-'].update(visible=True)
        window[f'-{tipo_progresso}-OK-'].update(visible=False)
        window[f'-{tipo_progresso}-ERROR-'].update(visible=False)
        window[f'-{tipo_progresso}-INFINITE-'].update(visible=False)
        window[f'-{tipo_progresso}-PROGRESS-'].update(visible=False)
    elif evento_progresso.startswith('TOTAL'):
        total = int(evento_progresso[5:])
        if total == 0:
            window[f'-{tipo_progresso}-OK-'].update(visible=True)
        else:
            dados_progresso['total'] += total
            window[f'-{tipo_progresso}-OK-'].update(visible=False)
            window[f'-{tipo_progresso}-ERROR-'].update(visible=False)
            window[f'-{tipo_progresso}-STOP-'].update(visible=False)
            window[f'-{tipo_progresso}-INFINITE-'].update(visible=False)
            window[f'-{tipo_progresso}-PROGRESS-'].update(
                current_count=dados_progresso['finalizados'],
                max=dados_progresso['total'],
                visible=True
            )


def generate_release():
    PyInstaller.__main__.run([
        __file__,
        '--onedir', '--nowindowed', '--noconfirm',
        f'--name={GeneralFunctions.project_name}',
        f'--icon=resources/ghost.ico',
        '--add-data=resources;resources',
        '--add-data=mysqldump;mysqldump',
        '--add-data=wkhtmltopdf;wkhtmltopdf',
        '--add-data=efd-pva-inspector;efd-pva-inspector',
        '--add-data=venv/Lib/site-packages/autoit/lib/*;autoit/lib',
        '--add-binary=venv/share/py4j/*;share/py4j',
        '--hidden-import=py4j.java_collections',
        '--hidden-import=AiimProofGenerator',
        f'--splash={InitialConfigurationWizard.splash_image_path()}'
    ])


if __name__ == "__main__":
    if len(sys.argv) > 0 and sys.argv[-1].endswith('release'):
        generate_release()
        sys.exit()

    try:
        import pyi_splash
        while not pyi_splash.is_alive():
            GeneralFunctions.logger.debug('Esperando splash screen ficar habilitada')
            time.sleep(1)
        pyi_splash.update_text(f'{GeneralFunctions.project_name} v{GeneralFunctions.project_version}')
        GeneralFunctions.logger.debug('Realizado update da splash screen')
    except ModuleNotFoundError:
        pass
    except Exception as e:
        GeneralFunctions.logger.exception('Falha ao fazer update na splashscreen')
        pass

    # tenta excluir diretorio tmp no início
    GeneralFunctions.clean_tmp_folder()

    sg.theme('SystemDefaultForReal')
    sg.set_options(ttk_theme=sg.THEME_WINNATIVE)

    if not GeneralConfiguration.get():
        InitialConfigurationWizard.create_config_file()

    # Criar janela
    window = sg.Window(GeneralFunctions.project_name, window_layout(), size=(1024, 768),
                       resizable=True, finalize=True,
                       enable_close_attempted_event=True)
    window.set_min_size((800, 500))
    window_layout_fix()
    refresh_data_tab()

    try:
        import pyi_splash
        pyi_splash.close()
        GeneralFunctions.logger.debug('Fechada janela splash')
    except ModuleNotFoundError:
        pass
    except Exception as e:
        GeneralFunctions.logger.exception('Falha ao fechar splashscreen')
        pass

    aiims = []
    extracoes = {}
    log_window: LogWindow = None
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        w, event, values = sg.read_all_windows(timeout=100)
        if isinstance(w, LogWindow) or event == '-LOG-WINDOW-EVENT-':
            log_window = w
            w.handle_event(event, values)
            if event == sg.WINDOW_CLOSED:
                clear_data_tab()
            continue
        if isinstance(w, AnalysisWizardWindow):
            w.handle_event(event, values)
            if event == sg.WINDOW_CLOSED:
                w.close()
                refresh_analysis_tab()
            continue
        elif event == sg.TIMEOUT_EVENT:
            if log_window:
                log_window.handle_event(event, values)
            update_gifs()
        # eventos da janela principal
        elif (event == sg.WINDOW_CLOSE_ATTEMPTED_EVENT
              or (event != sg.WINDOW_CLOSED and event.endswith('-MENU-EXIT-'))) and \
                GUIFunctions.popup_sim_nao('Deseja realmente sair?') == 'Sim':
            break
        elif event == sg.WIN_CLOSED or event == 'Cancel':  # if user closes window or clicks cancel
            break
        elif event == '-MAIN-TAB-':
            if values[event] == 'Dados':
                refresh_data_tab()
            if values[event] == 'Análise':
                refresh_analysis_tab()
            if values[event] == 'Notificações':
                refresh_notifications_tab()
            if values[event] == 'AIIM':
                refresh_aiim_tab()
        elif event.endswith('-MENU-CREATE-AUDIT-'):
            folder = sg.popup_get_folder('Escolha a pasta da nova auditoria', 'Criar auditoria',
                                         history_setting_filename=str(GeneralFunctions.get_folders_history_json_path()),
                                         no_window=True)
            if folder:
                create_audit(Path(folder))
        elif event.endswith('-MENU-OPEN-AUDIT-'):
            folder = sg.popup_get_folder('Escolha a pasta da auditoria', 'Abrir auditoria',
                                         history=True,
                                         history_setting_filename=str(GeneralFunctions.get_folders_history_json_path()),
                                         modal=True)
            if folder:
                try:
                    open_audit(Path(folder))
                except ConfigFileDecoderException as e:
                    GUIFunctions.popup_erro(str(e), titulo='Falha na abertura da auditoria')
        elif event == '-DATA-EXTRACTION-':
            grupos = [k[1:-10] for k, v in values.items() if k.endswith('-CHECKBOX-') and v]
            LogWindow(populate_database, 'Levantamento EFD e Launchpad', grupos, extracoes)
        elif event == '-DATA-EXTRACTION-STATUS-':
            # eventos lançados pelo processo de extração, para atualizar tela
            tipo = values[event][0]
            evento = values[event][1]
            data_extraction_progress_update(evento, tipo)
        elif event == '-ANALYSIS-CHOSEN-':
            if len(values[event]) > 0:
                analysis_chosen(values[event][0])
            else:
                refresh_analysis_tab()
        elif event == '-NEW-ANALYSIS-':
            AnalysisWizardWindow()
        elif event == '-QUERY-':
            run_query(values['-ANALYSIS-CHOSEN-'][0])
        elif event == '-NOTIFICATION-TAB-':
            if values[event] == '-PREVIEW-TAB-':
                if len(values['-NOTIFICATION-CHOSEN-']) > 0:
                    notification_prettyprint(
                        values['-NOTIFICATION-CHOSEN-'][0].notificacao_titulo(values['-NOTIFICATION-EDIT-TITLE-']),
                        values['-NOTIFICATION-CHOSEN-'][0].notificacao_corpo(values['-NOTIFICATION-EDIT-'])
                    )
                else:
                    window['-NOTIFICATION-PREVIEW-'].update('')
        elif event == '-NOTIFICATION-CHOSEN-':
            if len(values[event]) > 0:
                notification_chosen(values[event][0])
            else:
                verification_chosen_for_notification(None)
        elif event == '-NOTIFICATION-ATTACHMENTS-':
            notification_show_attachments(values['-NOTIFICATION-CHOSEN-'][0])
        elif event == '-NOTIFICATION-SEND-':
            notification_send(values['-NOTIFICATION-CHOSEN-'][0],
                              values['-NOTIFICATION-EDIT-TITLE-'],
                              values['-NOTIFICATION-EDIT-'])
        elif event == '-NOTIFICATION-MANUAL-SEND-':
            notification_manual_send(values['-NOTIFICATION-CHOSEN-'][0])
        elif event == '-INFRACTION-CHOSEN-':
            if len(values[event]) > 0:
                verification_chosen_for_infraction(values[event][0])
        elif event == '-MENU-AIIM-CREATE-':
            aiims = WaitWindow.open_wait_window(Controller.get_aiims_for_osf, '')
            if aiims is not None:
                if len(aiims) == 0:
                    WaitWindow.open_wait_window(Controller.create_aiim, 'criar AIIM')
                else:
                    if len(aiims) == 1:
                        mensagem = 'Achei um AIIM aberto para esta OSF. Deseja utilizar esse número, ou criar um ' \
                                   'novo? '
                    else:
                        mensagem = 'Achei AIIMs abertos para esta OSF. Deseja utilizar um deles, ou criar um novo?'
                    layout_popup = [[sg.Text(mensagem, auto_size_text=True)], []]
                    for auto in aiims:
                        layout_popup[1].append(sg.Button(auto))
                    layout_popup[1].append(sg.Button('Novo AIIM'))
                    layout_popup[1].append(sg.Button('Cancelar'))
                    popup = sg.Window(title="Número AIIM", layout=layout_popup, auto_size_text=True,
                                      grab_anywhere=False, finalize=True, modal=True, no_titlebar=False,
                                      element_justification='c')
                    evento, valores = popup.read()
                    popup.close()
                    del popup
                    if evento == 'Novo AIIM':
                        WaitWindow.open_wait_window(Controller.create_aiim, 'criar AIIM')
                    else:
                        aiim_existing = evento
                        WaitWindow.open_wait_window(Controller.link_aiim_to_audit, 'cadastrar AIIM no AIIM2003',
                                                    aiim_existing)
            refresh_aiim_tab()
        elif event == '-AIIM-CREATE-ITEM-':
            aiim_item = values['-INFRACTION-CHOSEN-'][0]
            WaitWindow.open_wait_window(Controller.create_aiim_item, 'Criar Item no AIIM', aiim_item)
            refresh_aiim_tab()
            verification_chosen_for_infraction(aiim_item)
        elif event == '-AIIM-UPDATE-ITEM-':
            WaitWindow.open_wait_window(Controller.cria_ddf, 'Atualizar DDF de Item no AIIM',
                                        values['-INFRACTION-CHOSEN-'][0])
            verification_chosen_for_infraction(values['-INFRACTION-CHOSEN-'][0])
        elif event == '-AIIM-UPDATE-ITEM-NUMBER-':
            resposta = sg.popup_get_text('Digite o número correto atual do item no AIIM2003',
                                         title='Alteração Manual de Item')
            if resposta and re.match(r'^\d+$', resposta):
                Controller.update_aiim_item_number(values['-INFRACTION-CHOSEN-'][0], int(resposta))
                verification_chosen_for_infraction(values['-INFRACTION-CHOSEN-'][0])
        elif event == '-AIIM-UPDATE-NOTIF-ANSWER-':
            resposta = sg.popup_get_text('Digite o expediente Sem Papel com resposta à notificação',
                                         title='Resposta à Notificação')
            try:
                aiim_item: AiimItem = values['-INFRACTION-CHOSEN-'][0]
                Controller.update_aiim_item_notification_response(aiim_item, resposta)
                verification_chosen_for_infraction(aiim_item)
            except ValueError:
                GUIFunctions.popup_erro('Formato inválido para número de expediente Sem Papel '
                                        '(deveria ser algo como SFP-EXP-<ano>/<numero>)')
        elif event == '-AIIM-REMOVE-ITEM-':
            if GUIFunctions.popup_sim_nao('Deseja realmente remover este item da lista de infrações e do AIIM?',
                                          titulo='Alerta') == 'Sim':
                WaitWindow.open_wait_window(Controller.remove_aiim_item, 'Remover Item do AIIM',
                                            values['-INFRACTION-CHOSEN-'][0])
                refresh_aiim_tab()
        elif event == '-AIIM-ITEM-PROOFS-':
            WaitWindow.open_wait_window(Controller.aiim_item_cria_anexo, 'Criar anexo para Item no AIIM',
                                        values['-INFRACTION-CHOSEN-'][0])
        elif event.endswith('-MENU-UPDATE-OSF-'):
            WaitWindow.open_wait_window(Controller.update_dados_osf, 'Atualizar Dados do Contribuinte',
                                        get_current_audit().osf)
            __refresh_tabs(get_current_audit().path())
        elif event.endswith('-MENU-RELOAD-SHEET-'):
            get_current_audit().clear_cache()
            __refresh_tabs(get_current_audit().path())
        elif event.endswith('-MENU-PROPERTIES-'):
            GeneralConfiguration.configuration_window()
        elif event.endswith('-MENU-PRINT-LRE-'):
            print_efd('lre')
        elif event.endswith('-MENU-PRINT-LRS-'):
            print_efd('lrs')
        elif event.endswith('-MENU-PRINT-LRI-'):
            print_efd('lri')
        elif event.endswith('-MENU-PRINT-LRAICMS-'):
            print_efd('lraicms')
        elif event.endswith('-MENU-AIIM-REPORTS-'):
            WaitWindow.open_wait_window(Controller.print_aiim_reports, 'Gerar Relatórios do AIIM')
        elif event.endswith('-MENU-AIIM-CUSTOM-REPORT-'):
            WaitWindow.open_wait_window(Controller.generate_custom_report, 'Gerar Relatório Circunstanciado')
        elif event.endswith('-MENU-AIIM-GENERAL-PROOFS-'):
            WaitWindow.open_wait_window(Controller.generate_general_proofs_attachment, 'Gerar Provas Gerais')
        elif event.endswith('-MENU-AIIM-OPERATIONS-'):
            WaitWindow.open_wait_window(Controller.declare_operations_in_aiim, 'Cadastrar Operações no AIIM2003')
        elif event.endswith('-MENU-AIIM-RECEIPT-'):
            WaitWindow.open_wait_window(Controller.send_notification_with_files_digital_receipt, 'Enviar Recibo')
            refresh_aiim_tab()
        elif event.endswith('-MENU-AIIM-EXPORT-'):
            WaitWindow.open_wait_window(Controller.export_aiim, 'Exportar AIIM')
        elif event.endswith('-MENU-AIIM-REOPEN-'):
            WaitWindow.open_wait_window(Controller.reopen_aiim, 'Reabrir AIIM')
            refresh_aiim_tab()
        elif event.endswith('-MENU-AIIM-UPLOAD-'):
            WaitWindow.open_wait_window(Controller.upload_aiim, 'Transmitir AIIM')
        elif event.endswith('-MENU-ABOUT-'):
            sg.Window(GeneralFunctions.project_name,
                      [
                          [sg.Image(InitialConfigurationWizard.get_splash_image())],
                          [sg.T(f'{GeneralFunctions.project_name} versão {GeneralFunctions.project_version}')],
                          [sg.OK(s=10)]], element_justification='c').read(close=True)
    window.close()

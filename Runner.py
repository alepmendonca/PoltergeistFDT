import datetime
import os
import re
import subprocess
import sys
import threading
from json import JSONDecodeError
from zipfile import BadZipFile

import PyInstaller.__main__
import PySimpleGUI as sg
import numpy as np

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
extracoes: dict


def refresh_menu():
    window['-MENU-'].update(menu_definition=menu_layout('AUDITORIA_COM_AIIM' if get_current_audit().aiim_number
                                                        else 'AUDITORIA_SEM_AIIM'))


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
                                f'do sistema: {str(e)}', exception=e)
    window['-SQL-'].update(value='', disabled=True)
    window['-QUERY-'].update(disabled=True)


def refresh_notifications_tab():
    window['-NOTIFICATION-CHOSEN-'].update(Controller.get_possible_infractions_osf())
    verification_chosen_for_notification()
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
                                    'Conserte o arquivo no Excel e reabra a fiscalização.', exception=e)
            return
        except JSONDecodeError as ex:
            GUIFunctions.popup_erro(f'Falha na abertura do arquivo dados_auditoria.json da fiscalizada. Verifique se '
                                    f'não foi feita nenhuma alteração manual no arquivo no seguinte trecho: '
                                    f'{str(ex)}', exception=ex)
            return

        window['pasta'].update(f"Pasta inicial da fiscalização: {get_current_audit().path()}")
        window['osf'].update(f'OSF: {get_current_audit().osf}')
        window['empresa'].update(f'{get_current_audit().empresa} - CNPJ {get_current_audit().cnpj} - '
                                 f'IE {get_current_audit().ie if get_current_audit() else "Não Informada"} - '
                                 f'Situação {get_current_audit().situacao} '
                                 f'desde {get_current_audit().inicio_situacao.strftime("%d/%m/%Y")}')
        window['endereco'].update(f'Endereço: {get_current_audit().endereco_completo()}')
        window['periodo'].update(f'Período de Fiscalização: '
                                 f'{get_current_audit().inicio_auditoria.strftime("%m/%Y")} '
                                 f'a {get_current_audit().fim_auditoria.strftime("%m/%Y")}')
        refresh_menu()
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
                          element_justification='c', icon=GUIFunctions.app_icon)
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
        retorno = WaitWindow.open_wait_window(Controller.update_dados_osf, 'Carregar dados da OSF', numosf)
        if retorno is None:
            __clean_tabs()
            return
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
            GUIFunctions.popup_sim_nao('Não existe auditoria nesta pasta. Deseja criá-la?',
                                       'Auditoria inexistente'):
        create_audit(pasta)

    __clean_tabs()
    set_audit(pasta)
    __refresh_tabs(pasta)


def print_efd(book: str):
    referencias = WaitWindow.open_wait_window(Controller.efd_references_imported_PVA, '')
    referencias_txt = [f'{GeneralFunctions.meses[d.month - 1]} de {d.year}' for d in referencias]
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
    windowEFD = sg.Window(titulo, layout=layout,
                          size=(350, 300),
                          auto_size_text=True, auto_size_buttons=True,
                          text_justification='c',
                          resizable=False, finalize=True,
                          default_element_size=(15, 1),
                          modal=True, icon=GUIFunctions.app_icon)
    event, values = windowEFD.read()
    windowEFD.close()
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


def run_query(analysis: Analysis, query: str):
    try:
        if not analysis.is_query_based():
            total, resultado_query = analysis.function()
        else:
            if analysis.fix_database_function is not None:
                _, resultado_query = Controller.executa_consulta_BD(query)
                analysis.fix_database_function(resultado_query)
            total, resultado_query = Controller.executa_consulta_BD(query, 100)
    except AnalysisFunctionException as e:
        GUIFunctions.popup_erro(str(e), titulo='Erro no levantamento de dados adicionais para a base de dados',
                                exception=e)
    except QueryAnalysisException as e:
        GUIFunctions.popup_erro(str(e), titulo='Erro na consulta', exception=e)
    except Exception as e:
        erroSGBD = re.findall(r'ERROR:\s+(.*)\n', str(e))
        if erroSGBD:
            GUIFunctions.popup_ok(erroSGBD[0], titulo='Erro na consulta')
        else:
            GeneralFunctions.logger.exception('Erro em consulta ao BD de query para análise')
            GUIFunctions.popup_erro(str(e), titulo='Erro na consulta', exception=e)
    else:
        if total == 0:
            GUIFunctions.popup_ok('Não foram encontrados resultados para esta consulta.',
                                  titulo='Consulta ao banco de dados')
        else:
            dic_query = QueryResultWindow.open_query_result_window(total, resultado_query, query, analysis)
            if len(dic_query) > 0:
                try:
                    Controller.add_analysis_to_audit(
                        analysis,
                        planilha=dic_query.get('planilha', None), df=dic_query.get('df', None),
                        planilha_detalhe=dic_query.get('planilha_detalhe', None)
                    )
                except Controller.AIIMGeneratorUserWarning as e:
                    GUIFunctions.popup_erro(str(e), titulo='Aviso')
                refresh_analysis_tab()


def verification_chosen_for_notification(notification: PossibleInfraction = None):
    if notification and notification.verificacao.notification_title:
        window['-NOTIFICATION-EDIT-TITLE-'].update(notification.verificacao.notification_title, disabled=False)
        window['-NOTIFICATION-EDIT-'].update(notification.verificacao.notification_body, disabled=False)
        if notification.verificacao.has_notification_any_attachments():
            window['-NOTIFICATION-ATTACHMENTS-'].update(disabled=False)
        window['-NOTIFICATION-SEND-'].update(disabled=not get_current_audit().is_contribuinte_ativo())
        window['-NOTIFICATION-MANUAL-SEND-'].update(disabled=False)
    else:
        window['-NOTIFICATION-EDIT-TITLE-'].update('', disabled=True)
        window['-NOTIFICATION-EDIT-'].update('', disabled=True)
        window['-NOTIFICATION-ATTACHMENTS-'].update(disabled=True)
        window['-NOTIFICATION-SEND-'].update(disabled=True)
        window['-NOTIFICATION-MANUAL-SEND-'].update(disabled=True)


# ATENÇÃO: Mexendo diretamente no Widget para fazer negrito em partes do texto
def aiim_item_chosen(aiim_item: AiimItem):
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
            if aiim_item.planilha_detalhe:
                window['-AIIM-ITEM-DATA-'].update(f'Planilha Detalhada: ', font_for_value=('Arial', 10, 'bold'),
                                                  append=True)
                window['-AIIM-ITEM-DATA-'].update(f'{aiim_item.planilha_detalhe}\n', append=True)
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
                window['-AIIM-UPDATE-NOTIF-ANSWER-'].update(visible=aiim_item.notificacao and
                                                                    not aiim_item.notificacao_resposta)
            if aiim_item.relatorio_circunstanciado():
                window['-AIIM-ITEM-DATA-'].update('Relatório Circunstanciado: ',
                                                  font_for_value=('Arial', 10, 'bold'), append=True)
                window['-AIIM-ITEM-DATA-'].update(f'No item {aiim_item.item}, '
                                                  f'{aiim_item.relatorio_circunstanciado()}\n', append=True)
            proofs = aiim_item.proofs_for_report()
            if proofs:
                window['-AIIM-ITEM-DATA-'].update('Provas que compõem Anexo:\n',
                                                  font_for_value=('Arial', 10, 'bold'), append=True)
                for proof in proofs:
                    window['-AIIM-ITEM-DATA-'].update(f'    - {proof}\n', append=True)
            else:
                window['-AIIM-ITEM-PROOFS-'].update(visible=False)
            window['-AIIM-ITEM-DATA-'].update(visible=True)
            window['-AIIM-ITEM-DATA-'].expand(True, True)
            window['-AIIM-REMOVE-ITEM-'].update(visible=True)
    except ExcelArrazoadoAbaInexistenteException:
        if GUIFunctions.popup_sim_nao(f'A aba da planilha "{aiim_item.planilha}" não existe mais. '
                                      f'Deseja remover infração?'):
            WaitWindow.open_wait_window(Controller.remove_aiim_item, 'Remover Item do AIIM', aiim_item)
            refresh_aiim_tab()
    except Exception as ex:
        GeneralFunctions.logger.exception('Falha no levantamento de dados da infração')
        GUIFunctions.popup_erro(f'Falha no levantamento de dados da infração: {ex}', exception=ex)


def notification_chosen(notification: PossibleInfraction, title: str, body: str):
    try:
        verification_chosen_for_notification(notification)
        notification_prettyprint(
            notification.notificacao_titulo(title),
            notification.notificacao_corpo(body)
        )
    except ExcelArrazoadoAbaInexistenteException:
        if GUIFunctions.popup_sim_nao(f'A aba da planilha para essa notificação não existe mais. '
                                      f'Deseja remover notificação?'):
            Controller.remove_notification(notification)
            refresh_notifications_tab()
    except ExcelArrazoadoIncompletoException as e:
        GUIFunctions.popup_erro(str(e), exception=e)


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
    except Exception as e:
        GUIFunctions.popup_erro(f'Não foi possível criar anexo da análise {notification.verificacao}',
                                titulo='Falha na geração de anexo', exception=e)


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
            GUIFunctions.popup_erro('Número de notificação inválido!')


def notification_send(notification: PossibleInfraction, title: str, content: str):
    if GUIFunctions.popup_sim_nao('Será enviada uma notificação via DEC para o contribuinte,'
                                  'contendo as informações em tela e anexos gerados.\nConfirma?'):
        try:
            pasta_notificacao = WaitWindow.open_wait_window(
                Controller.send_notification, 'Enviar notificação via DEC',
                notification, title, content)
            if pasta_notificacao:
                GUIFunctions.popup_ok(f'Foi enviada notificação DEC! Os arquivos recebidos '
                                      f'em resposta devem ser guardados na pasta {pasta_notificacao}')
            refresh_notifications_tab()
        except Exception as e:
            GUIFunctions.popup_erro('Houve um erro no envio da notificação, '
                                    f'verifique se os arquivos anexos estão fechados: {e}', exception=e)


def update_gifs():
    for v in [v for k, v in window.key_dict.items() if isinstance(k, str) and k.endswith('-INFINITE-') and v.visible]:
        v.update_animation(v.Source, time_between_frames=100)


def window_layout():
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
                 sg.Image(data=GUIFunctions.bar_striped, size=(30, 25), visible=False, expand_x=True,
                          expand_y=False,
                          key=f'-{group}-{progress[0]}-INFINITE-'),
                 sg.ProgressBar(max_value=100, visible=False, size=(30, 25), expand_x=True, expand_y=False,
                                key=f'-{group}-{progress[0]}-PROGRESS-')]
                for progress in Controller.data_groups[group]['progressos']
            ], element_justification='left', expand_x=True, expand_y=True),
            sg.Column([[
                sg.Image(source=GUIFunctions.error_img, size=(30, 30), visible=False,
                         key=f'-{group}-{progress[0]}-ERROR-'),
                sg.Image(source=GUIFunctions.check_img, size=(30, 30), visible=False,
                         key=f'-{group}-{progress[0]}-OK-'),
                sg.Image(source=GUIFunctions.warning_img, size=(30, 30), visible=False,
                         key=f'-{group}-{progress[0]}-STOP-')
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
                ['&Editar', ['Propriedades::-MENU-PROPERTIES-', 'Cria Análise::-MENU-CREATE-ANALYSIS-', '---',
                             'Prepara Base de Dados::-MENU-PREPARE-BD-', 'Importa Inidôneos::-MENU-INIDONEOS-',
                             'Importa GIAs::-MENU-GIAS-', 'Importa Cadesp::-MENU-CADESP-']],
                ['A&juda', ['Abrir Pasta do Usuário::-MENU-USER-FOLDER-', 'Sobre::-MENU-ABOUT-']]
            ]
        case 'AUDITORIA_SEM_AIIM':
            return [
                ['&Arquivo', ['Criar Auditoria::-MENU-CREATE-AUDIT-',
                              'Abrir Auditoria::-MENU-OPEN-AUDIT-',
                              'Abrir Pasta da Auditoria::-MENU-AUDIT-FOLDER-',
                              'Sair::-MENU-EXIT-']],
                ['&Editar', ['Propriedades::-MENU-PROPERTIES-', 'Cria Análise::-MENU-CREATE-ANALYSIS-', '---',
                             'Prepara Base de Dados::-MENU-PREPARE-BD-', 'Importa Inidôneos::-MENU-INIDONEOS-',
                             'Importa GIAs::-MENU-GIAS-', 'Importa Cadesp::-MENU-CADESP-',
                             '---',
                             'Atualizar Dados da Fiscalizada::-MENU-UPDATE-OSF-',
                             'Abrir Planilha::-MENU-OPEN-SHEET-',
                             'Recarregar Planilha::-MENU-RELOAD-SHEET-']],
                ['E&FD', ['Imprimir LRE::-MENU-PRINT-LRE-',
                          'Imprimir LRS::-MENU-PRINT-LRS-',
                          'Imprimir LRI::-MENU-PRINT-LRI-',
                          'Imprimir LRAICMS::-MENU-PRINT-LRAICMS-']],
                ['A&IIM', ['Cria AIIM (gera número e AIIM2003)::-MENU-CREATE-AIIM-']],
                ['A&juda', ['Abrir Pasta do Usuário::-MENU-USER-FOLDER-', 'Sobre::-MENU-ABOUT-']]
            ]
        case 'AUDITORIA_COM_AIIM':
            recibo_key = 'Envia Recibo de Arquivos Digitais::-MENU-AIIM-RECEIPT-'
            aiim_submenu = ['Gera Relato e Quadros 1 a 3::-MENU-AIIM-REPORTS-',
                            'Atualiza Relatório Circunstanciado::-MENU-AIIM-CUSTOM-REPORT-',
                            'Gera Provas Gerais::-MENU-AIIM-GENERAL-PROOFS-',
                            'Atualiza Quadro de Operações::-MENU-AIIM-OPERATIONS-',
                            'Gera Capa para Anexo personalizada::-MENU-AIIM-PROOF-COVER-',
                            '---',
                            'Gera Arquivo Backup AIIM2003::-MENU-AIIM-EXPORT-',
                            'Gera Arquivo Transmissão AIIM2003::-MENU-AIIM-UPLOAD-']
            if not get_current_audit().is_aiim_open or not Controller.is_aiim_on_AIIM2003():
                aiim_submenu = ['!' + item for item in aiim_submenu]
                aiim_submenu.append('Reabre AIIM2003::-MENU-AIIM-REOPEN-')
            if get_current_audit().receipt_digital_files:
                recibo_key = '!' + recibo_key
            aiim_submenu.extend(['---', recibo_key])
            return [
                ['&Arquivo', ['Criar Auditoria::-MENU-CREATE-AUDIT-',
                              'Abrir Auditoria::-MENU-OPEN-AUDIT-',
                              'Abrir Pasta da Auditoria::-MENU-AUDIT-FOLDER-',
                              'Sair::-MENU-EXIT-']],
                ['&Editar', ['Propriedades::-MENU-PROPERTIES-', 'Cria Análise::-MENU-CREATE-ANALYSIS-', '---',
                             'Prepara Base de Dados::-MENU-PREPARE-BD-', 'Importa Inidôneos::-MENU-INIDONEOS-',
                             'Importa GIAs::-MENU-GIAS-', 'Importa Cadesp::-MENU-CADESP-',
                             '---',
                             'Atualizar Dados da Fiscalizada::-MENU-UPDATE-OSF-',
                             'Abrir Planilha::-MENU-OPEN-SHEET-',
                             'Recarregar Planilha::-MENU-RELOAD-SHEET-']],
                ['E&FD', ['Imprimir LRE::-MENU-PRINT-LRE-',
                          'Imprimir LRS::-MENU-PRINT-LRS-',
                          'Imprimir LRI::-MENU-PRINT-LRI-',
                          'Imprimir LRAICMS::-MENU-PRINT-LRAICMS-']],
                ['A&IIM', aiim_submenu],
                ['A&juda', ['Abrir Pasta do Usuário::-MENU-USER-FOLDER-', 'Sobre::-MENU-ABOUT-']]
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


def initialize_environment():
    try:
        GeneralFunctions.logger.debug("Inicializando ambiente...")
        Controller.set_proxy()
        GUIFunctions.update_splash(f'{GeneralFunctions.get_project_name()} v{GeneralFunctions.get_project_version()}')

        # tenta excluir diretorio tmp no início
        GeneralFunctions.clean_tmp_folder()

        sg.theme('SystemDefaultForReal')
        sg.set_options(ttk_theme=sg.THEME_WINNATIVE)

        if not GeneralConfiguration.get():
            GUIFunctions.close_splash()
            InitialConfigurationWizard.create_config_file()

        Controller.update_efd_pva_version()

        # Criar janela
        global window
        window = sg.Window(GeneralFunctions.get_project_name(), window_layout(), size=(1024, 768),
                           resizable=True, finalize=True,
                           enable_close_attempted_event=True, icon=GUIFunctions.app_icon)
        window.set_min_size((800, 500))
        window_layout_fix()
        refresh_data_tab()
    finally:
        GUIFunctions.close_splash()


def window_event_handler():
    log_window: LogWindow = None
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        w, event, values = sg.read_all_windows(timeout=100)
        if event == sg.TIMEOUT_EVENT:
            if log_window:
                log_window.handle_event(event, values)
            update_gifs()
        elif isinstance(w, LogWindow) or event == '-LOG-WINDOW-EVENT-':
            log_window = w
            w.handle_event(event, values)
            if event == sg.WINDOW_CLOSED:
                clear_data_tab()
            continue
        elif isinstance(w, AnalysisWizardWindow):
            w.handle_event(event, values)
            if event == sg.WINDOW_CLOSED:
                w.close()
                refresh_analysis_tab()
            continue
        # eventos da janela principal
        elif event == sg.WINDOW_CLOSE_ATTEMPTED_EVENT or event == sg.WINDOW_CLOSED or event.endswith('-MENU-EXIT-') \
                or event == 'Cancel':  # if user closes window or clicks cancel
            if GUIFunctions.popup_sim_nao('Deseja realmente sair?'):
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
                except Exception as e:
                    GUIFunctions.popup_erro(str(e), titulo='Falha na abertura da auditoria', exception=e)
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
        elif event == '-QUERY-':
            run_query(values['-ANALYSIS-CHOSEN-'][0], values['-SQL-'])
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
                notification_chosen(values[event][0],
                                    values['-NOTIFICATION-EDIT-TITLE-'], values['-NOTIFICATION-EDIT-'])
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
                aiim_item_chosen(values[event][0])
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
                                      element_justification='c', icon=GUIFunctions.app_icon)
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
            aiim_item_chosen(aiim_item)
        elif event == '-AIIM-UPDATE-ITEM-':
            WaitWindow.open_wait_window(Controller.cria_ddf, 'Atualizar DDF de Item no AIIM',
                                        values['-INFRACTION-CHOSEN-'][0])
            aiim_item_chosen(values['-INFRACTION-CHOSEN-'][0])
        elif event == '-AIIM-UPDATE-ITEM-NUMBER-':
            resposta = GUIFunctions.popup_pega_texto('Digite o número correto atual do item no AIIM2003',
                                                     'Alteração Manual de Item')
            if resposta and re.match(r'^\d+$', resposta):
                aiim_item = values['-INFRACTION-CHOSEN-'][0]
                WaitWindow.open_wait_window(Controller.update_aiim_item_number,
                                            'Atualizar número do Item',
                                            aiim_item, int(resposta))
                refresh_aiim_tab()
                values['-INFRACTION-CHOSEN-'] = [aiim_item]
                aiim_item_chosen(aiim_item)
        elif event == '-AIIM-UPDATE-NOTIF-ANSWER-':
            resposta = GUIFunctions.popup_pega_texto('Digite o expediente Sem Papel com resposta à notificação',
                                                     'Resposta à Notificação')
            try:
                aiim_item: AiimItem = values['-INFRACTION-CHOSEN-'][0]
                Controller.update_aiim_item_notification_response(aiim_item, resposta)
                aiim_item_chosen(aiim_item)
            except ValueError:
                GUIFunctions.popup_erro('Formato inválido para número de expediente Sem Papel '
                                        '(deveria ser algo como SFP-EXP-<ano>/<numero>)')
        elif event == '-AIIM-REMOVE-ITEM-':
            if GUIFunctions.popup_sim_nao('Deseja realmente remover este item da lista de infrações e do AIIM?',
                                          titulo='Alerta'):
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
        elif event.endswith('-MENU-CREATE-ANALYSIS-'):
            AnalysisWizardWindow()
        elif event.endswith('-MENU-OPEN-SHEET-'):
            subprocess.Popen(f"{GeneralFunctions.get_default_windows_app('.xlsx')} "
                             f'"{get_current_audit().get_sheet().planilha_path.absolute()}"')
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
        elif event.endswith('-MENU-AIIM-PROOF-COVER-'):
            texto = icon = GUIFunctions.app_icon('Informe o texto a ser colocado na capa:', 'Capa personalizada')
            if texto:
                caminho = sg.popup_get_file('Escolha o local e nome da nova capa', 'Nova capa',
                                            initial_folder=get_current_audit().path(), save_as=True,
                                            default_extension='.pdf',
                                            icon=GUIFunctions.app_icon,
                                            file_types=(('PDF', '.pdf'),), no_window=True)
                if caminho:
                    WaitWindow.open_wait_window(Controller.generate_custom_report_cover, '', texto, Path(caminho))
        elif event.endswith('-MENU-AIIM-RECEIPT-'):
            WaitWindow.open_wait_window(Controller.send_notification_with_files_digital_receipt, 'Enviar Recibo')
            refresh_menu()
        elif event.endswith('-MENU-AIIM-EXPORT-'):
            WaitWindow.open_wait_window(Controller.export_aiim, 'Exportar AIIM')
        elif event.endswith('-MENU-AIIM-REOPEN-'):
            WaitWindow.open_wait_window(Controller.reopen_aiim, 'Reabrir AIIM')
            refresh_menu()
        elif event.endswith('-MENU-AIIM-UPLOAD-'):
            WaitWindow.open_wait_window(Controller.upload_aiim, 'Transmitir AIIM')
            refresh_menu()
        elif event.endswith('-MENU-PREPARE-BD-'):
            WaitWindow.open_wait_window(Controller.prepare_database, 'Preparar base de dados')
        elif event.endswith('-MENU-GIAS-'):
            caminho = sg.popup_get_file('Escolha o arquivo de GIAs mais recente', 'GIAs',
                                        initial_folder=str(Path.home()),
                                        default_extension='.zip',
                                        icon=GUIFunctions.app_icon,
                                        file_types=(('Arquivos compactados', '.zip'),), no_window=True)
            WaitWindow.open_wait_window(Controller.update_gias, 'Importar GIAs', Path(caminho))
        elif event.endswith('-MENU-CADESP-'):
            caminho = sg.popup_get_file('Escolha o arquivo de Cadesp mais recente', 'Cadesp',
                                        initial_folder=str(Path.home()),
                                        default_extension='.zip',
                                        icon=GUIFunctions.app_icon,
                                        file_types=(('Arquivos compactados', '.zip'),), no_window=True)
            WaitWindow.open_wait_window(Controller.update_cadesp, 'Importar Cadesp', Path(caminho))
        elif event.endswith('-MENU-INIDONEOS-'):
            caminho = sg.popup_get_file('Escolha o arquivo de inidôneos mais recente', 'Inidôneos',
                                        initial_folder=str(Path.home()),
                                        default_extension='.zip',
                                        icon=GUIFunctions.app_icon,
                                        file_types=(('Arquivos compactados', '.zip'),), no_window=True)
            WaitWindow.open_wait_window(Controller.update_inidoneos, 'Importar Inidôneos', Path(caminho))
        elif event.endswith('-MENU-USER-FOLDER-'):
            subprocess.run([os.path.join(os.getenv('WINDIR'), 'explorer.exe'),
                            GeneralFunctions.get_user_path().absolute()])
        elif event.endswith('-MENU-AUDIT-FOLDER-'):
            subprocess.run([os.path.join(os.getenv('WINDIR'), 'explorer.exe'),
                            get_current_audit().path().absolute()])
        elif event.endswith('-MENU-ABOUT-'):
            GUIFunctions.popup_about()
    window.close()


# para ser usado como forma de gerar o release por IDE
def generate_release():
    PyInstaller.__main__.run_build(None, spec_file='PoltergeistFDT.spec', noconfirm=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--release':
        generate_release()
        sys.exit()

    extracoes = {}
    try:
        initialize_environment()
        window_event_handler()
    except Exception as e:
        GeneralFunctions.logger.exception(f'Exceção inesperada: {e}')
        GUIFunctions.popup_erro(f'Erro inesperado na execução do {GeneralFunctions.get_project_name()}: {e}',
                                exception=e)

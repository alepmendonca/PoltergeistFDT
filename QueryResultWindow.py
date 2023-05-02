import re

import pandas as pd
import PySimpleGUI as sg

import Controller
import Audit
import GUIFunctions
import WaitWindow
from ConfigFiles import Analysis


def open_query_result_window(total: int, resultado: pd.DataFrame, query: str, analysis: Analysis | None) -> dict:
    sheet_name = analysis.sheet_default_name if analysis and analysis.is_query_based() else 'Planilha'
    if total == len(resultado):
        texto = f'Resultado (total de {total} linhas)'
    else:
        texto = f"Resultado (total de {total} linhas, mostrando as primeiras {len(resultado)}):"
    # necessária essa conversão apenas para mostrar como data, não inteiro, quando é apenas uma coluna de data
    if len(resultado.keys()) == 1 and resultado.dtypes[0] == 'datetime64[ns]':
        tabela = [[v] for v in resultado[resultado.keys()[0]].values.astype('datetime64[us]').tolist()]
    else:
        tabela = resultado.values.tolist()
    layout = [
        [sg.Text(texto)],
        [sg.Table(
            size=(300, 15), expand_x=True, expand_y=True, key='-TABELA-QUERY-', auto_size_columns=True,
            headings=resultado.keys().tolist(), values=tabela, justification='left',
            vertical_scroll_only=False,
        )]
    ]
    if len(resultado.keys()) > 1:
        layout.append([
            sg.Push(),
            sg.InputText(default_text=sheet_name,
                         tooltip='Nome a ser dado para a nova aba da planilha de arrazoado, que '
                                 'terá os dados acima já formatados',
                         enable_events=True, key='-NEW-SHEET-NAME-', size=(31, 15)),
            sg.Button('Exporta Resultados para Planilha', key='-EXPORT-RESULTS-'),
            sg.Push()
        ])
    else:
        button_text = 'Gera Notificação' if analysis and analysis.notification_title else 'Gera Infração'
        layout.append([
            sg.Push(),
            sg.Button(button_text, key='-BUILD-NOTIFICATION-'),
            sg.Push()
        ])

    window = sg.Window('Resultado da Consulta', layout,
                       auto_size_buttons=True,
                       resizable=True, finalize=True,
                       default_element_size=(15, 1))

    retorno = {}
    # Event Loop to process "events" and get the "values" of the inputs
    try:
        while True:
            event, values = window.read()
            if event == sg.WINDOW_CLOSED:
                break
            elif event == '-NEW-SHEET-NAME-':
                # especificacao de nomes de sheet no Excel
                nome_corrigido = re.sub(r'[\\/*?:\[\]]', '', values[event])[:20]
                window[event].update(nome_corrigido)
                window['-EXPORT-RESULTS-'].update(disabled=len(nome_corrigido) == 0)
            elif event == '-EXPORT-RESULTS-':
                excel = Audit.get_current_audit().get_sheet()
                if values['-NEW-SHEET-NAME-'] not in excel.get_sheet_names() or \
                        not GUIFunctions.popup_sim_nao('Já existe uma aba na planilha da empresa fiscalizada'
                                                       ' com este nome! Deseja manter o conteúdo da aba?',
                                                       titulo='Aba existente na planilha'):
                    if query and len(resultado) != total:
                        _, resultado = WaitWindow.open_wait_window(Controller.executa_consulta_BD, '', query)
                    WaitWindow.open_wait_window(excel.exporta_relatorio_para_planilha, '',
                                                values['-NEW-SHEET-NAME-'], analysis, resultado)
                    if analysis and analysis.query_detail is not None:
                        _, resultado = WaitWindow.open_wait_window(Controller.executa_consulta_BD, '',
                                                                   analysis.query_detail)
                        detalhe = f"{values['-NEW-SHEET-NAME-']} - Detalhe"
                        WaitWindow.open_wait_window(excel.exporta_relatorio_para_planilha, '',
                                                    detalhe, analysis, resultado, False)
                        retorno['planilha_detalhe'] = detalhe
                retorno['planilha'] = values['-NEW-SHEET-NAME-']
                break
            elif event == '-BUILD-NOTIFICATION-':
                retorno['df'] = resultado
                break
    except Exception as e:
        sg.popup_error(f'Erro na exportação da tabela para Excel: {str(e)}', title='Erro')
        retorno = {}
    window.close()
    return retorno

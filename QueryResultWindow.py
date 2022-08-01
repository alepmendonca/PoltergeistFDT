import re

import pandas as pd
import PySimpleGUI as sg

import Controller
from ConfigFiles import Analysis


def open_query_result_window(total: int, resultado: pd.DataFrame, query: str, analysis: Analysis):
    sheet_name = analysis.sheet_default_name
    button_text = 'Gera Notificação' if analysis.notification_title else 'Gera Infração'
    if total == len(resultado):
        texto = f'Resultado (total de {total} linhas)'
    else:
        texto = f"Resultado (total de {total} linhas, mostrando as primeiras {len(resultado)}):"
    layout = [
        [sg.Text(texto)],
        [sg.Table(
            size=(300, 15), expand_x=True, expand_y=True, key='-TABELA-QUERY-', auto_size_columns=True,
            headings=resultado.keys().tolist(), values=resultado.values.tolist(), justification='left',
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
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED:
            break
        elif event == '-NEW-SHEET-NAME-':
            # especificacao de nomes de sheet no Excel
            nome_corrigido = re.sub(r'[\\\/\*\?\:\[\]]', '', values[event])[:20]
            window[event].update(nome_corrigido)
            window['-EXPORT-RESULTS-'].update(disabled=len(nome_corrigido) == 0)
        elif event == '-EXPORT-RESULTS-':
            excel = Controller.get_analysis_sheet()
            if window['-NEW-SHEET-NAME-'] in excel.get_sheet_names():
                sg.popup_ok('Já existe uma aba na planilha da empresa fiscalizada com este nome!'
                            ' Escolha outro nome e tente novamente.')
            else:
                try:
                    if query and len(resultado) != total:
                        _, resultado = Controller.executa_consulta_BD(query)
                    excel.exporta_relatorio_para_planilha(values['-NEW-SHEET-NAME-'], analysis, resultado)
                    retorno['planilha'] = values['-NEW-SHEET-NAME-']
                    break
                except Exception as e:
                    sg.popup_error(f'Erro na exportação da tabela para Excel: {str(e)}', title='Erro')
        elif event == '-BUILD-NOTIFICATION-':
            retorno['df'] = resultado
            break
    window.close()
    return retorno

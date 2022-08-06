import textwrap
import PySimpleGUI as sg

import GeneralFunctions


def popup_erro(texto: str, titulo='Erro'):
    sg.Window(titulo, [[sg.Text('\n'.join(textwrap.wrap(texto, 100)))],
                       [sg.Push(), sg.Button(button_color=sg.DEFAULT_ERROR_BUTTON_COLOR,
                                             button_text='Erro', s=10),
                        sg.Push()]], modal=True).read(close=True)


def popup_ok(texto: str, titulo=GeneralFunctions.project_name):
    sg.Window(titulo, [[sg.Text('\n'.join(textwrap.wrap(texto, 100)))],
                       [sg.Push(), sg.Button('OK', s=10),
                        sg.Push()]], modal=True).read(close=True)


def popup_sim_nao(texto: str, titulo='Atenção') -> str:
    botao = sg.Window(titulo, [[sg.Text('\n'.join(textwrap.wrap(texto, 100)))],
                       [sg.Push(), sg.Button('Sim', s=10), sg.Button('Não', s=10),
                        sg.Push()]], disable_close=True, modal=True).read(close=True)
    return botao[0] if botao else None

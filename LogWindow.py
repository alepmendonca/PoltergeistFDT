from collections import Callable

import PySimpleGUI as sg
import logging
import threading
import time
from GeneralFunctions import logger

"""
    Código originalmente tirado de
    https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Multithreaded_Logging.py
"""


# Abaixo segue um exemplo de funcao a ser passada como parametro da log_window
# A função sempre precisa ter como último parâmetro o threading.Event
# Importante olhar para o evento da thread, caso alguém peça para interromper o processo
def externalFunction(evento: threading.Event):
    logger.info('Iniciando processo')
    i = 0
    while not evento.is_set() and i < 10:
        logger.info(f'Rodando subparte nº {i} do processo...')
        i = i + 1
        time.sleep(1)
    if evento.is_set():
        logger.warning('Processo parado no meio...')
    else:
        logger.warning('Processo encerrado com sucesso!')


class ThreadedApp(threading.Thread):
    def __init__(self, funcao_controller: Callable, nome_batch: str, parametros_funcao_controller):
        super().__init__()
        self.setName(nome_batch)
        self._stop_event = threading.Event()
        self._funcao = funcao_controller
        self._parametros = list(parametros_funcao_controller)
        self._parametros.append(self._stop_event)

    def run(self):
        try:
            self._funcao(*self._parametros)
        except Exception:
            logger.exception(f'Ocorreu um erro na execução do processo {self.getName()}, tente novamente mais tarde.')

    def stop(self):
        self._stop_event.set()


class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        self.setLevel('INFO')

    def emit(self, record):
        self.log_queue.put(record)


class WindowEventHandler(logging.Handler):
    def __init__(self, window: sg.Window):
        super().__init__()
        self.window = window
        self.setLevel('INFO')

    def emit(self, record):
        self.window.write_event_value('-LOG-WINDOW-EVENT-', self.format(record))


class QueueFormatter(logging.Formatter):
    def format(self, record) -> str:
        if record.exc_info:
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return super().format(record)


class LogWindow(sg.Window):
    def __init__(self, funcao_batch: Callable, nome_funcao_batch: str, *parametros_funcao_batch):
        layout = [
            [sg.Push(),
             sg.Multiline(default_text='Após pressionar o botão Iniciar, NÃO MEXA NO SEU COMPUTADOR,' +
                                       ' exceto para preencher a senha do certificado digital.\n' +
                                       'Caso deseje parar o processo, clique no botão Parar.\n\n',
                          size=(300, 15),
                          expand_x=True, expand_y=True,
                          key='-LOG-', auto_size_text=True,
                          autoscroll=True, write_only=True),
             sg.Push()],
            [sg.Push(),
             sg.Button('Iniciar', bind_return_key=True, key='-START-'),
             sg.Button('Fechar', key='-STOP-'),
             sg.Push()],
        ]
        super().__init__('Detalhes do processamento', layout,
                         size=(850, 350),
                         auto_size_text=True, auto_size_buttons=True,
                         resizable=True, finalize=True,
                         default_element_size=(15, 1),
                         enable_close_attempted_event=True,
                         modal=True)
        # Setup logging
        self._msg_handler = WindowEventHandler(self)
        self._msg_handler.setFormatter(QueueFormatter("%(asctime)s - %(message)s", datefmt="%H:%M:%S"))
        logger.addHandler(self._msg_handler)
        self._funcao = funcao_batch
        self._funcao_nome = nome_funcao_batch
        self._funcao_parametros = parametros_funcao_batch
        self._threadedApp = None

    def close(self):
        logger.removeHandler(self._msg_handler)
        super().close()

    def handle_event(self, event, values):
        if event == '-START-':
            if self._threadedApp is None:
                self._threadedApp = ThreadedApp(self._funcao, self._funcao_nome, self._funcao_parametros)
                self._threadedApp.start()
                logger.debug('Iniciando processo...')
                self['-START-'].update(disabled=True)
                self['-STOP-'].update('Parar')
        elif event in ('-STOP-', sg.WINDOW_CLOSE_ATTEMPTED_EVENT) \
                and self._threadedApp and self._threadedApp.is_alive() \
                and sg.popup_yes_no("Deseja realmente parar o processo?") == 'Yes':
            self._threadedApp.stop()
            logger.warning('PARANDO EXECUÇÃO DO PROCESSO. AGUARDE...')
            self['-STOP-'].update(disabled=True)
        elif event in ('-STOP-', sg.WINDOW_CLOSE_ATTEMPTED_EVENT, sg.WINDOW_CLOSED) \
                and self._threadedApp is None:
            self.close()
        elif event == '-LOG-WINDOW-EVENT-':
            msg = values[event]
            if msg.upper() == msg:
                self['-LOG-'].update(msg + '\n', background_color_for_value='yellow', append=True)
            elif 'erro' in msg.lower() or 'falha' in msg.lower() or 'problema' in msg.lower():
                self['-LOG-'].update(msg + '\n', background_color_for_value='red', append=True)
            elif '!' in msg:
                self['-LOG-'].update(msg + '\n', background_color_for_value='green', append=True)
            else:
                self['-LOG-'].update(msg + '\n', append=True)
        if event == sg.TIMEOUT_EVENT:
            if self._threadedApp is not None and not self._threadedApp.is_alive():
                self['-LOG-'].update('PROCESSO ENCERRADO.\n', append=True)
                self._threadedApp = None
                self['-START-'].update(disabled=False)
                self['-STOP-'].update("Fechar", disabled=False)
                self['-STOP-'].ButtonText = 'Fechar'


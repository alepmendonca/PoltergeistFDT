import PySimpleGUI as sg
import queue

from collections.abc import Callable

import GUIFunctions
from GeneralFunctions import logger, ThreadWithReturnValue, QueueHandler, QueueFormatter


def open_wait_window(funcao_batch: Callable, funcao_desc: str, *parametros_funcao_batch, raise_exceptions=False):
    # Setup logging
    log_queue = queue.Queue()
    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(QueueFormatter("%(message)s"))
    logger.addHandler(queue_handler)

    message = ''
    layout = [
        [sg.Image(data=sg.DEFAULT_BASE64_LOADING_GIF, background_color='white', key='-IMAGE-')],
        [sg.Text(message, background_color='white', text_color='black', key='-TEXT-')]
    ]
    animated_window = sg.Window('', layout, no_titlebar=True, grab_anywhere=True,
                                keep_on_top=True, element_padding=(0, 0), margins=(0, 0),
                                finalize=True, element_justification='c', modal=True)
    thread = ThreadWithReturnValue(target=funcao_batch, args=parametros_funcao_batch)
    thread.start()

    exception = None
    while True:
        animated_window.read(100)
        if not thread.is_alive():
            animated_window.close()
            try:
                result = thread.join()
            except Exception as e:
                logger.exception(f'Erro ocorrido em WaitWindow da função {funcao_batch.__name__}')
                if not raise_exceptions:
                    GUIFunctions.popup_erro(f'Ocorreu o seguinte erro: {e}', exception=e)
                result = e
                exception = e
            else:
                if funcao_desc:
                    GUIFunctions.popup_ok(f'Tarefa "{funcao_desc}" finalizada com sucesso!')
            finally:
                logger.removeHandler(queue_handler)
                break

        # Poll queue
        try:
            record = log_queue.get(block=False)
        except queue.Empty:
            pass
        else:
            message = queue_handler.format(record)
            animated_window['-TEXT-'].update(message)
            if message == message.upper():
                animated_window.bring_to_front()

        animated_window['-IMAGE-'].update_animation(sg.DEFAULT_BASE64_LOADING_GIF, time_between_frames=100)

    if raise_exceptions and exception:
        raise exception
    else:
        return result

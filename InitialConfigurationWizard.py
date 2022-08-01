import io
import sys
import textwrap

import GeneralConfiguration
import GeneralFunctions
import WaitWindow
from WebScraper import SeleniumWebScraper
import PySimpleGUI as sg
from PIL import Image


def __create_wizard_window(layout: list) -> sg.Window:
    return sg.Window(GeneralFunctions.project_name, layout, size=(600, 550),
                     resizable=False, finalize=True, text_justification='center', element_justification='center')


def __get_dados_from_web(config):
    with SeleniumWebScraper() as ws:
        ws.get_dados_afr(config)
    return True


def get_splash_image():
    image = Image.open(r'resources/splash.jpg')
    image.thumbnail((480, 270))
    bio = io.BytesIO()
    image.save(bio, format='PNG')
    return sg.Image(bio.getvalue())


def create_config_file():
    layout = [
        [get_splash_image()],
        [sg.Text(f'Este é o {GeneralFunctions.project_name}, que faz a possessão do seu computador ')],
        [sg.Text('para fazer as tarefas mais repetitivas de uma auditoria fiscal.')],
        [sg.Text(f'Como não localizei nenhuma informação sua (sem entrar na sua cabeça), para começar, ')],
        [sg.Text(f'vou pedir alguns dados seus, que vão ficar guardados em um arquivo chamado ')],
        [sg.Text(f'{GeneralFunctions.get_local_dados_afr_path().name}, '
                 f'na pasta {GeneralFunctions.get_local_dados_afr_path().parent}')],
        [sg.Text(f'As senhas pedidas vão ficar num arquivo criptografado nessa mesma pasta, ')],
        [sg.Text(f'pra dificultar um pouquinho o trabalho de outros poltergeists...')],
        [sg.Push(),
         sg.Button('Estou pronto!', key='-WIZ-2-', size=(20, 3)),
         sg.Button('Vade Retro!', key='-WIZ-OUT-', size=(20, 3)),
         sg.Push()]
    ]
    window = __create_wizard_window(layout)
    while True:
        event, values = window.read()
        if not event or event == '-WIZ-OUT-':
            sys.exit()
        if event == '-WIZ-2-':
            window.close()
            break

    config = GeneralConfiguration.Configuration()
    certificados_validos = GeneralFunctions.get_icp_certificates()
    certificado_escolhido = ''
    if len(certificados_validos) == 0:
        sg.popup_error('Há algum problema no seu computador, pois não encontrei nenhum certificado digital!')
        sys.exit()
    if len(certificados_validos) == 1:
        certificado_escolhido = certificados_validos[0]
    else:
        layout = [
            [sg.VPush()],
            [sg.Text('Achei mais de um certificado digital nesta máquina, escolha o seu:')],
            [sg.Combo(values=sorted(certificados_validos),
                      key='-WIZ-CERTIFICADO-', default_value=sorted(certificados_validos)[0],
                      size=(500, 10),
                      readonly=True)],
            [sg.Push(), sg.Button('Sou este', key='-WIZ-3-', size=(20, 3)), sg.Push()],
            [sg.VPush()]
        ]
        window = __create_wizard_window(layout)
        while True:
            event, values = window.read()
            if not event:
                sys.exit()
            if event == '-WIZ-3-':
                certificado_escolhido = values['-WIZ-CERTIFICADO-']
                window.close()
                break
    config.certificado = certificado_escolhido

    text1 = f'Agora {certificado_escolhido.split()[0].capitalize()}, ' \
            f'preciso que você me diga quais são suas senhas, pra eu poder acessar os ' \
            f'sistemas fazendários e baixar informações dos contribuintes. As senhas não vão ' \
            f'ficar fáceis de serem copiadas por alguém.'
    text2 = 'Ao confirmar os dados abaixo, vou fazer umas pesquisas para pegar dados seus, ' \
            'então não mexa nas janelas que aparecerem no computador, para não dar nenhum problema.' \
            ' Você saberá que acabaram as pesquisas quando o navegador fechar e surgir uma nova ' \
            'mensagem no programa.'
    layout = [
        [sg.VPush()],
        [sg.Text('\n'.join(textwrap.wrap(text1, 75)), size=(580, None))],
        [sg.Text('\n'.join(textwrap.wrap(text2, 75)), size=(580, None))],
        [sg.Text('')],
        [sg.Text('Senha de rede: '), sg.InputText(expand_x=True,
                                                  password_char='*', key='-WIZ-INTRANET-PASS-')],
        [sg.Text('Senha do crachá: '), sg.InputText(expand_x=True,
                                                    password_char='*', key='-WIZ-CERTIFICATE-PASS-')],
        [sg.Text('Usuário do Sem Papel (Sigadoc)'), sg.InputText(expand_x=True, key='-WIZ-SIGADOC-USER-')],
        [sg.Text('Senha do Sem Papel (Sigadoc): '),
         sg.InputText(expand_x=True, password_char='*', key='-WIZ-SIGADOC-PASS-')],
        [sg.Push(), sg.Button('Vamos testar as senhas!', key='-WIZ-4-', size=(20, 3)), sg.Push()],
        [sg.VPush()]
    ]
    window = __create_wizard_window(layout)
    while True:
        event, values = window.read()
        if not event:
            sys.exit()
        if event == '-WIZ-4-':
            config.intranet_pass = values['-WIZ-INTRANET-PASS-']
            config.certificado_pass = values['-WIZ-CERTIFICATE-PASS-']
            config.sigadoc_login = values['-WIZ-SIGADOC-USER-']
            config.sigadoc_pass = values['-WIZ-SIGADOC-PASS-']
            if WaitWindow.open_wait_window(__get_dados_from_web, 'Carregar dados do AFRE', config):
                config.save()
                window.close()
                break

    layout = [
        [sg.Text(f'Muito bem, {GeneralConfiguration.get().nome.split()[0].capitalize()}, já sei bem quem você é!')],
        [sg.Text(f'O {GeneralFunctions.project_name} está configurado para uso! Bom proveito!')],
        [sg.Push(), sg.Button('Vamos lá!'), sg.Push()]
    ]
    window = __create_wizard_window(layout)
    window.read()
    window.close()

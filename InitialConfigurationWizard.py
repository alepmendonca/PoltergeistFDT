import io
import sys
import textwrap

import GUIFunctions
import GeneralConfiguration
import GeneralFunctions
import WaitWindow
from SQLReader import SQLReader
from WebScraper import SeleniumWebScraper
import PySimpleGUI as sg
from PIL import Image


def __create_wizard_window(layout: list) -> sg.Window:
    return sg.Window(GeneralFunctions.project_name, layout, size=(600, 550),
                     resizable=False, finalize=True, text_justification='center',
                     element_justification='center', icon=GUIFunctions.app_icon)


def __get_dados_from_web(config):
    with SeleniumWebScraper() as ws:
        ws.get_dados_afr(config)
    return True


def splash_image_path() -> str:
    return r'resources/splash.jpg'


def get_splash_image() -> bytes:
    image = Image.open(splash_image_path())
    image.thumbnail((480, 270))
    bio = io.BytesIO()
    image.save(bio, format='PNG')
    return bio.getvalue()


def create_config_file():
    layout = [
        [sg.Image(get_splash_image())],
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
    if len(certificados_validos) == 0:
        GUIFunctions.popup_erro('Há algum problema no seu computador, pois não encontrei nenhum certificado digital!')
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
            f'ficar fáceis de serem copiadas por alguém, sendo gravadas no cofre do Windows.'
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
                window.close()
            break

    layout = [
        [sg.VPush()],
        [sg.Text('Ajude-me a localizar os programas instalados no seu computador:')],
        [sg.Text('Pasta principal do EFD PVA ICMS:')],
        [sg.InputText(key='-WIZ-EFD-'), sg.FolderBrowse(initial_folder='c:')],
        [sg.Text('\n'.join(textwrap.wrap('Abaixo, coloque os dados do banco de dados local Postgres '
                                         '(na instalação dele aparecem essas informações, abaixo foram colocadas'
                                         'as opções comumente usadas).', 75)), size=(580, None))],
        [sg.Text("Endereço do Postgres:"), sg.Input(key='-WIZ-POSTGRES-ADDRESS-', default_text=config.postgres_address,
                                                    expand_x=True)],
        [sg.Text("Porta do Postgres:"), sg.Input(key='-WIZ-POSTGRES-PORT-', default_text=config.postgres_port,
                                                 expand_x=True)],
        [sg.Text("Instância:"), sg.Input(key='-WIZ-POSTGRES-DBNAME-', default_text=config.postgres_dbname,
                                         expand_x=True)],
        [sg.Text("Usuário:"), sg.Input(key='-WIZ-POSTGRES-USER-', default_text=config.postgres_user,
                                       expand_x=True)],
        [sg.Text("Senha:"), sg.Input(key='-WIZ-POSTGRES-PASS-', default_text=config.postgres_pass,
                                     expand_x=True, password_char='*')],
        [sg.Push(), sg.Button('Pronto', key='-WIZ-5-', size=(20, 3)), sg.Push()],
        [sg.VPush()]
    ]
    window = __create_wizard_window(layout)
    while True:
        event, values = window.read()
        if not event:
            sys.exit()
        if event == '-WIZ-5-':
            try:
                config.efd_path = values['-WIZ-EFD-']
            except ValueError as e:
                GUIFunctions.popup_erro(f'Problema com EFD PVA ICMS: {e}')
            else:
                config.postgres_address = values['-WIZ-POSTGRES-ADDRESS-']
                config.postgres_port = values['-WIZ-POSTGRES-PORT-']
                config.postgres_dbname = values['-WIZ-POSTGRES-DBNAME-']
                config.postgres_user = values['-WIZ-POSTGRES-USER-']
                config.postgres_pass = values['-WIZ-POSTGRES-PASS-']
                try:
                    with SQLReader(config=config) as postgres:
                        postgres.executa_consulta('SELECT 1')
                except Exception as e:
                    texto = 'Não foi possível conectar no banco de dados local. ' \
                            'Verifique os dados para conexão e tente novamente.' \
                            f'Erro ocorrido: {e}'
                    GUIFunctions.popup_erro(texto)
                else:
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

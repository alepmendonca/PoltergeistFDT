import datetime
import os.path
import queue
import re
import subprocess
import sys
import threading

import PySimpleGUI
import mysql.connector
import py4j.java_gateway
import py4j.protocol
from pathlib import Path
from py4j.compat import (unicode, bytestr)
from py4j.java_gateway import JavaGateway
from py4j.java_gateway import GatewayParameters

import GeneralConfiguration
import GeneralFunctions
from Audit import get_current_audit
from GeneralFunctions import logger


# Nova funcao para reconhecer output do Java em ISO-8859-1
def new_smart_decode(s):
    if isinstance(s, unicode):
        return s
    elif isinstance(s, bytestr):
        return unicode(s, 'iso-8859-1')
    else:
        return unicode(s)


# Monkey patching!
py4j.protocol.smart_decode = new_smart_decode
py4j.java_gateway.smart_decode = new_smart_decode
py4j.java_gateway.Popen = GeneralFunctions.PopenWindows


class EFDPVAInstaller:
    @staticmethod
    def upgrade_efd_pva(new_version_path: Path, install_path: Path, mysql_port: int):
        if not new_version_path.is_file():
            raise Exception(f'Não existe arquivo de instalação do EFD PVA ICMS em {new_version_path}, '
                            f'desistindo da instalação...')
        try:
            logger.info('Iniciando instalação do EFD PVA ICMS mais atual...')
            subprocess.check_call(f'java -DINSTALL_PATH="{install_path.resolve()}" '
                                  f'-jar "{new_version_path.resolve()}" '
                                  f'-console -options-system"')
            logger.info('Instalação do EFD PVA ICMS realizada!')
        except subprocess.CalledProcessError as cpe:
            raise Exception(f'Falha ao tentar instalar EFD PVA ICMS: {cpe}')
        if install_path.is_dir():
            # alterando o arquivo de propriedades para definir uma porta para o banco MySQL
            with (install_path / 'configuracoes' / 'spedfiscal.properties').open(mode='rt') as fin:
                propriedades = fin.read()
                with (install_path / 'configuracoes' / 'spedfiscal.properties').open(mode='wt') as fout:
                    propriedades = re.sub(r'portaBanco=\d+', f'portaBanco={mysql_port}', propriedades)
                    fout.write(propriedades)
            logger.info('Arquivo de propriedades do EFD PVA ICMS atualizado com sucesso!')
        else:
            raise Exception('Falha ao instalar EFD PVA ICMS, diretório não criado.')


class EFDPVAReversed:
    log_queue = queue.Queue()
    queue_handler = GeneralFunctions.QueueHandler(log_queue)
    queue_handler.setFormatter(GeneralFunctions.QueueFormatter("%(message)s"))

    def __init__(self):
        self._efds_json_path = GeneralFunctions.get_efds_json_path(get_current_audit().path()) \
            if get_current_audit() else None

        # Main path setup
        if getattr(sys, "frozen", False):
            self.script_path = os.path.dirname(sys.executable)
        else:
            self.script_path = os.path.dirname(os.path.abspath(__file__))

        efd_pva_path = str(GeneralConfiguration.get().efd_path.absolute())
        class_path = [
            os.path.join(self.script_path, 'efd-pva-inspector', 'bin'),
            os.path.join(efd_pva_path, 'fiscalpva.jar'),
            os.path.join(efd_pva_path, 'lib', 'br.gov.serpro.sped.fiscalpva', 'fiscalpva-dominio.jar'),
            os.path.join(efd_pva_path, 'lib', 'br.gov.serpro.sped.fiscalpva', 'fiscalpva-edicao.jar'),
            os.path.join(efd_pva_path, 'lib', 'br.gov.serpro.sped.fiscalpva', 'fiscalpva-geradorregistro.jar'),
            os.path.join(efd_pva_path, 'lib', 'br.gov.serpro.sped.fiscalpva', 'fiscalpva-nucleo.jar'),
            os.path.join(efd_pva_path, 'lib', 'br.gov.serpro.sped.fiscalpva', 'fiscalpva-persistencia.jar'),
            os.path.join(efd_pva_path, 'lib', 'br.gov.serpro.sped.fiscalpva', 'fiscalpva-relatorios.jar'),
            os.path.join(efd_pva_path, 'lib', 'br.gov.serpro.sped.fiscalpva', 'fiscalpva-validador.jar'),
            os.path.join(efd_pva_path, 'lib', 'br.gov.serpro.ppgd', 'ppgd-infraestrutura.jar')
        ]

        logger.addHandler(self.queue_handler)
        try:
            retorno = py4j.java_gateway.launch_gateway(
                classpath=os.pathsep.join(class_path),
                java_path=str((GeneralConfiguration.get().efd_java_path() / 'java').absolute()),
                javaopts=['-Dfile.encoding=Cp1252'],
                cwd=efd_pva_path,
                redirect_stdout=self.log_queue,
                redirect_stderr=self.log_queue,
                die_on_exit=True,
                return_proc=True
            )
            self._porta_gateway = retorno[0]
            self._processoJVM = retorno[1]
            self._gateway = JavaGateway(
                gateway_parameters=GatewayParameters(port=self._porta_gateway),
                java_process=self._processoJVM)
            self._is_efd_started = False
        except py4j.java_gateway.Py4JError as e:
            logger.exception(
                'Não foi encontrado o Java adequado nessa máquina para acessar EFD PVA. Instale o JDK versão 8.')
            raise e

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()

    def _close(self):
        logger.removeHandler(self.queue_handler)
        if self._gateway is not None:
            try:
                if self._is_efd_started:
                    self._gateway.jvm.br.gov.sp.efdpvainspector.EFDComprehension.encerramentoBD()
                    self._is_efd_started = False
                    logger.debug('Encerrado banco de dados do EFD PVA ICMS IPI.')
                self._gateway.shutdown()
                self._processoJVM.kill()
                self._gateway = None
            except Exception:
                logger.exception('Ocorreu erro durante encerramento do EFD PVA.')

    def __efd_pva(self) -> JavaGateway:
        if not self._is_efd_started:
            try:
                logger.info('Iniciando banco de dados do EFD PVA ICMS IPI...')
                self._gateway.jvm.br.gov.sp.efdpvainspector.EFDComprehension.inicializacaoSimplesBD()
                self._is_efd_started = True
            except py4j.java_gateway.Py4JJavaError as e:
                self._gateway = None
                self._is_efd_started = False
                logger.exception(
                    'Ocorreu problema na inicializacao do banco de dados do EFD PVA ICMS IPI.'
                )
                raise e
        return self._gateway

    def get_efd_pva_current_version(self) -> str:
        return self._gateway.jvm.br.gov.sp.efdpvainspector.EFDComprehension.verificaVersao()

    def import_efd(self, efd_file: Path, window: PySimpleGUI.Window, evento: threading.Event):
        try:
            if evento.is_set():
                window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-PVA', 'STOP'])
                return
            window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-PVA', 'BEGIN'])
            logger.info(f'Importando arquivo {efd_file} no EFD PVA ICMS IPI...')
            self.__efd_pva().jvm.br.gov.sp.efdpvainspector.EFDImporter.importaEFD(
                str(efd_file), str(self._efds_json_path))
            window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-PVA', 'END'])
        except Exception as e:
            logger.exception(f'Ocorreu uma falha na importação da EFD {efd_file}: {e}')
            window.write_event_value('-DATA-EXTRACTION-STATUS-', ['EFD-PVA', 'FAILURE'])
            raise e

    def print_LRAICMS(self, referencia: datetime.date, arquivo: Path):
        cnpj_sem_digitos = get_current_audit().cnpj_only_digits()
        ie = get_current_audit().ie_only_digits()
        logger.info(f'Imprimindo LRAICMS de {referencia.strftime("%m/%Y")}...')
        referencia = f"01/{referencia.strftime('%m/%Y')}"
        try:
            self.__efd_pva().jvm.br.gov.sp.efdpvainspector.EFDPrinter.imprimeApuracao(cnpj_sem_digitos, ie, referencia,
                                                                                      str(arquivo.absolute()))
        except py4j.java_gateway.Py4JJavaError as e:
            mensagem = str(e.java_exception).encode('iso-8859-1').decode()
            mensagem = mensagem[mensagem.find(' '):]
            logger.exception(f'Ocorreu uma falha na impressão do LRAICMS de {referencia}: {mensagem}')
            raise Exception(mensagem)

    def print_LRI(self, referencia: datetime.date, arquivo: Path):
        cnpj_sem_digitos = get_current_audit().cnpj_only_digits()
        ie = get_current_audit().ie_only_digits()
        logger.info(f'Imprimindo LRI de {referencia.strftime("%m/%Y")}...')
        referencia = f"01/{referencia.strftime('%m/%Y')}"
        try:
            self.__efd_pva().jvm.br.gov.sp.efdpvainspector.EFDPrinter.imprimeInventario(cnpj_sem_digitos, ie,
                                                                                        referencia,
                                                                                        str(arquivo.absolute()))
        except py4j.java_gateway.Py4JJavaError as e:
            mensagem = str(e.java_exception).encode('iso-8859-1').decode()
            mensagem = mensagem[mensagem.find(' '):]
            logger.exception(f'Ocorreu uma falha na impressão do LRI de {referencia}: {mensagem}')
            raise Exception(mensagem)

    def print_LRE(self, referencia: datetime.date, arquivo: Path):
        cnpj_sem_digitos = get_current_audit().cnpj_only_digits()
        ie = get_current_audit().ie_only_digits()
        logger.info(f'Imprimindo LRE de {referencia.strftime("%m/%Y")}...')
        referencia = f"01/{referencia.strftime('%m/%Y')}"
        try:
            self.__efd_pva().jvm.br.gov.sp.efdpvainspector.EFDPrinter.imprimeEntradas(cnpj_sem_digitos, ie, referencia,
                                                                                      str(arquivo.absolute()))
        except py4j.java_gateway.Py4JJavaError as e:
            mensagem = str(e.java_exception).encode('iso-8859-1').decode()
            mensagem = mensagem[mensagem.find(' '):]
            logger.exception(f'Ocorreu uma falha na impressão do LRE de {referencia}: {mensagem}')
            raise Exception(mensagem)

    def print_LRS(self, referencia: datetime.date, arquivo: Path):
        cnpj_sem_digitos = get_current_audit().cnpj_only_digits()
        ie = get_current_audit().ie_only_digits()
        logger.info(f'Imprimindo LRS de {referencia.strftime("%m/%Y")}...')
        referencia = f"01/{referencia.strftime('%m/%Y')}"
        try:
            self.__efd_pva().jvm.br.gov.sp.efdpvainspector.EFDPrinter.imprimeSaidas(cnpj_sem_digitos, ie, referencia,
                                                                                    str(arquivo.absolute()))
        except py4j.java_gateway.Py4JJavaError as e:
            mensagem = str(e.java_exception).encode('iso-8859-1').decode()
            mensagem = mensagem[mensagem.find(' '):]
            logger.exception(f'Ocorreu uma falha na impressão do LRS de {referencia}: {mensagem}')
            raise Exception(mensagem)

    def list_imported_files(self, cnpj):
        efddb = None
        cur = None
        # para garantir inicialização do BD do EFD PVA ICMS
        self.__efd_pva()
        logger.info('Levantando períodos das EFDs importadas...')
        try:
            efddb = mysql.connector.connect(host='127.0.0.1', port=GeneralConfiguration.get().efd_port,
                                            charset='latin1',
                                            user='spedfiscal', password='spedfiscal', db='master')
            cur = efddb.cursor()
            cnpj_sem_digitos = re.sub(r"[^\d]", "", cnpj).zfill(14)
            cur.execute('SELECT localizacaoArquivo '
                        'FROM escrituracaofiscal where cpf_cnpj=%s',
                        [cnpj_sem_digitos])
            return list(map(lambda row: row[0], cur.fetchall()))
        except mysql.connector.errors.Error as e:
            logger.exception('Falha na conexão ao banco de dados do EFD PVA')
        finally:
            if cur:
                cur.close()
            if efddb:
                efddb.close()

    def dump_db(self, database: str, dump_file: Path):
        comando = str(Path('mysqldump') / 'mysqldump.exe') + ' --user=spedfiscal --password=spedfiscal ' \
                                                             f'--host=127.0.0.1 ' \
                                                             f'--port={GeneralConfiguration.get().efd_port} ' \
                                                             f'--result-file={str(dump_file)} ' \
                                                             '--skip-add-locks --compatible=postgresql ' \
                                                             '--skip-quote-names '
        # --default-character-set=latin1
        for ignored_table in ['docentrada', 'docsaida', 'inconsistencia', 'metainf', 'resumototaissaida',
                              'resumototaissaida_chaveregpai',
                              'docentrada', 'tabelaexternareferenciada', 'uddate_table']:
            comando += f'--ignore-table={database}.{ignored_table} '
        comando += f'{database}'
        dump_file.unlink(missing_ok=True)
        # para garantir inicialização do BD do EFD PVA ICMS
        self.__efd_pva()
        try:
            subprocess.check_output(comando.split(' '))
        except subprocess.CalledProcessError as cpe:
            raise Exception(f'Falha na execução do comando mysqldump: {cpe.output}')

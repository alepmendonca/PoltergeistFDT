import datetime
import json
from pathlib import Path
from unittest import TestCase, mock

import GeneralConfiguration
import GeneralFunctions


class TestConfiguration(TestCase):
    config: GeneralConfiguration.Configuration
    path = Path('teste_afr_configuration.json')

    def setUp(self) -> None:
        with mock.patch('GeneralConfiguration.GeneralFunctions.get_local_dados_afr_path',
                        return_value=self.path):
            self.config = GeneralConfiguration.Configuration()

    def tearDown(self) -> None:
        self.path.unlink(missing_ok=True)

    @mock.patch('GeneralConfiguration.keyring')
    def test_intranet_pass(self, mock_keyring):
        mock_keyring.get_password.return_value = None
        self.assertIsNone(self.config.intranet_pass)
        mock_keyring.get_password.return_value = 'teste'
        self.config.intranet_pass = 'teste123'
        mock_keyring.set_password.assert_called_once_with(mock.ANY, 'intranet', 'teste123')
        self.assertEqual('teste', self.config.intranet_pass)

    @mock.patch('GeneralConfiguration.keyring')
    def test_certificado_pass(self, mock_keyring):
        mock_keyring.get_password.return_value = None
        self.assertIsNone(self.config.certificado_pass)
        mock_keyring.get_password.return_value = 'teste'
        self.config.certificado_pass = 'teste123'
        mock_keyring.set_password.assert_called_once_with(mock.ANY, 'certificate', 'teste123')
        self.assertEqual('teste', self.config.certificado_pass)

    @mock.patch('GeneralConfiguration.keyring')
    def test_sigadoc_pass(self, mock_keyring):
        mock_keyring.get_password.return_value = None
        self.assertIsNone(self.config.sigadoc_pass)
        mock_keyring.get_password.return_value = 'teste'
        self.config.sigadoc_pass = 'teste123'
        mock_keyring.set_password.assert_called_once_with(mock.ANY, 'sigadoc', 'teste123')
        self.assertEqual('teste', self.config.sigadoc_pass)

    @mock.patch('GeneralConfiguration.keyring')
    def test_postgres_pass(self, mock_keyring):
        mock_keyring.get_password.return_value = None
        self.assertIsNone(self.config.postgres_pass)
        mock_keyring.get_password.return_value = 'teste'
        self.config.postgres_pass = 'teste123'
        mock_keyring.set_password.assert_called_once_with(mock.ANY, 'postgres', 'teste123')
        self.assertEqual('teste', self.config.postgres_pass)

    def test_drt_sigla(self):
        self.assertIsNone(self.config.drt_sigla)
        with self.assertRaises(ValueError) as ctx:
            self.config.drt_sigla = 'nada a ver'
        self.assertEqual('Sigla de delegacia inválida: nada a ver', str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            self.config.drt_sigla = 'DRT-17'
        self.config.drt_sigla = ' 05 - DRT-05 - CAMPINAS\n'
        self.assertEqual('DRT-5', self.config.drt_sigla)
        self.config.drt_sigla = ' 10 - DRT15 - araraquara\n'
        self.assertEqual('DRT-15', self.config.drt_sigla)
        self.config.drt_sigla = 'DRT-12'
        self.assertEqual('DRT-12', self.config.drt_sigla)
        self.config.drt_sigla = 'C1 - DRTC-I - SAO PAULO'
        self.assertEqual('DRTC-I', self.config.drt_sigla)

    def test_equipe_fiscal(self):
        self.assertEqual(0, self.config.nucleo_fiscal())
        self.assertEqual(0, self.config.equipe_fiscal)
        with self.assertRaises(ValueError) as ctx:
            self.config.equipe_fiscal = 'nada a ver'
        self.assertEqual('Equipe fiscal inválida: nada a ver', str(ctx.exception))
        self.config.equipe_fiscal = '34'
        self.assertEqual(34, self.config.equipe_fiscal)
        self.assertEqual(3, self.config.nucleo_fiscal())
        self.config.equipe_fiscal = 52
        self.assertEqual(52, self.config.equipe_fiscal)
        self.assertEqual(5, self.config.nucleo_fiscal())

    def test_inidoneos_last_update(self):
        self.assertEqual(datetime.date(2000, 1, 1), self.config.inidoneos_last_update)
        self.config.inidoneos_last_update = datetime.date(2022, 5, 1)
        self.assertEqual(datetime.date(2022, 5, 1), self.config.inidoneos_last_update)
        with self.assertRaises(ValueError) as ctx:
            self.config.inidoneos_last_update = 'nada a ver'
        self.assertEqual('Data para atualização de inidôneos inválida: nada a ver', str(ctx.exception))
        self.config.inidoneos_last_update = '01/11/2019'
        self.assertEqual(datetime.date(2019, 11, 1), self.config.inidoneos_last_update)

    def test_inidoneos(self):
        with self.assertRaises(ValueError) as ctx:
            self.config.inidoneos_date_from_file(Path('nada a ver.txt'))
        self.assertEqual('Nome de arquivo de inidôneos inválido - deve ter mês e ano no nome!', str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            self.config.inidoneos_date_from_file(Path('Inidôneos January 2020.zip'))
        self.assertEqual('Não localizei o mês de geração do arquivo no nome, achei que era January', str(ctx.exception))
        self.assertEqual(datetime.date(2021, 4, 1),
                         self.config.inidoneos_date_from_file(Path('Inidôneos Abril-2021.zip')))
        self.assertEqual(datetime.date(2023, 6, 1),
                         self.config.inidoneos_date_from_file(Path('Inidoneos Jun 2023.zip')))

    def test_gia(self):
        with self.assertRaises(ValueError) as ctx:
            self.config.gia_date_from_file(Path('nada a ver.txt'))
        self.assertEqual('Nome de arquivo de GIAs inválido - deve ter mês e ano no nome!', str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            self.config.gia_date_from_file(Path('GIAs January 2020.zip'))
        self.assertEqual('Não localizei o mês de geração do arquivo no nome, achei que era January', str(ctx.exception))
        self.assertEqual(datetime.date(2021, 12, 1),
                         self.config.gia_date_from_file(Path('GIAs 2013 a 2021 Dezembro 2021.zip')))
        self.assertEqual(datetime.date(2023, 2, 1),
                         self.config.gia_date_from_file(Path('GIAs muito tempo 2012 - Fev-2023.zip')))

    def test_cadesp(self):
        with self.assertRaises(ValueError) as ctx:
            self.config.cadesp_date_from_file(Path('nada a ver.txt'))
        self.assertEqual('Nome de arquivo de Cadesp inválido - deve ter mês e ano no nome!', str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            self.config.cadesp_date_from_file(Path('CadSefaz_Regimes January 2020.zip'))
        self.assertEqual('Não localizei o mês de geração do arquivo no nome, achei que era January', str(ctx.exception))
        self.assertEqual(datetime.date(2021, 11, 1),
                         self.config.cadesp_date_from_file(Path('CadSefaz_SAFI Novembro-2021.zip')))
        self.assertEqual(datetime.date(2023, 8, 1),
                         self.config.cadesp_date_from_file(Path('CadSefaz_Regimes Ago 2023.zip')))

    def test_postgres_port(self):
        self.assertEqual(5431, self.config.postgres_port)
        with self.assertRaises(ValueError) as ctx:
            self.config.postgres_port = 'eita'
        self.assertEqual('Porta deve ser um número!', str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            self.config.postgres_port = '-123'
        self.assertEqual('Porta deve ser um número maior que zero!', str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            self.config.postgres_port = -200
        self.assertEqual('Porta deve ser um número maior que zero!', str(ctx.exception))
        self.config.postgres_port = '778'
        self.assertEqual(778, self.config.postgres_port)
        self.config.postgres_port = 6654
        self.assertEqual(6654, self.config.postgres_port)

    def test_drt_nome(self):
        self.assertIsNone(self.config.drt_nome)
        self.config.drt_nome = 'qualquer coisa'
        self.assertIsNone(self.config.drt_nome)
        self.config.drt_nome = 'DELEGACIA REGIONAL TRIBUTÁRIA DE GUARULHOS'
        self.assertEqual('DRT-13', self.config.drt_sigla)
        self.assertEqual('DELEGACIA REGIONAL TRIBUTÁRIA DE GUARULHOS', self.config.drt_nome)

    def test_efd_path(self):
        self.assertEqual(Path('efd-pva'), self.config.efd_path)
        self.assertEqual(Path('efd-pva') / 'jre' / 'bin', self.config.efd_java_path())
        efd_pva_path = Path('bagaca')
        with self.assertRaises(ValueError) as ctx:
            self.config.efd_path = efd_pva_path
        self.assertEqual('Caminho para EFD PVA ICMS inválido. É necessário que exista um arquivo java.exe '
                         'dentro da subpasta bagaca\\jre\\bin', str(ctx.exception))
        javapath = efd_pva_path / Path('jre/bin/java.exe')
        try:
            javapath.parent.mkdir(parents=True, exist_ok=True)
            with javapath.open(mode='w') as f:
                f.write('asdf')
            self.config.efd_path = efd_pva_path
            self.assertEqual(efd_pva_path, self.config.efd_path)
            self.assertEqual(efd_pva_path / 'jre' / 'bin', self.config.efd_java_path())
        finally:
            while javapath != efd_pva_path:
                if javapath.is_file():
                    javapath.unlink(missing_ok=True)
                elif javapath.is_dir():
                    javapath.rmdir()
                javapath = javapath.parent
            javapath.rmdir()

    def test_efd_port(self):
        self.assertEqual(3337, self.config.efd_port)
        with self.assertRaises(ValueError) as ctx:
            self.config.efd_port = 'eita'
        self.assertEqual('Porta deve ser um número!', str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            self.config.efd_port = '-123'
        self.assertEqual('Porta deve ser um número maior que zero!', str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            self.config.efd_port = -200
        self.assertEqual('Porta deve ser um número maior que zero!', str(ctx.exception))
        self.config.efd_port = '778'
        self.assertEqual(778, self.config.efd_port)
        self.config.efd_port = 6654
        self.assertEqual(6654, self.config.efd_port)

    def test_save(self):
        self.assertFalse(self.path.is_file())
        GeneralConfiguration._singleton = None
        with mock.patch('GeneralConfiguration.GeneralFunctions.get_local_dados_afr_path',
                        return_value=self.path):
            self.assertIsNone(GeneralConfiguration.get())
            self.config.drt_sigla = 'DRTC-III'
            self.config.equipe_fiscal = 44
            self.config.nome = 'AFRE TESTE'
            self.config.certificado = 'AFRE TESTE:12345678900'
            self.config.email = 'teste@fazenda.sp.gov.br'
            self.config.funcional = '53.445-7'
            self.config.intranet_login = 'teste'
            self.config.sigadoc_login = 'testesigadoc'
            self.config.save()
        self.assertTrue(self.path.is_file())
        with self.path.open(mode='r') as outfile:
            dicionario = json.load(outfile)
        self.assertEqual(
            {'drt', 'nome', 'certificado', 'efd_path', 'efd_port', 'sigadoc_login', 'funcional',
             'email', 'equipe', 'inidoneos_last_update', 'intranet_login', 'max_epat_attachment_size',
             'postgres_address', 'postgres_dbname', 'postgres_port', 'postgres_user', 'ultima_pasta',
             'cadesp_last_update', 'gia_last_update'},
            set(dicionario.keys()))
        with mock.patch('GeneralConfiguration.GeneralFunctions.get_local_dados_afr_path',
                        return_value=self.path):
            self.assertIsNotNone(GeneralConfiguration.get())
            self.assertEqual('DELEGACIA REGIONAL TRIBUTÁRIA DA CAPITAL-III', GeneralConfiguration.get().drt_nome)
            self.assertEqual('DRTC-III', GeneralConfiguration.get().drt_sigla)
            self.assertEqual('AFRE TESTE', GeneralConfiguration.get().nome)
            self.assertEqual('AFRE TESTE:12345678900', GeneralConfiguration.get().certificado)
            self.assertEqual(Path('efd-pva').absolute(), GeneralConfiguration.get().efd_path)
            self.assertEqual(3337, GeneralConfiguration.get().efd_port)
            self.assertEqual('testesigadoc', GeneralConfiguration.get().sigadoc_login)
            self.assertEqual('53.445-7', GeneralConfiguration.get().funcional)
            self.assertEqual('teste@fazenda.sp.gov.br', GeneralConfiguration.get().email)
            self.assertEqual(44, GeneralConfiguration.get().equipe_fiscal)
            self.assertEqual(4, GeneralConfiguration.get().nucleo_fiscal())
            self.assertEqual('teste', GeneralConfiguration.get().intranet_login)
            self.assertEqual(8, GeneralConfiguration.get().max_epat_attachment_size)
            self.assertEqual('localhost', GeneralConfiguration.get().postgres_address)
            self.assertEqual('postgres', GeneralConfiguration.get().postgres_dbname)
            self.assertEqual(5431, GeneralConfiguration.get().postgres_port)
            self.assertEqual('postgres', GeneralConfiguration.get().postgres_user)
            self.assertEqual(GeneralFunctions.get_user_path().absolute(), GeneralConfiguration.get().ultima_pasta)
            self.assertEqual(datetime.date(2000, 1, 1), GeneralConfiguration.get().inidoneos_last_update)
            self.assertEqual(datetime.date(2000, 1, 1), GeneralConfiguration.get().gia_last_update)
            self.assertEqual(datetime.date(2000, 1, 1), GeneralConfiguration.get().cadesp_last_update)


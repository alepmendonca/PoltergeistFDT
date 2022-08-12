import datetime
import json
import os
import shutil
from unittest import TestCase
from pathlib import Path
import Audit
from ConfigFiles import ConfigFileDecoderException


class AuditTestSetup(TestCase):
    _main_path = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._main_path = Path(__file__).parent.resolve()
        (cls._main_path / 'Dados').mkdir(exist_ok=True)
        (cls._main_path / 'Achados').mkdir(exist_ok=True)
        (cls._main_path / 'AIIM').mkdir(exist_ok=True)

    def setUp(self) -> None:
        shutil.copyfile(os.path.join(self._main_path, 'template', 'dados_auditoria.json'),
                        os.path.join(self._main_path, 'Dados', 'dados_auditoria.json'))
        shutil.copyfile(os.path.join(self._main_path, 'template', 'Arrazoado - Teste.xlsm'),
                        os.path.join(self._main_path, 'Achados', 'Arrazoado - Teste.xlsm'))
        Audit.set_audit(self._main_path)

    def tearDown(self) -> None:
        for subpasta in ['Dados', 'Achados', 'AIIM', 'Notificações']:
            for path, _, arquivos in os.walk(self._main_path / subpasta):
                for arquivo in arquivos:
                    (Path(path) / arquivo).unlink(missing_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            shutil.rmtree(cls._main_path / 'Dados')
            shutil.rmtree(cls._main_path / 'Achados')
            shutil.rmtree(cls._main_path / 'AIIM')
            shutil.rmtree(cls._main_path / 'Notificações')
        except:
            pass


class AuditTest(AuditTestSetup):

    def test_audit_contents(self):
        audit = Audit.get_current_audit()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.empresa, 'TESTE COMERCIAL LTDA')
        self.assertEqual(audit.logradouro, 'AVENIDA BAGACA FRANCO')
        self.assertEqual(audit.numero, '334')
        self.assertEqual(audit.complemento, 'FUNDOS')
        self.assertEqual(audit.bairro, 'CENTRO')
        self.assertEqual(audit.cep, '01.234-000')
        self.assertEqual(audit.cidade, 'SAO PAULO')
        self.assertEqual(audit.uf, 'SP')
        self.assertEqual('AVENIDA BAGACA FRANCO, 334 - FUNDOS - CENTRO - SAO PAULO/SP - CEP 01.234-000',
                         audit.endereco_completo())
        self.assertEqual(audit.cnpj_only_digits(), '10203040000150')
        self.assertEqual(audit.ie_only_digits(), '012345678910')
        self.assertEqual(audit.osf_only_digits(), '01168489176')
        self.assertEqual(audit.schema, 'teste')
        self.assertEqual(audit.situacao, 'Ativo')
        self.assertEqual(audit.inicio_auditoria, datetime.date(2017, 1, 1))
        self.assertEqual(audit.fim_auditoria, datetime.date(2018, 12, 31))
        self.assertEqual(audit.inicio_inscricao, datetime.date(2009, 5, 13))
        self.assertEqual(audit.inicio_situacao, datetime.date(2010, 10, 16))
        self.assertTrue(audit.is_aiim_open)
        self.assertEqual('1.111.111-2', audit.aiim_number)
        self.assertEqual(1111111, audit.aiim_number_no_digit())

    def test_audit_rpa_timerange_unlimited(self):
        audit = Audit.get_current_audit()
        audit.fim_auditoria = datetime.date.today()
        self.assertEqual([[datetime.date(2018, 1, 1), datetime.date.today()]],
                         audit.get_periodos_da_fiscalizacao(rpa=True))

    def test_audit_rpa_timerange_limited_audit_ending(self):
        audit = Audit.get_current_audit()
        self.assertEqual([[datetime.date(2018, 1, 1), audit.fim_auditoria]],
                         audit.get_periodos_da_fiscalizacao(rpa=True))

    def test_audit_sn_timerange_limited_audit_beginning(self):
        audit = Audit.get_current_audit()
        self.assertEqual([[audit.inicio_auditoria, datetime.date(2017, 12, 31)]],
                         audit.get_periodos_da_fiscalizacao(rpa=False))

    def test_audit_sn_timerange_unlimited(self):
        audit = Audit.get_current_audit()
        audit.inicio_auditoria = datetime.date(2000, 1, 1)
        self.assertEqual([[datetime.date(2009, 5, 13), datetime.date(2017, 12, 31)]],
                         audit.get_periodos_da_fiscalizacao(rpa=False))

    def test_audit_notifications(self):
        audit = Audit.get_current_audit()
        self.assertEqual(1, len(audit.notificacoes))
        self.assertEqual('Divergências RBA x PGDAS-D', audit.notificacoes[0].verificacao.name)
        self.assertEqual('PGDAS', audit.notificacoes[0].planilha)
        self.assertIsNone(audit.notificacoes[0].df)

    def test_audit_aiim_itens(self):
        audit = Audit.get_current_audit()
        self.assertEqual(2, len(audit.aiim_itens))

        item = list(filter(
            lambda i: i.verificacao.name == 'Documentos de entrada tributados (NF-e e CT-e) não escriturados no LRE',
            audit.aiim_itens))[0]
        self.assertEqual(1, item.item)
        self.assertTrue(item.has_aiim_item_number())
        self.assertEqual('IC/N/FIS/000002375/2022', item.notificacao)
        self.assertEqual(self._main_path / 'Notificações' / f'2022-2375 - {item.verificacao.name}',
                          item.notification_path())
        self.assertEqual(item.notification_path() / 'Resposta', item.notification_response_path())
        self.assertIsNone(item.notificacao_resposta)
        self.assertEqual('planilha', item.planilha)
        self.assertEqual('V', item.infracao.inciso)
        self.assertEqual('a', item.infracao.alinea)
        self.assertEqual('Tributada', item.infracao.operation_type)
        item.notificacao_resposta = 'SFP-EXP-2020/465'
        self.assertEqual('SFP-EXP-2020/465', item.notificacao_resposta)

        item = list(filter(
            lambda
                i: i.verificacao.name == 'Documentos de entrada não tributados (NF-e e CT-e) não escriturados no LRE',
            audit.aiim_itens))[0]
        self.assertEqual(0, item.item)
        self.assertFalse(item.has_aiim_item_number())
        self.assertEqual('IC/N/FIS/000002375/2022', item.notificacao)
        self.assertEqual(self._main_path / 'Notificações' / f'2022-2375 - {item.verificacao.name}',
                          item.notification_path())
        self.assertEqual(item.notification_path() / 'Resposta', item.notification_response_path())
        self.assertIsNone(item.notificacao_resposta)
        self.assertEqual('planilha', item.planilha)
        self.assertEqual('V', item.infracao.inciso)
        self.assertEqual('a', item.infracao.alinea)
        self.assertEqual('Não Tributada', item.infracao.operation_type)

    def test_audit_aiim_item_notification_errors(self):
        audit = Audit.get_current_audit()
        item = list(filter(
            lambda i: i.verificacao.name == 'Documentos de entrada tributados (NF-e e CT-e) não escriturados no LRE',
            audit.aiim_itens))[0]
        with self.assertRaises(ValueError) as context:
            item.notificacao = 'Notificação 04'
            self.assertEqual('Número de notificação inválido: Notificação 04', context.exception)
        with self.assertRaises(ValueError) as context:
            item.notificacao_resposta = 'Resposta 04'
            self.assertEqual('Número do expediente Sem Papel em resposta à notificação inválido: Notificação 04',
                              context.exception)

    def test_setter_errors(self):
        audit = Audit.get_current_audit()
        with self.assertRaises(ValueError) as context:
            audit.inicio_auditoria = '1651'
            self.assertEqual('Início de auditoria em formato errado (mm/aaaa): 1651', context.exception)
        with self.assertRaises(ValueError) as context:
            audit.inicio_auditoria = '13/2015'
            self.assertEqual('Início de auditoria em formato errado (mm/aaaa): 13/2015', context.exception)
        with self.assertRaises(ValueError) as context:
            audit.inicio_auditoria = '01/1999'
            self.assertEqual('Início de auditoria em formato errado (mm/aaaa): 01/1999', context.exception)
        with self.assertRaises(ValueError) as context:
            audit.inicio_auditoria = '01/2020'
            self.assertEqual('Início de auditoria 01/2020 deve ser maior que o final 12/2018', context.exception)
        with self.assertRaises(ValueError) as context:
            audit.fim_auditoria = '1651'
            self.assertEqual('Fim de auditoria em formato errado (mm/aaaa): 1651', context.exception)
        with self.assertRaises(ValueError) as context:
            audit.fim_auditoria = '13/2015'
            self.assertEqual('Fim de auditoria em formato errado (mm/aaaa): 13/2015', context.exception)
        with self.assertRaises(ValueError) as context:
            audit.fim_auditoria = '01/1999'
            self.assertEqual('Fim de auditoria em formato errado (mm/aaaa): 01/1999', context.exception)
        with self.assertRaises(ValueError) as context:
            audit.fim_auditoria = '01/2015'
            self.assertEqual('Início de auditoria 01/2017 deve ser maior que o final 01/2015', context.exception)
        with self.assertRaises(ValueError) as context:
            audit.inicio_inscricao = '01/1999'
            self.assertEqual('Início da inscrição em formato errado (dd/mm/aaaa): 01/1999', context.exception)
        with self.assertRaises(ValueError) as context:
            audit.inicio_situacao = '01/1999'
            self.assertEqual('Início da situação em formato errado (dd/mm/aaaa): 01/1999', context.exception)

    def test_save_audit(self):
        audit = Audit.get_current_audit()
        with (self._main_path / 'Dados' / 'dados_auditoria.json').open(mode='r') as outfile:
            texto_original = outfile.read()
        audit.save()
        with (self._main_path / 'Dados' / 'dados_auditoria.json').open(mode='r') as outfile:
            texto_final = outfile.read()
        self.assertEqual(texto_original, texto_final)

    def test_no_audit(self):
        Audit.set_audit(None)
        self.assertIsNone(Audit.get_current_audit())
        (self._main_path / 'Dados' / 'dados_auditoria.json').unlink(missing_ok=True)
        Audit.set_audit(self._main_path)
        self.assertIsNone(Audit.get_current_audit())
        Audit.create_new_audit(self._main_path)
        self.assertIsNotNone(Audit.get_current_audit())

    def test_create_audit_with_json_file_just_opens_it(self):
        Audit.get_current_audit().save()
        with (self._main_path / 'template' / 'dados_auditoria.json').open(mode='r') as outfile:
            template = outfile.read()
        with (self._main_path / 'Dados' / 'dados_auditoria.json').open(mode='r') as outfile:
            texto_final = outfile.read()
        self.assertEqual(template, texto_final)

    def test_no_analysis_from_file(self):
        dados = {
            'empresa': 'bagaca',
            'notificacoes': [{'verificacao': 'bagacinha', 'planilha': 'template'}]
        }
        with (self._main_path / 'Dados' / 'dados_auditoria.json').open(mode='w') as outfile:
            json.dump(dados, outfile, sort_keys=True, indent=3)
        with self.assertRaises(ConfigFileDecoderException) as context:
            Audit.set_audit(self._main_path)
            self.assertEqual('Não existe verificação chamada bagacinha. '
                             'Altere manualmente o arquivo de configurações da auditoria.', context.exception)

    def test_notification_subs(self):
        audit = Audit.get_current_audit()
        item = audit.aiim_itens[0]
        item.notification_path()
        audit.notification_path().mkdir(exist_ok=True)
        item.notification_path().mkdir(exist_ok=True)
        item.notification_response_path().mkdir(exist_ok=True)
        self.assertEqual('OSF 01.1.68489/17-6 - Teste',
                         item.notificacao_titulo('OSF <osf> - Teste'))
        item.clear_cache()
        self.assertEqual('OSF 01.1.68489/17-6, documentos modelos 55 e 57 dos períodos de abril de 2019 e julho de 2020',
                         item.notificacao_corpo('OSF <osf>, documentos <modelos> d<periodo>'))
        item.clear_cache()
        self.assertEqual('documentos do período de 2019 a 2020',
                         item.notificacao_corpo('documentos d<periodoAAAA>'))
        item.clear_cache()
        item.infracao.relatorio_circunstanciado = \
            'Deixou de pagar imposto nos documentos <modelos> d<periodoAAAA>.'
        self.assertEqual('Deixou de pagar imposto nos documentos modelos 55 e 57 do período de 2019 a 2020.\n'
                         'O contribuinte foi notificado por meio da notificação DEC IC/N/FIS/000002375/2022, '
                         'sem apresentar resposta à fiscalização.',
                         item.relatorio_circunstanciado())
        item.clear_cache()
        item.infracao.relatorio_circunstanciado = \
            'Deixou de pagar imposto nos documentos <modelos> d<periodoAAAA>.'
        item.notificacao_resposta = 'SFP-EXP-2022/45646'
        self.assertEqual('Deixou de pagar imposto nos documentos modelos 55 e 57 do período de 2019 a 2020.\n'
                         'O contribuinte foi notificado por meio da notificação DEC IC/N/FIS/000002375/2022, '
                         'com resposta dada no expediente SFP-EXP-2022/45646, '
                         'mas sem justificativas legais para todos os pontos questionados.',
                         item.relatorio_circunstanciado())

import datetime
import json
import os
import shutil
import threading
import unittest

import PySimpleGUI as sg
from unittest import TestCase, mock
from unittest.mock import call

from pathlib import Path

import pandas as pd

import Controller
import Audit
import GeneralFunctions
from ConfigFiles import Analysis
from WebScraper import WebScraperTimeoutException
from tests.test_Audit import AuditTestSetup


class ControllerTest(TestCase):
    _main_path = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._main_path = Path(__file__).parent.resolve()
        os.makedirs(os.path.join(cls._main_path, 'Dados'), exist_ok=True)
        os.makedirs(os.path.join(cls._main_path, 'Achados'), exist_ok=True)

    def setUp(self) -> None:
        shutil.copyfile(os.path.join(self._main_path, 'template', 'dados_auditoria.json'),
                        os.path.join(self._main_path, 'Dados', 'dados_auditoria.json'))
        shutil.copyfile(os.path.join(self._main_path, 'template', 'Arrazoado - Teste.xlsm'),
                        os.path.join(self._main_path, 'Achados', 'Arrazoado - Teste.xlsm'))

    def tearDown(self) -> None:
        os.remove(os.path.join(self._main_path, 'Dados', 'dados_auditoria.json'))
        os.remove(os.path.join(self._main_path, 'Achados', 'Arrazoado - Teste.xlsm'))
        (self._main_path / 'analise.json').unlink(missing_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            shutil.rmtree(cls._main_path / 'Dados')
            shutil.rmtree(cls._main_path / 'Achados')
            shutil.rmtree(cls._main_path / 'Notificações')
        except:
            pass

    def test_add_analysis_with_df_one_datetime_column(self):
        analysis = Analysis({
            "verificacao": "teste",
            "funcao": {
                "nome": "verifica_omissao_efds",
                "descricao": "Não usada nesse teste"
            },
            "infracoes": ["Vm-LRAICMS"]
        })
        dados = {
            'empresa': 'bagaca'
        }
        with (self._main_path / 'Dados' / 'dados_auditoria.json').open(mode='w') as outfile:
            json.dump(dados, outfile, sort_keys=True, indent=3)
        Audit.set_audit(self._main_path)
        audit = Audit.get_current_audit()
        df = pd.DataFrame(columns=['Referência'],
                          data=[[datetime.date(2022, 1, 1)],
                                [datetime.date(2022, 4, 1)]])
        df = df.astype({'Referência': 'datetime64[ns]'})
        Controller.add_analysis_to_audit(analysis, df=df)
        audit.save()
        self.assertEqual(0, len(audit.notificacoes))
        self.assertEqual(1, len(audit.aiim_itens))
        self.assertIsInstance(audit.aiim_itens[0].df, pd.DataFrame)
        self.assertListEqual(['Referência'], audit.aiim_itens[0].df.keys().tolist())
        self.assertListEqual([datetime.datetime(2022, 1, 1), datetime.datetime(2022, 4, 1)],
                             GeneralFunctions.get_dates_from_df(audit.aiim_itens[0].df))

    def test_add_analysis_with_df_more_than_one_column(self):
        analysis_dict = {
            "verificacao": "teste",
            "funcao": {
                "nome": "verifica_omissao_efds",
                "descricao": "Não usada nesse teste",
                "cabecalho": ['data', 'total']
            },
            "infracoes": ["Vm-LRAICMS"]
        }
        analysis = Analysis(analysis_dict)
        dados = {
            'empresa': 'bagaca'
        }
        with (self._main_path / 'Dados' / 'dados_auditoria.json').open(mode='w') as outfile:
            json.dump(dados, outfile, sort_keys=True, indent=3)
        Audit.set_audit(self._main_path)
        audit = Audit.get_current_audit()
        df = pd.DataFrame(columns=['Referência', 'Valor'],
                          data=[[datetime.date(2022, 1, 1), 120.3],
                                [datetime.date(2022, 4, 1), 400.2]])
        df = df.astype({'Referência': 'datetime64[ns]', 'Valor': 'Float64'})
        Controller.add_analysis_to_audit(analysis, df=df)
        audit.save()
        with (self._main_path / 'analise.json').open(mode='w') as analise_file:
            json.dump(analysis_dict, analise_file)

        Audit.set_audit(None)
        Audit.set_audit(self._main_path)
        audit = Audit.get_current_audit()

        self.assertEqual(0, len(audit.notificacoes))
        self.assertEqual(1, len(audit.aiim_itens))
        calculated_df = audit.aiim_itens[0].df
        self.assertIsInstance(calculated_df, pd.DataFrame)
        self.assertListEqual(['data', 'total'], calculated_df.keys().tolist())
        self.assertIsInstance(calculated_df['data'][0], datetime.date)
        self.assertListEqual([datetime.datetime(2022, 1, 1), datetime.datetime(2022, 4, 1)],
                             GeneralFunctions.get_dates_from_df(calculated_df))
        self.assertListEqual([120.3, 400.2], calculated_df['total'].values.tolist())

    def test_add_analysis_with_df_with_excedent_columns(self):
        analysis_dict = {
            "verificacao": "teste",
            "funcao": {
                "nome": "verifica_omissao_efds",
                "descricao": "Não usada nesse teste"
            },
            "infracoes": ["Vm-LRAICMS"]
        }
        analysis = Analysis(analysis_dict)
        dados = {
            'empresa': 'bagaca'
        }
        with (self._main_path / 'Dados' / 'dados_auditoria.json').open(mode='w') as outfile:
            json.dump(dados, outfile, sort_keys=True, indent=3)
        Audit.set_audit(self._main_path)
        audit = Audit.get_current_audit()
        df = pd.DataFrame(columns=['Referência', 'Valor'],
                          data=[[datetime.date(2022, 1, 1), 120.3],
                                [datetime.date(2022, 4, 1), 400.2]])
        df = df.astype({'Referência': 'datetime64[ns]', 'Valor': 'Float64'})
        Controller.add_analysis_to_audit(analysis, df=df)
        audit.save()

        Audit.set_audit(None)
        with (self._main_path / 'analise.json').open(mode='w') as analise_file:
            json.dump(analysis_dict, analise_file)
        with self.assertRaises(ValueError) as ctx:
            Audit.set_audit(self._main_path)
        self.assertEqual("Dataframe da função verifica_omissao_efds da verificação teste tem 2 colunas, "
                         "mas a configuração da verificação tem os seguintes cabeçalhos: ['Referência']",
                         str(ctx.exception))

    def test_move_analysis_from_notification_to_infraction_happyday(self):
        analysis_name = Analysis.get_all_analysis(self._main_path)[0].name
        dados = {
            'empresa': 'bagaca',
            'notificacoes': [{'verificacao': analysis_name, 'planilha': 'template'}]
        }
        with (self._main_path / 'Dados' / 'dados_auditoria.json').open(mode='w') as outfile:
            json.dump(dados, outfile, sort_keys=True, indent=3)
        Audit.set_audit(self._main_path)
        audit = Audit.get_current_audit()
        Controller.move_analysis_from_notification_to_aiim(audit.notificacoes[0],
                                                           'IC/N/FIS/456/2021')
        self.assertEqual(1, len(audit.aiim_itens))
        self.assertEqual(0, len(audit.notificacoes))
        item = audit.aiim_itens[0]
        self.assertEqual('template', item.planilha)
        self.assertEqual('IC/N/FIS/000000456/2021', item.notificacao)
        self.assertTrue(item.notification_response_path().is_dir())

    def test_move_analysis_from_notification_to_infraction_no_sheet(self):
        analysis_name = Analysis.get_all_analysis(self._main_path)[0].name
        dados = {
            'empresa': 'bagaca',
            'notificacoes': [{'verificacao': analysis_name, 'planilha': 'planilha123'}]
        }
        with (self._main_path / 'Dados' / 'dados_auditoria.json').open(mode='w') as outfile:
            json.dump(dados, outfile, sort_keys=True, indent=3)
        Audit.set_audit(self._main_path)
        audit = Audit.get_current_audit()
        Controller.move_analysis_from_notification_to_aiim(audit.notificacoes[0],
                                                           'IC/N/FIS/456/2021')
        self.assertEqual(0, len(audit.aiim_itens))
        self.assertEqual(0, len(audit.notificacoes))


class ControllerPopulateDatabase(AuditTestSetup):
    @mock.patch("Controller.SeleniumWebScraper")
    @mock.patch("Controller.SQLWriter")
    @mock.patch("Controller.time")
    @mock.patch("WebScraper.time")
    def test_run_launchpad_report_break_download_periods(self, mock_time1, mock_time2, mock_postgres, mock_ws):
        audit = Audit.get_current_audit()
        self.assertDictEqual({}, audit.reports)
        window = mock.create_autospec(sg.Window)
        event = threading.Event()
        Controller.populate_database(['NFeDest'], window, event)
        self.assertDictEqual({'NFeDest': '1y'}, audit.reports)
        mock_ws.assert_called_once_with(Audit.get_current_audit().reports_path())
        mock_ws_ctx = mock_ws.return_value.__enter__.return_value
        self.assertEqual(5, mock_ws_ctx.get_launchpad_report.call_count)
        self.assertEqual(2, len([c for c in mock_ws_ctx.get_launchpad_report.mock_calls
                                 if len(c.args) and c.args[0] == 'NFe_Destinatario_OSF']))
        calls = [
            call('NFe_Destinatario_OSF', 'NFe_Destinatario_OSF_01012017_31122017.csv', event, window,
                 audit.cnpj_only_digits(), '01/01/2017', '31/12/2017', '0', audit.osf_only_digits(),
                 relatorio_anterior=None),
            call('NFe_Destinatario_OSF', 'NFe_Destinatario_OSF_01012018_31122018.csv', event, window,
                 audit.cnpj_only_digits(), '01/01/2018', '31/12/2018', '0', audit.osf_only_digits(),
                 relatorio_anterior=mock.ANY)
        ]
        mock_ws_ctx.get_launchpad_report.assert_has_calls(calls, any_order=True)

    @mock.patch("Controller.SeleniumWebScraper")
    @mock.patch("Controller.SQLWriter")
    @mock.patch("Controller.time")
    @mock.patch("WebScraper.time")
    def test_run_launchpad_report_dont_break_download_periods_for_aggregated_reports(self, mock_time1, mock_time2,
                                                                                     mock_postgres, mock_ws):
        audit = Audit.get_current_audit()
        self.assertDictEqual({}, audit.reports)
        window = mock.create_autospec(sg.Window)
        event = threading.Event()
        Controller.populate_database(['NFeDest'], window, event)
        self.assertDictEqual({'NFeDest': '1y'}, audit.reports)
        mock_ws_ctx = mock_ws.return_value.__enter__.return_value
        self.assertEqual(1, len([c for c in mock_ws_ctx.get_launchpad_report.mock_calls
                                 if len(c.args) and c.args[0] == 'NFe Docs Referenciados Destinatário']))
        calls = [
            call('NFe Docs Referenciados Destinatário', 'NFe_Docs_Referenciados_Destinatário_01012017_31122018.csv',
                 event, window,
                 audit.cnpj_only_digits(), '201701', '201812')
        ]
        mock_ws_ctx.get_launchpad_report.assert_has_calls(calls)

    @mock.patch("Controller.SeleniumWebScraper")
    @mock.patch("Controller.SQLWriter")
    @mock.patch("Controller.time")
    @mock.patch("WebScraper.time")
    def test_run_launchpad_report_timeout_during_download_decrease_download_period(self, mock_time1, mock_time2,
                                                                                   mock_postgres, mock_ws):
        audit = Audit.get_current_audit()
        self.assertDictEqual({}, audit.reports)
        window = mock.create_autospec(sg.Window)
        event = threading.Event()
        mock_ws_ctx = mock_ws.return_value.__enter__.return_value
        mock_ws_ctx.get_launchpad_report.side_effect = WebScraperTimeoutException('deu ruim')
        Controller.populate_database(['NFeDest'], window, event)
        self.assertDictEqual({'NFeDest': '6m'}, audit.reports)
        self.assertEqual(2, len([c for c in mock_ws_ctx.get_launchpad_report.mock_calls
                                 if len(c.args) and c.args[0] == 'NFe_Destinatario_OSF']))
        calls = [
            call('NFe_Destinatario_OSF', 'NFe_Destinatario_OSF_01012017_31122017.csv', event, window,
                 audit.cnpj_only_digits(), '01/01/2017', '31/12/2017', '0', audit.osf_only_digits(),
                 relatorio_anterior=None),
            call('NFe_Destinatario_OSF', 'NFe_Destinatario_OSF_01012018_31122018.csv', event, window,
                 audit.cnpj_only_digits(), '01/01/2018', '31/12/2018', '0', audit.osf_only_digits(),
                 relatorio_anterior=mock.ANY)
        ]
        mock_ws_ctx.get_launchpad_report.assert_has_calls(calls, any_order=True)

        # da próxima vez, vai rodar em períodos de 6 meses
        mock_ws_ctx.reset_mock()
        Controller.populate_database(['NFeDest'], window, event)
        self.assertDictEqual({'NFeDest': '3m'}, audit.reports)
        self.assertEqual(4, len([c for c in mock_ws_ctx.get_launchpad_report.mock_calls
                                 if len(c.args) and c.args[0] == 'NFe_Destinatario_OSF']))
        calls = [
            call('NFe_Destinatario_OSF', 'NFe_Destinatario_OSF_01012017_30062017.csv', event, window,
                 audit.cnpj_only_digits(), '01/01/2017', '30/06/2017', '0', audit.osf_only_digits(),
                 relatorio_anterior=None),
            call('NFe_Destinatario_OSF', 'NFe_Destinatario_OSF_01072017_31122017.csv', event, window,
                 audit.cnpj_only_digits(), '01/07/2017', '31/12/2017', '0', audit.osf_only_digits(),
                 relatorio_anterior=mock.ANY),
            call('NFe_Destinatario_OSF', 'NFe_Destinatario_OSF_01012018_30062018.csv', event, window,
                 audit.cnpj_only_digits(), '01/01/2018', '30/06/2018', '0', audit.osf_only_digits(),
                 relatorio_anterior=mock.ANY),
            call('NFe_Destinatario_OSF', 'NFe_Destinatario_OSF_01072018_31122018.csv', event, window,
                 audit.cnpj_only_digits(), '01/07/2018', '31/12/2018', '0', audit.osf_only_digits(),
                 relatorio_anterior=mock.ANY)
        ]
        mock_ws_ctx.get_launchpad_report.assert_has_calls(calls, any_order=True)

        # da próxima vez, vai rodar em períodos de 3 meses
        mock_ws_ctx.reset_mock()
        Controller.populate_database(['NFeDest'], window, event)
        self.assertDictEqual({'NFeDest': '1m'}, audit.reports)
        self.assertEqual(8, len([c for c in mock_ws_ctx.get_launchpad_report.mock_calls
                                 if len(c.args) and c.args[0] == 'NFe_Destinatario_OSF']))

        # da próxima vez, vai rodar em períodos de 1 mês
        mock_ws_ctx.reset_mock()
        Controller.populate_database(['NFeDest'], window, event)
        self.assertDictEqual({'NFeDest': '16d'}, audit.reports)
        self.assertEqual(24, len([c for c in mock_ws_ctx.get_launchpad_report.mock_calls
                                 if len(c.args) and c.args[0] == 'NFe_Destinatario_OSF']))

        # da próxima vez, vai rodar em período quinzenal
        mock_ws_ctx.reset_mock()
        Controller.populate_database(['NFeDest'], window, event)
        self.assertDictEqual({'NFeDest': '11d'}, audit.reports)
        self.assertEqual(48, len([c for c in mock_ws_ctx.get_launchpad_report.mock_calls
                                 if len(c.args) and c.args[0] == 'NFe_Destinatario_OSF']))

        # da próxima vez, vai rodar em 3 períodos por mês
        mock_ws_ctx.reset_mock()
        Controller.populate_database(['NFeDest'], window, event)
        self.assertDictEqual({'NFeDest': '11d'}, audit.reports)
        self.assertEqual(72, len([c for c in mock_ws_ctx.get_launchpad_report.mock_calls
                                 if len(c.args) and c.args[0] == 'NFe_Destinatario_OSF']))

        # das próximas vezes, vai continuar tentando em período semanal
        mock_ws_ctx.reset_mock()
        Controller.populate_database(['NFeDest'], window, event)
        self.assertDictEqual({'NFeDest': '11d'}, audit.reports)
        self.assertEqual(72, len([c for c in mock_ws_ctx.get_launchpad_report.mock_calls
                                  if len(c.args) and c.args[0] == 'NFe_Destinatario_OSF']))

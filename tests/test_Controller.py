import datetime
import json
import os
import shutil
from unittest import TestCase

from pathlib import Path

import pandas as pd

import Controller
import Audit
import GeneralFunctions
from ConfigFiles import Analysis


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

import datetime
import json
import unittest
from unittest import mock

import Controller
from Audit import get_current_audit
from ConfigFiles import Analysis
from tests.test_Audit import AuditTestSetup


class AnalysisFunctionsTest(AuditTestSetup):

    def test_infraction_omissao_efds_lrs(self):
        analysis_dic = {
            "verificacao": "Falta de livro",
            "funcao": {
                "nome": "verifica_omissao_efds", "descricao": "Vê se faltam arquivos SPED no diretório"
            },
            "infracoes": ["Vj-LRE"]
        }
        with (get_current_audit().reports_path() / 'verificacao.json').open(mode='w') as arquivo:
            json.dump(analysis_dic, arquivo, sort_keys=True, indent=3)
        Analysis.clear_audit_analysis()
        analysis = Analysis.get_analysis_by_name(get_current_audit().path(), "Falta de livro")
        self.assertListEqual([[datetime.date(2018, 1, 1), datetime.date(2018, 12, 31)]],
                             get_current_audit().get_periodos_da_fiscalizacao(rpa=True))
        tamanho, df = analysis.function()
        self.assertEqual(12, tamanho)
        all_dates = [datetime.date(2018, month, 1) for month in range(1, 13)]
        self.assertListEqual(all_dates, df['Referencia'].tolist())
        Controller.add_analysis_to_audit(analysis, df=df)
        ddf_result = Controller.get_ddf_for_infraction(analysis.infractions[0])
        self.assertEqual('V', ddf_result['inciso'])
        self.assertEqual('j', ddf_result['alinea'])
        self.assertListEqual(['1'], ddf_result['ddf']['Livros'].tolist())
        self.assertListEqual(['12'], ddf_result['ddf']['Meses'].tolist())

    def test_infraction_omissao_efds_lri(self):
        analysis_dic = {
            "verificacao": "Falta de livro",
            "funcao": {
                "nome": "verifica_omissao_efds", "descricao": "Vê se faltam arquivos SPED no diretório"
            },
            "infracoes": ["Vj-LRI"]
        }
        with (get_current_audit().reports_path() / 'verificacao.json').open(mode='w') as arquivo:
            json.dump(analysis_dic, arquivo, sort_keys=True, indent=3)
        Analysis.clear_audit_analysis()
        analysis = Analysis.get_analysis_by_name(get_current_audit().path(), "Falta de livro")
        self.assertListEqual([[datetime.date(2018, 1, 1), datetime.date(2018, 12, 31)]],
                             get_current_audit().get_periodos_da_fiscalizacao(rpa=True))
        tamanho, df = analysis.function()
        self.assertEqual(12, tamanho)
        all_dates = [datetime.date(2018, month, 1) for month in range(1, 13)]
        self.assertListEqual(all_dates, df['Referencia'].tolist())
        Controller.add_analysis_to_audit(analysis, df=df)
        ddf_result = Controller.get_ddf_for_infraction(analysis.infractions[0])
        self.assertEqual('V', ddf_result['inciso'])
        self.assertEqual('j', ddf_result['alinea'])
        self.assertListEqual(['1'], ddf_result['ddf']['Livros'].tolist())
        self.assertListEqual(['1'], ddf_result['ddf']['Meses'].tolist())

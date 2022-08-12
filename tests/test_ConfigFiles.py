import os
import unittest
from pathlib import Path
from unittest import mock

import GeneralFunctions
from ConfigFiles import Analysis


class ConfigFilesTest(unittest.TestCase):

    def test_json_schema_analysis(self):
        directory = str(Path(r'resources/verificacoes').resolve())
        for (path, _, verificacoes) in os.walk(directory):
            for verificacao in verificacoes:
                if verificacao.endswith('.json') and \
                        verificacao not in GeneralFunctions.get_project_special_files():
                    Analysis(Path(path) / verificacao, validate=True)

    def test_default_analysis_have_all_fields(self):
        GeneralFunctions.clean_tmp_folder()
        Analysis.clear_user_analysis()
        with mock.patch('GeneralFunctions.get_user_path', return_value=GeneralFunctions.get_tmp_path()):
            all_analysis = Analysis.get_all_analysis()
        for a in all_analysis:
            for i in a.infractions:
                self.assertIsNotNone(i.report, f'Análise {a}, infração {i}')
                self.assertIsNotNone(i.relatorio_circunstanciado, f'Análise {a}, infração {i}')
                self.assertGreater(len(i.provas), 0, f'Análise {a}, infração {i}')
                self.assertGreater(len(i.ttpa), 0, f'Análise {a}, infração {i}')
                self.assertIsNotNone(i.capitulation, f'Análise {a}, infração {i}')
                if i.capitulation.clear_existing_capitulation:
                    self.assertGreater(len(i.capitulation.articles), 0, f'Análise {a}, infração {i}')

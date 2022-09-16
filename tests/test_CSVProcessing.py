import shutil
import unittest
from pathlib import Path

import CSVProcessing
import WebScraper


class CSVProcessingTest(unittest.TestCase):
    _files_path = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._files_path = Path(__file__).parent.resolve() / 'arquivos_csv'

    def setUp(self) -> None:
        self._files_path.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self._files_path, ignore_errors=True)

    def test_verify_existence_of_all_launchpad_reports_methods(self):
        for report, options in WebScraper.launchpad_report_options.items():
            if options['Tipo'] == 'Dados':
                relatorio_attr = CSVProcessing.to_ascii(report)
                getattr(CSVProcessing, f'__{relatorio_attr}_already_did_import')
                getattr(CSVProcessing, f'__{relatorio_attr}_missing_prerequisite')
                getattr(CSVProcessing, f'__{relatorio_attr}_import_file')
                self.assertTrue((Path('resources') / 'sql' / f'{relatorio_attr}_create.sql').is_file(),
                                f'Não encontrado script SQL {relatorio_attr}_create.sql')
                self.assertTrue((Path('resources') / 'sql' / f'{relatorio_attr}_insert.sql').is_file(),
                                f'Não encontrado script SQL {relatorio_attr}_insert.sql')



import datetime
import re
from pathlib import Path
from unittest import TestCase

from tika import parser

import Audit
from tests.test_Audit import AuditTestSetup


class ExcelDDFsTest(AuditTestSetup):

    def assertEqualsContents(self, aiim_number: str, expected_file: Path, actual_file: Path):
        raw = parser.from_file(str(expected_file.absolute()))
        expected_text = re.sub(r'\d{2}/\d{2}/\d{4}', datetime.date.today().strftime('%d/%m/%Y'), str(raw['content']))
        raw = parser.from_file(str(actual_file.absolute()))
        actual_text = re.sub(r'\d.\d{3}.\d{3}-\d', aiim_number, str(raw['content']))
        self.assertEqual(expected_text, actual_text)

    def _verifica_quadro_3(self, aiim_number: str):
        caminho_q1 = self._main_path / 'template' / f'Quadro1_{aiim_number}.pdf'
        caminho_q3 = self._main_path / 'template' / f'Quadro3_{aiim_number}.pdf'
        aiim_number = f'{aiim_number[0]}.{aiim_number[1:4]}.{aiim_number[4:7]}-{aiim_number[-1]}'
        Audit.get_current_audit().aiim_number = aiim_number
        Audit.get_current_audit().get_sheet().gera_quadro_3(caminho_q1)
        self.assertTrue((self._main_path / 'AIIM' / 'Quadro 3.pdf').is_file())
        self.assertEqualsContents(aiim_number, caminho_q3, self._main_path / 'AIIM' / 'Quadro 3.pdf')

    def test_gera_quadro_3(self):
        self._verifica_quadro_3('41500581')
        self._verifica_quadro_3('41427889')
        self._verifica_quadro_3('41473700')

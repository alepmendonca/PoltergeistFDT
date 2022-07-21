import json
import os
import shutil
from unittest import TestCase

from pathlib import Path

import Controller
import Audit
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
        Controller.set_main_path(self._main_path)

    def tearDown(self) -> None:
        os.remove(os.path.join(self._main_path, 'Dados', 'dados_auditoria.json'))
        os.remove(os.path.join(self._main_path, 'Achados', 'Arrazoado - Teste.xlsm'))

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            shutil.rmtree(cls._main_path / 'Dados')
            shutil.rmtree(cls._main_path / 'Achados')
            shutil.rmtree(cls._main_path / 'Notificações')
        except:
            pass

    def test_move_analysis_from_notification_to_infraction_happyday(self):
        analysis_name = Analysis.get_default_analysis()[0].name
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
        analysis_name = Analysis.get_default_analysis()[0].name
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

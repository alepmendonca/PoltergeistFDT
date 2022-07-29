import datetime
import re
import shutil
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd
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

    @unittest.skip
    def test_gera_quadro_3(self):
        with mock.patch('MDBReader.MDBReader.get_last_ufesp_stored', return_value=31.97):
            self._verifica_quadro_3('41500581')
            self._verifica_quadro_3('41427889')
            self._verifica_quadro_3('41473700')

    def test_get_operations_with_csv_file(self):
        arquivo_csv = Path(self._main_path / 'Dados' / 'valor_operacoes.csv')
        self.assertFalse(arquivo_csv.is_file())
        with arquivo_csv.open(mode='w') as valores:
            valores.write('Periodo,Mes,Ano,Valor Contabil - CFOP\n2022-02-01,2,2022,"317.019.158,71"\n'
                          '2022-01-01,1,2022,"294.531.750,63"\n2021-12-01,12,2021,"303.732.994,99"\n'
                          '2021-11-01,11,2021,"325.268.407,73"\n2021-10-01,10,2021,"285.257.651,94"\n'
                          '2021-09-01,9,2021,"255.123.857,59"\n2021-08-01,8,2021,"285.477.452,18"\n'
                          '2021-07-01,7,2021,"276.445.191,91"\n2021-06-01,6,2021,"313.171.355,82"\n'
                          '2021-05-01,5,2021,"316.672.689,54"\n2021-04-01,4,2021,"303.077.942,56"\n'
                          '2021-03-01,3,2021,"313.859.083,41"\n2021-02-01,2,2021,"296.753.854,64"\n')
        resultado = Audit.get_current_audit().get_sheet().get_operations_for_aiim(
            Path('arquivo_inexistente.xlsx'))
        self.assertIsInstance(resultado, pd.DataFrame)
        self.assertEqual(13, len(resultado))
        self.assertListEqual([2, 1, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2],
                             resultado['Mes'].tolist())
        self.assertListEqual([2022, 2022, 2021, 2021, 2021, 2021, 2021, 2021, 2021, 2021, 2021, 2021, 2021],
                             resultado['Ano'].tolist())
        self.assertListEqual(['317.019.158,71', '294.531.750,63', '303.732.994,99', '325.268.407,73', '285.257.651,94',
                              '255.123.857,59', '285.477.452,18', '276.445.191,91', '313.171.355,82', '316.672.689,54',
                              '303.077.942,56', '313.859.083,41', '296.753.854,64'],
                             resultado['Valor Contabil - CFOP'].tolist())

    def test_get_operations_without_any_files(self):
        arquivo_csv = Path(self._main_path / 'Dados' / 'valor_operacoes.csv')
        self.assertFalse(arquivo_csv.is_file())
        resultado = Audit.get_current_audit().get_sheet().get_operations_for_aiim(
            Path('arquivo_inexistente.xlsx'))
        self.assertIsInstance(resultado, pd.DataFrame)
        self.assertEqual(0, len(resultado))

    def test_get_operations_with_only_xlsx_no_gia(self):
        arquivo_csv = Path(self._main_path / 'Dados' / 'valor_operacoes.csv')
        self.assertFalse(arquivo_csv.is_file())
        arquivo_xls = self._main_path / 'Dados' / 'Valores.xlsx'
        shutil.copyfile(Path('tests') / 'template' / 'Valor_Total_Documentos_Fiscais_x_GIA_so_df.xlsx',
                        arquivo_xls)
        resultado = Audit.get_current_audit().get_sheet().get_operations_for_aiim(arquivo_xls)
        self.assertIsInstance(resultado, pd.DataFrame)
        self.assertFalse(arquivo_xls.is_file())
        self.assertTrue(arquivo_csv.is_file())
        self.assertEqual(13, len(resultado))
        self.assertListEqual([6, 5, 4, 3, 2, 1, 12, 11, 10, 9, 8, 7, 6],
                             resultado['Mes'].tolist())
        self.assertListEqual([2022, 2022, 2022, 2022, 2022, 2022, 2021, 2021, 2021, 2021, 2021, 2021, 2021],
                             resultado['Ano'].tolist())
        self.assertListEqual(['168.524,29', '164.055,94', '179.554,15', '276.304,36', '289.298,44',
                              '293.562,28', '426.965,64', '194.553,62', '128.981,42', '104.222,81',
                              '91.875,42', '206.516,29', '348.674,27'],
                             resultado['Valor Contabil - CFOP'].tolist())
        resultado2 = Audit.get_current_audit().get_sheet().get_operations_for_aiim(arquivo_xls)
        self.assertIsInstance(resultado2, pd.DataFrame)
        self.assertEqual(13, len(resultado2))
        self.assertListEqual([6, 5, 4, 3, 2, 1, 12, 11, 10, 9, 8, 7, 6],
                             resultado2['Mes'].tolist())
        self.assertListEqual([2022, 2022, 2022, 2022, 2022, 2022, 2021, 2021, 2021, 2021, 2021, 2021, 2021],
                             resultado2['Ano'].tolist())
        self.assertListEqual(['168.524,29', '164.055,94', '179.554,15', '276.304,36', '289.298,44',
                              '293.562,28', '426.965,64', '194.553,62', '128.981,42', '104.222,81',
                              '91.875,42', '206.516,29', '348.674,27'],
                             resultado2['Valor Contabil - CFOP'].tolist())

    def test_get_operations_with_only_xlsx_gia_less_than_df(self):
        arquivo_csv = Path(self._main_path / 'Dados' / 'valor_operacoes.csv')
        self.assertFalse(arquivo_csv.is_file())
        arquivo_xls = self._main_path / 'Dados' / 'Valores.xlsx'
        shutil.copyfile(Path('tests') / 'template' / 'Valor_Total_Documentos_Fiscais_x_GIA_gia_menor.xlsx',
                        arquivo_xls)
        resultado = Audit.get_current_audit().get_sheet().get_operations_for_aiim(arquivo_xls)
        self.assertIsInstance(resultado, pd.DataFrame)
        self.assertFalse(arquivo_xls.is_file())
        self.assertTrue(arquivo_csv.is_file())
        self.assertEqual(13, len(resultado))
        self.assertListEqual([6, 5, 4, 3, 2, 1, 12, 11, 10, 9, 8, 7, 6],
                             resultado['Mes'].tolist())
        self.assertListEqual([2022, 2022, 2022, 2022, 2022, 2022, 2021, 2021, 2021, 2021, 2021, 2021, 2021],
                             resultado['Ano'].tolist())
        self.assertListEqual(['168.524,29', '164.055,94', '179.554,15', '276.304,36', '289.298,44',
                              '293.562,28', '426.965,64', '194.553,62', '128.981,42', '104.222,81',
                              '91.875,42', '206.516,29', '348.674,27'],
                             resultado['Valor Contabil - CFOP'].tolist())

    def test_get_operations_with_only_xlsx_gia_more_than_df(self):
        arquivo_csv = Path(self._main_path / 'Dados' / 'valor_operacoes.csv')
        self.assertFalse(arquivo_csv.is_file())
        arquivo_xls = self._main_path / 'Dados' / 'Valores.xlsx'
        shutil.copyfile(Path('tests') / 'template' / 'Valor_Total_Documentos_Fiscais_x_GIA_gia_maior.xlsx',
                        arquivo_xls)
        resultado = Audit.get_current_audit().get_sheet().get_operations_for_aiim(arquivo_xls)
        self.assertIsInstance(resultado, pd.DataFrame)
        self.assertFalse(arquivo_xls.is_file())
        self.assertTrue(arquivo_csv.is_file())
        self.assertEqual(13, len(resultado))
        self.assertListEqual([6, 5, 4, 3, 2, 1, 12, 11, 10, 9, 8, 7, 6],
                             resultado['Mes'].tolist())
        self.assertListEqual([2022, 2022, 2022, 2022, 2022, 2022, 2021, 2021, 2021, 2021, 2021, 2021, 2021],
                             resultado['Ano'].tolist())
        self.assertListEqual(['300.000,00' for i in range(0, 13)],
                             resultado['Valor Contabil - CFOP'].tolist())

    def test_get_operations_with_csv_and_xlsx_update_existing_values(self):
        arquivo_csv = Path(self._main_path / 'Dados' / 'valor_operacoes.csv')
        self.assertFalse(arquivo_csv.is_file())
        with arquivo_csv.open(mode='w') as valores:
            valores.write('Periodo,Mes,Ano,Valor Contabil - CFOP\n2022-02-01,2,2022,"317.019.158,71"\n'
                          '2022-01-01,1,2022,"294.531.750,63"\n2021-12-01,12,2021,"303.732.994,99"\n'
                          '2021-11-01,11,2021,"325.268.407,73"\n2021-10-01,10,2021,"285.257.651,94"\n'
                          '2021-09-01,9,2021,"255.123.857,59"\n2021-08-01,8,2021,"285.477.452,18"\n'
                          '2021-07-01,7,2021,"276.445.191,91"\n2021-06-01,6,2021,"313.171.355,82"\n'
                          '2021-05-01,5,2021,"316.672.689,54"\n2021-04-01,4,2021,"303.077.942,56"\n'
                          '2021-03-01,3,2021,"313.859.083,41"\n2021-02-01,2,2021,"296.753.854,64"\n')
        arquivo_xls = self._main_path / 'Dados' / 'Valores.xlsx'
        shutil.copyfile(Path('tests') / 'template' / 'Valor_Total_Documentos_Fiscais_x_GIA_gia_maior.xlsx',
                        arquivo_xls)
        resultado = Audit.get_current_audit().get_sheet().get_operations_for_aiim(arquivo_xls)
        self.assertIsInstance(resultado, pd.DataFrame)
        self.assertFalse(arquivo_xls.is_file())
        self.assertTrue(arquivo_csv.is_file())
        self.assertIsInstance(resultado, pd.DataFrame)
        self.assertEqual(17, len(resultado))
        self.assertListEqual([6, 5, 4, 3, 2, 1, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2],
                             resultado['Mes'].tolist())
        self.assertListEqual([2022, 2022, 2022, 2022, 2022, 2022, 2021, 2021, 2021, 2021, 2021, 2021, 2021,
                              2021, 2021, 2021, 2021],
                             resultado['Ano'].tolist())
        valores = ['300.000,00' for i in range(0, 13)]
        valores.extend(['316.672.689,54', '303.077.942,56', '313.859.083,41', '296.753.854,64'])
        self.assertListEqual(valores, resultado['Valor Contabil - CFOP'].tolist())

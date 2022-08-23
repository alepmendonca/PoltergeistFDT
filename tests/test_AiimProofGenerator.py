import datetime
from unittest import mock
from unittest.mock import Mock

import pandas as pd
import Audit
import EFDPVAReversed
import GeneralFunctions
from ConfigFiles import AiimProof
from WebScraper import SeleniumWebScraper
from tests.test_Audit import AuditTestSetup
from AiimProofGenerator import AiimProofException


class AiimProofGeneratorTestCase(AuditTestSetup):
    @staticmethod
    def _planilha_com_agrupamento():
        return pd.DataFrame(columns=['Chave', 'Emissão', 'Entrada', 'Valor', 'mês'],
                            data=[['3517221155565466541255000000000001', datetime.date(2022, 1, 5),
                                   datetime.date(2022, 2, 3), 100.5, datetime.date(2022, 2, 28)],
                                  ['Total Subitem 1.1', None, None, 100.5, datetime.date(2022, 2, 28)],
                                  ['3718546546566665561255000000000002', datetime.date(2022, 4, 2),
                                   datetime.date(2022, 4, 3), 300.2, datetime.date(2022, 4, 30)],
                                  ['Total Subitem 1.2', None, None, 300.2, datetime.date(2022, 4, 30)],
                                  ['TOTAL ITEM 1', None, None, 400.7, 'Total Geral']])

    def test_generate_lre_fail_missing_column_entrada(self):
        mock_pva = mock.create_autospec(EFDPVAReversed.EFDPVAReversed)
        proof_type = AiimProof({'tipo': 'LRE', 'descricao': ''})
        df_capenga = self._planilha_com_agrupamento()[['Chave', 'Emissão', 'Valor', 'mês']]
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=df_capenga):
            with self.assertRaises(AiimProofException) as ctx:
                proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], None, mock_pva)
            self.assertEqual('Não existe na planilha uma coluna de data contendo no título "Entrada". '
                             'Não é possível localizar as provas no Livro Registro de Entradas sem a data de entrada. '
                             'Altere o título da coluna certa para gerar as provas do LRE.', str(ctx.exception))
        mock_pva.print_LRE.assert_not_called()

    def test_generate_lre_fail_missing_column_emissao(self):
        mock_pva = mock.create_autospec(EFDPVAReversed.EFDPVAReversed)
        proof_type = AiimProof({'tipo': 'LRE', 'descricao': ''})
        df_capenga = self._planilha_com_agrupamento()[['Chave', 'Entrada', 'Valor', 'mês']]
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=df_capenga):
            with self.assertRaises(AiimProofException) as ctx:
                proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], None, mock_pva)
            self.assertEqual('Não existe na planilha uma coluna de data contendo no título "Emiss". '
                             'Não é possível localizar as provas no Livro Registro de Entradas sem a data de emissão. '
                             'Altere o título da coluna certa para gerar as provas do LRE.', str(ctx.exception))
        mock_pva.print_LRE.assert_not_called()

    def test_generate_lre_fail_missing_column_chave(self):
        mock_pva = mock.create_autospec(EFDPVAReversed.EFDPVAReversed)
        proof_type = AiimProof({'tipo': 'LRE', 'descricao': ''})
        df_capenga = self._planilha_com_agrupamento()[['Emissão', 'Entrada', 'Valor', 'mês']].dropna()
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=df_capenga):
            with self.assertRaises(AiimProofException) as ctx:
                proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], None, mock_pva)
            self.assertEqual('Não existe na planilha uma coluna contendo no título "Chave". '
                             'Não é possível localizar as provas no Livro Registro de Entradas sem a chave do '
                             'documento. '
                             'Altere o título da coluna certa para gerar as provas do LRE.', str(ctx.exception))
        mock_pva.print_LRE.assert_not_called()

    @mock.patch('AiimProofGenerator.PdfWriter')
    @mock.patch('AiimProofGenerator.PdfReader')
    def test_generate_lre_multiple_months(self, mock_reader, mock_writer):
        mock_pva = mock.create_autospec(EFDPVAReversed.EFDPVAReversed)
        mock_page1 = Mock(**{'extract_text.return_value': '03/02/2022 05/01/2022 1 55 100 reais\n'
                                                          '04/02/2022 06/01/2022 346 55 200 reais'})
        mock_page2 = Mock(**{'extract_text.return_value': '03/04/2022 02/04/2022 2 55 500 reais'})
        type(mock_reader).pages = mock.PropertyMock(side_effect=[[mock_page1], [mock_page2]])
        proof_type = AiimProof({'tipo': 'LRE', 'descricao': ''})
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=self._planilha_com_agrupamento()):
            with mock.patch('AiimProofGenerator.PdfReader', return_value=mock_reader):
                with mock.patch('AiimProofGenerator.PdfWriter', return_value=mock_writer):
                    retorno = proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], None, mock_pva)
        calls = [mock.call(datetime.date(2022, 2, 28), GeneralFunctions.get_tmp_path() / 'lre202202.pdf'),
                 mock.call(datetime.date(2022, 4, 30), GeneralFunctions.get_tmp_path() / 'lre202204.pdf')]
        mock_pva.print_LRE.assert_has_calls(calls)
        mock_writer.add_page.assert_has_calls([mock.call(mock_page1), mock.call(mock_page2)])
        self.assertEqual(2, mock_writer.write.call_count)
        self.assertEqual(retorno, [GeneralFunctions.get_tmp_path() / 'lre202202-selection.pdf',
                                   GeneralFunctions.get_tmp_path() / 'lre202204-selection.pdf'])

    @mock.patch('AiimProofGenerator.PdfWriter')
    @mock.patch('AiimProofGenerator.PdfReader')
    def test_generate_one_lre_multiple_lines(self, mock_reader, mock_writer):
        df = pd.DataFrame(columns=['Chave', 'Emissão', 'Entrada', 'Valor', 'mês'],
                          data=[['3517221155565466541255000000000001', datetime.date(2022, 1, 5),
                                 datetime.date(2022, 4, 3), 100.5, datetime.date(2022, 4, 30)],
                                ['3718546546566665561255000000000002', datetime.date(2022, 1, 20),
                                 datetime.date(2022, 4, 8), 300.2, datetime.date(2022, 4, 30)],
                                ['Total Subitem 1.1', None, None, 400.7, datetime.date(2022, 4, 30)],
                                ['TOTAL ITEM 1', None, None, 400.7, 'Total Geral']])
        mock_pva = mock.create_autospec(EFDPVAReversed.EFDPVAReversed)
        mock_page1 = Mock(**{'extract_text.return_value': '03/04/2022 05/01/2022 1 55 100 reais\n'
                                                          '08/04/2022 20/01/2022 2 55 300 reais'})
        type(mock_reader).pages = mock.PropertyMock(return_value=[mock_page1])
        proof_type = AiimProof({'tipo': 'LRE', 'descricao': ''})
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=df):
            with mock.patch('AiimProofGenerator.PdfReader', return_value=mock_reader):
                with mock.patch('AiimProofGenerator.PdfWriter', return_value=mock_writer):
                    retorno = proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], None, mock_pva)
        mock_pva.print_LRE.assert_called_once_with(datetime.date(2022, 4, 30),
                                                   GeneralFunctions.get_tmp_path() / 'lre202204.pdf')
        mock_writer.add_page.assert_has_calls([mock.call(mock_page1)])
        self.assertEqual(1, mock_writer.write.call_count)
        self.assertEqual(retorno, [GeneralFunctions.get_tmp_path() / 'lre202204-selection.pdf'])

    def test_generate_lrs_fail_missing_column_emissao(self):
        mock_pva = mock.create_autospec(EFDPVAReversed.EFDPVAReversed)
        proof_type = AiimProof({'tipo': 'LRS', 'descricao': ''})
        df_capenga = self._planilha_com_agrupamento()[['Chave', 'Entrada', 'Valor', 'mês']]
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=df_capenga):
            with self.assertRaises(AiimProofException) as ctx:
                proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], None, mock_pva)
            self.assertEqual('Não existe na planilha uma coluna de data contendo no título "Emiss". '
                             'Não é possível localizar as provas no Livro Registro de Saídas sem a data de emissão. '
                             'Altere o título da coluna certa para gerar as provas do LRS.', str(ctx.exception))
        mock_pva.print_LRS.assert_not_called()

    def test_generate_lrs_fail_missing_column_chave(self):
        mock_pva = mock.create_autospec(EFDPVAReversed.EFDPVAReversed)
        proof_type = AiimProof({'tipo': 'LRS', 'descricao': ''})
        df_capenga = self._planilha_com_agrupamento()[['Emissão', 'Entrada', 'Valor', 'mês']].dropna()
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=df_capenga):
            with self.assertRaises(AiimProofException) as ctx:
                proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], None, mock_pva)
            self.assertEqual('Não existe na planilha uma coluna contendo no título "Chave". '
                             'Não é possível localizar as provas no Livro Registro de Saídas sem a chave do '
                             'documento. '
                             'Altere o título da coluna certa para gerar as provas do LRS.', str(ctx.exception))
        mock_pva.print_LRS.assert_not_called()

    @mock.patch('AiimProofGenerator.PdfWriter')
    @mock.patch('AiimProofGenerator.PdfReader')
    def test_generate_lrs_multiple_months(self, mock_reader, mock_writer):
        mock_pva = mock.create_autospec(EFDPVAReversed.EFDPVAReversed)
        mock_page1 = Mock(**{'extract_text.return_value': '05/01/2022 1 55 100 reais\n'
                                                          '06/01/2022 346 55 200 reais'})
        mock_page2 = Mock(**{'extract_text.return_value': '02/04/2022 2 55 500 reais'})
        type(mock_reader).pages = mock.PropertyMock(side_effect=[[mock_page1], [mock_page2]])
        proof_type = AiimProof({'tipo': 'LRS', 'descricao': ''})
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=self._planilha_com_agrupamento()):
            with mock.patch('AiimProofGenerator.PdfReader', return_value=mock_reader):
                with mock.patch('AiimProofGenerator.PdfWriter', return_value=mock_writer):
                    retorno = proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], None, mock_pva)
        calls = [mock.call(datetime.date(2022, 1, 31), GeneralFunctions.get_tmp_path() / 'lrs202201.pdf'),
                 mock.call(datetime.date(2022, 4, 30), GeneralFunctions.get_tmp_path() / 'lrs202204.pdf')]
        mock_pva.print_LRS.assert_has_calls(calls)
        mock_writer.add_page.assert_has_calls([mock.call(mock_page1), mock.call(mock_page2)])
        self.assertEqual(2, mock_writer.write.call_count)
        self.assertEqual(retorno, [GeneralFunctions.get_tmp_path() / 'lrs202201-selection.pdf',
                                   GeneralFunctions.get_tmp_path() / 'lrs202204-selection.pdf'])

    @mock.patch('AiimProofGenerator.PdfWriter')
    @mock.patch('AiimProofGenerator.PdfReader')
    def test_generate_one_lrs_multiple_lines(self, mock_reader, mock_writer):
        df = pd.DataFrame(columns=['Chave', 'Emissão', 'Entrada', 'Valor', 'mês'],
                          data=[['3517221155565466541255000000000001', datetime.date(2022, 4, 5),
                                 datetime.date(2022, 4, 6), 100.5, datetime.date(2022, 4, 30)],
                                ['3718546546566665561255000000000002', datetime.date(2022, 4, 20),
                                 datetime.date(2022, 4, 22), 300.2, datetime.date(2022, 4, 30)],
                                ['Total Subitem 1.1', None, None, 400.7, datetime.date(2022, 4, 30)],
                                ['TOTAL ITEM 1', None, None, 400.7, 'Total Geral']])
        mock_pva = mock.create_autospec(EFDPVAReversed.EFDPVAReversed)
        mock_page1 = Mock(**{'extract_text.return_value': '05/04/2022 1 55 100 reais\n'
                                                          '20/04/2022 2 55 300 reais'})
        type(mock_reader).pages = mock.PropertyMock(return_value=[mock_page1])
        proof_type = AiimProof({'tipo': 'LRS', 'descricao': ''})
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=df):
            with mock.patch('AiimProofGenerator.PdfReader', return_value=mock_reader):
                with mock.patch('AiimProofGenerator.PdfWriter', return_value=mock_writer):
                    retorno = proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], None, mock_pva)
        mock_pva.print_LRS.assert_called_once_with(datetime.date(2022, 4, 30),
                                                   GeneralFunctions.get_tmp_path() / 'lrs202204.pdf')
        mock_writer.add_page.assert_has_calls([mock.call(mock_page1)])
        self.assertEqual(1, mock_writer.write.call_count)
        self.assertEqual(retorno, [GeneralFunctions.get_tmp_path() / 'lrs202204-selection.pdf'])

    def test_generate_gia_outros_creditos(self):
        proof_type = AiimProof({'tipo': 'GIA-OutrosCreditos', 'descricao': ''})
        mock_ws = mock.create_autospec(SeleniumWebScraper)
        mock_ws.print_gia_outros_creditos.return_value = ['teste.pdf']
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=self._planilha_com_agrupamento()):
            retorno = proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], mock_ws, None)
        mock_ws.print_gia_outros_creditos.assert_called_once_with('012.345.678.910',
                                                                  [datetime.date(2022, 2, 28),
                                                                   datetime.date(2022, 4, 30)])
        self.assertEqual(retorno, ['teste.pdf'])

    def test_generate_gia_outros_creditos_same_reference(self):
        proof_type = AiimProof({'tipo': 'GIA-OutrosCreditos', 'descricao': ''})
        mock_ws = mock.create_autospec(SeleniumWebScraper)
        mock_ws.print_gia_outros_creditos.return_value = ['teste.pdf']
        df = pd.DataFrame(columns=['Chave', 'Emissão', 'Entrada', 'Valor', 'mês'],
                          data=[['3517221155565466541255000000000001', datetime.date(2022, 4, 5),
                                 datetime.date(2022, 4, 6), 100.5, datetime.date(2022, 4, 30)],
                                ['3718546546566665561255000000000002', datetime.date(2022, 4, 20),
                                 datetime.date(2022, 4, 22), 300.2, datetime.date(2022, 4, 30)],
                                ['Total Subitem 1.1', None, None, 400.7, datetime.date(2022, 4, 30)],
                                ['TOTAL ITEM 1', None, None, 400.7, 'Total Geral']])
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=df):
            retorno = proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], mock_ws, None)
        mock_ws.print_gia_outros_creditos.assert_called_once_with('012.345.678.910',
                                                                  [datetime.date(2022, 4, 30)])
        self.assertEqual(retorno, ['teste.pdf'])

    def test_generate_gia_outros_debitos(self):
        proof_type = AiimProof({'tipo': 'GIA-OutrosDebitos', 'descricao': ''})
        mock_ws = mock.create_autospec(SeleniumWebScraper)
        mock_ws.print_gia_outros_debitos.return_value = ['teste.pdf']
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=self._planilha_com_agrupamento()):
            retorno = proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], mock_ws, None)
        mock_ws.print_gia_outros_debitos.assert_called_once_with('012.345.678.910',
                                                                  [datetime.date(2022, 2, 28),
                                                                   datetime.date(2022, 4, 30)])
        self.assertEqual(retorno, ['teste.pdf'])

    def test_generate_gia_outros_debitos_same_reference(self):
        proof_type = AiimProof({'tipo': 'GIA-OutrosDebitos', 'descricao': ''})
        mock_ws = mock.create_autospec(SeleniumWebScraper)
        mock_ws.print_gia_outros_debitos.return_value = ['teste.pdf']
        df = pd.DataFrame(columns=['Chave', 'Emissão', 'Entrada', 'Valor', 'mês'],
                          data=[['3517221155565466541255000000000001', datetime.date(2022, 4, 5),
                                 datetime.date(2022, 4, 6), 100.5, datetime.date(2022, 4, 30)],
                                ['3718546546566665561255000000000002', datetime.date(2022, 4, 20),
                                 datetime.date(2022, 4, 22), 300.2, datetime.date(2022, 4, 30)],
                                ['Total Subitem 1.1', None, None, 400.7, datetime.date(2022, 4, 30)],
                                ['TOTAL ITEM 1', None, None, 400.7, 'Total Geral']])
        with mock.patch('ExcelDDFs.ExcelDDFs.planilha', return_value=df):
            retorno = proof_type.generate_proof(Audit.get_current_audit().aiim_itens[0], mock_ws, None)
        mock_ws.print_gia_outros_debitos.assert_called_once_with('012.345.678.910',
                                                                  [datetime.date(2022, 4, 30)])
        self.assertEqual(retorno, ['teste.pdf'])

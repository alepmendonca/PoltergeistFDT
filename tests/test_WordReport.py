from pathlib import Path
from unittest import mock

import win32com
import win32com.client

import Audit
import GeneralConfiguration
import PDFExtractor
from Audit import get_current_audit
import WordReport
from tests.test_Audit import AuditTestSetup


class WordReportTest(AuditTestSetup):

    @staticmethod
    def __refresh_word(caminho: Path):
        was_open = False
        try:
            word = win32com.client.GetActiveObject("Word.Application")
        except:
            word = win32com.client.Dispatch("Word.Application")
            was_open = True

        try:
            worddoc = word.Documents.Open(str(caminho.absolute()))
            worddoc.Save()
            worddoc.Close()
        finally:
            if word and was_open:
                try:
                    word.Quit()
                except:
                    pass

    def test_create_report_from_template(self):
        GeneralConfiguration.get().drt_sigla = 'DRT-07'
        GeneralConfiguration.get().equipe_fiscal = 57
        GeneralConfiguration.get().nome = 'FISCAL TESTE'
        GeneralConfiguration.get().funcional = '25.456-8'
        report = get_current_audit().get_report()
        self.assertEqual(get_current_audit().path() / 'AIIM' / 'Relatório Circunstanciado.docx', report.report_path)
        self.assertTrue(report.report_path.is_file())
        self.assertMultiLineEqual(report.report.sections[0].header.tables[0].rows[0].cells[0].text,
                                  "SECRETARIA DA FAZENDA E PLANEJAMENTO\n"
                                  "SUBSECRETARIA DA RECEITA ESTADUAL\n"
                                  "DELEGACIA REGIONAL TRIBUTÁRIA DE BAURU - DRT-7\n"
                                  "NÚCLEO DE FISCALIZAÇÃO 5 - EQUIPE 57")
        titulos = report.titulos_inseridos()
        self.assertListEqual([WordReport.WordReport.titulos[t] for t in titulos.keys()],
                             ['DA CONCLUSÃO DO TRABALHO FISCAL'])
        self.assertListEqual(list(report.anexos_inseridos().keys()), [WordReport.WordReport.PROVAS_GERAIS_BULLET])
        paragrafos_finais = [p.text.strip() for p in
                             report.report.paragraphs[report.anexos_inseridos()[
                                                          WordReport.WordReport.PROVAS_GERAIS_BULLET] + 2:]]
        self.assertEqual('Por agir em desacordo com a Legislação Tributária, foi lavrado o '
                         'AIIM nº 1.111.111-2, nos termos da Lei 6.374/89. Foram juntadas ao presente AIIM '
                         'as provas citadas necessárias para comprovar as infrações praticadas.',
                         paragrafos_finais[0])
        self.assertEqual(f'DRT-7/NF-5/Equipe 57, em', paragrafos_finais[2][:paragrafos_finais[2].index(',') + 4])
        self.assertEqual('FISCAL TESTE', paragrafos_finais[4])
        self.assertEqual('AUDITOR FISCAL DA RECEITA ESTADUAL', paragrafos_finais[5])
        self.assertEqual('IF: 25.456-8', paragrafos_finais[6])

    def test_notificacao(self):
        GeneralConfiguration.get().drt_sigla = 'DRT-07'
        GeneralConfiguration.get().equipe_fiscal = 57
        GeneralConfiguration.get().nome = 'FISCAL TESTE'
        GeneralConfiguration.get().funcional = '25.456-8'
        pdf_notificacao = Audit.get_current_audit().path() / 'notificacao.pdf'
        with mock.patch('WordReport.AIIM2003MDBReader.get_afr_drt_address_and_phone',
                        return_value=('RUA DA DELEGACIA, 123 - CIDADE QUALQUER/SP - CEP 123-000', '(11) 234-1231')):
            try:
                WordReport.cria_notificacao_modelo_4('12.234.456/0001-99', '123.456.789.000', 'EMPRESA FISCALIZADA LTDA',
                                                     'RUA DA EMPRESA, 454 - CENTRO - CIDADE/SP - CEP 11.123-000',
                                                     'No âmbito da OSF 122.456, fica o contribuinte notificado.\n'
                                                     'PRAZO PARA ATENDIMENTO: 10 (dez) dias.\n'
                                                     'BASE LEGAL: Art. 494 do RICMS', '02/2022',
                                                     pdf_notificacao)
                linhas = PDFExtractor.parse_pdf(pdf_notificacao)
            finally:
                pdf_notificacao.unlink(missing_ok=True)
        self.assertEqual('NOTIFICAÇÃO 02/2022', linhas[4].strip())
        self.assertEqual('DRT-7', linhas[11].strip())
        self.assertEqual('NF-5', linhas[12].strip())
        self.assertEqual('EQUIPE 57', linhas[13].strip())
        self.assertEqual('RUA DA DELEGACIA, 123 - CIDADE QUALQUER/SP - CEP 123-000', linhas[16].strip())
        self.assertEqual('(11) 234-1231', linhas[17].strip())
        self.assertEqual('EMPRESA FISCALIZADA LTDA', linhas[22].strip())
        self.assertEqual('RUA DA EMPRESA, 454 - CENTRO - CIDADE/SP - CEP 11.123-000', linhas[23].strip())
        self.assertEqual('123.456.789.000', linhas[24].strip())
        self.assertEqual('12.234.456/0001-99', linhas[26].strip())
        corpo = ''.join(linhas[linhas.index('CUMPRIR AS OBRIGAÇÕES ABAIXO ESPECIFICADAS. ')+1:
                               linhas.index('FORMALIZAÇÃO ')]).strip()
        self.assertEqual('No âmbito da OSF 122.456, fica o contribuinte notificado. PRAZO PARA ATENDIMENTO: '
                         '10 (dez) dias. BASE LEGAL: Art. 494 do RICMS', corpo)
        self.assertEqual('DRT-7-NF-5-EQ-57, ______/______/_______',
                         linhas[linhas.index('EMBARAÇO À AÇÃO FISCALIZADORA IMPLICARÃO SANÇÕES LEGAIS. ')+2].strip())
        idx = linhas.index('RECEBI A 2ª VIA ÀS       :       HS DO DIA      /      /      . ')
        self.assertEqual('FISCAL TESTE', linhas[idx+2].strip())
        self.assertEqual('AFRE - IF 25.456-8', linhas[idx+3].strip())

    def test_insert_titles(self):
        word = get_current_audit().get_report()
        word.insere_item(1, 1, 'aconteceu o seguinte', False)
        titulos = word.titulos_inseridos()
        self.assertListEqual([WordReport.WordReport.titulos[t] for t in titulos.keys()],
                             ["DAS IRREGULARIDADES NO PAGAMENTO DO IMPOSTO", 'DA CONCLUSÃO DO TRABALHO FISCAL'])
        texto_do_titulo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[word.titulos_inseridos()[1] + 1:word.titulos_inseridos()[
                 WordReport.WordReport.PROVAS]]])
        self.assertMultiLineEqual(texto_do_titulo, 'No item 1, aconteceu o seguinte\n')

    def test_insert_multiple_itens_at_same_title(self):
        word = get_current_audit().get_report()
        word.insere_item(1, 1, 'aconteceu o seguinte', False)
        word.insere_item(2, 1, 'depois rolou outra parada', False)
        titulos = word.titulos_inseridos()
        self.assertListEqual([WordReport.WordReport.titulos[t] for t in titulos.keys()],
                             ["DAS IRREGULARIDADES NO PAGAMENTO DO IMPOSTO", 'DA CONCLUSÃO DO TRABALHO FISCAL'])
        texto_do_titulo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[word.titulos_inseridos()[1] + 1:word.titulos_inseridos()[
                 WordReport.WordReport.PROVAS]]])
        self.assertMultiLineEqual(texto_do_titulo,
                                  'No item 1, aconteceu o seguinte\nNo item 2, depois rolou outra parada\n\n')

    def test_insert_new_title_before_existing(self):
        word = get_current_audit().get_report()
        word.insere_item(3, 2, 'o contribuinte fez caquinha', False)
        word.insere_item(2, 1, 'rolou muita treta', False)
        titulos = word.titulos_inseridos()
        self.assertListEqual([WordReport.WordReport.titulos[t] for t in titulos.keys()],
                             ["DAS IRREGULARIDADES NO PAGAMENTO DO IMPOSTO",
                              "DAS IRREGULARIDADES NO CRÉDITO DO IMPOSTO",
                              'DA CONCLUSÃO DO TRABALHO FISCAL'])
        texto_do_titulo_1 = '\n'.join(
            [p.text for p in
             word.report.paragraphs[word.titulos_inseridos()[1] + 1:word.titulos_inseridos()[2]]])
        self.assertMultiLineEqual(texto_do_titulo_1, 'No item 2, rolou muita treta\n')
        texto_do_titulo_2 = '\n'.join(
            [p.text for p in
             word.report.paragraphs[word.titulos_inseridos()[2] + 1:word.titulos_inseridos()[
                 WordReport.WordReport.PROVAS]]])
        self.assertMultiLineEqual(texto_do_titulo_2, 'No item 3, o contribuinte fez caquinha\n')

    def test_insert_title_with_proof_reference(self):
        word = get_current_audit().get_report()
        word.insere_item(4, 5, 'o contribuinte fez caquinha', True)
        titulos = word.titulos_inseridos()
        self.assertListEqual([WordReport.WordReport.titulos[t] for t in titulos.keys()],
                             ["DAS IRREGULARIDADES NOS LIVROS FISCAIS", 'DA CONCLUSÃO DO TRABALHO FISCAL'])
        texto_do_titulo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[word.titulos_inseridos()[5] + 1:word.titulos_inseridos()[
                 WordReport.WordReport.PROVAS]]])
        self.assertMultiLineEqual(texto_do_titulo,
                                  'No item 4, o contribuinte fez caquinha\n'
                                  'Os demonstrativos que comprovam especificamente a infringência '
                                  'deste item do auto de infração encontram-se no Anexo do Item 4.\n')

    def test_remove_item_with_multiple_titles(self):
        word = get_current_audit().get_report()
        word.insere_item(1, 1, 'aconteceu o seguinte', False)
        word.insere_item(2, 1, 'depois rolou outra parada', False)
        word.remove_item(1)
        titulos = word.titulos_inseridos()
        self.assertListEqual([WordReport.WordReport.titulos[t] for t in titulos.keys()],
                             ["DAS IRREGULARIDADES NO PAGAMENTO DO IMPOSTO", 'DA CONCLUSÃO DO TRABALHO FISCAL'])
        texto_do_titulo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[word.titulos_inseridos()[1] + 1:word.titulos_inseridos()[
                 WordReport.WordReport.PROVAS]]])
        self.assertMultiLineEqual(texto_do_titulo,
                                  'No item 2, depois rolou outra parada\n\n')

    def test_remove_only_item_at_title(self):
        word = get_current_audit().get_report()
        word.insere_item(1, 1, 'aconteceu o seguinte', False)
        word.remove_item(1)
        titulos = word.titulos_inseridos()
        self.assertListEqual([WordReport.WordReport.titulos[t] for t in titulos.keys()],
                             ['DA CONCLUSÃO DO TRABALHO FISCAL'])

    def test_insert_proof(self):
        word = get_current_audit().get_report()
        word.insere_anexo(1, ['listagem', 'prova fatal'])
        titulos = word.titulos_inseridos()
        self.assertListEqual([WordReport.WordReport.titulos[t] for t in titulos.keys()],
                             ['DA CONCLUSÃO DO TRABALHO FISCAL'])
        self.assertListEqual(list(word.anexos_inseridos().keys()), [1, WordReport.WordReport.PROVAS_GERAIS_BULLET])
        texto_do_anexo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[word.anexos_inseridos()[1]:
                                    word.anexos_inseridos()[WordReport.WordReport.PROVAS_GERAIS_BULLET]]])
        self.assertMultiLineEqual(texto_do_anexo,
                                  'Anexo do Item 1, contendo:\nlistagem;\nprova fatal.')

    def test_insert_proofs_unsorted(self):
        word = get_current_audit().get_report()
        word.insere_anexo(3, ['eita'])
        word.insere_anexo(2, ['listagem', 'prova fatal'])
        word.insere_anexo(4, ['opa', 'rapaz'])
        self.assertListEqual(list(word.anexos_inseridos().keys()),
                             [2, 3, 4, WordReport.WordReport.PROVAS_GERAIS_BULLET])
        texto_do_anexo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[word.anexos_inseridos()[2]:
                                    word.anexos_inseridos()[WordReport.WordReport.PROVAS_GERAIS_BULLET]]])
        self.assertMultiLineEqual(texto_do_anexo,
                                  'Anexo do Item 2, contendo:\nlistagem;\nprova fatal.\n'
                                  'Anexo do Item 3, contendo:\neita.\n'
                                  'Anexo do Item 4, contendo:\nopa;\nrapaz.')

    def test_remove_proof(self):
        word = get_current_audit().get_report()
        word.insere_anexo(3, ['eita'])
        word.insere_anexo(2, ['listagem', 'prova fatal'])
        word.remove_anexo(3)
        self.assertListEqual(list(word.anexos_inseridos().keys()), [2, WordReport.WordReport.PROVAS_GERAIS_BULLET])
        texto_do_anexo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[word.anexos_inseridos()[2]:
                                    word.anexos_inseridos()[WordReport.WordReport.PROVAS_GERAIS_BULLET]]])
        self.assertMultiLineEqual(texto_do_anexo,
                                  'Anexo do Item 2, contendo:\nlistagem;\nprova fatal.')
        word.remove_anexo(2)
        self.assertListEqual(list(word.anexos_inseridos().keys()), [WordReport.WordReport.PROVAS_GERAIS_BULLET])

    def test_update_general_proofs(self):
        word = get_current_audit().get_report()
        word.atualiza_provas_gerais(['prova 1', 'prova melhor ainda', 'prova 3'])
        self.assertListEqual(list(word.anexos_inseridos().keys()), [WordReport.WordReport.PROVAS_GERAIS_BULLET])
        texto_do_anexo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[word.anexos_inseridos()[WordReport.WordReport.PROVAS_GERAIS_BULLET]:
                                    word.anexos_inseridos()[WordReport.WordReport.PROVAS_GERAIS_BULLET] + 5]])
        self.assertMultiLineEqual(texto_do_anexo,
                                  'Provas Gerais, contendo:\nprova 1;\nprova melhor ainda;\nprova 3.\n')

    def test_remove_inexistent_item(self):
        word = get_current_audit().get_report()
        word.insere_item(3, 1, 'aconteceu o seguinte', False)
        word.remove_item(2)
        titulos = word.titulos_inseridos()
        self.assertListEqual([WordReport.WordReport.titulos[t] for t in titulos.keys()],
                             ["DAS IRREGULARIDADES NO PAGAMENTO DO IMPOSTO", 'DA CONCLUSÃO DO TRABALHO FISCAL'])
        texto_do_titulo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[
             word.titulos_inseridos()[1] + 1:word.titulos_inseridos()[WordReport.WordReport.PROVAS]]])
        self.assertMultiLineEqual(texto_do_titulo, 'No item 3, aconteceu o seguinte\n')

    def test_remove_item_starting_similar(self):
        word = get_current_audit().get_report()
        word.insere_item(10, 1, 'aconteceu o seguinte', True)
        word.insere_anexo(10, ['eita'])
        self.assertListEqual(list(word.anexos_inseridos().keys()), [10, WordReport.WordReport.PROVAS_GERAIS_BULLET])
        texto_do_titulo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[
             word.titulos_inseridos()[1] + 1:word.titulos_inseridos()[WordReport.WordReport.PROVAS]]])
        self.assertMultiLineEqual(texto_do_titulo,
                                  'No item 10, aconteceu o seguinte\n'
                                  'Os demonstrativos que comprovam especificamente a infringência deste item do '
                                  'auto de infração encontram-se no Anexo do Item 10.\n')
        titulos = word.titulos_inseridos()
        self.assertListEqual([WordReport.WordReport.titulos[t] for t in titulos.keys()],
                             ["DAS IRREGULARIDADES NO PAGAMENTO DO IMPOSTO", 'DA CONCLUSÃO DO TRABALHO FISCAL'])
        self.assertListEqual(list(word.anexos_inseridos().keys()), [10, WordReport.WordReport.PROVAS_GERAIS_BULLET])
        word.remove_item(1)
        word.remove_anexo(1)
        texto_do_titulo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[
             word.titulos_inseridos()[1] + 1:word.titulos_inseridos()[WordReport.WordReport.PROVAS]]])
        self.assertMultiLineEqual(texto_do_titulo,
                                  'No item 10, aconteceu o seguinte\n'
                                  'Os demonstrativos que comprovam especificamente a infringência deste item do '
                                  'auto de infração encontram-se no Anexo do Item 10.\n')
        self.assertListEqual(list(word.anexos_inseridos().keys()), [10, WordReport.WordReport.PROVAS_GERAIS_BULLET])

    def test_insert_item_with_existing_other_title(self):
        word = get_current_audit().get_report()
        word.insere_item(2, 5, 'aconteceu o seguinte', False)
        word.insere_item(3, 5, 'depois piorou', False)

        titulos = word.titulos_inseridos()
        self.assertListEqual([WordReport.WordReport.titulos[t] for t in titulos.keys()],
                             ["DAS IRREGULARIDADES NOS LIVROS FISCAIS",
                              'DA CONCLUSÃO DO TRABALHO FISCAL'])
        texto_do_titulo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[
             word.titulos_inseridos()[5] + 1:word.titulos_inseridos()[WordReport.WordReport.PROVAS]]])
        self.assertMultiLineEqual(texto_do_titulo,
                                  'No item 2, aconteceu o seguinte\n'
                                  'No item 3, depois piorou\n\n')

        word.insere_item(1, 1, 'primeiro foi isso', False)

        titulos = word.titulos_inseridos()
        self.assertListEqual([WordReport.WordReport.titulos[t] for t in titulos.keys()],
                             ["DAS IRREGULARIDADES NO PAGAMENTO DO IMPOSTO",
                              "DAS IRREGULARIDADES NOS LIVROS FISCAIS",
                              'DA CONCLUSÃO DO TRABALHO FISCAL'])
        texto_do_titulo = '\n'.join(
            [p.text for p in
             word.report.paragraphs[
             word.titulos_inseridos()[1] + 1:word.titulos_inseridos()[WordReport.WordReport.PROVAS]]])
        self.assertMultiLineEqual(texto_do_titulo,
                                  'No item 1, primeiro foi isso\n\n'
                                  '- DAS IRREGULARIDADES NOS LIVROS FISCAIS\n'
                                  'No item 2, aconteceu o seguinte\n'
                                  'No item 3, depois piorou\n\n')

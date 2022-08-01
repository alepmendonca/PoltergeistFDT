import datetime
import math
import os
import shutil
import openpyxl
import pandas as pd
import re
import pywintypes
import win32com.client
from dateutil.relativedelta import relativedelta
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Border, Side, Alignment
from copy import copy

from pathlib import Path

from openpyxl.worksheet.worksheet import Worksheet
from pandas._libs.missing import NAType

import Audit
import GeneralFunctions
import MDBReader
import PDFExtractor
from ConfigFiles import Analysis, Infraction
from GeneralFunctions import logger
from SQLReader import SQLReader
from WebScraper import SeleniumWebScraper


class ExcelArrazoadoException(Exception):
    pass


class ExcelArrazoadoCriticalException(ExcelArrazoadoException):
    pass


class ExcelArrazoadoIncompletoException(ExcelArrazoadoException):
    pass


class ExcelArrazoadoAbaInexistenteException(ExcelArrazoadoException):
    pass


def _dataframe_to_rows(df: pd.DataFrame, header=True):
    """
    Copiado e adaptado do openpyxl, mas corrigindo comportamento para Int64
    Convert a Pandas dataframe into something suitable for passing into a worksheet.
    If index is True then the index will be included, starting one row below the header.
    If header is True then column headers will be included starting one column to the right.
    Formatting should be done by client code.
    """
    import numpy
    from pandas import Timestamp
    blocks = df._data.blocks
    ncols = sum(b.shape[0] for b in blocks)
    data = [None] * ncols

    for b in blocks:
        values = b.values

        if b.dtype.type == numpy.datetime64:
            values = numpy.array([Timestamp(v) for v in values.ravel()])
            values = values.reshape(b.shape)
        elif b.dtype.name == 'Int64':
            values = numpy.array([v for v in values.ravel()])
            values = values.reshape(b.shape)

        result = values.tolist()

        for col_loc, col in zip(b.mgr_locs, result):
            data[col_loc] = col

    if header:
        rows = [list(df.columns.values)]
        for row in rows:
            n = []
            for v in row:
                if isinstance(v, numpy.datetime64):
                    v = Timestamp(v)
                n.append(v)
            row = n
            yield row

    expanded = ([v] for v in df.index)
    for idx, v in enumerate(expanded):
        row = [data[j][idx] if not isinstance(data[j][idx], NAType) else None for j in range(ncols)]
        yield row


def _exporta_relatorio_para_planilha(sheet_name: str, analysis: Analysis, df: pd.DataFrame,
                                     wb: Workbook, infraction: Infraction = None):
    try:
        ws = wb.copy_worksheet(wb['template'])
        if infraction and infraction.has_filtro():
            ws.title = infraction.sheet_extended_name(sheet_name)
        else:
            ws.title = sheet_name
        celula_cabecalho_template = ws[f'A{ws.max_row}']
        template_row = ws.max_row
        columns_to_drop = []
        if infraction:
            columns_to_drop = infraction.analysis.filter_columns()
            columns_to_drop.remove(infraction.filtro_coluna)

        cabecalhos = [c for c in df.keys().tolist() if c not in columns_to_drop]

        ws['A7'] = analysis.name if infraction is None else infraction.analysis_name
        # faz merge das primeiras linhas, até a última linha antes do cabeçalho
        coluna_A = [row[0] for row in ws[f'A{ws.min_row}:A{ws.max_row}']]
        coluna_A.reverse()
        for cell in coluna_A:
            if cell.fill.bgColor.value == '00000000':
                ws.merge_cells(start_row=cell.row, end_row=cell.row,
                               start_column=1, end_column=len(cabecalhos))

        # adiciona a imagem do brasao na planilha
        img = Image(r'resources/brasao.png')
        img.anchor = 'A1'
        # fazendo resize da imagem na mao
        img.height *= 0.556
        img.width *= 0.556
        ws.add_image(img)

        # faz um subconjunto do dataframe, caso tenha filtro
        if infraction and infraction.has_filtro():
            df = df.drop(labels=columns_to_drop, axis=1)
            if infraction.is_positive_filter():
                df = df[df[infraction.filtro_coluna] >= 0]
            else:
                df = df[df[infraction.filtro_coluna] <= 0]
            if len(df) == 0:
                wb.remove(ws)
                return

        # joga valores do dataframe na planilha
        for linha in _dataframe_to_rows(df):
            ws.append(linha)

        # formata valores
        df = df.convert_dtypes()
        for idx in range(1, len(df.dtypes) + 1):
            column = openpyxl.utils.get_column_letter(idx)
            col_type = df.dtypes.tolist()[idx - 1]
            if col_type == 'datetime64[ns]':
                for row in ws.iter_rows(min_row=template_row + 1, max_row=ws.max_row, min_col=idx, max_col=idx):
                    if cabecalhos[idx - 1] in ('Período', 'Referência'):
                        row[0].number_format = 'mm/yyyy'
                    else:
                        row[0].number_format = 'dd/mm/yyyy'
                    row[0].alignment = Alignment(horizontal='center', vertical='center')
            elif col_type == 'Float64':
                for row in ws.iter_rows(min_row=template_row + 1, max_row=ws.max_row, min_col=idx, max_col=idx):
                    row[0].number_format = r'_-\R$ * #,##0.00_-'
            elif col_type == 'Int64':
                for row in ws.iter_rows(min_row=template_row + 1, max_row=ws.max_row, min_col=idx, max_col=idx):
                    row[0].number_format = '@'
                    row[0].alignment = Alignment(horizontal='center', vertical='center')

        # entende que o formato do cabeçalho da tabela é igual da última linha da coluna A do template
        # como fez append do dataframe, a linha template precisa ser removida depois
        for i in range(1, len(cabecalhos) + 1):
            ws.cell(row=template_row + 1, column=i)._style = copy(celula_cabecalho_template._style)
        ws.delete_rows(template_row)

        # coloca bordas nos dados
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                             top=Side(style='thin'), bottom=Side(style='thin'))
        for row in ws.iter_rows(min_row=template_row + 1, max_row=ws.max_row, max_col=len(cabecalhos)):
            for cell in row:
                cell.border = thin_border

        # tenta fazer autosize das colunas
        for column_cells in ws.columns:
            if column_cells[-1].number_format.endswith('yyyy'):
                length = max(len(column_cells[template_row - 1].value), len(column_cells[-1].number_format)) + 1
            else:
                length = max(len(str(cell.value) or "") + 1 for cell in column_cells[template_row - 1:])

            if column_cells[-1].number_format == r'_-\R$ * #,##0.00_-':
                # adiciona os caracteres de formatacao de moeda
                length += int((length - 2) / 3) + 4
            logger.debug(f'Coluna {column_cells[-1].column_letter} terá largura {length}')
            ws.column_dimensions[column_cells[-1].column_letter].width = length

        # opcoes de impressao
        ws.print_options.horizontalCentered = True
        ws.print_title_rows = f'{template_row}:{template_row}'
        ws.page_margins.top = 1
        ws.page_margins.bottom = 1
        ws.page_margins.left = 0.5
        ws.page_margins.right = 0.5
        ws.page_margins.header = 0.5
        ws.page_margins.footer = 0.5
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToWidth = True
        ws.evenFooter.center.text = "Página &[Page] de &N"
        ws.oddFooter.center.text = "Página &[Page] de &N"
    except Exception as e:
        logger.exception('Falha na exportação de tabela para Excel')
        if ws:
            wb.remove(ws)
        raise ExcelArrazoadoCriticalException(str(e))


def refresh_planilha_creditos(path: Path):
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False
    excel.ScreenUpdating = False
    excel.DisplayAlerts = False
    excel.EnableEvents = False
    wb = None
    try:
        wb = excel.Workbooks.Open(str(path))
        wb.RefreshAll()
        excel.CalculateUntilAsyncqueriesDone()
        wb.Save()
    except pywintypes.com_error as comerror:
        raise ExcelArrazoadoCriticalException(f'Falha no Excel: {comerror.excepinfo[2]}')
    finally:
        if wb:
            wb.Close()
        excel.Quit()


def print_workbook_as_pdf(wb_path: Path, pdf: Path, sheet_number: int = None, header=False) -> Path:
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False
    excel.ScreenUpdating = False
    excel.DisplayAlerts = False
    excel.EnableEvents = False
    wb = None
    try:
        wb = excel.Workbooks.Open(str(wb_path))
        # Array em COM começa em 1, enquanto arrays em Python começam em 0
        if sheet_number is not None:
            sheets = [sheet_number + 1]
        else:
            sheets = list(range(1, int(wb.Worksheets.Count) + 1))
        # Serve para corrigir o uso das definições de PageSetup no COM
        for idx in sheets:
            ws = wb.Worksheets[idx - 1]
            if header:
                ws.PageSetup.CenterHeader = f'Arquivo {wb_path.name} - Planilha {ws.Name}'
                # Landscape
                ws.PageSetup.Orientation = 2
            for name in ws.Names:
                if name.Name.endswith('!Print_Area'):
                    ws.PageSetup.PrintArea = name.RefersTo
        pdf.unlink(missing_ok=True)
        # assinatura do método ExportedAsFixedFormat disponível em
        # https://docs.microsoft.com/pt-br/office/vba/api/excel.workbook.exportasfixedformat
        if sheet_number is not None:
            ws = wb.Worksheets[sheet_number]
            ws.ExportAsFixedFormat(0, str(pdf.absolute()), 0, True, False)
        else:
            wb.Worksheets(sheets).Select()
            wb.ActiveSheet.ExportAsFixedFormat(0, str(pdf.absolute()), 0, True, False)
        return pdf
    except pywintypes.com_error as comerror:
        raise ExcelArrazoadoCriticalException(f'Falha no Excel: {comerror.excepinfo[2]}')
    finally:
        if wb:
            wb.Close()
        excel.Quit()


class ExcelDDFs:
    def __init__(self):
        self.main_path = Audit.get_current_audit().path()
        dadosAFR = GeneralFunctions.get_local_dados_afr()
        empresa = GeneralFunctions.get_default_name_for_business(Audit.get_current_audit().empresa)

        (self.main_path / 'Achados').mkdir(exist_ok=True)
        self.planilha_path = self.main_path / 'Achados' / f'Arrazoado - {empresa}.xlsm'
        if not self.planilha_path.is_file():
            try:
                shutil.copyfile(os.path.join('resources', 'template.xlsm'), self.planilha_path)
                wb = openpyxl.load_workbook(self.planilha_path, keep_vba=True)
                ws = wb['EFDs']
                ws['A4'].value = f"{dadosAFR['drt_nome']} - {dadosAFR['drt']}"
                ws['A5'].value = f"NÚCLEO DE FISCALIZAÇÃO - NF {dadosAFR['nf']} - EQUIPE FISCAL {dadosAFR['equipe']}"
                ws['A8'].value = f'{Audit.get_current_audit().empresa} - IE {Audit.get_current_audit().ie}'
                self.salva_planilha(wb)
            except Exception as e:
                logger.exception('Ocorreu uma falha ao copiar a planilha template para a pasta da fiscalização')
                try:
                    self.planilha_path.unlink(missing_ok=True)
                except Exception:
                    pass
                raise e
        self.planilha = pd.read_excel(self.planilha_path, sheet_name=None)
        self.creditos_path = self.main_path / 'Achados' / 'Glosa de Créditos.xlsx'

    def get_sheet_as_df(self, sheet_name) -> pd.DataFrame:
        df = pd.read_excel(self.planilha_path, sheet_name=sheet_name, header=9)
        if 'Chave' in df.keys():
            df = df[df['Chave'] >= '1']
        aggregator = [i for i, x in enumerate(df.keys()) if isinstance(x, str) and x.lower() in ('mês', 'dia')]
        if aggregator:
            df = df[~df[df.keys()[0]].str.upper().str.startswith('TOTAL')]
            df = df.iloc[:, 0:aggregator[0]]
        return df

    def create_creditos_sheet(self, saldos: pd.DataFrame):
        wb = None
        if not self.creditos_path.is_file():
            try:
                logger.info('Criando planilha de glosa de créditos com saldos de GIA da CFICMS')
                shutil.copyfile(os.path.join('resources', 'Glosa de Créditos.xlsx'),
                                self.creditos_path)
                wb = openpyxl.load_workbook(self.creditos_path)
                ws = wb['Dados']
                mes_referencia = GeneralFunctions.last_day_of_month(
                    Audit.get_current_audit().get_periodos_da_fiscalizacao()[0][0])
                ws['A2'].value = mes_referencia

                linha_saldo = 2
                for _, referencia in saldos.iterrows():
                    if mes_referencia != referencia['referencia']:
                        raise ExcelArrazoadoCriticalException(f'Não foi encontrada na Conta Fiscal ICMS saldo para '
                                                              f'referência {mes_referencia}! '
                                                              f'Talvez precise editar arquivo cficms.json manualmente...')
                    ws.cell(linha_saldo, 8).value = referencia['saldo']
                    linha_saldo += 1
                    mes_referencia = GeneralFunctions.last_day_of_month(mes_referencia + datetime.timedelta(days=1))
                self.salva_planilha(wb, self.creditos_path)
            except Exception as e:
                logger.exception('Ocorreu uma falha ao copiar a planilha de créditos '
                                 'template para a pasta da fiscalização')
                try:
                    self.creditos_path.unlink(missing_ok=True)
                except Exception:
                    pass
                raise e
            finally:
                if wb is not None:
                    wb.close()

    def generate_creditos_ddf(self, ddf: pd.DataFrame) -> pd.DataFrame:
        wb = None
        glosas_item_path = self.main_path / 'Achados' / 'Glosa - Item.xlsx'
        try:
            logger.info('Preenchendo planilha de glosa de créditos com valores a glosar')
            shutil.copyfile(self.creditos_path, glosas_item_path)
            wb = openpyxl.load_workbook(glosas_item_path)
            ws = wb['Dados']
            mes_inicial = ws['A2'].value
            linha_inicial = 2
            for _, linha in ddf.iterrows():
                if not math.isnan(linha['valor']):
                    mes = linha['referencia']
                    diferenca_referencias = relativedelta(mes, mes_inicial)
                    meses = diferenca_referencias.years * 12 + diferenca_referencias.months
                    ws.cell(meses + linha_inicial, 6).value = linha['valor']
            self.salva_planilha(wb, glosas_item_path)

            glosas = pd.read_excel(glosas_item_path, sheet_name='Subitens')
            glosas = glosas[glosas['subitem'] > 0]
            glosas = glosas.iloc[:, [1, 11, 17, 18, 19]]
            glosas['referencia'] = glosas.iloc[:, 0].map(lambda dt: GeneralFunctions.last_day_of_month(dt))
            resultado = ddf.merge(glosas, on='referencia')
            if 'valor_basico' in resultado.columns:
                resultado = resultado.iloc[:, [1, 3, 8, 9, 10, 11]]
                resultado.columns = ['valor_basico', 'referencia', 'valor', 'dci', 'dij', 'dcm']
                resultado['valor_basico'] = resultado['valor_basico'].apply(
                    lambda v: '{:.2f}'.format(float(v)).replace('.', ','))
            else:
                resultado = resultado.iloc[:, [2, 7, 8, 9, 10]]
                resultado.columns = ['referencia', 'valor', 'dci', 'dij', 'dcm']
                resultado['valor_basico'] = resultado['valor'].apply(
                    lambda v: '{:.2f}'.format(float(v)).replace('.', ','))
            resultado['valor'] = resultado['valor'].apply(
                lambda v: '{:.2f}'.format(float(v)).replace('.', ','))
            resultado['dci'] = resultado['dci'].apply(
                lambda d: None if isinstance(d, NAType) else f'{d.strftime("%d/%m/%y")}'
            )
            resultado['dij'] = resultado['dij'].apply(
                lambda d: None if isinstance(d, NAType) else f'{d.strftime("%d/%m/%y")}'
            )
            resultado['dcm'] = resultado['dcm'].apply(
                lambda d: f'{d.strftime("%d/%m/%y")}'
            )
            return resultado
        except Exception as e:
            logger.exception('Ocorreu uma falha ao copiar a planilha de créditos '
                             'template para a pasta da fiscalização')
            raise e
        finally:
            if wb is not None:
                wb.close()

    def refresh_sheet(self):
        self.planilha = pd.read_excel(self.planilha_path, sheet_name=None)

    def get_sheet_names(self) -> list:
        return list(self.planilha.keys())

    def conta_fiscal_path(self) -> Path:
        return self.main_path / 'Conta Fiscal.pdf'

    def get_vencimentos_GIA(self) -> pd.DataFrame:
        audit = Audit.get_current_audit()
        if not self.conta_fiscal_path().is_file():
            with SeleniumWebScraper(self.main_path) as ws:
                ws.get_conta_fiscal(audit.ie, audit.inicio_auditoria.year, audit.fim_auditoria.year,
                                    self.conta_fiscal_path())
        return PDFExtractor.vencimentos_de_PDF_CFICMS(self.conta_fiscal_path(), self.main_path,
                                                      audit.get_periodos_da_fiscalizacao(rpa=True))

    def get_ddf_from_sheet(self, sheet_name: str, inciso: str, alinea: str):
        self.refresh_sheet()

        vencimentos = self.get_vencimentos_GIA()
        sheet = self.planilha[sheet_name]
        is_monthly_grouped = list(filter(lambda x: isinstance(x, str), sheet.iloc[:, -2]))[0] \
                                 .upper() == 'MÊS'
        titulos_planilha = sheet.select_dtypes(include='object').dropna(axis=0).iloc[0, :].tolist()
        if not is_monthly_grouped and any([titulo in titulos_planilha for titulo in ['Referência', 'Período']]):
            # se a planilha não é agrupada, vou supor que última coluna tem os valores
            titulo_index = int(sheet[sheet[sheet.keys()[0]].isin(titulos_planilha)].index[0])
            titulo = [titulo for titulo in titulos_planilha if titulo in ['Referência', 'Período']][0]
            aba = sheet[titulo_index+1:]
            aba = aba.dropna(axis=0, how='all')
            aba['item'] = aba.index
            aba = aba.iloc[:, [-1, -2, titulos_planilha.index(titulo)]]
            aba['numero'] = aba.index
            aba.columns = ['item', 'valor', 'referencia', 'numero']
            aba['referencia'] = aba['referencia'].apply(lambda r: GeneralFunctions.last_day_of_month(r))
        else:
            aba = sheet[
                sheet.iloc[:, 0].map(lambda texto: isinstance(texto, str) and bool(re.search('Subitem', texto)))]
            aba = aba.dropna(axis=1)
            if aba.empty:
                # pode ser que seja um caso de não totalização - cada linha é uma referência
                raise ExcelArrazoadoIncompletoException(f'Planilha {sheet_name} não tem coluna "Referência" ou "Período" '
                                                        f'(quando itens já estão agrupados) ou ela tem vários itens '
                                                        f'da mesma referência, mas está sem totalizadores!\n'
                                                        f'No segundo caso, execute a macro com CTRL+SHIFT+E, '
                                                        f'salve, feche a planilha e tente novamente!')
            if len(aba.columns) > 4:
                aba.columns = ['item', 'valor_basico', 'valor', 'referencia', 'numero']
            else:
                aba.columns = ['item', 'valor', 'referencia', 'numero']

        aba['referencia'] = aba['referencia'].astype('datetime64[ns]')

        if inciso == 'I' and alinea in ['b', 'c', 'd', 'i', 'j', 'l', 'm']:
            if is_monthly_grouped:
                aba['valor'] = aba['valor'].apply(lambda v: '{:.2f}'.format(float(v)).replace('.', ','))
                ddf = aba.merge(vencimentos, how='left', on='referencia')
                if len(ddf.dropna(axis=0)) < len(ddf):
                    raise ExcelArrazoadoIncompletoException(
                        'Não foram encontradas datas de vencimento no PDF da Conta Fiscal ICMS '
                        'para todas as referências da planilha! '
                        'Verifique se o PDF precisa ser complementado e apague o arquivo cficms.json na pasta Dados!'
                    )
                ddf['vencimento'] = ddf['vencimento'].apply(
                    lambda d: f'{(d + datetime.timedelta(days=1)).strftime("%d/%m/%y")}'
                )
                ddf = ddf[['valor', 'referencia', 'vencimento']]
            else:
                aba['valor'] = aba['valor'].apply(lambda v: '{:.2f}'.format(float(v)).replace('.', ','))
                ddf = aba[['valor', 'referencia']]
                ddf['vencimento'] = ddf['referencia'].apply(
                    lambda d: f'{(d + datetime.timedelta(days=1)).strftime("%d/%m/%y")}'
                )
        elif inciso == 'I' and alinea == 'e':
            aba['valor'] = aba['valor'].apply(lambda v: '{:.2f}'.format(float(v)).replace('.', ','))
            ddf = aba[['valor', 'referencia']]
            ddf['davb'] = ddf['referencia'].apply(
                lambda d: f'{(d + datetime.timedelta(days=1)).strftime("%d/%m/%y")}'
            )
        elif inciso == 'II':
            if alinea != 'j' and len(aba.columns) == 4:
                raise ExcelArrazoadoIncompletoException(
                    'Planilha precisa ter 2 subtotais: valor básico e imposto, nesta ordem. '
                    'Refaça a totalização da planilha selecionando as 2 colunas simultaneamente, '
                    'antes de rodar a macro com CTRL+SHIFT+E')
            self.create_creditos_sheet(vencimentos)
            ddf = aba.merge(vencimentos, on='referencia', how='right')
            ddf = self.generate_creditos_ddf(ddf)
        elif inciso == 'V' and alinea in ['a', 'c', 'm']:
            aba['valor'] = aba['valor'].apply(lambda v: '{:.2f}'.format(float(v)).replace('.', ','))
            ddf = aba[['referencia', 'valor']]
        elif inciso == 'VII' and alinea == 'a':
            if len(aba.columns) == 4:
                aba.columns = ['referencia', 'entrega', 'atraso', 'valor']
                ddf = aba[['referencia', 'valor', 'atraso']]
            else:
                aba.columns = ['referencia', 'valor']
                ddf = aba[['referencia', 'valor']]
                ddf['atraso'] = None
        else:
            raise ExcelArrazoadoCriticalException(f'Inciso/alinea não mapeados: {inciso}, {alinea}')

        assert type(ddf) == pd.DataFrame, \
            'Não gerou uma listagem: não deve ter dados na planilha, ou os dados não foram bem filtrados'
        assert len(ddf) > 0, 'Listagem está vazia, deu algum problema na leitura dos dados'

        ddf['referencia'] = ddf['referencia'].apply(
            lambda d: f'{d.strftime("%d/%m/%y")}'
        )

        return {'inciso': inciso, 'alinea': alinea, 'ddf': ddf, 'mensal': is_monthly_grouped}

    def generate_dados_efds_e_imprime(self, path: Path):
        logger.info('Gerando listagem de EFDs...')
        wb = openpyxl.load_workbook(self.planilha_path, keep_vba=True)
        ws = wb['EFDs']
        try:
            if ws.max_row <= 10:
                with SQLReader(Audit.get_current_audit().schema) as postgres:
                    if not postgres.does_table_exist('escrituracaofiscal'):
                        return
                    qtd, df = postgres.executa_consulta(
                        "SELECT replace(to_char(cpf_cnpj::bigint, '00:000:000/0000-00'), ':', '.') as \"CNPJ\", "
                        "REPLACE(to_char(ie::bigint, '000:000:000:000'), ':', '.') AS \"IE\", "
                        "efd.nome_contribuinte as \"Contribuinte\", "
                        "to_char(efd.dataInicial, 'mm/yyyy') as \"Referência\", "
                        "to_date(substring(efd.localizacaoarquivo FROM '(\d{8})\d+.txt'), 'ddmmyyyy') "
                        "AS \"Data Recepção\", "
                        "efd.hasharquivo::varchar AS \"Hash\" "
                        "FROM escrituracaofiscal as efd ORDER BY efd.datainicial")
                for linha in _dataframe_to_rows(df):
                    ws.append(linha)
                # coloca bordas nos dados
                thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                     top=Side(style='thin'), bottom=Side(style='thin'))
                for row in ws.iter_rows(min_row=11, max_row=ws.max_row, max_col=5):
                    for cell in row:
                        cell.border = thin_border
                self.salva_planilha(wb)
            self.imprime_planilha('EFDs', path)
        except Exception as e:
            logger.exception('Erro no preenchimento de dados de EFD na planilha de arrazoado')
            raise e

    def periodos_de_referencia(self, sheet_name, freq='M'):
        try:
            aba = self.planilha[sheet_name]
        except KeyError:
            raise ExcelArrazoadoAbaInexistenteException(f'Aba {sheet_name} não existe mais na planilha!')
        if type(aba.iloc[-2, -2]) == datetime.datetime:
            aba = aba.iloc[:, [-2]]
        else:
            # considera que a última coluna de data (não timestamp preenchido) encontrada é a referência
            colunas_data = [x for x in aba.iloc[-1, :].tolist()
                            if type(x) == datetime.datetime and x.time() == datetime.time()]
            if len(colunas_data) == 0:
                raise ExcelArrazoadoIncompletoException(f'Planilha {sheet_name} não tem uma coluna de data! '
                                                        f'Deixe a penúltima coluna com a referência!')
            else:
                aba = aba.iloc[:, [aba.iloc[-1, :].tolist().index(colunas_data[-1])]]
        aba.columns = ['referencia']
        aba = aba[aba['referencia'].map(lambda referencia: type(referencia) == datetime.datetime)]
        if freq == 'M':
            aba['referencia'] = aba['referencia'].apply(lambda r: GeneralFunctions.last_day_of_month(r))
        elif freq == 'Y':
            aba['referencia'] = aba['referencia'].apply(lambda r: datetime.datetime(r.year, 1, 1))
        return [pd.Timestamp(npdt).date() for npdt in aba.sort_values(by='referencia')['referencia'].unique()]

    def modelos_documento_fiscal(self, sheet_name):
        try:
            aba = self.planilha[sheet_name]
        except KeyError:
            raise ExcelArrazoadoAbaInexistenteException(f'Aba {sheet_name} não existe mais na planilha!')
        colunas = aba.loc[:, (aba == 'Modelo').any()].columns
        assert len(colunas) == 1, f'Não achei 1 coluna com um campo escrito "Modelo", achei {len(colunas)}'
        modelos = aba[colunas[0]][aba[colunas[0]].map(lambda v: type(v) == int)]
        return modelos.sort_values().unique()

    def imprime_planilha(self, sheet, report_full_path: Path, path: Path = None, item: int = None) -> Path:
        if item:
            # coloca número do anexo na planilha e mostra detalhes, caso subtotais estejam fechados
            openpyxlwb = openpyxl.load_workbook(self.planilha_path, keep_vba=True)
            openpyxlws: Worksheet = openpyxlwb[sheet]

            openpyxlws.cell(row=10,
                            column=len([x.value for x in openpyxlws[10] if isinstance(x.value, str)]) + 1).value = item
            is_grouped = any(x > 0 for x in
                             [v.outline_level for v in [openpyxlws.row_dimensions[idx]
                                                        for idx in range(10, openpyxlws.max_row)]])
            if is_grouped:
                for idx in range(10, openpyxlws.max_row):
                    openpyxlws.row_dimensions[idx].hidden = False
            self.salva_planilha(openpyxlwb)

        wb_path = self.planilha_path if path is None else path
        if type(sheet) == str:
            sheet_number = self.get_sheet_names().index(sheet)
        else:
            sheet_number = sheet
        return print_workbook_as_pdf(wb_path, report_full_path, sheet_number=sheet_number)

    def salva_planilha(self, wb: Workbook, path=None):
        caminho = self.planilha_path if path is None else path
        if wb:
            try:
                wb.save(caminho)
            except PermissionError as pe:
                raise ExcelArrazoadoCriticalException(
                    f'Arquivo Excel {caminho} está aberto, feche-o e tente novamente.')
            finally:
                wb.close()
        if not path:
            self.refresh_sheet()
        else:
            # refresh via com, para salvar os valores calculados
            refresh_planilha_creditos(caminho)

    def exporta_relatorio_para_planilha(self, sheet_name: str, analysis: Analysis, df: pd.DataFrame):
        wb = openpyxl.load_workbook(self.planilha_path, keep_vba=True)
        _exporta_relatorio_para_planilha(sheet_name, analysis, df, wb)
        if len(analysis.filter_columns()) > 0:
            for infraction in analysis.infractions:
                _exporta_relatorio_para_planilha(sheet_name, analysis, df, wb, infraction=infraction)
        self.salva_planilha(wb)

    # TODO PDFExtractor precisa trazer mais dados pra dar certo - ver DDF da Vigor
    def gera_quadro_3(self, quadro_1: Path):
        logger.info('Extraindo informações do Quadro 1 do AIIM para gerar Quadro 3...')
        df = PDFExtractor.get_quadro_1_data(quadro_1)
        wb = None
        quadro3_path = self.main_path / 'AIIM' / 'Quadro 3.xlsm'
        logger.info('Gerando arquivo Quadro 3.xlsm...')
        try:
            shutil.copyfile(Path('resources') / 'Quadro 3.xlsm', quadro3_path)
            wb = openpyxl.load_workbook(quadro3_path, keep_vba=True)
            ws = wb['DDF Original']
            ws['C2'].value = Audit.get_current_audit().cnpj
            ws['G2'].value = Audit.get_current_audit().empresa
            ws['C4'].value = Audit.get_current_audit().aiim_number
            with MDBReader.MDBReader() as aiim2003:
                ws['Q4'].value = aiim2003.get_last_ufesp_stored()
            ws_row = 9
            for linha in df:
                for col, val in enumerate(linha, start=2):
                    # é necessário pular uma coluna a partir da 13, pelo formato da planilha
                    ws.cell(row=ws_row, column=(col + 1 if col >= 13 else col), value=val)
                ws_row += 1
            self.salva_planilha(wb, quadro3_path)
            logger.info('Gerando Quadro 3.pdf...')
            self.imprime_planilha(4, self.main_path / 'AIIM' / 'Quadro 3.pdf', path=quadro3_path)
        except Exception as e:
            logger.exception('Falha no preenchimento do Quadro 3')
            if quadro3_path:
                quadro3_path.unlink(missing_ok=True)
            raise ExcelArrazoadoCriticalException(f'Falha no preenchimento do Quadro 3: {str(e)}')
        finally:
            if wb:
                wb.close()

    def get_operations_for_aiim(self, operacoes_xls: Path):
        operacoes_csv = self.main_path / 'Dados' / 'valor_operacoes.csv'
        csv_df = None
        if operacoes_csv.is_file():
            csv_df = pd.read_csv(str(operacoes_csv), index_col=0, parse_dates=True)
        if not operacoes_xls.is_file():
            if csv_df is not None:
                return csv_df
            else:
                return []
        try:
            logger.info('Encontrei arquivo de relatório Valor Total Documentos Fiscais x GIA, processando valores...')
            wb = openpyxl.load_workbook(str(operacoes_xls))
            ws = wb['Doc Fiscais x GIA']
            data = []
            refs = []

            # usa a coluna de documentos se for maior que a de GIA, e vice-versa
            # não mistura os valores pra evitar problemas na defesa do AIIM
            row = 5
            while type(ws.cell(row=row, column=1).value) == int:
                row += 1
            if type(ws.cell(row=row, column=8).value) == float:
                total_docs = ws.cell(row=row, column=8).value
            else:
                total_docs = float(str(ws.cell(row=row, column=8).value).replace('.', '').replace(',', '.'))
            row = 5
            while type(ws.cell(row=row, column=10).value) == int:
                row += 1
            if type(ws.cell(row=row, column=11).value) == float:
                total_gias = ws.cell(row=row, column=11).value
            else:
                total_gias = float(str(ws.cell(row=row, column=11).value).replace('.', '').replace(',', '.'))
            if total_docs > total_gias:
                logger.info('Decidido usar tabela de documentos fiscais por ter valores maiores, para cadastro de VTO')
                coluna_ref = 1
                coluna_valor = 8
            else:
                logger.info('Decidido usar tabela de GIA por ter valores maiores, para cadastro de VTO')
                coluna_ref = 10
                coluna_valor = 11

            row = 5
            while type(ws.cell(row=row, column=coluna_ref).value) == int:
                ref = ws.cell(row=row, column=coluna_ref).value
                valor = ws.cell(row=row, column=coluna_valor).value
                periodo = datetime.datetime.strptime(str(ref), '%Y%m').date()
                data.append([int(str(ref)[4:]), int(str(ref)[:4]), valor])
                refs.append(periodo)
                row += 1
            refs.sort()
            new_df = pd.DataFrame(data, columns=['Mes', 'Ano', 'Valor Contabil - CFOP'], index=pd.to_datetime(refs))
            if operacoes_csv.is_file() and refs[0] < GeneralFunctions.first_day_of_month_before(datetime.date.today()):
                ops_df = pd.concat([csv_df, new_df])
            else:
                ops_df = new_df
            ops_df = ops_df.drop_duplicates(subset=['Ano', 'Mes'], keep='last').sort_index(ascending=False)
            ops_df.to_csv(operacoes_csv)
            if operacoes_xls.is_file():
                operacoes_xls.unlink()
            return ops_df
        finally:
            if wb:
                wb.close()

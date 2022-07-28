from io import BytesIO
from pathlib import Path
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter
from tika import parser
import pandas as pd
import re
import datetime

import GeneralFunctions


# workaround for PyPDF4 issue #24
# https://github.com/claird/PyPDF4/issues/24
class PdfFileWriterWithStreamAttribute(PdfFileWriter):
    def __init__(self):
        super().__init__()
        self.stream = BytesIO()


def __fix_pdf_removing_trailing_scripts(pdf_file: Path):
    with pdf_file.open(mode='rb+') as p:
        txt = (p.readlines())
        # get the new list terminating correctly
        for i, x in enumerate(txt[::-1]):
            if b'%%EOF' in x:
                actual_line = len(txt) - i
                break
        # return the list up to that point
        txtx = txt[:actual_line]
        if len(txt) > len(txtx):
            # rewrite pdf
            p.seek(0)
            p.truncate()
            p.writelines(txtx)


def merge_pdfs(filename: Path, pdfs: list[Path], remove_original_pdfs: bool = True):
    merger = PdfFileMerger(strict=False)
    try:
        for pdf in pdfs:
            __fix_pdf_removing_trailing_scripts(pdf)
            merger.append(str(pdf.absolute()), import_bookmarks=False)
            # concatena todos os PDFs e apaga os individuais, por padrão
        try:
            filename.unlink(missing_ok=True)
            merger.write(str(filename.absolute()))
            if remove_original_pdfs:
                for f in pdfs:
                    f.unlink(missing_ok=True)
        except IOError:
            # deixa os PDFs lá, se deu algum problema...
            pass
    finally:
        merger.close()


def split_pdf(filename: Path, max_size: int) -> list[Path]:
    # se tamanho em MB for menor que max_size, nem faz nada
    if not filename.is_file():
        return []

    if int(filename.stat().st_size/1024/1024) < max_size:
        return [filename]

    GeneralFunctions.logger.info(f'Dividindo arquivo {filename.name} em arquivos de no máximo {max_size}Mb...')
    original_pdf = PdfFileReader(str(filename.absolute()))
    page_number = 0
    first_page = 0
    pdf_list = []
    tmp_pdf = None
    while page_number < original_pdf.numPages:
        if not tmp_pdf:
            tmp_pdf = PdfFileWriterWithStreamAttribute()
            first_page = page_number
        tmp_pdf.addPage(original_pdf.getPage(page_number))
        tmp_pdf_path = filename.parent / 'tmp.pdf'
        with tmp_pdf_path.open('wb') as tmp_parte:
            tmp_pdf.write(tmp_parte)
        page_number += 1
        if tmp_pdf_path.stat().st_size/1024/1024 > max_size:
            # achei a qtd de paginas maxima, monta o PDF parcial
            tmp_pdf_path.unlink()
            new_pdf_path = Path(str(filename.parent.absolute() / filename.stem) + f' - Parte {len(pdf_list) + 1}.pdf')
            new_pdf = PdfFileWriterWithStreamAttribute()
            for rpagenum in range(first_page, page_number-1):
                new_pdf.addPage(original_pdf.getPage(rpagenum))
            with new_pdf_path.open('wb') as file_parte:
                new_pdf.write(file_parte)
            if page_number < original_pdf.numPages:
                page_number -= 1
                tmp_pdf = None
            pdf_list.append(new_pdf_path)
        elif page_number == original_pdf.numPages:
            new_pdf_path = Path(str(filename.parent.absolute() / filename.stem) + f' - Parte {len(pdf_list) + 1}.pdf')
            tmp_pdf_path.rename(new_pdf_path)
            pdf_list.append(new_pdf_path)
    filename.unlink(missing_ok=True)
    # pode acontecer da regeração reduzir o PDF e ficar só um...
    # aí muda o nome do único arquivo gerado pra ficar igual ao original
    if len(pdf_list) == 1:
        pdf_list[0].rename(filename)
        pdf_list[0] = filename
    return pdf_list


def vencimentos_de_PDF_CFICMS(file_cficms: Path, path_name: Path,
                              periodos_rpa: list[[datetime.date, datetime.date]]) -> pd.DataFrame:
    # busca um PDF do extrato da Conta Fiscal do ICMS
    # varre os meses em busca das linhas de GIA normal, pegando o vencimento
    # retorna um DataFrame com referencia e vencimento
    cficms_json = GeneralFunctions.get_conta_fiscal_json_path(path_name)
    if cficms_json.is_file():
        return pd.read_json(cficms_json, orient='records',
                            dtype={'referencia': 'datetime64[D]', 'vencimento': 'datetime64[D]', 'saldo': 'Float64'})

    raw = parser.from_file(str(file_cficms.absolute()))
    texto = str(raw['content'])
    referencias = []
    vencimentos = []
    saldos = []
    referencia: datetime.date = None
    vencimento: datetime.date = None
    saldo: float = None
    buscar_vencimento = False
    for linha in texto.splitlines():
        if len(linha) == 0:
            continue
        match = re.match(r'^([A-ZÇ]+)\s+(\d{4})$', linha)
        if match:
            if referencia:
                if vencimento and saldo:
                    vencimentos.append(vencimento)
                    saldos.append(saldo)
                else:
                    for periodo in periodos_rpa:
                        if periodo[0] <= referencia <= periodo[1]:
                            raise Exception(f'Não foi localizado vencimento ou saldo para a referência '
                                            f'{referencia.strftime("%m/%Y")} '
                                            f'no PDF da Conta Fiscal ICMS! Talvez segue um formato inesperado '
                                            f'pelo sistema...')
            referencia = GeneralFunctions.last_day_of_month(
                datetime.date(int(match.group(2)), GeneralFunctions.meses.index(match.group(1).capitalize()) + 1, 1)
            )
            referencias.append(referencia)
            vencimento = None
            saldo = None
            buscar_vencimento = False
        elif referencia and (not vencimento or not saldo):
            matchgia = re.match(r'^GIA\s+\d+.*\s+-([\d.,]+)\s+.*DATA DE VENCIMENTO \((\d{2})/(\d{2})/(\d{4})\)', linha)
            if matchgia:
                saldo = float(matchgia.group(1).replace('.', '').replace(',', '.'))
                vencimento = datetime.date(int(matchgia.group(4)), int(matchgia.group(3)), int(matchgia.group(2)))
            else:
                if buscar_vencimento:
                    matchgia = re.match(r'906\*DATA DE VENCIMENTO \((\d{2})/(\d{2})/(\d{4})\)', linha)
                    if matchgia:
                        vencimento = datetime.date(int(matchgia.group(3)), int(matchgia.group(2)),
                                                   int(matchgia.group(1)))
                        buscar_vencimento = False
                else:
                    matchgia = re.match(r'^GIA\s+\d+.*\s+([\d.,]+)\s+1\d+.*SALDO CREDOR.*', linha)
                    if matchgia:
                        buscar_vencimento = True
                        saldo = -1*float(matchgia.group(1).replace('.', '').replace(',', '.'))
                    else:
                        matchgia = re.match(r'^GIA\s+\d+.*\s+-([\d.,]+)\s\d+.*', linha)
                        if matchgia:
                            buscar_vencimento = True
                            saldo = float(matchgia.group(1).replace('.', '').replace(',', '.'))

    if vencimento and saldo:
        vencimentos.append(vencimento)
        saldos.append(saldo)
    referencias_rpa_encontradas = [ref for ref in referencias
                                   if any([p[0] <= ref <= p[1] for p in periodos_rpa])]
    if len(referencias_rpa_encontradas) != len(vencimentos) \
            or len(referencias_rpa_encontradas) != len(saldos):
        raise Exception('Não localizou todos os saldos de GIA ou vencimentos! Possivelmente são casos especiais '
                        'não tratados pelo sistema!')
    cficms = pd.DataFrame(data={'referencia': referencias_rpa_encontradas,
                                'vencimento': vencimentos,
                                'saldo': saldos})
    cficms['referencia'] = cficms['referencia'].astype('datetime64[D]')
    cficms['vencimento'] = cficms['vencimento'].astype('datetime64[D]')
    cficms['saldo'] = cficms['saldo'].astype('Float64')
    cficms.to_json(cficms_json, orient='records', date_format='iso')
    return cficms


def get_quadro_1_data(quadro1_file: Path):
    raw = parser.from_file(str(quadro1_file))
    texto = str(raw['content'])
    linhas = texto.splitlines()
    linhas = [linha for linha in linhas[linhas.index('18') + 1:] if re.match(r'^\d+\.?\s', linha)]
    df = []
    item = 1
    for subitem in linhas:
        subitem = subitem.replace('R$ ', '').replace('LI', 'LI 0 0')
        novo_item = int(re.search(r'^\d+', subitem).group())
        if novo_item not in (item, item + 1):
            continue
        else:
            item = novo_item
        subitem = re.sub(r'^(?P<item>\d+)\.\s+', r'\g<item>.', subitem)
        subitem = re.sub(r'^(?P<item>\d+)\s+(\d+\s\w+)\s', r'\g<item> descricao ', subitem)
        colunas = subitem.split()
        linha = []
        # tem grupo de valor original, imposto e multa, valor original e multa ou só multa
        if colunas[1].find(',') > 0:
            if colunas[2].find('/') > 0:
                if colunas[6].find('/') > 0 and len(colunas) >= 8:
                    # tem os três
                    linha.extend(colunas[:9])
                else:
                    # sem valor original, tem multa com valor básico
                    linha = colunas[:1]
                    linha.extend([None for _ in range(4)])
                    linha.extend(colunas[1:5])
            elif colunas[2].find(',') > 0:
                # não tem juros
                linha = colunas[:2]
                linha.extend([None for _ in range(3)])
                linha.append(colunas[2])
                if colunas[3].find('/') > 0:
                    # tem taxas de multa
                    linha.extend(colunas[3:5])
                else:
                    linha.extend([None for _ in range(2)])
        elif colunas[1] == 'descricao':
            # tem multa sem valor básico
            linha = colunas[:1]
            linha.extend([None for _ in range(7)])
            linha.append(colunas[1])
        else:
            linha = colunas[:1]

        fim_linha = []
        if colunas[-1].find(',') > 0:
            # não tem coluna 15 de data
            fim_linha = [colunas[-1], None]
        elif colunas[-1].find('/') > 0:
            if colunas[-2].find(',') > 0:
                # tem colunas 14 e 15
                fim_linha.append(colunas[-2])
            fim_linha.append(colunas[-1])

        linha = linha + [None for _ in range(15 - len(linha) - len(fim_linha))] + fim_linha
        # coluna 11 é relevante apenas se for 'MI'
        if 'MI' in colunas:
            linha[10] = 'MI'
        # converte dados para tipos numérico e data
        for i in range(15):
            if linha[i] is None:
                continue
            elif linha[i].find('/') > 0:
                linha[i] = datetime.datetime.strptime(linha[i], '%d/%m/%y')
            elif linha[i].find(',') > 0:
                linha[i] = float(linha[i].replace('.', '').replace(',', '.'))

        df.append(linha)
    return df

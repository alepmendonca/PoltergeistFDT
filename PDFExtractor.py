import pandas as pd
import re
import datetime
from dateutil.rrule import rrule, MONTHLY
import GeneralFunctions
from pathlib import Path
import fitz


class PDFUtilitiesException(Exception):
    pass


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


def parse_pdf(file: Path, sorted_pdf=False) -> list[str]:
    doc = fitz.Document()
    texto_pdf: list[str] = []
    try:
        doc = fitz.Document(file)
        for page in doc:
            texto_pdf.extend(page.get_text(
                flags=~fitz.TEXT_PRESERVE_SPANS & ~fitz.TEXT_PRESERVE_IMAGES,
                sort=sorted_pdf).splitlines())
    finally:
        if doc is not None:
            doc.close()
    return texto_pdf


def merge_pdfs(filename: Path, pdfs: list[Path], remove_original_pdfs: bool = True):
    merger = fitz.Document()
    for pdf_path in pdfs:
        pdf = None
        try:
            pdf = fitz.Document(pdf_path)
            __fix_pdf_removing_trailing_scripts(pdf_path)
            merger.insert_pdf(pdf)
        finally:
            if pdf is not None:
                pdf.close()

    # concatena todos os PDFs e apaga os individuais, por padrão
    filename.unlink(missing_ok=True)
    merger.save(filename)
    merger.close()

    if remove_original_pdfs:
        for f in pdfs:
            f.unlink(missing_ok=True)


def split_pdf(filename: Path, max_size: int) -> list[Path]:
    # se tamanho em MB for menor que max_size, nem faz nada
    if not filename.is_file():
        return []

    if int(filename.stat().st_size / 1024 / 1024) < max_size:
        return [filename]

    GeneralFunctions.logger.info(f'Dividindo arquivo {filename.name} em arquivos de no máximo {max_size}Mb...')
    original_pdf = fitz.Document(filename)
    page_number = 0
    first_page = 0
    pdf_list = []
    while page_number < original_pdf.page_count:
        tmp_pdf = fitz.Document()
        new_pdf_path = Path(str(filename.parent.absolute() / filename.stem) + f' - Parte {len(pdf_list) + 1}.pdf')
        tmp_pdf.insert_pdf(original_pdf, from_page=first_page, to_page=page_number)
        file_size = len(tmp_pdf.tobytes())
        tmp_pdf.close()
        page_number += 1
        if file_size / 1024 / 1024 > max_size:
            # achei a qtd de paginas maxima, monta o PDF parcial
            new_pdf = fitz.Document()
            new_pdf.insert_pdf(original_pdf, from_page=first_page, to_page=page_number - 1)
            new_pdf.save(new_pdf_path)
            if page_number < original_pdf.page_count:
                page_number -= 1
                first_page = page_number
            pdf_list.append(new_pdf_path)
        elif page_number == original_pdf.page_count:
            new_pdf = fitz.Document()
            new_pdf.insert_pdf(original_pdf, from_page=first_page)
            new_pdf.save(new_pdf_path)
            pdf_list.append(new_pdf_path)

    original_pdf.close()
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

    referencias = {}
    linha_gia = False
    referencia: datetime.date = None
    vencimento: datetime.date = None
    saldo: float = None
    linhas = parse_pdf(file_cficms, sorted_pdf=True)
    regex_referencia = re.compile(r'^([A-ZÇ]+)\s+(\d{4})$')
    regex_valor = re.compile(r'^-*([\d.]+,\d{2})$')
    regex_vencimento = re.compile(r'.*DATA DE VENCIMENTO \((\d{2})/(\d{2})/(\d{4})\)')
    for idx in range(0, len(linhas)):
        linha = linhas[idx]
        if not referencia:
            match = regex_referencia.match(linha)
            if match:
                referencia = GeneralFunctions.last_day_of_month(
                    datetime.date(int(match.group(2)), GeneralFunctions.meses.index(match.group(1).capitalize()) + 1, 1)
                )
                vencimento = None
                saldo = None
        elif referencia and (not vencimento or saldo is None):
            if linha == 'GIA':
                if not linha_gia:
                    linha_gia = True
                    continue
            if linha_gia:
                if regex_valor.match(linha):
                    saldo = -1 * float(linha.replace('.', '').replace(',', '.'))
                match_vencimento = regex_vencimento.match(linha)
                if match_vencimento:
                    vencimento = datetime.date(int(match_vencimento.group(3)), int(match_vencimento.group(2)),
                                               int(match_vencimento.group(1)))
                if 'NAO APRESENTOU GIA' in linha:
                    # caso não apresente GIA em uma referência, conforme planilha de glosas,
                    # o saldo deve ser considerado zerado
                    saldo = 0.0
        if referencia and vencimento is not None and saldo is not None:
            referencias[referencia] = {'vencimento': vencimento, 'saldo': saldo}
            referencia = None
            saldo = None
            vencimento = None
            linha_gia = False

    referencias_rpa_encontradas = [ref for ref in referencias.keys()
                                   if any([p[0] <= ref <= p[1] for p in periodos_rpa])]
    if len(referencias_rpa_encontradas) != sum([len(list(rrule(MONTHLY, dtstart=periodo[0], until=periodo[1])))
                                                for periodo in periodos_rpa]):
        raise Exception('Não localizou todos os saldos de GIA ou vencimentos! Possivelmente são casos especiais '
                        'não tratados pelo sistema!')
    cficms = pd.DataFrame(data={'referencia': referencias.keys(),
                                'vencimento': [vlw['vencimento'] for vlw in referencias.values()],
                                'saldo': [vlw['saldo'] for vlw in referencias.values()]})
    cficms['referencia'] = cficms['referencia'].astype('datetime64[D]')
    cficms['vencimento'] = cficms['vencimento'].astype('datetime64[D]')
    cficms['saldo'] = cficms['saldo'].astype('Float64')
    cficms.to_json(cficms_json, orient='records', date_format='iso')
    return cficms


def get_quadro_1_data(quadro1_file: Path):
    pdf = parse_pdf(quadro1_file, sorted_pdf=True)
    itens = []
    linhas = []
    start_page = 0
    last_page_idx = [idx for idx in range(0, len(pdf)) if pdf[idx].startswith('  **Valor da Ufesp')][0]
    while True:
        # remove partes desnecessárias
        start_page = pdf.index('DIRETORIA EXECUTIVA DA ADMINISTRAÇÃO TRIBUTÁRIA', start_page) + 2
        if start_page > last_page_idx:
            break
        end_page = pdf.index('AIIM', start_page + 1)
        itens.extend(pdf[start_page:end_page])

    # limpando os itens
    itens = [item.replace('R$ ', '') for item in itens]
    itens = [item for item in itens if len(item.strip()) > 0]
    li_idxs = [idx for idx in range(0, len(itens)) if itens[idx] == 'LI']
    for i in range(0, len(li_idxs)):
        itens.insert(li_idxs[i] + 2 * i + 1, '0')
        itens.insert(li_idxs[i] + 2 * i + 1, '0')

    # agrupando textos em uma única linha, como na visualização do PDF
    idx_itens = [idx for idx in range(0, len(itens)) if re.match(r'\d+\.\s+\d+$', itens[idx])]
    # adiciona como inicio de linha os casos em que há uma descrição na multa (não tem data fim no final)
    desc_idxs = [idx for idx in range(0, len(itens)) if re.match(r'^\d+\s+\w+', itens[idx].strip())]
    for i in range(0, len(desc_idxs)):
        idx_itens.append(desc_idxs[i] - 1)
    idx_itens.sort()
    # adiciona como inicio de linha os casos em que é número isolado
    regex_num = re.compile(r'^\d+$')
    regex_dt = re.compile(r'^\d{2}/\d{2}/\d{2}$')
    for idx in range(0, len(itens)):
        if regex_num.match(itens[idx]) and (idx == 0 or regex_dt.match(itens[idx-1])):
            idx_itens.append(idx)
    idx_itens = sorted(list(set(idx_itens)))

    for i in range(0, len(idx_itens) - 1):
        linhas.append(itens[idx_itens[i]:idx_itens[i + 1]])
    linhas.append(itens[idx_itens[-1]:])
    linhas = sorted(linhas, key=lambda x: (int(x[0].split('.')[0].strip()),
                                           0 if len(x[0].split('.')) == 1 else int(x[0].split('.')[1].strip())))

    df = []
    item = 1
    for subitem in linhas:
        novo_item = int(re.search(r'^\d+', subitem[0]).group())
        if novo_item not in (item, item + 1):
            continue
        else:
            item = novo_item
        subitem[0] = re.sub(r'^(?P<item>\d+)\.\s+', r'\g<item>.', subitem[0])
        # serve para não dar pau numa fórmula da planilha...
        if subitem[0].find('.') < 0:
            subitem[0] += '.1'
        colunas = subitem
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


def highlight_pdf(caminho_pdf: Path, textos: list[str]) -> Path:
    doc = fitz.Document(str(caminho_pdf.resolve()))
    selection = fitz.Document()

    try:
        header_end = 'CST/ICMS'
        footer_beginning = 'Página'
        beginning_regex = re.compile(r'.*' + header_end + r'\s(.*?)\s\d{2}/\d{2}/\d{4}')
        textointeiro_regexes = [re.compile('.*(' + texto + r'.*?)\s\d{2}/\d{2}/\d{4}') for texto in textos]
        textoparcial_regexes = [re.compile('.*(' + texto + r'.*?)\s' + footer_beginning) for texto in textos]
        gets_beginning_page = False
        textos_a_procurar = textos
        for page in doc:
            include_page = False
            tp = page.get_textpage()
            texto_pdf = page.get_text("text", textpage=tp).replace('\n', ' ')
            if gets_beginning_page:
                match = beginning_regex.match(texto_pdf)
                if match:
                    rect = page.search_for(match.group(1), quads=True, textpage=tp)
                    page.add_highlight_annot(quads=rect)
                    include_page = True
                gets_beginning_page = False
            textos_a_remover = []
            for idx in range(0, len(textointeiro_regexes)):
                match = textointeiro_regexes[idx].match(texto_pdf)
                if match:
                    rectangle = page.search_for(match.group(1), quads=True, textpage=tp)
                    page.add_highlight_annot(quads=rectangle)
                    include_page = True
                    textos_a_remover.append(idx)
            for idx in [idx for idx in range(0, len(textoparcial_regexes)) if idx not in textos_a_remover]:
                match = textoparcial_regexes[idx].match(texto_pdf)
                if match:
                    rectangle = page.search_for(match.group(1), quads=True, textpage=tp)
                    page.add_highlight_annot(quads=rectangle)
                    gets_beginning_page = True
                    include_page = True
                    textos_a_remover.append(idx)
            if include_page:
                selection.insert_pdf(doc, from_page=page.number, to_page=page.number)
            for idx in sorted(textos_a_remover, reverse=True):
                textos_a_procurar.pop(idx)
                textointeiro_regexes.pop(idx)
                textoparcial_regexes.pop(idx)
            if not textos_a_procurar and not gets_beginning_page:
                break
        if textos_a_procurar:
            raise PDFUtilitiesException(
                f'Não foram encontrados todos os textos no PDF {caminho_pdf.name}: '
                f'{textos_a_procurar}')
        doc.close()
        caminho_selection = caminho_pdf.parent / f'{caminho_pdf.stem}-selecao.pdf'
        selection.save(str(caminho_selection.resolve()))
        return caminho_selection
    finally:
        if not doc.is_closed:
            doc.close()
        selection.close()

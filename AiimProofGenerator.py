import datetime
import os
import re
import threading
from pathlib import Path

import pandas as pd
from pandas import Timestamp

import ExcelDDFs
import GeneralFunctions
import PDFExtractor
import WebScraper
import WordReport
from Audit import AiimItem, get_current_audit
from EFDPVAReversed import EFDPVAReversed
from GeneralFunctions import logger
from WebScraper import SeleniumWebScraper

SAMPLING = 5
MIN_SAMPLE = 5
MAX_SAMPLE = 30
SUPPORTED_DFE_MODELS = [55, 57, 59]


class AiimProofException(Exception):
    pass


def generate_general_proofs_file() -> list[str]:
    GeneralFunctions.clean_tmp_folder()
    arquivo_path = get_current_audit().aiim_path() / 'Provas Gerais.pdf'
    capa = GeneralFunctions.get_tmp_path() / 'capa.pdf'
    WordReport.cria_capa_para_anexo('PROVAS GERAIS', capa)
    arquivos = [capa]
    descricao_arquivos = ['Ordem de Serviço Fiscal assinada']
    if (get_current_audit().path() / 'OSF Assinada.pdf').is_file():
        arquivos.append(get_current_audit().path() / 'OSF Assinada.pdf')
    else:
        descricao_arquivos[0] += ' (ARQUIVO NÃO LOCALIZADO, JUNTAR MANUALMENTE)'
    if get_current_audit().get_periodos_da_fiscalizacao(rpa=True):
        efds = GeneralFunctions.get_tmp_path() / 'efds.pdf'
        descricao_arquivos.append('Lista de arquivos digitais de Escrituração Fiscal Digital - EFD - '
                                  'entregues pelo contribuinte e considerados na instrução do '
                                  'presente auto de infração')
        get_current_audit().get_sheet().generate_dados_efds_e_imprime(efds)
        arquivos.append(efds)
    if get_current_audit().get_periodos_da_fiscalizacao(rpa=True):
        vencimentos = get_current_audit().get_sheet().get_vencimentos_GIA()
        ultima_referencia_cf = pd.Timestamp(vencimentos.iloc[-1, 0]).date()
        texto = 'Conta Fiscal do ICMS do contribuinte contendo as referências do período de fiscalização'
        if ultima_referencia_cf > get_current_audit().fim_auditoria:
            texto += f' e estendendo-se o extrato até a referência {ultima_referencia_cf.strftime("%m/%Y")}, ' \
                     f'devido à utilização destas referências para cálculo de DDF que considere o mês em que ' \
                     f'o saldo do contribuinte torna-se devedor, nos termos do art. 96, I, b da Lei 6.374/89'
        arquivos.append(get_current_audit().get_sheet().conta_fiscal_path())
        descricao_arquivos.append(texto)
    if get_current_audit().receipt_digital_files:
        if not (get_current_audit().notification_path() / 'notif_recibo.pdf').is_file() or \
                not (get_current_audit().notification_path() / 'Recibo de Entrega de Arquivos Digitais.pdf').is_file():
            logger.info('Baixando notificação de recibo de entrega de arquivos digitais...')
            with SeleniumWebScraper() as ws:
                ws.get_notification(get_current_audit().receipt_digital_files,
                                    get_current_audit().notification_path() / 'notif_recibo.pdf',
                                    get_current_audit().notification_path(), only_after_received=False)
        arquivos.append(get_current_audit().notification_path() / 'notif_recibo.pdf')
        arquivos.append(get_current_audit().notification_path() / 'Recibo de Entrega de Arquivos Digitais.pdf')
        descricao_arquivos.append(f'Notificação DEC {get_current_audit().receipt_digital_files}, contendo '
                                  f'recibo de entrega de arquivos digitais pelo contribuinte, em resposta '
                                  f'às notificações fiscais')
    logger.info('Juntando provas no arquivo Provas Gerais.pdf...')
    PDFExtractor.merge_pdfs(arquivo_path, arquivos, remove_original_pdfs=False)
    return descricao_arquivos


def get_aiim_listing_from_sheet(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    if not item.planilha:
        return []
    logger.info('Gerando listagem inicial a partir da planilha...')
    return [get_current_audit().get_sheet().imprime_planilha(item.planilha,
                                                             ws.tmp_path / f'lista{item.item}.pdf',
                                                             item=item.item)]


def get_notification_and_response(item: AiimItem, ws: SeleniumWebScraper) -> list[Path]:
    proofs = []
    if item.notificacao:
        # junta notificação e anexos
        notification_file = f'notificacao{item.notification_numeric_part()}.pdf'
        notification_path = item.notification_path() / notification_file
        notification_attachment_path = item.notification_path() / 'Anexos'
        notification_attachment_path.mkdir(exist_ok=True)
        if not notification_path.is_file():
            logger.info(f'Baixando notificação {item.notificacao}...')
            if not ws.get_notification(item.notificacao, notification_path, notification_attachment_path):
                raise AiimProofException(
                    f'Ainda não houve ciência (expressa ou tácita) da notificação {item.notificacao}, '
                    f'deve-se aguardar para juntar no AIIM...')
        proofs.append(notification_path)
        proofs.extend([notification_attachment_path / f
                       for f in next(os.walk(notification_attachment_path), (None, None, []))[2]])

        if item.notificacao_resposta:
            # baixa expediente Sem Papel na pasta Respostas, caso tenha sido apontado
            arquivo = item.notification_response_path() / (re.sub(r'[^A-Z0-9]', '', item.notificacao_resposta) + '.pdf')
            if not arquivo.is_file():
                logger.info(f'Baixando resposta de notificação no expediente {item.notificacao_resposta}...')
                download = ws.get_expediente_sem_papel(item.notificacao_resposta)
                GeneralFunctions.move_downloaded_file(download, arquivo.name, arquivo, 10)
            proofs.append(arquivo)

        # junta PDFs e impressao de arquivos Excel existentes na pasta Respostas e subpastas
        for (path, _, files) in os.walk(item.notification_response_path()):
            for file in files:
                suffix = Path(file).suffix.lower()
                if suffix in ['.xlsx', '.xls', '.xlsm']:
                    logger.info(f'Gerando PDF do arquivo de resposta à notificação {file}...')
                    proofs.append(ExcelDDFs.print_workbook_as_pdf(
                        Path(path) / file,
                        ws.tmp_path / f'{Path(file).stem}.pdf', header=True))
                elif suffix == '.pdf':
                    proofs.append(Path(path) / file)
                else:
                    logger.warning(f'Não foi adicionado como prova o arquivo {file}, tipo de arquivo não tratado.')
    return proofs


def _get_sample_size(total: int) -> int:
    if total == 0:
        return total
    if MIN_SAMPLE / total > 0.3:
        return total
    sample = int(total * SAMPLING / 100)
    if sample > MAX_SAMPLE:
        return MAX_SAMPLE
    return sample if sample > MIN_SAMPLE else MIN_SAMPLE


def has_sample(item: AiimItem) -> bool:
    listing = _get_sample(item)
    return len(listing) > _get_sample_size(len(listing))


def _get_sample(item: AiimItem) -> pd.DataFrame:
    if item.df:
        return item.df
    logger.info('Levantando informações da planilha para verificar o tamanho da amostra de DF-e')
    df = get_current_audit().get_sheet().get_sheet_as_df(item.planilha)

    if 'Chave' in df.keys():
        if 'Modelo' not in df.keys():
            df['Modelo'] = pd.to_numeric(df['Chave'].str[20:22])
        df = df[df['Modelo'].isin(SUPPORTED_DFE_MODELS)]
    return df


def get_df_list(item: AiimItem) -> pd.DataFrame:
    df = _get_sample(item)
    amostragem = _get_sample_size(len(df))
    logger.info(f'Tentará buscar {amostragem} amostras de DF-e!')
    if 'Chave' not in df.keys():
        return df

    qtd_por_modelo = {model: len(df[df['Modelo'] == model]) for model in SUPPORTED_DFE_MODELS}
    # ordena da menor qtd pra maior, para pegar amostras menores primeiro
    qtd_por_modelo = {k: v for k, v in sorted(qtd_por_modelo.items(), key=lambda qtd: qtd[1])}
    value_column = df.keys()[[i for i, x in enumerate(df.dtypes.tolist()) if x == 'Float64'][-1]]
    dfe = pd.DataFrame()
    for model in qtd_por_modelo.keys():
        models_to_get = len(SUPPORTED_DFE_MODELS) - list(qtd_por_modelo.keys()).index(model)
        possible_sample = qtd_por_modelo[model]
        model_sample = min(possible_sample, int(amostragem / models_to_get))
        if model_sample > 0:
            dfe = pd.concat(
                [dfe, df[df['Modelo'] == model].sort_values(by=value_column, ascending=False)[:model_sample]])
            amostragem -= model_sample
    return dfe


def get_dfe(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    paths = []
    df = item.get_dfs_list_for_proof_generation()
    for model in SUPPORTED_DFE_MODELS:
        dfe = df[df['Modelo'] == model]['Chave']
        if not dfe.empty:
            logger.info(f'Baixando transcrições de documentos fiscais modelo {model}...')
            if model == 59:
                paths.extend(ws.print_sat_cupom(dfe.tolist()))
            else:
                dfe = ';'.join(dfe.tolist())
                report = [k for k, v in WebScraper.launchpad_report_options.items()
                          if v['Grupo'] == 'Prova' and v.get('Modelo', 0) == model][0]
                pdf_file = ws.get_launchpad_report(report, f'dfe{model}.pdf', threading.Event(), None, [dfe])
                paths.append(pdf_file)
    return paths


def get_lre(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    df = item.get_dfs_list_for_proof_generation()
    date_columns = df.keys()[[i for i, x in enumerate(df.dtypes.tolist()) if x == 'datetime64[ns]']].tolist()
    if not [x for x in date_columns if x.upper().find('ENTRADA') >= 0]:
        raise AiimProofException('Não existe na planilha uma coluna de data contendo no título "Entrada". '
                                 'Não é possível localizar as provas no Livro Registro de Entradas '
                                 'sem a data de entrada. '
                                 'Altere o título da coluna certa para gerar as provas do LRE.')
    if not [x for x in date_columns if x.upper().find('EMISS') >= 0]:
        raise AiimProofException('Não existe na planilha uma coluna de data contendo no título "Emiss". '
                                 'Não é possível localizar as provas no Livro Registro de Entradas '
                                 'sem a data de emissão. '
                                 'Altere o título da coluna certa para gerar as provas do LRE.')
    if not [x for x in df.keys() if x.upper().find('CHAVE') >= 0]:
        raise AiimProofException('Não existe na planilha uma coluna contendo no título "Chave". '
                                 'Não é possível localizar as provas no Livro Registro de Entradas '
                                 'sem a chave do documento. '
                                 'Altere o título da coluna certa para gerar as provas do LRE.')
    coluna_entrada = [x for x in date_columns if x.upper().find('ENTRADA') >= 0][0]
    coluna_emissao = [x for x in date_columns if x.upper().find('EMISS') >= 0][0]
    coluna_chave = [x for x in df.keys() if x.upper().find('CHAVE') >= 0][0]
    df.sort_values(by=coluna_entrada, inplace=True)
    referencias = list(set([GeneralFunctions.last_day_of_month(Timestamp(t).date()) for t in df[coluna_entrada]]))
    paths = []
    for ref in sorted(referencias):
        lre_file = Path('tmp', f'lre{ref.strftime("%Y%m")}.pdf')
        lre_file.unlink(missing_ok=True)
        pva.print_LRE(ref, lre_file)
        df_ref = df[(df[coluna_entrada].dt.month == ref.month) & (df[coluna_entrada].dt.year == ref.year)]
        textos_a_procurar = df_ref.apply(
            lambda x: f"{x[coluna_entrada].strftime('%d/%m/%Y')} {x[coluna_emissao].strftime('%d/%m/%Y')} "
                      f"{int(x[coluna_chave][25:34])} {int(x[coluna_chave][20:22])}",
            axis=1).tolist()
        logger.info(f'Extraindo folhas do LRE {ref.strftime("%m/%Y")} '
                    f'contendo {len(textos_a_procurar)} documentos fiscais...')
        selection_file = PDFExtractor.highlight_pdf(lre_file, textos_a_procurar)
        paths.append(selection_file)
    return paths


def get_lraicms(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    df = item.get_dfs_list_for_proof_generation()
    date_column = df.keys()[[i for i, x in enumerate(df.dtypes.tolist()) if x == 'datetime64[ns]'][-1]]
    df.sort_values(by=date_column)
    referencias = [Timestamp(t).date() for t in df[date_column].unique()]
    paths = []
    for ref in referencias:
        file = Path('tmp', f'lraicms{ref.strftime("%Y%m")}.pdf')
        file.unlink(missing_ok=True)
        pva.print_LRAICMS(ref, file)
        paths.append(file)
    return paths


def get_lri(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    df = item.get_dfs_list_for_proof_generation()
    date_column = df.keys()[[i for i, x in enumerate(df.dtypes.tolist()) if x == 'datetime64[ns]'][-1]]
    df.sort_values(by=date_column)
    referencias = set([Timestamp(t).date().year for t in df[date_column].unique()])
    paths = []
    for ano in referencias:
        file = Path('tmp', f'lri{ano}.pdf')
        file.unlink(missing_ok=True)
        pva.print_LRI(datetime.datetime.date(ano, 2, 1), file)
        paths.append(file)
    return paths


def get_lrs(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    df = item.get_dfs_list_for_proof_generation()
    date_columns = df.keys()[[i for i, x in enumerate(df.dtypes.tolist()) if x == 'datetime64[ns]']].tolist()
    if not [x for x in date_columns if x.upper().find('EMISS') >= 0]:
        raise AiimProofException('Não existe na planilha uma coluna de data contendo no título "Emiss". '
                                 'Não é possível localizar as provas no Livro Registro de Saídas '
                                 'sem a data de emissão. '
                                 'Altere o título da coluna certa para gerar as provas do LRS.')
    if not [x for x in df.keys() if x.upper().find('CHAVE') >= 0]:
        raise AiimProofException('Não existe na planilha uma coluna contendo no título "Chave". '
                                 'Não é possível localizar as provas no Livro Registro de Saídas '
                                 'sem a chave do documento. '
                                 'Altere o título da coluna certa para gerar as provas do LRS.')
    coluna_emissao = [x for x in date_columns if x.upper().find('EMISS') >= 0][0]
    coluna_chave = [x for x in df.keys() if x.upper().find('CHAVE') >= 0][0]
    df.sort_values(by=coluna_emissao, inplace=True)
    referencias = list(set([GeneralFunctions.last_day_of_month(Timestamp(t).date()) for t in df[coluna_emissao]]))
    paths = []
    for ref in sorted(referencias):
        lrs_file = Path('tmp', f'lrs{ref.strftime("%Y%m")}.pdf')
        lrs_file.unlink(missing_ok=True)
        pva.print_LRS(ref, lrs_file)
        df_ref = df[(df[coluna_emissao].dt.month == ref.month) & (df[coluna_emissao].dt.year == ref.year)]
        textos_a_procurar = df_ref.apply(
            lambda x: f"{x[coluna_emissao].strftime('%d/%m/%Y')} {int(x[coluna_chave][25:34])} "
                      f"{int(x[coluna_chave][20:22])}",
            axis=1).tolist()
        logger.info(f'Extraindo folhas do LRS {ref.strftime("%m/%Y")} '
                    f'contendo {len(textos_a_procurar)} documentos fiscais...')
        selection_file = PDFExtractor.highlight_pdf(lrs_file, textos_a_procurar)
        paths.append(selection_file)
    return paths


def get_gias_entregues(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    return ws.print_gia_entregas(get_current_audit().ie,
                                 get_current_audit().inicio_auditoria,
                                 get_current_audit().fim_auditoria)


def get_gia_apuracao(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    df = item.get_dfs_list_for_proof_generation()
    date_column = df.keys()[[i for i, x in enumerate(df.dtypes.tolist()) if x == 'datetime64[ns]'][-1]]
    df.sort_values(by=date_column)

    referencias = [Timestamp(t).date() for t in df[date_column].unique()]
    return ws.print_gia_apuracao(get_current_audit().ie, referencias)


def get_gia_outros_debitos(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    df = item.get_dfs_list_for_proof_generation()
    date_column = df.keys()[[i for i, x in enumerate(df.dtypes.tolist()) if x == 'datetime64[ns]'][-1]]
    referencias = list(set([GeneralFunctions.last_day_of_month(Timestamp(t).date()) for t in df[date_column]]))
    return ws.print_gia_outros_debitos(get_current_audit().ie, sorted(referencias))


def get_gia_outros_creditos(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    df = item.get_dfs_list_for_proof_generation()
    date_column = df.keys()[[i for i, x in enumerate(df.dtypes.tolist()) if x == 'datetime64[ns]'][-1]]
    referencias = list(set([GeneralFunctions.last_day_of_month(Timestamp(t).date()) for t in df[date_column]]))
    return ws.print_gia_outros_creditos(get_current_audit().ie, sorted(referencias))


def get_efd_obrigatoriedade(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    file_path = Path('tmp') / 'obrigatoriedade.pdf'
    if not file_path.is_file():
        ws.print_efd_obrigatoriedade(get_current_audit().cnpj_only_digits(), file_path)
    return [file_path]


def get_efd_entregas(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    file_path = Path('tmp') / 'entregas_efd.pdf'
    if not file_path.is_file():
        ws.print_efd_entregas(get_current_audit().cnpj_only_digits(),
                              get_current_audit().inicio_auditoria,
                              get_current_audit().fim_auditoria,
                              file_path)
    return [file_path]


def get_item_credit_sheet(item: AiimItem, ws: SeleniumWebScraper, pva: EFDPVAReversed) -> list[Path]:
    if item.infracao.inciso != 'II':
        return []
    else:
        # TODO gerar PDF com as 2 planilhas de "Glosa do Item x.xlsx"
        return []


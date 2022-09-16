import re
import shutil
import sys

from pathlib import Path

from GeneralFunctions import logger
from SQLReader import SQLWriter


class CSVProcessingMissingPrerequisite(Exception):
    def __init__(self, report: str, prereq: str):
        self.report = report
        self.missing_prerequisite = prereq
        super().__init__()

    def __str__(self):
        return f'Importação do relatório {self.report} cancelada ' \
               f'por falta de importação anterior de {self.missing_prerequisite}'


class CSVProcessingWrongHeader(Exception):
    pass


def import_report(relatorio_nome_inicio: str, files_path: Path, schema: str):
    with SQLWriter(schema) as postgres:
        # verifica se já fez importação no BD, antes de rodar tudo de novo
        relatorio = to_ascii(relatorio_nome_inicio)
        if getattr(sys.modules[__name__], f'__{relatorio}_already_did_import')(postgres):
            logger.info(f'Relatório {relatorio_nome_inicio} já havia sido importado, resolvido!')
            return
        # verifica se falta algum pre-requisito
        missing_prereq = getattr(sys.modules[__name__],
                                 f'__{relatorio}_missing_prerequisite')(postgres)
        if missing_prereq:
            raise CSVProcessingMissingPrerequisite(relatorio, missing_prereq)

        # executa query que cria tabelas definitivas e temporárias
        logger.info(f'Iniciando importação do relatório {relatorio_nome_inicio}...')
        postgres.run_ddl(f'{relatorio}_create.sql')
        for file in files_path.glob(f'{relatorio_nome_inicio}*.csv'):
            __verify_header(relatorio, file)
            try:
                logger.info(f'Carregando dados do arquivo {file.name} no banco de dados central...')
                before_cleaning_file = __clean_file(file)
                # chama uma das funções desse módulo que termina com _import_file
                getattr(sys.modules[__name__], f'__{relatorio}_import_file')(file, postgres)
                before_cleaning_file.unlink()
            except Exception as e:
                if before_cleaning_file.is_file():
                    file.unlink(missing_ok=True)
                    before_cleaning_file.rename(file)
                raise e
        logger.info(f'Jogando dados processados do relatório {relatorio_nome_inicio} no banco de dados central...')
        postgres.run_ddl(f'{relatorio}_insert.sql')


def to_ascii(report_name: str) -> str:
    de_para = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ã': 'a', 'õ': 'o', 'ç': 'c', '-': '_', ' ': '_'}
    return ''.join([de_para.get(character, character) for character in report_name])


def __verify_header(report_name: str, file: Path):
    # verifica se o cabeçalho do arquivo está igual ao conteúdo de arquivo template, caso exista
    header_template = Path('resources') / 'sql' / f'{report_name}_header_template.txt'
    if header_template.is_file():
        with header_template.open(mode='r', encoding='UTF-8') as f:
            texto_template = f.readline().strip()
        with file.open(mode='r', encoding='UTF-8') as f:
            texto_file = f.readline().strip()
        if texto_template != texto_file:
            template_cols = texto_template.split(',')
            file_cols = texto_file.split(',')
            if len(template_cols) != len(file_cols):
                raise CSVProcessingWrongHeader(f'Esperava que relatório {report_name} tivesse {template_cols} colunas,'
                                               f' mas veio com {file_cols}!')
            colunas_faltando = set(template_cols) - set(file_cols)
            colunas_sobrando = set(file_cols) - set(template_cols)
            msg = f'Relatório {report_name} veio com colunas diferentes do esperado. '
            if colunas_faltando:
                msg += f'Colunas faltando ({colunas_faltando}).'
            if colunas_sobrando:
                msg += f'Colunas novas ({colunas_sobrando}).'
            raise CSVProcessingWrongHeader(msg)


# retorna arquivo anterior à limpeza, pra apagar depois que der certo
def __clean_file(file: Path) -> Path:
    # faz limpeza do arquivo, tirando caracteres que confundem o COPY do postgres
    backup = Path(str(file) + '.old')
    backup.unlink(missing_ok=True)
    shutil.copyfile(file, backup)
    with file.open(mode='r', encoding='UTF-8') as f:
        texto = f.read()
    texto = re.sub(r'(?P<a>[^,"\r\n])"(?P<b>[^,"\r\n])', r'\g<a>\g<b>', texto)
    texto = re.sub(r'(?P<a>[^,"\r\n])"",', r'\g<a>",', texto)
    texto = re.sub(r'",""(?P<a>[^,"\r\n])', r'","\g<a>', texto)
    with file.open(mode='w', encoding='UTF-8') as f:
        f.write(texto)
    return backup


def __CFOP_por_IE_import_file(file: Path, postgres: SQLWriter):
    postgres.import_dump_file(file, 'gia_cfop_temp')


def __CFOP_por_IE_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('gia_cfop') \
           and postgres.has_return_set('select 1 from gia_cfop;')


def __CFOP_por_IE_missing_prerequisite(postgres: SQLWriter):
    return None


def __Consulta_Ingresso_Suframa_import_file(file: Path, postgres: SQLWriter):
    postgres.import_dump_file(file, 'suframa_temp')


def __Consulta_Ingresso_Suframa_missing_prerequisite(postgres: SQLWriter):
    return None


def __Consulta_Ingresso_Suframa_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('suframa')


def __Consulta_DI_por_CNPJ_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('importacao_adicao') \
           and postgres.has_return_set('select 1 from importacao_adicao')


def __Consulta_DI_por_CNPJ_missing_prerequisite(postgres: SQLWriter):
    return None


def __Consulta_DI_por_CNPJ_import_file(file: Path, postgres: SQLWriter):
    # existem 2 estruturas de dados diferentes no arquivo
    with file.open(mode='r', encoding='UTF-8') as f:
        texto = f.read()
    quebra_relatorios = list(re.finditer(r'"Núm. DI","Núm. Adição.*', texto))
    texto1 = texto[:quebra_relatorios[1].regs[0][0]]
    tmp1 = Path('tmp') / 'di.csv'
    if len(texto1.splitlines()) > 1:
        try:
            with tmp1.open(mode='w', encoding='UTF-8') as f:
                f.write(texto1)
            postgres.import_dump_file(tmp1, 'di_temp')
        finally:
            tmp1.unlink()
    texto2 = texto[quebra_relatorios[1].regs[0][0]:]
    tmp2 = Path('tmp') / 'di_adicao.csv'
    if len(texto2.splitlines()) > 1:
        try:
            with tmp2.open(mode='w', encoding='UTF-8') as f:
                f.write(texto2)
            postgres.import_dump_file(tmp2, 'di_adicao_temp')
        finally:
            tmp2.unlink()


def __Manifestacoes_NFe_Destinatario_OSF_import_file(file: Path, postgres: SQLWriter):
    postgres.import_dump_file(file, 'nfe_mdf_temp')


def __Manifestacoes_NFe_Destinatario_OSF_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('nfe') and postgres.does_table_exist('nfe_mdf') \
           and postgres.has_return_set('select 1 from nfe_mdf where autor = cnpj_auditoria();')


def __Manifestacoes_NFe_Destinatario_OSF_missing_prerequisite(postgres: SQLWriter):
    return 'NF-e' if not postgres.does_table_exist('nfe') else None


def __Manifestacoes_NFe_Emitente_OSF_import_file(file: Path, postgres: SQLWriter):
    postgres.import_dump_file(file, 'nfe_mdf_temp')


def __Manifestacoes_NFe_Emitente_OSF_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('nfe') and postgres.does_table_exist('nfe_mdf') \
           and postgres.has_return_set('select 1 from nfe_mdf where autor != cnpj_auditoria() '
                                       'AND cnpj_auditoria() = substring(chave, 7, 14);')


def __Manifestacoes_NFe_Emitente_OSF_missing_prerequisite(postgres: SQLWriter):
    return 'NF-e' if not postgres.does_table_exist('nfe') else None


def __NFe_Destinatario_OSF_import_file(file: Path, postgres: SQLWriter):
    # existem duas estruturas diferentes no mesmo arquivo,
    # gero 2 arquivos pra carregar
    with file.open(mode='r', encoding='UTF-8') as f:
        texto = f.read()
    quebra_relatorios = list(re.finditer(r'"Chave Acesso.*', texto))[1]
    texto1 = texto[:quebra_relatorios.regs[0][0]]
    tmp1 = Path('tmp') / 'dest_sp.csv'
    try:
        with tmp1.open(mode='w', encoding='UTF-8') as f:
            f.write(texto1)
        postgres.import_dump_file(tmp1, 'nfe_dest_temp')
    finally:
        tmp1.unlink()
    texto2 = texto[quebra_relatorios.regs[0][1] + 1:]
    tmp2 = Path('tmp') / 'dest_outras_ufs.csv'
    try:
        with tmp2.open(mode='w', encoding='UTF-8') as f:
            f.write(texto2)
        postgres.import_dump_file(tmp2, 'nfe_dest_outras_ufs_temp')
    finally:
        tmp2.unlink()


def __NFe_Destinatario_OSF_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('nfe') \
           and postgres.has_return_set('select 1 from nfe where cnpj_emit != cnpj_auditoria() and '
                                       "tipo_doc_fiscal != 'Entrada'")


def __NFe_Destinatario_OSF_missing_prerequisite(postgres: SQLWriter):
    return None


def __NFe_Destinatario_Itens_OSF_import_file(file: Path, postgres: SQLWriter):
    # após ter aparecido o listbox para situação nesse relatório, sumiu o 2o cabeçalho...
    # pode ser que volte posteriormente...

    #with file.open(mode='r', encoding='UTF-8') as f:
    #    texto = f.read()
    #quebra_relatorios = list(re.finditer(r'"Chave Acesso.*', texto))[1]
    #texto = texto[:quebra_relatorios.regs[0][0]] + texto[quebra_relatorios.regs[0][1] + 1:]
    #with file.open(mode='w', encoding='UTF-8') as f:
    #    f.write(texto)
    postgres.import_dump_file(file, 'nfe_item_dest_temp')


def __NFe_Destinatario_Itens_OSF_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('nfe') and postgres.does_table_exist('nfe_item') \
           and postgres.has_return_set('select 1 from nfe_item where cnpj_emit != cnpj_auditoria()')


def __NFe_Destinatario_Itens_OSF_missing_prerequisite(postgres: SQLWriter):
    return 'NF-e' if not postgres.does_table_exist('nfe') else None


def __NFe_Emitente_OSF_import_file(file: Path, postgres: SQLWriter):
    postgres.import_dump_file(file, 'nfe_emit_temp')


def __NFe_Emitente_OSF_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('nfe') \
           and postgres.has_return_set('select 1 from nfe where cnpj_emit = cnpj_auditoria() and '
                                       "tipo_doc_fiscal != 'Entrada'")


def __NFe_Emitente_OSF_missing_prerequisite(postgres: SQLWriter):
    return None


def __NFe_Emitente_Itens_OSF_import_file(file: Path, postgres: SQLWriter):
    postgres.import_dump_file(file, 'nfe_item_emit_temp')


def __NFe_Emitente_Itens_OSF_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('nfe') and postgres.does_table_exist('nfe_item') \
           and postgres.has_return_set('select 1 from nfe_item where cnpj_emit = cnpj_auditoria()')


def __NFe_Emitente_Itens_OSF_missing_prerequisite(postgres: SQLWriter):
    return 'NF-e' if not postgres.does_table_exist('nfe') else None


def __NFe_Docs_Referenciados_Destinatario_import_file(file: Path, postgres: SQLWriter):
    with file.open(mode='r', encoding='UTF-8') as f:
        texto = f.read()
    quebras_relatorios = list(re.finditer(r'"Documento.*', texto))
    if len(quebras_relatorios) > 1:
        texto = texto[:quebras_relatorios[1].regs[0][0]] + texto[quebras_relatorios[1].regs[0][1] + 1:]
        with file.open(mode='w', encoding='UTF-8') as f:
            f.write(texto)
    postgres.import_dump_file(file, 'nfe_refs_temp')


def __NFe_Docs_Referenciados_Destinatario_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('nfe') and postgres.does_table_exist('nfe_x_nfe') \
           and postgres.has_return_set('select 1 from nfe, nfe_x_nfe '
                                       'where nfe.chave in (nfe_x_nfe.chave_referente, nfe_x_nfe.chave_referenciada) '
                                       'AND nfe.cnpj_emit != cnpj_auditoria()')


def __NFe_Docs_Referenciados_Destinatario_missing_prerequisite(postgres: SQLWriter):
    return 'NF-e' if not postgres.does_table_exist('nfe') else None


def __NFe_Docs_Referenciados_Emitente_import_file(file: Path, postgres: SQLWriter):
    with file.open(mode='r', encoding='UTF-8') as f:
        texto = f.read()
    quebra_relatorios = list(re.finditer(r'"Documento.*', texto))
    if len(quebra_relatorios) > 1:
        quebra_relatorios = quebra_relatorios[1]
        texto = texto[:quebra_relatorios.regs[0][0]] + texto[quebra_relatorios.regs[0][1] + 1:]
        with file.open(mode='w', encoding='UTF-8') as f:
            f.write(texto)
    postgres.import_dump_file(file, 'nfe_refs_temp')


def __NFe_Docs_Referenciados_Emitente_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('nfe') and postgres.does_table_exist('nfe_x_nfe') \
           and postgres.has_return_set('select 1 from nfe, nfe_x_nfe '
                                       'where nfe.chave in (nfe_x_nfe.chave_referente, nfe_x_nfe.chave_referenciada) '
                                       'AND nfe.cnpj_emit = cnpj_auditoria()')


def __NFe_Docs_Referenciados_Emitente_missing_prerequisite(postgres: SQLWriter):
    return 'NF-e' if not postgres.does_table_exist('nfe') else None


def __NF_es_exportacao_com_evento_de_averbacao_por_CNPJ_x_periodo_already_did_import(postgres: SQLWriter):
    # TODO ver como importar esse relatorio
    raise CSVProcessingWrongHeader('Ainda não sei como importar esse relatório!')


def __NF_es_exportacao_com_evento_de_averbacao_por_CNPJ_x_periodo_missing_prerequisite(postgres: SQLWriter):
    return None


def __NF_es_exportacao_com_evento_de_averbacao_por_CNPJ_x_periodo_import_file(file: Path, postgres: SQLWriter):
    return None


def __REDF_consulta_Cupons_Fiscais_ECF_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('redf') and \
        postgres.has_return_set('select 1 from redf')


def __REDF_consulta_Cupons_Fiscais_ECF_missing_prerequisite(postgres: SQLWriter):
    return None


def __REDF_consulta_Cupons_Fiscais_ECF_import_file(file: Path, postgres: SQLWriter):
    postgres.import_dump_file(file, 'redf_temp')


def __SN_e_COMMERCE_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('intermediario_transacao') \
           and postgres.has_return_set('select 1 from intermediario_transacao')


def __SN_e_COMMERCE_missing_prerequisite(postgres: SQLWriter):
    return None


def __SN_e_COMMERCE_import_file(file: Path, postgres: SQLWriter):
    # existem 3 estruturas de dados diferentes no arquivo
    with file.open(mode='r', encoding='UTF-8') as f:
        texto = f.read()
    quebra_relatorios = list(re.finditer(r'"Id Arquivo.*', texto))
    texto1 = texto[:quebra_relatorios[1].regs[0][0]]
    tmp1 = Path('tmp') / 'if.csv'
    if len(texto1.splitlines()) > 1:
        try:
            with tmp1.open(mode='w', encoding='UTF-8') as f:
                f.write(texto1)
            postgres.import_dump_file(tmp1, 'intermediario_if_temp')
        finally:
            tmp1.unlink()
    texto2 = texto[quebra_relatorios[1].regs[0][0]:quebra_relatorios[2].regs[0][0]]
    tmp2 = Path('tmp') / 'ic.csv'
    if len(texto2.splitlines()) > 1:
        try:
            with tmp2.open(mode='w', encoding='UTF-8') as f:
                f.write(texto2)
            postgres.import_dump_file(tmp2, 'intermediario_ic_temp')
        finally:
            tmp2.unlink()

    texto3 = texto[quebra_relatorios[2].regs[0][0]:]
    tmp3 = Path('tmp') / 'intermediario_arquivos.csv'
    try:
        with tmp3.open(mode='w', encoding='UTF-8') as f:
            f.write(texto3)
        postgres.import_dump_file(tmp3, 'intermediario_arquivo_temp')
    finally:
        tmp3.unlink()


def __CTe_CNPJ_Emitente_Tomador_Remetente_Destinatario_OSF_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('cte') \
           and postgres.has_return_set('select 1 from cte')


def __CTe_CNPJ_Emitente_Tomador_Remetente_Destinatario_OSF_missing_prerequisite(postgres: SQLWriter):
    return None


def __CTe_CNPJ_Emitente_Tomador_Remetente_Destinatario_OSF_import_file(file: Path, postgres: SQLWriter):
    postgres.import_dump_file(file, 'cte_temp')


def __CTe_CNPJ_Info_Adicionais_OSF_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('cte_nfe') \
           and postgres.has_return_set('select 1 from cte_nfe')


def __CTe_CNPJ_Info_Adicionais_OSF_missing_prerequisite(postgres: SQLWriter):
    if not postgres.does_table_exist('nfe'):
        return 'NF-e'
    if not postgres.does_table_exist('nfe'):
        return 'CT-e'
    return None


def __CTe_CNPJ_Info_Adicionais_OSF_import_file(file: Path, postgres: SQLWriter):
    postgres.import_dump_file(file, 'cte_adicional_temp')


def __SAT___CuponsEmitidosPorContribuinteCNPJ_OSF_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('sat_cupom') \
           and postgres.has_return_set('select 1 from sat_cupom')


def __SAT___CuponsEmitidosPorContribuinteCNPJ_OSF_missing_prerequisite(postgres: SQLWriter):
    return None


def __SAT___CuponsEmitidosPorContribuinteCNPJ_OSF_import_file(file: Path, postgres: SQLWriter):
    postgres.import_dump_file(file, 'sat_cupom_temp')


def __SAT___ItensDeCuponsCNPJ_OSF_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('sat_cupom_item') \
           and postgres.has_return_set('select 1 from sat_cupom_item')


def __SAT___ItensDeCuponsCNPJ_OSF_missing_prerequisite(postgres: SQLWriter):
    if not postgres.does_table_exist('sat_cupom'):
        return 'SAT Cupom'
    return None


def __SAT___ItensDeCuponsCNPJ_OSF_import_file(file: Path, postgres: SQLWriter):
    postgres.import_dump_file(file, 'sat_cupom_item_temp')


def __Consulta_BO___Cartoes_Sumarizados_e_detalhado___2010_a_2019_import_file(file: Path, postgres: SQLWriter):
    postgres.import_dump_file(file, 'transacao_cartao_temp')


def __Consulta_BO___Cartoes_Sumarizados_e_detalhado___2010_a_2019_already_did_import(postgres: SQLWriter):
    return postgres.does_table_exist('transacao_cartao') \
           and postgres.has_return_set('select 1 from transacao_cartao where cnpj = cnpj_auditoria()')


def __Consulta_BO___Cartoes_Sumarizados_e_detalhado___2010_a_2019_missing_prerequisite(postgres: SQLWriter):
    return None

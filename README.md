# PoltergeistFDT
Ferramenta automatizadora de verificações em auditorias fiscais na Sefaz-SP

Ferramenta tem as seguintes principais funcionalidades:
  - download de relatórios do Infoview e escriturações EFD extraídas do portal Arquivos Digitais;
  - importação em um banco de dados PostgreSQL (não incluso) dos arquivos baixados (relatórios e EFDs);
  - oferece verificações pré-cadastradas, cruzando informações existentes no banco de dados;
  - permite a criação de novas verificações;
  - criação de planilhas com o resultado das verificações, para aprofundamento da análise;
  - envio de notificação DEC com a planilha relacionada à verificação, como anexo;
  - criação de AIIM no sistema AIIM2003, com:
    - inclusão e exclusão de itens automaticamente;
    - geração de DDFs a partir dos dados da planilha relacionada à verificação;
    - atualização automática de dados de SELIC e UFESP;
    - geração do arquivo Quadro 3;
    - atualização do quadro de operações dos últimos 12 meses (art. 85-A do RICMS/00);
  - geração de relatório circunstanciado, contendo templates para cada item do AIIM;
  - geração de provas para um item de AIIM, a partir de relatórios Infoview (ex: DANFE, DACTE), consultas públicas (ex: SAT-CF-e) e programa EFD PVA ICMS da RFB (ex: trechos de livros fiscais de entradas e saídas, livro de apuração do ICMS)
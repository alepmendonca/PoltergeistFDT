CREATE TABLE IF NOT EXISTS efd_ajuste_icms (
	codigo varchar,
	descricao varchar,
	dt_ini date NOT NULL,
	dt_fim date NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS efd_ajuste_icms_codigo ON efd_ajuste_icms USING btree (codigo, dt_ini);

INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP000202','Diferença de imposto apurada por contribuinte.','2015-01-01',NULL),
	 ('SP000206','Entrada de mercadoria com imposto a pagar ou utilização de serviços com imposto a pagar.','2015-01-01',NULL),
	 ('SP000207','Entrada de mercadoria, oriunda de outro Estado, destinada a uso, consumo ou integração no ativo imobilizado ou utilização de serviço iniciado fora do território paulista - Diferencial de alíquota.','2015-01-01',NULL),
	 ('SP000208','Complemento do imposto por contribuinte substituído - Complemento de Substituição Tributária.','2015-01-01',NULL),
	 ('SP000209','Ressarcimento de substituição tributária por Pedido de Liquidação de Débito Fiscal.','2015-01-01',NULL),
	 ('SP000210','Ressarcimento de substituição tributária por Nota Fiscal de Ressarcimento.','2015-01-01',NULL),
	 ('SP000211','Ressarcimento de substituição tributária por Pedido de Ressarcimento.','2015-01-01',NULL),
	 ('SP000212','Estabelecimento que receber de outro Estado, mercadoria abrangida pela substituição tributária, quando a responsabilidade pelo pagamento do imposto seja a ele atribuída - valor do imposto incidente sobre sua própria operação.','2015-01-01',NULL),
	 ('SP000213','Sujeito passivo por substituição que realizar operação fora do estabelecimento, sem destinatário certo, com mercadoria abrangida pela Substituição Tributária - ICMS próprio em remessa para venda fora do estabelecimento.','2015-01-01',NULL),
	 ('SP000214','Entrada de resíduo de materiais em estabelecimento industrial.','2015-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP000215','Entrada de metais não-ferrosos  em estabelecimentos industriais. (Validade até a referência 08/2000).','2015-01-01',NULL),
	 ('SP000216','Remessa para venda fora do estabelecimento.','2015-01-01','2019-09-30'),
	 ('SP000217','Diferença paga por empresa seguradora relativamente a peças adquiridas para emprego em conserto de veículo acidentado.','2015-01-01',NULL),
	 ('SP000218','Transferência de saldo credor  para estabelecimento centralizador.','2015-01-01',NULL),
	 ('SP000219','Recebimento de saldo devedor - estabelecimento centralizador.','2015-01-01',NULL),
	 ('SP000220','Devolução de crédito acumulado mediante autorização eletrônica.','2015-01-01',NULL),
	 ('SP000221','Apropriação de crédito acumulado mediante autorização eletrônica.','2015-01-01',NULL),
	 ('SP000222','Transferência de crédito acumulado – Protocolo ICM 12/84.','2015-01-01',NULL),
	 ('SP000223','Devolução de crédito recebido de Produtor Rural ou Cooperativa de Produtores Rurais mediante autorização eletrônica.','2015-01-01',NULL),
	 ('SP000224','Imposto devido na prestação de serviço de comunicação a usuário localizado neste Estado, na hipótese de inexistência de estabelecimento do prestador no território paulista.','2015-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP000225','Transferência de Crédito Simples do ICMS, decorrente da entrada de bem destinado ao ativo permanente.','2015-01-01',NULL),
	 ('SP000226','Transferência de crédito do ICMS para cooperativa centralizadora de vendas.','2015-01-01',NULL),
	 ('SP000299','OUTRAS HIPÓTESES - PREENCHIDA PELO CONTRIBUINTE.','2015-01-01',NULL),
	 ('SP010301','Estorno de imposto creditado quando a mercadoria entrada no estabelecimento vier a perecer, deteriorar-se ou for objeto de roubo, furto ou extravio.','2015-01-01',NULL),
	 ('SP010302','Estorno de imposto creditado quando o serviço tomado ou a mercadoria adquirida for objeto de saída ou prestação de serviço não tributada.','2015-01-01',NULL),
	 ('SP010303','Estorno de imposto creditado quando a mercadoria adquirida for integrada ou consumida em processo de industrialização ou produção rural, quando a saída não for tributada ou estiver isenta do imposto.','2015-01-01',NULL),
	 ('SP010304','Estorno de imposto creditado quando a mercadoria adquirida for integrada ou consumida em processo de industrialização ou produção rural, quando a saída tiver base de cálculo reduzida.','2015-01-01',NULL),
	 ('SP010305','Estorno do valor do crédito deduzido na guia de recolhimento nas saídas de café cru, em coco ou em grão.','2015-01-01',NULL),
	 ('SP010306','Estorno do valor do crédito deduzido na guia de recolhimento nas saídas de gado em pé bovino e suíno.','2015-01-01',NULL),
	 ('SP010307','Ativo Permanente - transferência de crédito  remanescente.','2015-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP010308','Saídas de produtos agrícolas - ICMS recolhido pelo armazém geral, por guia de recolhimentos especiais.','2015-01-01',NULL),
	 ('SP010309','Uso ou consumo da mercadoria ou serviço destinado à comercialização ou Industrialização.','2015-01-01',NULL),
	 ('SP010310','Estorno do imposto creditado na ocorrência 007.08.','2015-01-01',NULL),
	 ('SP010399','OUTRAS HIPÓTESES - PREENCHIDA PELO CONTRIBUINTE.','2015-01-01',NULL),
	 ('SP020708','Importação de bem ou mercadoria com direito a crédito de ICMS.','2015-01-01',NULL),
	 ('SP020709','Crédito outorgado sobre o imposto devido na prestação de serviço de transporte, exceto aéreo.','2015-01-01',NULL),
	 ('SP020710','Imposto pago indevidamente, em virtude de erro de fato ocorrido na escrituração dos livros fiscais ou no preparo da guia de recolhimento.','2015-01-01',NULL),
	 ('SP020711','Imposto correspondente à diferença verificada entre a importância recolhida e a apurada decorrente do desenquadramento do regime de estimativa.','2015-01-01',NULL),
	 ('SP020712','Imposto pago indevidamente, objeto de pedido administrativo de restituição quando a decisão não tiver sido proferida no prazo de 45 dias, contados da data do respectivo pedido.','2015-01-01',NULL),
	 ('SP020713','Imposto pago indevidamente em razão de destaque a maior em documento fiscal, até o limite estabelecido pela Secretaria da Fazenda.','2015-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP020714','Valor do imposto destacado na nota fiscal relativa à aquisição de bem, objeto de arrendamento mercantil  pela empresa arrendadora, por ocasião da entrada no estabelecimento.','2015-01-01',NULL),
	 ('SP020716','Imposto recolhido por guia de recolhimentos  especiais nas saídas de álcool carburante e  de produtos resultantes da industrialização do petróleo.','2015-01-01',NULL),
	 ('SP020717','Imposto recolhido pelo destinatário por guia de recolhimentos especiais, relativo a serviço tomado ou mercadoria entrada no estabelecimento.','2015-01-01',NULL),
	 ('SP020718','Entrada de mercadoria, oriunda de outro Estado, destinada a uso, consumo ou integração no ativo imobilizado, ou utilização de serviço iniciado noutro Estado - Diferencial de alíquota.','2015-01-01',NULL),
	 ('SP020719','Ressarcimento de substituição tributária, por estabelecimento de contribuinte substituído.','2015-01-01',NULL),
	 ('SP020720','Compensação de imposto pago na operação própria do substituto, por estabelecimento de contribuinte substituído, relativamente a operações com veículos.','2015-01-01',NULL),
	 ('SP020721','Crédito relativo à operação própria do Substituto  em operação interestadual promovida pelo  contribuinte substituído.','2015-01-01',NULL),
	 ('SP020722','Imposto recolhido mediante guia de recolhimentos especiais nas operações com café cru.','2015-01-01',NULL),
	 ('SP020723','Imposto recolhido por guia de recolhimentos especiais pelo abate de gado.','2015-01-01',NULL),
	 ('SP020724','Crédito outorgado – abate de bovinos e suínos.','2015-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP020725','Imposto recolhido mediante guia de recolhimentos especiais nas operações com gado em pé.','2015-01-01',NULL),
	 ('SP020726','Imposto relativo à entrada de gado em pé originário de outro Estado.','2015-01-01',NULL),
	 ('SP020727','Recolhimento em outros Estados nas operações de vendas fora do estabelecimento.','2015-01-01',NULL),
	 ('SP020728','Na desistência de ressarcimento por Nota Fiscal de Ressarcimento, Pedido de Ressarcimento ou Pedido de Liquidação de Débito Fiscal - Reincorporação do imposto.','2015-01-01',NULL),
	 ('SP020729','Transferência de saldo devedor para estabelecimento centralizador.','2015-01-01',NULL),
	 ('SP020730','Recebimento de saldo credor – estabelecimento centralizador.','2015-01-01',NULL),
	 ('SP020731','Crédito outorgado – abate de aves.','2015-01-01',NULL),
	 ('SP020732','Crédito outorgado – outros produtos alimentícios.','2015-01-01',NULL),
	 ('SP020733','Crédito outorgado – informática periférico.','2015-01-01',NULL),
	 ('SP020734','Crédito outorgado – telefone celular.','2015-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP020735','Crédito outorgado – unidade de processamento.','2015-01-01',NULL),
	 ('SP020736','Crédito outorgado –  informática outros.','2015-01-01',NULL),
	 ('SP020737','Crédito outorgado - leite esterilizado UHT (longa vida).','2015-01-01',NULL),
	 ('SP020738','Crédito outorgado – adesivo hidroxilado - garrafas PET.','2015-01-01',NULL),
	 ('SP020739','Valor destinado ao Programa de Ação Cultural - PAC.','2015-01-01',NULL),
	 ('SP020740','Recebimento de crédito acumulado mediante autorização eletrônica.','2015-01-01',NULL),
	 ('SP020741','Reincorporação de crédito acumulado mediante autorização eletrônica.','2015-01-01',NULL),
	 ('SP020742','Valor destinado ao Programa de Incentivo ao Esporte - PIE.','2015-01-01',NULL),
	 ('SP020743','Recebimento de Crédito Acumulado – Protocolo ICM 12/84.','2015-01-01',NULL),
	 ('SP020744','Recebimento de crédito de estabelecimento de Produtor Rural ou de estabelecimento de Cooperativas de Produtores Rurais mediante autorização eletrônica.','2015-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP020745','Incorporação de Crédito por estabelecimento de Cooperativas de Produtores Rurais mediante autorização eletrônica.','2015-01-01',NULL),
	 ('SP020746','Crédito oriundo de serviço de comunicação utilizado na prestação de serviço de mesma natureza a usuário localizado neste Estado, na hipótese de inexistência de estabelecimento do prestador no território paulista.','2015-01-01',NULL),
	 ('SP020747','Recebimento de Crédito Simples do ICMS, a que se refere o Decreto 56.133/2010.','2015-01-01',NULL),
	 ('SP020748','Recebimento de crédito do ICMS de estabelecimento fabricante de açúcar ou etanol.','2015-01-01',NULL),
	 ('SP020799','OUTRAS HIPÓTESES - PREENCHIDA PELO CONTRIBUINTE.','2015-01-01',NULL),
	 ('SP030801','Devolução de mercadoria oriunda de outro Estado, destinada a uso, consumo ou integração no ativo imobilizado, ou de utilização de serviço iniciado em outro Estado.','2015-01-01',NULL),
	 ('SP030802','Regularização de documentos fiscais em virtude de diferença no preço, em operação ou prestação, ou na quantidade de mercadoria, quando a regularização se efetuar após o período de apuração.','2015-01-01',NULL),
	 ('SP030803','Lançamento do imposto, não efetuado em época própria, em virtude de erro de cálculo ou de classificação fiscal, ou outro, quando a regularização se efetuar após o período de apuração.','2015-01-01',NULL),
	 ('SP030804','Imposto relativo à operações realizadas pelo sujeito passivo por substituição fora do estabelecimento com mercadoria abrangida pela substituição tributária - Estorno do ICMS próprio no retorno - venda fora do estabelecimento.','2015-01-01',NULL),
	 ('SP030805','Operações com café cru: imposto a ser recolhido em período posterior.','2015-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP030806','Imposto destacado em Nota Fiscal de remessa para venda fora do estabelecimento.','2015-01-01','2019-09-30'),
	 ('SP030807','Estorno de débito decorrente de cancelamento de BP-e escriturado com débito do imposto.','2018-12-01',NULL),
	 ('SP030899','OUTRAS HIPÓTESES - PREENCHIDA PELO CONTRIBUINTE.','2015-01-01',NULL),
	 ('SP041499','Deduções – RPA – ST – RES.','2015-01-01',NULL),
	 ('SP100201','Imposto retido em remessa para venda fora do estabelecimento.','2015-01-01',NULL),
	 ('SP100202','ICMS retido nas vendas efetuadas a revendedores ambulantes para revenda no sistema porta-a-porta para consumidores finais.','2015-01-01',NULL),
	 ('SP100299','OUTRAS HIPÓTESES - PREENCHIDA PELO CONTRIBUINTE.','2015-01-01',NULL),
	 ('SP110399','OUTRAS HIPÓTESES - PREENCHIDA PELO CONTRIBUINTE.','2015-01-01',NULL),
	 ('SP120701','Ressarcimento de imposto retido por nota fiscal','2015-01-01',NULL),
	 ('SP120702','Dedução de imposto retido – ressarcimento por depósito bancário.','2015-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP120703','Ressarcimento relativo a operações interestaduais com combustíveis.','2015-01-01',NULL),
	 ('SP120704','Repasse a outras unidades federadas relativo a operações interestaduais com combustíveis.','2015-01-01',NULL),
	 ('SP120799','OUTRAS HIPÓTESES - PREENCHIDA PELO CONTRIBUINTE.','2015-01-01',NULL),
	 ('SP130801','Estorno de imposto retido no retorno – venda fora do estabelecimento.','2015-01-01',NULL),
	 ('SP130899','OUTRAS HIPÓTESES - PREENCHIDA PELO CONTRIBUINTE.','2015-01-01',NULL),
	 ('SP141499','Deduções – RPA – ST – RES.','2015-01-01',NULL),
	 ('SP009999','Outros débitos para ajuste de apuração ICMS.','2009-01-01','2015-03-31'),
	 ('SP109999','Outros débitos para ajuste de apuração ICMS ST.','2009-01-01','2015-03-31'),
	 ('SP019999','Estorno de créditos para ajuste de apuração ICMS.','2009-01-01','2015-03-31'),
	 ('SP119999','Estorno de créditos para ajuste de apuração ICMS ST.','2009-01-01','2015-03-31') ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP029999','Outros créditos para ajuste de apuração ICMS.','2009-01-01','2015-03-31'),
	 ('SP129999','Outros créditos para ajuste de apuração ICMS ST.','2009-01-01','2015-03-31'),
	 ('SP039999','Estorno de débitos para ajuste de apuração ICMS.','2009-01-01','2015-03-31'),
	 ('SP139999','Estorno de débitos para ajuste de apuração ICMS ST.','2009-01-01','2015-03-31'),
	 ('SP049999','Deduções do imposto apurado na apuração ICMS.','2009-01-01','2015-03-31'),
	 ('SP149999','Deduções do imposto apurado na apuração ICMS ST.','2009-01-01','2015-03-31'),
	 ('SP059999','Débito especial de ICMS .','2009-01-01',NULL),
	 ('SP159999','Débito especial de ICMS ST.','2009-01-01',NULL),
	 ('SP099999','Controle do ICMS extra-apuração .','2013-01-01','2015-03-31'),
	 ('SP000287','Parcela do diferencial de alíquota decorrente de operações e prestações que destinem bens e serviços a não contribuinte do ICMS localizado em outra unidade federada, líquida das devoluções (EC 87/2015)','2016-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP209999','Outros débitos para ajuste de apuração ICMS Difal/FCP','2016-01-01','2016-12-31'),
	 ('SP219999','Estorno de créditos para ajuste de apuração ICMS Difal/FCP','2016-01-01','2016-12-31'),
	 ('SP229999','Outros créditos para ajuste de apuração ICMS Difal/FCP','2016-01-01','2016-12-31'),
	 ('SP239999','Estorno de débitos para ajuste de apuração ICMS Difal/FCP','2016-01-01','2016-12-31'),
	 ('SP249999','Deduções do imposto apurado na apuração ICMS Difal/FCP','2016-01-01','2016-12-31'),
	 ('SP259999','Débito especial de ICMS Difal/FCP','2016-01-01','2016-12-31'),
	 ('SP020770','Transferência do ICMS próprio devido ao FECOEP para apuração específica.','2016-02-01',NULL),
	 ('SP120770','Transferência do ICMS ST devido ao FECOEP para apuração específica.','2016-02-01',NULL),
	 ('SP019319','Transferência do saldo apurado correspondente ao ressarcimento do imposto retido por substituição tributária, do registro de apuração de operações próprias do ICMS para o registro de controle de créditos fiscais do ICMS (1200).','2017-01-01',NULL),
	 ('SP029719','Transferência do total de créditos de ressarcimento do imposto retido por substituição tributária a ser utilizado no período (campo 06 do Registro 1200) para o registro de apuração de operações próprias do ICMS.','2017-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP099719','Código de controle do saldo de créditos fiscais decorrentes do ressarcimento do imposto retido por substituição tributária, de uso exclusivo no Registro 1200.','2017-01-01',NULL),
	 ('SP209999','Outros débitos para ajuste de apuração ICMS Difal.','2017-01-01',NULL),
	 ('SP219999','Estorno de créditos para ajuste de apuração ICMS Difal.','2017-01-01',NULL),
	 ('SP229999','Outros créditos para ajuste de apuração ICMS Difal.','2017-01-01',NULL),
	 ('SP239999','Estorno de débitos para ajuste de apuração ICMS Difal.','2017-01-01',NULL),
	 ('SP249999','Deduções do imposto apurado na apuração ICMS Difal.','2017-01-01',NULL),
	 ('SP259999','Débito especial de ICMS Difal.','2017-01-01',NULL),
	 ('SP309999','Outros débitos para ajuste de apuração ICMS FCP.','2017-01-01',NULL),
	 ('SP319999','Estorno de créditos para ajuste de apuração ICMS FCP.','2017-01-01',NULL),
	 ('SP329999','Outros créditos para ajuste de apuração ICMS FCP.','2017-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('SP339999','Estorno de débitos para ajuste de apuração ICMS FCP.','2017-01-01',NULL),
	 ('SP349999','Deduções do imposto apurado na apuração ICMS FCP.','2017-01-01',NULL),
	 ('SP359999','Débito especial de ICMS FCP.','2017-01-01',NULL),
	 ('SP020749','Ressarcimento de Substituição Tributária - Compensação Escritural mediante autorização eletrônica.','2018-05-01',NULL),
	 ('SP020750','Crédito relativo ao estoque de mercadoria excluída do regime da substituição tributária.','2020-02-01',NULL),
	 ('SP000227','Débito relativo ao estoque de mercadoria incluída no regime da substituição tributária.','2020-02-01',NULL),
	 ('UF009999','Outros débitos para ajuste de apuração ICMS para','2009-01-01',NULL),
	 ('UF109999','Outros débitos para ajuste de apuração ICMS ST para','2009-01-01',NULL),
	 ('UF019999','Estorno de créditos para ajuste de apuração ICMS para','2009-01-01',NULL),
	 ('UF119999','Estorno de créditos para ajuste de apuração ICMS ST para','2009-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('UF029999','Outros créditos para ajuste de apuração ICMS para','2009-01-01',NULL),
	 ('UF129999','Outros créditos para ajuste de apuração ICMS ST para','2009-01-01',NULL),
	 ('UF039999','Estorno de débitos para ajuste de apuração ICMS para','2009-01-01',NULL),
	 ('UF139999','Estorno de débitos para ajuste de apuração ICMS ST para','2009-01-01',NULL),
	 ('UF049999','Deduções do imposto apurado na apuração ICMS para','2009-01-01',NULL),
	 ('UF149999','Deduções do imposto apurado na apuração ICMS ST para','2009-01-01',NULL),
	 ('UF059999','Débito especial de ICMS para','2009-01-01',NULL),
	 ('UF159999','Débito especial de ICMS ST para','2009-01-01',NULL),
	 ('UF099999','Controle do ICMS extra-apuração para','2013-01-01',NULL),
	 ('UF209999','Outros débitos para ajuste de apuração ICMS Difal/FCP para a UF','2016-01-01','2016-12-31') ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('UF219999','Estorno de créditos para ajuste de apuração ICMS Difal/FCP para a UF','2016-01-01','2016-12-31'),
	 ('UF229999','Outros créditos para ajuste de apuração ICMS Difal/FCP para a UF','2016-01-01','2016-12-31'),
	 ('UF239999','Estorno de débitos para ajuste de apuração ICMS Difal/FCP para a UF','2016-01-01','2016-12-31'),
	 ('UF249999','Deduções do imposto apurado na apuração ICMS Difal/FCP para a UF','2016-01-01','2016-12-31'),
	 ('UF259999','Débito especial de ICMS Difal/FCP para a UF','2016-01-01','2016-12-31'),
	 ('UF209999','Outros débitos para ajuste de apuração ICMS Difal para a UF','2017-01-01',NULL),
	 ('UF219999','Estorno de créditos para ajuste de apuração ICMS Difal para a UF','2017-01-01',NULL),
	 ('UF229999','Outros créditos para ajuste de apuração ICMS Difal para a UF','2017-01-01',NULL),
	 ('UF239999','Estorno de débitos para ajuste de apuração ICMS Difal para a UF','2017-01-01',NULL),
	 ('UF249999','Deduções do imposto apurado na apuração ICMS Difal para a UF','2017-01-01',NULL) ON CONFLICT DO NOTHING;
INSERT INTO efd_ajuste_icms (codigo,descricao,dt_ini,dt_fim) VALUES
	 ('UF259999','Débito especial de ICMS Difal para a UF','2017-01-01',NULL),
	 ('UF309999','Outros débitos para ajuste de apuração ICMS FCP para a UF XX','2017-01-01',NULL),
	 ('UF319999','Estorno de créditos para ajuste de apuração ICMS FCP para a UF XX','2017-01-01',NULL),
	 ('UF329999','Outros créditos para ajuste de apuração ICMS FCP para a UF XX','2017-01-01',NULL),
	 ('UF339999','Estorno de débitos para ajuste de apuração ICMS FCP para a UF XX','2017-01-01',NULL),
	 ('UF349999','Deduções do imposto apurado na apuração ICMS FCP para a UF XX','2017-01-01',NULL),
	 ('UF359999','Débito especial de ICMS FCP para a UF XX','2017-01-01',NULL) ON CONFLICT DO NOTHING;

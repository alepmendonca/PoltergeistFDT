package br.gov.sp.efdpvainspector;
import java.lang.reflect.Method;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.List;

import br.gov.serpro.bdembutido.dao.generico.IDAOGenerico;
import br.gov.serpro.comum.relatorio.IRelatorio;
import br.gov.serpro.sped.fiscalpva.dominio.entidades.EscrituracaoFiscal;
import br.gov.serpro.sped.fiscalpva.dominio.entidades.assinatura.DadosAssinatura;
import br.gov.serpro.sped.fiscalpva.nucleo.controle.fabrica.FabricaControle;
import br.gov.serpro.sped.fiscalpva.nucleo.util.VersaoCorrenteAplicativo;
import br.gov.serpro.sped.fiscalpva.nucleo.util.assinatura.ControleRecuperarDadosAssinaturaV1;
import br.gov.serpro.sped.fiscalpva.nucleo.util.assinatura.IControleRecuperarDadosAssinatura;
import br.gov.serpro.sped.fiscalpva.persistencia.PersistenciaEscrituracaoFiscal;
import br.gov.serpro.sped.fiscalpva.persistencia.PersistenciaFiscalPVA;
import br.gov.serpro.sped.fiscalpva.relatorios.ato002.EnumRelatoriosTitulosExibidoAto002;
import br.gov.serpro.sped.fiscalpva.relatorios.ato002.comun.entidades.ParametroPesquisa;
import br.gov.serpro.sped.fiscalpva.relatorios.controle.IControleGerarRelatorio;
import net.sf.jasperreports.engine.JasperExportManager;
import net.sf.jasperreports.engine.JasperPrint;

/**
 * Todos os métodos de impressão usando o EFD PVA devem primeiro inicializar o BD pela função citada no main,
 * assim como deve-se garantir o encerramento do BD ao final.
 * O main traz a receita de bolo que deve ser executada.
 * 
 * @author Alexandre Mendonca
 *
 */
public class EFDPrinter {

	public static void main(String[] args) throws Exception {
		EFDComprehension.inicializacaoSimplesBD();
		String[] datas = {"01/04/2018"};
		try {
			for (String data: datas) {
				imprimeEntradas("CNPJ", "IE", 
						data, 
						"C:/LRE" + data.substring(6) + data.substring(3, 5) + ".pdf");
			}
		} finally {
			EFDComprehension.encerramentoBD();
		}
	}

	/**
	 * Partes copiadas de:
	 *  fiscalpva.jar!br.gov.serpro.sped.fiscalpva.abrirescrituracao.controle.ControleAbrirEscrituracao
	 * 							abrirEscrituracao
	 *  fiscalpva.jar!br.gov.serpro.sped.fiscalpva.fronteira.ppgd.acoes.AcaoEscrituracao
	 *  						abrirEscrituracao
	 *  
	 *  As ações da tree view estão num xml que varia conforme ato cotepe, mas maioria deve funcionar conforme
	 *  		fiscalpva.jar!br.gov.serpro.sped.fiscalpva.fronteira.relatorios.acoes.AcoesArvoreRelatorios
	 */
	private static IControleGerarRelatorio generatePrinterObject(String cnpj, String ie, String referenciaString) throws Exception {
		Date referencia = new SimpleDateFormat("dd/MM/yyyy").parse(referenciaString);
        EscrituracaoFiscal escrituracao = new EscrituracaoFiscal();
        escrituracao.setCpfCnpj(cnpj);
        escrituracao.setIe(ie);
        escrituracao.setDataInicial(referencia);
        Calendar dataFinal = Calendar.getInstance();
        dataFinal.setTime(referencia);
        dataFinal.set(Calendar.DATE, dataFinal.getActualMaximum(Calendar.DATE));
        escrituracao.setDataFinal(dataFinal.getTime());

        IDAOGenerico<EscrituracaoFiscal> dao = PersistenciaFiscalPVA.getSingleton().getFabricaDaoMaster().getDaoEscrituracaoFiscal();
        // Seleciona todos os objetos, mas sem verificar a integridade, pra não dar pau à toa
        for (EscrituracaoFiscal escrituracaoBanco: dao.selecionarTodosOsObjetos(false)) {
        	if (escrituracao.getCpfCnpj().contentEquals(escrituracaoBanco.getCpfCnpj()) 
        			&& escrituracao.getIe().contentEquals(escrituracaoBanco.getIe())
        			&& escrituracao.getDataInicial().equals(escrituracaoBanco.getDataInicial()) 
        			&& escrituracao.getDataFinal().equals(escrituracaoBanco.getDataFinal())) {
        		escrituracao = escrituracaoBanco;
        		break;
        	}
        }
        FabricaControle.getSingleton().setarVersao(escrituracao);

        IControleGerarRelatorio controleGerarRelatorio = (IControleGerarRelatorio)FabricaControle.getSingleton().getServico(IControleGerarRelatorio.class);
		PersistenciaEscrituracaoFiscal persistenciaEscrituracao = PersistenciaFiscalPVA.getSingleton().abrirPersistenciaEscrituracaoFiscal(escrituracao);
		controleGerarRelatorio.setVersaoCorrenteAplicativo(VersaoCorrenteAplicativo.getVersao());

		IControleRecuperarDadosAssinatura controleRecuperarDadosAssinatura = FabricaControle.getSingleton().getServico(IControleRecuperarDadosAssinatura.class);
        if (! controleRecuperarDadosAssinatura.getClass().equals(ControleRecuperarDadosAssinaturaV1.class)) {
        	throw new Exception("EFD mudou versão do ControleRecuperarDadosAssinatura! Talvez precise adaptar importador...");
        }
        // usando um método privado para não abrir janela (fim da picada)
        Method metodo_privado = controleRecuperarDadosAssinatura.getClass().getDeclaredMethod("recuperarInformacoesAssinatura", String.class, boolean.class, boolean.class);
        metodo_privado.setAccessible(true);
        DadosAssinatura dadosAssinatura = (DadosAssinatura) metodo_privado.invoke(controleRecuperarDadosAssinatura, escrituracao.getLocalizacaoArquivo(), false, true);

		controleGerarRelatorio.inicializarControleGerarRelatorio(escrituracao, dadosAssinatura, persistenciaEscrituracao);
		controleGerarRelatorio.carregarDadosCabecalhoRodape(escrituracao);
		return controleGerarRelatorio;
	}

	public static void imprimeApuracao(String cnpj, String ie, String referenciaString, String arquivoSaida) throws Exception {
		IControleGerarRelatorio controleGerarRelatorio = generatePrinterObject(cnpj, ie, referenciaString);
		ParametroPesquisa parametroPesquisa = controleGerarRelatorio.getParametroPesquisa_E100(0);
		parametroPesquisa.setExibirDetalheDocumentos(true);
		EnumRelatoriosTitulosExibidoAto002.ICMS_OP.setExibirDetalheDocumentos(true);
		IRelatorio relatorio = controleGerarRelatorio.gerarRelatorioRegistroFiscaisApuracaoICMSOP(parametroPesquisa, null);
		JasperPrint jasperPrint = relatorio.getTodasAsPaginas();
		JasperExportManager.exportReportToPdfFile(jasperPrint, arquivoSaida);
	}

	public static void imprimeEntradas(String cnpj, String ie, String referenciaString, String arquivoSaida) throws Exception {
		IControleGerarRelatorio controleGerarRelatorio = generatePrinterObject(cnpj, ie, referenciaString);
		ParametroPesquisa parametroPesquisa = controleGerarRelatorio.getParametroPesquisa_E100(0);
		parametroPesquisa.setExibirDetalheDocumentos(true);
		IRelatorio relatorio = controleGerarRelatorio.gerarRelatorioDocumentosFiscaisEntrada(parametroPesquisa, null);
		JasperPrint jasperPrint = relatorio.getTodasAsPaginas();
		JasperExportManager.exportReportToPdfFile(jasperPrint, arquivoSaida);
	}

	public static void imprimeSaidas(String cnpj, String ie, String referenciaString, String arquivoSaida) throws Exception {
		IControleGerarRelatorio controleGerarRelatorio = generatePrinterObject(cnpj, ie, referenciaString);
		ParametroPesquisa parametroPesquisa = controleGerarRelatorio.getParametroPesquisa_E100(0);
		parametroPesquisa.setExibirDetalheDocumentos(true);
		IRelatorio relatorio = controleGerarRelatorio.gerarRelatorioDocumentosFiscaisSaida(parametroPesquisa, null);
		JasperPrint jasperPrint = relatorio.getTodasAsPaginas();
		JasperExportManager.exportReportToPdfFile(jasperPrint, arquivoSaida);
	}

	public static void imprimeInventario(String cnpj, String ie, String referenciaString, String arquivoSaida) throws Exception {
		IControleGerarRelatorio controleGerarRelatorio = generatePrinterObject(cnpj, ie, referenciaString);
		List<ParametroPesquisa> parametrosPesquisa = controleGerarRelatorio.getDataInvetarioH005();
		for (ParametroPesquisa parametroPesquisa: parametrosPesquisa) {
			parametroPesquisa.setExibirDetalheDocumentos(true);
			IRelatorio relatorio = controleGerarRelatorio.gerarRelatorioIventario(parametroPesquisa, null);
			JasperPrint jasperPrint = relatorio.getTodasAsPaginas();
			JasperExportManager.exportReportToPdfFile(jasperPrint, arquivoSaida);
		}
	}
}

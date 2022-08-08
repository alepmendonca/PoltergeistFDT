package br.gov.sp.efdpvainspector;

import br.gov.serpro.sped.fiscalpva.dominio.configuracao.ConfiguracoesAplicacao;
import br.gov.serpro.sped.fiscalpva.nucleo.controle.fabrica.FabricaControle;
import br.gov.serpro.sped.fiscalpva.nucleo.init.InicializacaoSistemaSPEDFiscalPVA;
import br.gov.serpro.sped.fiscalpva.persistencia.PersistenciaFiscalPVA;

public class EFDComprehension {

	/**
	 * Simplificação do comando InicializacaoSistemaSPEDFiscalPVA.getSingleton().iniciarSPEDFiscalPVA();
	 */
	public static void inicializacaoSimplesBD() throws Exception {
		System.out.println("Iniciando banco de dados do EFD PVA ICMS IPI...");
		PersistenciaFiscalPVA.getSingleton().iniciarSGBD(ConfiguracoesAplicacao.getSingleton().getPortaBanco());
		FabricaControle.getSingleton().configurar();
		System.out.println("Banco de dados da EFD inicializado.");
	}

	public static void encerramentoBD() throws Exception {
		System.out.println("Encerrando banco de dados do EFD PVA ICMS IPI...");
		InicializacaoSistemaSPEDFiscalPVA.getSingleton().encerrarSPEDFiscalPVA();
		System.out.println("Banco de dados da EFD encerrado.");
	}
	
}

package br.gov.serpro.comum.util;

import br.gov.serpro.comum.excecao.ExcecaoIO;
import br.gov.serpro.sped.fiscal.nucleo.leitorescrituracao.LeitorArquivoHierarquicoInputStreamFiscal;
import br.gov.serpro.sped.fiscalpva.dominio.configuracao.ConfiguracoesAplicacao;
import br.gov.serpro.sped.fiscalpva.persistencia.PersistenciaFiscalPVA;

import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.net.MalformedURLException;
import java.net.URL;

public class UtilResources {

	/**
	 * Esse override via classpath serve para evitar os problemas quando o classloading  
	 * não é feito via JAR
	 */
	public static InputStream getInputStream(String caminhoResource) throws FileNotFoundException {
		InputStream isResource = null;
		if (caminhoResource.contentEquals("/descritor/comum/queries/queries.xml")) {
			isResource = ConfiguracoesAplicacao.class.getResourceAsStream(caminhoResource);
		} else if (caminhoResource.contentEquals("/configuracoes/atualizadorTabela.conf.xml")) {
			isResource = LeitorArquivoHierarquicoInputStreamFiscal.class.getResourceAsStream(caminhoResource.toLowerCase());
		} else if (caminhoResource.contentEquals("/configuracoes/bd-namedpipe.properties")) {
			isResource = PersistenciaFiscalPVA.class.getResourceAsStream(caminhoResource);
		} else if (caminhoResource.contains("/relatorios/bdembutido/queries/queries.relatorio.atocotepe.xml")) {
			isResource = PersistenciaFiscalPVA.class.getResourceAsStream(caminhoResource);
		}

		if (isResource == null && !caminhoResource.startsWith("/")) {
			isResource = Class.class.getResourceAsStream("/" + caminhoResource);
		}
		try {
			if (isResource == null) {
				isResource = (new URL(caminhoResource)).openStream();         }
		} catch (MalformedURLException var3) {
			isResource = new FileInputStream(caminhoResource);
		} catch (IOException var4) {
			throw new ExcecaoIO(var4);
		}

		return (InputStream)isResource;
	}
}
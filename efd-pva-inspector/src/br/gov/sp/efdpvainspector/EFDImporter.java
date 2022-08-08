package br.gov.sp.efdpvainspector;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.reflect.Method;
import java.text.SimpleDateFormat;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import br.gov.serpro.comum.hash.UtilitarioHash;
import br.gov.serpro.comum.progresso.IMostrarProgresso;
import br.gov.serpro.sped.fiscal.nucleo.leitorescrituracao.LeitorArquivoHierarquicoInputStreamFiscal;
import br.gov.serpro.sped.fiscalpva.dominio.constantes.EnumEstadoEscrituracao;
import br.gov.serpro.sped.fiscalpva.dominio.constantes.EnumXmlDescritorEscrituracao;
import br.gov.serpro.sped.fiscalpva.dominio.entidades.EscrituracaoFiscal;
import br.gov.serpro.sped.fiscalpva.dominio.entidades.assinatura.DadosAssinatura;
import br.gov.serpro.sped.fiscalpva.nucleo.controle.escrituracaofiscal.ControleEscrituracaoFiscal;
import br.gov.serpro.sped.fiscalpva.nucleo.controle.fabrica.FabricaControle;
import br.gov.serpro.sped.fiscalpva.nucleo.util.arquivo.ArquivoDeEscrituracao;
import br.gov.serpro.sped.fiscalpva.nucleo.util.assinatura.ControleRecuperarDadosAssinaturaV1;
import br.gov.serpro.sped.fiscalpva.nucleo.util.assinatura.IControleRecuperarDadosAssinatura;
import br.gov.serpro.sped.fiscalpva.persistencia.PersistenciaEscrituracaoFiscal;
import br.gov.serpro.sped.fiscalpva.persistencia.PersistenciaFiscalPVA;
import br.gov.serpro.sped.fiscalpva.validador.fachada.FachadaValidadorSPEDFiscal;
import br.gov.serpro.sped.fiscalpva.validador.resultado.ResultadoValidacao;
import br.gov.serpro.vepxml.nucleo.excecao.ExcecaoLeitorEscrituracao;
import br.gov.serpro.vepxml.nucleo.leitorescrituracao.ILeitorEscrituracao;
import br.gov.serpro.vepxml.nucleo.leitorescrituracao.coordenador.configuracao.ConfiguracoesCoordenador;
import br.gov.serpro.vepxml.nucleo.sessao.SessaoVep;
import br.gov.serpro.vepxml.persistencia.configuracao.ConfiguracaoConexaoPersistencia;
import br.gov.serpro.vepxml.validador.coordenador.CoordenadorImportacaoDefault;
import br.gov.serpro.vepxml.validador.fachada.FachadaVepModuloValidador;
import br.gov.serpro.vepxml.validador.resultado.Inconsistencia;

public class EFDImporter {

	/**
	 * Importa o arquivo EFD passado como 1º parametro, excluindo a escrituração igual já importada
	 * 2º parâmetro é o arquivo onde vai guardar a relação entre BD, hash e auditoria
	 * @param arquivo_efd arquivo_efds_json
	 * @throws Exception
	 */
	public static void importaEFD(String nomeArquivo, String efdsJsonFilePath) throws Exception {
		EscrituracaoFiscal escrituracao = importaEscrituracao(nomeArquivo);
		escrituracao.setLocalizacaoArquivo(nomeArquivo);
		updateEfdsFile(efdsJsonFilePath, escrituracao);
	}

	public static void main(String[] args) throws Exception {
		EFDComprehension.inicializacaoSimplesBD();
		try {
			for (String nomeArquivo: args) {
				if (nomeArquivo.contentEquals(args[0])) continue;
				System.out.println("Importando escrituração " + nomeArquivo);
				EscrituracaoFiscal escrituracao = importaEscrituracao(nomeArquivo);
				escrituracao.setLocalizacaoArquivo(nomeArquivo);
				updateEfdsFile(args[0], escrituracao);
			}
		} finally {
			EFDComprehension.encerramentoBD();
		}
	}
	
	private static void updateEfdsFile(String json_path, EscrituracaoFiscal escrituracao) throws IOException {
		File arquivo = new File(json_path);
		FileInputStream json = null;
		ObjectMapper objMap = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
		JsonNode rootNode = null;
		ArrayNode listNode = null;
		try {
			json = new FileInputStream(arquivo);
			rootNode = objMap.readTree(json);
		} catch (FileNotFoundException e) {
			arquivo.getParentFile().mkdirs();
			arquivo.createNewFile();
			json = new FileInputStream(arquivo);
		} catch (JsonMappingException e) {
			// relaxa que vai corrigir em seguida
		}
		if (arquivo.length() == 0) {
			rootNode = objMap.createObjectNode();
			((ObjectNode) rootNode).put("efds", objMap.createArrayNode());
		}
		listNode = (ArrayNode) rootNode.path("efds");
		Iterator<JsonNode> iter = listNode.iterator();
		SimpleDateFormat df = new SimpleDateFormat("MM/yyyy");
		while (iter.hasNext()) {
			JsonNode efd = iter.next();
			String referencia = efd.path("referencia").asText();
			if (referencia.contentEquals(df.format(escrituracao.getDataInicial()))) {
				iter.remove();
				break;
			}
		}
		ObjectNode newNode = objMap.createObjectNode();
		newNode.put("referencia", df.format(escrituracao.getDataInicial()));
		newNode.put("hash", escrituracao.getHashArquivo());
		newNode.put("cnpj", escrituracao.getCpfCnpj());
		newNode.put("ie", escrituracao.getIe());
		newNode.put("nome", escrituracao.getNomeContribuinte());
		newNode.put("bd", escrituracao.getNomeBD());
		newNode.put("arquivo", escrituracao.getLocalizacaoArquivo());
		listNode.add(newNode);

		OutputStream outputStream = new FileOutputStream(arquivo);
		objMap.writeValue(outputStream, rootNode);
	}

	/**
	 * 
	 * Copia adaptada do método
	 * 		public void importarEscrituracao(String caminhoArquivoEscrituracao, 
	 * 				IInteracaoImportacaoEscrituracao interacao, IMostrarProgresso mostrarProgresso, 
	 * 				boolean recuperarRecibo, int maximoErros, int maximoAdvertencias) 
	 * 				throws ExcecaoArquivo, ExcecaoEscrituracaoInvalida, ExcecaoBanco, ExcecaoSistema
	 *  da classe br.gov.serpro.sped.fiscalpva.nucleo.controle.importacao.escrituracao.ControleImportacaoExportacaoEscrituracaoV2
	 * 	que está no pacote fiscalpva-nucleo.jar
	 * 
	 * Para funcionar:
	 * 		- tem que rodar como basedir o diretório do EFD PVA ICMS
	 * 		- tem que colocar o fiscalpva.jar no classpath  
	 */
	static EscrituracaoFiscal importaEscrituracao(String nomeArquivo) throws Exception {
		boolean escrituracaoAssinada = false;
		String hashArquivo = null;
		long offsetInicioAssinatura = 0L;
		ILeitorEscrituracao leitor = null;
		ResultadoValidacao resultado = null;

		String caminhoArquivoEscrituracao = nomeArquivo.replace('\\', '/');
		ArquivoDeEscrituracao arquivoDeEscrituracao = new ArquivoDeEscrituracao(caminhoArquivoEscrituracao);
        EscrituracaoFiscal escrituracao = ControleEscrituracaoFiscal.getSingleton().getEscrituracaoFiscal(arquivoDeEscrituracao);
        FabricaControle.getSingleton().setarVersao(escrituracao);
        try {
            IControleRecuperarDadosAssinatura controleRecuperarDadosAssinatura = FabricaControle.getSingleton().getServico(IControleRecuperarDadosAssinatura.class);
            if (! controleRecuperarDadosAssinatura.getClass().equals(ControleRecuperarDadosAssinaturaV1.class)) {
            	throw new Exception("EFD mudou versão do ControleRecuperarDadosAssinatura! Talvez precise adaptar importador...");
            }
            // usando um método privado para não abrir janela (fim da picada)
            Method metodo_privado = controleRecuperarDadosAssinatura.getClass().getDeclaredMethod("recuperarInformacoesAssinatura", String.class, boolean.class, boolean.class);
            metodo_privado.setAccessible(true);
            DadosAssinatura dadosAssinatura = (DadosAssinatura) metodo_privado.invoke(controleRecuperarDadosAssinatura, caminhoArquivoEscrituracao, false, true);
            SessaoVep sessao = new SessaoVep();
            sessao.putObjetoNaSessao(DadosAssinatura.class, dadosAssinatura);
            if (dadosAssinatura != null) {
                escrituracaoAssinada = true;
                hashArquivo = dadosAssinatura.getHashArquivo();
                offsetInicioAssinatura = dadosAssinatura.getInicioNoArquivo();
            } else {
                if (!arquivoDeEscrituracao.finalDeUltimaLinhaOk()) {
                    throw new Exception("Estrutura da linha invalida. A escrituracao nao pode ser importada.\nA ultima linha da escrituracao nao termina com caracter indicador de final de linha.");
                }
            }
            arquivoDeEscrituracao = new ArquivoDeEscrituracao(caminhoArquivoEscrituracao);
            escrituracao = ControleEscrituracaoFiscal.getSingleton().getEscrituracaoFiscal(arquivoDeEscrituracao);
            if (dadosAssinatura != null) {
                escrituracao.setTamanhoSemAssinatura(offsetInicioAssinatura);
                int idXmlDescritorEscrituracao = dadosAssinatura.getDadosDaEscrituracaoNaAssinatura().getIdXmlDescritorEscrituracao();
                escrituracao.setEnumXmlDescritorEscrituracao(EnumXmlDescritorEscrituracao.get((Integer)idXmlDescritorEscrituracao));
                int versaoDoDescritorEscrituracaoUtilizadoValidacao = dadosAssinatura.getDadosDaEscrituracaoNaAssinatura().getVersaoXmlDescritorEscrituracao();
                escrituracao.setVersaoDoDescritorEscrituracaoUtilizadoValidacao(Integer.valueOf(versaoDoDescritorEscrituracaoUtilizadoValidacao));
            } else {
                escrituracao.setTamanhoSemAssinatura(Long.valueOf(arquivoDeEscrituracao.length()));
            }
            EscrituracaoFiscal escrituracaoFiscalBanco = ControleEscrituracaoFiscal.getSingleton().obterEscrituracaoComMesmoIdentificador(escrituracao);
            if (escrituracaoFiscalBanco != null) {
            	ControleEscrituracaoFiscal.getSingleton().apagarEscrituracaoBanco(escrituracaoFiscalBanco);
            }
            FileInputStream is = new FileInputStream(escrituracao.getLocalizacaoArquivo());
            leitor = new LeitorArquivoHierarquicoInputStreamFiscal(is, escrituracao.getDescritor(), offsetInicioAssinatura);
            resultado = importarEscrituracao(leitor, escrituracao, 0, 0, sessao);
        } catch (ExcecaoLeitorEscrituracao e) {
            resultado = new ResultadoValidacao();
            resultado.setImportado(false);
        }
        if (!resultado.isImportado()) {
        	throw new Exception("Arquivo não foi importado!");
        }
        escrituracao.setNomeBD(resultado.getNomePersistencia());
        if (!escrituracaoAssinada) {
            hashArquivo = leitor.getHashSha1();
        }
        escrituracao.setHashArquivo(hashArquivo);
        escrituracao.setEstado(EnumEstadoEscrituracao.IMPORTADA);
        if (escrituracaoAssinada) {
            escrituracao.setEstado(EnumEstadoEscrituracao.SOMENTE_VISUALIZACAO);
        }
        escrituracao.setHashArquivoDisco(UtilitarioHash.geraHashMD5((File)new File(escrituracao.getLocalizacaoArquivo())));
        escrituracao.setHash(Long.valueOf(0L));
        PersistenciaFiscalPVA.getSingleton().getFabricaDaoMaster().getDaoEscrituracaoFiscal().inserirObjeto(escrituracao);
        System.out.println("Sucesso " + escrituracao.getNomeBD() + " " + escrituracao.getHashArquivo());
        return escrituracao;
	}

	static ResultadoValidacao importarEscrituracao(ILeitorEscrituracao leitorEscrituracao, EscrituracaoFiscal bdIndividual, int maximoErros, int maximoAdvertencias, SessaoVep sessao) throws Exception {
		ResultadoValidacao resultado = new ResultadoValidacao();
		resultado.setImportado(false);
		 
		InputStream configCoordenador = FachadaValidadorSPEDFiscal.class.getResourceAsStream("/vep/coordenador/coordenador-importacao.xml");
		CoordenadorImportacaoDefault coordenador = null;
		coordenador = new CoordenadorImportacaoDefault(new ConfiguracoesCoordenador(configCoordenador));
		
		String nomePersistencia = PersistenciaFiscalPVA.getSingleton().criarPersistenciaEscrituracao(bdIndividual);
		resultado.setNomePersistencia(nomePersistencia);
		bdIndividual.setNomeBD(nomePersistencia);
		ConfiguracaoConexaoPersistencia configsCamadaPersistencia = PersistenciaEscrituracaoFiscal.getConfiguracaoCamadaPersistenciaVep(bdIndividual);
		Map<String, List<Inconsistencia>> mapErros = FachadaVepModuloValidador.importarArquivo(leitorEscrituracao, bdIndividual.getDescritor(), 
				coordenador, nomePersistencia, maximoErros, maximoAdvertencias, configsCamadaPersistencia, new MostrarProgressoMock(), sessao);
		if (mapErros.size() == 0) {
			resultado.setImportado(true);
		} else {
			resultado.setMapErros(mapErros);
		}

		return resultado;
	}
}

final class MostrarProgressoMock implements IMostrarProgresso {

	@Override
	public void exibir() {
	}

	@Override
	public void fechar() {
	}

	@Override
	public boolean foiCanceladoOuFechado() {
		return false;
	}

	@Override
	public void setProgresso(Object arg0, int arg1) {
	}

	@Override
	public void setTitulo(String arg0) {
	}

	@Override
	public void setTituloAcao(String arg0) {
	}
}
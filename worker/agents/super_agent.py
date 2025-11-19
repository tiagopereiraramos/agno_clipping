"""
Super Agent - Agente Orquestrador Principal.

Coordena a execução dos outros agentes e gerencia o fluxo completo de clipping.
"""

from typing import Dict, Any, List
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class SuperAgent(BaseAgent):
    """Agente orquestrador que coordena todos os outros agentes."""
    
    def __init__(self, configuracao: Dict[str, Any], agentes: Dict[str, BaseAgent]):
        """
        Inicializa o Super Agent.
        
        Args:
            configuracao: Configurações do agente
            agentes: Dicionário com os outros agentes disponíveis
        """
        super().__init__("SuperAgent", configuracao)
        self.agentes = agentes
    
    def executar(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa o fluxo completo de clipping.
        
        Args:
            contexto: Contexto com instrução e parâmetros do job
            
        Returns:
            Resultado completo do processamento
        """
        self.registrar_log("inicio", f"Iniciando processamento do job {contexto.get('job_id')}")
        
        resultado = {
            "job_id": contexto.get("job_id"),
            "status": "em_processamento",
            "etapas": [],
            "resultados": {}
        }
        
        try:
            # Etapa 1: Browser Agent - Navegação e extração
            if "browser" in self.agentes:
                self.registrar_log("etapa", "Executando Browser Agent")
                browser_result = self.agentes["browser"].executar(contexto)
                resultado["etapas"].append("browser")
                resultado["resultados"]["browser"] = browser_result
                
                # Atualizar contexto com resultado do browser
                contexto["conteudo_extraido"] = browser_result.get("conteudo")
                contexto["url"] = browser_result.get("url")
            
            # Etapa 2: File Agent - Processamento de arquivos
            if "file" in self.agentes and contexto.get("conteudo_extraido"):
                self.registrar_log("etapa", "Executando File Agent")
                file_result = self.agentes["file"].executar(contexto)
                resultado["etapas"].append("file")
                resultado["resultados"]["file"] = file_result
                contexto["artefatos"] = file_result.get("formats", {})
                if contexto.get("conteudo_extraido"):
                    contexto["resumo_conteudo"] = contexto["conteudo_extraido"][:600]
            
            # Etapa 3: Notification Agent - Enviar notificações
            if "notification" in self.agentes:
                self.registrar_log("etapa", "Executando Notification Agent")
                notification_result = self.agentes["notification"].executar(contexto)
                resultado["etapas"].append("notification")
                resultado["resultados"]["notification"] = notification_result
            
            resultado["status"] = "concluido"
            self.registrar_log("sucesso", f"Job {contexto.get('job_id')} processado com sucesso")
            
        except Exception as e:
            resultado["status"] = "erro"
            resultado["erro"] = str(e)
            self.registrar_log("erro", f"Erro ao processar job: {e}")
            raise
        
        return resultado


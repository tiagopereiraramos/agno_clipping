"""
Classe base para todos os agentes Agno.

Define a interface comum que todos os agentes devem implementar.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Classe base abstrata para agentes Agno."""
    
    def __init__(self, nome: str, configuracao: Dict[str, Any]):
        """
        Inicializa o agente base.
        
        Args:
            nome: Nome do agente
            configuracao: Configurações do agente
        """
        self.nome = nome
        self.config = configuracao
        self.logger = logging.getLogger(f"{__name__}.{nome}")
    
    @abstractmethod
    def executar(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa a lógica principal do agente.
        
        Args:
            contexto: Contexto de execução com dados do job
            
        Returns:
            Resultado da execução do agente
        """
        pass
    
    def validar_contexto(self, contexto: Dict[str, Any]) -> bool:
        """
        Valida o contexto de execução.
        
        Args:
            contexto: Contexto a ser validado
            
        Returns:
            True se válido, False caso contrário
        """
        return True
    
    def registrar_log(self, evento: str, mensagem: str, metadata: Optional[Dict] = None) -> None:
        """
        Registra um log de execução.
        
        Args:
            evento: Tipo do evento
            mensagem: Mensagem do log
            metadata: Metadados adicionais
        """
        self.logger.info(f"[{evento}] {mensagem}", extra={"metadata": metadata or {}})


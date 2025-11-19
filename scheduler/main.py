"""
Módulo principal do Scheduler Agno - Agendador de Jobs Cron.

Este módulo inicia o scheduler que agenda jobs de clipping
periodicamente usando APScheduler e envia mensagens para RabbitMQ.
"""

import logging
import os
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic_settings import BaseSettings
import pika

# Configurar logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConfiguracoesScheduler(BaseSettings):
    """Configurações do Scheduler."""
    
    rabbitmq_url: str
    database_url: str
    log_level: str = "INFO"
    debug: bool = False
    timezone: str = "America/Sao_Paulo"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class SchedulerAgno:
    """Scheduler que agenda jobs de clipping."""
    
    def __init__(self, configuracoes: ConfiguracoesScheduler):
        """
        Inicializa o scheduler.
        
        Args:
            configuracoes: Configurações do scheduler
        """
        self.config = configuracoes
        self.scheduler = BlockingScheduler(timezone=self.config.timezone)
        self.conexao_rabbitmq: pika.BlockingConnection = None
        self.canal_rabbitmq: pika.channel.Channel = None
        
    def conectar_rabbitmq(self) -> None:
        """Estabelece conexão com RabbitMQ."""
        try:
            parametros = pika.URLParameters(self.config.rabbitmq_url)
            self.conexao_rabbitmq = pika.BlockingConnection(parametros)
            self.canal_rabbitmq = self.conexao_rabbitmq.channel()
            self.canal_rabbitmq.queue_declare(queue="clippings.jobs", durable=True)
            logger.info("Conectado ao RabbitMQ com sucesso")
        except Exception as e:
            logger.error(f"Erro ao conectar ao RabbitMQ: {e}")
            raise
    
    def enviar_job(self, instrucao: str, parametros: dict = None) -> None:
        """
        Envia um job para a fila RabbitMQ.
        
        Args:
            instrucao: Instrução do job
            parametros: Parâmetros adicionais do job
        """
        try:
            import json
            mensagem = {
                "instruction": instrucao,
                "parameters": parametros or {},
                "created_at": datetime.now().isoformat()
            }
            
            self.canal_rabbitmq.basic_publish(
                exchange="",
                routing_key="clippings.jobs",
                body=json.dumps(mensagem),
                properties=pika.BasicProperties(delivery_mode=2)  # Persistente
            )
            
            logger.info(f"Job enviado para fila: {instrucao[:50]}...")
            
        except Exception as e:
            logger.error(f"Erro ao enviar job: {e}")
            raise
    
    def agendar_jobs(self) -> None:
        """Agenda jobs periódicos."""
        # Exemplo: Job diário às 8h
        self.scheduler.add_job(
            func=lambda: self.enviar_job(
                "Coletar clippings diários das fontes configuradas",
                {"tipo": "diario", "horario": "08:00"}
            ),
            trigger=CronTrigger(hour=8, minute=0),
            id="clipping_diario",
            name="Clipping Diário",
            replace_existing=True
        )
        
        logger.info("Jobs agendados com sucesso")
    
    def iniciar(self) -> None:
        """Inicia o scheduler."""
        try:
            self.conectar_rabbitmq()
            self.agendar_jobs()
            
            logger.info("Scheduler iniciado")
            self.scheduler.start()
            
        except KeyboardInterrupt:
            logger.info("Interrompendo scheduler...")
            self.parar()
        except Exception as e:
            logger.error(f"Erro fatal no scheduler: {e}")
            raise
    
    def parar(self) -> None:
        """Para o scheduler e fecha conexões."""
        if self.scheduler.running:
            self.scheduler.shutdown()
        if self.conexao_rabbitmq and not self.conexao_rabbitmq.is_closed:
            self.conexao_rabbitmq.close()
        logger.info("Scheduler parado")


def main() -> None:
    """Função principal de entrada do scheduler."""
    try:
        configuracoes = ConfiguracoesScheduler()
        scheduler = SchedulerAgno(configuracoes)
        scheduler.iniciar()
    except Exception as e:
        logger.error(f"Erro ao iniciar scheduler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


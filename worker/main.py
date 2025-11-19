"""
Módulo principal do Worker Agno - Processador de Jobs de Clipping.

Este módulo inicia o worker que consome mensagens da fila RabbitMQ
e processa jobs de clipping usando os agentes Agno especializados.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Optional, Dict, Any, List

import pika
from pydantic_settings import BaseSettings

from worker.agents import SuperAgent, BrowserAgent, FileAgent, NotificationAgent
from worker.utils.database import DatabaseManager
from worker.utils.llm_interpreter import LLMInterpreter

# Configurar logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConfiguracoesWorker(BaseSettings):
    """Configurações do Worker."""
    
    database_url: str
    rabbitmq_url: str
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    log_level: str = "INFO"
    debug: bool = False
    worker_concurrency: int = 3
    max_retries: int = 3
    backoff_seconds: int = 30
    
    # LLM
    openai_api_key: str
    llm_model: str = "gpt-4o"
    llm_input_cost_per_1k: float = 0.005
    llm_output_cost_per_1k: float = 0.015
    
    # Browserless / Browser-Use
    browserless_url: str = "http://browserless:3000"
    browserless_token: Optional[str] = None
    browser_use_model: str = "gpt-5-mini-2025-08-07"
    browser_use_max_steps: int = 40
    browser_use_temperature: float = 0.2
    browser_use_allowed_domains: Optional[str] = None
    
    # MinIO
    minio_endpoint: Optional[str] = None
    minio_access_key: Optional[str] = None
    minio_secret_key: Optional[str] = None
    minio_bucket: str = "clippings"
    minio_use_ssl: bool = False
    
    # Notificações (opcional)
    slack_webhook_url: Optional[str] = None
    smtp_enabled: bool = False
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_to: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignorar campos extras do .env


class WorkerAgno:
    """Worker principal que processa jobs de clipping."""
    
    def __init__(self, configuracoes: ConfiguracoesWorker):
        """
        Inicializa o worker.
        
        Args:
            configuracoes: Configurações do worker
        """
        self.config = configuracoes
        self.conexao: Optional[pika.BlockingConnection] = None
        self.canal: Optional[pika.channel.Channel] = None
        
        # Inicializar componentes
        self.db = DatabaseManager(configuracoes.database_url)
        self.llm = LLMInterpreter(
            api_key=configuracoes.openai_api_key,
            model=configuracoes.llm_model,
            input_cost_per_1k=configuracoes.llm_input_cost_per_1k,
            output_cost_per_1k=configuracoes.llm_output_cost_per_1k
        )
        
        # Inicializar agentes
        self.agentes = self._inicializar_agentes()
        self.super_agent = SuperAgent({}, self.agentes)
        
    def conectar_rabbitmq(self) -> None:
        """Estabelece conexão com RabbitMQ."""
        try:
            parametros = pika.URLParameters(self.config.rabbitmq_url)
            self.conexao = pika.BlockingConnection(parametros)
            self.canal = self.conexao.channel()
            
            # Declarar fila
            self.canal.queue_declare(queue="clippings.jobs", durable=True)
            
            logger.info("Conectado ao RabbitMQ com sucesso")
        except Exception as e:
            logger.error(f"Erro ao conectar ao RabbitMQ: {e}")
            raise
    
    def _inicializar_agentes(self) -> Dict[str, Any]:
        """
        Inicializa todos os agentes especializados.
        
        Returns:
            Dicionário com agentes inicializados
        """
        agentes = {}
        
        # Browser Agent
        allowed_domains = self.config.browser_use_allowed_domains
        if allowed_domains:
            allowed_domains = [dom.strip() for dom in allowed_domains.split(",") if dom.strip()]
        else:
            allowed_domains = ["automotivebusiness.com.br", "www.automotivebusiness.com.br"]
        
        agentes["browser"] = BrowserAgent({
            "browserless_url": self.config.browserless_url,
            "browserless_token": self.config.browserless_token,
            "timeout": 30000,
            "openai_api_key": self.config.openai_api_key,
            "browser_use_model": self.config.browser_use_model,
            "browser_use_max_steps": self.config.browser_use_max_steps,
            "browser_use_temperature": self.config.browser_use_temperature,
            "allowed_domains": allowed_domains
        })
        
        # File Agent
        agentes["file"] = FileAgent({
            "minio": {
                "endpoint": self.config.minio_endpoint or "minio:9000",
                "access_key": self.config.minio_access_key or "minioadmin",
                "secret_key": self.config.minio_secret_key or "minioadmin",
                "bucket": self.config.minio_bucket,
                "use_ssl": self.config.minio_use_ssl
            }
        })
        
        # Notification Agent
        agentes["notification"] = NotificationAgent({
            "slack_webhook_url": self.config.slack_webhook_url,
            "smtp": {
                "enabled": self.config.smtp_enabled,
                "server": self.config.smtp_server if hasattr(self.config, 'smtp_server') else None,
                "port": self.config.smtp_port if hasattr(self.config, 'smtp_port') else 587,
                "user": self.config.smtp_user if hasattr(self.config, 'smtp_user') else None,
                "password": self.config.smtp_password if hasattr(self.config, 'smtp_password') else None,
                "from_email": self.config.smtp_from if hasattr(self.config, 'smtp_from') else None,
                "to_email": self.config.smtp_to if hasattr(self.config, 'smtp_to') else None
            }
        })
        
        return agentes
    
    def processar_mensagem(self, ch, method, properties, body: bytes) -> None:
        """
        Processa uma mensagem recebida da fila.
        
        Args:
            ch: Canal do RabbitMQ
            method: Método de entrega
            properties: Propriedades da mensagem
            body: Corpo da mensagem
        """
        job_id = None
        try:
            # Parsear mensagem
            mensagem = json.loads(body.decode())
            instrucao = mensagem.get("instruction", mensagem.get("text", str(body.decode())))
            
            # Gerar ID único para o job
            job_id = mensagem.get("job_id") or f"job_{uuid.uuid4().hex[:12]}"
            
            logger.info(f"Processando job {job_id}: {instrucao[:100]}...")
            
            # Criar job no banco
            parametros = mensagem.get("parameters", {})
            if isinstance(parametros, dict):
                parametros = json.dumps(parametros)
            job_data = self.db.criar_job(job_id, instrucao, parametros)
            self.db.atualizar_job(job_id, "processing")
            
            # Interpretar instrução usando LLM
            logger.info(f"Interpretando instrução com LLM...")
            interpretacao = self.llm.interpretar_instrucao(instrucao)
            llm_usage = interpretacao.pop("llm_usage", None)
            
            # Preparar contexto para os agentes
            contexto = {
                "job_id": job_id,
                "instrucao_original": instrucao,
                "url": interpretacao.get("url") or mensagem.get("url"),
                "tipo": interpretacao.get("tipo"),
                "parametros": {**interpretacao.get("parametros", {}), **mensagem.get("parameters", {})},
                "status": "processing"
            }
            if llm_usage:
                contexto["llm_usage"] = llm_usage
                contexto["llm_usage_details"] = {"interprete": llm_usage}
                logger.info(
                    "LLM usage job=%s prompt_tokens=%s completion_tokens=%s total_cost_usd=%.6f",
                    job_id,
                    llm_usage.get("prompt_tokens"),
                    llm_usage.get("completion_tokens"),
                    llm_usage.get("total_cost_usd", 0.0)
                )
            
            if not contexto["url"]:
                raise ValueError("URL não encontrada na instrução e não fornecida nos parâmetros")
            
            logger.info(f"URL identificada: {contexto['url']}")
            
            # Executar Super Agent (orquestra todos os outros)
            resultado = self.super_agent.executar(contexto)
            
            # Salvar resultados no banco
            browser_result = resultado.get("resultados", {}).get("browser", {})
            file_result = resultado.get("resultados", {}).get("file", {})
            
            if browser_result.get("conteudo"):
                self.db.salvar_resultado(
                    job_id=job_id,
                    titulo=browser_result.get("url", "Sem título"),
                    url=contexto["url"],
                    conteudo=browser_result.get("conteudo", ""),
                    s3_uri_json=file_result.get("formats", {}).get("json", {}).get("uri"),
                    s3_uri_markdown=file_result.get("formats", {}).get("markdown", {}).get("uri")
                )
            
            # Atualizar status do job
            self.db.atualizar_job(job_id, "completed", resultado)
            
            logger.info(f"Job {job_id} processado com sucesso")
            
            # Acknowledge da mensagem
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
            
            # Atualizar job com erro
            if job_id:
                try:
                    self.db.atualizar_job(job_id, "failed", erro=str(e))
                except:
                    pass
            
            # Rejeitar mensagem e reenviar para fila (máximo de retries)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def iniciar(self) -> None:
        """Inicia o worker e começa a consumir mensagens."""
        try:
            self.conectar_rabbitmq()
            
            # Configurar QoS
            self.canal.basic_qos(prefetch_count=self.config.worker_concurrency)
            
            # Consumir mensagens
            self.canal.basic_consume(
                queue="clippings.jobs",
                on_message_callback=self.processar_mensagem
            )
            
            logger.info("Worker iniciado e aguardando mensagens...")
            self.canal.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Interrompendo worker...")
            self.parar()
        except Exception as e:
            logger.error(f"Erro fatal no worker: {e}")
            raise
    
    def parar(self) -> None:
        """Para o worker e fecha conexões."""
        if self.canal and not self.canal.is_closed:
            self.canal.stop_consuming()
        if self.conexao and not self.conexao.is_closed:
            self.conexao.close()
        logger.info("Worker parado")


def main() -> None:
    """Função principal de entrada do worker."""
    try:
        configuracoes = ConfiguracoesWorker()
        worker = WorkerAgno(configuracoes)
        worker.iniciar()
    except Exception as e:
        logger.error(f"Erro ao iniciar worker: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


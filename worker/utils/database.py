"""
Utilitários para acesso ao banco de dados PostgreSQL.
"""

from typing import Dict, Any, Optional
import os
import json
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gerenciador de conexões e operações no banco de dados."""
    
    def __init__(self, database_url: str):
        """
        Inicializa o gerenciador de banco de dados.
        
        Args:
            database_url: URL de conexão do PostgreSQL
        """
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def criar_job(self, job_id: str, instrucao: str, parametros: Optional[Any] = None) -> Dict[str, Any]:
        """
        Cria um novo job no banco de dados.
        
        Args:
            job_id: ID único do job
            instrucao: Instrução em linguagem natural
            parametros: Parâmetros adicionais (dict ou JSON string)
            
        Returns:
            Dados do job criado
        """
        with self.SessionLocal() as session:
            try:
                # Converter parametros para JSON string se necessário
                if isinstance(parametros, dict):
                    parametros_json = json.dumps(parametros)
                elif parametros is None:
                    parametros_json = "{}"
                else:
                    parametros_json = str(parametros)
                
                query = text("""
                    INSERT INTO clippings_app.clipping_jobs 
                    (job_id, status, instruction, parameters, created_at)
                    VALUES (:job_id, 'pending', :instruction, CAST(:parameters AS jsonb), NOW())
                    RETURNING id, job_id, status, created_at
                """)
                
                result = session.execute(
                    query,
                    {
                        "job_id": job_id,
                        "instruction": instrucao,
                        "parameters": parametros_json
                    }
                )
                session.commit()
                
                row = result.fetchone()
                return {
                    "id": str(row[0]),
                    "job_id": row[1],
                    "status": row[2],
                    "created_at": row[3].isoformat() if row[3] else None
                }
            except Exception as e:
                session.rollback()
                logger.error(f"Erro ao criar job: {e}")
                raise
    
    def atualizar_job(self, job_id: str, status: str, resultado: Optional[Dict] = None, erro: Optional[str] = None) -> None:
        """
        Atualiza o status e resultado de um job.
        
        Args:
            job_id: ID do job
            status: Novo status
            resultado: Resultado do processamento
            erro: Mensagem de erro se houver
        """
        with self.SessionLocal() as session:
            try:
                resultado_json = None
                if resultado:
                    if isinstance(resultado, dict):
                        resultado_json = json.dumps(resultado)
                    else:
                        resultado_json = str(resultado)
                
                query = text("""
                    UPDATE clippings_app.clipping_jobs
                    SET status = :status,
                        result_metadata = CAST(:resultado AS jsonb),
                        error_message = :erro,
                        completed_at = CASE WHEN :status IN ('completed', 'failed') THEN NOW() ELSE completed_at END,
                        started_at = CASE WHEN started_at IS NULL THEN NOW() ELSE started_at END
                    WHERE job_id = :job_id
                """)
                
                session.execute(
                    query,
                    {
                        "job_id": job_id,
                        "status": status,
                        "resultado": resultado_json,
                        "erro": erro
                    }
                )
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Erro ao atualizar job: {e}")
                raise
    
    def salvar_resultado(self, job_id: str, titulo: str, url: str, conteudo: str, 
                        s3_uri_json: Optional[str] = None, s3_uri_markdown: Optional[str] = None) -> None:
        """
        Salva o resultado de um clipping.
        
        Args:
            job_id: ID do job
            titulo: Título do conteúdo
            url: URL de origem
            conteudo: Conteúdo extraído
            s3_uri_json: URI do arquivo JSON no S3
            s3_uri_markdown: URI do arquivo Markdown no S3
        """
        with self.SessionLocal() as session:
            try:
                query = text("""
                    INSERT INTO clippings_app.clipping_results
                    (job_id, title, url, content, s3_uri_json, s3_uri_markdown, created_at)
                    VALUES (:job_id, :title, :url, :content, :s3_uri_json, :s3_uri_markdown, NOW())
                """)
                
                session.execute(
                    query,
                    {
                        "job_id": job_id,
                        "title": titulo,
                        "url": url,
                        "content": conteudo,
                        "s3_uri_json": s3_uri_json,
                        "s3_uri_markdown": s3_uri_markdown
                    }
                )
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Erro ao salvar resultado: {e}")
                raise

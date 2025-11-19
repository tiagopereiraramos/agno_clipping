"""
File Agent - Agente de Processamento de Arquivos.

Responsável por processar conteúdo extraído e salvar em diferentes formatos.
"""

from typing import Dict, Any, Optional
import json
import logging
import io
from datetime import datetime
from minio import Minio
from minio.error import S3Error
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class FileAgent(BaseAgent):
    """Agente especializado em processamento e armazenamento de arquivos."""
    
    def __init__(self, configuracao: Dict[str, Any]):
        """
        Inicializa o File Agent.
        
        Args:
            configuracao: Configurações incluindo MinIO/S3
        """
        super().__init__("FileAgent", configuracao)
        self.minio_config = configuracao.get("minio", {})
        
        # Inicializar cliente MinIO se configurado
        self.minio_client = None
        if self.minio_config.get("endpoint") and self.minio_config.get("access_key"):
            try:
                self.minio_client = Minio(
                    self.minio_config["endpoint"],
                    access_key=self.minio_config["access_key"],
                    secret_key=self.minio_config["secret_key"],
                    secure=self.minio_config.get("use_ssl", False)
                )
                # Garantir que o bucket existe
                bucket_name = self.minio_config.get("bucket", "clippings")
                if not self.minio_client.bucket_exists(bucket_name):
                    self.minio_client.make_bucket(bucket_name)
                    self.registrar_log("info", f"Bucket '{bucket_name}' criado no MinIO")
            except Exception as e:
                self.registrar_log("warning", f"Erro ao conectar ao MinIO: {e}. Usando armazenamento local.")
                self.minio_client = None
    
    def executar(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa conteúdo e salva em diferentes formatos.
        
        Args:
            contexto: Contexto com conteúdo extraído
            
        Returns:
            Resultado com URIs dos arquivos salvos
        """
        conteudo = contexto.get("conteudo_extraido")
        job_id = contexto.get("job_id")
        url = contexto.get("url")
        
        if not conteudo:
            raise ValueError("Conteúdo não encontrado no contexto")
        
        self.registrar_log("processamento", f"Processando conteúdo do job {job_id}")
        
        resultado = {
            "formats": {},
            "status": "sucesso"
        }
        
        try:
            # Gerar diferentes formatos
            resultado["formats"]["json"] = self._salvar_json(conteudo, job_id, url)
            resultado["formats"]["markdown"] = self._salvar_markdown(conteudo, job_id, url)
            
            self.registrar_log("sucesso", f"Arquivos processados para job {job_id}")
            return resultado
            
        except Exception as e:
            self.registrar_log("erro", f"Erro ao processar arquivos: {e}")
            raise
    
    def _salvar_json(self, conteudo: str, job_id: str, url: Optional[str]) -> Dict[str, str]:
        """
        Salva conteúdo em formato JSON.
        
        Args:
            conteudo: Conteúdo a ser salvo
            job_id: ID do job
            url: URL de origem
            
        Returns:
            Informações do arquivo salvo
        """
        dados = {
            "job_id": job_id,
            "url": url,
            "conteudo": conteudo,
            "timestamp": datetime.now().isoformat(),
            "formato": "json"
        }
        
        json_str = json.dumps(dados, ensure_ascii=False, indent=2)
        json_bytes = json_str.encode("utf-8")
        nome_arquivo = f"{job_id}.json"
        
        # Tentar salvar no MinIO primeiro
        if self.minio_client:
            try:
                bucket_name = self.minio_config.get("bucket", "clippings")
                self.minio_client.put_object(
                    bucket_name,
                    nome_arquivo,
                    io.BytesIO(json_bytes),
                    length=len(json_bytes),
                    content_type="application/json"
                )
                
                # Construir URI S3
                endpoint = self.minio_config["endpoint"]
                protocol = "https" if self.minio_config.get("use_ssl", False) else "http"
                s3_uri = f"s3://{bucket_name}/{nome_arquivo}"
                
                self.registrar_log("sucesso", f"JSON salvo no MinIO: {s3_uri}")
                return {
                    "path": s3_uri,
                    "uri": s3_uri,
                    "size": len(json_bytes),
                    "storage": "minio"
                }
            except S3Error as e:
                self.registrar_log("erro", f"Erro ao salvar no MinIO: {e}. Usando armazenamento local.")
        
        # Fallback: salvar localmente
        caminho = f"/app/workspace/{nome_arquivo}"
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(json_str)
        
        return {
            "path": caminho,
            "uri": f"file://{caminho}",
            "size": len(json_bytes),
            "storage": "local"
        }
    
    def _salvar_markdown(self, conteudo: str, job_id: str, url: Optional[str]) -> Dict[str, str]:
        """
        Salva conteúdo em formato Markdown.
        
        Args:
            conteudo: Conteúdo a ser salvo
            job_id: ID do job
            url: URL de origem
            
        Returns:
            Informações do arquivo salvo
        """
        markdown = f"""# Clipping - {job_id}

**URL:** {url}
**Data:** {datetime.now().isoformat()}

---

{conteudo}
"""
        
        markdown_bytes = markdown.encode("utf-8")
        nome_arquivo = f"{job_id}.md"
        
        # Tentar salvar no MinIO primeiro
        if self.minio_client:
            try:
                bucket_name = self.minio_config.get("bucket", "clippings")
                self.minio_client.put_object(
                    bucket_name,
                    nome_arquivo,
                    io.BytesIO(markdown_bytes),
                    length=len(markdown_bytes),
                    content_type="text/markdown"
                )
                
                # Construir URI S3
                s3_uri = f"s3://{bucket_name}/{nome_arquivo}"
                
                self.registrar_log("sucesso", f"Markdown salvo no MinIO: {s3_uri}")
                return {
                    "path": s3_uri,
                    "uri": s3_uri,
                    "size": len(markdown_bytes),
                    "storage": "minio"
                }
            except S3Error as e:
                self.registrar_log("erro", f"Erro ao salvar no MinIO: {e}. Usando armazenamento local.")
        
        # Fallback: salvar localmente
        caminho = f"/app/workspace/{nome_arquivo}"
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        return {
            "path": caminho,
            "uri": f"file://{caminho}",
            "size": len(markdown.encode('utf-8')),
            "storage": "local"
        }


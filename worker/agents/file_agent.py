"""
File Agent - Agente de Processamento de Arquivos.

Responsável por processar conteúdo extraído e salvar em diferentes formatos.
"""

from typing import Dict, Any, Optional, List
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
        Consolida toda a saída do Browser Agent e formata para email.
        
        Args:
            contexto: Contexto com conteúdo extraído
            
        Returns:
            Resultado com URIs dos arquivos salvos e conteúdo formatado para email
        """
        conteudo = contexto.get("conteudo_extraido")
        job_id = contexto.get("job_id")
        url = contexto.get("url")
        clipping_json = contexto.get("clipping_json")
        email_body_ptbr = contexto.get("email_body_ptbr")
        itens = contexto.get("itens_coletados", [])
        browseruse_steps = contexto.get("browseruse_steps", "")
        browseruse_reasoning = contexto.get("browseruse_reasoning", "")
        llm_usage = contexto.get("llm_usage", {})
        llm_usage_details = contexto.get("llm_usage_details", {})
        parametros = contexto.get("parametros", {})
        
        if not conteudo and not clipping_json:
            raise ValueError("Conteúdo não encontrado no contexto")
        
        self.registrar_log("processamento", f"Consolidando saída do Browser Agent para job {job_id}")
        
        resultado = {
            "formats": {},
            "status": "sucesso",
            "relatorio_formatado": {}
        }
        
        try:
            # Consolidar e formatar relatório completo
            relatorio_completo = self._consolidar_relatorio(
                job_id=job_id,
                url=url,
                clipping_json=clipping_json,
                email_body_ptbr=email_body_ptbr,
                itens=itens,
                conteudo_bruto=conteudo,
                browseruse_steps=browseruse_steps,
                browseruse_reasoning=browseruse_reasoning,
                llm_usage=llm_usage,
                llm_usage_details=llm_usage_details,
                parametros=parametros
            )
            
            # Salvar relatório consolidado
            resultado["formats"]["json"] = self._salvar_json(relatorio_completo, job_id, url)
            resultado["formats"]["markdown"] = self._salvar_markdown(relatorio_completo, job_id, url)
            resultado["formats"]["relatorio_email"] = self._salvar_relatorio_email(relatorio_completo, job_id)
            
            # Formatar para email
            resultado["relatorio_formatado"] = self._formatar_para_email(relatorio_completo)
            
            # Atualizar contexto com conteúdo formatado para email
            contexto["relatorio_formatado"] = resultado["relatorio_formatado"]
            contexto["email_body_ptbr"] = relatorio_completo.get("email_body_ptbr", "")
            
            self.registrar_log("sucesso", f"Relatório consolidado para job {job_id}: {len(itens)} itens")
            return resultado
            
        except Exception as e:
            self.registrar_log("erro", f"Erro ao processar arquivos: {e}")
            raise
    
    def _salvar_json(self, relatorio: Dict[str, Any], job_id: str, url: Optional[str]) -> Dict[str, str]:
        """
        Salva relatório consolidado em formato JSON.
        
        Args:
            relatorio: Relatório consolidado (pode ser dict ou string)
            job_id: ID do job
            url: URL de origem
            
        Returns:
            Informações do arquivo salvo
        """
        # Se for string, tentar parsear como JSON ou criar estrutura básica
        if isinstance(relatorio, str):
            try:
                dados = json.loads(relatorio)
            except json.JSONDecodeError:
                dados = {
                    "job_id": job_id,
                    "url": url,
                    "conteudo": relatorio,
                    "timestamp": datetime.now().isoformat(),
                    "formato": "json"
                }
        else:
            dados = relatorio
        
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
    
    def _salvar_markdown(self, relatorio: Dict[str, Any], job_id: str, url: Optional[str]) -> Dict[str, str]:
        """
        Salva relatório consolidado em formato Markdown.
        
        Args:
            relatorio: Relatório consolidado (pode ser dict ou string)
            job_id: ID do job
            url: URL de origem
            
        Returns:
            Informações do arquivo salvo
        """
        # Se for dict, formatar como markdown estruturado
        if isinstance(relatorio, dict):
            itens = relatorio.get("clipping", {}).get("itens", [])
            email_body = relatorio.get("clipping", {}).get("email_body_ptbr", "")
            parametros = relatorio.get("parametros", {})
            llm_usage = relatorio.get("llm_usage", {}).get("total", {})
            
            markdown = f"""# Relatório de Clipping - {job_id}

**URL Base:** {url}  
**Data/Hora:** {relatorio.get('timestamp', datetime.now().isoformat())}

## Parâmetros da Busca

"""
            for chave, valor in parametros.items():
                markdown += f"- **{chave}:** {valor}\n"
            
            markdown += f"""
## Resumo

- **Total de itens coletados:** {len(itens)}

## Conteúdo do Clipping

{email_body}

"""
            if itens:
                markdown += "## Itens Coletados\n\n"
                for idx, item in enumerate(itens, start=1):
                    markdown += f"""### [{idx}] {item.get('titulo', 'Sem título')}

- **URL:** {item.get('url', 'N/A')}
- **Data:** {item.get('data_iso', 'N/A')}
- **Seção:** {item.get('secao', 'N/A')}
- **Autor:** {item.get('autor', 'N/A')}
- **Score:** {item.get('score', 0)}
- **Resumo:** {item.get('resumo_2l', 'Sem resumo')}
- **Termos encontrados:** {', '.join(item.get('termos_encontrados', []))}
- **Menciona LEAR:** {'Sim' if item.get('menciona_lear', False) else 'Não'}

"""
            
            markdown += f"""## Consumo de LLM

- **Prompt tokens:** {llm_usage.get('prompt_tokens', 0)}
- **Completion tokens:** {llm_usage.get('completion_tokens', 0)}
- **Total tokens:** {llm_usage.get('total_tokens', 0)}
- **Custo total (USD):** ${llm_usage.get('total_cost_usd', 0.0):.6f}

"""
        else:
            # Se for string, usar formato simples
            markdown = f"""# Clipping - {job_id}

**URL:** {url}
**Data:** {datetime.now().isoformat()}

---

{relatorio}
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


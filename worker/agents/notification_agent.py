"""
Notification Agent - Agente de Notificações.

Responsável por enviar notificações sobre o status dos jobs.
"""

from typing import Dict, Any, Optional
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class NotificationAgent(BaseAgent):
    """Agente especializado em envio de notificações."""
    
    def __init__(self, configuracao: Dict[str, Any]):
        """
        Inicializa o Notification Agent.
        
        Args:
            configuracao: Configurações de SMTP, Slack, etc.
        """
        super().__init__("NotificationAgent", configuracao)
        self.smtp_config = configuracao.get("smtp", {})
        self.slack_webhook = configuracao.get("slack_webhook_url")
        
        # Verificar se SMTP está habilitado
        self.smtp_enabled = self.smtp_config.get("enabled", False)
        if self.smtp_enabled:
            self.smtp_server = self.smtp_config.get("server")
            self.smtp_port = self.smtp_config.get("port", 587)
            self.smtp_user = self.smtp_config.get("user")
            self.smtp_password = self.smtp_config.get("password")
            self.smtp_from = self.smtp_config.get("from_email") or self.smtp_user
            self.smtp_destinatario = self.smtp_config.get("to_email") or "tiagopereiraramos@gmail.com"
    
    def executar(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envia notificações sobre o status do job.
        
        Args:
            contexto: Contexto com informações do job
            
        Returns:
            Resultado do envio de notificações
        """
        job_id = contexto.get("job_id")
        status = contexto.get("status", "concluido")
        
        self.registrar_log("notificacao", f"Enviando notificações para job {job_id}")
        
        resultado = {
            "canais": [],
            "status": "sucesso"
        }
        
        try:
            # Enviar via Slack se configurado
            if self.slack_webhook:
                self._enviar_slack(job_id, status, contexto)
                resultado["canais"].append("slack")
            
            # Enviar via Email se configurado
            if self.smtp_config.get("enabled"):
                self._enviar_email(job_id, status, contexto)
                resultado["canais"].append("email")
            
            self.registrar_log("sucesso", f"Notificações enviadas para job {job_id}")
            return resultado
            
        except Exception as e:
            self.registrar_log("erro", f"Erro ao enviar notificações: {e}")
            # Não falhar o job por erro de notificação
            resultado["status"] = "erro_parcial"
            resultado["erro"] = str(e)
            return resultado
    
    def _enviar_slack(self, job_id: str, status: str, contexto: Dict[str, Any]) -> None:
        """
        Envia notificação via Slack.
        
        Args:
            job_id: ID do job
            status: Status do job
            contexto: Contexto adicional
        """
        import httpx
        
        mensagem = {
            "text": f"Job de Clipping {job_id}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Job de Clipping*\n*ID:* {job_id}\n*Status:* {status}"
                    }
                }
            ]
        }
        
        with httpx.Client() as client:
            response = client.post(self.slack_webhook, json=mensagem)
            response.raise_for_status()
    
    def _enviar_email(self, job_id: str, status: str, contexto: Dict[str, Any]) -> None:
        """
        Envia notificação via Email usando SMTP.
        
        Args:
            job_id: ID do job
            status: Status do job
            contexto: Contexto adicional
        """
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            if not all([self.smtp_server, self.smtp_user, self.smtp_password, self.smtp_from]):
                self.registrar_log("warning", "Configuração SMTP incompleta")
                return
            
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = self.smtp_from
            msg['To'] = self.smtp_destinatario
            msg['Subject'] = f"[Clipping LEAR] Job {job_id} - {status.upper()}"
            
            url = contexto.get("url", "N/A")
            relatorio_formatado = contexto.get("relatorio_formatado", {})
            email_body_ptbr = contexto.get("email_body_ptbr") or relatorio_formatado.get("email_body_ptbr", "")
            artefatos = contexto.get("artefatos", {})
            parametros = contexto.get("parametros", {})
            
            # Usar relatório formatado se disponível, senão usar fallback
            if relatorio_formatado:
                linhas_plain = [relatorio_formatado.get("texto", "")]
                linhas_html = [relatorio_formatado.get("html", "")]
            else:
                # Fallback para formato antigo
                resumo = contexto.get("resumo_conteudo") or (contexto.get("conteudo_extraido") or "")[:600]
                linhas_plain = [
                    "Relatório de Clipping Processado",
                    "",
                    f"Job: {job_id}",
                    f"Status: {status}",
                    f"URL base: {url}",
                    "",
                    "Resumo do conteúdo:",
                    email_body_ptbr or resumo or "Não foi possível gerar resumo.",
                    "",
                    "Artefatos gerados:"
                ]
                linhas_html = [
                    "<html><body>",
                    "<h2 style='font-family:Arial,sans-serif;color:#0b3d91;'>Clipping LEAR - Automotive Business</h2>",
                    f"<p><strong>Job:</strong> {job_id}<br>",
                    f"<strong>Status:</strong> {status.upper()}<br>",
                    f"<strong>Fonte inicial:</strong> <a href='{url}'>{url}</a></p>",
                    "<h3 style='font-family:Arial,sans-serif;color:#0b3d91;'>Resumo principal</h3>",
                    f"<p style='font-family:Arial,sans-serif;white-space:pre-wrap;'>{email_body_ptbr or resumo or 'Sem conteúdo disponível.'}</p>",
                ]
            
            # Se não usou relatório formatado, adicionar artefatos e detalhes
            if not relatorio_formatado:
                if artefatos:
                    linhas_plain.append("")
                    for formato, info in artefatos.items():
                        uri = info.get("uri", "N/A")
                        linhas_plain.append(f"- {formato.upper()}: {uri}")
                    linhas_html.append("<h3 style='font-family:Arial,sans-serif;color:#0b3d91;'>Downloads</h3><ul>")
                    for formato, info in artefatos.items():
                        uri = info.get("uri", "#")
                        tamanho = info.get("size", 0)
                        linhas_html.append(
                            f"<li><strong>{formato.upper()}:</strong> "
                            f"<a href='{uri}'>{uri}</a> "
                            f"(~{tamanho} bytes)</li>"
                        )
                    linhas_html.append("</ul>")
                else:
                    linhas_plain.append("- Nenhum artefato disponível.")
                    linhas_html.append("<p><em>Nenhum artefato disponível.</em></p>")
                
                if parametros:
                    linhas_html.append("<h3 style='font-family:Arial,sans-serif;color:#0b3d91;'>Parâmetros da Busca</h3><ul>")
                    linhas_plain.append("")
                    linhas_plain.append("Parâmetros utilizados:")
                    for chave, valor in parametros.items():
                        linhas_plain.append(f"- {chave}: {valor}")
                        linhas_html.append(f"<li><strong>{chave}:</strong> {valor}</li>")
                    linhas_html.append("</ul>")
                
                llm_usage = contexto.get("llm_usage")
                if llm_usage:
                    linhas_plain.append("")
                    linhas_plain.append("Consumo LLM:")
                    linhas_plain.append(f"- Prompt tokens: {llm_usage.get('prompt_tokens', 0)}")
                    linhas_plain.append(f"- Completion tokens: {llm_usage.get('completion_tokens', 0)}")
                    linhas_plain.append(f"- Custo total (USD): ${llm_usage.get('total_cost_usd', 0.0):.6f}")
                    
                    linhas_html.append("<h3 style='font-family:Arial,sans-serif;color:#0b3d91;'>Consumo de LLM</h3><ul>")
                    linhas_html.append(f"<li>Prompt tokens: {llm_usage.get('prompt_tokens', 0)}</li>")
                    linhas_html.append(f"<li>Completion tokens: {llm_usage.get('completion_tokens', 0)}</li>")
                    linhas_html.append(f"<li>Custo total (USD): ${llm_usage.get('total_cost_usd', 0.0):.6f}</li>")
                    linhas_html.append("</ul>")
                
                detalhes_llm = contexto.get("llm_usage_details")
                if detalhes_llm:
                    linhas_plain.append("")
                    linhas_plain.append("Consumo por componente:")
                    linhas_html.append("<h3 style='font-family:Arial,sans-serif;color:#0b3d91;'>Detalhamento por componente</h3><ul>")
                    for nome, dados in detalhes_llm.items():
                        linhas_plain.append(f"[{nome}] prompt={dados.get('prompt_tokens', 0)} tokens, completion={dados.get('completion_tokens', 0)} tokens, custo=${dados.get('total_cost_usd', 0.0):.6f}")
                        linhas_html.append(
                            "<li><strong>{}</strong>: prompt={} | completion={} | custo=${:.6f}</li>".format(
                                nome,
                                dados.get("prompt_tokens", 0),
                                dados.get("completion_tokens", 0),
                                dados.get("total_cost_usd", 0.0)
                            )
                        )
                    linhas_html.append("</ul>")
                
                linhas_html.append("<p style='font-family:Arial,sans-serif;'>Abraços,<br>Equipe Agno Clipping</p></body></html>")
            
            msg.attach(MIMEText("\n".join(linhas_plain), "plain"))
            msg.attach(MIMEText("".join(linhas_html), "html"))
            
            # Enviar email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            self.registrar_log("sucesso", f"Email enviado com sucesso para job {job_id}")
            
        except Exception as e:
            self.registrar_log("erro", f"Erro ao enviar email: {e}")
            raise


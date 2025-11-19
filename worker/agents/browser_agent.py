"""
Browser Agent - Agente de Navegação Web orientado por BrowserUSE.

Responsável por navegar no site alvo usando o agente oficial do BrowserUSE
conectado ao Browserless via CDP/MCP, garantindo navegação real (inputs, cliques,
buscas) e entrega de reasoning completo.
"""

from __future__ import annotations

import asyncio
import time
import logging
import os
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, urlparse, urlunparse

import httpx
from browser_use.agent.service import Agent as BrowserUseAgent
from browser_use.agent.views import AgentHistoryList
from browser_use.browser.profile import BrowserProfile
from browser_use.browser.session import BrowserSession
from browser_use.llm.models import ChatOpenAI
from websockets.exceptions import ConnectionClosedError

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class BrowserAgent(BaseAgent):
    """Agente especializado em navegação web utilizando BrowserUSE + Browserless."""
    
    def __init__(self, configuracao: Dict[str, Any]):
        super().__init__("BrowserAgent", configuracao)
        self.browserless_url = configuracao.get("browserless_url", "http://browserless:3000").rstrip("/")
        self.browserless_token = configuracao.get("browserless_token")
        self.timeout_ms = configuracao.get("timeout", 30000)
        self.openai_api_key = configuracao.get("openai_api_key")
        self.browser_use_model = configuracao.get("browser_use_model", "gpt-4o-mini")
        self.browser_use_max_steps = configuracao.get("browser_use_max_steps", 40)
        self.browser_use_temperature = configuracao.get("browser_use_temperature", 0.2)
        self.browser_use_retries = configuracao.get("browser_use_retries", 2)
        self.allowed_domains: List[str] = configuracao.get("allowed_domains") or [
            "automotivebusiness.com.br",
            "www.automotivebusiness.com.br",
        ]
        self.downloads_path = configuracao.get("downloads_path", "/tmp/browseruse_downloads")
        os.makedirs(self.downloads_path, exist_ok=True)
        self.http_timeout = max(self.timeout_ms / 1000 if self.timeout_ms else 60, 30)
    
    def executar(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        if not self.openai_api_key:
            raise ValueError("Chave da OpenAI não configurada para o Browser Agent.")
        
        url = contexto.get("url")
        if not url:
            raise ValueError("URL não fornecida no contexto")
        
        tarefa = self._montar_tarefa(contexto)
        self.registrar_log("navegacao", f"Iniciando BrowserUSE com tarefa: {tarefa}")
        
        history = self._executar_com_retries(tarefa)
        self._logar_passos(history)
        
        conteudo = history.final_result() or self._resumir_passos(history)
        contexto["conteudo_extraido"] = conteudo
        contexto["browseruse_steps"] = self._resumir_passos(history, detalhado=True)
        
        if history.usage:
            usage_dict = self._converter_usage(history.usage)
            self._acumular_llm_usage(contexto, usage_dict, "browser_agent")
        
        resultado = {
            "url": url,
            "conteudo": conteudo,
            "status": "sucesso",
            "tamanho": len(conteudo) if conteudo else 0
        }
        self.registrar_log("sucesso", f"BrowserUSE finalizado. Tamanho do relatório: {resultado['tamanho']} caracteres")
        return resultado
    
    def _montar_tarefa(self, contexto: Dict[str, Any]) -> str:
        parametros = contexto.get("parametros", {})
        palavras = parametros.get("palavras_chave", ["Lear", "Lear Corporation", "Lear do Brasil"])
        min_noticias = parametros.get("min_noticias", 3)
        cliente = parametros.get("cliente", "Cliente")
        site = contexto.get("url")
        
        etapas = [
            f"Acesse {site} e localize o campo 'Buscar'.",
            "Execute buscas independentes para cada termo listado, navegando pelos resultados e abrindo as notícias encontradas.",
            f"Garanta que pelo menos {min_noticias} notícias distintas que mencionem LEAR sejam coletadas.",
            "Para cada notícia capture título, data, autor, URL completa e um resumo com até 4 frases destacando produtos/contratos.",
            "Se algum termo não retornar resultados, registre explicitamente a tentativa e o motivo.",
            f"Ao final produza um sumário executivo destacando oportunidades para o time do {cliente}.",
            "Mantenha a navegação estritamente dentro do domínio alvo."
        ]
        
        etapas_formatadas = "\n- ".join(etapas)
        palavras_formatadas = ", ".join(palavras)
        
        return (
            f"Atue como um agente de clipping automotivo.\n"
            f"Palavras-chave: {palavras_formatadas}\n"
            f"Requisitos:\n- {etapas_formatadas}\n"
            "Só conclua quando o sumário executivo estiver pronto."
        )
    
    def _executar_com_retries(self, tarefa: str) -> AgentHistoryList:
        tentativas = max(1, int(self.browser_use_retries))
        erros: List[str] = []
        
        for tentativa in range(1, tentativas + 1):
            try:
                return self._executar_browser_use(tarefa)
            except (ConnectionClosedError, TimeoutError, RuntimeError) as exc:
                msg = f"Tentativa {tentativa}/{tentativas} falhou: {exc}"
                erros.append(msg)
                self.registrar_log("erro", f"[BrowserUSE] {msg}")
                if tentativa < tentativas:
                    time.sleep(3)
                continue
        
        raise RuntimeError("BrowserUSE falhou após múltiplas tentativas: " + "; ".join(erros))
    
    def _executar_browser_use(self, tarefa: str) -> AgentHistoryList:
        cdp_url = self._obter_cdp_url()
        browser_profile = BrowserProfile(
            cdp_url=cdp_url,
            headless=True,
            allowed_domains=self.allowed_domains,
            downloads_path=self.downloads_path
        )
        browser_session = BrowserSession(browser_profile=browser_profile)
        llm = ChatOpenAI(
            model=self.browser_use_model,
            api_key=self.openai_api_key,
            temperature=self.browser_use_temperature
        )
        
        agente = BrowserUseAgent(
            task=tarefa,
            llm=llm,
            browser_session=browser_session,
            max_failures=5,
            use_vision=False,
            include_attributes=["href", "aria-label", "title", "text"]
        )
        
        try:
            history = agente.run_sync(max_steps=self.browser_use_max_steps)
            return history
        finally:
            try:
                asyncio.run(browser_session.stop())
            except Exception:
                pass
    
    def _obter_cdp_url(self) -> str:
        params = {}
        if self.browserless_token:
            params["token"] = self.browserless_token
        version_url = f"{self.browserless_url}/json/version"
        if params:
            version_url = f"{version_url}?{urlencode(params)}"
        
        with httpx.Client(timeout=self.http_timeout) as client:
            response = client.get(version_url)
            response.raise_for_status()
            data = response.json()
        
        ws_url = data.get("webSocketDebuggerUrl")
        if not ws_url:
            raise RuntimeError("Browserless não retornou webSocketDebuggerUrl.")
        
        return self._ajustar_ws_url(ws_url)
    
    def _ajustar_ws_url(self, ws_url: str) -> str:
        parsed_ws = urlparse(ws_url)
        base_parts = urlparse(self.browserless_url)
        scheme = "wss" if base_parts.scheme == "https" else "ws"
        netloc = base_parts.netloc
        query = parsed_ws.query
        if self.browserless_token:
            extra = urlencode({"token": self.browserless_token})
            query = f"{query}&{extra}" if query else extra
        return urlunparse(parsed_ws._replace(scheme=scheme, netloc=netloc, query=query))
    
    def _resumir_passos(self, history: AgentHistoryList, detalhado: bool = False) -> str:
        partes: List[str] = []
        for idx, passo in enumerate(history.history, start=1):
            for resultado in passo.result:
                pensamento = (resultado.thinking or "").strip()
                acao = ""
                if resultado.action:
                    if resultado.action.extracted_content:
                        acao = resultado.action.extracted_content.strip()
                    elif resultado.action.long_term_memory:
                        acao = resultado.action.long_term_memory.strip()
                if pensamento or acao:
                    if detalhado:
                        partes.append(f"Passo {idx}:\nPensamento: {pensamento}\nAção: {acao}\n")
                    else:
                        partes.append(f"Passo {idx}: {pensamento or acao}")
        return "\n".join(partes) if partes else ""
    
    def _logar_passos(self, history: AgentHistoryList) -> None:
        for idx, passo in enumerate(history.history, start=1):
            for resultado in passo.result:
                pensamento = getattr(resultado, "thinking", None)
                if pensamento:
                    self.registrar_log("detalhe", f"[BrowserUSE][Passo {idx}] Pensamento: {pensamento}")
                acao = getattr(resultado, "action", None)
                if acao and getattr(acao, "extracted_content", None):
                    preview = acao.extracted_content.strip()
                    if len(preview) > 400:
                        preview = preview[:400] + "..."
                    self.registrar_log("detalhe", f"[BrowserUSE][Passo {idx}] Resultado: {preview}")
    
    def _converter_usage(self, usage: Any) -> Dict[str, float]:
        return {
            "prompt_tokens": usage.total_prompt_tokens or 0,
            "completion_tokens": usage.total_completion_tokens or 0,
            "total_tokens": usage.total_tokens or 0,
            "prompt_cost_usd": usage.total_prompt_cost or 0.0,
            "completion_cost_usd": usage.total_completion_cost or 0.0,
            "total_cost_usd": usage.total_cost or 0.0,
        }
    
    def _acumular_llm_usage(self, contexto: Dict[str, Any], usage: Dict[str, float], label: str) -> None:
        total = contexto.get("llm_usage", {}).copy()
        for chave, valor in usage.items():
            if isinstance(valor, (int, float)):
                total[chave] = total.get(chave, 0) + valor
        contexto["llm_usage"] = total
        
        detalhes = contexto.get("llm_usage_details", {}).copy()
        detalhes[label] = usage
        contexto["llm_usage_details"] = detalhes

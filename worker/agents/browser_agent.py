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
import threading
import json
import re
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
        self.use_local_browser = configuracao.get("use_local_browser", True)  # Padrão: local (Playwright)
        self.browserless_url = configuracao.get("browserless_url", "http://browserless:3000").rstrip("/")
        self.browserless_token = configuracao.get("browserless_token")
        self.timeout_ms = configuracao.get("timeout", 30000)
        self.openai_api_key = configuracao.get("openai_api_key")
        self.browser_use_model = configuracao.get("browser_use_model", "gpt-4o-mini")
        self.browser_use_max_steps = configuracao.get("browser_use_max_steps", 30)
        self.browser_use_temperature = configuracao.get("browser_use_temperature", 0.2)
        self.browser_use_retries = configuracao.get("browser_use_retries", 3)
        self.browser_use_timeout = configuracao.get("browser_use_timeout", 3600)  # 60 minutos máximo (aumentado para máxima estabilidade)
        self.allowed_domains: List[str] = configuracao.get("allowed_domains") or [
            "automotivebusiness.com.br",
            "www.automotivebusiness.com.br",
        ]
        self.downloads_path = configuracao.get("downloads_path", "/tmp/browseruse_downloads")
        os.makedirs(self.downloads_path, exist_ok=True)
        self.http_timeout = max(self.timeout_ms / 1000 if self.timeout_ms else 60, 60)  # Aumentado para 60s mínimo
        self.cdp_connection_timeout = 120  # 120 segundos para conexão CDP (WebSocket handshake)
        # Caminho para storage_state (sessão do Chrome)
        self.storage_state_path = configuracao.get("storage_state_path", "/app/browser_session/storage_state.json")
        os.environ.setdefault("CDP_CONNECTION_TIMEOUT", "60")
        
        if self.use_local_browser:
            self.registrar_log("info", "✅ Modo LOCAL ativado (Playwright - Chrome local)")
        else:
            self.registrar_log("info", "✅ Modo REMOTO ativado (Browserless)")
    
    def executar(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        if not self.openai_api_key:
            raise ValueError("Chave da OpenAI não configurada para o Browser Agent.")
        
        url = contexto.get("url")
        if not url:
            raise ValueError("URL não fornecida no contexto")
        
        tarefa = self._montar_tarefa(contexto)
        self.registrar_log("navegacao", f"🌐 Iniciando BrowserUSE")
        self.registrar_log("navegacao", f"📋 Tarefa: {tarefa[:200]}...")
        self.registrar_log("navegacao", f"🔗 URL: {url}")
        self.registrar_log("navegacao", f"👀 Acompanhe em: http://localhost:3001/ (clique em 'Sessions')")
        
        # Executar com logging em tempo real
        history = self._executar_com_retries_com_logging(tarefa)
        self._logar_passos(history)
        
        # Extrair resultado final e estruturar
        resultado_final = history.final_result() or self._resumir_passos(history)
        resultado_estruturado = self._extrair_e_estruturar_resultado(resultado_final, contexto)
        
        # Consolidar toda a saída do agente
        contexto["conteudo_extraido"] = resultado_estruturado.get("conteudo_completo")
        contexto["clipping_json"] = resultado_estruturado.get("clipping_json")
        contexto["email_body_ptbr"] = resultado_estruturado.get("email_body_ptbr")
        contexto["itens_coletados"] = resultado_estruturado.get("itens", [])
        contexto["browseruse_steps"] = self._resumir_passos(history, detalhado=True)
        contexto["browseruse_reasoning"] = self._extrair_reasoning_completo(history)
        
        if history.usage:
            usage_dict = self._converter_usage(history.usage)
            self._acumular_llm_usage(contexto, usage_dict, "browser_agent")
        
        resultado = {
            "url": url,
            "conteudo": resultado_estruturado.get("conteudo_completo"),
            "clipping_json": resultado_estruturado.get("clipping_json"),
            "email_body_ptbr": resultado_estruturado.get("email_body_ptbr"),
            "itens": resultado_estruturado.get("itens", []),
            "status": "sucesso",
            "tamanho": len(resultado_estruturado.get("conteudo_completo", "")) if resultado_estruturado.get("conteudo_completo") else 0
        }
        self.registrar_log("sucesso", f"BrowserUSE finalizado. {len(resultado_estruturado.get('itens', []))} itens coletados")
        return resultado
    
    def _montar_tarefa(self, contexto: Dict[str, Any]) -> str:
        """Monta tarefa a partir de prompt parametrizável em arquivo TXT."""
        parametros = contexto.get("parametros", {})
        site = contexto.get("url", "https://www.automotivebusiness.com.br/")
        
        # Parâmetros com valores padrão
        cliente = parametros.get("cliente", "LEAR")
        periodo = parametros.get("periodo", "últimos 7 dias")
        max_itens = parametros.get("max_itens", 10)
        min_noticias = parametros.get("min_noticias", max_itens)  # Fallback para compatibilidade
        
        # Tentar carregar prompt do arquivo
        prompt_paths = [
            "/app/prompts/clipping_lear.txt",
            "./prompts/clipping_lear.txt",
            "prompts/clipping_lear.txt"
        ]
        
        prompt_template = None
        for path in prompt_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        prompt_template = f.read()
                    self.registrar_log("info", f"✅ Prompt carregado de: {path}")
                    break
            except Exception as e:
                self.registrar_log("aviso", f"⚠️ Erro ao carregar prompt de {path}: {e}")
                continue
        
        # Se não encontrou arquivo, usar prompt padrão otimizado
        if not prompt_template:
            self.registrar_log("aviso", "⚠️ Arquivo de prompt não encontrado, usando prompt padrão")
            palavras = parametros.get("palavras_chave", ["Lear", "Lear Corporation", "Lear do Brasil"])
            palavras_str = ", ".join(palavras[:3])
            return (
                f"Clipping: {site}\n"
                f"Buscar: {palavras_str}\n"
                f"Coletar: {min_noticias} notícias únicas\n"
                f"Extrair: título, data, autor, URL, resumo (4 frases), produtos/contratos\n"
                f"Entregar: lista de notícias + sumário executivo para {cliente}\n"
                f"Timeout: {self.browser_use_timeout}s máximo"
            )
        
        # Substituir variáveis no template
        prompt = prompt_template.replace("{cliente}", cliente)
        prompt = prompt.replace("{periodo}", periodo)
        prompt = prompt.replace("{max_itens}", str(max_itens))
        prompt = prompt.replace("{site}", site)
        prompt = prompt.replace("{timeout}", str(self.browser_use_timeout))
        
        # Adicionar instrução de timeout no final
        prompt += f"\n\n## Timeout\n\nTempo máximo de execução: {self.browser_use_timeout} segundos. Colete o máximo de itens possível dentro deste tempo. Não há limite rígido de quantidade - apenas limite de tempo."
        
        return prompt
    
    def _executar_com_retries(self, tarefa: str) -> AgentHistoryList:
        tentativas = max(1, int(self.browser_use_retries))
        erros: List[str] = []
        
        retry_waits = [10, 15, 20]
        for tentativa in range(1, tentativas + 1):
            try:
                return self._executar_browser_use(tarefa)
            except (ConnectionClosedError, TimeoutError, RuntimeError) as exc:
                msg = f"Tentativa {tentativa}/{tentativas} falhou: {exc}"
                erros.append(msg)
                self.registrar_log("erro", f"[BrowserUSE] {msg}")
                if tentativa < tentativas:
                    wait_time = retry_waits[min(tentativa - 1, len(retry_waits) - 1)]
                    self.registrar_log("info", f"⏳ Aguardando {wait_time}s antes de retry...")
                    time.sleep(wait_time)
                    # Tentar reconectar ao CDP
                    try:
                        self.registrar_log("info", "🔄 Tentando reconectar ao Browserless...")
                        cdp_url = self._obter_cdp_url()
                        self.registrar_log("info", f"✅ Reconectado: {cdp_url[:50]}...")
                    except Exception as reconexao_error:
                        self.registrar_log("aviso", f"⚠️ Erro na reconexão: {reconexao_error}")
                continue
        
        raise RuntimeError("BrowserUSE falhou após múltiplas tentativas: " + "; ".join(erros))
    
    def _executar_com_retries_com_logging(self, tarefa: str) -> AgentHistoryList:
        """Executa BrowserUSE com logging em tempo real dos reasonings."""
        tentativas = max(1, int(self.browser_use_retries))
        erros: List[str] = []
        
        retry_waits = [10, 15, 20]
        for tentativa in range(1, tentativas + 1):
            try:
                return self._executar_browser_use_com_logging(tarefa)
            except (ConnectionClosedError, TimeoutError, RuntimeError) as exc:
                msg = f"Tentativa {tentativa}/{tentativas} falhou: {exc}"
                erros.append(msg)
                self.registrar_log("erro", f"[BrowserUSE] {msg}")
                if tentativa < tentativas:
                    wait_time = retry_waits[min(tentativa - 1, len(retry_waits) - 1)]
                    self.registrar_log("info", f"⏳ Aguardando {wait_time}s antes de retry...")
                    time.sleep(wait_time)
                    # Tentar reconectar ao CDP
                    try:
                        self.registrar_log("info", "🔄 Tentando reconectar ao Browserless...")
                        cdp_url = self._obter_cdp_url()
                        self.registrar_log("info", f"✅ Reconectado: {cdp_url[:50]}...")
                    except Exception as reconexao_error:
                        self.registrar_log("aviso", f"⚠️ Erro na reconexão: {reconexao_error}")
                continue
        
        raise RuntimeError("BrowserUSE falhou após múltiplas tentativas: " + "; ".join(erros))
    
    def _executar_browser_use(self, tarefa: str) -> AgentHistoryList:
        """Executa BrowserUSE sem logging em tempo real (método original)."""
        return self._executar_browser_use_com_logging(tarefa)
    
    def _executar_browser_use_com_logging(self, tarefa: str) -> AgentHistoryList:
        """Executa BrowserUSE com logging em tempo real dos reasonings."""
        from threading import Timer
        import json
        from queue import Queue
        
        # Carregar storage_state se existir (sessão do Chrome)
        storage_state = None
        if os.path.exists(self.storage_state_path):
            try:
                with open(self.storage_state_path, 'r') as f:
                    storage_state = json.load(f)
                cookie_count = len(storage_state.get('cookies', []))
                self.registrar_log("info", f"🍪 Sessão do Chrome carregada: {cookie_count} cookies")
            except Exception as e:
                self.registrar_log("aviso", f"⚠️ Erro ao carregar storage_state: {e}")
        else:
            self.registrar_log("info", "ℹ️ Nenhuma sessão do Chrome encontrada (storage_state.json não existe)")
        
        # Escolher entre modo local (Playwright) ou remoto (Browserless)
        if self.use_local_browser:
            browser_profile = self._criar_browser_profile_local(storage_state)
        else:
            browser_profile = self._criar_browser_profile_remoto(storage_state)
        
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
            max_failures=2,  # Reduzido para velocidade
            use_vision=False,  # Desabilitado para navegação rápida (apenas DOM)
            include_attributes=["href", "title", "text", "id", "class"]  # Atributos essenciais para DOM
        )
        
        history_ref = {"history": None}  # Usar dict para referência mutável
        timeout_ocorreu = [False]  # Lista para permitir modificação em closure
        
        def timeout_handler():
            timeout_ocorreu[0] = True
            self.registrar_log("aviso", f"⏱️ Timeout de {self.browser_use_timeout}s atingido")
            try:
                asyncio.run(browser_session.stop())
            except:
                pass
        
        # Thread para monitorar history em tempo real
        def monitorar_reasonings():
            ultimo_step = 0
            while not timeout_ocorreu[0]:
                try:
                    current_history = history_ref["history"]
                    if current_history and hasattr(current_history, 'history') and len(current_history.history) > ultimo_step:
                        # Novo passo detectado
                        for idx in range(ultimo_step, len(current_history.history)):
                            passo = current_history.history[idx]
                            step_num = idx + 1
                            for resultado in passo.result:
                                # Extrair thinking/reasoning
                                thinking = getattr(resultado, "thinking", None)
                                if thinking and thinking.strip():
                                    self.registrar_log("reasoning", f"🧠 [Passo {step_num}] {thinking.strip()}")
                                
                                # Extrair ação
                                action = getattr(resultado, "action", None)
                                if action:
                                    action_type = type(action).__name__
                                    if hasattr(action, "extracted_content") and action.extracted_content:
                                        content = action.extracted_content.strip()[:200]
                                        self.registrar_log("acao", f"⚡ [Passo {step_num}] {action_type}: {content}...")
                                    elif hasattr(action, "long_term_memory") and action.long_term_memory:
                                        memory = action.long_term_memory.strip()[:200]
                                        self.registrar_log("memoria", f"💭 [Passo {step_num}] Memória: {memory}...")
                        ultimo_step = len(current_history.history)
                    time.sleep(0.5)  # Verificar a cada 500ms
                except Exception:
                    # Ignorar erros no monitoramento
                    time.sleep(1)
        
        timer = Timer(self.browser_use_timeout, timeout_handler)
        monitor_thread = threading.Thread(target=monitorar_reasonings, daemon=True)
        
        try:
            timer.start()
            monitor_thread.start()
            
            self.registrar_log("inicio", "🚀 Iniciando execução BrowserUSE...")
            history = agente.run_sync(max_steps=self.browser_use_max_steps)
            history_ref["history"] = history  # Atualizar referência
            timer.cancel()
            
            # Log final dos reasonings
            if history and len(history.history) > 0:
                self.registrar_log("info", f"✅ BrowserUSE completou {len(history.history)} passos")
                # Logar reasonings finais que podem ter sido perdidos
                for idx, passo in enumerate(history.history, start=1):
                    for resultado in passo.result:
                        thinking = getattr(resultado, "thinking", None)
                        if thinking and thinking.strip():
                            self.registrar_log("reasoning", f"🧠 [Passo {idx}] {thinking.strip()}")
            
            if timeout_ocorreu[0]:
                self.registrar_log("aviso", "⏱️ Timeout atingido, retornando resultado parcial")
            
            # Mesmo com erros de conexão, tentar extrair resultado parcial
            if history and history.final_result():
                self.registrar_log("sucesso", "✅ BrowserUSE retornou resultado final")
                return history
            # Se não houver resultado final, usar o que foi coletado
            if history and len(history.history) > 0:
                self.registrar_log("aviso", "⚠️ BrowserUSE completou com resultado parcial")
                return history
            raise RuntimeError("BrowserUSE não retornou resultado")
        except (ConnectionClosedError, TimeoutError, RuntimeError) as e:
            timer.cancel()
            self.registrar_log("erro", f"❌ Erro durante execução BrowserUSE: {e}")
            # Tentar extrair resultado parcial mesmo com erro
            history = history_ref.get("history")
            if history and len(history.history) > 0:
                self.registrar_log("aviso", "⚠️ Retornando resultado parcial apesar do erro")
                # Aguardar um pouco para garantir que tudo foi processado
                time.sleep(2)
                return history
            # Se não houver histórico, tentar reconectar uma última vez
            self.registrar_log("info", "🔄 Tentando reconexão final...")
            try:
                time.sleep(5)
                cdp_url = self._obter_cdp_url()
                self.registrar_log("info", f"✅ Reconexão bem-sucedida: {cdp_url[:50]}...")
            except Exception as reconexao_error:
                self.registrar_log("erro", f"❌ Falha na reconexão final: {reconexao_error}")
            raise
        finally:
            timer.cancel()
            timeout_ocorreu[0] = True  # Parar thread de monitoramento
            time.sleep(0.6)  # Aguardar thread finalizar
            try:
                asyncio.run(browser_session.stop())
            except Exception as e:
                self.registrar_log("aviso", f"Erro ao parar sessão: {e}")
    
    def _verificar_browserless_disponivel(self) -> bool:
        """Verifica se o Browserless está disponível antes de tentar conectar."""
        try:
            # Tentar /json/version que sempre funciona
            version_url = f"{self.browserless_url}/json/version"
            with httpx.Client(timeout=15.0) as client:
                response = client.get(version_url)
                if response.status_code == 200:
                    data = response.json()
                    ws_url = data.get("webSocketDebuggerUrl")
                    if ws_url:
                        self.registrar_log("info", "✅ Browserless está disponível e respondendo")
                        return True
            return False
        except Exception as e:
            self.registrar_log("aviso", f"⚠️ Browserless não disponível: {e}")
            return False
    
    def _obter_cdp_url(self, max_retries: int = 3) -> str:
        """Obtém URL CDP com retry e timeout aumentado."""
        params = {}
        if self.browserless_token:
            params["token"] = self.browserless_token
        version_url = f"{self.browserless_url}/json/version"
        if params:
            version_url = f"{version_url}?{urlencode(params)}"
        
        # Verificar disponibilidade primeiro
        if not self._verificar_browserless_disponivel():
            self.registrar_log("aviso", "⚠️ Browserless não está disponível. Aguardando 5s...")
            time.sleep(5)
        
        ultimo_erro = None
        for tentativa in range(1, max_retries + 1):
            try:
                self.registrar_log("info", f"🔌 Tentativa {tentativa}/{max_retries} de obter CDP URL...")
                with httpx.Client(timeout=self.http_timeout) as client:
                    response = client.get(version_url)
                    response.raise_for_status()
                    data = response.json()
                
                ws_url = data.get("webSocketDebuggerUrl")
                if not ws_url:
                    raise RuntimeError("Browserless não retornou webSocketDebuggerUrl.")
                
                cdp_url = self._ajustar_ws_url(ws_url)
                self.registrar_log("info", f"✅ CDP URL obtida com sucesso: {cdp_url[:50]}...")
                return cdp_url
            except Exception as e:
                ultimo_erro = e
                self.registrar_log("aviso", f"⚠️ Erro ao obter CDP URL (tentativa {tentativa}/{max_retries}): {e}")
                if tentativa < max_retries:
                    wait_time = 5 * tentativa
                    self.registrar_log("info", f"⏳ Aguardando {wait_time}s antes de retry...")
                    time.sleep(wait_time)
        
        raise RuntimeError(f"Falha ao obter CDP URL após {max_retries} tentativas: {ultimo_erro}")
    
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
    
    def _criar_browser_profile_local(self, storage_state: Optional[Dict[str, Any]]) -> BrowserProfile:
        """Cria BrowserProfile usando Playwright local (sem Browserless)."""
        self.registrar_log("info", "🖥️ Iniciando Chrome local via Playwright...")
        
        # BrowserProfile sem cdp_url faz browser-use usar Playwright internamente
        # O browser-use detecta automaticamente quando não há cdp_url e usa Playwright
        browser_profile = BrowserProfile(
            headless=True,
            allowed_domains=self.allowed_domains,
            downloads_path=self.downloads_path,
            keep_alive=True,
            storage_state=storage_state,
            minimum_wait_page_load_time=3.0,  # Aumentado para estabilidade
            wait_for_network_idle_page_load_time=5.0,  # Aumentado para estabilidade
            wait_between_actions=2.0,  # Aumentado para estabilidade
            # Não passar cdp_url faz browser-use usar Playwright diretamente
        )
        
        self.registrar_log("info", "✅ BrowserProfile local criado (Playwright - sem CDP URL)")
        return browser_profile
    
    def _criar_browser_profile_remoto(self, storage_state: Optional[Dict[str, Any]]) -> BrowserProfile:
        """Cria BrowserProfile usando Browserless remoto."""
        self.registrar_log("info", f"🔌 Conectando ao Browserless: {self.browserless_url}")
        
        # Aguardar um pouco para garantir que o Browserless está totalmente pronto
        self.registrar_log("info", "⏳ Aguardando 8s para garantir que Browserless está totalmente pronto...")
        time.sleep(8)
        
        # Verificar disponibilidade e obter CDP URL com retry
        cdp_url = self._obter_cdp_url(max_retries=5)  # 5 tentativas com backoff
        self.registrar_log("info", f"✅ CDP URL obtida: {cdp_url[:50]}...")
        
        # Testar conexão WebSocket antes de passar para browser-use
        self.registrar_log("info", "🧪 Testando conexão WebSocket antes de iniciar browser-use...")
        if not self._testar_conexao_websocket(cdp_url):
            self.registrar_log("aviso", "⚠️ Teste de WebSocket falhou. Aguardando 10s e tentando novamente...")
            time.sleep(10)
            cdp_url = self._obter_cdp_url(max_retries=3)  # Tentar obter nova URL
            if not self._testar_conexao_websocket(cdp_url):
                raise RuntimeError("Não foi possível estabelecer conexão WebSocket com Browserless após múltiplas tentativas")
        
        self.registrar_log("info", "✅ Conexão WebSocket testada e funcionando")
        
        browser_profile = BrowserProfile(
            cdp_url=cdp_url,
            headless=True,
            allowed_domains=self.allowed_domains,
            downloads_path=self.downloads_path,
            keep_alive=True,
            storage_state=storage_state,
            minimum_wait_page_load_time=2.0,  # Navegação rápida - apenas DOM
            wait_for_network_idle_page_load_time=3.0,  # Navegação rápida - apenas DOM
            wait_between_actions=1.0  # Navegação rápida - apenas DOM
        )
        
        self.registrar_log("info", "✅ BrowserProfile remoto criado (Browserless)")
        return browser_profile
    
    def _testar_conexao_websocket(self, cdp_url: str, timeout: float = 15.0) -> bool:
        """Testa se a conexão WebSocket está funcionando antes de passar para browser-use."""
        try:
            import websocket
            ws = websocket.create_connection(
                cdp_url,
                timeout=timeout,
                enable_multithread=True,
                suppress_origin=True
            )
            ws.close()
            return True
        except Exception as e:
            self.registrar_log("aviso", f"⚠️ Erro ao testar WebSocket: {e}")
            return False
    
    def _resumir_passos(self, history: AgentHistoryList, detalhado: bool = False) -> str:
        partes: List[str] = []
        for idx, passo in enumerate(history.history, start=1):
            for resultado in passo.result:
                pensamento = getattr(resultado, "thinking", None) or ""
                pensamento = pensamento.strip() if pensamento else ""
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
    
    def _extrair_e_estruturar_resultado(self, resultado_final: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai e estrutura o resultado do BrowserUSE, tentando parsear JSON se presente.
        
        Args:
            resultado_final: Resultado bruto do BrowserUSE
            contexto: Contexto com parâmetros
            
        Returns:
            Dicionário estruturado com clipping_json, email_body_ptbr, itens, etc.
        """
        resultado_estruturado = {
            "conteudo_completo": resultado_final or "",
            "clipping_json": None,
            "email_body_ptbr": None,
            "itens": []
        }
        
        if not resultado_final:
            return resultado_estruturado
        
        # Tentar extrair JSON do resultado
        try:
            # Procurar por blocos JSON no resultado
            json_pattern = r'\{[^{}]*"itens"[^{}]*\{[^{}]*\}.*?"email_body_ptbr"[^{}]*\}'
            json_match = re.search(json_pattern, resultado_final, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                clipping_data = json.loads(json_str)
                resultado_estruturado["clipping_json"] = clipping_data
                resultado_estruturado["itens"] = clipping_data.get("itens", [])
                resultado_estruturado["email_body_ptbr"] = clipping_data.get("email_body_ptbr", "")
                self.registrar_log("info", f"✅ JSON estruturado extraído: {len(resultado_estruturado['itens'])} itens")
            else:
                # Tentar parsear o resultado inteiro como JSON
                try:
                    clipping_data = json.loads(resultado_final.strip())
                    if isinstance(clipping_data, dict) and "itens" in clipping_data:
                        resultado_estruturado["clipping_json"] = clipping_data
                        resultado_estruturado["itens"] = clipping_data.get("itens", [])
                        resultado_estruturado["email_body_ptbr"] = clipping_data.get("email_body_ptbr", "")
                        self.registrar_log("info", f"✅ JSON completo parseado: {len(resultado_estruturado['itens'])} itens")
                except json.JSONDecodeError:
                    # Se não for JSON, manter como texto
                    self.registrar_log("aviso", "⚠️ Resultado não é JSON válido, mantendo como texto")
        except Exception as e:
            self.registrar_log("aviso", f"⚠️ Erro ao extrair JSON: {e}, mantendo resultado como texto")
        
        return resultado_estruturado
    
    def _extrair_reasoning_completo(self, history: AgentHistoryList) -> str:
        """
        Extrai todo o reasoning (pensamentos) do agente em português.
        
        Args:
            history: Histórico do BrowserUSE
            
        Returns:
            String com todo o reasoning consolidado
        """
        reasoning_parts = []
        for idx, passo in enumerate(history.history, start=1):
            for resultado in passo.result:
                thinking = getattr(resultado, "thinking", None)
                if thinking and thinking.strip():
                    reasoning_parts.append(f"[Passo {idx}] {thinking.strip()}")
        return "\n\n".join(reasoning_parts) if reasoning_parts else ""

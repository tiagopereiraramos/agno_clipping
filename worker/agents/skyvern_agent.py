"""
Skyvern Agent - Agente de Navegação Web usando Skyvern MCP + Agno.

Responsável por navegar no site alvo usando Skyvern MCP como engine de automação
via Agno framework, garantindo navegação em linguagem natural e coleta de artigos.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class SkyvernAgent(BaseAgent):
    """Agente especializado em navegação web utilizando Skyvern MCP + Agno."""
    
    def __init__(self, configuracao: Dict[str, Any]):
        super().__init__("SkyvernAgent", configuracao)
        self.openai_api_key = configuracao.get("openai_api_key")
        self.skyvern_model = configuracao.get("skyvern_model", "gpt-5-mini-2025-08-07")
        self.skyvern_timeout = configuracao.get("skyvern_timeout", 3600)
        self.prompt_path = configuracao.get("prompt_path", "/app/prompts/clipping_lear.txt")
        self.config_path = configuracao.get("config_path", "/app/config/clipping_params.json")
        self.results_dir = configuracao.get("results_dir", "/app/results")
        
        # Configuração de transporte Skyvern (local HTTP ou stdio)
        self.skyvern_base_url = configuracao.get("skyvern_base_url", "http://localhost:8000")
        self.skyvern_transport = configuracao.get("skyvern_transport", "http")  # "http" ou "stdio"
        
        # Criar diretório de resultados se não existir
        os.makedirs(self.results_dir, exist_ok=True)
        
        if not self.openai_api_key:
            raise ValueError("Chave da OpenAI não configurada para o Skyvern Agent.")
        
        self.registrar_log("info", f"✅ SkyvernAgent inicializado (transport={self.skyvern_transport})")
    
    def executar(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa o clipping usando Skyvern MCP + Agno.
        
        Args:
            contexto: Contexto com parâmetros de execução
            
        Returns:
            Dicionário com resultado estruturado
        """
        try:
            self.registrar_log("info", "🚀 Iniciando clipping automotivo com Skyvern MCP")
            
            # Carregar configuração e prompt
            config = self._carregar_configuracao()
            prompt_template = self._carregar_prompt()
            prompt_parametrizado = self._parametrizar_prompt(prompt_template, config)
            
            self.registrar_log("info", f"📝 Prompt carregado e parametrizado para {config.get('cliente', 'LEAR')}")
            
            # Executar com Skyvern via Agno
            resultado = asyncio.run(self._executar_com_skyvern(prompt_parametrizado, config))
            
            # Salvar resultado
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            resultado_path = os.path.join(self.results_dir, f"clipping_resultado_{timestamp}.json")
            self._salvar_resultado(resultado, resultado_path)
            
            self.registrar_log("info", f"✅ Clipping concluído. Resultado salvo em: {resultado_path}")
            
            # Estruturar resultado para compatibilidade com FileAgent
            return self._estruturar_resultado(resultado, config)
            
        except Exception as e:
            self.registrar_log("erro", f"❌ Erro ao executar SkyvernAgent: {e}")
            raise
    
    def _carregar_configuracao(self) -> Dict[str, Any]:
        """Carrega configuração do arquivo JSON."""
        try:
            if not os.path.exists(self.config_path):
                self.registrar_log("aviso", f"⚠️ Arquivo de configuração não encontrado: {self.config_path}. Usando valores padrão.")
                return {
                    "cliente": "LEAR",
                    "periodo": "últimos 30 dias",
                    "max_itens": 15,
                    "site": "https://www.automotivebusiness.com.br/",
                    "timeout": 3600
                }
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.registrar_log("info", f"📋 Configuração carregada: {config.get('cliente')} - {config.get('periodo')}")
            return config
            
        except json.JSONDecodeError as e:
            self.registrar_log("erro", f"❌ Erro ao parsear JSON de configuração: {e}")
            raise ValueError(f"JSON inválido em {self.config_path}: {e}")
        except Exception as e:
            self.registrar_log("erro", f"❌ Erro ao carregar configuração: {e}")
            raise
    
    def _carregar_prompt(self) -> str:
        """Carrega prompt do arquivo TXT."""
        try:
            if not os.path.exists(self.prompt_path):
                raise FileNotFoundError(f"Arquivo de prompt não encontrado: {self.prompt_path}")
            
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                prompt = f.read()
            
            self.registrar_log("info", f"📄 Prompt carregado: {len(prompt)} caracteres")
            return prompt
            
        except Exception as e:
            self.registrar_log("erro", f"❌ Erro ao carregar prompt: {e}")
            raise
    
    def _parametrizar_prompt(self, prompt_template: str, config: Dict[str, Any]) -> str:
        """Substitui placeholders no prompt pelos valores da configuração."""
        prompt = prompt_template
        prompt = prompt.replace("{cliente}", config.get("cliente", "LEAR"))
        prompt = prompt.replace("{periodo}", config.get("periodo", "últimos 30 dias"))
        prompt = prompt.replace("{max_itens}", str(config.get("max_itens", 15)))
        prompt = prompt.replace("{site}", config.get("site", "https://www.automotivebusiness.com.br/"))
        prompt = prompt.replace("{timeout}", str(config.get("timeout", 3600)))
        
        self.registrar_log("info", "✅ Prompt parametrizado com sucesso")
        return prompt
    
    async def _executar_com_skyvern(self, prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Executa o clipping usando Skyvern MCP via Agno."""
        try:
            # Importar Agno (pode não estar instalado)
            try:
                from agno.agent import Agent
                from agno.models.openai import OpenAIChat
                from agno.tools.mcp import MCPTools
            except ImportError as e:
                self.registrar_log("erro", f"❌ Agno não instalado. Execute: pip install agno")
                raise ImportError("Agno framework não está instalado. Instale com: pip install agno") from e
            
            self.registrar_log("info", f"🔌 Inicializando Skyvern MCP (transport={self.skyvern_transport})...")
            
            # Configurar MCPTools para Skyvern
            if self.skyvern_transport == "http":
                # Modo HTTP: conectar ao servidor Skyvern local
                mcp_tools = MCPTools(
                    transport="http",
                    url=self.skyvern_base_url
                )
                self.registrar_log("info", f"✅ Skyvern MCP configurado (HTTP: {self.skyvern_base_url})")
            else:
                # Modo stdio: executar skyvern run mcp diretamente
                mcp_tools = MCPTools(
                    transport="stdio",
                    command="python -m skyvern run mcp"
                )
                self.registrar_log("info", "✅ Skyvern MCP configurado (stdio)")
            
            # Criar agent Agno
            agent = Agent(
                model=OpenAIChat(id=self.skyvern_model, api_key=self.openai_api_key),
                tools=[mcp_tools],
                markdown=True,
                add_datetime_to_context=True
            )
            
            self.registrar_log("info", "👨‍💻 Agent Agno criado com sucesso")
            self.registrar_log("info", "🌐 Iniciando navegação e coleta de artigos...")
            
            # Executar com Skyvern
            resultado_texto = ""
            try:
                # MCPTools deve ser usado como context manager
                async with mcp_tools:
                    # Executar agent de forma assíncrona
                    # Nota: Agno pode usar diferentes métodos dependendo da versão
                    if hasattr(agent, 'aprint_response'):
                        resultado = await agent.aprint_response(
                            input=prompt,
                            stream=True
                        )
                    elif hasattr(agent, 'run'):
                        resultado = await agent.run(prompt)
                    else:
                        # Fallback: usar run síncrono
                        resultado = agent.run(prompt)
                    
                    resultado_texto = str(resultado) if resultado else ""
            except Exception as e:
                self.registrar_log("erro", f"❌ Erro ao executar agent: {e}")
                raise
            
            self.registrar_log("info", f"✅ Navegação concluída. Resultado: {len(resultado_texto)} caracteres")
            
            # Tentar extrair JSON do resultado
            resultado_estruturado = self._extrair_json_do_resultado(resultado_texto)
            
            return resultado_estruturado
            
        except ImportError:
            raise
        except Exception as e:
            self.registrar_log("erro", f"❌ Erro ao executar com Skyvern: {e}")
            raise
    
    def _extrair_json_do_resultado(self, resultado_texto: str) -> Dict[str, Any]:
        """Extrai JSON estruturado do resultado do agent."""
        try:
            # Tentar encontrar JSON no resultado
            import re
            
            # Procurar por blocos JSON
            json_pattern = r'\{[^{}]*"metadata"[^{}]*\{[^{}]*\}.*?"itens"[^{}]*\[.*?\]'
            json_match = re.search(json_pattern, resultado_texto, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                resultado = json.loads(json_str)
                self.registrar_log("info", f"✅ JSON extraído: {len(resultado.get('itens', []))} itens")
                return resultado
            else:
                # Tentar parsear o resultado inteiro como JSON
                try:
                    resultado = json.loads(resultado_texto.strip())
                    return resultado
                except:
                    # Se não for JSON válido, criar estrutura básica
                    self.registrar_log("aviso", "⚠️ Não foi possível extrair JSON. Criando estrutura básica.")
                    return {
                        "metadata": {
                            "cliente": "LEAR",
                            "periodo": "últimos 30 dias",
                            "sites_visitados": [],
                            "total_artigos_encontrados": 0,
                            "total_artigos_validos": 0,
                            "tempo_utilizado_segundos": 0,
                            "coletado_em": datetime.now().isoformat(),
                            "status": "parcial",
                            "mensagem": "Resultado não pôde ser parseado como JSON"
                        },
                        "itens": [],
                        "email_body_ptbr": "Nenhum resultado coletado.",
                        "log_execucao": [f"Erro ao parsear resultado: {resultado_texto[:200]}"]
                    }
                    
        except Exception as e:
            self.registrar_log("erro", f"❌ Erro ao extrair JSON: {e}")
            raise
    
    def _salvar_resultado(self, resultado: Dict[str, Any], caminho: str) -> None:
        """Salva resultado em arquivo JSON."""
        try:
            with open(caminho, 'w', encoding='utf-8') as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)
            
            self.registrar_log("info", f"💾 Resultado salvo em: {caminho}")
            
        except Exception as e:
            self.registrar_log("erro", f"❌ Erro ao salvar resultado: {e}")
            raise
    
    def _estruturar_resultado(self, resultado: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Estrutura resultado para compatibilidade com FileAgent."""
        return {
            "conteudo_completo": json.dumps(resultado, ensure_ascii=False, indent=2),
            "clipping_json": resultado,
            "email_body_ptbr": resultado.get("email_body_ptbr", ""),
            "itens": resultado.get("itens", []),
            "reasoning": f"Execução via Skyvern MCP + Agno para {config.get('cliente', 'LEAR')}",
            "steps": resultado.get("log_execucao", []),
            "llm_usage": {
                "total_tokens": 0,
                "total_cost_usd": 0.0
            }
        }


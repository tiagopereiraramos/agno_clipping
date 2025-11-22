"""
Interpretador de Linguagem Natural usando LLM.

Interpreta instruções em linguagem natural e extrai parâmetros estruturados.
"""

from typing import Dict, Any, Optional
import json
import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMInterpreter:
    """Interpreta instruções em linguagem natural usando OpenAI."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo",
        input_cost_per_1k: float = 0.0,
        output_cost_per_1k: float = 0.0
    ):
        """
        Inicializa o interpretador LLM.
        
        Args:
            api_key: Chave da API OpenAI
            model: Modelo a ser usado
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.input_cost_per_1k = input_cost_per_1k or 0.0
        self.output_cost_per_1k = output_cost_per_1k or 0.0
    
    def interpretar_instrucao(self, instrucao: str) -> Dict[str, Any]:
        """
        Interpreta uma instrução em linguagem natural e extrai parâmetros.
        
        Args:
            instrucao: Instrução em linguagem natural
            
        Returns:
            Dicionário com parâmetros estruturados
        """
        # Prompt otimizado para economia de tokens
        prompt = f"""Extraia da instrução: URL, tipo, parâmetros.

Instrução: "{instrucao}"

Retorne JSON:
{{
    "url": "URL ou null",
    "tipo": "noticia|artigo|produto",
    "parametros": {{"extrair_imagens": false, "extrair_links": true, "formato": "json"}},
    "instrucoes_especificas": "resumo conciso"
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extraia dados estruturados. Retorne apenas JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Reduzido para mais determinismo
                max_tokens=300,  # Limitar tokens de saída
                response_format={"type": "json_object"}
            )
            
            resultado = json.loads(response.choices[0].message.content)
            
            usage_info = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
                "completion_tokens": getattr(response.usage, "completion_tokens", 0) if response.usage else 0,
                "total_tokens": getattr(response.usage, "total_tokens", 0) if response.usage else 0,
                "prompt_cost_usd": 0.0,
                "completion_cost_usd": 0.0,
                "total_cost_usd": 0.0
            }
            if usage_info["prompt_tokens"]:
                usage_info["prompt_cost_usd"] = (usage_info["prompt_tokens"] / 1000) * self.input_cost_per_1k
            if usage_info["completion_tokens"]:
                usage_info["completion_cost_usd"] = (usage_info["completion_tokens"] / 1000) * self.output_cost_per_1k
            usage_info["total_cost_usd"] = usage_info["prompt_cost_usd"] + usage_info["completion_cost_usd"]
            
            resultado["llm_usage"] = usage_info
            logger.info(
                "LLM interpretado | prompt_tokens=%s completion_tokens=%s total_tokens=%s total_cost_usd=%.6f",
                usage_info["prompt_tokens"],
                usage_info["completion_tokens"],
                usage_info["total_tokens"],
                usage_info["total_cost_usd"]
            )
            logger.info(f"Instrução interpretada: {resultado}")
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao interpretar instrução: {e}")
            # Fallback: tentar extrair URL manualmente
            return self._fallback_interpret(instrucao)
    
    def _fallback_interpret(self, instrucao: str) -> Dict[str, Any]:
        """
        Método fallback para extrair URL manualmente.
        
        Args:
            instrucao: Instrução original
            
        Returns:
            Dicionário básico com URL extraída
        """
        import re
        
        # Tentar encontrar URL
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, instrucao)
        
        return {
            "url": urls[0] if urls else None,
            "tipo": "artigo",
            "parametros": {
                "extrair_imagens": False,
                "extrair_links": True,
                "formato": "both"
            },
            "instrucoes_especificas": instrucao
        }


#!/usr/bin/env python3
"""
Script de teste direto do SkyvernAgent (sem filas)
Testa navegação usando Skyvern MCP + Agno
"""

import os
import sys
import json
import time
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from worker.agents.skyvern_agent import SkyvernAgent

# Carregar variáveis de ambiente
load_dotenv()

def main():
    print("🚀 TESTE DIRETO DO SKYVERN AGENT")
    print("=" * 60)
    print()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY não configurada no .env")
        sys.exit(1)
    
    # Configurações
    config = {
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "skyvern_model": os.getenv("SKYVERN_MODEL", "gpt-5-mini-2025-08-07"),
        "skyvern_timeout": int(os.getenv("SKYVERN_TIMEOUT", "3600")),
        "prompt_path": os.getenv("SKYVERN_PROMPT_PATH", "/app/prompts/clipping_lear.txt"),
        "config_path": os.getenv("SKYVERN_CONFIG_PATH", "/app/config/clipping_params.json"),
        "results_dir": os.getenv("SKYVERN_RESULTS_DIR", "/app/results")
    }
    
    print("📋 Configurações:")
    print(f"   Engine: Skyvern MCP + Agno")
    print(f"   Model: {config['skyvern_model']}")
    print(f"   Timeout: {config['skyvern_timeout']}s")
    print(f"   Prompt: {config['prompt_path']}")
    print(f"   Config: {config['config_path']}")
    print()
    
    # Verificar se Skyvern está instalado
    try:
        import skyvern
        print("✅ Skyvern instalado")
    except ImportError:
        print("❌ Skyvern não instalado. Execute: pip install skyvern")
        sys.exit(1)
    
    # Verificar se Agno está instalado
    try:
        import agno
        print("✅ Agno instalado")
    except ImportError:
        print("❌ Agno não instalado. Execute: pip install agno")
        sys.exit(1)
    
    print()
    print("🔄 Iniciando teste...")
    print()
    
    # Criar agente
    try:
        agent = SkyvernAgent(config)
        
        # Contexto de execução
        contexto = {
            "url": "https://www.automotivebusiness.com.br/",
            "parametros": {
                "cliente": "LEAR",
                "periodo": "últimos 30 dias",
                "max_itens": 10,
                "site": "https://www.automotivebusiness.com.br/",
                "timeout": 3600
            }
        }
        
        # Executar
        inicio = time.time()
        resultado = agent.executar(contexto)
        tempo_total = time.time() - inicio
        
        print()
        print("=" * 60)
        print("✅ TESTE CONCLUÍDO")
        print("=" * 60)
        print(f"⏱️  Tempo total: {tempo_total:.2f}s")
        print(f"📊 Itens coletados: {len(resultado.get('itens', []))}")
        print()
        
        # Mostrar resultado resumido
        if resultado.get('itens'):
            print("📝 Primeiros itens:")
            for i, item in enumerate(resultado['itens'][:3], 1):
                print(f"   {i}. {item.get('titulo', 'Sem título')[:60]}...")
        else:
            print("⚠️  Nenhum item coletado")
        
        print()
        print(f"💾 Resultado completo salvo em: {resultado.get('results_path', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()


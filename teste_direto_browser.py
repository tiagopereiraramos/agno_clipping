#!/usr/bin/env python3
"""
Script de teste direto do BrowserAgent (sem filas)
Testa navegação, monitoramento, logs e custos em tempo real
"""

import os
import sys
import json
import time
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from worker.agents.browser_agent import BrowserAgent

# Carregar variáveis de ambiente
load_dotenv()

def main():
    print("🚀 TESTE DIRETO DO BROWSER AGENT")
    print("=" * 60)
    print()
    
    # Configurações
    use_local = os.getenv("USE_LOCAL_BROWSER", "true").lower() == "true"
    config = {
        "use_local_browser": use_local,  # True = Playwright local, False = Browserless
        "browserless_url": os.getenv("BROWSERLESS_URL", "http://browserless:3000"),
        "browserless_token": os.getenv("BROWSERLESS_TOKEN", ""),
        "timeout": 30000,
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "browser_use_model": os.getenv("BROWSER_USE_MODEL", "gpt-5-mini-2025-08-07"),
        "browser_use_max_steps": int(os.getenv("BROWSER_USE_MAX_STEPS", "30")),
        "browser_use_temperature": float(os.getenv("BROWSER_USE_TEMPERATURE", "0.2")),
        "browser_use_retries": int(os.getenv("BROWSER_USE_RETRIES", "3")),
        "browser_use_timeout": int(os.getenv("BROWSER_USE_TIMEOUT", "1800")),  # 30 minutos para busca de 10 anos
        "storage_state_path": "/app/browser_session/storage_state.json",
        "allowed_domains": ["automotivebusiness.com.br", "www.automotivebusiness.com.br"]
    }
    
    if not config["openai_api_key"]:
        print("❌ OPENAI_API_KEY não configurada no .env")
        sys.exit(1)
    
    print("📋 Configurações:")
    print(f"   Modo: {'LOCAL (Playwright)' if config['use_local_browser'] else 'REMOTO (Browserless)'}")
    if not config['use_local_browser']:
        print(f"   Browserless URL: {config['browserless_url']}")
    print(f"   Model: {config['browser_use_model']}")
    print(f"   Max Steps: {config['browser_use_max_steps']}")
    print(f"   Timeout: {config['browser_use_timeout']}s")
    print(f"   Storage State: {config['storage_state_path']}")
    print()
    
    # Verificar se storage_state existe
    if os.path.exists(config["storage_state_path"]):
        with open(config["storage_state_path"], 'r') as f:
            storage = json.load(f)
        cookie_count = len(storage.get('cookies', []))
        print(f"🍪 Sessão do Chrome encontrada: {cookie_count} cookies")
    else:
        print("ℹ️  Nenhuma sessão do Chrome encontrada (será criada nova sessão)")
    print()
    
    # Verificar se prompt existe
    prompt_path = "/app/prompts/clipping_lear.txt"
    if os.path.exists(prompt_path):
        print(f"✅ Prompt parametrizável encontrado: {prompt_path}")
    else:
        print(f"⚠️  Prompt não encontrado em {prompt_path}, usando prompt padrão")
    print()
    
    # Criar BrowserAgent
    print("🔧 Inicializando BrowserAgent...")
    browser_agent = BrowserAgent(config)
    print("✅ BrowserAgent inicializado")
    print()
    
    # Carregar parâmetros do arquivo de configuração (se existir)
    params_file = "/app/config/clipping_params.json"
    if os.path.exists(params_file):
        with open(params_file, 'r', encoding='utf-8') as f:
            params_config = json.load(f)
        print(f"✅ Parâmetros carregados de: {params_file}")
    else:
        # Parâmetros padrão
        params_config = {
            "cliente": "LEAR",
            "periodo": "últimos 7 dias",
            "max_itens": 10,
            "min_noticias": 3
        }
        print(f"ℹ️  Usando parâmetros padrão (arquivo {params_file} não encontrado)")
    
    # Contexto com parâmetros (será usado pelo prompt parametrizável)
    contexto = {
        "url": params_config.get("url", "https://www.automotivebusiness.com.br/"),
        "parametros": {
            "cliente": params_config.get("cliente", "LEAR"),
            "periodo": params_config.get("periodo", "últimos 7 dias"),
            "max_itens": params_config.get("max_itens", 10),
            "min_noticias": params_config.get("min_noticias", 3)
        }
    }
    
    print("📝 Parâmetros do Clipping:")
    print("-" * 60)
    print(f"   Cliente: {contexto['parametros']['cliente']}")
    print(f"   Período: {contexto['parametros']['periodo']}")
    print(f"   Max Itens: {contexto['parametros']['max_itens']}")
    print(f"   URL: {contexto['url']}")
    print("-" * 60)
    print()
    
    print("🌐 Iniciando navegação...")
    print("📺 Acompanhe em tempo real:")
    print("   - Logs abaixo (em tempo real)")
    print("   - Browserless UI: http://localhost:3001/")
    print("   - Sessões CDP: ./scripts/verificar_sessoes_browserless.sh")
    print()
    print("=" * 60)
    print("📊 LOGS EM TEMPO REAL:")
    print("=" * 60)
    print()
    
    inicio = time.time()
    
    try:
        # Executar navegação
        resultado = browser_agent.executar(contexto)
        
        tempo_total = time.time() - inicio
        
        print()
        print("=" * 60)
        print("✅ NAVEGAÇÃO CONCLUÍDA")
        print("=" * 60)
        print(f"⏱️  Tempo total: {tempo_total:.2f}s")
        print()
        
        # Mostrar resultado
        if resultado:
            print("📄 Resultado:")
            print("-" * 60)
            
            # Extrair informações relevantes
            conteudo = resultado.get("conteudo", "")
            if conteudo:
                preview = conteudo[:500] + "..." if len(conteudo) > 500 else conteudo
                print(preview)
            
            # Mostrar estatísticas
            if "llm_usage" in resultado:
                usage = resultado["llm_usage"]
                print()
                print("💰 Custo LLM:")
                print(f"   Prompt tokens: {usage.get('prompt_tokens', 0):,}")
                print(f"   Completion tokens: {usage.get('completion_tokens', 0):,}")
                print(f"   Total tokens: {usage.get('total_tokens', 0):,}")
                print(f"   Custo total: ${usage.get('total_cost_usd', 0):.6f}")
            
            # Salvar resultado completo
            resultado_file = "teste_browser_resultado.json"
            with open(resultado_file, 'w', encoding='utf-8') as f:
                json.dump(resultado, f, indent=2, ensure_ascii=False)
            print()
            print(f"💾 Resultado completo salvo em: {resultado_file}")
        
    except Exception as e:
        tempo_total = time.time() - inicio
        print()
        print("=" * 60)
        print("❌ ERRO NA NAVEGAÇÃO")
        print("=" * 60)
        print(f"⏱️  Tempo até erro: {tempo_total:.2f}s")
        print(f"❌ Erro: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

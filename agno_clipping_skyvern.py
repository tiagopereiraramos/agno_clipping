#!/usr/bin/env python3
"""
Agno Clipping com Skyvern MCP - Clipping Automotivo
Integra Skyvern MCP (browser automation) com Agno framework para coleta de artigos automotivos.
Usa Chrome local via Skyvern server HTTP (não Browserless remoto).
"""

import asyncio
import json
import os
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

try:
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from agno.tools.mcp import MCPTools
except ImportError as e:
    print(f"❌ ERRO: Agno não instalado. Execute: pip install agno>=0.5.0")
    print(f"   Erro: {e}")
    sys.exit(1)


async def main():
    print("\n" + "="*70)
    print("🚀 CLIPPING AUTOMOTIVO LEAR - SKYVERN + CHROME LOCAL (AJUSTADO)")
    print("="*70 + "\n")
    
    # Verificação prévia: Chrome disponível?
    print("🔍 Verificando Chrome local...")
    chrome_path = "/root/.cache/ms-playwright/chromium-1129/chrome-linux/chrome"
    if os.path.exists(chrome_path):
        print(f"   ✅ Chrome encontrado: {chrome_path}\n")
    else:
        # Tentar encontrar Chrome do Playwright
        from pathlib import Path
        playwright_path = Path("/root/.cache/ms-playwright")
        if playwright_path.exists():
            chromium_dirs = list(playwright_path.glob("chromium-*/chrome-linux/chrome"))
            if chromium_dirs:
                chrome_path = str(chromium_dirs[0])
                print(f"   ✅ Chrome encontrado: {chrome_path}\n")
            else:
                print(f"   ⚠️  Chrome não encontrado")
                print("   Continuando mesmo assim...\n")
        else:
            print(f"   ⚠️  Playwright path não existe")
            print("   Continuando mesmo assim...\n")
    
    # PASSO 1: Carregar configuração
    print("📂 Carregando configuração...")
    try:
        with open("config/clipping_params.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        print(f"   ✅ Cliente: {config['cliente']}")
        print(f"   ✅ Período: {config['periodo']}")
        print(f"   ✅ Max itens: {config['max_itens']}\n")
    except FileNotFoundError:
        print("❌ ERRO: Arquivo config/clipping_params.json não encontrado")
        sys.exit(1)
    
    # PASSO 2: Carregar prompt
    print("📝 Carregando prompt...")
    try:
        with open("prompts/clipping_lear.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()
        print("   ✅ Prompt carregado\n")
    except FileNotFoundError:
        print("❌ ERRO: Arquivo prompts/clipping_lear.txt não encontrado")
        sys.exit(1)
    
    # PASSO 3: Parametrizar prompt
    print("🔧 Parametrizando prompt...")
    prompt_parametrizado = prompt_template.replace("{cliente}", config.get("cliente", "LEAR"))
    prompt_parametrizado = prompt_parametrizado.replace("{periodo}", config.get("periodo", "últimos 30 dias"))
    prompt_parametrizado = prompt_parametrizado.replace("{max_itens}", str(config.get("max_itens", 15)))
    prompt_parametrizado = prompt_parametrizado.replace("{site}", config.get("site", "https://www.automotivebusiness.com.br/"))
    prompt_parametrizado = prompt_parametrizado.replace("{timeout}", str(config.get("timeout", 1800)))
    print("   ✅ Prompt parametrizado\n")
    
    # PASSO 4: Verificar OPENAI_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ ERRO: OPENAI_API_KEY não configurada no .env")
        sys.exit(1)
    
    # PASSO 5: Configurar Skyvern MCP com Chrome Local
    # Usar stdio transport (não precisa de servidor HTTP separado)
    print("🔌 Conectando a Skyvern MCP (Chrome local via stdio)...")
    print("   Modo: STDIO (execução direta, sem servidor HTTP)")
    
    # Encontrar Chrome
    chrome_path = "/root/.cache/ms-playwright/chromium-1129/chrome-linux/chrome"
    if not os.path.exists(chrome_path):
        from pathlib import Path
        playwright_path = Path("/root/.cache/ms-playwright")
        if playwright_path.exists():
            chromium_dirs = list(playwright_path.glob("chromium-*/chrome-linux/chrome"))
            if chromium_dirs:
                chrome_path = str(chromium_dirs[0])
    
    if os.path.exists(chrome_path):
        print(f"   ✅ Chrome: {chrome_path}")
        # Configurar variáveis de ambiente ANTES de criar MCPTools
        os.environ["CHROME_BIN"] = chrome_path
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/root/.cache/ms-playwright"
        os.environ["SKYVERN_MODE"] = "local"
        print(f"   ✅ Variáveis de ambiente configuradas")
    else:
        print(f"   ⚠️  Chrome não encontrado, mas continuando...")
    
    print("   ⚠️  Skyvern será executado como processo filho\n")
    
    try:
        # Usar stdio transport (executa skyvern run mcp diretamente)
        # As env vars já estão configuradas acima, então serão herdadas
        mcp_tools = MCPTools(
            transport="stdio",  # ← stdio não precisa de servidor HTTP
            command="python -m skyvern run mcp"  # ← Executa MCP (herda env vars do processo pai)
        )
        print("   ✅ MCPTools configurado (stdio com Chrome local)\n")
    except Exception as e:
        print(f"   ❌ ERRO ao conectar: {e}")
        print("\n   DEBUG:")
        print("   - Verifique se skyvern está instalado: pip install skyvern[local]")
        print("   - Verifique se Chrome está em: /root/.cache/ms-playwright/chromium-*/chrome-linux/chrome")
        import traceback
        traceback.print_exc()
        return
    
    # PASSO 6: Criar agent
    print("👨‍💻 Criando agent Agno com GPT-5-mini-2025-08-07...")
    try:
        agent = Agent(
            model=OpenAIChat(id="gpt-5-mini-2025-08-07", api_key=openai_key),
            tools=[mcp_tools],
            markdown=True,
            add_datetime_to_context=True,
            instructions="""🚨 EXECUTE AGORA - NÃO PLANEJE 🚨

Você DEVE executar as ações imediatamente usando as ferramentas Skyvern MCP disponíveis.
NÃO retorne planos, pseudocódigo ou descrições do que você faria.
USE AS FERRAMENTAS para navegar, extrair e processar conteúdo REAL.

INSTRUÇÕES:
1. Use as ferramentas Skyvern MCP para navegar para os sites
2. Extraia conteúdo real dos artigos
3. Processe os dados coletados
4. Retorne JSON estruturado com os dados reais coletados

NÃO DESCREVA - EXECUTE!"""
        )
        print("   ✅ Agent criado com instruções de execução\n")
    except Exception as e:
        print(f"   ❌ ERRO ao criar agent: {e}")
        return
    
    # PASSO 7: Executar com Chrome Local
    print("="*70)
    print("🌐 INICIANDO NAVEGAÇÃO COM CHROME LOCAL")
    print("="*70 + "\n")
    
    try:
        resultado = await agent.aprint_response(
            input=prompt_parametrizado,
            stream=True
        )
    except Exception as e:
        print(f"\n❌ ERRO durante execução: {e}")
        print("\nDEBUG: Possíveis causas:")
        print("  1. Chrome não está realmente rodando (HTTP 403)")
        print("  2. Skyvern não tem modo local ativo")
        print("  3. MCPTools não conseguiu conectar")
        import traceback
        traceback.print_exc()
        return
    
    # PASSO 8: Salvar resultado
    print("\n" + "="*70)
    print("✅ CLIPPING CONCLUÍDO COM SUCESSO!")
    print("="*70)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results/clipping_resultado_{timestamp}.json"
    
    os.makedirs("results", exist_ok=True)
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            if isinstance(resultado, str):
                # Tentar extrair JSON do resultado se for string
                import re
                json_match = re.search(r'\{.*\}', resultado, re.DOTALL)
                if json_match:
                    try:
                        resultado_json = json.loads(json_match.group(0))
                        json.dump(resultado_json, f, ensure_ascii=False, indent=2)
                    except:
                        f.write(resultado)
                else:
                    f.write(resultado)
            else:
                json.dump(resultado, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Resultado salvo em: {filename}\n")
    except Exception as e:
        print(f"⚠️  Aviso: Erro ao salvar resultado: {e}")
        print(f"   Resultado: {resultado}")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Agno Clipping com Skyvern MCP - Clipping Automotivo (VERSÃO CORRIGIDA)
Usa servidor HTTP do Skyvern para garantir que Chrome local seja usado corretamente.
"""

import asyncio
import json
import os
import sys
import time
import requests
import subprocess
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


def encontrar_chrome():
    """Encontra o caminho do Chrome instalado via Playwright."""
    chrome_path = "/root/.cache/ms-playwright/chromium-1129/chrome-linux/chrome"
    if os.path.exists(chrome_path):
        return chrome_path
    
    # Tentar encontrar Chrome do Playwright
    playwright_path = Path("/root/.cache/ms-playwright")
    if playwright_path.exists():
        chromium_dirs = list(playwright_path.glob("chromium-*/chrome-linux/chrome"))
        if chromium_dirs:
            return str(chromium_dirs[0])
    return None


def iniciar_skyvern_server(chrome_path):
    """Inicia Skyvern server em background com Chrome local."""
    print("🚀 Iniciando Skyvern server em background...")
    
    # Configurar variáveis de ambiente
    env = os.environ.copy()
    env["CHROME_BIN"] = chrome_path
    env["PLAYWRIGHT_BROWSERS_PATH"] = "/root/.cache/ms-playwright"
    env["SKYVERN_MODE"] = "local"
    env["PYTHONUNBUFFERED"] = "1"
    
    # Iniciar servidor em background
    cmd = ["python", "-m", "skyvern", "run", "server"]
    print(f"   Comando: {' '.join(cmd)}")
    print(f"   CHROME_BIN={chrome_path}")
    
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Redirecionar stderr para stdout
        text=True,
        bufsize=1
    )
    
    # Aguardar servidor iniciar (com logs)
    print("   ⏳ Aguardando Skyvern iniciar...")
    output_lines = []
    for i in range(60):  # 60 tentativas, 1 segundo cada (aumentado para 60s)
        # Verificar se processo ainda está rodando
        if process.poll() is not None:
            # Processo terminou, ler saída
            stdout, _ = process.communicate()
            print(f"   ❌ Skyvern terminou com código {process.returncode}")
            print(f"   Saída: {stdout[:500] if stdout else 'Nenhuma saída'}")
            return None
        
        # Tentar conectar (qualquer resposta HTTP significa que servidor está rodando)
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            # Se recebeu resposta (mesmo 404), servidor está rodando
            if response.status_code in [200, 404]:
                print(f"   ✅ Skyvern server iniciado (PID: {process.pid})")
                print(f"   Status: {response.status_code} (servidor respondendo)")
                return process
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            # Se não é ConnectionError, servidor pode estar rodando
            try:
                # Tentar endpoint raiz
                response = requests.get("http://localhost:8000/", timeout=2)
                if response.status_code in [200, 404, 405]:
                    print(f"   ✅ Skyvern server iniciado (PID: {process.pid})")
                    print(f"   Status: {response.status_code} (servidor respondendo)")
                    return process
            except:
                pass
        
        # Ler saída não bloqueante
        try:
            if process.stdout and process.stdout.readable():
                line = process.stdout.readline()
                if line:
                    output_lines.append(line.strip())
                    if len(output_lines) > 10:  # Manter apenas últimas 10 linhas
                        output_lines.pop(0)
        except:
            pass
        
        time.sleep(1)
        if i % 10 == 0 and i > 0:
            print(f"   ⏳ Ainda aguardando... ({i}s)")
            if output_lines:
                print(f"   Últimas linhas: {output_lines[-3:]}")
    
    print("   ❌ Skyvern não iniciou em 60 segundos")
    if output_lines:
        print(f"   Últimas linhas de saída: {output_lines[-5:]}")
    process.terminate()
    try:
        process.wait(timeout=5)
    except:
        process.kill()
    return None


async def main():
    print("\n" + "="*70)
    print("🚀 CLIPPING AUTOMOTIVO LEAR - SKYVERN + CHROME LOCAL (FIXED)")
    print("="*70 + "\n")
    
    # Verificação prévia: Chrome disponível?
    print("🔍 Verificando Chrome local...")
    chrome_path = encontrar_chrome()
    if chrome_path and os.path.exists(chrome_path):
        print(f"   ✅ Chrome encontrado: {chrome_path}\n")
    else:
        print(f"   ❌ Chrome NÃO encontrado!")
        print("   Execute: playwright install chromium")
        sys.exit(1)
    
    # Iniciar Skyvern server
    skyvern_process = iniciar_skyvern_server(chrome_path)
    if not skyvern_process:
        print("❌ Não foi possível iniciar Skyvern server")
        sys.exit(1)
    
    try:
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
        
        # PASSO 5: Configurar Skyvern MCP com HTTP (servidor já está rodando)
        print("🔌 Conectando a Skyvern MCP (HTTP)...")
        print("   URL: http://localhost:8000")
        print("   Modo: HTTP (servidor com Chrome local)\n")
        
        try:
            mcp_tools = MCPTools(
                transport="http",
                url="http://localhost:8000"
            )
            print("   ✅ MCPTools configurado\n")
        except Exception as e:
            print(f"   ❌ ERRO ao conectar: {e}")
            raise
        
        # PASSO 6: Criar agent
        print("👨‍💻 Criando agent Agno com GPT-5-mini-2025-08-07...")
        try:
            agent = Agent(
                model=OpenAIChat(id="gpt-5-mini-2025-08-07", api_key=openai_key),
                tools=[mcp_tools],
                markdown=True,
                add_datetime_to_context=True,
                show_tool_calls=True,  # Mostrar chamadas de ferramentas
                instructions="""🚨 USE AS FERRAMENTAS SKYVERN MCP AGORA 🚨

VOCÊ TEM FERRAMENTAS SKYVERN MCP DISPONÍVEIS. USE-AS DIRETAMENTE:

1. As ferramentas Skyvern estão disponíveis via MCPTools
2. USE as ferramentas para navegar, clicar, extrair
3. NÃO retorne planos ou pseudocódigo
4. NÃO sugira scripts Python ou Selenium
5. EXECUTE usando as ferramentas disponíveis
6. Retorne JSON com dados REAIS coletados

Chrome local está funcionando. Ferramentas estão disponíveis. USE-AS AGORA!"""
            )
            print("   ✅ Agent criado com instruções de execução\n")
        except Exception as e:
            print(f"   ❌ ERRO ao criar agent: {e}")
            raise
        
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
            import traceback
            traceback.print_exc()
            raise
        
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
    
    finally:
        # Parar Skyvern server
        if skyvern_process:
            print("\n🛑 Parando Skyvern server...")
            skyvern_process.terminate()
            skyvern_process.wait(timeout=5)
            print("   ✅ Skyvern server parado")


if __name__ == "__main__":
    asyncio.run(main())


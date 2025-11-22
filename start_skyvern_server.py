#!/usr/bin/env python3
"""
Helper script para iniciar Skyvern server com Chrome local.
Garante que Chrome está disponível e Skyvern está configurado corretamente.
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def verificar_chrome():
    """Verifica se Chrome/Chromium está disponível."""
    print("🔍 Verificando Chrome/Chromium...")
    
    # Caminhos possíveis
    caminhos_chrome = [
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/root/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
    ]
    
    # Verificar via which
    try:
        result = subprocess.run(["which", "chromium-browser"], capture_output=True, text=True)
        if result.returncode == 0:
            chrome_path = result.stdout.strip()
            print(f"   ✅ Chrome encontrado: {chrome_path}")
            return chrome_path
    except:
        pass
    
    # Verificar via playwright
    try:
        from pathlib import Path
        playwright_path = Path("/root/.cache/ms-playwright")
        if playwright_path.exists():
            chromium_dirs = list(playwright_path.glob("chromium-*/chrome-linux/chrome"))
            if chromium_dirs:
                chrome_path = str(chromium_dirs[0])
                print(f"   ✅ Chrome Playwright encontrado: {chrome_path}")
                return chrome_path
    except:
        pass
    
    print("   ⚠️ Chrome não encontrado automaticamente")
    print("   Tentando usar Playwright chromium...")
    return None

def verificar_porta_8000():
    """Verifica se porta 8000 está livre."""
    print("🔍 Verificando porta 8000...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("   ⚠️ Porta 8000 já está em uso (Skyvern pode estar rodando)")
            return False
    except requests.exceptions.ConnectionError:
        print("   ✅ Porta 8000 está livre")
        return True
    except Exception as e:
        print(f"   ⚠️ {e}")
        return True

def iniciar_skyvern():
    """Inicia Skyvern server com Chrome local."""
    print("\n🚀 Iniciando Skyvern server com Chrome local...")
    
    # Verificar porta
    if not verificar_porta_8000():
        print("\n❌ Porta 8000 já está em uso.")
        print("   Pare o Skyvern anterior com: pkill -f 'skyvern run'")
        return
    
    # Verificar Chrome
    chrome_path = verificar_chrome()
    
    # Configurar variáveis de ambiente
    env = os.environ.copy()
    env["SKYVERN_MODE"] = "local"
    env["PYTHONUNBUFFERED"] = "1"
    
    if chrome_path:
        env["CHROME_BIN"] = chrome_path
        env["PLAYWRIGHT_BROWSERS_PATH"] = "/root/.cache/ms-playwright"
    
    # Comando para iniciar Skyvern (sem --local, não existe essa opção)
    # O modo local é controlado por variáveis de ambiente
    cmd = ["python", "-m", "skyvern", "run", "server"]
    
    print(f"\n   Comando: {' '.join(cmd)}")
    print(f"   Modo: LOCAL (via variáveis de ambiente)")
    print(f"   SKYVERN_MODE=local")
    if chrome_path:
        print(f"   CHROME_BIN={chrome_path}")
        print(f"   Chrome: {chrome_path}")
    print("\n   ⏳ Iniciando... (pressione Ctrl+C para parar)\n")
    print("="*70)
    
    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\n\n✅ Skyvern server parado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar Skyvern: {e}")
        sys.exit(1)

def main():
    print("="*70)
    print("🚀 SKYVERN SERVER - CHROME LOCAL")
    print("="*70)
    iniciar_skyvern()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script de teste para verificar se Skyvern está funcionando corretamente com Chrome local.
"""

import requests
import time
import json

print("🧪 Testando Skyvern com Chrome local...\n")

# TESTE 1: Health check
print("1️⃣ Verificando saúde do Skyvern...")
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        print(f"   ✅ Skyvern respondendo")
        try:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        except:
            print(f"   Response: {response.text[:200]}")
    else:
        print(f"   ❌ Status {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except requests.exceptions.ConnectionError:
    print("   ❌ Skyvern NÃO está rodando em localhost:8000")
    print("   Execute: python start_skyvern_server.py")
    print("   Ou: SKYVERN_MODE=local skyvern run server --local")
    exit(1)
except Exception as e:
    print(f"   ❌ Erro: {e}")
    exit(1)

# TESTE 2: Tentar navegação simples
print("\n2️⃣ Testando navegação a Google (simples)...")
task = {
    "url": "https://www.google.com",
    "goal": "Get the title of the page"
}

try:
    print("   Enviando requisição...")
    response = requests.post(
        "http://localhost:8000/tasks",
        json=task,
        timeout=30
    )
    
    if response.status_code == 200:
        print(f"   ✅ Navegação bem-sucedida!")
        try:
            result = response.json()
            print(f"   Resultado: {json.dumps(result, indent=2)[:500]}")
        except:
            print(f"   Response: {response.text[:500]}")
    elif response.status_code == 403:
        print(f"   ❌ HTTP 403 - Chrome NÃO está realmente navegando")
        print(f"   Possível causa: Chrome não foi inicializado corretamente")
        print(f"   Solução: Reinicie Skyvern com: SKYVERN_MODE=local skyvern run server --local")
    else:
        print(f"   ⚠️ Status {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        
except Exception as e:
    print(f"   ❌ Erro: {e}")

# TESTE 3: Tentar navegação ao site real
print("\n3️⃣ Testando navegação a automotivebusiness.com.br...")
task = {
    "url": "https://www.automotivebusiness.com.br/",
    "goal": "Get page title and check if page loaded successfully"
}

try:
    print("   Enviando requisição...")
    response = requests.post(
        "http://localhost:8000/tasks",
        json=task,
        timeout=30
    )
    
    if response.status_code == 200:
        print(f"   ✅ Navegação bem-sucedida!")
        print(f"   Sem 403! Chrome está funcionando corretamente.")
        try:
            result = response.json()
            print(f"   Resultado: {json.dumps(result, indent=2)[:500]}")
        except:
            print(f"   Response: {response.text[:500]}")
    elif response.status_code == 403:
        print(f"   ❌ Ainda recebendo 403")
        print(f"   Chrome local pode não estar funcionando corretamente")
        print(f"   Verifique:")
        print(f"     1. Chrome está instalado no container")
        print(f"     2. Skyvern está usando modo local")
        print(f"     3. Reinicie Skyvern com: SKYVERN_MODE=local skyvern run server --local")
    else:
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        
except Exception as e:
    print(f"   ❌ Erro: {e}")

print("\n✅ Teste concluído!")
print("\n📋 Próxima etapa:")
print(" Se todos os testes passaram, execute seu script:")
print(" python agno_clipping_skyvern.py")

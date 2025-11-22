#!/bin/bash

# Script para extrair sessão do Chrome e converter para formato compatível com Browserless/BrowserUSE

set -e

CHROME_PROFILE_DIR="${CHROME_PROFILE_DIR:-$HOME/.config/google-chrome}"
OUTPUT_DIR="${OUTPUT_DIR:-./browser_session}"
COOKIES_FILE="${OUTPUT_DIR}/cookies.json"
STORAGE_STATE_FILE="${OUTPUT_DIR}/storage_state.json"

echo "🍪 Extraindo sessão do Chrome..."
echo "=================================="
echo ""

# Criar diretório de saída
mkdir -p "$OUTPUT_DIR"

# Verificar se o Chrome está instalado
if ! command -v google-chrome >/dev/null 2>&1 && ! command -v chromium >/dev/null 2>&1; then
    echo "❌ Chrome/Chromium não encontrado"
    exit 1
fi

# Verificar se o perfil existe
if [ ! -d "$CHROME_PROFILE_DIR" ]; then
    echo "❌ Perfil do Chrome não encontrado em: $CHROME_PROFILE_DIR"
    echo "💡 Dica: Defina CHROME_PROFILE_DIR com o caminho do seu perfil"
    exit 1
fi

echo "📂 Perfil do Chrome: $CHROME_PROFILE_DIR"
echo "📂 Diretório de saída: $OUTPUT_DIR"
echo ""

# Usar Python para extrair cookies do banco SQLite do Chrome
python3 << 'PYTHON_SCRIPT'
import json
import sqlite3
import os
from pathlib import Path

chrome_profile = os.environ.get('CHROME_PROFILE_DIR', os.path.expanduser('~/.config/google-chrome'))
output_dir = os.environ.get('OUTPUT_DIR', './browser_session')
cookies_db = os.path.join(chrome_profile, 'Default', 'Cookies')
storage_state_file = os.path.join(output_dir, 'storage_state.json')

# Encontrar o banco de cookies (pode estar em diferentes locais)
possible_paths = [
    os.path.join(chrome_profile, 'Default', 'Cookies'),
    os.path.join(chrome_profile, 'Profile 1', 'Cookies'),
    os.path.join(chrome_profile, 'Profile 2', 'Cookies'),
]

cookies_db_path = None
for path in possible_paths:
    if os.path.exists(path):
        cookies_db_path = path
        break

if not cookies_db_path:
    print(f"❌ Banco de cookies não encontrado. Procurou em: {possible_paths}")
    exit(1)

print(f"📦 Banco de cookies encontrado: {cookies_db_path}")

# Copiar banco temporariamente (Chrome pode ter lock)
import shutil
import tempfile
temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
shutil.copy2(cookies_db_path, temp_db.name)

try:
    conn = sqlite3.connect(temp_db.name)
    cursor = conn.cursor()
    
    # Query para extrair cookies
    cursor.execute("""
        SELECT 
            host_key,
            name,
            value,
            path,
            expires_utc,
            is_secure,
            is_httponly,
            same_site,
            priority
        FROM cookies
        WHERE host_key LIKE '%automotivebusiness.com.br%' 
           OR host_key LIKE '%google%'
           OR host_key LIKE '%gstatic%'
           OR host_key LIKE '%recaptcha%'
        ORDER BY host_key
    """)
    
    cookies = []
    for row in cursor.fetchall():
        host_key, name, value, path, expires_utc, is_secure, is_httponly, same_site, priority = row
        
        # Converter expires_utc (Chrome usa epoch em microsegundos desde 1601)
        # Converter para timestamp Unix
        if expires_utc and expires_utc > 0:
            # Chrome epoch: 1601-01-01
            chrome_epoch = 11644473600000000
            unix_timestamp = (expires_utc - chrome_epoch) / 1000000
        else:
            unix_timestamp = None
        
        cookie = {
            "name": name,
            "value": value,
            "domain": host_key,
            "path": path or "/",
            "expires": unix_timestamp if unix_timestamp and unix_timestamp > 0 else -1,
            "httpOnly": bool(is_httponly),
            "secure": bool(is_secure),
            "sameSite": "Lax" if same_site == 1 else "Strict" if same_site == 2 else "None"
        }
        cookies.append(cookie)
    
    conn.close()
    
    # Criar storage_state no formato Playwright/BrowserUSE
    storage_state = {
        "cookies": cookies,
        "origins": []
    }
    
    # Salvar storage_state.json
    os.makedirs(output_dir, exist_ok=True)
    with open(storage_state_file, 'w') as f:
        json.dump(storage_state, f, indent=2)
    
    print(f"✅ {len(cookies)} cookies extraídos")
    print(f"✅ Storage state salvo em: {storage_state_file}")
    print(f"")
    print(f"📋 Domínios encontrados:")
    domains = set(cookie["domain"] for cookie in cookies)
    for domain in sorted(domains):
        count = sum(1 for c in cookies if c["domain"] == domain)
        print(f"   - {domain}: {count} cookies")
    
finally:
    os.unlink(temp_db.name)

PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Sessão extraída com sucesso!"
    echo ""
    echo "📝 Próximos passos:"
    echo "   1. O arquivo storage_state.json foi criado em: $OUTPUT_DIR"
    echo "   2. Este arquivo será usado automaticamente pelo BrowserAgent"
    echo "   3. Reinicie o worker: sudo docker-compose restart agno_worker"
    echo ""
else
    echo "❌ Erro ao extrair sessão"
    exit 1
fi


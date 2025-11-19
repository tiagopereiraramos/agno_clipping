#!/bin/bash

echo "🔍 Validando estrutura do projeto..."
echo ""

ERROS=0

# Validar sintaxe Python
echo "📝 Validando arquivos Python..."
for arquivo in worker/main.py scheduler/main.py api/main.py; do
    if python3 -m py_compile "$arquivo" 2>/dev/null; then
        echo "  ✓ $arquivo"
    else
        echo "  ✗ $arquivo - Erro de sintaxe"
        ERROS=$((ERROS + 1))
    fi
done

# Validar docker-compose
echo ""
echo "🐳 Validando docker-compose.yml..."
if docker-compose config --quiet 2>/dev/null; then
    echo "  ✓ docker-compose.yml válido"
else
    echo "  ✗ docker-compose.yml - Erro de sintaxe"
    ERROS=$((ERROS + 1))
fi

# Validar YAMLs
echo ""
echo "📋 Validando arquivos YAML..."
for arquivo in config/loki-config.yaml config/promtail-config.yaml config/grafana/provisioning/datasources/datasources.yaml; do
    if python3 -c "import yaml; yaml.safe_load(open('$arquivo'))" 2>/dev/null; then
        echo "  ✓ $arquivo"
    else
        echo "  ✗ $arquivo - Erro de sintaxe"
        ERROS=$((ERROS + 1))
    fi
done

# Validar JSON
echo ""
echo "📄 Validando arquivos JSON..."
if python3 -c "import json; json.load(open('config/grafana/provisioning/dashboards/clippings-dashboard.json'))" 2>/dev/null; then
    echo "  ✓ clippings-dashboard.json"
else
    echo "  ✗ clippings-dashboard.json - Erro de sintaxe"
    ERROS=$((ERROS + 1))
fi

# Validar scripts bash
echo ""
echo "🔧 Validando scripts bash..."
for script in scripts/*.sh; do
    if bash -n "$script" 2>/dev/null; then
        echo "  ✓ $(basename $script)"
    else
        echo "  ✗ $(basename $script) - Erro de sintaxe"
        ERROS=$((ERROS + 1))
    fi
done

# Verificar estrutura de diretórios
echo ""
echo "📁 Verificando estrutura de diretórios..."
DIRETORIOS=("api" "worker" "scheduler" "config" "scripts" "logs" "workspace")
for dir in "${DIRETORIOS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir/"
    else
        echo "  ✗ $dir/ - Diretório não encontrado"
        ERROS=$((ERROS + 1))
    fi
done

# Verificar arquivos essenciais
echo ""
echo "📄 Verificando arquivos essenciais..."
ARQUIVOS=("docker-compose.yml" "requirements.txt" "init-db.sql" "Dockerfile.worker" "Dockerfile.scheduler" "Dockerfile.api")
for arquivo in "${ARQUIVOS[@]}"; do
    if [ -f "$arquivo" ]; then
        echo "  ✓ $arquivo"
    else
        echo "  ✗ $arquivo - Arquivo não encontrado"
        ERROS=$((ERROS + 1))
    fi
done

# Verificar .env
echo ""
if [ -f ".env" ]; then
    echo "  ✓ .env encontrado"
else
    echo "  ⚠ .env não encontrado (criar a partir de .env.example)"
fi

echo ""
if [ $ERROS -eq 0 ]; then
    echo "✅ Validação concluída sem erros!"
    exit 0
else
    echo "❌ Validação encontrou $ERROS erro(s)"
    exit 1
fi


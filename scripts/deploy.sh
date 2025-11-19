#!/bin/bash

set -e

echo "🚀 Iniciando deploy da stack Clippings Agno v3.1..."

# Verificar .env
if [ ! -f .env ]; then
    echo "❌ Arquivo .env não encontrado!"
    echo "📋 Copie .env.example para .env e configure os valores"
    exit 1
fi

# Load env
source .env

# Criar diretorios necessários
mkdir -p logs config/grafana/provisioning/{datasources,dashboards} workspace

# Build images
echo "🔨 Building custom images..."
docker-compose build

# Subir stack
echo "📦 Bringing up stack..."
docker-compose up -d

# Aguardar serviços
echo "⏳ Aguardando serviços..."
sleep 30

# Health check
echo "🏥 Verificando saúde dos serviços..."
docker-compose ps

echo ""
echo "✅ Stack iniciado com sucesso!"
echo ""
echo "🌐 Acesso aos serviços:"
echo "   Portainer: http://localhost:9000"
echo "   RabbitMQ:  http://localhost:15672 (admin/admin123)"
echo "   Grafana:   http://localhost:3000 (admin/admin123)"
echo "   Browserless: http://localhost:3001"
echo "   API Docs:  http://localhost:8000/docs"
echo ""


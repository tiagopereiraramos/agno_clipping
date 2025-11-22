#!/bin/bash

# Script para monitorar job em tempo real com logs formatados

set -e

JOB_ID=${1:-""}

echo "🔍 Monitoramento de Job - Agno Clipping"
echo "========================================"
echo ""
echo "📺 Acompanhe visualmente em: http://localhost:3001/"
echo "   - Clique no botão 'Sessions' (ícone de ondas) na barra lateral"
echo "   - Você verá as sessões ativas do Browserless em tempo real"
echo ""

if [ -z "$JOB_ID" ]; then
    echo "📊 Último job:"
    cd /home/ubuntu/apps/agno_agent/agno_clipping
    JOB_ID=$(sudo docker-compose exec -T postgres psql -U clippings_user -d clippings_db -t -c "SELECT job_id FROM clippings_app.clipping_jobs ORDER BY created_at DESC LIMIT 1;" | tr -d ' ')
    if [ -z "$JOB_ID" ]; then
        echo "❌ Nenhum job encontrado"
        exit 1
    fi
    echo "   Job ID: $JOB_ID"
    echo ""
fi

echo "📋 Monitorando logs em tempo real..."
echo "   Pressione Ctrl+C para parar"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd /home/ubuntu/apps/agno_agent/agno_clipping

# Monitorar logs com filtros para mostrar informações relevantes
sudo docker-compose logs -f --tail=50 agno_worker 2>&1 | \
    grep --line-buffered -E "(🧠|⚡|💭|🚀|✅|⏱️|🍪|🔌|🌐|📋|🔗|👀|reasoning|acao|memoria|inicio|Step [0-9]+:|BrowserUSE|navegacao|Job.*processado|File Agent|Notification Agent|email|SMTP|enviado|completado|sucesso|erro)" | \
    sed -u 's/^[^|]*| //' | \
    sed -u 's/INFO.*\[\([^]]*\)\]/\1/' | \
    awk '{print "\033[36m" strftime("%H:%M:%S") "\033[0m", $0}'


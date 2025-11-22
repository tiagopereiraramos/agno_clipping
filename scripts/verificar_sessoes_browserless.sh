#!/bin/bash

# Script para verificar sessões ativas no Browserless

echo "🔍 Verificando Sessões no Browserless"
echo "======================================"
echo ""

# Verificar se o Browserless está acessível
if ! curl -s http://localhost:3001/health > /dev/null 2>&1; then
    echo "❌ Browserless não está acessível em http://localhost:3001/"
    exit 1
fi

echo "✅ Browserless está acessível"
echo ""

# Tentar obter sessões via API REST (sessões criadas via API)
echo "📊 Sessões via API REST (/sessions):"
SESSIONS_REST=$(curl -s http://localhost:3001/sessions 2>/dev/null)
if [ -z "$SESSIONS_REST" ] || [ "$SESSIONS_REST" = "[]" ]; then
    echo "   ℹ️  Nenhuma sessão via API REST (esperado - browser-use usa CDP direto)"
else
    echo "$SESSIONS_REST" | python3 -m json.tool 2>/dev/null || echo "$SESSIONS_REST"
fi
echo ""

# Tentar obter sessões via CDP (sessões CDP ativas)
echo "📊 Sessões via CDP (/json):"
SESSIONS_CDP=$(curl -s http://localhost:3001/json 2>/dev/null)
if [ -z "$SESSIONS_CDP" ] || [ "$SESSIONS_CDP" = "[]" ]; then
    echo "   ℹ️  Nenhuma sessão CDP ativa no momento"
else
    echo "$SESSIONS_CDP" | python3 -m json.tool 2>/dev/null | head -30 || echo "$SESSIONS_CDP" | head -10
fi
echo ""

# Verificar processos do Chrome no Browserless
echo "🔍 Processos do Chrome no container Browserless:"
sudo docker-compose exec -T browserless ps aux | grep -E "(chrome|chromium)" | grep -v grep | head -5 || echo "   ℹ️  Nenhum processo Chrome encontrado"
echo ""

# Verificar logs recentes
echo "📋 Últimas conexões nos logs do Browserless:"
sudo docker-compose logs --tail=50 browserless 2>&1 | grep -E "(session|Session|connected|CDP|WebSocket)" | tail -10 || echo "   ℹ️  Nenhuma conexão recente nos logs"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "ℹ️  NOTA IMPORTANTE:"
echo "   O browser-use conecta diretamente via CDP (Chrome DevTools Protocol),"
echo "   não via API REST do Browserless. Por isso, as sessões podem não aparecer"
echo "   na UI do Browserless (que mostra apenas sessões criadas via API REST)."
echo ""
echo "✅ Para acompanhar o que está acontecendo:"
echo "   1. Use os logs do worker: ./scripts/monitorar_job.sh"
echo "   2. Verifique os logs do Browserless: sudo docker-compose logs -f browserless"
echo "   3. Execute este script durante um job ativo para ver sessões CDP"
echo ""


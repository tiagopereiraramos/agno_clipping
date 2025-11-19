#!/bin/bash

echo "🏥 Verificando saúde da stack..."
echo ""

# PostgreSQL
echo -n "PostgreSQL: "
if nc -z localhost 5432 2>/dev/null; then
    echo "✅ OK"
else
    echo "❌ DOWN"
fi

# RabbitMQ
echo -n "RabbitMQ AMQP: "
if nc -z localhost 5672 2>/dev/null; then
    echo "✅ OK"
else
    echo "❌ DOWN"
fi

# RabbitMQ Management
echo -n "RabbitMQ Management UI: "
if curl -s http://localhost:15672 > /dev/null; then
    echo "✅ OK"
else
    echo "❌ DOWN"
fi

# Grafana
echo -n "Grafana: "
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ OK"
else
    echo "❌ DOWN"
fi

# Loki
echo -n "Loki: "
if curl -s http://localhost:3100/loki/api/v1/status > /dev/null; then
    echo "✅ OK"
else
    echo "❌ DOWN"
fi

# Browserless
echo -n "Browserless: "
if curl -s http://localhost:3001/health > /dev/null; then
    echo "✅ OK"
else
    echo "❌ DOWN"
fi

# API
echo -n "API: "
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ OK"
else
    echo "❌ DOWN"
fi

echo ""
echo "🎯 Container Status:"
docker-compose ps


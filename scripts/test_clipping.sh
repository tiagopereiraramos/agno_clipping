#!/bin/bash

# Script para testar clipping enviando mensagem para a fila RabbitMQ

RABBITMQ_HOST=${RABBITMQ_HOST:-localhost}
RABBITMQ_PORT=${RABBITMQ_PORT:-5672}
RABBITMQ_USER=${RABBITMQ_USER:-admin}
RABBITMQ_PASSWORD=${RABBITMQ_PASSWORD:-admin123}

# Prompt de teste para coletar informações sobre produtos LEAR
PROMPT="Coletar todas as informações disponíveis sobre produtos da empresa LEAR no site https://www.automotivebusiness.com.br/. Incluir artigos, notícias, releases e qualquer conteúdo relacionado à LEAR. Extrair título, data de publicação, autor, URL completa e conteúdo principal de cada item encontrado."

echo "🚀 Enviando job de clipping para a fila..."
echo ""
echo "📋 Prompt:"
echo "$PROMPT"
echo ""

# Instalar python3 e pika se necessário
python3 << EOF
import pika
import json
import sys

try:
    # Conectar ao RabbitMQ
    credentials = pika.PlainCredentials('${RABBITMQ_USER}', '${RABBITMQ_PASSWORD}')
    parameters = pika.ConnectionParameters(
        host='${RABBITMQ_HOST}',
        port=${RABBITMQ_PORT},
        credentials=credentials
    )
    
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    # Declarar fila
    channel.queue_declare(queue='clippings.jobs', durable=True)
    
    # Criar mensagem
    mensagem = {
        "instruction": "${PROMPT}",
        "parameters": {
            "site": "https://www.automotivebusiness.com.br/",
            "cliente": "LEAR",
            "tipo_busca": "produtos",
            "extrair_imagens": False,
            "extrair_links": True,
            "formato": "both"
        }
    }
    
    # Enviar mensagem
    channel.basic_publish(
        exchange='',
        routing_key='clippings.jobs',
        body=json.dumps(mensagem),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Tornar mensagem persistente
        )
    )
    
    print("✅ Mensagem enviada com sucesso!")
    print(f"📝 Job ID será gerado automaticamente pelo worker")
    print("")
    print("🔍 Para acompanhar o processamento:")
    print("   ./scripts/logs.sh worker")
    print("")
    
    connection.close()
    
except Exception as e:
    print(f"❌ Erro ao enviar mensagem: {e}")
    sys.exit(1)
EOF


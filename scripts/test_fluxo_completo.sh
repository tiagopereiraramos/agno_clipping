#!/bin/bash

# Script para testar o fluxo completo de clipping
# Inclui: LLM -> Browser -> File (MinIO) -> Notification (SMTP)

set -e

RABBITMQ_HOST=${RABBITMQ_HOST:-localhost}
RABBITMQ_PORT=${RABBITMQ_PORT:-5672}
RABBITMQ_USER=${RABBITMQ_USER:-admin}
RABBITMQ_PASSWORD=${RABBITMQ_PASSWORD:-admin123}

echo "🚀 TESTE DE FLUXO COMPLETO - Agno Clipping"
echo "=========================================="
echo ""

# Prompt de teste para LEAR no Automotive Business
PROMPT=$(cat <<'PROMPT_EOF'
Você é um analista de clipping automotivo que opera 100% de forma autônoma. Siga exatamente este plano:
1. Abra https://www.automotivebusiness.com.br/ e identifique o campo de busca 'Buscar'.
2. Pesquise, na ordem, pelos termos: 'Lear', 'Lear Corporation', 'Lear do Brasil'. Para cada termo, percorra as páginas de resultados até encontrar pelo menos 3 notícias únicas.
3. Para cada notícia encontrada: abra o link, extraia título, data, autor (se houver), URL completa, resumo em até 4 frases e destaque se menciona produtos ou contratos.
4. Caso não encontre 3 notícias após esgotar os termos, registre que não há cobertura recente, detalhando quais buscas foram feitas.
5. Monte um sumário executivo destacando insights principais para o time comercial.
Devolva a lista de notícias (mínimo 3 itens) + o sumário executivo.
PROMPT_EOF
)

echo "📋 Prompt de Teste:"
echo "$PROMPT"
echo ""
echo "🔄 Fluxo esperado:"
echo "  1. Mensagem enviada para fila RabbitMQ"
echo "  2. Worker consome mensagem"
echo "  3. LLM (OpenAI) interpreta instrução e extrai URL"
echo "  4. Browser Agent navega no site usando Browserless"
echo "  5. Conteúdo extraído e processado"
echo "  6. File Agent salva JSON e Markdown no MinIO"
echo "  7. Resultado salvo no PostgreSQL"
echo "  8. Notification Agent envia email via SMTP"
echo ""

# Verificar se serviços estão rodando
echo "🔍 Verificando serviços..."
if ! nc -z $RABBITMQ_HOST $RABBITMQ_PORT 2>/dev/null; then
    echo "❌ RabbitMQ não está acessível em $RABBITMQ_HOST:$RABBITMQ_PORT"
    echo "   Execute: sudo docker-compose up -d rabbitmq"
    exit 1
fi
echo "✅ RabbitMQ acessível"

# Determinar onde executar o publicador Python (host ou container)
USE_WORKER_PY=false
if command -v docker-compose >/dev/null 2>&1; then
    if sudo docker-compose ps agno_worker >/dev/null 2>&1; then
        USE_WORKER_PY=true
    fi
fi
RABBIT_TARGET_HOST=$RABBITMQ_HOST
if [ "$USE_WORKER_PY" = true ]; then
    RABBIT_TARGET_HOST="rabbitmq"
fi

# Enviar mensagem
echo ""
echo "📨 Enviando mensagem para a fila..."

PYTHON_SNIPPET=$(cat <<EOF
import pika
import json
import sys
from datetime import datetime

try:
    credentials = pika.PlainCredentials('${RABBITMQ_USER}', '${RABBITMQ_PASSWORD}')
    parameters = pika.ConnectionParameters(
        host='${RABBIT_TARGET_HOST}',
        port=${RABBITMQ_PORT},
        credentials=credentials
    )

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue='clippings.jobs', durable=True)

    # Tentar carregar parâmetros do arquivo de configuração
    import os
    params_file = "/app/config/clipping_params.json"
    if os.path.exists(params_file):
        with open(params_file, 'r', encoding='utf-8') as f:
            params_config = json.load(f)
    else:
        # Parâmetros padrão
        params_config = {
            "cliente": "LEAR",
            "periodo": "últimos 7 dias",
            "max_itens": 10,
            "min_noticias": 3,
            "url": "https://www.automotivebusiness.com.br/",
            "palavras_chave": ["Lear", "Lear Corporation", "Lear do Brasil"],
            "extrair_imagens": False,
            "extrair_links": True,
            "formato": "both",
            "notificar": True
        }
    
    mensagem = {
        "instruction": """${PROMPT}""",
        "parameters": {
            "site": params_config.get("url", "https://www.automotivebusiness.com.br/"),
            "cliente": params_config.get("cliente", "LEAR"),
            "periodo": params_config.get("periodo", "últimos 7 dias"),
            "max_itens": params_config.get("max_itens", 10),
            "palavras_chave": params_config.get("palavras_chave", ["Lear", "Lear Corporation", "Lear do Brasil"]),
            "estrategia_busca": "abrir página inicial, identificar campo 'Buscar', pesquisar termos na ordem indicada e percorrer resultados até reunir 3 notícias",
            "min_noticias": params_config.get("min_noticias", 3),
            "extrair_imagens": params_config.get("extrair_imagens", False),
            "extrair_links": params_config.get("extrair_links", True),
            "formato": params_config.get("formato", "both"),
            "notificar": params_config.get("notificar", True)
        },
        "timestamp": datetime.now().isoformat()
    }

    channel.basic_publish(
        exchange='',
        routing_key='clippings.jobs',
        body=json.dumps(mensagem, ensure_ascii=False),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type='application/json'
        )
    )

    print("✅ Mensagem enviada com sucesso!")
    print("")
    print("📊 Para acompanhar o processamento:")
    print("   ./scripts/logs.sh worker")
    print("")
    print("🗄️  Para verificar resultados no banco:")
    print("   sudo docker-compose exec postgres psql -U clippings_user -d clippings_db -c \"SELECT job_id, status, created_at FROM clippings_app.clipping_jobs ORDER BY created_at DESC LIMIT 5;\"")
    print("")
    print("📦 Para verificar arquivos no MinIO:")
    print("   Acesse: http://localhost:9001 (minioadmin/minioadmin)")
    print("   Bucket: clippings")
    print("")
    print("📧 Email será enviado se SMTP estiver configurado no .env")

    connection.close()

except Exception as e:
    print(f"❌ Erro ao enviar mensagem: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF
)

if [ "$USE_WORKER_PY" = true ]; then
    printf "%s\n" "$PYTHON_SNIPPET" | sudo docker-compose exec -T agno_worker python -
else
    printf "%s\n" "$PYTHON_SNIPPET" | python3 -
fi

echo ""
echo "✅ Teste iniciado!"
echo ""
echo "⏳ Aguarde o processamento completo..."
echo "   O job será processado pelo worker em background"


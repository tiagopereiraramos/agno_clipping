#!/bin/bash

# Script para verificar resultados do processamento

JOB_ID=${1:-""}

echo "🔍 Verificando Resultados do Clipping"
echo "======================================"
echo ""

if [ -z "$JOB_ID" ]; then
    echo "📊 Últimos 5 jobs processados:"
    echo ""
    sudo docker-compose exec -T postgres psql -U clippings_user -d clippings_db << EOF
SELECT 
    job_id,
    status,
    LEFT(instruction, 50) as instrucao_preview,
    created_at,
    completed_at
FROM clippings_app.clipping_jobs
ORDER BY created_at DESC
LIMIT 5;
EOF
    echo ""
    echo "💡 Para ver detalhes de um job específico:"
    echo "   ./scripts/verificar_resultado.sh <job_id>"
else
    echo "📋 Detalhes do Job: $JOB_ID"
    echo ""
    
    # Informações do job
    echo "📝 Status do Job:"
    sudo docker-compose exec -T postgres psql -U clippings_user -d clippings_db << EOF
SELECT 
    job_id,
    status,
    instruction,
    error_message,
    created_at,
    started_at,
    completed_at
FROM clippings_app.clipping_jobs
WHERE job_id = '$JOB_ID';
EOF
    
    echo ""
    echo "📄 Resultados do Clipping:"
    sudo docker-compose exec -T postgres psql -U clippings_user -d clippings_db << EOF
SELECT 
    id,
    title,
    url,
    LEFT(content, 100) as conteudo_preview,
    s3_uri_json,
    s3_uri_markdown,
    created_at
FROM clippings_app.clipping_results
WHERE job_id = '$JOB_ID';
EOF
    
    echo ""
    echo "📧 Notificações Enviadas:"
    sudo docker-compose exec -T postgres psql -U clippings_user -d clippings_db << EOF
SELECT 
    channel,
    recipient,
    status,
    error_message,
    timestamp
FROM clippings_app.notification_logs
WHERE job_id = '$JOB_ID';
EOF
fi

echo ""
echo "📦 Para verificar arquivos no MinIO:"
echo "   Acesse: http://localhost:9001"
echo "   Credenciais: minioadmin/minioadmin"
echo "   Bucket: clippings"


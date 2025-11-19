#!/bin/bash

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p $BACKUP_DIR

echo "💾 Iniciando backup..."

# PostgreSQL Backup
echo "📊 Backing up PostgreSQL..."
docker-compose exec -T postgres pg_dump -U clippings_user clippings_db > $BACKUP_DIR/postgres_$TIMESTAMP.sql

# RabbitMQ Definitions
echo "📨 Backing up RabbitMQ definitions..."
docker-compose exec -T rabbitmq rabbitmqctl export_definitions /tmp/rabbitmq_definitions.json
docker cp clippings_rabbitmq:/tmp/rabbitmq_definitions.json $BACKUP_DIR/rabbitmq_$TIMESTAMP.json

# Volumes
echo "💿 Compressing volumes..."
tar -czf $BACKUP_DIR/volumes_$TIMESTAMP.tar.gz \
    -C . postgres_data rabbitmq_data grafana_data 2>/dev/null || true

echo "✅ Backup completado: $BACKUP_DIR/"
ls -lah $BACKUP_DIR/


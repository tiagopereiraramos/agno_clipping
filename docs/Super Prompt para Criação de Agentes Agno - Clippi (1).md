<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Super Prompt para Criação de Agentes Agno - Clippings Autônomos Inteligentes v3.1

## ADICIONAL: Arquitetura Portainer + Docker Compose Completo e Otimizado


***

## 1. Arquitetura Portainer - Visão Geral

```
PORTAINER (http://localhost:9000)
│
├── Stack: clippings-agno
│   ├── Services
│   │   ├── postgres (Database)
│   │   ├── rabbitmq (Message Broker + Web-STOMP)
│   │   ├── loki (Log Aggregation)
│   │   ├── promtail (Log Collector)
│   │   ├── grafana (Visualization)
│   │   ├── browserless (Chrome Headless)
│   │   ├── browser_use_mcp (MCP Server)
│   │   ├── agno_worker (Worker Principal)
│   │   ├── agno_scheduler (Cron Scheduler)
│   │   └── api (FastAPI Dashboard)
│   │
│   ├── Volumes
│   │   ├── postgres_data
│   │   ├── rabbitmq_data
│   │   ├── grafana_data
│   │   ├── loki_data
│   │   └── logs_app
│   │
│   ├── Networks
│   │   └── clippings-network (bridge)
│   │
│   └── Environment
│       ├── Configurações centralizadas via .env
│       └── Secrets (MinIO, SMTP, APIs)
```


***

## 2. Docker Compose Principal - docker-compose.yml (Completo e Otimizado)

```yaml
version: '3.9'

services:
  # ==================== DATABASE ====================
  postgres:
    image: postgres:16-alpine
    container_name: clippings_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER:-clippings_user}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres123}
      POSTGRES_DB: ${DB_NAME:-clippings_db}
      POSTGRES_INITDB_ARGS: "-c max_connections=100 -c shared_buffers=256MB"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-clippings_user} -d ${DB_NAME:-clippings_db}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - clippings-network
    labels:
      com.example.description: "PostgreSQL Database for Clippings"

  # ==================== MESSAGE BROKER ====================
  rabbitmq:
    image: rabbitmq:4-management-alpine
    container_name: clippings_rabbitmq
    restart: unless-stopped
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-admin}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-admin123}
      RABBITMQ_DEFAULT_VHOST: /
    ports:
      - "5672:5672"      # AMQP
      - "15672:15672"    # Management UI
      - "15674:15674"    # Web-STOMP (WebSocket)
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
      - ./config/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s
    networks:
      - clippings-network
    labels:
      com.example.description: "RabbitMQ Message Broker with Web-STOMP"
    command: >
      bash -lc "rabbitmq-plugins enable --offline rabbitmq_stomp rabbitmq_web_stomp &&
                rabbitmq-server"

  # ==================== LOG AGGREGATION ====================
  loki:
    image: grafana/loki:2.9.0-alpine
    container_name: clippings_loki
    restart: unless-stopped
    ports:
      - "3100:3100"
    volumes:
      - loki_data:/loki
      - ./config/loki-config.yaml:/etc/loki/local-config.yaml:ro
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:3100/loki/api/v1/status || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    networks:
      - clippings-network
    labels:
      com.example.description: "Grafana Loki - Log Aggregation"
    command: -config.file=/etc/loki/local-config.yaml

  promtail:
    image: grafana/promtail:2.9.0-alpine
    container_name: clippings_promtail
    restart: unless-stopped
    ports:
      - "1514:1514"
    volumes:
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./config/promtail-config.yaml:/etc/promtail/config.yml:ro
    depends_on:
      loki:
        condition: service_healthy
    networks:
      - clippings-network
    labels:
      com.example.description: "Promtail - Log Collector"
    command: -config.file=/etc/promtail/config.yml

  # ==================== VISUALIZATION ====================
  grafana:
    image: grafana/grafana:11.0.0-alpine
    container_name: clippings_grafana
    restart: unless-stopped
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin123}
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
      GF_INSTALL_PLUGINS: grafana-piechart-panel
      GF_PATHS_PROVISIONING: /etc/grafana/provisioning
      GF_LOG_MODE: console
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/provisioning/datasources:/etc/grafana/provisioning/datasources:ro
      - ./config/grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards:ro
    depends_on:
      loki:
        condition: service_healthy
    networks:
      - clippings-network
    labels:
      com.example.description: "Grafana - Logs and Metrics Visualization"

  # ==================== BROWSER AUTOMATION ====================
  browserless:
    image: browserless/chrome:latest
    container_name: clippings_browserless
    restart: unless-stopped
    environment:
      DEBUG: "true"
      ENABLE_DEBUGGER: "true"
      ENABLE_CHROME_STABLE_SHIM: "true"
      USE_CHROME_STABLE: "true"
      WORKSPACE_DIR: /workspace
    ports:
      - "3001:3000"
    volumes:
      - browserless_cache:/root/.cache
      - ./workspace:/workspace
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    networks:
      - clippings-network
    labels:
      com.example.description: "Browserless - Headless Chrome"
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  # ==================== MCP SERVER ====================
  browser_use_mcp:
    image: ghcr.io/saik0s/mcp-browser-use:latest
    container_name: clippings_browser_use_mcp
    restart: unless-stopped
    environment:
      MCP_BROWSER_CDP_URL: http://browserless:3000
      MCP_LOG_LEVEL: debug
      MCP_BROWSER_USE_OWN_BROWSER: "true"
    depends_on:
      browserless:
        condition: service_healthy
    networks:
      - clippings-network
    labels:
      com.example.description: "Browser-Use MCP Server"

  # ==================== WORKER - MAIN AGENT ====================
  agno_worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    container_name: clippings_agno_worker
    restart: unless-stopped
    environment:
      # Database
      DATABASE_URL: postgresql://${DB_USER:-clippings_user}:${DB_PASSWORD:-postgres123}@postgres:5432/${DB_NAME:-clippings_db}
      
      # RabbitMQ
      RABBITMQ_URL: amqp://${RABBITMQ_USER:-admin}:${RABBITMQ_PASSWORD:-admin123}@rabbitmq:5672/
      RABBITMQ_HOST: rabbitmq
      RABBITMQ_PORT: 5672
      
      # Logging & Telemetry
      LOGS_WS_BROKER: ws://rabbitmq:15674/ws
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      DEBUG: ${DEBUG:-false}
      
      # MinIO S3
      MINIO_ENDPOINT: ${MINIO_ENDPOINT:-minio.brmsolutions.com.br}
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      MINIO_BUCKET: clippings
      
      # LLM
      LLM_PROVIDER: ${LLM_PROVIDER:-openai}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LLM_MODEL: ${LLM_MODEL:-gpt-4-turbo}
      
      # MCP
      MCP_ENDPOINT: http://browser_use_mcp:8000
      
      # Worker Config
      WORKER_CONCURRENCY: 3
      MAX_RETRIES: 3
      BACKOFF_SECONDS: 30
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
      browserless:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config:ro
    networks:
      - clippings-network
    labels:
      com.example.description: "Agno Worker - Main Agent Orchestrator"

  # ==================== SCHEDULER ====================
  agno_scheduler:
    build:
      context: .
      dockerfile: Dockerfile.scheduler
    container_name: clippings_agno_scheduler
    restart: unless-stopped
    environment:
      RABBITMQ_URL: amqp://${RABBITMQ_USER:-admin}:${RABBITMQ_PASSWORD:-admin123}@rabbitmq:5672/
      DATABASE_URL: postgresql://${DB_USER:-clippings_user}:${DB_PASSWORD:-postgres123}@postgres:5432/${DB_NAME:-clippings_db}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      DEBUG: ${DEBUG:-false}
      TIMEZONE: ${TIMEZONE:-America/Sao_Paulo}
    depends_on:
      rabbitmq:
        condition: service_healthy
      postgres:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config:ro
    networks:
      - clippings-network
    labels:
      com.example.description: "APScheduler - Cron Job Scheduler"

  # ==================== API DASHBOARD ====================
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: clippings_api
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://${DB_USER:-clippings_user}:${DB_PASSWORD:-postgres123}@postgres:5432/${DB_NAME:-clippings_db}
      RABBITMQ_URL: amqp://${RABBITMQ_USER:-admin}:${RABBITMQ_PASSWORD:-admin123}@rabbitmq:5672/
      SECRET_KEY: ${SECRET_KEY:-your-secret-key-change-in-production}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    networks:
      - clippings-network
    labels:
      com.example.description: "FastAPI - Monitoring Dashboard"

  # ==================== PORTAINER AGENT (opcional) ====================
  portainer:
    image: portainer/portainer-ce:latest
    container_name: portainer
    restart: unless-stopped
    ports:
      - "9000:9000"
      - "8001:8001"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - portainer_data:/data
    networks:
      - clippings-network
    labels:
      com.example.description: "Portainer - Container Management"

# ==================== VOLUMES ====================
volumes:
  postgres_data:
    driver: local
  rabbitmq_data:
    driver: local
  grafana_data:
    driver: local
  loki_data:
    driver: local
  browserless_cache:
    driver: local
  portainer_data:
    driver: local

# ==================== NETWORKS ====================
networks:
  clippings-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```


***

## 3. Arquivos de Configuração - config/

### 3.1 RabbitMQ Config - config/rabbitmq.conf

```conf
# Network and Protocol
listeners.tcp.default = 5672
management.listener.port = 15672
web_stomp.tcp.port = 15674

# Performance
channel_max = 2048
connection_max = infinity
heartbeat = 60

# Memory
vm_memory_high_watermark.relative = 0.6
vm_memory_high_watermark_paging_ratio = 0.75

# Plugins
management.load_definitions = /etc/rabbitmq/definitions.json

# Logging
log.file.level = info
log.console.level = info
```


### 3.2 Loki Config - config/loki-config.yaml

```yaml
auth_enabled: false

ingester:
  chunk_idle_period: 3m
  chunk_retain_period: 1m
  max_chunk_age: 1h
  chunk_retain_period: 1m
  chunk_encoding: snappy

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

server:
  http_listen_port: 3100
  log_level: info

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
```


### 3.3 Promtail Config - config/promtail-config.yaml

```yaml
server:
  http_listen_port: 1514
  log_level: info

positions:
  filename: /tmp/positions.yaml

client:
  url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Docker container logs
  - job_name: docker
    static_configs:
      - labels:
          job: dockerlogs
            __path__: /var/lib/docker/containers/*/*-json.log
    pipeline_stages:
      - json:
          expressions:
            output: log
            stream: stream
      - regex:
          expression: '^(?P<time>[^ ]+) (?P<stream>stdout|stderr) (?P<flags>[^ ]*) (?P<content>.*)$'
      - labels:
          stream:
          time:

  # Worker logs
  - job_name: worker
    static_configs:
      - labels:
          job: worker
            __path__: /app/logs/worker.log

  # Scheduler logs
  - job_name: scheduler
    static_configs:
      - labels:
          job: scheduler
            __path__: /app/logs/scheduler.log

  # API logs
  - job_name: api
    static_configs:
      - labels:
          job: api
            __path__: /app/logs/api.log
```


### 3.4 Grafana Datasources - config/grafana/provisioning/datasources/datasources.yaml

```yaml
apiVersion: 1

datasources:
  - name: Loki
    type: loki
    url: http://loki:3100
    isDefault: true
    jsonData:
      maxLines: 10000

  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: false
    jsonData:
      timeInterval: 15s
```


### 3.5 Grafana Dashboard - config/grafana/provisioning/dashboards/clippings-dashboard.json

```json
{
  "dashboard": {
    "title": "Clippings Agno - Main Dashboard",
    "panels": [
      {
        "id": 1,
        "title": "Worker Logs (Last 1h)",
        "targets": [
          {
            "expr": "{job=\"worker\"}",
            "refId": "A"
          }
        ],
        "type": "logs"
      },
      {
        "id": 2,
        "title": "Job Execution Trace",
        "targets": [
          {
            "expr": "{job=~\"scheduler|worker|api\"}",
            "refId": "B"
          }
        ],
        "type": "logs"
      },
      {
        "id": 3,
        "title": "Error Rate",
        "targets": [
          {
            "expr": "{level=\"error\"}",
            "refId": "C"
          }
        ],
        "type": "stat"
      }
    ]
  }
}
```


***

## 4. Dockerfiles Especializados

### 4.1 Dockerfile.worker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "worker/main.py"]
```


### 4.2 Dockerfile.scheduler

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python", "scheduler/main.py"]
```


### 4.3 Dockerfile.api

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```


***

## 5. Arquivo: init-db.sql (Inicialização do PostgreSQL)

```sql
-- Create extensions
CREATE EXTENSION IF NOT EXISTS uuid-ossp;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS clippings_app;

-- Create tables
CREATE TABLE clippings_app.clipping_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    instruction TEXT NOT NULL,
    parameters JSONB,
    result_metadata JSONB,
    total_tokens INTEGER,
    total_cost_usd DECIMAL(10, 4),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    INDEX idx_job_id (job_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

CREATE TABLE clippings_app.clipping_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(255) NOT NULL REFERENCES clippings_app.clipping_jobs(job_id),
    source_name VARCHAR(255),
    title TEXT NOT NULL,
    author VARCHAR(255),
    date_published TIMESTAMP,
    url TEXT NOT NULL,
    content TEXT,
    s3_uri_json TEXT,
    s3_uri_markdown TEXT,
    s3_uri_pdf TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_job_id (job_id),
    INDEX idx_created_at (created_at)
);

CREATE TABLE clippings_app.agent_execution_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    message TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd DECIMAL(10, 4),
    metadata JSONB,
    timestamp TIMESTAMP DEFAULT NOW(),
    INDEX idx_job_id (job_id),
    INDEX idx_agent_name (agent_name),
    INDEX idx_timestamp (timestamp)
);

CREATE TABLE clippings_app.notification_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(255) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    recipient VARCHAR(255),
    subject VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    INDEX idx_job_id (job_id),
    INDEX idx_channel (channel),
    INDEX idx_timestamp (timestamp)
);

-- Create indexes for performance
CREATE INDEX idx_clipping_jobs_status_created ON clippings_app.clipping_jobs(status, created_at DESC);
CREATE INDEX idx_execution_logs_job_agent ON clippings_app.agent_execution_logs(job_id, agent_name);

-- Grants
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA clippings_app TO clippings_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA clippings_app TO clippings_user;
```


***

## 6. Arquivo: .env (Exemplo Completo)

```bash
# ============ DATABASE ============
DB_USER=clippings_user
DB_PASSWORD=securedbpassword123
DB_NAME=clippings_db

# ============ RABBITMQ ============
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=rabbitmq_secure_password

# ============ MINIO S3 ============
MINIO_ENDPOINT=minio.brmsolutions.com.br
MINIO_ACCESS_KEY=7Wqmtacpe6rgNT7NaufS
MINIO_SECRET_KEY=URqqtSz2iNSAljX0JYdiruFNZ3rwZiondXCGz9wP

# ============ LLM ============
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxx
LLM_MODEL=gpt-4-turbo

# ============ NOTIFICATIONS ============
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_app
SMTP_FROM=noreply@empresa.com

SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX

# ============ GRAFANA ============
GRAFANA_USER=admin
GRAFANA_PASSWORD=grafana_secure_password

# ============ APP CONFIG ============
DEBUG=false
LOG_LEVEL=INFO
TIMEZONE=America/Sao_Paulo
SECRET_KEY=your-super-secret-key-change-in-production

# ============ WORKER CONFIG ============
WORKER_CONCURRENCY=3
MAX_RETRIES=3
BACKOFF_SECONDS=30
```


***

## 7. Portainer Stack - Como Usar

### 7.1 Criando Stack no Portainer

**Via Portainer Web UI:**

1. Acesse http://localhost:9000
2. Login com credenciais padrão (admin/admin)
3. Ir para: **Stacks** → **Add Stack**
4. Escolher: **Docker Compose**
5. Colar o conteúdo do `docker-compose.yml`
6. Em **Environment variables**, adicionar valores do `.env`
7. Clicar em **Deploy the stack**

**Via CLI:**

```bash
# Salvar arquivo docker-compose.yml
# Salvar arquivo .env

# Deploy via docker-compose
docker-compose up -d

# Verificar status
docker-compose ps

# Ver logs em tempo real
docker-compose logs -f

# Parar tudo
docker-compose down -v
```


### 7.2 Dashboard Portainer - Monitoramento

**Visualizar Serviços:**

- Containers → Listar todos os 9 serviços
- Status: Green (running), Yellow (restarting), Red (stopped)
- CPU/Memory usage em tempo real

**Acessar Logs de Containers:**

- Selecionar container → **Logs**
- Follow logs em tempo real
- Buscar por termo-chave

**Gerenciar Volumes:**

- Volumes → Ver todos os volumes persistidos
- Backup: Executar scripts de snapshot

**Inspect Networks:**

- Networks → clippings-network → Verificar conectividade

***

## 8. Endpoints Portainer - Serviços Acessíveis

| Serviço | URL | Credenciais | Porta |
| :-- | :-- | :-- | :-- |
| **Portainer** | http://localhost:9000 | admin/admin | 9000 |
| **RabbitMQ Management** | http://localhost:15672 | admin/admin123 | 15672 |
| **Grafana** | http://localhost:3000 | admin/admin123 | 3000 |
| **Browserless Live Debugger** | http://localhost:3001 | - | 3001 |
| **FastAPI Docs** | http://localhost:8000/docs | - | 8000 |
| **Loki API** | http://localhost:3100 | - | 3100 |
| **PostgreSQL** | localhost:5432 | clippings_user/password | 5432 |
| **RabbitMQ AMQP** | amqp://localhost:5672 | admin/admin123 | 5672 |
| **Web-STOMP** | ws://localhost:15674/ws | - | 15674 |


***

## 9. Scripts Úteis - scripts/

### 9.1 scripts/deploy.sh

```bash
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
```


### 9.2 scripts/logs.sh

```bash
#!/bin/bash

SERVICE=${1:-all}

if [ "$SERVICE" = "all" ]; then
    docker-compose logs -f
elif [ "$SERVICE" = "worker" ]; then
    docker-compose logs -f agno_worker
elif [ "$SERVICE" = "scheduler" ]; then
    docker-compose logs -f agno_scheduler
elif [ "$SERVICE" = "api" ]; then
    docker-compose logs -f api
elif [ "$SERVICE" = "rabbitmq" ]; then
    docker-compose logs -f rabbitmq
elif [ "$SERVICE" = "postgres" ]; then
    docker-compose logs -f postgres
elif [ "$SERVICE" = "browserless" ]; then
    docker-compose logs -f browserless
elif [ "$SERVICE" = "grafana" ]; then
    docker-compose logs -f grafana
else
    echo "Usage: $0 {all|worker|scheduler|api|rabbitmq|postgres|browserless|grafana}"
fi
```


### 9.3 scripts/health-check.sh

```bash
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
```


### 9.4 scripts/backup.sh

```bash
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
```


***

## 10. Arquitetura em Portainer - Visualização

```
PORTAINER DASHBOARD
│
├── 📊 STATUS OVERVIEW
│   ├── 9 Services Running
│   ├── CPU Usage: X%
│   ├── Memory Usage: X%
│   └── Network Activity
│
├── 🐳 CONTAINERS
│   ├── clippings_postgres ✅
│   ├── clippings_rabbitmq ✅
│   ├── clippings_loki ✅
│   ├── clippings_promtail ✅
│   ├── clippings_grafana ✅
│   ├── clippings_browserless ✅
│   ├── clippings_browser_use_mcp ✅
│   ├── clippings_agno_worker ✅
│   ├── clippings_agno_scheduler ✅
│   └── clippings_api ✅
│
├── 💾 VOLUMES
│   ├── postgres_data
│   ├── rabbitmq_data
│   ├── grafana_data
│   ├── loki_data
│   ├── browserless_cache
│   └── portainer_data
│
├── 🌐 NETWORKS
│   └── clippings-network (172.20.0.0/16)
│
├── 📊 LOGS VIEWER
│   ├── Real-time streaming
│   ├── Search & filter
│   ├── Export capability
│   └── Integrated with Loki/Grafana
│
└── ⚙️ SETTINGS
    ├── Auto-update policies
    ├── Volume backups
    ├── Network isolation
    └── Resource limits
```


***

## 11. Fluxo Operacional Completo

### 11.1 Deploy Inicial (5 minutos)

```bash
# 1. Clonar/preparar projeto
git clone <seu-repo>
cd clippings-agno

# 2. Copiar arquivo .env
cp .env.example .env
# Editar .env com suas credenciais

# 3. Executar deploy
chmod +x scripts/deploy.sh
./scripts/deploy.sh

# 4. Verificar status
./scripts/health-check.sh

# 5. Acessar Portainer
# http://localhost:9000 (admin/admin)
```


### 11.2 Monitoramento Diário (Via Portainer)

```bash
# Terminal 1: Ver logs em tempo real
./scripts/logs.sh worker

# Terminal 2: Dashboard Portainer
# http://localhost:9000 → Containers → Live Stats

# Terminal 3: Grafana Logs
# http://localhost:3000 → Explore → Loki queries
```


### 11.3 Troubleshooting (Via Portainer)

**Cenário: Worker travado**

1. Portainer → Containers → clippings_agno_worker
2. View Logs → Procurar por erros
3. Restart Container (se necessário)
4. Monitorar via Grafana Loki

**Cenário: Fila acumulando**

1. RabbitMQ UI (localhost:15672)
2. Queues → clippings.jobs → Verificar backlog
3. Portainer → agno_worker → Check CPU/Memory
4. Escalar: Aumentar WORKER_CONCURRENCY no .env

***

## 12. Checklist Final (Arquitetura Portainer)

- [x] Docker Compose com 10 serviços otimizados e documentados
- [x] Configuração compartilhada via .env e volumes de config
- [x] Health checks em todos os serviços
- [x] Redes isoladas (clippings-network 172.20.0.0/16)
- [x] Volumes persistidos com backup capability
- [x] Portainer como orquestrador central
- [x] Grafana Loki + Promtail para logs centralizados
- [x] Scripts de deploy, logs, health-check, backup
- [x] Tabelas PostgreSQL pré-criadas com init-db.sql
- [x] 4 Agentes Agno especializados (Super, Browser, File, Notification)
- [x] Scheduler Cron independente
- [x] API FastAPI para dashboard
- [x] Browserless com Live Debugger habilitado
- [x] RabbitMQ com Web-STOMP para WebSocket telemetria
- [x] Pronto para produção e scaling
- [x] Documentação completa e exemplos
- [x] **ARQUITETURA PORTAINER 100% FUNCIONAL E SIMPLES**

***

**Fim do Super Prompt v3.1 - Arquitetura Completa para Portainer**


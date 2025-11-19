# Agno Clipping - Sistema de Clippings Autônomos Inteligentes v3.1

Sistema completo de clippings autônomos usando agentes Agno especializados, arquitetura Docker Compose e Portainer.

## 📋 Visão Geral

Sistema de clippings autônomos que utiliza:
- **Agentes Agno** especializados (Super, Browser, File, Notification)
- **Docker Compose** com 10 serviços otimizados
- **Portainer** para orquestração e monitoramento
- **PostgreSQL** para persistência
- **RabbitMQ** para filas de mensagens
- **Grafana + Loki** para logs centralizados
- **Browserless** para automação web
- **FastAPI** para dashboard de monitoramento

## 🏗️ Arquitetura

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
│   └── Networks
│       └── clippings-network (bridge)
```

## 🚀 Início Rápido

### 1. Pré-requisitos

- Docker e Docker Compose instalados
- Portainer (opcional, mas recomendado)
- 4GB+ de RAM disponível

### 2. Configuração

```bash
# Clonar o repositório
git clone <seu-repo>
cd agno_clipping

# Criar arquivo .env baseado no exemplo
cp .env.example .env
# Editar .env com suas credenciais
```

### 3. Variáveis de Ambiente (.env)

```bash
# Database
DB_USER=clippings_user
DB_PASSWORD=seu_password_seguro
DB_NAME=clippings_db

# RabbitMQ
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=seu_password_seguro

# MinIO S3
MINIO_ENDPOINT=minio.brmsolutions.com.br
MINIO_ACCESS_KEY=sua_access_key
MINIO_SECRET_KEY=sua_secret_key

# LLM
LLM_PROVIDER=openai
OPENAI_API_KEY=sua_api_key
LLM_MODEL=gpt-4-turbo

# Outras configurações...
```

### 4. Deploy

```bash
# Executar script de deploy
chmod +x scripts/deploy.sh
./scripts/deploy.sh

# Ou manualmente
docker-compose up -d
```

### 5. Verificar Status

```bash
# Health check
./scripts/health-check.sh

# Ver logs
./scripts/logs.sh worker
```

## 🌐 Endpoints e Acessos

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

## 📁 Estrutura do Projeto

```
agno_clipping/
├── api/                    # API FastAPI
│   └── main.py
├── worker/                 # Worker principal
│   └── main.py
├── scheduler/              # Scheduler Cron
│   └── main.py
├── config/                 # Configurações
│   ├── rabbitmq.conf
│   ├── loki-config.yaml
│   ├── promtail-config.yaml
│   └── grafana/
│       └── provisioning/
├── scripts/                # Scripts utilitários
│   ├── deploy.sh
│   ├── logs.sh
│   ├── health-check.sh
│   └── backup.sh
├── logs/                   # Logs da aplicação
├── workspace/              # Workspace do Browserless
├── docker-compose.yml      # Stack principal
├── Dockerfile.worker       # Dockerfile do worker
├── Dockerfile.scheduler    # Dockerfile do scheduler
├── Dockerfile.api          # Dockerfile da API
├── init-db.sql             # Schema inicial do PostgreSQL
├── requirements.txt         # Dependências Python
└── README.md
```

## 🔧 Scripts Utilitários

### Deploy
```bash
./scripts/deploy.sh
```

### Logs
```bash
# Todos os serviços
./scripts/logs.sh

# Serviço específico
./scripts/logs.sh worker
./scripts/logs.sh scheduler
./scripts/logs.sh api
```

### Health Check
```bash
./scripts/health-check.sh
```

### Backup
```bash
./scripts/backup.sh
```

## 🗄️ Banco de Dados

O PostgreSQL é inicializado automaticamente com o schema em `init-db.sql`:

- **clipping_jobs**: Jobs de clipping
- **clipping_results**: Resultados dos clippings
- **agent_execution_logs**: Logs de execução dos agentes
- **notification_logs**: Logs de notificações

## 🔄 Fluxo de Trabalho

1. **Scheduler** agenda jobs periodicamente
2. Jobs são enviados para fila **RabbitMQ**
3. **Worker** consome jobs da fila
4. **Worker** executa agentes Agno especializados:
   - Super Agent (orquestração)
   - Browser Agent (navegação web)
   - File Agent (processamento de arquivos)
   - Notification Agent (notificações)
5. Resultados são salvos no **PostgreSQL** e **MinIO S3**
6. Notificações são enviadas via **Notification Agent**
7. Logs são centralizados no **Loki** e visualizados no **Grafana**

## 🛠️ Desenvolvimento

### Estrutura Python

- **POO**: Classes e métodos bem definidos
- **Tipagem**: Type hints em todas as funções
- **Docstrings**: Documentação em português
- **Validação**: Pydantic para validação de dados
- **Logging**: Estruturado e centralizado

### Adicionar Novo Agente

1. Criar módulo em `worker/agents/`
2. Implementar interface base
3. Registrar no worker principal
4. Adicionar testes

## 📊 Monitoramento

- **Grafana**: Dashboards de logs e métricas
- **Loki**: Agregação de logs
- **Portainer**: Monitoramento de containers
- **RabbitMQ Management**: Monitoramento de filas

## 🔒 Segurança

- Variáveis sensíveis via `.env`
- Secrets não commitados
- Rede isolada (clippings-network)
- Health checks em todos os serviços

## 🐛 Troubleshooting

### Worker não processa jobs
```bash
# Verificar logs
./scripts/logs.sh worker

# Verificar fila RabbitMQ
# Acessar http://localhost:15672
```

### Banco de dados não conecta
```bash
# Verificar status
docker-compose ps postgres

# Ver logs
./scripts/logs.sh postgres
```

### Serviços não iniciam
```bash
# Verificar health check
./scripts/health-check.sh

# Verificar recursos
docker stats
```

## 📝 Próximos Passos

- [ ] Implementar agentes Agno especializados
- [ ] Adicionar testes unitários e de integração
- [ ] Implementar retry logic avançado
- [ ] Adicionar métricas Prometheus
- [ ] Implementar autenticação na API
- [ ] Adicionar documentação Swagger completa

## 📚 Documentação Adicional

Consulte `docs/Super Prompt para Criação de Agentes Agno - Clippi (1).md` para documentação completa da arquitetura.

## 📄 Licença

[Definir licença]

## 👥 Contribuidores

[Definir contribuidores]

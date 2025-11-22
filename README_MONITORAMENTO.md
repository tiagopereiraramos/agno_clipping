# 📺 Como Acompanhar Jobs em Tempo Real

## 1. Interface Visual do Browserless

Acesse: **http://localhost:3001/**

### Passos:
1. Abra o navegador em `http://localhost:3001/`
2. Clique no botão **"Sessions"** na barra lateral (ícone de ondas 📡)
3. Você verá todas as sessões ativas do Browserless
4. Clique em uma sessão para ver:
   - Screenshots em tempo real
   - Console logs
   - Network requests
   - DOM tree

## 2. Logs em Tempo Real via Terminal

### Opção 1: Script de Monitoramento
```bash
./scripts/monitorar_job.sh
```

Este script mostra:
- 🧠 Reasonings do agente
- ⚡ Ações executadas
- 💭 Memórias
- 🚀 Status de execução
- ✅ Conclusões

### Opção 2: Logs Diretos
```bash
# Ver todos os logs
sudo docker-compose logs -f agno_worker

# Ver apenas logs relevantes
sudo docker-compose logs -f agno_worker | grep -E "(🧠|⚡|💭|🚀|✅|reasoning|acao|Step)"
```

## 3. Verificar Status no Banco

```bash
sudo docker-compose exec postgres psql -U clippings_user -d clippings_db -c \
  "SELECT job_id, status, created_at, completed_at FROM clippings_app.clipping_jobs ORDER BY created_at DESC LIMIT 5;"
```

## 4. Logs Formatados

Os logs incluem emojis para facilitar identificação:
- 🧠 **Reasoning**: Pensamentos do agente
- ⚡ **Ação**: Ações executadas
- 💭 **Memória**: Memórias de longo prazo
- 🚀 **Início**: Início de operações
- ✅ **Sucesso**: Operações concluídas
- ⏱️ **Timeout**: Timeouts
- 🍪 **Cookies**: Sessão do Chrome
- 🔌 **Conexão**: Conexões estabelecidas
- 🌐 **Navegação**: Navegação iniciada
- 📋 **Tarefa**: Detalhes da tarefa
- 🔗 **URL**: URLs acessadas
- 👀 **Monitoramento**: Links para acompanhamento

## 5. Troubleshooting

Se não estiver vendo logs:
1. Verifique se o worker está rodando: `sudo docker-compose ps agno_worker`
2. Verifique logs de erro: `sudo docker-compose logs --tail=100 agno_worker | grep -i error`
3. Reinicie o worker: `sudo docker-compose restart agno_worker`


# 📺 Guia de Monitoramento em Tempo Real

## 🎯 Acompanhar Visualmente no Browserless

### Passo a Passo:

1. **Acesse a Interface do Browserless:**
   ```
   http://localhost:3001/
   ```
   Ou se estiver via SSH tunnel:
   ```
   http://54.197.132.154:3001/
   ```

2. **Visualizar Sessões Ativas:**
   - Clique no botão **"Sessions"** na barra lateral esquerda (ícone de ondas 📡)
   - Você verá todas as sessões ativas do Browserless
   - Cada sessão mostra:
     - Screenshots em tempo real
     - Console logs
     - Network requests
     - DOM tree
     - CDP events

3. **Monitorar uma Sessão Específica:**
   - Clique em uma sessão na lista
   - Veja o que o navegador está fazendo em tempo real
   - Acompanhe cliques, digitação, navegação

## 📊 Acompanhar via Logs

### Opção 1: Script de Monitoramento (Recomendado)
```bash
./scripts/monitorar_job.sh
```

### Opção 2: Logs Diretos com Filtros
```bash
# Ver todos os logs relevantes
sudo docker-compose logs -f agno_worker | grep -E "(🧠|⚡|💭|🚀|✅|reasoning|Step|BrowserUSE)"

# Ver apenas erros
sudo docker-compose logs -f agno_worker | grep -E "(ERROR|erro|failed)"
```

### Opção 3: Logs Completos
```bash
sudo docker-compose logs -f agno_worker
```

## 🔍 O que Procurar nos Logs

### Emojis e Significados:
- 🧠 **Reasoning**: Pensamentos do agente BrowserUSE
- ⚡ **Ação**: Ações executadas (cliques, digitação)
- 💭 **Memória**: Memórias de longo prazo do agente
- 🚀 **Início**: Início de operações
- ✅ **Sucesso**: Operações concluídas
- ⏱️ **Timeout**: Timeouts atingidos
- 🍪 **Cookies**: Status da sessão do Chrome
- 🔌 **Conexão**: Conexões estabelecidas
- 🌐 **Navegação**: Navegação iniciada
- 📋 **Tarefa**: Detalhes da tarefa
- 🔗 **URL**: URLs acessadas

### Exemplo de Logs:
```
🧠 [Passo 1] Estou analisando a página e localizando o campo de busca...
⚡ [Passo 1] InputAction: Digitando "Lear" no campo de busca
🧠 [Passo 2] Aguardando resultados da busca aparecerem...
💭 [Passo 2] Memória: Encontrei 7 resultados na primeira página
```

## 🐛 Troubleshooting

### Se não estiver vendo sessões no Browserless:
1. Verifique se o Browserless está rodando:
   ```bash
   sudo docker-compose ps browserless
   ```

2. Verifique os logs do Browserless:
   ```bash
   sudo docker-compose logs browserless | tail -50
   ```

3. Acesse diretamente a API:
   ```bash
   curl http://localhost:3001/json/version
   ```

### Se os logs não aparecerem:
1. Verifique se o worker está processando:
   ```bash
   sudo docker-compose logs agno_worker | tail -50
   ```

2. Verifique se há jobs na fila:
   ```bash
   sudo docker-compose exec rabbitmq rabbitmqctl list_queues
   ```

3. Verifique o status dos jobs:
   ```bash
   sudo docker-compose exec postgres psql -U clippings_user -d clippings_db -c \
     "SELECT job_id, status, created_at FROM clippings_app.clipping_jobs ORDER BY created_at DESC LIMIT 5;"
   ```

## 📝 Dicas

- **Mantenha o Browserless UI aberto** enquanto o job roda para ver tudo em tempo real
- **Use o script de monitoramento** para logs filtrados e formatados
- **Combine ambos**: UI do Browserless + logs do terminal para visão completa


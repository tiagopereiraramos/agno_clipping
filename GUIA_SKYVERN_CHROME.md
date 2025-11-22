# 🚀 Guia: Skyvern + Chrome Local - Resolução de HTTP 403

## ❌ Problema

Skyvern está retornando HTTP 403 mesmo com Chrome local, indicando que:
- Chrome NÃO está realmente navegando como browser real
- Requisições estão sendo detectadas como bots
- Skyvern precisa usar Chrome real do sistema/Docker

## ✅ Solução: Configurar Skyvern para Usar Chrome Real

### PASSO 1: Verificar Chrome Instalado

**No Docker:**
```bash
sudo docker-compose run --rm agno_worker which chromium-browser
sudo docker-compose run --rm agno_worker ls -la /root/.cache/ms-playwright/chromium-*/
```

**Chrome está instalado via Playwright em:**
```
/root/.cache/ms-playwright/chromium-1129/chrome-linux/chrome
```

### PASSO 2: Parar Skyvern Anterior

```bash
# Parar processos anteriores
pkill -f "skyvern run"

# Verificar porta 8000
lsof -i :8000
```

### PASSO 3: Iniciar Skyvern com Chrome Local

**OPÇÃO A: Usar Script Helper (Recomendado)**

```bash
# No Docker
sudo docker-compose run --rm agno_worker python /app/start_skyvern_server.py

# Localmente
python start_skyvern_server.py
```

**OPÇÃO B: Manual**

```bash
# Terminal 1: Iniciar Skyvern server
SKYVERN_MODE=local skyvern run server --local --verbose

# Ou no Docker:
sudo docker-compose run --rm agno_worker bash -c "SKYVERN_MODE=local skyvern run server --local --verbose"
```

**Esperado:**
```
✅ Skyvern running on http://localhost:8000
✅ Browser mode: LOCAL
✅ Using: Chromium/Chrome
```

### PASSO 4: Testar Conexão

```bash
# No Docker
sudo docker-compose run --rm agno_worker python /app/test_skyvern_chrome.py

# Localmente
python test_skyvern_chrome.py
```

**Esperado:**
```
✅ Skyvern respondendo
✅ Navegação bem-sucedida (sem 403)
```

### PASSO 5: Executar Clipping

**Terminal 1: Iniciar Skyvern Server**
```bash
sudo docker-compose run --rm agno_worker python /app/start_skyvern_server.py
```

**Terminal 2: Executar Clipping**
```bash
sudo docker-compose run --rm agno_worker python /app/agno_clipping_skyvern.py
```

## 🔧 Configuração do Skyvern para Chrome Local

O Skyvern precisa estar configurado para usar Chrome real. Variáveis de ambiente importantes:

```bash
SKYVERN_MODE=local
CHROME_BIN=/root/.cache/ms-playwright/chromium-1129/chrome-linux/chrome
PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
```

## ⚠️ Troubleshooting

### Erro: HTTP 403 persistente

**Causa:** Chrome não está realmente sendo usado

**Solução:**
1. Verifique se Chrome está instalado: `ls /root/.cache/ms-playwright/chromium-*/chrome-linux/chrome`
2. Inicie Skyvern com modo local explícito: `SKYVERN_MODE=local skyvern run server --local`
3. Verifique logs do Skyvern para ver se Chrome foi detectado

### Erro: Porta 8000 já em uso

**Solução:**
```bash
pkill -f "skyvern run"
sleep 2
# Tente novamente
```

### Erro: Chrome não encontrado

**Solução:**
```bash
# Reinstalar Playwright Chromium
sudo docker-compose run --rm agno_worker playwright install chromium
```

## 📋 Checklist

- [ ] Chrome instalado via Playwright
- [ ] Skyvern server rodando em localhost:8000
- [ ] Test script retorna ✅ em todos os testes
- [ ] HTTP 403 não ocorre mais
- [ ] Clipping executa com sucesso

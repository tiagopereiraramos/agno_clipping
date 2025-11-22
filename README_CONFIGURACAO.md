# ⚙️ Configuração de Parâmetros

## 📁 Arquivo de Configuração

Os parâmetros do clipping podem ser configurados no arquivo:

```
config/clipping_params.json
```

## 📋 Parâmetros Disponíveis

```json
{
  "cliente": "LEAR",                    // Nome do cliente
  "periodo": "últimos 7 dias",          // Período de busca
  "max_itens": 10,                      // Máximo de itens a coletar
  "min_noticias": 3,                    // Mínimo de notícias (compatibilidade)
  "url": "https://www.automotivebusiness.com.br/",  // URL do site
  "palavras_chave": [                   // Palavras-chave para busca
    "Lear",
    "Lear Corporation",
    "Lear do Brasil"
  ],
  "extrair_imagens": false,             // Extrair imagens
  "extrair_links": true,                // Extrair links
  "formato": "both",                    // Formato de saída (json, markdown, both)
  "notificar": true                     // Enviar notificação por email
}
```

## 🔧 Onde os Parâmetros são Usados

### 1. **Teste Direto (sem filas)**

Arquivo: `teste_direto_browser.py`

O script carrega automaticamente os parâmetros de `config/clipping_params.json`:

```python
# O script já está configurado para ler o arquivo automaticamente
# Basta editar config/clipping_params.json
```

### 2. **Fluxo Completo (com filas)**

Arquivo: `scripts/test_fluxo_completo.sh`

O script também carrega os parâmetros de `config/clipping_params.json`:

```bash
# Execute normalmente
./scripts/test_fluxo_completo.sh
```

### 3. **Worker (processamento de filas)**

Arquivo: `worker/main.py`

O worker extrai os parâmetros da mensagem recebida da fila RabbitMQ:

```python
# Os parâmetros vêm da mensagem JSON enviada para a fila
parametros = mensagem.get("parameters", {})
```

## 📝 Como Configurar

### Opção 1: Editar o arquivo JSON (Recomendado)

```bash
nano config/clipping_params.json
```

Edite os valores desejados e salve.

### Opção 2: Configurar no código Python

Se estiver criando um script customizado:

```python
contexto = {
    "url": "https://www.automotivebusiness.com.br/",
    "parametros": {
        "cliente": "LEAR",
        "periodo": "últimos 7 dias",
        "max_itens": 10,
        "min_noticias": 3
    }
}
```

### Opção 3: Enviar via mensagem RabbitMQ

Ao enviar uma mensagem para a fila, inclua os parâmetros:

```python
mensagem = {
    "instruction": "Seu prompt aqui...",
    "parameters": {
        "cliente": "LEAR",
        "periodo": "últimos 7 dias",
        "max_itens": 10
    }
}
```

## 🔄 Ordem de Precedência

1. **Parâmetros na mensagem RabbitMQ** (maior prioridade)
2. **Arquivo `config/clipping_params.json`**
3. **Valores padrão no código**

## ✅ Exemplo de Uso

1. Edite `config/clipping_params.json`:
```json
{
  "cliente": "LEAR",
  "periodo": "últimos 30 dias",
  "max_itens": 15
}
```

2. Execute o teste:
```bash
sudo docker-compose exec agno_worker python /app/teste_direto_browser.py
```

3. Os parâmetros serão aplicados automaticamente!

## 📌 Notas Importantes

- O arquivo JSON deve estar em UTF-8
- Valores booleanos: `true`/`false` (minúsculas)
- Valores numéricos: sem aspas
- Strings: com aspas duplas
- Após editar, reinicie o worker se necessário: `sudo docker-compose restart agno_worker`


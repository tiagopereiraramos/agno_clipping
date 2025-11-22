# 🚀 Skyvern MCP + Agno - Clipping Automotivo

## 📋 Visão Geral

Esta implementação adiciona **Skyvern MCP** como opção alternativa ao **browser-use** para automação de navegação web. O Skyvern usa linguagem natural via Agno framework para executar tarefas de clipping.

## ⚙️ Configuração

### Variável de Ambiente Principal

```bash
BROWSER_ENGINE=skyvern  # ou "browser-use" (padrão)
```

### Variáveis de Ambiente do Skyvern

```bash
SKYVERN_MODEL=gpt-5-mini-2025-08-07
SKYVERN_TIMEOUT=3600
SKYVERN_PROMPT_PATH=/app/prompts/clipping_lear.txt
SKYVERN_CONFIG_PATH=/app/config/clipping_params.json
SKYVERN_RESULTS_DIR=/app/results
```

## 📦 Instalação

### 1. Instalar Dependências

```bash
pip install agno>=0.5.0 skyvern>=0.1.0
```

### 2. Inicializar Skyvern (Primeira Vez)

```bash
skyvern init
```

Durante o setup:
- **Modo**: Local (não cloud)
- **LLM Provider**: OpenAI
- **API Key**: Sua chave OpenAI

### 3. Verificar Instalação

```bash
skyvern run server
```

Servidor deve iniciar em `http://localhost:8000`

## 🧪 Teste

### Teste Direto (Recomendado)

```bash
# No container
sudo BROWSER_ENGINE=skyvern docker-compose exec agno_worker python /app/teste_skyvern.py

# Ou localmente (se tiver Python 3.11+)
python teste_skyvern.py
```

### Teste via Worker

```bash
sudo BROWSER_ENGINE=skyvern docker-compose up agno_worker
```

## 📁 Estrutura de Arquivos

```
project/
├── .env                          # Variáveis de ambiente
├── requirements.txt              # Dependências (já atualizado)
├── prompts/
│   └── clipping_lear.txt        # Prompt consolidado
├── config/
│   └── clipping_params.json     # Parâmetros (cliente, periodo, site, timeout)
├── results/                      # Resultados salvos automaticamente
│   └── clipping_resultado_*.json
└── worker/agents/
    └── skyvern_agent.py          # Agente Skyvern
```

## 🔄 Comparação: Browser-Use vs Skyvern

| Característica | Browser-Use | Skyvern |
|---------------|-------------|---------|
| **Engine** | browser-use | Skyvern MCP |
| **Framework** | Direto | Agno |
| **Linguagem** | Python puro | Python + Agno |
| **Navegação** | CDP/Playwright | Linguagem natural |
| **Complexidade** | Média | Baixa |
| **Requisitos** | Python 3.11+ | Python 3.11+ (hard) |

## 🎯 Como Usar

### Modo Browser-Use (Padrão)

```bash
BROWSER_ENGINE=browser-use docker-compose up agno_worker
```

### Modo Skyvern

```bash
BROWSER_ENGINE=skyvern docker-compose up agno_worker
```

## 📝 Arquivo de Configuração

`config/clipping_params.json`:

```json
{
  "cliente": "LEAR",
  "periodo": "últimos 30 dias",
  "max_itens": 15,
  "site": "https://www.automotivebusiness.com.br/",
  "timeout": 3600
}
```

## 🔍 Logs

O SkyvernAgent registra logs em português:

```
🚀 Iniciando clipping automotivo com Skyvern MCP
📝 Prompt carregado e parametrizado para LEAR
🔌 Skyvern MCP conectado e pronto
👨‍💻 Agent criado com sucesso
🌐 Iniciando navegação e coleta de artigos...
✅ Clipping concluído. Resultado salvo em: /app/results/clipping_resultado_20251121_120000.json
```

## ⚠️ Troubleshooting

### Erro: "Agno não instalado"

```bash
pip install agno>=0.5.0
```

### Erro: "Skyvern não instalado"

```bash
pip install skyvern>=0.1.0
```

### Erro: "Python 3.11 required"

Skyvern requer Python 3.11+ (hard requirement). Verifique:

```bash
python --version  # Deve ser 3.11.x ou superior
```

### Erro: "Skyvern MCP não responde"

1. Verifique se Skyvern está instalado: `skyvern --version`
2. Teste manualmente: `skyvern run server`
3. Verifique logs do container

## 📚 Referências

- [Skyvern Docs](https://docs.skyvern.com)
- [Agno Framework](https://github.com/agno-ai/agno)
- [MCP Protocol](https://modelcontextprotocol.io)

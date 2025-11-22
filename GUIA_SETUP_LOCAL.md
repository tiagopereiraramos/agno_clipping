# 🚀 Guia: Setup Local - Clipping Automotivo com Skyvern + Agno

## 📋 Pré-requisitos

### Sistema Operacional
- **Windows 10/11**, **macOS** ou **Linux**
- Python 3.11 ou superior
- Git instalado

### Software Necessário
- Google Chrome ou Chromium instalado
- Python 3.11+
- pip (gerenciador de pacotes Python)

## 🔧 Passo 1: Clonar o Repositório

```bash
# Clone o repositório
git clone <URL_DO_SEU_REPOSITORIO>
cd agno_clipping

# Ou se já estiver no diretório
cd /caminho/para/agno_clipping
```

## 🔧 Passo 2: Criar Ambiente Virtual (Recomendado)

### Windows
```powershell
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
.\venv\Scripts\Activate.ps1
# Ou se PowerShell bloqueado:
.\venv\Scripts\activate.bat
```

### macOS/Linux
```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate
```

## 🔧 Passo 3: Instalar Dependências

```bash
# Atualizar pip
pip install --upgrade pip

# Instalar dependências do projeto
pip install -r requirements.txt

# Instalar Chrome/Chromium via Playwright
playwright install chromium

# Verificar instalação
python -c "import agno; import skyvern; print('✅ Dependências instaladas')"
```

## 🔧 Passo 4: Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```bash
# .env
OPENAI_API_KEY=sua_chave_openai_aqui
PYTHONUNBUFFERED=1
```

**Importante:** Substitua `sua_chave_openai_aqui` pela sua chave real da OpenAI.

## 🔧 Passo 5: Verificar Configuração

### Verificar Chrome
```bash
# Verificar se Chrome está instalado
# Windows
where chrome
# macOS
which google-chrome
# Linux
which google-chrome-stable || which chromium-browser

# Verificar Playwright Chromium
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); print(p.chromium.executable_path)"
```

### Verificar Skyvern
```bash
# Verificar instalação do Skyvern
python -m skyvern --version

# Testar Skyvern MCP
python -m skyvern run mcp --help
```

## 🔧 Passo 6: Testar Setup Básico

### Teste 1: Verificar Arquivos
```bash
# Verificar se arquivos necessários existem
ls config/clipping_params.json
ls prompts/clipping_lear.txt
ls agno_clipping_skyvern_fixed.py
```

### Teste 2: Testar Importações
```bash
python -c "
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools
print('✅ Agno importado com sucesso')
"
```

## 🚀 Passo 7: Executar Clipping Local

### Opção A: Versão Fixed (HTTP Server - Recomendada)

```bash
# Executar clipping
python agno_clipping_skyvern_fixed.py
```

**O que acontece:**
1. Verifica se Chrome está instalado
2. Inicia Skyvern server HTTP automaticamente
3. Conecta via MCPTools
4. Executa clipping
5. Salva resultado em `results/clipping_resultado_*.json`
6. Para servidor automaticamente

### Opção B: Versão Original (stdio)

```bash
# Executar clipping
python agno_clipping_skyvern.py
```

**O que acontece:**
1. Verifica Chrome
2. Executa Skyvern MCP via stdio (sem servidor HTTP)
3. Executa clipping
4. Salva resultado

## 📊 Passo 8: Verificar Resultados

```bash
# Listar resultados
ls -lh results/

# Ver último resultado
cat results/clipping_resultado_*.json | tail -1 | python -m json.tool
```

## 🐛 Troubleshooting

### Erro: "Chrome não encontrado"

**Solução:**
```bash
# Instalar Chrome via Playwright
playwright install chromium

# Ou instalar Chrome manualmente:
# Windows: Baixar de https://www.google.com/chrome/
# macOS: brew install --cask google-chrome
# Linux: sudo apt-get install google-chrome-stable
```

### Erro: "OPENAI_API_KEY não encontrada"

**Solução:**
```bash
# Verificar se .env existe
cat .env

# Se não existir, criar:
echo "OPENAI_API_KEY=sua_chave_aqui" > .env
```

### Erro: "Skyvern não instalado"

**Solução:**
```bash
# Reinstalar Skyvern
pip install --upgrade skyvern[local]

# Verificar instalação
python -m skyvern --version
```

### Erro: "Porta 8000 já em uso"

**Solução:**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill -9
```

### Erro: "ModuleNotFoundError"

**Solução:**
```bash
# Reinstalar todas as dependências
pip install --upgrade -r requirements.txt

# Verificar ambiente virtual está ativo
which python  # Deve apontar para venv/bin/python (ou venv\Scripts\python.exe no Windows)
```

## 🔍 Debug Avançado

### Ver Logs Detalhados

```bash
# Executar com logs detalhados
PYTHONUNBUFFERED=1 python agno_clipping_skyvern_fixed.py 2>&1 | tee debug.log
```

### Testar Skyvern MCP Diretamente

```bash
# Iniciar Skyvern MCP manualmente
python -m skyvern run mcp

# Em outro terminal, testar conexão
python -c "
import asyncio
from agno.tools.mcp import MCPTools

async def test():
    mcp = MCPTools(transport='stdio', command='python -m skyvern run mcp')
    async with mcp:
        print('✅ Skyvern MCP conectado')
        # Testar ferramentas disponíveis
        # (depende da implementação do MCPTools)

asyncio.run(test())
"
```

### Verificar Variáveis de Ambiente

```bash
# Windows PowerShell
$env:OPENAI_API_KEY
$env:CHROME_BIN

# macOS/Linux
echo $OPENAI_API_KEY
echo $CHROME_BIN
```

## 📁 Estrutura de Arquivos Local

```
agno_clipping/
├── .env                          # Variáveis de ambiente (criar)
├── .gitignore                    # Arquivos ignorados pelo git
├── requirements.txt              # Dependências Python
├── config/
│   └── clipping_params.json      # Parâmetros de configuração
├── prompts/
│   └── clipping_lear.txt         # Prompt do agente
├── results/                      # Resultados (criado automaticamente)
│   └── clipping_resultado_*.json
├── agno_clipping_skyvern.py      # Script principal (stdio)
├── agno_clipping_skyvern_fixed.py # Script principal (HTTP)
├── start_skyvern_server.py       # Helper para iniciar Skyvern
├── test_skyvern_chrome.py        # Script de teste
└── GUIA_SETUP_LOCAL.md           # Este arquivo
```

## ✅ Checklist de Setup

- [ ] Repositório clonado
- [ ] Ambiente virtual criado e ativado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Chrome instalado (via Playwright ou manual)
- [ ] Arquivo `.env` criado com `OPENAI_API_KEY`
- [ ] Arquivos de configuração presentes (`config/`, `prompts/`)
- [ ] Teste básico executado com sucesso
- [ ] Clipping executado e resultado salvo

## 🎯 Próximos Passos

1. **Testar execução básica:**
   ```bash
   python agno_clipping_skyvern_fixed.py
   ```

2. **Verificar resultado:**
   ```bash
   cat results/clipping_resultado_*.json | python -m json.tool
   ```

3. **Ajustar configuração:**
   - Editar `config/clipping_params.json` para mudar parâmetros
   - Editar `prompts/clipping_lear.txt` para ajustar comportamento

4. **Integrar com sistema maior:**
   - Usar resultado JSON em outros sistemas
   - Automatizar execução (cron, scheduler, etc.)

## 💡 Dicas

1. **Performance:** Use `agno_clipping_skyvern_fixed.py` (HTTP) para melhor performance
2. **Debug:** Use `agno_clipping_skyvern.py` (stdio) para ver logs mais detalhados
3. **Timeout:** Ajuste `timeout` em `config/clipping_params.json` se necessário
4. **Chrome:** Use Chrome local (não headless) para evitar bloqueios 403

## 📞 Suporte

Se encontrar problemas:
1. Verifique os logs de erro
2. Confirme que todas as dependências estão instaladas
3. Teste cada componente isoladamente (Chrome, Skyvern, Agno)
4. Consulte a documentação oficial:
   - [Agno Framework](https://github.com/agno-ai/agno)
   - [Skyvern](https://www.skyvern.com/docs)

---

**Última atualização:** 2025-11-22


# 📝 Sistema de Prompts Parametrizáveis

## 📁 Estrutura

Os prompts são armazenados em arquivos TXT no diretório `prompts/`:

```
prompts/
  └── clipping_lear.txt  # Prompt principal para clipping LEAR
```

## 🔧 Variáveis Disponíveis

No arquivo de prompt, você pode usar as seguintes variáveis que serão substituídas automaticamente:

- `{cliente}` - Nome do cliente (padrão: "LEAR")
- `{periodo}` - Período de busca (padrão: "últimos 7 dias")
- `{max_itens}` - Máximo de itens a coletar (padrão: 10)
- `{site}` - URL do site alvo (padrão: "https://www.automotivebusiness.com.br/")
- `{timeout}` - Timeout em segundos (padrão: 600)

## 📋 Como Editar o Prompt

1. Edite o arquivo `prompts/clipping_lear.txt`
2. Use as variáveis `{variavel}` onde necessário
3. Salve o arquivo
4. Reinicie o worker: `sudo docker-compose restart agno_worker`

## 🎯 Exemplo de Uso

### No código Python:

```python
contexto = {
    "url": "https://www.automotivebusiness.com.br/",
    "parametros": {
        "cliente": "LEAR",
        "periodo": "últimos 7 dias",
        "max_itens": 10
    }
}
```

### No arquivo de prompt:

```
Você é um agente de clipping para o cliente {cliente}.
Buscar no período: {periodo}
Coletar até {max_itens} itens do site {site}
```

## 🔄 Como Funciona

1. O `BrowserAgent` tenta carregar o prompt de `prompts/clipping_lear.txt`
2. Se encontrado, substitui as variáveis pelos valores do contexto
3. Se não encontrado, usa um prompt padrão otimizado
4. O prompt final é enviado ao browser-use para execução

## 📝 Estrutura do Prompt Atual

O prompt atual (`clipping_lear.txt`) inclui:

- **Objetivo**: Descrição clara do que o agente deve fazer
- **Escopo**: Domínio permitido e preferências
- **Vocabulário de busca**: Termos relacionados a chicotes/EDS e produtos LEAR
- **Estratégia de busca**: Passos para encontrar conteúdo
- **Passos de navegação**: Instruções detalhadas
- **Critérios de inclusão**: O que incluir/excluir
- **Formato de saída**: JSON esperado
- **Boas práticas**: Economia de tokens

## 🛠️ Manutenção

Para ajustar o prompt:

1. Edite `prompts/clipping_lear.txt`
2. Teste com: `sudo docker-compose exec agno_worker python /app/teste_direto_browser.py`
3. Verifique os logs para ver se o prompt foi carregado corretamente

## ⚠️ Notas Importantes

- O arquivo deve estar em UTF-8
- Use `{variavel}` para variáveis (não `$variavel` ou `{{variavel}}`)
- O prompt é carregado uma vez por execução
- Alterações no prompt requerem reinício do worker (ou rebuild se necessário)


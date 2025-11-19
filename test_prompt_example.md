# Prompt de Teste - Clipping LEAR no Automotive Business

## Prompt Recomendado

```
Coletar todas as informações disponíveis sobre produtos, notícias e conteúdo relacionado à empresa LEAR no site https://www.automotivebusiness.com.br/. 

Incluir:
- Artigos e notícias sobre produtos LEAR
- Releases de produtos
- Menções à empresa LEAR
- Conteúdo relacionado a soluções da LEAR

Para cada item encontrado, extrair:
- Título completo
- Data de publicação (se disponível)
- Autor (se disponível)
- URL completa do artigo
- Conteúdo principal do texto
- Links relacionados

Formato de saída: JSON e Markdown
```

## Variações do Prompt

### Versão Simples
```
Buscar e extrair todas as informações sobre produtos da LEAR no site https://www.automotivebusiness.com.br/
```

### Versão Detalhada
```
Realizar clipping completo do site https://www.automotivebusiness.com.br/ focando especificamente em conteúdo relacionado à empresa LEAR. 

Objetivo: Coletar informações sobre:
1. Produtos e soluções da LEAR mencionados
2. Notícias e artigos sobre a empresa
3. Releases e comunicados
4. Análises e opiniões sobre produtos LEAR

Extrair para cada resultado:
- Título
- Data
- Autor
- URL
- Conteúdo completo
- Tags/categorias

Salvar em formato JSON estruturado e Markdown para fácil leitura.
```

### Versão com Busca Específica
```
Navegar no site https://www.automotivebusiness.com.br/ e buscar por "LEAR" ou "Lear Corporation". 
Coletar todos os artigos, notícias e menções encontradas. 
Para cada resultado, extrair título, data, autor, URL e conteúdo principal.
```

## Como Usar

1. **Via Script de Teste:**
```bash
./scripts/test_clipping.sh
```

2. **Via API:**
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Coletar todas as informações sobre produtos LEAR no site https://www.automotivebusiness.com.br/",
    "parameters": {
      "site": "https://www.automotivebusiness.com.br/",
      "cliente": "LEAR"
    }
  }'
```

3. **Via RabbitMQ diretamente:**
```python
import pika
import json

connection = pika.BlockingConnection(
    pika.ConnectionParameters('localhost')
)
channel = connection.channel()

mensagem = {
    "instruction": "Coletar todas as informações sobre produtos LEAR no site https://www.automotivebusiness.com.br/",
    "parameters": {
        "cliente": "LEAR",
        "formato": "both"
    }
}

channel.basic_publish(
    exchange='',
    routing_key='clippings.jobs',
    body=json.dumps(mensagem)
)
```

## Resultado Esperado

O sistema deve:
1. ✅ Interpretar o prompt e identificar a URL
2. ✅ Navegar até o site
3. ✅ Buscar conteúdo relacionado à LEAR
4. ✅ Extrair informações estruturadas
5. ✅ Salvar em JSON e Markdown
6. ✅ Registrar no banco de dados
7. ✅ Retornar resultado completo


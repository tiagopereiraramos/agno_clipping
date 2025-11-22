# Sessão do Browser

Este diretório armazena a sessão do Chrome extraída para evitar problemas com CAPTCHA.

## Como extrair sua sessão do Chrome

### 1. Execute o script de extração

```bash
./scripts/extrair_sessao_chrome.sh
```

O script irá:
- Extrair cookies do seu Chrome
- Filtrar cookies relevantes (automotivebusiness.com.br, Google, reCAPTCHA)
- Criar `storage_state.json` no formato compatível com BrowserUSE

### 2. Verificar se foi criado

```bash
ls -lh browser_session/storage_state.json
```

### 3. Reiniciar o worker

```bash
sudo docker-compose restart agno_worker
```

## Formato do arquivo

O arquivo `storage_state.json` segue o formato Playwright/BrowserUSE:

```json
{
  "cookies": [
    {
      "name": "cookie_name",
      "value": "cookie_value",
      "domain": ".automotivebusiness.com.br",
      "path": "/",
      "expires": 1234567890,
      "httpOnly": false,
      "secure": true,
      "sameSite": "Lax"
    }
  ],
  "origins": []
}
```

## Personalização

Você pode ajustar o script para:
- Extrair cookies de outros domínios
- Modificar o caminho do perfil do Chrome
- Filtrar cookies específicos

Edite `scripts/extrair_sessao_chrome.sh` conforme necessário.

## Notas

- O arquivo `storage_state.json` contém informações sensíveis (cookies de sessão)
- Não commite este arquivo no Git (já está no `.gitignore`)
- Atualize a sessão periodicamente se os cookies expirarem


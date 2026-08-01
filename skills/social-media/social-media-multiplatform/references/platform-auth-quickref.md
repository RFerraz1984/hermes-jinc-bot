# Quick Reference: Auth & Setup por Plataforma

## Bluesky (AT Protocol)
```
# 1. Instalar CLI (no container) — OPÇÃO FUNCIONA SEM ROOT/GO/UNZIP
mkdir -p /opt/data/home/.local/bin
cd /opt/data/home/.local/bin
python3 -c "
import zipfile, urllib.request, os
url = 'https://github.com/mattn/bsky/releases/download/v0.0.81/bsky-linux-0.0.81.zip'
dest = '/opt/data/home/.local/bin/bsky.zip'
urllib.request.urlretrieve(url, dest)
with zipfile.ZipFile(dest, 'r') as z:
    z.extractall('/opt/data/home/.local/bin/')
os.remove(dest)
os.chmod('/opt/data/home/.local/bin/bsky', 0o755)
"
# Verificar
/opt/data/home/.local/bin/bsky --help

# 2. Criar App Password no Bluesky
# Settings → Privacy → App Passwords → Create
# Nome: "JINC Bot" → Copiar senha gerada

# 3. Login (fora da sessão do agente, no terminal do container)
# IMPORTANTE: Use HOME=/opt/data/home e caminho completo do binário
# O handle correto é: inclusivo.bsky.social (NÃO jornalistainclusivo.bsky.social)
HOME=/opt/data/home /opt/data/home/.local/bin/bsky login \
  inclusivo.bsky.social \
  SUA_APP_PASSWORD_AQUI

# 4. Testar
HOME=/opt/data/home /opt/data/home/.local/bin/bsky post "Teste JINC 🧵 #Acessibilidade"
```
## Telegram Channel

```bash
# 1. Bot já configurado no Hermes Gateway (token salvo lá)
# 2. Adicionar bot ao canal como Admin:
#    - Abrir canal → Editar → Administradores → Adicionar @SeuBot
#    - Permissão: "Post Messages" ✅

# 3. Obter Chat ID do canal:
#    - Encaminhar msg do canal para @userinfobot → pega -100xxxxxxxxx
#    - Ou usar @jornalistainclusivo (username público)

# 4. Variáveis de ambiente no container (Umbrel → Hermes → Env vars):
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF... (já no gateway, mas script precisa)
TELEGRAM_CHANNEL_ID=-1001234567890  # ou @jornalistainclusivo
```

> ⚠️ **Problema crítico (2026-07-05)**: O `.env` usa `TELEGRAM_HOME_CHANNEL=965862678` mas os scripts esperam `TELEGRAM_CHANNEL_ID`.
> **Fix no script/cron**: `export TELEGRAM_CHANNEL_ID="${TELEGRAM_CHANNEL_ID:-${TELEGRAM_HOME_CHANNEL}}"`
>
> ⚠️ **Token INVÁLIDO (2026-07-05)**: Token `876079...WpOY` rejeitado pelo Telegram (`InvalidToken: Not Found`).
> **Fix**: Regenerar no @BotFather (`/mybots` → Bot → API Token → Revoke & Get new) → Atualizar no Umbrel Settings → Hermes → Env vars → Reiniciar app Hermes.
## X/Twitter (xurl)

```bash
# 1. Instalar
curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh | bash

# 2. Criar App no developer.x.com
#    - Redirect URI: http://localhost:8080/callback
#    - App type: "Web app, automated app or bot"
#    - Permissions: Read and Write + Direct Messages

# 3. Configurar (HOME=/opt/data/home para container)
HOME=/opt/data/home xurl auth apps add jinc-app \
  --client-id SEU_CLIENT_ID \
  --client-secret SEU_CLIENT_SECRET

HOME=/opt/data/home xurl auth oauth2 --app jinc-app @jornalistainc
HOME=/opt/data/home xurl auth default jinc-app

# 4. Testar
HOME=/opt/data/home xurl post "Teste JINC 🧵 #Acessibilidade"
```

> ⚠️ **Problema conhecido (2026-07-05)**: `xurl` **não está instalado** no container. O cron job "Jornalista Inclusivo - Auto-post RSS para X/Twitter" está **PAUSADO**. Instalar via comando acima quando o App Review no developer.x.com for aprovado.

## Telegram Channel
```
# ⚠️ REQUER APP REVIEW (pode levar semanas)

# 1. Meta Developer App → Add Product → Facebook Login
# 2. Configurar: Valid OAuth Redirect URIs
# 3. Permissões necessárias (solicitar review):
#    - pages_manage_posts
#    - pages_read_engagement
#    - pages_show_list

# 4. Após aprovação, gerar tokens:
#    - Graph Explorer → Get User Access Token (com permissões acima)
#    - Trocar por Long-Lived (60 dias):
curl "https://graph.facebook.com/v19.0/oauth/access_token?
  grant_type=fb_exchange_token&
  client_id=APP_ID&
  client_secret=APP_SECRET&
  fb_exchange_token=SHORT_TOKEN"

#    - Obter Page Access Token:
curl "https://graph.facebook.com/v19.0/me/accounts?access_token=LONG_TOKEN"

# 5. Variáveis de ambiente:
FB_PAGE_ACCESS_TOKEN=EAAxxx...
FB_PAGE_ID=1234567890
```

## LinkedIn
```
❌ NÃO RECOMENDADO PARA AUTOMAÇÃO VIA API
- API de postagem pública descontinuada
- Partner Program obrigatório (processo comercial)
- Risco de ban com wrappers não-oficiais

✅ ALTERNATIVAS:
- Post manual + agendamento nativo do LinkedIn
- Buffer/Hootsuite/Later (têm parceria oficial)
- Zapier/Make com conexão oficial
```

## WhatsApp Business (Cloud API)
```
⚠️ SOMENTE CONTA BUSINESS VERIFICADA

# 1. Meta Business Manager → WhatsApp → Get Started
# 2. Verificar Business (documentos da empresa)
# 3. Configurar Phone Number + Templates
# 4. Permanent Access Token (não expira)

# 5. Templates precisam ser APROVADOS pela Meta (24-48h)
# Exemplo template "novo_artigo_jinc":
# "Novo artigo: {{1}} 🔗 {{2}}"

# 6. Variáveis:
WHATSAPP_PHONE_NUMBER_ID=123456789
WHATSAPP_ACCESS_TOKEN=EAAxxx...
WHATSAPP_TEMPLATE_NAME=novo_artigo_jinc
WHATSAPP_TEMPLATE_LANG=pt_BR

# ⚠️ LIMITAÇÕES:
# - Só envia para quem deu opt-in
# - Custo por conversa iniciada pela empresa
# - Não é broadcast (1:1 apenas)
# - Rate limits estritos
```

## Instalação Rápida no Container (Tudo de Uma Vez)
```bash
# No terminal do container Hermes (Umbrel Dashboard → Hermes → Terminal)

# Dependências base
apk add --no-cache curl jq libxml2-utils  # xmllint

# xurl (X/Twitter)
curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh | bash

# bsky (Bluesky) — SEM GO, SEM UNZIP, SEM ROOT
mkdir -p /opt/data/home/.local/bin
cd /opt/data/home/.local/bin
python3 -c "
import zipfile, urllib.request, os
url = 'https://github.com/mattn/bsky/releases/download/v0.0.81/bsky-linux-0.0.81.zip'
dest = '/opt/data/home/.local/bin/bsky.zip'
urllib.request.urlretrieve(url, dest)
with zipfile.ZipFile(dest, 'r') as z:
    z.extractall('/opt/data/home/.local/bin/')
os.remove(dest)
os.chmod('/opt/data/home/.local/bin/bsky', 0o755)
"

# Verificar
/opt/data/home/.local/bin/xurl --help
/opt/data/home/.local/bin/bsky --help
```

# Variáveis de Ambiente Resumo (Umbrel → Hermes → Settings → Env vars)
```bash
# Obrigatórias Fase 1
TELEGRAM_BOT_TOKEN=123456...
TELEGRAM_CHANNEL_ID=-1001234567890
BSKY_HANDLE=inclusivo.bsky.social
```
# Fase 2 (após config)
# XURL já usa ~/.xurl (configurado via CLI)

# Fase 3 (opcional)
# FB_PAGE_ACCESS_TOKEN=EAA...
# FB_PAGE_ID=123...
# WHATSAPP_PHONE_NUMBER_ID=...
# WHATSAPP_ACCESS_TOKEN=...
# WHATSAPP_TEMPLATE_NAME=novo_artigo_jinc
```
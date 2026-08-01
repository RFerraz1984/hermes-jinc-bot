---
name: social-media-multiplatform
description: "Multi-platform social media posting for Jornalista Inclusivo: Bluesky, Facebook, LinkedIn, Telegram Channel, WhatsApp Business + X/Twitter. Includes CLI tools, API references, auth patterns, and cron job templates."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
prerequisites:
  commands: [curl, jq]
metadata:
  hermes:
    tags: [social-media, bluesky, facebook, linkedin, telegram, whatsapp, journalism, accessibility, pcd]
    homepage: https://github.com/openclaw/openclaw
---

# Social Media Multi-Plataforma — Jornalista Inclusivo

Skill para **publicação automatizada em múltiplas plataformas** a partir do RSS do Jornalista Inclusivo (e outras fontes), com foco em jornalismo inclusivo, acessibilidade e direitos PcD no Brasil.

### ⚠️ Container Runtime Fixes (Aplicados 2026-07-03) — **Ler antes de usar no container Hermes/Umbrel**

| Problema | Causa | Fix Aplicado |
|----------|-------|--------------|
| `xmllint: command not found` | Container sem `libxml2-utils` (sem apt root) | **Python `xml.etree.ElementTree`** no script (stdlib, sem deps) |
| RSS retorna vazio | WordPress redirect 301 `/feed` → `/feed/` | `curl -sL` (follow redirects) / Python segue auto |
| HTTP 403 Forbidden | Cloudflare WAF bloqueia sem User-Agent | Header `User-Agent: Mozilla/5.0 (compatible; JINC-RSS-Bot/1.0)` |
| Script para na 1ª plataforma que falha | `set -e` + exit code 2 (skip) | `|| true` após cada chamada de plataforma |
| Configs de CLI não persistem | `HOME=/opt/data` (Hermes) vs `HOME=/opt/data/home` (subprocessos) | **Sempre `HOME=/opt/data/home`** para bsky, xurl, etc. |
| `bsky login` falha | CLI v0.0.81 usa **argumentos posicionais** (não flags `-a`/`-p`) | `bsky login handle password` (sem flags) |
| Post excede 300 grafemas | Bluesky limita a 300 grafemas (não bytes/chars) | Truncar texto ~280 chars; usar link curto |
| **xurl não instalado** | Binário não existe no container | **Instalar via Go ou baixar release** (ver seção X/Twitter) |
| **TELEGRAM_CHANNEL_ID não definido** | `.env` usa `TELEGRAM_HOME_CHANNEL=965862678`, script espera `TELEGRAM_CHANNEL_ID` | `export TELEGRAM_CHANNEL_ID="${TELEGRAM_CHANNEL_ID:-${TELEGRAM_HOME_CHANNEL}}"` no script/cron |
| **Token Telegram inválido (HTTP 401)** | Token `876079...WpOY` rejeitado pelo servidor | Regenerar no @BotFather → atualizar Env var Umbrel → restart app |

> **Detalhes completos**: `references/container-runtime-fixes.md` + `references/bluesky-post-limits.md` + `references/bluesky-cli-notes.md` + `references/container-install-workarounds.md` + `references/deployed-state.md`

---

## Plataformas Suportadas

| Plataforma | CLI/Tool | Auth | Status | Limitações |
|------------|----------|------|--------|------------|
| **X/Twitter** | `xurl` | OAuth 2.0 PKCE | ✅ Pronto | Requer app aprovado no developer.x.com |
| **Bluesky** | `bsky` (Go) / `atproto` CLI / API direta | App Password / OAuth | ✅ Viável | API aberta (AT Protocol), sem rate limit agressivo |
| **Facebook Pages** | `facebook-cli` / Graph API direta | OAuth + Page Access Token | ⚠️ Parcial | Requer **App Review** para `pages_manage_posts`; só Pages (não perfis) |
| **LinkedIn** | `linkedin-cli` / API direta | OAuth 2.0 | ⚠️ Restrito | **Partner Program** obrigatório para postar; rate limits estritos |
| **Telegram Channel** | Bot API (HTTP) / `telegram-cli` | Bot Token | ✅ Nativo | Já configurado no Hermes Gateway; só canais/grupos onde bot é admin |
| **WhatsApp Business** | WhatsApp Cloud API / On-premise | Bearer Token (Cloud) | ⚠️ Somente Business | **Não funciona com conta pessoal**; requer Meta Business Verified |

---

## Cron Jobs — Natural Language Output Pattern (Standardizado 2026-07-21)

**Todos os cronjob scripts que entregam no Telegram DEVEM outputar em linguagem natural Português**, não JSON bruto. Este padrão foi estabelecido na sessão 2026-07-21 e aplicado a todos os watchdogs/monitors.

### Padrão Unificado

```python
# 1. Silent exit quando nada a reportar (watchdog pattern)
if not changes and not errors:
    return 0  # Sem output = sem mensagem no Telegram

# 2. Com mudanças/alertas: relatório estruturado em linguagem natural
lines = [f"📊 **{job_name}** — {datetime.now().strftime('%d/%m/%Y %H:%M')}"]
for item in items:
    lines.append(f"\n  • **{item.title}**")
    lines.append(f"    {item.detail}")

# Status claro
if critical:
    lines.append("\n⚠️ **ATENÇÃO**: ação necessária")
elif warning:
    lines.append("\n⚡ **CUIDADO**: monitorar")
else:
    lines.append("\n✅ **OK**: dentro da normalidade")

lines.append(f"\n---\n*Verificação automática a cada {interval} via Hermes cron*")
print("\n".join(lines))
```

### Elementos Obrigatórios
- **Markdown** para renderização no Telegram
- **Emojis** para escaneamento visual rápido
- **Números** com separador de milhares (`1,234`)
- **Status line** explícita (✅ OK / ⚡ CUIDADO / ⚠️ ATENÇÃO / ❌ ERRO)
- **Footer** com contexto de automação
- **Silent exit** (return 0, no output) quando nada a reportar

### Aplicado a (scripts em `/opt/data/scripts/`):
| Script | Cronjob | Descrição |
|--------|---------|-----------|
| `check_openrouter_rate.py` | `e11c70a86885` (30min) | OpenRouter rate-limit watchdog |
| `moltbook_monitor.py` | `582cdb557284` (15min) | Moltbook comentários + ciclo Auditor |
| `moltbook_verification_checker.py` | `7f7cd6d2f4b1` (5min) | Verificação challenges posts pendentes |
| `watch_hermes_shared.py` | `e005e2a045b5` (15min) | Watchdog pasta hermes-shared + mini-RAG |
| `backup-hermes-selective.sh` | `fbb2f2b8405a` (diário 03:00) | Backup seletivo (sem segredos) |

---

## 1. Bluesky (AT Protocol)

### Instalação

**Opção A: bsky CLI (Go) - recomendado** (requer Go 1.26+)
```bash
go install github.com/mattn/bsky@latest
```

**Opção B: Download direto do binário (sem Go, sem unzip) — FUNCIONA NO CONTAINER UMBREL**
```bash
# No container Hermes (onde apt/apk não têm permissão de root):
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
```
> **Nota**: O asset no GitHub Releases é `bsky-linux-<version>.zip` (não `.tar.gz`). Use a versão mais recente em https://github.com/mattn/bsky/releases.

**Opção C: atproto CLI (Node)**
```bash
npm install -g @atproto/cli
```

**Opção D: API direta via curl (sem dependências)**

### Autenticação (App Password)

```bash
# 1. Criar App Password no Bluesky
# Settings → Privacy → App Passwords → Create
# Nome: "JINC Bot" → Copiar senha gerada

# 2. Login (fora da sessão do agente, no terminal do container)
# IMPORTANTE: Use HOME=/opt/data/home para o container Hermes
# ATENÇÃO: bsky CLI v0.0.81 usa ARGUMENTOS POSICIONAIS (não flags -a/-p)
# Handle correto: inclusivo.bsky.social
HOME=/opt/data/home /opt/data/home/.local/bin/bsky login \
  inclusivo.bsky.social \
  SUA_APP_PASSWORD_AQUI

# 3. Testar
HOME=/opt/data/home /opt/data/home/.local/bin/bsky post "Teste JINC 🧵 #Acessibilidade"
```

> **Nota**: O comando é `bsky login` (não `bsky auth login`). Config salva em `~/.config/bsky/` (resolvido via `HOME=/opt/data/home` → `/opt/data/home/.config/bsky/`).
> 
> **Umbrel env vars:** Tokens like `TELEGRAM_BOT_TOKEN` are stored in `/opt/data/.env` but **not** exported to cron/shell. Load them before running the script:  
> `export $(grep -E '^(TELEGRAM|BSKY|FB_)_' /opt/data/.env | xargs)`  
> **Pitfall:** `.env` uses `TELEGRAM_HOME_CHANNEL`, but the script expects `TELEGRAM_CHANNEL_ID`. Map it: `export TELEGRAM_CHANNEL_ID="${TELEGRAM_CHANNEL_ID:-${TELEGRAM_HOME_CHANNEL}}"`

### Postar
```bash
# Texto simples
bsky post "Novo artigo: \"Título\" 🔗 https://link #Acessibilidade #PcD"

# Com imagem
bsky post "Texto..." --image /path/to/image.jpg

# Thread
bsky post "1/3 Primeiro post" && bsky post "2/3 Segundo" --reply-to POST_URI && bsky post "3/3 Terceiro" --reply-to POST_URI
```

### Rate Limits
- **Posts**: ~300/15min (generoso)
- **Images**: 100/15min
- **Sem custo financeiro**

---

## 2. Facebook Pages (Graph API)

### Pré-requisitos
1. **Meta Developer App** em https://developers.facebook.com
2. **App Review** para permissões: `pages_manage_posts`, `pages_read_engagement`
3. **Page Access Token** (long-lived, 60 dias → renovar)

### Instalação
```bash
# facebook-cli (Python)
pip install facebook-cli
# ou API direta via curl
```

### Autenticação
```bash
# 1. Gerar User Access Token (curto) no Graph Explorer
# 2. Trocar por Long-Lived User Token (60 dias):
curl -X GET "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN"

# 3. Obter Page Access Token:
curl -X GET "https://graph.facebook.com/v19.0/me/accounts?access_token=LONG_LIVED_USER_TOKEN"

# 4. Salvar PAGE_ACCESS_TOKEN (não expira se app em modo Live)
```

### Postar
```bash
# Via curl (simples, sem CLI extra)
curl -X POST "https://graph.facebook.com/v19.0/PAGE_ID/feed" \
  -d "message=Novo artigo: \"Título\" 🔗 https://link #Acessibilidade" \
  -d "access_token=PAGE_ACCESS_TOKEN"

# Com imagem (upload first)
curl -X POST "https://graph.facebook.com/v19.0/PAGE_ID/photos" \
  -F "url=https://exemplo.com/imagem.jpg" \
  -F "caption=Legenda" \
  -F "access_token=PAGE_ACCESS_TOKEN"
```

### Limitações Críticas
- **App Review obrigatório** (pode levar semanas)
- **Só Pages** — perfis pessoais não podem postar via API
- Rate limit: 200 posts/hora por Page

---

## 3. LinkedIn

### Realidade Atual (2024-2025)
- **API pública de postagem DESCONTINUADA** para a maioria
- **Partner Program** obrigatório: https://developer.linkedin.com/partner-programs
- Alternativas não-oficiais (risco de ban): `linkedin-api` (Python), browser automation

### Recomendação
**Não automatize LinkedIn via API** sem parceria oficial. Use:
- Post manual + agendamento nativo do LinkedIn
- Ferramentas de social media management (Buffer, Hootsuite, Later) que têm parceria

---

## 4. Telegram Channel (Bot API)

### Já Configurado no Hermes
O Hermes Gateway já tem bot Telegram configurado. Para postar em canal:

### Pré-requisitos
1. Bot adicionado ao canal como **Administrador** (com permissão "Post Messages")
2. Chat ID do canal (ex: `@jornalistainclusivo` ou `-1001234567890`)

### Postar via curl (simples)
```bash
# Token do bot (já configurado no Hermes gateway)
BOT_TOKEN="SEU_BOT_TOKEN"
CHANNEL_ID="@jornalistainclusivo"  # ou -100xxxxxxxxx

curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
  -d "chat_id=$CHANNEL_ID" \
  -d "text=Novo artigo: \"Título\" 🔗 https://link #Acessibilidade #PcD" \
  -d "parse_mode=Markdown" \
  -d "disable_web_page_preview=false"
```

### Com imagem
```bash
curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendPhoto" \
  -F "chat_id=$CHANNEL_ID" \
  -F "photo=@/path/to/image.jpg" \
  -F "caption=Legenda com link 🔗 https://link"
```

### Vantagens
- **Já funciona** no seu ambiente (gateway configurado)
- Sem rate limit prático para canais
- Suporte nativo a Markdown/HTML
- Entrega garantida (push)

---

## 5. WhatsApp Business (Cloud API)

### Só Conta Business Verificada
- **Não funciona com WhatsApp pessoal**
- Requer: Meta Business Account verificada + WhatsApp Business Account
- Custo: conversas iniciadas pelo usuário (grátis) / iniciadas pela empresa (pago por conversa)

### Setup (Cloud API)
```bash
# 1. Meta Business Manager → WhatsApp → API Setup
# 2. Gerar Permanent Access Token (não expira)
# 3. Phone Number ID + Business Account ID
```

### Postar (Template Message - obrigatório para iniciar conversa)
```bash
# Para enviar notificação, precisa de TEMPLATE APROVADO
curl -X POST "https://graph.facebook.com/v19.0/PHONE_NUMBER_ID/messages" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "5511999999999",
    "type": "template",
    "template": {
      "name": "novo_artigo_jinc",
      "language": { "code": "pt_BR" },
      "components": [{
        "type": "body",
        "parameters": [
          { "type": "text", "text": "Título do artigo" },
          { "type": "text", "text": "https://link" }
        ]
      }]
    }
  }'
```

### Limitações
- **Templates pré-aprovados** pela Meta (24-48h)
- **Opt-in obrigatório** do usuário
- Custo por conversa iniciada pela empresa
- **Não é broadcast** — é 1:1

---

## Arquitetura Recomendada para JINC

```
┌─────────────────┐
│  RSS Feed       │  (jornalistainclusivo.com.br/feed)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  Orchestrator Script (/opt/data/scripts/    │
│  multiplatform-post.sh)                     │
│  - Deduplicação (state file)                │
│  - Formatação por plataforma                │
│  - Rate limiting                            │
│  - Retry/fallback                           │
└────────┬────────────────────┬────────────────┘
         │                    │
    ┌────▼────┐         ┌─────▼─────┐
    │ Bluesky │         │ Telegram  │  ← PRIORIDADE ALTA (fácil, grátis, nativo)
    │ (bsky)  │         │ Channel   │
    └─────────┘         └───────────┘
         │                    │
    ┌────▼────┐         ┌─────▼─────┐
    │ X/Twitter│         │ Facebook  │  ← PRIORIDADE MÉDIA (precisa App Review)
    │ (xurl)  │         │ Page      │
    └─────────┘         └───────────┘
         │
    ┌────▼────┐
    │ WhatsApp│  ← PRIORIDADE BAIXA (só Business, templates, custo)
    │ Cloud   │
    └─────────┘
```

---

## Script Multi-Plataforma (Template + Deployed)

**Template**: `templates/multiplatform-post.sh` (copiar para `/opt/data/scripts/`)

**Template**: `templates/rss-md.py` (script RSS→Telegram simples, copiar para `/opt/data/scripts/`)

**Deployed & Testado**: `/opt/data/scripts/multiplatform-post.sh` — versão com fixes de container aplicados:
- Python XML parser (sem xmllint)
- curl -L para redirect 301
- User-Agent para Cloudflare (`Mozilla/5.0 (compatible; JINC-RSS-Bot/1.0)`)
- `|| true` para set -e resilience
- HOME=/opt/data/home para CLIs
- **Bluesky truncation** (~280 chars) para limite de 300 grafemas
- **Deduplicação por GUID** (não índice numérico) — state file: `GUID|title|link`

```bash
# Deploy do template (já inclui fixes de container)
cp templates/multiplatform-post.sh /opt/data/scripts/multiplatform-post.sh
chmod +x /opt/data/scripts/multiplatform-post.sh

# Testar
/opt/data/scripts/multiplatform-post.sh
```

---

## Cron Jobs — Natural Language Output Pattern (Standardizado 2026-07-21)

**Todos os cronjob scripts que entregam no Telegram DEVEM outputar em linguagem natural Português**, não JSON bruto. Este padrão foi estabelecido na sessão 2026-07-21 e aplicado a todos os watchdogs/monitors.

### Padrão Unificado

```python
# 1. Silent exit quando nada a reportar (watchdog pattern)
if not changes and not errors:
    return 0  # Sem output = sem mensagem no Telegram

# 2. Com mudanças/alertas: relatório estruturado em linguagem natural
lines = [f"📊 **{job_name}** — {datetime.now().strftime('%d/%m/%Y %H:%M')}"]
for item in items:
    lines.append(f"\n  • **{item.title}**")
    lines.append(f"    {item.detail}")

# Status claro
if critical:
    lines.append("\n⚠️ **ATENÇÃO**: ação necessária")
elif warning:
    lines.append("\n⚡ **CUIDADO**: monitorar")
else:
    lines.append("\n✅ **OK**: dentro da normalidade")

lines.append(f"\n---\n*Verificação automática a cada {interval} via Hermes cron*")
print("\n".join(lines))
```

### Elementos Obrigatórios
- **Markdown** para renderização no Telegram
- **Emojis** para escaneamento visual rápido
- **Números** com separador de milhares (`1,234`)
- **Status line** explícita (✅ OK / ⚡ CUIDADO / ⚠️ ATENÇÃO / ❌ ERRO)
- **Footer** com contexto de automação
- **Silent exit** (return 0, no output) quando nada a reportar

### Aplicado a (scripts em `/opt/data/scripts/`):
| Script | Cronjob | Descrição |
|--------|---------|-----------|
| `check_openrouter_rate.py` | `e11c70a86885` (30min) | OpenRouter rate-limit watchdog |
| `moltbook_monitor.py` | `582cdb557284` (15min) | Moltbook comentários + ciclo Auditor |
| `moltbook_verification_checker.py` | `7f7cd6d2f4b1` (5min) | Verificação challenges posts pendentes |
| `watch_hermes_shared.py` | `e005e2a045b5` (15min) | Watchdog pasta hermes-shared + mini-RAG |
| `backup-hermes-selective.sh` | `fbb2f2b8405a` (diário 03:00) | Backup seletivo (sem segredos) |

---

## 1. Bluesky (AT Protocol)

### Fase 1 — Imediata (Esta semana) ✅ FÁCIL
| Ação | Esforço | Status |
|------|---------|--------|
| Instalar `bsky` CLI no container | 5 min | ⬜ |
| Criar App Password no Bluesky | 2 min | ⬜ |
| Configurar `bsky auth login` | 2 min | ⬜ |
| Adicionar bot ao canal Telegram como admin | 1 min | ⬜ |
| Testar post manual no Bluesky + Telegram | 5 min | ⬜ |
| Criar cron job multi-plataforma (Bluesky + Telegram) | 10 min | ⬜ |

### Fase 2 — Curto Prazo (1-2 semanas) ⚠️ MÉDIO
| Ação | Esforço | Bloqueador |
|------|---------|------------|
| Configurar `xurl` para X/Twitter (já iniciado) | 30 min | App approval no developer.x.com |
| Criar Meta Developer App para Facebook | 1 h | App Review (semanas) |
| Obter Page Access Token longo | 30 min | Precisa app Live |
| Testar Facebook Page post | 15 min | Após review |

### Fase 3 — Longo Prazo / Opcional 🔄
| Plataforma | Viabilidade | Recomendação |
|------------|-------------|--------------|
| LinkedIn | Baixa (precisa Partner) | **Não automatizar** — post manual + agendamento nativo |
| WhatsApp Business | Média (custo, templates) | Só se tiver Meta Business verificado + base de opt-in |
| Instagram | Baixa (API só Business, review) | Via Meta Business Suite (manual/agendado) |
| Threads | Média (API nova) | Aguardar estabilização |

---

## Cron Jobs Sugeridos

```bash
# 1. Bluesky + Telegram (FASE 1 - rodar a cada 30 min)
cronjob create --name "JINC Multi: Bluesky+Telegram" \
  --schedule "*/30 * * * *" \
  --prompt "Executar /opt/data/scripts/multiplatform-post.sh (Bluesky + Telegram only)"

# 2. X/Twitter (FASE 2 - após xurl configurado)
cronjob create --name "JINC X/Twitter" \
  --schedule "*/30 * * * *" \
  --prompt "Executar /opt/data/scripts/rss-to-x.sh"

# 3. Facebook Page (FASE 2 - após App Review)
cronjob create --name "JINC Facebook Page" \
  --schedule "0 * * * *" \
  --prompt "Executar script Facebook Page post (hourly, rate limit)"

# 4. RSS→Telegram SIMPLES (backup/diário, já existe como 'jornalistainclusivo/rss-md')
# Schedule: 30 12 * * * (diário 12:30 UTC)
# Comando: /opt/data/voice-venv/bin/python /opt/data/scripts/rss-md.py
# Entrega: origin + telegram:965862678
# ⚠️ Requer fix do bug --feed e venv correto
```

---

## Variáveis de Ambiente Necessárias

Adicionar ao container (Umbrel → Hermes → Env vars) ou `/opt/data/.env`:

```bash
# Bluesky
BSKY_HANDLE=inclusivo.bsky.social
# BSKY_APP_PASSWORD=  # NÃO colocar aqui — usar bsky login interativo

# Telegram (já no gateway, mas para script standalone)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNO_pqrSTUvwxyz
TELEGRAM_CHANNEL_ID=@jornalistainclusivo

# X/Twitter (via xurl config em ~/.xurl)
# XURL_DEFAULT_APP=jinc-app

# Facebook (se/quando)
FB_PAGE_ACCESS_TOKEN=EAAxxxxxxxx
FB_PAGE_ID=123456789
```

---

## ⚠️ Nuance Crítica: HOME Path no Container Umbrel

O Hermes roda com **duas HOMEs diferentes** dependendo do contexto:

| Contexto | HOME | Onde configs salvam |
|----------|------|---------------------|
| Hermes process (dashboard/gateway) | `/opt/data` | `/opt/data/.config/...` |
| **Subprocessos (terminal, cron jobs, scripts)** | `/opt/data/home` | `/opt/data/home/.config/...` |

**Regra de Ouro**: Sempre use `HOME=/opt/data/home` ao rodar CLIs que salvam configuração (bsky, xurl, etc.) dentro de cron jobs ou scripts.

```bash
# ✅ Correto (config visível para subprocessos)
HOME=/opt/data/home /opt/data/home/.local/bin/bsky login -a handle -p password
HOME=/opt/data/home /opt/data/home/.local/bin/xurl auth status

# ❌ Errado (config salva em /opt/data/.config/, cron job não vê)
bsky login -a handle -p password
xurl auth status
```

Veja `references/container-install-workarounds.md` para detalhes e workarounds de instalação sem root/apt.

---

## Referências Relacionadas

- `references/container-runtime-fixes.md` — **Problemas de runtime no container Hermes/Umbrel e correções aplicadas (XML parser, redirect 301, Cloudflare 403, set -e, HOME path)**
- `references/bluesky-post-limits.md` — **Limites de caracteres/grafemas testados (Bluesky 300 grafemas) + CLI notes**
- `references/bluesky-cli-notes.md` — **Instalação e uso do `bsky` CLI no container (sem Go/unzip)**
- `references/container-install-workarounds.md` — Workarounds para instalar ferramentas sem root/apt
- `references/platform-auth-quickref.md` — Referência rápida de autenticação por plataforma
- `references/state-file-format.md` — Formato do state file e lógica de deduplicação por GUID
- `references/rss-multifeed-robustness.md` — robustez ao combinar múltiplos feeds RSS no cron (RSS_URLS + set -u)
- `references/cronjob-templates.md` — Templates de cron jobs por fase
- **NUNCA** coloque tokens/secrets no script ou cron job
- Use **arquivos de config** fora do repo (`~/.config/bsky/`, `~/.xurl/`, `/opt/data/home/.xurl/`)
- No container Umbrel: `HOME=/opt/data/home` para ferramentas CLI
- Tokens do Telegram Bot já estão no gateway Hermes (não duplicar)

---

## Referências Rápidas (arquivos em `references/`)

- `platform-auth-quickref.md` — passo a passo auth por plataforma
- `cronjob-templates.md` — templates de cron jobs por fase
- `bluesky-post-limits.md` — limites de caracteres e formato testado (Bluesky 300 grafemas)
- `state-file-format.md` — formato do state file e lógica de deduplicação por GUID
- `container-runtime-fixes.md` — fixes completos de runtime container (Python XML, curl -L, User-Agent, HOME)
- `bluesky-cli-notes.md` — instalação e uso do `bsky` CLI no container
- `container-install-workarounds.md` — workarounds para instalar ferramentas sem root/apt
- `rss-md-script.md` — **Script rss-md.py (RSS→Telegram simples): bugs, dependências, cron job, diferenças para multiplatform-post.sh**

---

## Próximos Passos Para Você

1. **Bluesky**: `go install github.com/bluesky-social/indigo/cmd/bsky@latest` + criar App Password
2. **Telegram**: Adicionar bot @JornalistaInclusivoBot ao canal como admin
3. **Testar**: `bsky post "Teste JINC 🧵 #Acessibilidade"` e curl Telegram
4. **Eu crio o cron job** multi-plataforma (Bluesky + Telegram) agora
5. **X/Twitter**: Continuar configuração do `xurl` (App Review no developer.x.com)
6. **Facebook**: Criar Meta App → solicitar `pages_manage_posts` → aguardar review

Quer que eu:
1. **Instale o `bsky` CLI** no container agora?
2. **Crie o cron job Fase 1** (Bluesky + Telegram) assumindo que você vai configurar as credenciais?
3. **Gere o script completo** `/opt/data/scripts/multiplatform-post.sh` pronto para<tool_call>
<function=skill_manage>
<parameter=action>
write_file
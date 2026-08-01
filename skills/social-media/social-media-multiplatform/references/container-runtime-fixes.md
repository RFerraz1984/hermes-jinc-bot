# Container Runtime Fixes — Hermes/Umbrel

Problemas encontrados e correções aplicadas ao rodar scripts de social media no container Hermes (Umbrel app).

## Problemas e Correções

| Problema | Causa | Fix Aplicado |
|----------|-------|--------------|
| `xmllint: command not found` | Container sem `libxml2-utils` (sem apt root) | **Python `xml.etree.ElementTree`** no script (stdlib, sem deps) |
| RSS retorna vazio | WordPress redirect 301 `/feed` → `/feed/` | `curl -sL` (follow redirects) / Python segue auto |
| HTTP 403 Forbidden | Cloudflare WAF bloqueia sem User-Agent | Header `User-Agent: Mozilla/5.0 (compatible; JINC-RSS-Bot/1.0)` |
| Script para na 1ª plataforma que falha | `set -e` + exit code 2 (skip) | `|| true` após cada chamada de plataforma |
| Configs de CLI não persistem | `HOME=/opt/data` (Hermes) vs `HOME=/opt/data/home` (subprocessos) | **Sempre `HOME=/opt/data/home`** para bsky, xurl, etc. |
| `bsky login` falha | CLI v0.0.81 usa **argumentos posicionais** (não flags `-a`/`-p`) | `bsky login handle password` (sem flags) |
| Post excede 300 grafemas | Bluesky limita a 300 grafemas (não bytes/chars) | Truncar texto ~280 chars; usar link curto |
| `jq: command not found` | Container não tem `jq` e `apt-get` exige root | **Download binary direto** para `~/.local/bin/jq` |
| Variáveis `.env` não carregadas no cron | Cron job do Umbrel não herda `.env` automaticamente | **`set -a; source /opt/data/.env; set +a`** antes do script |
| **xurl não instalado** | Binary faltando no container | **Instalar via Go ou download release** — veja seção X/Twitter |
| **TELEGRAM_CHANNEL_ID undefined** | `.env` usa `TELEGRAM_HOME_CHANNEL=965862678`, script espera `TELEGRAM_CHANNEL_ID` | `export TELEGRAM_CHANNEL_ID="${TELEGRAM_CHANNEL_ID:-${TELEGRAM_HOME_CHANNEL}}"` no topo do script |
| **Telegram token inválido (HTTP 401)** | Token `876079...WpOY` rejeitado pelo servidor | Regenerar no @BotFather → atualizar Env var no Umbrel → restart app |
| **TELEGRAM_CHANNEL_ID formato** | Canal Telegram exige prefixo `-100` (ex: `-1001454737963`), não ID bruto | Garantir `-100` prefix ao definir no `.env` / Umbrel Env vars |
| **xurl instalação** | Binary faltando no container sem Go | **install.sh oficial** (`curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh \| bash`) |

## Python XML Parser (Substitui xmllint)

```python
import xml.etree.ElementTree as ET

def parse_rss(rss_content):
    root = ET.fromstring(rss_content)
    items = []
    for item in root.findall('.//item'):
        title = item.findtext('title', '').strip()
        link = item.findtext('link', '').strip()
        guid = item.findtext('guid', '').strip()
        if title and link:
            items.append({
                'id': guid or link,
                'title': title,
                'link': link
            })
    return items
```

## cURL com Redirect e User-Agent

```bash
curl -sL \
  -H "User-Agent: Mozilla/5.0 (compatible; JINC-RSS-Bot/1.0)" \
  "https://jornalistainclusivo.com.br/feed/"
```

- `-L` = segue redirects (301/302)
- `-s` = silent
- User-Agent evita 403 do Cloudflare

## Resilience para set -e

```bash
# Em vez de falhar o script todo:
post_bluesky "$title" "$link" || true
post_telegram "$title" "$link" || true
post_x "$title" "$link" || true

# Cada plataforma tenta independentemente
```

## HOME Path no Container Umbrel

| Contexto | HOME | Onde configs salvam |
|----------|------|---------------------|
| Hermes process (dashboard/gateway) | `/opt/data` | `/opt/data/.config/...` |
| **Subprocessos (terminal, cron jobs, scripts)** | `/opt/data/home` | `/opt/data/home/.config/...` |

**Regra de Ouro**: Sempre use `HOME=/opt/data/home` ao rodar CLIs que salvam configuração (bsky, xurl, etc.) dentro de cron jobs ou scripts.

```bash
# ✅ Correto
HOME=/opt/data/home /opt/data/home/.local/bin/bsky login -a handle -p password
HOME=/opt/data/home /opt/data/home/.local/bin/xurl auth status

# ❌ Errado
bsky login -a handle -p password
xurl auth status
```

## bsky CLI v0.0.81 — Argumentos Posicionais

```bash
# ✅ Correto (argumentos posicionais)
HOME=/opt/data/home /opt/data/home/.local/bin/bsky login inclusivo.bsky.social SUA_APP_PASSWORD

# ❌ Errado (flags não existem nesta versão)
bsky login -a inclusivo.bsky.social -p SUA_APP_PASSWORD
```

## Install bsky CLI sem Go/unzip (Container Umbrel)

```bash
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

Adicionar isso no topo de `/opt/data/scripts/multiplatform-post.sh` e scripts similares.

> **Fix aplicado 2026-07-05**: Patch em `/opt/data/scripts/multiplatform-post.sh` linhas 8-12:
> ```bash
> # Carregar variáveis de ambiente do .env (necessário para cron jobs)
> if [[ -f "/opt/data/.env" ]]; then
>     export $(grep -E '^(TELEGRAM_BOT_TOKEN|TELEGRAM_CHANNEL_ID|TELEGRAM_HOME_CHANNEL|FB_PAGE_ACCESS_TOKEN|FB_PAGE_ID)=' /opt/data/.env | xargs)
> fi
> ```
> Isso garante que cron jobs herdem tokens e IDs sem depender de env vars do container.

---

## Instalar `jq` sem Root (Container Umbrel)

O script `multiplatform-post.sh` usa `jq` para validar respostas da API do Telegram e Facebook. O container pode não ter `jq` e `apt-get` exige root.

```bash
mkdir -p /opt/data/home/.local/bin
curl -sL https://github.com/jqlang/jq/releases/download/jq-1.7.1/jq-linux-amd64 \
  -o /opt/data/home/.local/bin/jq
chmod +x /opt/data/home/.local/bin/jq
/opt/data/home/.local/bin/jq --version
```

Configure o `PATH` antes de rodar o script:

```bash
export PATH="/opt/data/home/.local/bin:$PATH"
```

---

## PATH Fix para Cron Jobs (Adicionado 2026-07-05)

O gateway container roda com PATH mínimo (`/usr/local/bin:/usr/bin:/bin`). Cron jobs **não herdam** PATH do `.env` a menos que configurado explicitamente.

**Fix no Umbrel Settings → Hermes → Env vars (ou `/opt/data/.env`):**
```bash
PATH=/opt/data/.npm-global/bin:/opt/data/bin:/opt/data/home/.local/bin:$PATH
```

Isso habilita todos os CLIs:
- `raft` → `/opt/data/.npm-global/bin/raft`
- `cosign` → `/opt/data/bin/cosign`
- `bsky` → `/opt/data/home/.local/bin/bsky`
- `xurl` → `/opt/data/home/.local/bin/xurl` (após instalar)
- `jq` → `/opt/data/home/.local/bin/jq`

> **Nota**: Adicionado ao `/opt/data/.env` na sessão 2026-07-05 + gateway restart.
> Em Umbrel, preferir Settings → Hermes → Env vars (persistente em updates).

---

## Carregar `.env` em Scripts Standalone com Mapeamento Crítico

```bash
# Carregar todas as vars TELEGRAM_, BSKY_, FB_, XURL_, GROQ_, HF_, TAVILY_, OPENAI_, OLLAMA_, GITHUB_
export $(grep -E '^(TELEGRAM|BSKY|FB_|XURL|GROQ|HF|TAVILY|OPENAI|OLLAMA|GITHUB)_' /opt/data/.env | xargs)

# Mapeamento CRÍTICO: .env usa TELEGRAM_HOME_CHANNEL, script espera TELEGRAM_CHANNEL_ID
export TELEGRAM_CHANNEL_ID="${TELEGRAM_CHANNEL_ID:-${TELEGRAM_HOME_CHANNEL}}"
```

Adicionar isso no topo de `/opt/data/scripts/multiplatform-post.sh` e scripts similares.
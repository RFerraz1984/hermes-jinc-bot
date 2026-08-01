# Deployed State — JINC Social Media Automation (2026-07-05)

Estado atual do sistema em produção no container Hermes/Umbrel.

---

## Cron Jobs Ativos

| Job ID | Nome | Schedule | Status | Última Execução |
|--------|------|----------|--------|-----------------|
| `1befd3e63b80` | monthly-backup | `0 2 1 * * *` (1º do mês 02:00) | ✅ Ativo | Nunca |
| `a4fbf1ca4981` | daily-security-check | `30 11 * * *` (diário 11:30) | ✅ Ativo | 2026-07-02 OK |
| `e127c8d3659a` | **JINC Multi: Bluesky + Telegram** | `*/30 * * * *` (a cada 30 min) | ✅ Ativo | 2026-07-06 00:32 OK (0 new) |
| `54008bb9bacd` | tts-pt-br-daily-check | `0 9 * * *` (diário 09:00) | ✅ Ativo | Nunca |
| `d52faa4a94ae` | jornalistainclusivo/rss-md | `30 12 * * *` (diário 12:30) | ✅ Ativo | Nunca |

**Removidos (duplicados/pausados):**
- `d9714b6f412c` — Auto-post RSS → X/Twitter (pausado)
- `e978d680a4f8` — daily-security-check-pattern-b (duplicado .sh)
- `3b2490f7215f` — monthly-backup-pattern-b (duplicado .sh)

---

## Scripts em Produção

| Script | Localização | Status | Notas |
|--------|-------------|--------|-------|
| `multiplatform-post.sh` | `/opt/data/scripts/multiplatform-post.sh` | ✅ **Produção** | Bluesky + Telegram Channel; carrega `.env`; Python XML parser; dedup por GUID |
| `security-daily-check.py` | `/opt/data/scripts/security-daily-check.py` | ✅ Produção | Daily security check (cron `a4fbf1ca4981`) |
| `monthly-backup.py` | `/opt/data/scripts/monthly-backup.py` | ✅ Produção | Monthly backup (cron `1befd3e63b80`) |
| `rss-md.py` | `/opt/data/scripts/rss-md.py` | ⚠️ Precisa fix | Cron `d52faa4a94ae` — bug `--feed` + venv |
| `rss-to-x.sh` | `/opt/data/scripts/rss-to-x.sh` | 📦 Standby | Para X/Twitter quando xurl autenticado |

---

## Binários Instalados no Container

| Ferramenta | Versão | Local | Como instalado |
|------------|--------|-------|----------------|
| `bsky` | v0.0.81 | `/opt/data/home/.local/bin/bsky` | Python download + unzip (sem Go) |
| `xurl` | v1.2.2 | `/opt/data/home/.local/bin/xurl` | `install.sh` oficial (curl \| bash) |
| `jq` | 1.7.1 | `/opt/data/home/.local/bin/jq` | Binary direto GitHub releases |
| `raft` | v0.0.15 | `/opt/data/.npm-global/bin/raft` | npm global (`/opt/data/.npm-global`) |
| `cosign` | latest | `/opt/data/bin/cosign` | Binary direto |
| `tirith` | latest | `/opt/data/bin/tirith` | Binary direto |

---

## Variáveis de Ambiente (`.env` + Umbrel Env vars)

```bash
# PATH para cron jobs (adicionado 2026-07-05)
PATH=/opt/data/.npm-global/bin:/opt/data/bin:/opt/data/home/.local/bin:$PATH

# Telegram (Gateway usa para conectar; script usa para postar)
TELEGRAM_BOT_TOKEN=876079...WpOY          # ⚠️ Token rejeitado pelo Telegram (InvalidToken)
TELEGRAM_ALLOWED_USERS=965862678
TELEGRAM_HOME_CHANNEL=965862678
TELEGRAM_HOME_CHANNEL_THREAD_ID=
TELEGRAM_CHANNEL_ID=-1001454737963        # Canal Jornalista Inclusivo (corrigido com -100)

# APIs
OPENROUTER_API_KEY=***
GROQ_API_KEY=***
HF_TOKEN=***
HF_BASE_URL=https://router.huggingface.co/v1
TAVILY_API_KEY=tvly-d...UpzY
GITHUB_TOKEN=***
OPENAI_API_KEY=***
OLLAMA_BASE_URL=http://192.168.1.50:11434
```

---

## Gateway Status (2026-07-05 19:07 UTC)

```json
{
  "gateway_state": "running",
  "platforms": {
    "telegram": { "state": "connected" },
    "whatsapp": { "state": "fatal", "error": "whatsapp_not_paired" },
    "webhook": { "state": "connected" },
    "raft": { "state": "connected" }
  },
  "pid": 1013
}
```

---

## Raft / Hermes External Agent

- **Agent ID**: `e63b5242-0fa2-40be-afd7-03eb9d1f0ef7`
- **Server**: `https://api.raft.build`
- **Profile**: `jornalista-inclusivo-bot`
- **Credential**: `/opt/data/home/.slock/profiles/jornalista-inclusivo-bot/credential.json`
- **Scopes**: channels, knowledge, mentions, reactions, read, send, server, tasks
- **Status**: Connected (bridge auto-spawned via RAFT_PROFILE)

---

## Próximas Ações Pendentes

1. **🔴 CRÍTICO**: Token Telegram inválido — regenerar no @BotFather → atualizar Env var Umbrel → restart app
2. **🟡 MÉDIO**: Testar postagem multi-plataforma quando houver artigo novo no RSS
3. **🟢 BAIXO**: Configurar xurl auth para X/Twitter (aguarda App Review developer.x.com)
4. **🟢 BAIXO**: Fix `rss-md.py` cron job (bug `--feed` + venv correto)
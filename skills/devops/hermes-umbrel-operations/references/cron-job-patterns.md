# Cron Job Configuration Patterns (Session 2026-06-26, updated 2026-07-05)

## Common Cron Job Failures & Fixes

| Failure | Root Cause | Fix |
|---------|------------|-----|
| `ResourceExhausted: Worker local total request limit reached` | Free tier model rate limited (e.g., `nvidia/nemotron-3-ultra-550b-a55b:free` on OpenRouter) | Switch to provider with generous free tier: **Groq** (`llama-3.3-70b-versatile`) |
| `HTTP 404: The model ... does not exist` | Job has `provider: groq` but `model: null` → falls back to default OpenRouter model | Set explicit model in job: `model: "llama-3.3-70b-versatile"`, `provider: "groq"` |
| `Context length exceeded (X tokens)` | Skill loaded (`blogwatcher`) has massive SKILL.md + reference files; blows context | 1. Remove non-existent skills (`social-media` was missing)<br>2. Simplify prompt to limit scope<br>3. Use single focused skill instead of multiple |
| **`raft CLI not found in PATH`** | `/opt/data/.npm-global/bin` not in PATH for cron environment | Add to `.env`: `PATH=/opt/data/.npm-global/bin:/opt/data/bin:/opt/data/home/.local/bin:${PATH}` |
| **`cosign not in PATH`** | `/opt/data/bin` not in PATH | Same PATH fix above |
| **`bsky/xurl: command not found`** | `/opt/data/home/.local/bin` not in PATH | Same PATH fix above |
| **`HTTP 401: Missing Authentication header` (Telegram)** | Script expects `TELEGRAM_CHANNEL_ID` but `.env` has `TELEGRAM_HOME_CHANNEL` | Map in script: `export TELEGRAM_CHANNEL_ID="${TELEGRAM_CHANNEL_ID:-${TELEGRAM_HOME_CHANNEL}}"` |
| **Telegram token invalid (InvalidToken: Not Found)** | Token rejected by Telegram server | Regenerate at @BotFather → update Umbrel Env var → restart Hermes app |
| **Duplicate cron jobs** | Multiple jobs doing same task (e.g., `daily-security-check` + `daily-security-check-pattern-b`) | Remove duplicates via `hermes cronjob remove <id>` |
| **Cron job prompt asks for `edge-tts` but nothing happens / missed run** | Toolset `tts` not loaded because global `toolsets` is a string, or job has no `enabled_toolsets` | Set `enabled_toolsets: ["tts"]` on the job and use explicit `deliver: telegram:<chat_id>` (see TTS section below) |

## Fixing a Broken Cron Job (Step-by-Step)

```bash
# 1. Check current job config
/opt/hermes/.venv/bin/hermes cronjob list

# 2. View job details (shows model/provider)
cat /opt/data/cron/jobs.json | jq '.jobs[] | select(.id=="<job_id>")'

# 3. Fix provider + model explicitly
/opt/hermes/.venv/bin/hermes cronjob update <job_id> \
  --provider groq \
  --model llama-3.3-70b-versatile

# 4. If model still null in jobs.json, patch directly:
# Edit /opt/data/cron/jobs.json, set "model": "llama-3.3-70b-versatile"

# 5. Test run
/opt/hermes/.venv/bin/hermes cronjob run <job_id>
```

## Adding New Provider (Groq Example)

```bash
# 1. Ensure API key in /opt/data/.env (GROQ_API_KEY=***)
# 2. Add provider config
/opt/hermes/.venv/bin/hermes config set providers.groq.base_url https://api.groq.com/openai/v1
/opt/hermes/.venv/bin/hermes config set providers.groq.api_key '${GROQ_API_KEY}'

# 3. Restart gateway to pick up provider
s6-svc -r /run/s6/services/hermes-gateway

# 4. Verify
/opt/hermes/.venv/bin/hermes config show | grep -A2 groq
```

## Skill Context Management for Cron Jobs

- **Large skills** (`blogwatcher` ~15KB SKILL.md + refs) → context explosion in cron runs
- **Fix**: Use minimal skill set, explicit focused prompt, `[SILENT]` pattern for no-op runs
- **Avoid**: Loading multiple heavy skills in one cron job
- **Pattern**: Single skill + concise prompt + token limit awareness

## PATH Fix for Cron Jobs (Session 2026-07-05)

Cron jobs run in minimal environment without the interactive shell PATH. Required fix in `/opt/data/.env`:

```bash
PATH="/opt/data/.npm-global/bin:/opt/data/bin:/opt/data/home/.local/bin:${PATH}"
```

Then restart gateway:

```bash
s6-svc -r /run/s6/services/hermes-gateway
```

This enables:
- `raft` (Raft external agent bridge)
- `cosign` (security verification)
- `bsky` (Bluesky CLI)
- `xurl` (X/Twitter CLI, once installed — see below)
- Any other user-space binaries under `/opt/data`

### Installing xurl (X/Twitter CLI)

```bash
# Install xurl to /opt/data/home/.local/bin (persists across Umbrel restarts)
cd /opt/data && HOME=/opt/data/home curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh | bash

# Verify
/opt/data/home/.local/bin/xurl --version  # Should show version like 1.2.2

# Authenticate (requires X Developer App)
HOME=/opt/data/home /opt/data/home/.local/bin/xurl auth oauth2 --app meu-app @seu_usuario
```

The install script downloads the latest release for your platform and places the binary in `$HOME/.local/bin`. With the PATH fix above, it's available in cron jobs.

## Pattern A vs Pattern B — Scheduler Bug Workaround (Session 2026-07-06)

**Critical finding (Hermes v0.17.0 on Umbrel):** Cron jobs using **Pattern A** (LLM-based, `--skill` + `--deliver telegram`) **do not fire automatically**. The `cron ticker` runs every 60s but jobs with skills never execute on schedule.

| Pattern | Type | Reliability | Use Case |
|---------|------|-------------|----------|
| **A** | LLM + Skill (`hermes cron create ... --skill X --deliver telegram`) | ❌ **Broken** — doesn't fire on schedule | Rich reports, natural language output |
| **B** | Script Standalone (`cronjob tool ... no_agent=true script=foo.py`) | ✅ **Works** — fires reliably | Alert-focused, deterministic output |

**Workaround validated this session:** Migrate Pattern A jobs to Pattern B using the tool `cronjob` action=create with `no_agent=true`.

### Migration executed this session:

| Original (Pattern A) | Migrated (Pattern B) | Template |
|----------------------|----------------------|----------|
| `monthly-backup` (never ran) | `monthly-backup-pattern-b` | `templates/monthly-backup.py` |
| `daily-security-check` (ran once) | `daily-security-check-pattern-b` | `templates/security-daily-check.py` |

**Commands used:**
```bash
# monthly-backup → Pattern B
cronjob create --name "monthly-backup-pattern-b" --schedule "0 2 1 * * *" --script "monthly-backup.py" --no-agent true --deliver "telegram" --workdir "/opt/data"

# daily-security-check → Pattern B
cronjob create --name "daily-security-check-pattern-b" --schedule "30 11 * * *" --script "security-daily-check.py" --no-agent true --deliver "telegram" --workdir "/opt/data"
```

**Both Pattern B scripts tested manually — exit code 0, output delivered to Telegram.**

---

## python-telegram-bot v20+ Async Fix (Session 2026-07-06)

**Issue:** `python-telegram-bot` v20+ makes `Bot.send_message()` async — must be awaited.

**Error:**
```
RuntimeWarning: coroutine 'Bot.send_message' was never awaited
Bot(bot_token).send_message(chat_id=int(channel_id), text=markdown, parse_mode='Markdown', disable_web_page_preview=True)
```

**Fix applied to `/opt/data/scripts/rss-md.py`:**
```python
import asyncio
from telegram import Bot

async def send_telegram(channel_id, markdown):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    bot = Bot(bot_token)
    await bot.send_message(chat_id=int(channel_id), text=markdown, parse_mode='Markdown', disable_web_page_preview=True)

asyncio.run(send_telegram(os.getenv('TELEGRAM_HOME_CHANNEL'), output['markdown']))
```

**Tested with cron job's dedicated venv (`/opt/data/venv/rss-md/bin/python`) — exit code 0, JSON output valid, Telegram message sent.**

---

## Script Wrapper Arguments Not Expanded (Session 2026-07-25)

**Problem:** Cron job with `script: "cron_wrapper.sh \"Backup Seletivo Hermes\" /opt/data/scripts/backup-hermes-selective.sh"` failed with `Script not found: /opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh` — the scheduler treats the entire string as a single script filename instead of parsing arguments.

**Root Cause:** The cron job's `script` field is designed for a single executable file (or shell command when `no_agent=true`). It does not perform shell word-splitting on the value. When the whole `cron_wrapper.sh "args..."` string is stored as the script name, the executor looks for a file literally named `cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh`, which doesn't exist.

**Fix:** Create a dedicated wrapper script that embeds the arguments, then point the cron job to that single script:

```bash
# 1. Create wrapper with baked-in arguments
cat > /opt/data/scripts/backup-hermes-daily.sh << 'EOF'
#!/usr/bin/env bash
/opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh
EOF
chmod +x /opt/data/scripts/backup-hermes-daily.sh

# 2. Update cron job to use the wrapper
/opt/hermes/.venv/bin/hermes cron edit <job_id> --script backup-hermes-daily.sh
```

**Lesson:** Never put shell commands with arguments directly in the `script` field of a cron job. Always use a single executable file as the entry point.

---

### ⚠️ Cron Job Mode Conflict: `skill`/`skills` vs `script`/`no_agent` (Session 2026-07-29)

**Problem:** A cron job configured with BOTH `skill: "moltbook"` / `skills: ["moltbook"]` AND `script: "..."` / `no_agent: true` failed with:
```
RuntimeError: HTTP 400: tool call validation failed: attempted to call tool 'skill_view(name="moltbook")' which was not in request.tools
```

**Root Cause:** The scheduler interprets `skill`/`skills` as "run in agent mode with this skill loaded", while `script` + `no_agent: true` means "run as standalone script". When both are present, the system tries to load the skill in agent mode but the toolset doesn't include `skill_view`, causing the tool call to fail.

**Fix:** Choose ONE mode exclusively:

| Mode | Fields | Use Case |
|------|--------|----------|
| **Agent (Pattern A)** | `skill: "x"`, `skills: ["x"]`, `prompt: "..."` | Rich LLM-driven tasks, natural language output |
| **Script (Pattern B)** | `script: "wrapper.sh"`, `no_agent: true`, `workdir: "/opt/data"` | Deterministic shell/python tasks, reliable scheduling |

**Migration executed this session:**
- Job `3d75d014af16` ("Moltbook Heartbeat"): Removed `skill`/`skills`, set `no_agent: true`, created wrapper script `/opt/data/scripts/moltbook_heartbeat_wrapper.sh`, set `workdir: "/opt/data"`. Job now runs successfully every 4h (verified: last run `2026-07-29T19:30:06.959196+00:00`, status `ok`).

**Lesson:** Never mix `skill`/`skills` with `script`/`no_agent`. The scheduler cannot resolve the conflict. Always audit existing jobs for this pattern.

---

### ⚠️ Tavily MCP OAuth Fails in Containerized Hermes (Added 2026-07-28)

**Sintoma:**
```
MCP OAuth for 'tavily': non-interactive environment and no cached tokens found.
Run `hermes mcp login tavily` interactively first to complete initial authorization.
```

**Causa:** `config.yaml` tem `mcp_servers.tavily.auth: oauth` mas container Hermes não tem browser/TTY para fluxo OAuth interativo.

**Config problemática:**
```yaml
tavily:
  auth: oauth
  enabled: true
  url: https://mcp.tavily.com/mcp/
  headers:
    Authorization: Bearer ***  # placeholder, não funciona com OAuth
```

**Soluções (ordem de preferência):**
1. **API Key direta** — se tem `TAVILY_API_KEY`: mudar `auth: none` + header `Authorization: Bearer $TAVILY_API_KEY`
2. **Desabilitar** — `enabled: false` no config.yaml (para erro imediato)
3. **Login interativo** — `hermes mcp login tavily` em terminal anexado (token expira, não recomendado para cron)

**Ação recomendada:** Verificar se `TAVILY_API_KEY` existe em `/opt/data/.env` e migrar para auth none.

**Padrão geral:** Qualquer MCP server configurado com `auth: oauth` falhará em ambiente headless/containerizado sem browser. Prefira `auth: none` + API key via header, ou desabilite se não crítico.

---

## TTS Cron Job Troubleshooting (Session 2026-07-05)

### Root causes

1. **Global `toolsets` misconfigured as string** — `hermes config set toolsets '[...]'` wrote:
   ```yaml
   toolsets: '[hermes-cli, web, file, cronjob, skills, browser, tts, delegation]'
   ```
   This is a single YAML string, not a list. The gateway cannot load individual toolsets from it, so `tts` may be unavailable.

2. **Job did not declare its own toolset** — `enabled_toolsets: null` made the job depend on the broken global list.

3. **Deliver set to `origin` with `origin: null`** — works only via silent fallback to Telegram home channel; fragile and hard to debug.

### Fix applied

Update the job to carry its own toolset and explicit delivery:

```bash
hermes cronjob update 54008bb9bacd \
  --enabled-toolsets tts \
  --deliver telegram:965862678
```

Or directly in `/opt/data/cron/jobs.json`:

```json
{
  "enabled_toolsets": ["tts"],
  "deliver": "telegram:965862678"
}
```

### Verification

After the update, a manual run (`hermes cronjob run <id>`) produced:

```text
Job 'tts-pt-br-daily-check' completed successfully
delivered to telegram:965862678 via live adapter
```

Audio file generated:
```bash
/opt/data/acessibilidade-jornalismo-direito.mp3  # 19.584 bytes
```

### TTS dependency check

```bash
# Required: edge-tts in the voice venv
/opt/data/voice-venv/bin/python -c "import edge_tts; print(edge_tts.__version__)"

# Manual synthesis test
/opt/data/voice-venv/bin/python -c "
import edge_tts, asyncio
async def main():
    await edge_tts.Communicate('Acessibilidade em jornalismo é direito!', 'pt-BR-FranciscaNeural').save('/tmp/tts_test.mp3')
asyncio.run(main())
"
```

### Recommendation

Always set `enabled_toolsets` on cron jobs that need a specific toolset. Do not rely on the global `toolsets` list until the config.yaml format is corrected to a real YAML list. If a TTS/audio cron job must run, set:

```json
"enabled_toolsets": ["tts"]
```

For jobs that only run shell commands, set:

```json
"enabled_toolsets": ["terminal"]
```

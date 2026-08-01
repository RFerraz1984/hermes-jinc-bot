---
name: cronjob-python-environment
priority: 500
category: devops
description: Criar e gerenciar ambientes virtuais para scripts Python usados em cronjobs com isolamento de dependências
---

### Cron Jobs — Natural Language Output Pattern (Standardizado 2026-07-21)

**Todos os cronjob scripts Python que entregam no Telegram DEVEM outputar em linguagem natural Português**, não JSON bruto. Este padrão foi estabelecido na sessão 2026-07-21 e aplicado a todos os watchdogs/monitors.

#### Padrão Unificado

```python
# 1. Silent exit quando nada a reportar (watchdog pattern)
if not changes and not errors:
    sys.exit(0)  # Sem output = sem mensagem no Telegram

# 2. Com mudanças/alertas: relatório estruturado em linguagem natural
from datetime import datetime
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

#### Elementos Obrigatórios
- **Markdown** para renderização no Telegram
- **Emojis** para escaneamento visual rápido
- **Números** com separador de milhares (`1,234`)
- **Status line** explícita (✅ OK / ⚡ CUIDADO / ⚠️ ATENÇÃO / ❌ ERRO)
- **Footer** com contexto de automação
- **Silent exit** (`sys.exit(0)`, no output) quando nada a reportar

#### Aplicado a (scripts em `/opt/data/scripts/`):
| Script | Cronjob | Descrição |
|--------|---------|-----------|
| `check_openrouter_rate.py` | `e11c70a86885` (30min) | OpenRouter rate-limit watchdog |
| `moltbook_monitor.py` | `582cdb557284` (15min) | Moltbook comentários + ciclo Auditor |
| `moltbook_verification_checker.py` | `7f7cd6d2f4b1` (5min) | Verificação challenges posts pendentes |
| `watch_hermes_shared.py` | `e005e2a045b5` (15min) | Watchdog pasta hermes-shared + mini-RAG |
| `backup-hermes-selective.sh` | `fbb2f2b8405a` (diário 03:00) | Backup seletivo (sem segredos) |

---

### Workflow recomendado

1. ✅ **Preparação do ambiente** (venv isolado)
   `python3 -m venv /opt/data/venv/nome-do-ambiente`

2. 🔄 **Instalar dependências** — **Opção A: uv (recomendado, mais rápido)**
   `/opt/data/venv/nome-do-ambiente/bin/uv pip install feedparser PyYAML python-telegram-bot`
   
   **Opção B: pip padrão**
   `/opt/data/venv/nome-do-ambiente/bin/pip install feedparser PyYAML python-telegram-bot`

3. ▶️ **Executar script com Python isolado** (caminho absoluto — sem `source activate`)
   `/opt/data/venv/nome-do-ambiente/bin/python /opt/data/scripts/nome-do-script.py`


### Diretrizes técnicas
- Utilize caminhos absolutos para evitar dependência da shell init
- Valide o ambiente com: `import sys; print(sys.executable)`
- **Evite `source activate` em cronjobs** — use o caminho absoluto do Python do venv
- **python-telegram-bot v20+ é assíncrono** — use `asyncio.run()` + `await bot.send_message(...)` (ver exemplo abaixo)


### ⚡ Pattern: Telegram Bot Async (python-telegram-bot v20+)
```python
import asyncio
from telegram import Bot
import os

async def send_telegram(channel_id, markdown):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    bot = Bot(bot_token)
    await bot.send_message(
        chat_id=int(channel_id),
        text=markdown,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

# No main (fora de função async):
asyncio.run(send_telegram(os.getenv('TELEGRAM_HOME_CHANNEL'), output['markdown']))
```

---

### Accessibility Audit Toolkit — Cron Deploy & Runtime (Session 2026-07-28)

**Context:** Deploy do `accessibility-audit-toolkit` no Hermes/Umbrel — instalação de deps, teste CLI, criação de cron jobs.

#### 1. Hermes Cron — Criação Individual (não `--from-file`)
`hermes cron create --from-file` **não existe**. Crie jobs um a um via CLI:

```bash
/opt/hermes/bin/hermes cron create \
  --name "audit-daily-jinc" \
  --schedule "0 3 * * *" \
  --skill accessibility-audit-toolkit \
  --prompt "Auditoria diária automática (axe + pa11y + lighthouse) dos sites Jornalista Inclusivo. Use --url-list /opt/data/urls_production.txt --auto-only --output /opt/data/audits/daily_$(date +%F)" \
  --deliver "telegram:965862678"
```

#### 2. Playwright Browser Path no Container Hermes
Container não tem write em `/opt/hermes/.playwright`. Use **sempre**:
```bash
PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright python -m scripts.audit ...
```
No cron job, exporte no prompt:
```bash
export PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright
```

#### 3. Gerenciamento Python com `uv` (PEP 668)
Sistema usa `externally-managed-environment`. Use `uv`:
```bash
uv pip install -r requirements.txt
uv pip install pytest pytest-asyncio
```

#### 4. Node Binaries Path
`npm install -g` instala em `/opt/data/.npm-global/bin/`. Exporte:
```bash
export PATH="/opt/data/.npm-global/bin:$PATH"
axe --version && pa11y --version && lhci --version
```

#### 5. Variáveis de Ambiente no Prompt do Cron Job
Inclua setup completo no `--prompt` do cron:
```bash
export PATH="/opt/data/.npm-global/bin:$PATH"
export PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright
cd /opt/data/skills/journalism/accessibility-audit-toolkit
python -m scripts.audit --url-list /opt/data/urls_production.txt --auto-only --output /opt/data/audits/daily_$(date +%F)
```

#### 6. URL List para Produção
Mantenha `/opt/data/urls_production.txt`:
```
https://jornalistainclusivo.com
https://pcd.dataverso.org
https://dados.dataverso.org/pcd
```
Use `--url-list` (evita crawl/discovery que pode travar em timeout).

---

### Roteiro para feeds RSS (references/feedparser.md):
```bash
# Comando recomendado para feeds
/opt/data/venv/rss-md/bin/python /opt/data/scripts/rss-md.py \
  --feed https://jornalistainclusivo.com.br/feed
```
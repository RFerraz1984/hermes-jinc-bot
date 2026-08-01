# Cron Job: JINC Gmail Triagem 15d — Complete Setup (session 2026-07-28)

## Cron Job Configuration

**Job ID:** `12d59b921ae1`
**Name:** `JINC Gmail triagem-15d (placeholder)`
**Schedule:** `0 9 * * *` (daily 09:00 UTC = 06:00 BRT)
**Script:** `jinc_gmail_triagem_15d_filtered.py`
**Model:** `nvidia/nemotron-3-ultra-550b-a55b:free` (OpenRouter)
**Delivery:** `origin,telegram` (chat 965862678)
**State:** ✅ `enabled: true`, `state: scheduled`
**Next run:** `2026-07-29T09:00:00+00:00`

## Script Chain

```
/opt/data/scripts/jinc_gmail_triagem_15d_filtered.py
    └─► subprocess.run() → /opt/data/scripts/jinc_gmail_triagem_15d.py
            └─► IMAP search (optimized header-first)
            └─► Dedupe by Message-ID → /opt/data/journali/processed-message-ids.jsonl
            └─► Classify: release | sugestao_de_pauta
            └─► Output: JSON (stdout) + Markdown file
    └─► stdin (JSON) → smart_notify_filter.py --job-name "JINC Gmail Triagem" --exit-code $?
            └─► Formats for Telegram (PT-BR natural language)
            └─► Delivers to chat 965862678
```

## Config File: `/opt/data/journali/imap-config.json`

```json
{
  "host": "imap.gmail.com",
  "port": 993,
  "username": "jornalistainclusivo@gmail.com",
  "password": "xmnm jggs xbms vdfl",  // App Password (16 chars, no spaces in use)
  "search_folder": "INBOX"
}
```

**Note:** Password stored with spaces in JSON; script removes spaces at runtime (`cfg['password'].replace(' ', '')`).

## Dedupe Store: `/opt/data/journali/processed-message-ids.jsonl`

Append-only, one Message-ID per line. Created automatically on first run.
```text
<1781850437.15532700.1785147313985@ltx1-app86970.prod.linkedin.com>
<6a675968.0fcb56c6.2f02b7.fa84googlealerts@google.com>
...
```

## Output Files

- **Markdown daily:** `/opt/data/journali/triagem-YYYY-MM-DD.md`
- **Telegram:** Single message with summary + top 3 releases + top 3 sugestões + link to markdown

## Test Results (2026-07-28)

| Run | Emails scanned | Matches | New items | Markdown |
|-----|----------------|---------|-----------|----------|
| 1 (manual) | 100 (of 578) | 8 | 8 | ✅ triagem-2026-07-28.md |
| 2 (dedupe test) | 100 | 8 | 0 | ✅ (empty sections) |
| 3 (cron run) | 100 | 8 | 0 | ✅ |

All runs: **exit 0**, Telegram delivered via `smart_notify_filter.py`.

## Keywords Monitored (11 terms)

| PT-BR (display) | IMAP search (ASCII) |
|-----------------|---------------------|
| acessibilidade | acessibilidade |
| deficiência | deficiencia |
| inclusão | inclusao |
| autismo | autismo |
| neurodiversidade | neurodiversidade |
| PCD | pcd |
| TEA | tea |
| WCAG | wcag |
| e-MAG | e-mag |
| capacitismo | capacitismo |
| pessoa com deficiência | pessoa com deficiencia |

## Dependencies

- Python stdlib only (`imaplib`, `email`, `json`, `datetime`, `pathlib`, `subprocess`)
- `smart_notify_filter.py` at `/opt/data/scripts/smart_notify_filter.py`
- `.env` at `/opt/data/.env` (for Telegram bot token if needed by filter)

## Commands

```bash
# Manual test (full script)
python3 /opt/data/scripts/jinc_gmail_triagem_15d.py

# Manual test (filtered for Telegram)
python3 /opt/data/scripts/jinc_gmail_triagem_15d_filtered.py

# Cron job manual run
hermes cron run 12d59b921ae1

# Check cron job status
hermes cron list | grep -A 10 "12d59b921ae1"
```

## Pitfalls Avoided (encoded in skill)

1. **IMAP SEARCH with accents** → client-side filtering with `CHARSET UTF-8 SINCE date`
2. **Timeout on 500+ emails** → limit to 100 most recent, header-first fetch
3. **Placeholder credentials** → script validates and exits with clear message
4. **No deduplication** → Message-ID append-only store
5. **Raw JSON to Telegram** → `smart_notify_filter.py` wrapper formats PT-BR natural language
6. **Cron running before config ready** → created paused, updated script, then resumed
# Cronjob Output Pattern — Natural Language for Telegram

**Established:** Session 2026-07-21  
**Context:** All cronjob scripts delivering to Telegram MUST output in natural language Portuguese, not raw JSON. This was a key correction made during the session.

## Pattern

### BAD — Raw JSON (hard to read on mobile)
```python
print(json.dumps({"remaining": 150, "limit": 200, "pct": 75}))
```

### GOOD — Natural language with emojis and structure
```python
report = f"""📊 **Relatório de Limites OpenRouter**
🔑 Chave: `{label}`

**Limites atuais:**
  • Requisições/min: {req_remain:,}/{req_limit:,} restantes ({req_pct:.1f}% livre)
  • Tokens/min: {tok_remain:,}/{tok_limit:,} restantes ({tok_pct:.1f}% livre)
  • Requisições/dia: {day_remain:,}/{day_limit:,} restantes ({day_pct:.1f}% livre)

**Status:** {status}

---
*Verificação automática a cada 30 min via Hermes cron*"""
print(report)
```

## Key Elements
- Markdown formatting for Telegram rendering
- Emojis for quick visual scanning
- Human-readable numbers with thousands separators
- Clear status line (OK / ⚠️ CUIDADO / ⚠️ ATENÇÃO)
- Footer with automation context
- **Silent exit** (return 0, no output) when nothing to report (watchdog pattern)

## Applied To (scripts updated/created in this session)
- `check_openrouter_rate.py` — OpenRouter rate-limit watchdog (updated 2026-07-21)
- `moltbook_monitor.py` — Moltbook comment monitor + Auditor cycle (created 2026-07-21)
- `moltbook_verification_checker.py` — Post verification challenge solver (created 2026-07-21)
- `watch_hermes_shared.py` — Hermes-shared folder watchdog (updated 2026-07-21)
- `backup-hermes-selective.sh` — Selective backup script (updated 2026-07-21)
- `publish.sh` — GitHub repo publisher (created 2026-07-21)

## Cronjob Configurations Created
| Job ID | Name | Schedule | Script |
|--------|------|----------|--------|
| 582cdb557284 | Moltbook Monitor (15min) | `*/15 * * * *` | moltbook_monitor.py |
| 7f7cd6d2f4b1 | Moltbook Verification Checker (5min) | `*/5 * * * *` | moltbook_verification_checker.py |
| 3d75d014af16 | Moltbook Heartbeat | `*/30 * * * *` | moltbook_helpers.py heartbeat |
| e005e2a045b5 | Watchdog hermes-shared | `*/15 * * * *` | watch_hermes_shared.py |
| fbb2f2b8405a | Backup seletivo Hermes | `0 3 * * *` | backup-hermes-selective.sh |
| e11c70a86885 | OpenRouter rate-limit watchdog | `*/30 * * * *` | check_openrouter_rate.py |

## Silent Exit Pattern (Watchdog)
```python
if not new_files and not changed_files and not deleted:
    return 0  # Silent exit - no output = no Telegram message
```
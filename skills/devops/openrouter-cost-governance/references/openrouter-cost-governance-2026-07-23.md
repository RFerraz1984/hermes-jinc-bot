# OpenRouter Cost Governance — Session Detail (2026-07-22/23)

> Captured from session where user added $10 to OpenRouter, used Claude Sonnet 5 for ~1hr, spent $7+.

## Context

- **Budget**: $10/month total
- **Event**: Switched to Claude Sonnet 5 (expensive), ~1hr usage → $7+ spent
- **Remaining**: ~$3 (8.40 shown in guard report)
- **Problem**: No guardrails, no visibility until after the fact

## What Was Built

### Scripts Created

| Script | Purpose | Location |
|--------|---------|----------|
| `check_openrouter_credits.py` | Layer 1: informational watchdog | `/opt/data/scripts/` + `~/.hermes/scripts/` |
| `openrouter_spending_guard.py` | Layer 2: active enforcement | `/opt/data/scripts/` + `~/.hermes/scripts/` |

### Cron Jobs Created (then removed for threshold adjustment)

| Job ID | Name | Schedule | Status |
|--------|------|----------|--------|
| `724ab8bd9889` | OpenRouter Credit Check (30min) | `*/30 * * * *` | ❌ Removed (thresholds too high) |
| `62bcefcb8d56` | OpenRouter Spending Guard (30min) | `*/30 * * * *` | ❌ Removed (thresholds too high) |

### Threshold Issue Identified

Original thresholds in `openrouter_spending_guard.py`:
```python
LIMITE_DIARIO_USD = 5.00      # 50% of monthly budget in 1 day!
LIMITE_SALDO_MINIMO = 10.00   # Higher than total budget!
LIMITE_CRITICO_USD = 20.00    # Impossible threshold
```

**Adjusted for $10/month:**
```python
LIMITE_DIARIO_USD = 0.30      # ~$9/month if sustained
LIMITE_SALDO_MINIMO = 2.00    # 20% reserve
LIMITE_CRITICO_USD = 1.50     # Hard stop
```

### Model Fallback Chain (Free Models)

```python
MODELOS_BLOQUEIO = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",  # 1st choice
    "google/gemma-2-9b-it:free",                # 2nd
    "meta-llama/llama-3.1-8b-instruct:free",    # 3rd
]
```

### Enforcement Mechanism

```python
# Block: switch to free model
set_model(free_model)  # via `hermes config set model.default <model>`

# Unblock: restore previous (with hysteresis)
if daily_spend < LIMITE_DIARIO_USD * 0.5 and remaining > LIMITE_SALDO_MINIMO * 1.5:
    set_model(previous_model)
```

### State Persistence

`/opt/data/openrouter_spending_state.json`:
```json
{
  "blocked": false,
  "previous_model": "openrouter/auto",
  "last_check": "2026-07-23T...",
  "last_daily_usage": 0.00,
  "last_remaining": 8.40,
  "last_action": "🔓 DESBLOQUEADO — Modelo restaurado: `openrouter/auto`"
}
```

## Natural Language Output Pattern (for Telegram)

Standardized in this session, now codified in `cybersecurity-wellbeing` and `social-media-multiplatform` skills:

```python
# Silent exit when OK
if not alerts and not action_taken:
    return 0

# Report
lines = [
    f"🛡️ **OpenRouter Spending Guard** — {ts}",
    f"💰 Saldo: **${remaining:.2f}** / ${total:.2f}",
    f"📅 Gasto hoje: **${daily_usage:.2f}**",
    f"🤖 Modelo atual: `{current_model}`",
]
if action_taken:
    lines.append(f"\n{action_taken}")  # 🔒 BLOQUEADO / 🔓 DESBLOQUEADO
lines.append("\n---\n*Verificação automática a cada 30 min via Hermes cron*")
print("\n".join(lines))
```

## Key Lessons

1. **Thresholds must fit budget** — $5/day makes no sense with $10/month
2. **Hysteresis prevents flapping** — don't revert on first improvement
3. **Free model fallback chain** — always have ordered list of `:free:` models
4. **Persisted state** — survives Hermes/cron restarts
5. **Silent exit** — don't spam Telegram when all OK
6. **Model switch via config** — `hermes config set model.default` is the enforcement lever

## Next Steps (When User Re-enables)

1. Update thresholds in `openrouter_spending_guard.py` to $10/month values
2. Re-create cron jobs with corrected thresholds
3. Test by running `python3 ~/.hermes/scripts/openrouter_spending_guard.py`
4. Verify Telegram delivery works
5. Monitor for 24-48h before considering stable
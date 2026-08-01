---
name: openrouter-cost-governance
description: Two-layer cost governance for OpenRouter API — informational watchdog + active spending guard with automatic model switching. Designed for budgets as low as $10/month.
version: "1.0"
author: Hermes Agent
license: MIT
platforms: [linux]
tags: [openrouter, cost-control, llm-governance, budget-management, hermes-cron]
---

# OpenRouter Cost Governance

> **Origin**: Session 2026-07-22/23 — user spent $7+ in ~1hr on Claude Sonnet 5 with $10 budget. Needed guardrails that **alert then block** expensive models.

## Problem

- OpenRouter has no "hard limit" per key via API (only rate limits)
- `/api/v1/credits` returns account-wide balance
- `/api/v1/auth/key` returns per-key usage: `usage_daily`, `usage_weekly`, `usage_monthly`, `limit`, `limit_remaining`
- Expensive models (Claude Sonnet 5, GPT-4o) burn credits fast; free models (Nemotron 3 Ultra, Gemma 2 9B, Llama 3.1 8B) cost $0

## Solution: Two-Layer Guard

### Layer 1 — Informational Watchdog (`check_openrouter_credits.py`)

- Queries `/credits` + `/auth/key` every 30min via cron
- Natural language report to Telegram
- **Silent exit** when OK (watchdog pattern)
- Alerts on: balance < threshold, daily spend > threshold, % limit critical
- **No enforcement** — visibility only

### Layer 2 — Active Spending Guard (`openrouter_spending_guard.py`)

**Enforcement logic:**
```python
if daily_spend > LIMITE_CRITICO_USD:      BLOCK
elif daily_spend > LIMITE_DIARIO_USD:      BLOCK
elif remaining_balance < LIMITE_SALDO_MINIMO: BLOCK
else:                                      ALLOW
```

**Hysteresis (anti-flapping):**
- Only unblock when: `daily_spend < 50% LIMITE_DIARIO` AND `remaining > 150% LIMITE_SALDO_MINIMO`
- Prevents toggle spam when spend hovers near threshold

**Enforcement mechanism:**
- `hermes config set model.default <free-model>` — switches default model at config level
- Fallback chain (ordered):
  1. `nvidia/nemotron-3-ultra-550b-a55b:free`
  2. `google/gemma-2-9b-it:free`
  3. `meta-llama/llama-3.1-8b-instruct:free`
- Restores previous model when unblocked

**State persisted** in `/opt/data/openrouter_spending_state.json` — survives Hermes/cron restarts.

## Recommended Thresholds (for $10/month budget)

| Threshold | Value | Action |
|-----------|-------|--------|
| `LIMITE_DIARIO_USD` | $0.30 | Alert + block expensive models |
| `LIMITE_SALDO_MINIMO` | $2.00 | Alert + block expensive models |
| `LIMITE_CRITICO_USD` | $1.50 | Hard stop immediate |

> Adjust per actual budget.

## Cron Integration (Hermes)

```bash
# Layer 1: Informational (30min) — delivers to Telegram
cronjob create --name "OpenRouter Credit Check" \
  --schedule "*/30 * * * *" \
  --script "check_openrouter_credits.py" \
  --no-agent --deliver telegram --workdir /opt/data

# Layer 2: Enforcement (30min) — only notifies on action/alert
cronjob create --name "OpenRouter Spending Guard" \
  --schedule "*/30 * * * *" \
  --script "openrouter_spending_guard.py" \
  --no-agent --deliver telegram --workdir /opt/data
```

## Natural Language Output Pattern (Standardized)

All cron scripts delivering to Telegram follow this pattern:

```python
# Silent exit when nothing to report
if not alerts and not action_taken:
    return 0  # no output = no message

# Structured markdown report
lines = [
    f"🛡️ **OpenRouter Spending Guard** — {ts}",
    f"💰 Saldo: **${remaining:.2f}** / ${total:.2f}",
    f"📅 Gasto hoje: **${daily_usage:.2f}**",
    f"🤖 Modelo atual: `{current_model}`",
]
if action_taken:
    lines.append(f"\n{action_taken}")  # 🔒 BLOCKED or 🔓 UNBLOCKED
elif daily_usage >= LIMITE_DIARIO_USD * 0.8:
    lines.append(f"\n⚡ **CUIDADO**: Gasto a {daily_usage/LIMITE_DIARIO_USD*100:.0f}% do limite")
lines.append("\n---\n*Verificação automática a cada 30 min via Hermes cron*")
print("\n".join(lines))
```

**Key elements:**
- Markdown for Telegram rendering
- Emojis for quick visual scanning
- Human-readable numbers with thousands separators
- Clear status line (OK / ⚡ CUIDADO / 🔒 BLOQUEADO / 🔓 DESBLOQUEADO)
- Footer with automation context
- Silent exit when all OK

## Files

| Path | Purpose |
|------|---------|
| `/opt/data/scripts/check_openrouter_credits.py` | Layer 1 watchdog |
| `/opt/data/scripts/openrouter_spending_guard.py` | Layer 2 enforcement |
| `~/.hermes/scripts/` (copies) | Cron job runtime location |
| `/opt/data/openrouter_spending_state.json` | Persisted guard state |

## Lessons Learned

1. **Thresholds must fit budget** — $5/day makes no sense with $10/month budget
2. **Hysteresis prevents flapping** — don't revert on first sign of improvement
3. **Free model fallback chain** — always have ordered list of `:free:` models
4. **Persisted state** — survives Hermes/cron restarts
5. **Silent exit** — don't spam Telegram when all OK
6. **Model switch via config** — `hermes config set model.default` is the enforcement lever

## References

- OpenRouter API: `/api/v1/credits`, `/api/v1/auth/key`
- Hermes `config set model.default` for dynamic model switching
- Skill `cybersecurity-wellbeing` — cron job templates + natural language output pattern
- Session 2026-07-23: `references/openrouter-cost-governance-2026-07-23.md` (session-specific detail)
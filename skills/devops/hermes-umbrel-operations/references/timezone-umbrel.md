# Timezone Configuration on Umbrel Hermes

## Problem
The Hermes app container runs in **UTC by default**. The host Umbrel OS may be set to your local timezone, but the container does not inherit it automatically.

**Symptoms:**
- Gateway logs show timestamps 3h ahead (Brasília/BRT) / 4h ahead (BRT with DST)
- Cron jobs run at wrong local times
- Dashboard timestamps don't match your clock

## Fix — Set TZ in Umbrel App Environment Variables

This is the **only persistent fix** that survives app updates.

### Via Umbrel Dashboard (Recommended)

1. Open Umbrel dashboard → **Apps → Hermes Agent → Settings** (gear icon)
2. Add Environment Variable:
   - **Key**: `TZ`
   - **Value**: `America/Sao_Paulo` (or your IANA timezone: `America/Fortaleza`, `America/Manaus`, `America/Belem`, etc.)
3. Click **Save**
4. Restart Hermes Agent app:
   - Desktop: Right-click Hermes Agent app icon → **Restart**
   - Mobile: Long-press Hermes Agent app icon → **Restart**

### Why App Config (not `.env` or `bashrc`)

| Method | Survives App Update? | Affects Gateway? | Affects Cron? | Affects Dashboard? |
|--------|---------------------|------------------|---------------|-------------------|
| Umbrel App Env Var (`TZ`) | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| `/opt/data/.env` | ✅ Yes | ✅ Yes* | ✅ Yes* | ❌ No |
| `~/.bashrc` / `export TZ` | ✅ Yes | ❌ No (shell only) | ❌ No | ❌ No |
| Cron job `schedule: 'TZ=...'` | ✅ Yes | ❌ No | ✅ Yes (that job only) | ❌ No |

\* The gateway reads `.env` on boot, but **Umbrel App Env Vars are the canonical source** — they're injected into the container at Docker level before any process starts.

## IANA Timezone Identifiers for Brazil

| Region | IANA TZ |
|--------|---------|
| Brasília, Rio, São Paulo, most states | `America/Sao_Paulo` |
| Fernando de Noronha | `America/Noronha` |
| Ceará, Piauí, Maranhão, etc. (no DST) | `America/Fortaleza` |
| Amazonas (west), Acre | `America/Manaus` |
| Pará (east), Amapá | `America/Belem` |
| Mato Grosso, Mato Grosso do Sul | `America/Cuiaba` |

## Verification

After restart, check gateway logs:

```bash
tail -20 /opt/data/logs/gateway.log | head -5
```

Should show timestamps matching your local clock (e.g., `16:31:xx` for Brasília, not `19:31:xx` UTC).

## Cron Jobs Without App Restart (Workaround)

If you cannot restart the app immediately, set TZ per cron job:

```yaml
# In cron job definition
schedule: 'TZ=America/Sao_Paulo 0 9 * * *'  # daily 9 AM Brasília
# or in the job's script/workdir environment
```

This only affects that specific job — gateway logs and dashboard remain in UTC until app restart.
# Telegram Connectivity on Umbrel (Docker Desktop / WSL)

## Problem Pattern Observed (2026-07-21)

The Hermes gateway on Umbrel (running in Docker Desktop on Windows via WSL 2) experiences **recurring Telegram connection failures** even with `TELEGRAM_API_URL=https://149.154.166.110` configured in `.env`.

### Log Signature

```
[Telegram] Primary api.telegram.org connection failed (); trying fallback IPs 149.154.166.110
[Telegram] Primary api.telegram.org path unreachable; using sticky fallback IP 149.154.166.110
[Telegram] Sticky fallback IP 149.154.166.110 failed; resetting to primary DNS path
[Telegram] Fallback IP 149.154.166.110 failed: All connection attempts failed
[Telegram] Telegram network error, scheduling reconnect: httpx.ConnectError: All connection attempts failed
[Telegram] Telegram polling reconnect failed: Timed out
```

This cycle repeats every few minutes, causing message delivery delays or apparent "freeze" from the user's perspective.

### Root Cause

**Network path instability**: Docker Desktop (Windows) → WSL 2 VM → Host networking → Internet.

The container's network stack traverses multiple layers:
1. Container namespace
2. Docker Desktop's internal bridge/VPN (Hyper-V / WSL 2 integration)
3. Windows host network stack
4. Physical network / VPN / firewall

Any hiccup in layers 2-4 breaks the long-lived polling connection to Telegram. The fallback IP helps but doesn't eliminate the problem because the underlying TCP path is the same.

### Mitigations (Applied / Recommended)

| Mitigation | Status | Notes |
|------------|--------|-------|
| `TELEGRAM_API_URL=https://149.154.166.110` in `.env` | ✅ Applied | Forces direct IP, skips DNS. Still traverses same network path. |
| Docker Desktop → Settings → Resources → Network → **Enable VPN compatibility mode** | 🔄 Try next | Changes how Docker routes container traffic on Windows. Can stabilize VPN/firewall interference. |
| `wsl --shutdown` + restart Docker Desktop | 🔄 Try next | Clears WSL 2 VM network state. Often fixes transient routing issues. |
| Increase Telegram adapter timeouts | ❌ Not configurable | Adapter uses hardcoded 30s connect / 60s read timeouts. |
| Run a sidecar TCP proxy (socat/ngrok) on host | 🔧 Advanced | Forward localhost:8443 → 149.154.166.110:443, point Hermes to `http://host.docker.internal:8443`. Bypasses Docker network stack for Telegram. |
| Move Hermes to native Ubuntu (no Docker Desktop) | 🎯 Long-term | Eliminates the Docker Desktop network layer entirely. See `references/umbrel-to-ubuntu-migration.md`. |

### Diagnostic Commands

```bash
# Test connectivity from inside the Hermes container
curl -v --max-time 10 "https://149.154.166.110/bot$TELEGRAM_BOT_TOKEN/getMe"

# Check if fallback IP is reachable at all
curl -v --max-time 10 https://149.154.166.110

# Check DNS resolution (should NOT be used if TELEGRAM_API_URL is set)
curl -v --max-time 10 https://api.telegram.org

# View recent gateway Telegram errors
grep -E "Telegram.*(failed|error|reconnect|fallback)" /opt/data/logs/gateway.log | tail -20
```

### Expected Behavior After Fix

Gateway logs should show stable connection:
```
[Telegram] Connected to Telegram (polling mode)
✓ telegram connected
# No further "connection failed / fallback / reconnect" lines for hours
```

### Session Recovery

When the gateway restarts (SIGTERM from s6-supervise), it persists `gateway_state=running` so `container_boot` auto-starts it on next boot. Active Telegram sessions are **resumed automatically** (session marked `resumable`), but any in-flight message during the disconnect may be lost or delayed.

---

## Related References

- `references/cron-job-patterns.md` — Cron job environment loading (Telegram vars)
- `references/umbrel-to-ubuntu-migration.md` — Full migration to eliminate Docker Desktop network layer
- `references/raft-external-agent.md` — Raft also uses long-lived connections; same network issues apply
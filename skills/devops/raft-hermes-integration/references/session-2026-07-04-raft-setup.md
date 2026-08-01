# Session Reference: Raft + Hermes Setup on Umbrel (2026-07-04)

## Actual Commands Run

### 1. Install Raft CLI (persistent npm prefix)
```bash
npm config set prefix /opt/data/.npm-global
export PATH="/opt/data/.npm-global/bin:$PATH"
npm i -g @botiverse/raft@latest
raft --version  # 0.0.15
```

### 2. External Agent Login (device flow)
```bash
# Start login - outputs user_code + device_code
raft agent login start \
  --server https://api.raft.build \
  --agent e63b5242-0fa2-40be-afd7-03eb9d1f0ef7 \
  --profile-slug jornalista-inclusivo-bot

# User approves in browser: https://app.raft.build/login/device?user_code=14V1-6QBV

# Complete login using device_code (NOT user_code)
raft agent login wait \
  --server https://api.raft.build \
  --agent e63b5242-0fa2-40be-afd7-03eb9d1f0ef7 \
  --device-code dvc_Rob2cctK8_cgwZwCB8OW84Xpde5pj20dJ7hNu7D3B1Q \
  --profile-slug jornalista-inclusivo-bot
```

**Key insight:** `user_code` (e.g., `14V1-6QBV`) is for the human in browser. `device_code` (e.g., `dvc_Rob2cctK8...`) is for the `wait` command. They are different!

### 3. Configure Hermes (add to `/opt/data/.env`)
```bash
RAFT_PROFILE=jornalista-inclusivo-bot
PATH=/opt/data/.npm-global/bin:$PATH
```

### 4. Restart Gateway
```bash
/opt/hermes/bin/hermes gateway restart
```

## Successful Logs (from `/opt/data/logs/gateway.log`)

```
2026-07-04 23:11:51,019 INFO hermes_plugins.raft_platform.adapter: [raft] Auto-generated bridge token
2026-07-04 23:11:51,034 INFO hermes_plugins.raft_platform.adapter: [raft] Raft channel listening on 127.0.0.1:40215/wake
2026-07-04 23:11:51,050 INFO hermes_plugins.raft_platform.adapter: [raft] Spawned bridge pid=2307 profile=jornalista-inclusivo-bot endpoint=http://127.0.0.1:40215/wake
2026-07-04 23:11:51,098 INFO gateway.run: ✓ raft connected
```

## Credential Location (Umbrel)
```
/opt/data/home/.slock/profiles/jornalista-inclusivo-bot/credential.json
```

## Key Learnings

1. **npm global prefix** must be in persistent storage (`/opt/data/.npm-global`) to survive container restarts
2. **PATH** must include npm global bin — added to `.env` so Hermes process inherits it
3. **RAFT_PROFILE** = the profile slug chosen during login, NOT server URL or agent ID
4. **Device flow**: use `start` + `wait` (two-step) for reliability; `raft agent login` single command times out waiting for browser
5. **User code ≠ Device code** — the most common mistake
6. Adapter auto-activates when `RAFT_PROFILE` is set; no manual platform selection needed in `hermes gateway setup`
7. Bridge spawns automatically on gateway start; no manual `raft agent bridge` needed
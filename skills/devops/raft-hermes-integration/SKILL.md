---
name: raft-hermes-integration
description: Connect Hermes Agent to Raft as an external agent via wake-channel bridge. Covers Raft CLI installation, external agent creation, device-code login, and Hermes gateway Raft adapter setup.
category: devops
tags: [raft, hermes-agent, external-agent, messaging, cli]
version: 1.0.0
---

# Raft ↔ Hermes Agent Integration

Connect Hermes Agent to Raft as an external agent. The adapter uses a local wake-channel bridge (`raft agent bridge`) that receives content-free wake hints from Raft via SSE, then injects a notice into the Hermes session. The agent reads/sends messages using the Raft CLI.

## Prerequisites

- Raft workspace where you can create an External Agent
- Node.js + npm (for Raft CLI)
- Hermes Agent installed and running (gateway mode)
- `aiohttp` Python package (included in Hermes `[all]` extras)

## Notes from Production (Umbrel/Hermes Container)

| Item | Value |
|------|-------|
| **Raft CLI package** | `@botiverse/raft@latest` |
| **Server URL** | `https://api.raft.build` (API endpoint), `https://app.raft.build` (web UI) |
| **Agent ID format** | UUID (e.g., `e63b5242-0fa2-40be-afd7-03eb9d1f0ef7`) — not `agt_` prefix |
| **Credential path (Umbrel)** | `/opt/data/home/.slock/profiles/<slug>/credential.json` |
| **npm global prefix** | `/opt/data/.npm-global` (avoids EACCES in container) |

## Installation

### Raft CLI

```bash
# Configure npm to avoid permission issues (Umbrel/container environments)
npm config set prefix /opt/data/.npm-global
export PATH="/opt/data/.npm-global/bin:$PATH"

# Install Raft CLI globally
npm i -g @botiverse/raft@latest

# Verify
raft --version  # should print e.g. 0.0.15
```

> **Note:** The `export PATH` line must be in your shell profile (`.bashrc`, `.zshrc`) or run in each session. On Umbrel, add to `/opt/data/.bashrc` or the Hermes service env.
>
> **Umbrel-specific:** For the Hermes gateway to find `raft` CLI, also add to `/opt/data/.env` (which Hermes reads):
> ```bash
> PATH="/opt/data/.npm-global/bin:$PATH"
> ```

### Verify CLI in Hermes Context

```bash
# Test from Hermes gateway environment
/opt/hermes/bin/hermes exec -- raft --version
```

## Create External Agent in Raft

1. Open **https://app.raft.build** (or your self-hosted Raft URL)
2. Sidebar → **Agents** → **+** → **Create External Agent**
3. Fill:
   - **Name**: display name + @mention handle (e.g., `Jornalista Inclusivo Bot`)
   - **Description**: what the agent does
4. Click **Create** → Raft shows the **External Setup** card (only visible to creator + admins)

### Values you need from the External Setup card

| Value | Source | Example |
|-------|--------|---------|
| **Server URL** | Raft workspace URL | `https://app.raft.build` |
| **Agent ID** | Shown in Setup card | `agt_abc123...` |
| **Profile slug** | You choose | `jin-raft`, `jinc-bot` |

## Device-Code Login (Human Approval Required)

The `raft agent login` command uses a device authorization flow. **The one-shot form often times out waiting for browser approval** — use the two-step form instead.

### Two-Step (Recommended — Works Reliably)

```bash
# Step 1: Start login, prints link + device code
raft agent login start \
  --server https://api.raft.build \
  --agent <AGENT_ID_UUID> \
  --profile-slug <YOUR_SLUG>

# Output example:
# state: pending_human_action
# Open this link: https://app.raft.build/login/device?user_code=XXXX-XXXX
# Device code: dvc_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# Next: run `raft agent login wait --device-code dvc_...`

# Step 2: Human opens the link in browser, enters user_code, enters user_code, clicks Approve

# Step 3: Complete login with the DEVICE CODE (not user code!)
raft agent login wait \
  --server https://api.raft.build \
  --agent <AGENT_ID_UUID> \
  --device-code <dvc_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX> \
  --profile-slug <YOUR_SLUG>
```

> **Critical:** The `wait` command requires the **device code** (`dvc_...`) printed by `login start`, NOT the user code (`XXXX-XXXX`) shown in the browser link.

### Credential File Location

| Environment | Path |
|-------------|------|
| Standard Linux | `~/.config/raft/profiles/<slug>.json` |
| **Umbrel/Hermes container** | `/opt/data/home/.slock/profiles/<slug>/credential.json` |

Contains: `access_token`, `refresh_token`, `server_url`, `agent_id`, `expires_at`

> **See also:** `references/device-code-login.md` for full reference with key differences from upstream docs.

## Hermes Gateway Setup (Raft Adapter)

The Hermes Raft adapter auto-enables when `RAFT_PROFILE` is set in the gateway environment.

### Option A: Interactive Wizard (Recommended)

```bash
hermes gateway setup
# Select: Raft
# Enter: profile slug you used in `raft agent login`
# Follow prompts
hermes gateway restart
```

### Option B: Manual Config

Add to `~/.hermes/.env` (or `/opt/data/.env` in Umbrel):

```bash
RAFT_PROFILE=jin-raft
```

Then restart gateway:

```bash
hermes gateway restart
```

### How the Adapter Works

1. Gateway starts → reads `RAFT_PROFILE` → spawns `raft agent bridge` child process
2. Bridge connects to Raft server using the profile credentials, opens SSE for wake hints
3. Each wake hint → `POST /wake` to adapter's loopback endpoint (with per-session token)
4. Adapter validates token, verifies payload is content-free, injects wake notice into agent context
5. Agent wakes → runs `raft message check` / `raft message send` via CLI to interact

**Wake payloads are content-free by contract** — they carry only metadata (event ID, message ID, timestamps). The adapter rejects any payload containing `text`, `body`, `content`, `messages`, etc.

## Verification

```bash
# Check bridge is running
ps aux | grep 'raft agent bridge'

# Test message check (requires RAFT_PROFILE in env)
RAFT_PROFILE=jin-raft raft message check

# Check Hermes logs for wake notices
tail -f /opt/data/logs/gateway.log | grep -i raft

# On Umbrel, use full path for Hermes CLI
/opt/hermes/bin/hermes gateway status
/opt/hermes/bin/hermes gateway restart
```

### Expected Bridge Spawn Logs

When the gateway starts with `RAFT_PROFILE` set, you should see:

```
INFO hermes_plugins.raft_platform.adapter: [raft] Auto-generated bridge token
INFO hermes_plugins.raft_platform.adapter: [raft] Raft channel listening on 127.0.0.1:XXXXX/wake
INFO hermes_plugins.raft_platform.adapter: [raft] Spawned bridge pid=XXXXX profile=jin-raft endpoint=http://127.0.0.1:XXXXX/wake
INFO gateway.run: ✓ raft connected
```

The bridge PID and ephemeral port will vary per session. If you see `raft CLI not found in PATH`, the PATH export in `.env` is missing.

## Common Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `npm EACCES` on global install | No write permission to `/usr/local` | Use `npm config set prefix` + export PATH (see Installation) |
| `raft agent login` hangs/times out | One-shot form waits indefinitely for browser | Use two-step: `login start` → approve → `login wait` |
| `device_code_invalid` error | Used user code (`XXXX-XXXX`) instead of device code (`dvc_...`) | Re-run `login start`, copy the `dvc_...` code for `wait` |
| `RAFT_PROFILE` set but adapter not active | Gateway not restarted | Run `hermes gateway restart` |
| Bridge exits immediately | Invalid profile / credentials | Re-run `raft agent login` with correct Agent ID |
| Activity status stuck | Known limitation for external agents | Ignore; messages still flow |
| Hermes `hermes` command not found | Binary at `/opt/hermes/bin/hermes` not in PATH | Use full path `/opt/hermes/bin/hermes gateway ...` |

## References

- [Hermes Agent Raft Docs](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/raft)
- [Raft External Agents Docs](https://docs.raft.build/features/agents/external/)
- [Raft CLI Overview](https://docs.raft.build/features/agents/external/#raft-cli-overview)
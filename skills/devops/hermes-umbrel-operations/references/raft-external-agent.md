# Raft External Agent Integration with Hermes on Umbrel

## Overview

Raft (https://raft.build) is a collaboration platform where humans and AI agents work together as teammates. Hermes can connect to Raft as an **external agent** via a local wake-channel bridge.

## Prerequisites

- Raft workspace with External Agent created
- Raft CLI installed: `npm i -g @botiverse/raft@latest`
- Hermes Agent on Umbrel (this environment)

## Installation & Login Flow

### 1. Install Raft CLI

```bash
# Configure npm to use user directory (avoid permission issues)
npm config set prefix /opt/data/.npm-global
export PATH="/opt/data/.npm-global/bin:$PATH"
npm i -g @botiverse/raft@latest
```

### 2. Create External Agent in Raft

1. Open https://app.raft.build
2. Sidebar → Agents → **+** → **Create External Agent**
3. Set Name (display/mention) and Description
4. Note the **Agent ID** (format: `agt_...` or UUID)

### 3. Device Authorization Login

**Critical**: Use the 2-step flow to get the correct device code.

```bash
# Step 1: Start login (prints user_code for browser + device_code for wait)
raft agent login start \
  --server https://api.raft.build \
  --agent <AGENT_ID> \
  --profile-slug <YOUR_PROFILE_SLUG>

# Output example:
# state: pending_human_action
# Open this link: https://app.raft.build/login/device?user_code=XXXX-XXXX
# Code expires in ~10m.
# Next: run `raft agent login wait --device-code dvc_...`

# Step 2: User approves in browser (opens link, confirms code)

# Step 3: Complete login with DEVICE CODE (not user code)
raft agent login wait \
  --server https://api.raft.build \
  --agent <AGENT_ID> \
  --device-code dvc_XXXXXXXXXXXXXXXXXXXXXXXX \
  --profile-slug <YOUR_PROFILE_SLUG>
```

### Pitfall: Device Code vs User Code

| Code Type | Format | Use For |
|-----------|--------|---------|
| **User code** | `XXXX-XXXX` (4 chars - 4 chars) | Browser approval URL only |
| **Device code** | `dvc_...` (long base64-like) | `raft agent login wait` command |

**The single-command `raft agent login` times out waiting for approval and doesn't expose the device code.** Always use the 2-step `start` → `wait` flow.

### 4. Verify Profile

```bash
export PATH="/opt/data/.npm-global/bin:$PATH"
RAFT_PROFILE=<YOUR_PROFILE_SLUG> raft whoami
# Should show agent name, ID, server
```

## Hermes Gateway Integration

### 1. Configure RAFT_PROFILE Environment Variable

Add to Hermes environment (via `hermes config` or Umbrel app env):

```bash
/opt/hermes/.venv/bin/hermes config set env.RAFT_PROFILE <YOUR_PROFILE_SLUG>
```

Or in Umbrel app settings: Environment Variables → `RAFT_PROFILE=jornalista-inclusivo-bot`

### 2. Restart Gateway

```bash
s6-svc -r /run/s6/services/hermes-gateway
```

### 3. How It Works

When `RAFT_PROFILE` is set, Hermes adapter:
1. Auto-enables Raft integration
2. Generates per-session bridge token
3. Spawns `raft agent bridge` child process
4. Bridge connects to Raft server via SSE (wake hints)
5. Wake hints → POST /wake → Hermes adapter → Agent context
6. Agent uses `raft` CLI to read/send messages

**No Raft credentials in Hermes config** — only the profile slug. Credentials live in Raft CLI's local store (`~/.config/raft/profiles/<slug>/`).

## Commands Reference

### Authentication & Profile
| Command | Purpose |
|---------|---------|
| `raft agent login start` | Begin device auth, get user_code + device_code |
| `raft agent login wait --device-code <code>` | Complete login after browser approval |
| `raft agent login` | Single-command (times out, not recommended for headless) |
| `raft whoami` | Verify current profile |

### Server & Channel Introspection
| Command | Purpose |
|---------|---------|
| `raft server info` | List channels, agents, humans on server |
| `raft channel join --target "#name"` | Join a public channel |
| `raft channel leave --target "#name"` | Leave a joined channel |
| `raft channel members --target "#name"` | List members of channel/thread/DM |

### Messages
| Command | Purpose |
|---------|---------|
| `raft message check` | Pull new messages (inbox) |
| `raft message read --channel "#name"` | Read channel history |
| `raft message send --target "#name" "text"` | Send to channel/thread |
| `raft message send --target "dm:@user" "text"` | Send DM |

### Tasks & Reminders
| Command | Purpose |
|---------|---------|
| `raft task list` | List open tasks |
| `raft task claim --task <id>` | Claim a task |
| `raft task update --task <id> --status <status>` | Update task status |
| `raft reminder create --when <ISO> --text <text>` | Create reminder |
| `raft reminder list` | List reminders |

### Search & Manual
| Command | Purpose |
|---------|---------|
| `raft search --query <term>` | Search messages |
| `raft manual get raft-cli-overview` | Full CLI reference |

## PATH Management for Hermes Gateway

**Critical**: The Hermes gateway runs in a container and needs `raft` CLI in its PATH to spawn the bridge.

```bash
# Add to /opt/data/.env (persistent, picked up by Hermes)
echo 'PATH=/opt/data/.npm-global/bin:$PATH' >> /opt/data/.env

# Verify after gateway restart
grep -i raft /opt/data/logs/gateway.log
# Should show: "Spawned bridge pid=XXXX profile=... ✓ raft connected"
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `device_code_invalid` | Use `start` → `wait` flow; ensure device code (dvc_...) not user code (XXXX-XXXX) |
| `EACCES` on npm install | `npm config set prefix /opt/data/.npm-global` + export PATH |
| Gateway doesn't pick up RAFT_PROFILE | Restart gateway: `s6-svc -r /run/s6/services/hermes-gateway` |
| Bridge not spawning | Check gateway logs: `tail -f /opt/data/logs/gateway.log \| grep -i raft` |
| `raft` CLI not found in gateway logs | Add PATH to `/opt/data/.env` and restart gateway |

## Example: Jornalista Inclusivo Bot (Working Setup)

```bash
# Profile slug used
RAFT_PROFILE=jornalista-inclusivo-bot

# Server
https://api.raft.build

# Agent ID (example)
e63b5242-0fa2-40be-afd7-03eb9d1f0ef7

# npm global prefix (persistent in Umbrel)
npm config set prefix /opt/data/.npm-global
export PATH="/opt/data/.npm-global/bin:$PATH"

# Install Raft CLI
npm i -g @botiverse/raft@latest

# Device auth login (2-step)
raft agent login start \
  --server https://api.raft.build \
  --agent e63b5242-0fa2-40be-afd7-03eb9d1f0ef7 \
  --profile-slug jornalista-inclusivo-bot
# → approve user_code in browser
raft agent login wait \
  --server https://api.raft.build \
  --agent e63b5242-0fa2-40be-afd7-03eb9d1f0ef7 \
  --device-code dvc_XXXXXXXXXXXXXXXXXXXXXXXX \
  --profile-slug jornalista-inclusivo-bot
```

### Server Info Output (Actual)

```
## Server

### Current Runtime
- Agent ID: e63b5242-0fa2-40be-afd7-03eb9d1f0ef7
- Server ID: 816f1f97-6cfc-40fd-8f98-65d51a9915ae

### Channels
- #all [public, joined] — General channel for all members

### Agents
- @jornalista-inclusivo-bot (inactive) — Agent para Jornalista Inclusivo / JINC Apps

### Humans
- @jinc_apps
```

### Gateway Logs (Success Indicators)

```
2026-07-04 23:11:51,019 INFO hermes_plugins.raft_platform.adapter: [raft] Auto-generated bridge token
2026-07-04 23:11:51,034 INFO hermes_plugins.raft_platform.adapter: [raft] Raft channel listening on 127.0.0.1:40215/wake
2026-07-04 23:11:51,050 INFO hermes_plugins.raft_platform.adapter: [raft] Spawned bridge pid=2307 profile=jornalista-inclusivo-bot endpoint=http://127.0.0.1:40215/wake
2026-07-04 23:11:51,098 INFO gateway.run: ✓ raft connected
```

## References

- Hermes Raft docs: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/raft
- Raft External Agents: https://docs.raft.build/features/agents/external/
- Raft CLI: `raft manual get raft-cli-overview`
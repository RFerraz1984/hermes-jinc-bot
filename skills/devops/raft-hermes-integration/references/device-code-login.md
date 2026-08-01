# Raft Device-Code Login Flow Reference

## Key Differences from Upstream Docs

| Upstream Docs | Actual Behavior (This Session) |
|---------------|-------------------------------|
| Server URL: `https://app.raft.build` | **API: `https://api.raft.build`** |
| Agent ID format: `agt_...` | **UUID: `e63b5242-0fa2-40be-afd7-03eb9d1f0ef7`** |
| One-shot `login` works | **One-shot times out** — use two-step |
| Credential: `~/.config/raft/profiles/<slug>.json` | **Umbrel: `/opt/data/home/.slock/profiles/<slug>/credential.json`** |
| CLI package: `@slock-ai/raft` | **`@botiverse/raft@latest`** |

---

## Two-Step Login (Reliable)

### Step 1: Start Login (prints both codes)

```bash
raft agent login start \
  --server https://api.raft.build \
  --agent <AGENT_ID_UUID> \
  --profile-slug <YOUR_SLUG>
```

**Output:**

```
state: pending_human_action
Open this link: https://app.raft.build/login/device?user_code=XXXX-XXXX
Device code: dvc_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
Next: raft agent login wait --device-code dvc_...
```

### Step 2: Human Approval

1. Open the **link** in browser
2. Enter the **user code** (`XXXX-XXXX`)
3. Click **Approve**

### Step 3: Complete with DEVICE CODE

```bash
raft agent login wait \
  --server https://api.raft.build \
  --agent <AGENT_ID_UUID> \
  --device-code <dvc_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX> \
  --profile-slug <YOUR_SLUG>
```

> ⚠️ **CRITICAL:** Use the `dvc_...` device code from Step 1 output, NOT the `XXXX-XXXX` user code from the browser link.

---

## Credential File Locations

| Environment | Path |
|-------------|------|
| Standard Linux | `~/.config/raft/profiles/<slug>.json` |
| **Umbrel/Hermes container** | `/opt/data/home/.slock/profiles/<slug>/credential.json` |

Contains: `access_token`, `refresh_token`, `server_url`, `agent_id`, `expires_at`

---

## Verify Login

```bash
# Check messages (requires RAFT_PROFILE in env)
RAFT_PROFILE=jin-raft raft message check

# Check identity
RAFT_PROFILE=jin-raft raft whoami
```

---

## Umbrel/Hermes npm Setup

```bash
# Avoid EACCES in container
npm config set prefix /opt/data/.npm-global
export PATH="/opt/data/.npm-global/bin:$PATH"

# Install
npm i -g @botiverse/raft@latest

# Verify
raft --version  # 0.0.15+
```
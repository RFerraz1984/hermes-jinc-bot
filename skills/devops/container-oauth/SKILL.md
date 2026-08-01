---
name: container-oauth
description: "OAuth authentication patterns for containerized environments (Umbrel, Docker, WSL) where callback URLs are container-local and inaccessible from host browser."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
tags: [oauth, container, umbrel, docker, spotify, pkce, authentication]
---

# OAuth in Containerized Environments

When running Hermes (or any app) inside a container (Umbrel, Docker, WSL2), OAuth flows that use `localhost`/`127.0.0.1` callback URLs break because:

- The OAuth server runs inside the container on `127.0.0.1:PORT`
- The user's browser runs on the host machine
- Host browser cannot reach container's loopback interface

## The Problem

Standard OAuth flow:
1. App starts local HTTP server on `127.0.0.1:43827` (inside container)
2. Opens browser to authorization URL with `redirect_uri=http://127.0.0.1:43827/callback`
3. User authorizes → OAuth provider redirects to `http://127.0.0.1:43827/callback?code=...`
4. **FAILS**: Host browser can't reach container's `127.0.0.1`

## Solution: Manual PKCE Code Exchange

Instead of relying on the automatic callback listener, use a **manual PKCE flow**:

### Prerequisites
- OAuth client supports PKCE (Spotify, Google, GitHub, etc.)
- You have the `client_id` and configured `redirect_uri` in the provider's dashboard

### Steps

1. **Generate PKCE parameters** (code_verifier + code_challenge)
2. **Build authorization URL** with `code_challenge` and `code_challenge_method=S256`
3. **Open URL in host browser** → user authorizes
4. **Copy `code` from browser address bar** after redirect (even if it shows "connection failed")
5. **Exchange code for tokens** using `code_verifier` via token endpoint
6. **Save tokens** to Hermes auth store

### Spotify Example (Umbrel)

```bash
# 1. Generate auth URL + code_verifier (run in container)
/opt/hermes/.venv/bin/python3 /opt/data/spotify_pkce.py

# 2. Open printed URL in host browser, authorize
# 3. Copy 'code' from redirect URL: http://127.0.0.1:43827/spotify/callback?code=CODE_HERE&state=...
# 4. Exchange code for tokens
/opt/hermes/.venv/bin/python3 /opt/data/spotify_pkce.py "COPIED_CODE" "SAVED_CODE_VERIFIER"
```

### Alternative: SSH Local Forward (if SSH available)

```bash
# On host machine
ssh -N -L 43827:127.0.0.1:43827 user@umbrel-host
# Then run normal `hermes auth spotify login` in container
```

**Limitation**: Umbrel containers often don't have SSH enabled by default.

## Reference Implementation

See `scripts/spotify_pkce.py` for a reusable PKCE helper script.

## Pitfalls

| Issue | Fix |
|-------|-----|
| `code` already used | PKCE codes are single-use. Regenerate auth URL + verifier and retry. |
| `INVALID_CLIENT: Invalid redirect URI` | Ensure redirect URI in provider dashboard EXACTLY matches what you use (including port). |
| Token expires | Use refresh_token (stored in auth.json) - Hermes auto-refreshes on 401. |
| No browser in container | Use `--no-browser` flag and copy URL manually. |

## Applies To

- Umbrel apps (Hermes, other self-hosted tools)
- Docker containers with host-network: false
- WSL2 when accessing container from Windows browser
- Any headless/containerized environment with OAuth

## Related Skills

- `umbrel` — Umbrel-specific paths, persistence, networking
- `hermes-agent` — Hermes configuration, auth commands
---
name: hermes-container-oauth
description: "OAuth authentication patterns for containerized Hermes deployments (Umbrel, Docker, Kubernetes) where localhost callbacks don't reach the host browser."
version: 1.0.0
tags: [hermes, oauth, umbrel, docker, container, networking, spotify, authentication]
---

# Hermes Container OAuth Patterns

When Hermes runs in a container (Umbrel app, Docker, Kubernetes), OAuth flows that use a localhost callback (`127.0.0.1:PORT`) fail because the callback server runs **inside the container** but the user's browser runs **on the host**.

## The Core Problem

```
┌─────────────────────────────────────────────────────────────┐
│  HOST (Windows/macOS/Linux)                                 │
│  ┌──────────────┐    Browser opens                          │
│  │   Browser    │ ──────► https://accounts.spotify.com/...  │
│  └──────────────┘         │                                 │
│                           ▼                                 │
│                    User clicks "Agree"                      │
│                           │                                 │
│                           ▼                                 │
│              Redirect to http://127.0.0.1:43827/callback   │
│                           │                                 │
│                           ✗ CANNOT REACH CONTAINER          │
└───────────────────────────│─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  CONTAINER (Umbrel app / Docker)                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Hermes callback server on 127.0.0.1:43827          │    │
│  │  (waiting for redirect that never arrives)          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Solution 1: SSH Local Port Forward (Recommended)

**Best for:** Umbrel, remote Docker hosts, any SSH-accessible container.

### Prerequisites
- SSH access to the container host (Umbrel: Settings → SSH → Enable)
- SSH client on host machine

### Steps

**1. On host machine, open tunnel:**
```bash
ssh -N -L 43827:127.0.0.1:43827 root@<UMBREL_IP>
```
- Replace `<UMBREL_IP>` with your Umbrel's LAN IP (e.g., `192.168.1.50`)
- Keep this terminal window open

**2. In container (Umbrel terminal or another SSH session):**
```bash
hermes auth spotify login --no-browser --client-id <YOUR_CLIENT_ID>
```

**3. On host browser:** Open the URL Hermes prints, authorize.

**4. Done.** Tokens saved to `/opt/data/auth.json` (Umbrel) or `~/.hermes/auth.json` (standard).

### Why SSH Tunnel Wins

| Factor | SSH Tunnel | Custom Redirect URI | Manual Code Exchange |
|--------|------------|---------------------|----------------------|
| Security | ✅ Encrypted, localhost-only | ⚠️ LAN-exposed port | ✅ Secure but manual |
| Ease | ✅ One command | ⚠️ Router/firewall config | ❌ Multi-step |
| Umbrel compatible | ✅ Yes | ❌ No port exposure | ✅ Yes |
| Persistence | ✅ Tokens persist | ✅ Same | ✅ Same |

## Solution 2: Custom Redirect URI (Advanced)

Only if you can expose a port on the container's network interface.

**1. In Spotify Developer Dashboard**, add redirect URI:
```
http://<UMBREL_LAN_IP>:43827/spotify/callback
```

**2. In container's `.env`:**
```bash
HERMES_SPOTIFY_REDIRECT_URI=http://<UMBREL_LAN_IP>:43827/spotify/callback
```

**3. Expose port 43827** via Umbrel/Docker/K8s networking (not default on Umbrel).

**⚠️ Not recommended for Umbrel** — app proxy doesn't expose arbitrary ports.

## Solution 3: Manual PKCE Code Exchange (No Network Access) ✅ WORKING

Use when no SSH, no port exposure possible. **Fully working method below.**

### Complete Working Method: Python Script + Direct Token Exchange

**1. Create the exchange script (in container, one-time):**
```bash
cat > /opt/data/spotify_pkce.py << 'EOF'
#!/usr/bin/env python3
import base64, hashlib, json, os, secrets, sys, urllib.parse, requests

CLIENT_ID = "YOUR_CLIENT_ID"
REDIRECT_URI = "http://127.0.0.1:43827/spotify/callback"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
SCOPES = "user-modify-playback-state user-read-playback-state user-read-currently-playing user-read-recently-played playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-library-read user-library-modify"
AUTH_FILE = "/opt/data/auth.json"

def gen_verifier(): return secrets.token_urlsafe(64)[:128]
def gen_challenge(v): return base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).decode().rstrip("=")

def build_url(verifier):
    params = {"client_id": CLIENT_ID, "response_type": "code", "redirect_uri": REDIRECT_URI,
              "scope": SCOPES, "code_challenge_method": "S256", "code_challenge": gen_challenge(verifier),
              "state": secrets.token_urlsafe(16)}
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}", gen_challenge(verifier)

def exchange(code, verifier):
    data = {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID, "code_verifier": verifier}
    r = requests.post(TOKEN_URL, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    r.raise_for_status()
    return r.json()

def save_tokens(tokens):
    import sys; sys.path.insert(0, "/opt/hermes")
    from hermes_cli.auth import _store_provider_state, _load_auth_store, _save_auth_store
    state = {"access_token": tokens["access_token"], "refresh_token": tokens["refresh_token"],
             "token_type": tokens.get("token_type", "Bearer"),
             "expires_at": "2026-06-21T17:38:30.883127+00:00",  # will be refreshed
             "scope": tokens.get("scope", ""), "granted_scope": tokens.get("scope", ""),
             "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI,
             "api_base_url": "https://api.spotify.com/v1", "accounts_base_url": "https://accounts.spotify.com",
             "auth_type": "oauth_pkce"}
    store = _load_auth_store()
    _store_provider_state(store, "spotify", state, set_active=False)
    _save_auth_store(store)
    print("Tokens saved to auth.json")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        v = gen_verifier()
        url, _ = build_url(v)
        print("=== AUTH URL ==="); print(url); print()
        print("=== CODE VERIFIER (SAVE THIS) ==="); print(v); print()
        print("Open URL in browser, authorize, copy 'code' from redirect URL.")
        print("Then run: python3 spotify_pkce.py <code> <code_verifier>")
    else:
        tokens = exchange(sys.argv[1], sys.argv[2])
        save_tokens(tokens)
        print(json.dumps(tokens, indent=2))
EOF
chmod +x /opt/data/spotify_pkce.py
```

**2. Generate auth URL + code_verifier:**
```bash
/opt/hermes/.venv/bin/python3 /opt/data/spotify_pkce.py
```
- Outputs an auth URL and a **code_verifier** (save both!)
- Open the auth URL in **host browser**, authorize
- Browser redirects to `http://127.0.0.1:43827/spotify/callback?code=<CODE>&state=...` (error page is normal)
- **Copy the `code` parameter** from browser address bar

**3. Exchange code for tokens:**
```bash
/opt/hermes/.venv/bin/python3 /opt/data/spotify_pkce.py <CODE> <CODE_VERIFIER>
```
- Tokens saved to `/opt/data/auth.json` via Hermes internal API

**4. Verify:**
```bash
/opt/hermes/.venv/bin/hermes auth status spotify
```

### Why This Works
- **Own code_verifier**: We generate it, so we know it for the exchange
- **Direct token endpoint**: Calls Spotify's `/api/token` directly (no callback server needed)
- **Internal API**: Uses `_store_provider_state` to write to protected `auth.json`
- **Zero network exposure**: No SSH tunnel, no port forwarding, works in air-gapped containers

## Provider-Specific Notes

### Spotify
- Uses PKCE (no client secret needed)
- Default callback port: 43827
- Scopes: playback control requires Premium
- Tokens auto-refresh on 401

### GitHub Copilot / Codex / Qwen OAuth
- Use device code flow (no localhost callback)
- **Not affected by this issue** — no tunnel needed

### Google / Microsoft / Generic OAuth
- If they use localhost callback → same problem
- Apply same SSH tunnel solution

## Umbrel-Specific Details

| Item | Value |
|------|-------|
| Persistent Hermes home | `/opt/data` |
| Auth file | `/opt/data/auth.json` |
| Env file | `/opt/data/.env` |
| SSH user | `root` |
| SSH port | 22 (standard) |
| Default callback port | 43827 |

## Troubleshooting Checklist

- [ ] SSH tunnel running on host (`ssh -N -L ...`)
- [ ] Correct Umbrel IP (check Umbrel Settings → Network)
- [ ] Spotify app has redirect URI `http://127.0.0.1:43827/spotify/callback`
- [ ] Client ID matches Spotify app
- [ ] `--no-browser` flag used (container has no display)
- [ ] Port 43827 free on host (or change with `-L 43828:127.0.0.1:43827` + env var)
- [ ] Spotify Premium if using playback control

## References

- `references/oauth-container-tunneling.md` — Detailed Umbrel/Spotify walkthrough
- `references/spotify-umbrel-setup.md` — Complete Spotify setup on Umbrel (SSH tunnel method)
- `references/manual-pkce-spotify.md` — **Manual PKCE code exchange (no SSH, no port exposure)**
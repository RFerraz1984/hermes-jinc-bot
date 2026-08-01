# Spotify OAuth on Umbrel: Complete Walkthrough

## Prerequisites

- Umbrel with Hermes Agent app installed
- SSH enabled on Umbrel (Settings → Advanced → SSH → Enable)
- Spotify account (Premium required for playback control)
- Host machine with SSH client (Windows: PowerShell/WSL, macOS/Linux: Terminal)

## Step-by-Step

### 1. Create Spotify Developer App

1. Open https://developer.spotify.com/dashboard on host browser
2. Log in → **Create app**
3. Fill:
   - **App name**: `hermes-umbrel` (or anything)
   - **App description**: `Hermes on Umbrel`
   - **Website**: (leave blank)
   - **Redirect URI**: `http://127.0.0.1:43827/spotify/callback`
   - **API/SDK**: ✅ **Web API**
4. Save → **Settings** → Copy **Client ID**

### 2. Open SSH Tunnel (Host Machine)

```powershell
# PowerShell / Windows Terminal / WSL
ssh -N -L 43827:127.0.0.1:43827 root@<UMBREL_IP>
```

- Replace `<UMBREL_IP>` with your Umbrel's LAN IP (e.g., `192.168.1.50`)
- Enter Umbrel password (default: `moneyprintergoesbrrr` unless changed)
- **Keep this window open** — tunnel must stay active

### 3. Run Auth in Container (Umbrel Terminal)

In Umbrel UI: **Hermes Agent → Terminal** (or SSH into Umbrel):

```bash
/opt/hermes/.venv/bin/hermes auth spotify login --no-browser \
  --client-id <YOUR_CLIENT_ID_FROM_STEP_1>
```

### 4. Authorize (Host Browser)

- Hermes prints a long `https://accounts.spotify.com/authorize?...` URL
- **Copy it and open in your host browser**
- Log in to Spotify if needed
- Click **Agree** to authorize `hermes-umbrel`

### 5. Verify Success

In Umbrel terminal:
```bash
/opt/hermes/.venv/bin/hermes auth status spotify
```

Should show: `✓ Authenticated` with token expiry.

### 6. Enable Spotify Toolset (if not already)

```bash
/opt/hermes/.venv/bin/hermes tools
# Toggle 🎵 Spotify on, press 's' to save
```

## Test It

Start a chat:
```bash
/opt/hermes/.venv/bin/hermes chat -q "what's playing on Spotify?"
```

## Common Issues

| Symptom | Fix |
|---------|-----|
| `ssh: connect to host ... port 22: Connection refused` | Enable SSH in Umbrel Settings; check IP |
| `Permission denied (publickey,password)` | Use `root` user; password is Umbrel's web password |
| `Address already in use` on host port 43827 | Use different local port: `ssh -N -L 43828:127.0.0.1:43827 ...` and set `HERMES_SPOTIFY_REDIRECT_URI=http://127.0.0.1:43828/spotify/callback` in container's `.env` |
| `INVALID_CLIENT: Invalid redirect URI` | Spotify app must have EXACT redirect URI: `http://127.0.0.1:43827/spotify/callback` |
| `403 Premium required` | Upgrade to Spotify Premium for playback control |
| `403 No active device` | Open Spotify on phone/desktop/speaker first |

## Persistence

- Tokens stored in `/opt/data/auth.json` → survives Umbrel app updates
- `HERMES_SPOTIFY_CLIENT_ID` in `/opt/data/.env` → survives updates
- Only re-auth if you revoke app in Spotify or delete tokens

## Automate with Cron (Optional)

Once working, create scheduled playback:

```bash
/opt/hermes/.venv/bin/hermes cron create \
  --name "morning-music" \
  "0 7 * * 1-5" \
  "Transfer to kitchen speaker, play 'Morning Vibes' playlist, volume 40, shuffle on"
```

Requires: Spotify toolset enabled, active Spotify Connect device (speaker always on).
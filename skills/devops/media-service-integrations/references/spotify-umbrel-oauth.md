# Spotify OAuth on Umbrel/Containerized Hermes

## The Problem

Hermes runs in a container. The Spotify OAuth flow:
1. Hermes starts a local HTTP server on port 43827 inside the container
2. Opens browser to Spotify authorization URL with redirect_uri=`http://127.0.0.1:43827/spotify/callback`
3. User authorizes, Spotify redirects to the callback URL
4. Container's localhost is not reachable from host browser → "Cannot connect to server"

## Solutions (in order of preference)

### 1. SSH Local Forward (if SSH access to container host)
```bash
# On host machine (Windows/WSL/Linux)
ssh -N -L 43827:127.0.0.1:43827 user@umbrel-host
# Then run hermes auth spotify login normally
```

### 2. Manual PKCE Flow (used in this session) - RECOMMENDED for Umbrel

**Step 1: Generate authorization URL with known code_verifier**
```bash
# In container
/opt/hermes/.venv/bin/python3 /opt/data/spotify_pkce.py
# Outputs: auth URL + code_verifier (SAVE THE VERIFIER)
```

**Step 2: Authorize in host browser**
Open the printed URL, click "Agree", copy the `code` from the failed redirect URL.

**Step 3: Exchange code for tokens**
```bash
/opt/hermes/.venv/bin/python3 /opt/data/spotify_pkce.py AUTH_CODE CODE_VERIFIER
```

**Step 4: Inject tokens into auth.json**
```python
import json
with open('/opt/data/auth.json') as f:
    auth = json.load(f)

auth['providers']['spotify'] = {
    'access_token': 'BQC...',
    'refresh_token': 'AQC...',
    'token_type': 'Bearer',
    'expires_at': '2026-06-21T22:08:04.986231+00:00',
    'scope': 'playlist-read-private playlist-read-collaborative user-modify-playback-state user-library-read user-library-modify playlist-modify-private playlist-modify-public user-read-playback-state user-read-currently-playing user-read-recently-played',
    'granted_scope': 'same as scope',
    'client_id': '29211866598740e891275a6076add397',
    'redirect_uri': 'http://127.0.0.1:43827/spotify/callback',
    'api_base_url': 'https://api.spotify.com/v1',
    'accounts_base_url': 'https://accounts.spotify.com',
    'auth_type': 'oauth_pkce',
    'obtained_at': '2026-06-21T21:08:04.986231+00:00',
    'expires_in': 3600,
}

with open('/opt/data/auth.json', 'w') as f:
    json.dump(auth, f, indent=2)
```

**Step 5: Verify**
```bash
/opt/hermes/.venv/bin/hermes auth status spotify
```

## Token Refresh

Automatic on 401. Manual:
```bash
curl -X POST https://accounts.spotify.com/api/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d grant_type=refresh_token \
  -d refresh_token=YOUR_REFRESH_TOKEN \
  -d client_id=YOUR_CLIENT_ID
```

## Scopes Required

| Feature | Scopes |
|---------|--------|
| Read playback state | `user-read-playback-state` |
| Read currently playing | `user-read-currently-playing` |
| Read recently played | `user-read-recently-played` |
| **Playback control (Premium)** | `user-modify-playback-state` |
| Queue control (Premium) | `user-modify-playback-state` |
| Device transfer (Premium) | `user-modify-playback-state` |
| Playlist read | `playlist-read-private`, `playlist-read-collaborative` |
| Playlist write | `playlist-modify-private`, `playlist-modify-public` |
| Library read | `user-library-read` |
| Library write | `user-library-modify` |

Default Hermes requests all of the above.

## Device IDs for Echo/Alexa

Format: `{uuid}_amzn_1` (e.g., `61c007ac-8fa7-4050-b61e-f83a4bead200_amzn_1`)
Type: `Speaker`
Must be active (shows as "Ativo" in `spotify_devices list`)

## Known API Issues

### 403 Forbidden on Playlist Track Add
- **Endpoint**: `POST /playlists/{id}/tracks`
- **Scopes present**: `playlist-modify-private`, `playlist-modify-public`
- **Error**: `{"error": {"status": 403, "message": "Forbidden"}}`
- **Workaround**: Create playlist via API, add tracks manually in Spotify app
- **Status**: Confirmed bug/limitation with Hermes Spotify app registration

### Recommendations Endpoint 404
- **Endpoint**: `GET /recommendations`
- **Error**: 404 Not Found
- **Note**: May require different parameters or be deprecated
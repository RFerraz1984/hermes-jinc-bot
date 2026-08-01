# Spotify API Limits and Workarounds

## Known Limitations with Hermes Spotify Integration

### 1. Playlist Track Add - 403 Forbidden

**Endpoint**: `POST /v1/playlists/{playlist_id}/tracks`
**Scopes**: `playlist-modify-private`, `playlist-modify-public` (both present)
**Error**: `{"error": {"status": 403, "message": "Forbidden"}}`

**Observed behavior**:
- Playlist creation works: `POST /v1/me/playlists` → 201
- Playlist read works: `GET /v1/me/playlists` → 200
- Track add fails on ALL playlists (new and existing)
- Both `spotify:track:` URIs and `spotify:track:` IDs fail

**Possible causes**:
- App registration missing "Web API" permission (check Spotify Dashboard → App → Settings)
- App in "Development" mode with user not in allowed users
- Scope mismatch between requested and granted
- Hermes Spotify app registration bug

**Workarounds**:
1. **Manual add**: Create playlist via API, open in Spotify app, use "Recommended" section
2. **Spotify app**: Add tracks manually via desktop/mobile app
3. **Alternative**: Use Spotify's "Enhance" feature on the playlist

### 2. Recommendations Endpoint - 404

**Endpoint**: `GET /v1/recommendations`
**Parameters tried**:
- `seed_tracks=track1,track2`
- `limit=20`
- Various audio features (instrumentalness, energy, valence)

**Error**: 404 Not Found

**Note**: This endpoint may require specific parameters or be deprecated in current API version.

**Workaround**: Use search with genre/artist queries:
```bash
# Search for similar artists
spotify_search "Joe Satriani"
spotify_search "Eric Johnson"
spotify_search "John Petrucci"
spotify_search "instrumental rock guitar"
```

### 3. Device Transfer Requires Active Device

**Error**: `403 Forbidden - Player command failed: No active device found`

**Cause**: No Spotify client running on any device.

**Fix**: Open Spotify app on phone/desktop/speaker, play something briefly to register device.

### 4. Premium Required for Playback Mutations

| Action | Free | Premium |
|--------|------|---------|
| `spotify_playback play/pause/next/prev/seek/volume/shuffle/repeat` | ✗ | ✓ |
| `spotify_queue add` | ✗ | ✓ |
| `spotify_devices transfer` | ✗ | ✓ |
| `spotify_playback get_state/currently_playing/recently_played` | ✓ | ✓ |
| `spotify_devices list` | ✓ | ✓ |
| `spotify_queue get` | ✓ | ✓ |
| `spotify_search` | ✓ | ✓ |
| `spotify_playlists` (all) | ✓ | ✓ |
| `spotify_albums` (all) | ✓ | ✓ |
| `spotify_library` (all) | ✓ | ✓ |

### 5. Rate Limits

- **429 Too Many Requests**: Spotify quota resets ~every 30 seconds
- **Burst**: ~100 requests/30s typical
- **Fix**: Wait 30-60s, retry

### 6. Token Expiry

- Access token: 1 hour (3600s)
- Refresh token: Long-lived (revoked only on app removal)
- Auto-refresh: Hermes handles on 401
- Manual refresh: POST to `https://accounts.spotify.com/api/token`

## Testing Checklist

Before reporting issues:
- [ ] Spotify Premium active?
- [ ] Device active and visible in `spotify_devices list`?
- [ ] Scopes granted match requirements?
- [ ] App in Spotify Dashboard shows "Web API" enabled?
- [ ] Redirect URI matches exactly: `http://127.0.0.1:43827/spotify/callback`
- [ ] Token not expired (check `hermes auth status spotify`)?

## Useful Debug Commands

```bash
# Check auth status
hermes auth status spotify

# List devices
hermes chat -q "spotify_devices list"

# Test search
hermes chat -q "spotify_search Joe Satriani"

# Test playback (requires Premium + active device)
hermes chat -q "toque Always with Me Always with You Joe Satriani na Minha Echo"

# Check playlist creation
hermes chat -q "crie playlist teste"
```
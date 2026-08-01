# Windows Path Mapping for Umbrel + Hermes Sidecar

## Host (Windows) → Umbrel VM → Containers

### Primary Umbrel Mount
```
C:\Users\RFERRAZ\Homelab-Umbrel\umbrel  →  /data  (inside Umbrel VM)
```

### Hermes App Data (confirmed by user)
```
C:\Users\RFERRAZ\Homelab-Umbrel\umbrel\app-data\hermes-agent\data
    →  /data/hermes-agent  (inside Umbrel VM)
    →  /opt/data  (inside Hermes container)
```

### Docker Volumes (inside Umbrel VM)
```
hermes-agent_data  (Docker named volume, external: true)
    → /var/lib/docker/volumes/hermes-agent_data/_data
    → mounted as /opt/data in Hermes container
    → mounted as /opt/data in hermes-tools sidecar container
```

### Complete Path Chain

| Layer | Path |
|---|---|
| Windows Host | `C:\Users\RFERRAZ\Homelab-Umbrel\umbrel\app-data\hermes-agent\data` |
| Umbrel VM (bind mount) | `/data/hermes-agent` |
| Docker Volume | `hermes-agent_data` → `/var/lib/docker/volumes/hermes-agent_data/_data` |
| Hermes Container | `/opt/data` |
| Sidecar Container | `/opt/data` |

### Verification Commands

**On Windows (PowerShell):**
```powershell
# Check directory exists
Test-Path "C:\Users\RFERRAZ\Homelab-Umbrel\umbrel\app-data\hermes-agent\data"

# List contents
ls "C:\Users\RFERRAZ\Homelab-Umbrel\umbrel\app-data\hermes-agent\data"
```

**Inside Umbrel VM (SSH):**
```bash
# Check volume exists
docker volume ls | grep hermes-agent

# Inspect volume mountpoint
docker volume inspect hermes-agent_data

# Test sidecar access
docker exec hermes-tools ls -la /opt/data/
```

### Common Mistakes

| Mistake | Reality |
|---|---|
| Mount `C:\...\umbrel` → `/data` in sidecar | No — sidecar must use `hermes-agent_data` volume |
| Run sidecar on Docker Desktop host | No — must run inside Umbrel VM |
| Use `/umbrel-os/home/umbrel/umbrel/app-data/hermes-agent` | That's the VM path, not the Windows path |
| Underscore in path: `hermes_agent` | Wrong — it's `hermes-agent` (hyphen) |
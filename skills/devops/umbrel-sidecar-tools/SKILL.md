---
name: umbrel-sidecar-tools
version: "1.0.0"
description: Sidecar container pattern for Hermes Agent on Umbrel OS — provides pandoc, weasyprint, libreoffice via shared volume with Hermes app data.
category: devops
tags: [umbrel, sidecar, docker, pandoc, weasyprint, libreoffice, container]
author: Hermes Agent
license: MIT
---

# Umbrel Sidecar Container for Hermes Tools

Provides system dependencies (pandoc, weasyprint, libreoffice) to Hermes Agent running in Umbrel OS via a sidecar container sharing the Hermes app data volume.

## Architecture

```
Umbrel VM (dockurr/umbrel)
├── Hermes App Container          → /opt/data = volume hermes-agent_data
└── hermes-tools Sidecar Container → /opt/data = volume hermes-agent_data (same volume)
```

Both containers run **inside the Umbrel VM**, not on the Docker Desktop host.

## Volume Mapping

| Host (Windows) | Umbrel VM | Hermes Container | Sidecar Container |
|---|---|---|---|
| `C:\Users\RFERRAZ\Homelab-Umbrel\umbrel\app-data\hermes-agent\data` | `/data/hermes-agent` | `/opt/data` | `/opt/data` |

Docker volume name: `hermes-agent_data` (created by Umbrel for the Hermes app).

## Installation

### 1. Create App Directory (on Windows host)

```powershell
$APPDATA = "C:\Users\RFERRAZ\Homelab-Umbrel\umbrel\app-data"
New-Item -ItemType Directory -Force -Path "$APPDATA\hermes-tools"
```

### 2. Create `umbrel-app.yml` in `C:\Users\RFERRAZ\Homelab-Umbrel\umbrel\app-data\hermes-tools\`

```yaml
id: hermes-tools
version: "1.0.0"
name: "Hermes Tools Sidecar"
description: "Pandoc, WeasyPrint, LibreOffice for Hermes Agent"
category: utilities
icon: "📄"
port: null
dependencies: []
```

### 3. Create `docker-compose.yml` in same directory

```yaml
version: "3.8"
services:
  hermes-tools:
    image: hermes-tools:latest
    container_name: hermes-tools
    restart: unless-stopped
    entrypoint: ["sleep", "infinity"]
    volumes:
      - hermes-agent_data:/opt/data

volumes:
  hermes-agent_data:
    external: true
    name: hermes-agent_data
```

### 4. Create `Dockerfile` in same directory

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc texlive-xetex \
    libreoffice-headless \
    python3 python3-pip python3-cairo python3-pango python3-gi \
    && pip3 install --break-system-packages weasyprint \
    && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["sleep", "infinity"]
```

### 5. Build and Install

```powershell
# SSH into Umbrel VM
ssh umbrel@<umbrel-ip>

# Build image
cd /home/umbrel/umbrel/app-data/hermes-tools
docker build -t hermes-tools:latest .

# Install app via Umbrel CLI
umbrel app install hermes-tools
# Or restart app manager:
sudo systemctl restart umbrel-app-manager
```

## Usage from Hermes

```bash
# Pandoc: markdown → PDF
docker exec hermes-tools pandoc /opt/data/input.md -o /opt/data/output.pdf --pdf-engine=xelatex

# WeasyPrint: HTML → PDF
docker exec hermes-tools python3 -c "
import weasyprint
weasyprint.HTML('/opt/data/input.html').write_pdf('/opt/data/output.pdf')
"

# LibreOffice: DOCX → PDF
docker exec hermes-tools libreoffice --headless --convert-to pdf --outdir /opt/data /opt/data/document.docx
```

## Key Points

- **Sidecar runs in Umbrel VM** — not on Docker Desktop host
- **Same volume `hermes-agent_data`** — both containers see identical `/opt/data`
- **Access via `docker exec` from Hermes** — both containers in same Docker network inside VM
- **Image size ~2GB** — includes texlive, libreoffice, python+cairo+pango+gobject
- **Update**: rebuild image, `docker stop hermes-tools && docker rm hermes-tools`, restart via Umbrel

## Troubleshooting

| Issue | Solution |
|---|---|
| `docker exec` fails: container not found | Check `docker ps -a` inside Umbrel VM; ensure app started via Umbrel |
| Permission denied on `/opt/data` | Check volume ownership; both containers run as root by default |
| weasyprint fails: missing fonts | Install `fonts-dejavu-core` in Dockerfile |
| LibreOffice fails: display | Use `--headless` flag; ensure `libreoffice-headless` package |
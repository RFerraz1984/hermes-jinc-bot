# Container Install Workarounds — Hermes/Umbrel (Sem Root/APT)

Problema: Container Hermes no Umbrel roda como usuário `hermes` (UID 1000), sem `sudo`, sem `apt`/`apk` root. Instalação de ferramentas CLI precisa de workarounds.

## 1. Go Binaries (bsky, etc.) — Download Direto via Python

```bash
# bsky CLI (GitHub Releases: bsky-linux-<version>.zip)
mkdir -p /opt/data/home/.local/bin
cd /opt/data/home/.local/bin
python3 -c "
import zipfile, urllib.request, os
url = 'https://github.com/mattn/bsky/releases/download/v0.0.81/bsky-linux-0.0.81.zip'
dest = '/opt/data/home/.local/bin/bsky.zip'
urllib.request.urlretrieve(url, dest)
with zipfile.ZipFile(dest, 'r') as z:
    z.extractall('/opt/data/home/.local/bin/')
os.remove(dest)
os.chmod('/opt/data/home/.local/bin/bsky', 0o755)
"
# Verificar
/opt/data/home/.local/bin/bsky --help
```

**Vantagens:** Sem Go, sem unzip, sem root. Usa só Python stdlib.

## 2. Python Packages (sounddevice, numpy, edge-tts, etc.) — uv + Venv do Usuário

```bash
# Criar venv persistente em /opt/data (sobrevive a updates Umbrel)
uv venv /opt/data/voice-venv --python 3.13

# Instalar packages (voz/TTS/STT)
/opt/data/voice-venv/bin/python3 -m pip install sounddevice numpy edge-tts faster-whisper

# Ou via uv (mais rápido):
uv pip install --python /opt/data/voice-venv/bin/python3 sounddevice numpy edge-tts faster-whisper

# --- RSS/Telegram automation (rss-md.py, multiplatform-post.sh) ---
/opt/data/voice-venv/bin/python3 -m pip install feedparser python-telegram-bot pyyaml
```

**Usar no CLI:**
```bash
PYTHONPATH=/opt/data/voice-venv/lib/python3.13/site-packages \
/opt/hermes/.venv/bin/hermes chat --tui
```

**Usar em script standalone:**
```bash
/opt/data/voice-venv/bin/python3 -c "
import edge_tts, asyncio
asyncio.run(edge_tts.Communicate('Texto', 'pt-BR-FranciscaNeural').save('audio.mp3'))
"
```

## 3. xurl (X/Twitter CLI) — Download Direto

```bash
# xurl releases: https://github.com/xdevplatform/xurl/releases
mkdir -p /opt/data/home/.local/bin
cd /opt/data/home/.local/bin
# Baixar .tar.gz ou .zip do release mais recente
curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh | bash
# O install.sh instala em ~/.local/bin (resolve para /opt/data/home/.local/bin)
```

## 4. HOME Path Crítico — Container Hermes tem DUAS HOMEs

| Contexto | HOME | Onde configs salvam |
|----------|------|---------------------|
| Hermes process (dashboard/gateway) | `/opt/data` | `/opt/data/.config/...` |
| **Subprocessos (terminal, cron jobs, scripts)** | `/opt/data/home` | `/opt/data/home/.config/...` |

**Regra de Ouro:** Sempre use `HOME=/opt/data/home` ao rodar CLIs que salvam config (bsky, xurl, etc.) dentro de cron jobs ou scripts.

```bash
# ✅ Correto
HOME=/opt/data/home /opt/data/home/.local/bin/bsky login handle password
HOME=/opt/data/home /opt/data/home/.local/bin/xurl auth status

# ❌ Errado (config salva em /opt/data/.config/, cron job não vê)
bsky login handle password
xurl auth status
```

## 5. Cloudflare/WAF 403 no RSS — User-Agent Obrigatório

```bash
# curl com User-Agent real
curl -sL -H 'User-Agent: Mozilla/5.0 (compatible; JINC-RSS-Bot/1.0)' \
  https://jornalistainclusivo.com.br/feed/
```

```python
# Python
import requests
headers = {'User-Agent': 'Mozilla/5.0 (compatible; JINC-RSS-Bot/1.0)'}
requests.get(url, headers=headers)
```

## 6. WordPress Redirect 301 `/feed` → `/feed/` — Seguir Redirects

```bash
# curl -L segue redirects
curl -sL https://jornalistainclusivo.com.br/feed/
```

```python
# Python requests segue auto
requests.get(url)  # follow_redirects=True por default
```

## 7. XML Parsing sem xmllint — Python stdlib

```python
import xml.etree.ElementTree as ET

root = ET.fromstring(xml_content)
for item in root.findall('.//item'):
    title = item.findtext('title')
    link = item.findtext('link')
    guid = item.findtext('guid')
    # ...
```

## Resumo: Checklist de Deploy no Container

- [ ] `bsky` CLI em `/opt/data/home/.local/bin/bsky`
- [ ] `xurl` CLI em `/opt/data/home/.local/bin/xurl`
- [ ] Venv `/opt/data/voice-venv` com `sounddevice numpy edge-tts faster-whisper`
- [ ] `HOME=/opt/data/home` em todos os cron jobs/scripts que usam CLIs
- [ ] `curl -L` + User-Agent para RSS
- [ ] Python `xml.etree` para parsing RSS (sem xmllint)
- [ ] State file usa GUID|title|link (não índice numérico)
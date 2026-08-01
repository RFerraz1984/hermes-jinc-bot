# Ollama on Windows Host with Hermes on Umbrel — Connectivity Fix

## Problem
Hermes running in Umbrel container cannot reach Ollama on Windows host when configured with IP `10.21.0.1:11434`.

## Root Cause
The IP `10.21.0.1` is not accessible from the Umbrel container. The correct Docker Desktop pattern is to use `host.docker.internal` which resolves to the Windows host.

## Solution

### 1. Fix Provider URL in config.yaml
```bash
/opt/hermes/.venv/bin/hermes config set providers.ollama.base_url http://host.docker.internal:11434/v1
```

### 2. On Windows Host — Configure Ollama to Listen Externally
By default Ollama only binds to `127.0.0.1`. To accept connections from the Umbrel container:

**Option A: Environment Variable (persistent)**
```powershell
# In PowerShell as Admin
setx OLLAMA_HOST "0.0.0.0:11434"
# Restart Ollama service or re-open terminal
```

**Option B: Per-session**
```powershell
$env:OLLAMA_HOST="0.0.0.0:11434"
ollama serve
```

### 3. Verify Connectivity

From Umbrel container:
```bash
# List models
curl http://host.docker.internal:11434/api/tags

# Test chat
curl -X POST http://host.docker.internal:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.1:8b", "messages": [{"role": "user", "content": "OK"}]}'
```

From Windows host:
```powershell
ollama list
# Should show pulled models
```

### 4. Model Requirements for Hermes
Hermes requires minimum 64K context window. Models that work:
| Model | Context | Size | RAM needed |
|-------|---------|------|------------|
| `llama3.1:8b` | 128K | 4.7GB | ~8GB |
| `qwen2.5:14b` | 128K | 9GB | ~16GB |
| `mistral-nemo:12b` | 128K | 7GB | ~16GB |
| `llama3.1:70b` | 128K | 40GB | ~48GB |

**Models that DON'T work (8K context):**
- `gemma:2b`, `gemma:7b`, `gemma2:*`
- `phi3:*`

### 5. Pull Model on Windows Host
```powershell
ollama pull llama3.1:8b
```

### 6. Test from Hermes
```bash
/opt/hermes/.venv/bin/hermes chat -q "Responda: OK" --provider ollama --model llama3.1:8b
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Connection refused` | Ollama not running or not binding to 0.0.0.0 |
| `host.docker.internal` not resolving | Docker Desktop not running; restart Docker |
| `Model ... has context window of 8,192` | Use 128K context model (llama3.1:8b, qwen2.5:14b) |
| `404: model not found` | Pull model on Windows host: `ollama pull llama3.1:8b` |
| Firewall blocks | Allow port 11434 in Windows Firewall (Private network) |

## Network Architecture
```
Windows Host (Ollama on 0.0.0.0:11434)
    ↑ host.docker.internal
Umbrel VM (Docker)
    ↑ container network
Hermes App Container → http://host.docker.internal:11434/v1
```
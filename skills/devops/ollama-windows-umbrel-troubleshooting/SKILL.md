---
name: ollama-windows-umbrel-troubleshooting
description: "Troubleshooting Ollama on Windows host with Hermes Agent on Umbrel OS — networking, firewall, model selection, and Hermes config."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, windows]
metadata:
  hermes:
    tags: [ollama, umbrel, windows, networking, firewall, troubleshooting, local-llm]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [hermes-umbrel-operations, ollama-host-windows-umbrel]
---

# Ollama on Windows Host with Hermes on Umbrel — Troubleshooting Guide

## Scenario
- Hermes Agent runs as Umbrel app (containerized)
- Ollama runs on Windows host machine (not in container)
- Need Hermes to use Ollama models via OpenAI-compatible API

---

## 1. Networking: Correct Host Address

**❌ Wrong** — IP address that may change or be unreachable:
```yaml
providers:
  ollama:
    base_url: http://10.21.0.1:11434/v1  # Don't use container-internal IPs
```

**✅ Correct** — Docker Desktop special DNS name:
```yaml
providers:
  ollama:
    base_url: http://host.docker.internal:11434/v1
    api_key: ollama  # Dummy key, Ollama doesn't validate
```

`host.docker.internal` resolves to the Windows host from inside the container automatically.

---

## 2. Windows Firewall: Allow Port 11434

Ollama must listen on **all interfaces** (`0.0.0.0:11434`), not just localhost.

### Verify Ollama is listening externally:
```powershell
netstat -an | findstr 11434
# Should show: TCP 0.0.0.0:11434 LISTENING
```

### If only shows `127.0.0.1:11434`, configure Ollama to bind to all interfaces:
```powershell
# Temporary (current session)
$env:OLLAMA_HOST="0.0.0.0:11434"
ollama serve

# Permanent (requires restart)
setx OLLAMA_HOST "0.0.0.0:11434"
# Then restart Ollama service or app
```

### Create firewall rule (PowerShell as Administrator):
```powershell
New-NetFirewallRule -DisplayName "Ollama API" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow -Profile Private
```

### Verify rule created:
```powershell
Get-NetFirewallRule -DisplayName "Ollama API"
```

---

## 3. Model Selection: Hermes Requires 64K+ Context

Hermes Agent **requires minimum 64,000 token context window**. Most small models (Gemma, Phi, Llama3 8B base) only have 8K.

### ❌ Models that FAIL (8K context):
| Model | Size | Context |
|-------|------|---------|
| `gemma:2b` / `gemma:7b` | 1.7–4.7 GB | 8K |
| `gemma2:2b` / `gemma2:9b` / `gemma2:27b` | 1.6–16 GB | 8K |
| `phi3:latest` | 2.2 GB | 8K (or 128K for phi3:14b) |
| `llama3:latest` (8B) | 4.7 GB | 8K |

### ✅ Models that WORK (128K+ context):
| Model | Size | Context | Notes |
|-------|------|---------|-------|
| `llama3.1:8b` | 4.7 GB | 128K | **Recommended** — fast, balanced |
| `qwen2.5:14b` | 9 GB | 128K | Strong reasoning |
| `mistral-nemo:12b` | 7 GB | 128K | Good multilingual |
| `llama3.1:70b` | 40 GB | 128K | Needs ~48 GB RAM |
| `command-r:35b` | 20 GB | 128K | RAG-optimized |
| `deepseek-r1:8b` | 5.2 GB | 131K | **Reasoning model** — slower |

### Install recommended model:
```powershell
ollama pull llama3.1:8b
```

---

## 4. Hermes Configuration

### In `/opt/data/config.yaml` (inside Hermes container):
```yaml
providers:
  ollama:
    base_url: http://host.docker.internal:11434/v1
    api_key: ollama

# Optional: override context length if model reports less than actual
model:
  context_length: 131072  # For deepseek-r1:8b, llama3.1:8b, etc.
```

### Test from Hermes container:
```bash
# List models
curl http://host.docker.internal:11434/api/tags

# Test chat completion
curl -X POST http://host.docker.internal:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.1:8b", "messages": [{"role": "user", "content": "OK"}]}'
```

### Test via Hermes CLI:
```bash
/opt/hermes/bin/hermes chat -q "Responda apenas: OK" --provider ollama --model llama3.1:8b
```

---

## 5. Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Connection refused` / timeout | Firewall blocking | Add Windows Firewall rule for 11434 (Private profile) |
| `HTTP 400: context window too small` | Model has <64K context | Use `llama3.1:8b`, `qwen2.5:14b`, or `deepseek-r1:8b` |
| `HTTP 404: model not found` | Model not pulled | Run `ollama pull <model>` on Windows |
| `host.docker.internal` not resolving | Docker Desktop not running / Linux host | On Linux: `--add-host=host.docker.internal:host-gateway` |
| `HTTP 400: property 'think' unsupported` | Reasoning model + reasoning_effort set | Set `reasoning_effort: none` in config or use non-reasoning model |
| Model loads but hangs forever | Reasoning model (deepseek-r1) thinking | Use non-reasoning model for speed, or increase timeout |

---

## 6. Quick Diagnostic Checklist

```bash
# 1. From Hermes container - check connectivity
curl -s http://host.docker.internal:11434/api/tags | jq '.models[].name'

# 2. Check model context lengths
curl -s http://host.docker.internal:11434/api/show -d '{"name": "llama3.1:8b"}' | jq '.details.context_length'

# 3. From Windows host - verify Ollama listening
netstat -an | findstr 11434

# 4. From Windows host - test local API
curl http://localhost:11434/api/tags

# 5. Check Windows Firewall
Get-NetFirewallRule -DisplayName "Ollama API" | Select-Object Enabled, Profile, Direction, Action
```

---

## 7. Performance Tips

- **Use non-reasoning models** (`llama3.1:8b`) for fast responses
- **Reasoning models** (`deepseek-r1:8b`) add 30-120s latency per response
- **Allocate RAM**: Model size + ~2-4 GB overhead (8B model → ~8 GB RAM)
- **Disable reasoning_effort** for local models in Hermes config:
  ```yaml
  model:
    reasoning_effort: none
  ```

---

## Related Skills
- `hermes-umbrel-operations` — General Hermes on Umbrel patterns
- `ollama-host-windows-umbrel` — Reference doc in hermes-agent skill references
---
name: hermes-umbrel-operations
description: "Hermes Agent configuration, CLI usage, and gateway operations on Umbrel — paths, safe config patterns, s6 service control, and common workflows."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [hermes, umbrel, config, gateway, s6, tavily, mcp]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [umbrel, hermes-agent]
---

## Script Wrapper Arguments Not Expanded (Session 2026-07-25)

**Problem:** Cron job with `script: "cron_wrapper.sh \"Backup Seletivo Hermes\" /opt/data/scripts/backup-hermes-selective.sh"` failed with `Script not found: /opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh` — the scheduler treats the entire string as a single script filename instead of parsing arguments.

**Root Cause:** The cron job's `script` field is designed for a single executable file (or shell command when `no_agent=true`). It does not perform shell word-splitting on the value. When the whole `cron_wrapper.sh "args..."` string is stored as the script name, the executor looks for a file literally named `cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh`, which doesn't exist.

**Fix:** Create a dedicated wrapper script that embeds the arguments, then point the cron job to that single script:

```bash
# 1. Create wrapper with baked-in arguments
cat > /opt/data/scripts/backup-hermes-daily.sh << 'EOF'
#!/usr/bin/env bash
/opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh
EOF
chmod +x /opt/data/scripts/backup-hermes-daily.sh

# 2. Update cron job to use the wrapper
/opt/hermes/.venv/bin/hermes cron edit <job_id> --script backup-hermes-daily.sh
```

**Lesson:** Never put shell commands with arguments directly in the `script` field of a cron job. Always use a single executable file as the entry point.

---

## Ollama on Windows Host — Correct URL Configuration (Session 2026-07-25)

**Problem:** Hermes on Umbrel (containerized) could not connect to Ollama running on the Windows host. The configured URL `http://10.21.0.1:11434/v1` timed out / connection refused.

**Root Cause:** The IP `10.21.0.1` is an internal Docker network address that does not reliably route to the Windows host from inside the Umbrel container. The correct Docker Desktop alias is `host.docker.internal`.

**Fix:** Update the Ollama provider base URL:

```bash
/opt/hermes/.venv/bin/hermes config set providers.ollama.base_url http://host.docker.internal:11434/v1
```

**Verification:** From inside the container:
```bash
curl http://host.docker.internal:11434/api/tags
# Should return list of models pulled on Windows host
```

**Models that work with Hermes (64K+ context required):**
| Model | Size | Context | RAM |
|-------|------|---------|-----|
| `llama3.1:8b` | 4.7GB | 128K | ~8GB |
| `qwen2.5:14b` | 9GB | 128K | ~16GB |
| `mistral-nemo:12b` | 7GB | 128K | ~16GB |

**Models that DO NOT work (context < 64K):**
- `gemma:2b`, `gemma:7b`, `gemma2:*` — all 8K context
- `phi3:*` — 131K context but 3.8B params, may be too small

**Windows host setup:**
```powershell
# 1. Allow external connections
setx OLLAMA_HOST "0.0.0.0:11434"

# 2. Pull model
ollama pull llama3.1:8b

# 3. Restart Ollama service
```

---

## Groq Fallback — Reasoning Effort & Function Calling Issues (Session 2026-07-25)

**Problem:** When OpenRouter fails and fallback to Groq triggers, Hermes sends `reasoning_effort` parameter and expects function calling, but Groq models don't support these.

**Errors observed:**
1. `HTTP 400: \`reasoning_effort\` is not supported with this model` (llama-3.3-70b-versatile)
2. `property 'think' is unsupported` (openai/gpt-oss-20b)
3. Function calling validation failures: `attempted to call tool 'clarify...' which was not in request.tools`

**Root Cause:** Hermes global config has `reasoning_effort: medium` and toolsets that enable function calling. Groq's OpenAI-compatible endpoint doesn't support these parameters.

**Workarounds applied:**
```bash
# Disable reasoning globally
/opt/hermes/.venv/bin/hermes config set model.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set agent.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set delegation.reasoning_effort none
```

**Better approach:** Use a Groq model that supports function calling natively, or accept that fallback will be text-only (no tools). For production fallback, consider:
- Using `llama-3.1-70b-versatile` (deprecated) → `llama-3.3-70b-versatile` works but no function calling
- Or configure fallback to use a provider that matches primary's capabilities

**Lesson:** When configuring `fallback_model`, ensure the fallback provider supports the same features (reasoning_effort, function calling, toolsets) as the primary, or disable those features globally.

---

## TTS Cron Job Troubleshooting (Session 2026-07-05)

### Root causes

> **Prerequisite**: Familiarity with the `umbrel` skill (paths, persistence, container model) and the `hermes-agent` skill (CLI reference, config structure).

---

## Script Wrapper Arguments Not Expanded (Session 2026-07-25)

**Problem:** Cron job with `script: "cron_wrapper.sh \"Backup Seletivo Hermes\" /opt/data/scripts/backup-hermes-selective.sh"` failed with `Script not found: /opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh` — the scheduler treats the entire string as a single script filename instead of parsing arguments.

**Root Cause:** The cron job's `script` field is designed for a single executable file (or shell command when `no_agent=true`). It does not perform shell word-splitting on the value. When the whole `cron_wrapper.sh "args..."` string is stored as the script name, the executor looks for a file literally named `cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh`, which doesn't exist.

**Fix:** Create a dedicated wrapper script that embeds the arguments, then point the cron job to that single script:

```bash
# 1. Create wrapper with baked-in arguments
cat > /opt/data/scripts/backup-hermes-daily.sh << 'EOF'
#!/usr/bin/env bash
/opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh
EOF
chmod +x /opt/data/scripts/backup-hermes-daily.sh

# 2. Update cron job to use the wrapper
/opt/hermes/.venv/bin/hermes cron edit <job_id> --script backup-hermes-daily.sh
```

**Lesson:** Never put shell commands with arguments directly in the `script` field of a cron job. Always use a single executable file as the entry point.

---

## Ollama on Windows Host — Correct URL Configuration (Session 2026-07-25)

**Problem:** Hermes on Umbrel (containerized) could not connect to Ollama running on the Windows host. The configured URL `http://10.21.0.1:11434/v1` timed out / connection refused.

**Root Cause:** The IP `10.21.0.1` is an internal Docker network address that does not reliably route to the Windows host from inside the Umbrel container. The correct Docker Desktop alias is `host.docker.internal`.

**Fix:** Update the Ollama provider base URL:

```bash
/opt/hermes/.venv/bin/hermes config set providers.ollama.base_url http://host.docker.internal:11434/v1
```

**Verification:** From inside the container:
```bash
curl http://host.docker.internal:11434/api/tags
# Should return list of models pulled on Windows host
```

**Models that work with Hermes (64K+ context required):**
| Model | Size | Context | RAM |
|-------|------|---------|-----|
| `llama3.1:8b` | 4.7GB | 128K | ~8GB |
| `qwen2.5:14b` | 9GB | 128K | ~16GB |
| `mistral-nemo:12b` | 7GB | 128K | ~16GB |

**Models that DO NOT work (context < 64K):**
- `gemma:2b`, `gemma:7b`, `gemma2:*` — all 8K context
- `phi3:*` — 131K context but 3.8B params, may be too small

**Windows host setup:**
```powershell
# 1. Allow external connections
setx OLLAMA_HOST "0.0.0.0:11434"

# 2. Pull model
ollama pull llama3.1:8b

# 3. Restart Ollama service
```

---

## Groq Fallback — Reasoning Effort & Function Calling Issues (Session 2026-07-25)

**Problem:** When OpenRouter fails and fallback to Groq triggers, Hermes sends `reasoning_effort` parameter and expects function calling, but Groq models don't support these.

**Errors observed:**
1. `HTTP 400: \`reasoning_effort\` is not supported with this model` (llama-3.3-70b-versatile)
2. `property 'think' is unsupported` (openai/gpt-oss-20b)
3. Function calling validation failures: `attempted to call tool 'clarify...' which was not in request.tools`

**Root Cause:** Hermes global config has `reasoning_effort: medium` and toolsets that enable function calling. Groq's OpenAI-compatible endpoint doesn't support these parameters.

**Workarounds applied:**
```bash
# Disable reasoning globally
/opt/hermes/.venv/bin/hermes config set model.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set agent.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set delegation.reasoning_effort none
```

**Better approach:** Use a Groq model that supports function calling natively, or accept that fallback will be text-only (no tools). For production fallback, consider:
- Using `llama-3.1-70b-versatile` (deprecated) → `llama-3.3-70b-versatile` works but no function calling
- Or configure fallback to use a provider that matches primary's capabilities

**Lesson:** When configuring `fallback_model`, ensure the fallback provider supports the same features (reasoning_effort, function calling, toolsets) as the primary, or disable those features globally.

---

## TTS Cron Job Troubleshooting (Session 2026-07-05)

### Root causes
|---------|------|
| Persistent Hermes home (config, sessions, skills, logs) | `/opt/data` |
| Hermes CLI binary (venv) | `/opt/hermes/.venv/bin/hermes` |
| Hermes CLI symlink | `/opt/hermes/bin/hermes` |
| Config file | `/opt/data/config.yaml` |
| Secrets / API keys | `/opt/data/.env` (managed via `hermes auth` / `hermes config`) |
| Gateway logs | `/opt/data/logs/gateway.log` |
| Skills directory | `/opt/data/skills/` |

---

## Script Wrapper Arguments Not Expanded (Session 2026-07-25)

**Problem:** Cron job with `script: "cron_wrapper.sh \"Backup Seletivo Hermes\" /opt/data/scripts/backup-hermes-selective.sh"` failed with `Script not found: /opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh` — the scheduler treats the entire string as a single script filename instead of parsing arguments.

**Root Cause:** The cron job's `script` field is designed for a single executable file (or shell command when `no_agent=true`). It does not perform shell word-splitting on the value. When the whole `cron_wrapper.sh "args..."` string is stored as the script name, the executor looks for a file literally named `cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh`, which doesn't exist.

**Fix:** Create a dedicated wrapper script that embeds the arguments, then point the cron job to that single script:

```bash
# 1. Create wrapper with baked-in arguments
cat > /opt/data/scripts/backup-hermes-daily.sh << 'EOF'
#!/usr/bin/env bash
/opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh
EOF
chmod +x /opt/data/scripts/backup-hermes-daily.sh

# 2. Update cron job to use the wrapper
/opt/hermes/.venv/bin/hermes cron edit <job_id> --script backup-hermes-daily.sh
```

**Lesson:** Never put shell commands with arguments directly in the `script` field of a cron job. Always use a single executable file as the entry point.

---

## Ollama on Windows Host — Correct URL Configuration (Session 2026-07-25)

**Problem:** Hermes on Umbrel (containerized) could not connect to Ollama running on the Windows host. The configured URL `http://10.21.0.1:11434/v1` timed out / connection refused.

**Root Cause:** The IP `10.21.0.1` is an internal Docker network address that does not reliably route to the Windows host from inside the Umbrel container. The correct Docker Desktop alias is `host.docker.internal`.

**Fix:** Update the Ollama provider base URL:

```bash
/opt/hermes/.venv/bin/hermes config set providers.ollama.base_url http://host.docker.internal:11434/v1
```

**Verification:** From inside the container:
```bash
curl http://host.docker.internal:11434/api/tags
# Should return list of models pulled on Windows host
```

**Models that work with Hermes (64K+ context required):**
| Model | Size | Context | RAM |
|-------|------|---------|-----|
| `llama3.1:8b` | 4.7GB | 128K | ~8GB |
| `qwen2.5:14b` | 9GB | 128K | ~16GB |
| `mistral-nemo:12b` | 7GB | 128K | ~16GB |

**Models that DO NOT work (context < 64K):**
- `gemma:2b`, `gemma:7b`, `gemma2:*` — all 8K context
- `phi3:*` — 131K context but 3.8B params, may be too small

**Windows host setup:**
```powershell
# 1. Allow external connections
setx OLLAMA_HOST "0.0.0.0:11434"

# 2. Pull model
ollama pull llama3.1:8b

# 3. Restart Ollama service
```

---

## Groq Fallback — Reasoning Effort & Function Calling Issues (Session 2026-07-25)

**Problem:** When OpenRouter fails and fallback to Groq triggers, Hermes sends `reasoning_effort` parameter and expects function calling, but Groq models don't support these.

**Errors observed:**
1. `HTTP 400: \`reasoning_effort\` is not supported with this model` (llama-3.3-70b-versatile)
2. `property 'think' is unsupported` (openai/gpt-oss-20b)
3. Function calling validation failures: `attempted to call tool 'clarify...' which was not in request.tools`

**Root Cause:** Hermes global config has `reasoning_effort: medium` and toolsets that enable function calling. Groq's OpenAI-compatible endpoint doesn't support these parameters.

**Workarounds applied:**
```bash
# Disable reasoning globally
/opt/hermes/.venv/bin/hermes config set model.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set agent.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set delegation.reasoning_effort none
```

**Better approach:** Use a Groq model that supports function calling natively, or accept that fallback will be text-only (no tools). For production fallback, consider:
- Using `llama-3.1-70b-versatile` (deprecated) → `llama-3.3-70b-versatile` works but no function calling
- Or configure fallback to use a provider that matches primary's capabilities

**Lesson:** When configuring `fallback_model`, ensure the fallback provider supports the same features (reasoning_effort, function calling, toolsets) as the primary, or disable those features globally.

---

## TTS Cron Job Troubleshooting (Session 2026-07-05)

### Root causes

```bash
# Use the venv hermes binary (not host PATH)
/opt/hermes/.venv/bin/hermes config set <key> <value>

# View current config
/opt/hermes/.venv/bin/hermes config show
```

### Common Config Operations

```bash
# Enable web toolset + set Tavily as backend
/opt/hermes/.venv/bin/hermes config set toolsets '["hermes-cli", "web"]'
/opt/hermes/.venv/bin/hermes config set web.backend tavily

# Add MCP server (e.g., Tavily for /research + /map endpoints)
/opt/hermes/.venv/bin/hermes config set mcp_servers.tavily.url 'https://mcp.tavily.com/mcp/'
/opt/hermes/.venv/bin/hermes config set mcp_servers.tavily.auth oauth

# Add new LLM provider (e.g., Groq, Together, Fireworks)

### 🧱 TTS Dependency Chain

**When using custom venvs:** Always install core dependencies:
```bash
/opt/data/voice-venv/bin/pip install edge-tts sounddevice faster-whisper
/opt/data/voice-venv/bin/uv pip install hermes # Para garantir hermes_tools
```

### 🤖 Cron Job Fix

```bash
/opt/hermes/.venv/bin/hermes config set \
  tts.provider_edge_tts.python_path \
  /opt/data/voice-venv/bin/python
```
# API key references .env variable — no hardcoded secrets
/opt/hermes/.venv/bin/hermes config set providers.groq.base_url https://api.groq.com/openai/v1
/opt/hermes/.venv/bin/hermes config set providers.groq.api_key '${GROQ_API_KEY}'

# Verify changes
/opt/hermes/.venv/bin/hermes config show | grep -A2 -E 'toolsets|web:|mcp_servers|providers'
```

---

## Script Wrapper Arguments Not Expanded (Session 2026-07-25)

**Problem:** Cron job with `script: "cron_wrapper.sh \"Backup Seletivo Hermes\" /opt/data/scripts/backup-hermes-selective.sh"` failed with `Script not found: /opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh` — the scheduler treats the entire string as a single script filename instead of parsing arguments.

**Root Cause:** The cron job's `script` field is designed for a single executable file (or shell command when `no_agent=true`). It does not perform shell word-splitting on the value. When the whole `cron_wrapper.sh "args..."` string is stored as the script name, the executor looks for a file literally named `cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh`, which doesn't exist.

**Fix:** Create a dedicated wrapper script that embeds the arguments, then point the cron job to that single script:

```bash
# 1. Create wrapper with baked-in arguments
cat > /opt/data/scripts/backup-hermes-daily.sh << 'EOF'
#!/usr/bin/env bash
/opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh
EOF
chmod +x /opt/data/scripts/backup-hermes-daily.sh

# 2. Update cron job to use the wrapper
/opt/hermes/.venv/bin/hermes cron edit <job_id> --script backup-hermes-daily.sh
```

**Lesson:** Never put shell commands with arguments directly in the `script` field of a cron job. Always use a single executable file as the entry point.

---

## Ollama on Windows Host — Correct URL Configuration (Session 2026-07-25)

**Problem:** Hermes on Umbrel (containerized) could not connect to Ollama running on the Windows host. The configured URL `http://10.21.0.1:11434/v1` timed out / connection refused.

**Root Cause:** The IP `10.21.0.1` is an internal Docker network address that does not reliably route to the Windows host from inside the Umbrel container. The correct Docker Desktop alias is `host.docker.internal`.

**Fix:** Update the Ollama provider base URL:

```bash
/opt/hermes/.venv/bin/hermes config set providers.ollama.base_url http://host.docker.internal:11434/v1
```

**Verification:** From inside the container:
```bash
curl http://host.docker.internal:11434/api/tags
# Should return list of models pulled on Windows host
```

**Models that work with Hermes (64K+ context required):**
| Model | Size | Context | RAM |
|-------|------|---------|-----|
| `llama3.1:8b` | 4.7GB | 128K | ~8GB |
| `qwen2.5:14b` | 9GB | 128K | ~16GB |
| `mistral-nemo:12b` | 7GB | 128K | ~16GB |

**Models that DO NOT work (context < 64K):**
- `gemma:2b`, `gemma:7b`, `gemma2:*` — all 8K context
- `phi3:*` — 131K context but 3.8B params, may be too small

**Windows host setup:**
```powershell
# 1. Allow external connections
setx OLLAMA_HOST "0.0.0.0:11434"

# 2. Pull model
ollama pull llama3.1:8b

# 3. Restart Ollama service
```

---

## Groq Fallback — Reasoning Effort & Function Calling Issues (Session 2026-07-25)

**Problem:** When OpenRouter fails and fallback to Groq triggers, Hermes sends `reasoning_effort` parameter and expects function calling, but Groq models don't support these.

**Errors observed:**
1. `HTTP 400: \`reasoning_effort\` is not supported with this model` (llama-3.3-70b-versatile)
2. `property 'think' is unsupported` (openai/gpt-oss-20b)
3. Function calling validation failures: `attempted to call tool 'clarify...' which was not in request.tools`

**Root Cause:** Hermes global config has `reasoning_effort: medium` and toolsets that enable function calling. Groq's OpenAI-compatible endpoint doesn't support these parameters.

**Workarounds applied:**
```bash
# Disable reasoning globally
/opt/hermes/.venv/bin/hermes config set model.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set agent.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set delegation.reasoning_effort none
```

**Better approach:** Use a Groq model that supports function calling natively, or accept that fallback will be text-only (no tools). For production fallback, consider:
- Using `llama-3.1-70b-versatile` (deprecated) → `llama-3.3-70b-versatile` works but no function calling
- Or configure fallback to use a provider that matches primary's capabilities

**Lesson:** When configuring `fallback_model`, ensure the fallback provider supports the same features (reasoning_effort, function calling, toolsets) as the primary, or disable those features globally.

---

## TTS Cron Job Troubleshooting (Session 2026-07-05)

### Root causes

```bash
# Restart gateway service only (fast, preserves dashboard)
s6-svc -r /run/s6/services/hermes-gateway

# Or via Umbrel UI:
# Settings → Apps → Hermes Agent → Restart
# (or right-click/long-press app icon on homescreen)
```

> **Why**: Toolset/backend config is read at gateway startup. The CLI `hermes config set` writes to `/opt/data/config.yaml` immediately, but the running gateway process doesn't hot-reload it.

---

## Script Wrapper Arguments Not Expanded (Session 2026-07-25)

**Problem:** Cron job with `script: "cron_wrapper.sh \"Backup Seletivo Hermes\" /opt/data/scripts/backup-hermes-selective.sh"` failed with `Script not found: /opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh` — the scheduler treats the entire string as a single script filename instead of parsing arguments.

**Root Cause:** The cron job's `script` field is designed for a single executable file (or shell command when `no_agent=true`). It does not perform shell word-splitting on the value. When the whole `cron_wrapper.sh "args..."` string is stored as the script name, the executor looks for a file literally named `cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh`, which doesn't exist.

**Fix:** Create a dedicated wrapper script that embeds the arguments, then point the cron job to that single script:

```bash
# 1. Create wrapper with baked-in arguments
cat > /opt/data/scripts/backup-hermes-daily.sh << 'EOF'
#!/usr/bin/env bash
/opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh
EOF
chmod +x /opt/data/scripts/backup-hermes-daily.sh

# 2. Update cron job to use the wrapper
/opt/hermes/.venv/bin/hermes cron edit <job_id> --script backup-hermes-daily.sh
```

**Lesson:** Never put shell commands with arguments directly in the `script` field of a cron job. Always use a single executable file as the entry point.

---

## Ollama on Windows Host — Correct URL Configuration (Session 2026-07-25)

**Problem:** Hermes on Umbrel (containerized) could not connect to Ollama running on the Windows host. The configured URL `http://10.21.0.1:11434/v1` timed out / connection refused.

**Root Cause:** The IP `10.21.0.1` is an internal Docker network address that does not reliably route to the Windows host from inside the Umbrel container. The correct Docker Desktop alias is `host.docker.internal`.

**Fix:** Update the Ollama provider base URL:

```bash
/opt/hermes/.venv/bin/hermes config set providers.ollama.base_url http://host.docker.internal:11434/v1
```

**Verification:** From inside the container:
```bash
curl http://host.docker.internal:11434/api/tags
# Should return list of models pulled on Windows host
```

**Models that work with Hermes (64K+ context required):**
| Model | Size | Context | RAM |
|-------|------|---------|-----|
| `llama3.1:8b` | 4.7GB | 128K | ~8GB |
| `qwen2.5:14b` | 9GB | 128K | ~16GB |
| `mistral-nemo:12b` | 7GB | 128K | ~16GB |

**Models that DO NOT work (context < 64K):**
- `gemma:2b`, `gemma:7b`, `gemma2:*` — all 8K context
- `phi3:*` — 131K context but 3.8B params, may be too small

**Windows host setup:**
```powershell
# 1. Allow external connections
setx OLLAMA_HOST "0.0.0.0:11434"

# 2. Pull model
ollama pull llama3.1:8b

# 3. Restart Ollama service
```

---

## Groq Fallback — Reasoning Effort & Function Calling Issues (Session 2026-07-25)

**Problem:** When OpenRouter fails and fallback to Groq triggers, Hermes sends `reasoning_effort` parameter and expects function calling, but Groq models don't support these.

**Errors observed:**
1. `HTTP 400: \`reasoning_effort\` is not supported with this model` (llama-3.3-70b-versatile)
2. `property 'think' is unsupported` (openai/gpt-oss-20b)
3. Function calling validation failures: `attempted to call tool 'clarify...' which was not in request.tools`

**Root Cause:** Hermes global config has `reasoning_effort: medium` and toolsets that enable function calling. Groq's OpenAI-compatible endpoint doesn't support these parameters.

**Workarounds applied:**
```bash
# Disable reasoning globally
/opt/hermes/.venv/bin/hermes config set model.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set agent.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set delegation.reasoning_effort none
```

**Better approach:** Use a Groq model that supports function calling natively, or accept that fallback will be text-only (no tools). For production fallback, consider:
- Using `llama-3.1-70b-versatile` (deprecated) → `llama-3.3-70b-versatile` works but no function calling
- Or configure fallback to use a provider that matches primary's capabilities

**Lesson:** When configuring `fallback_model`, ensure the fallback provider supports the same features (reasoning_effort, function calling, toolsets) as the primary, or disable those features globally.

---

## TTS Cron Job Troubleshooting (Session 2026-07-05)

### Root causes

```bash
# 1. Confirm config persisted
/opt/hermes/.venv/bin/hermes config show

# 2. Test in a fresh session
/opt/hermes/.venv/bin/hermes chat -q "Search for latest accessibility news in Brazil"
# Should use web_search → web_extract via Tavily
```

---

## Script Wrapper Arguments Not Expanded (Session 2026-07-25)

**Problem:** Cron job with `script: "cron_wrapper.sh \"Backup Seletivo Hermes\" /opt/data/scripts/backup-hermes-selective.sh"` failed with `Script not found: /opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh` — the scheduler treats the entire string as a single script filename instead of parsing arguments.

**Root Cause:** The cron job's `script` field is designed for a single executable file (or shell command when `no_agent=true`). It does not perform shell word-splitting on the value. When the whole `cron_wrapper.sh "args..."` string is stored as the script name, the executor looks for a file literally named `cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh`, which doesn't exist.

**Fix:** Create a dedicated wrapper script that embeds the arguments, then point the cron job to that single script:

```bash
# 1. Create wrapper with baked-in arguments
cat > /opt/data/scripts/backup-hermes-daily.sh << 'EOF'
#!/usr/bin/env bash
/opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh
EOF
chmod +x /opt/data/scripts/backup-hermes-daily.sh

# 2. Update cron job to use the wrapper
/opt/hermes/.venv/bin/hermes cron edit <job_id> --script backup-hermes-daily.sh
```

**Lesson:** Never put shell commands with arguments directly in the `script` field of a cron job. Always use a single executable file as the entry point.

---

## Ollama on Windows Host — Correct URL Configuration (Session 2026-07-25)

**Problem:** Hermes on Umbrel (containerized) could not connect to Ollama running on the Windows host. The configured URL `http://10.21.0.1:11434/v1` timed out / connection refused.

**Root Cause:** The IP `10.21.0.1` is an internal Docker network address that does not reliably route to the Windows host from inside the Umbrel container. The correct Docker Desktop alias is `host.docker.internal`.

**Fix:** Update the Ollama provider base URL:

```bash
/opt/hermes/.venv/bin/hermes config set providers.ollama.base_url http://host.docker.internal:11434/v1
```

**Verification:** From inside the container:
```bash
curl http://host.docker.internal:11434/api/tags
# Should return list of models pulled on Windows host
```

**Models that work with Hermes (64K+ context required):**
| Model | Size | Context | RAM |
|-------|------|---------|-----|
| `llama3.1:8b` | 4.7GB | 128K | ~8GB |
| `qwen2.5:14b` | 9GB | 128K | ~16GB |
| `mistral-nemo:12b` | 7GB | 128K | ~16GB |

**Models that DO NOT work (context < 64K):**
- `gemma:2b`, `gemma:7b`, `gemma2:*` — all 8K context
- `phi3:*` — 131K context but 3.8B params, may be too small

**Windows host setup:**
```powershell
# 1. Allow external connections
setx OLLAMA_HOST "0.0.0.0:11434"

# 2. Pull model
ollama pull llama3.1:8b

# 3. Restart Ollama service
```

---

## Groq Fallback — Reasoning Effort & Function Calling Issues (Session 2026-07-25)

**Problem:** When OpenRouter fails and fallback to Groq triggers, Hermes sends `reasoning_effort` parameter and expects function calling, but Groq models don't support these.

**Errors observed:**
1. `HTTP 400: \`reasoning_effort\` is not supported with this model` (llama-3.3-70b-versatile)
2. `property 'think' is unsupported` (openai/gpt-oss-20b)
3. Function calling validation failures: `attempted to call tool 'clarify...' which was not in request.tools`

**Root Cause:** Hermes global config has `reasoning_effort: medium` and toolsets that enable function calling. Groq's OpenAI-compatible endpoint doesn't support these parameters.

**Workarounds applied:**
```bash
# Disable reasoning globally
/opt/hermes/.venv/bin/hermes config set model.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set agent.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set delegation.reasoning_effort none
```

**Better approach:** Use a Groq model that supports function calling natively, or accept that fallback will be text-only (no tools). For production fallback, consider:
- Using `llama-3.1-70b-versatile` (deprecated) → `llama-3.3-70b-versatile` works but no function calling
- Or configure fallback to use a provider that matches primary's capabilities

**Lesson:** When configuring `fallback_model`, ensure the fallback provider supports the same features (reasoning_effort, function calling, toolsets) as the primary, or disable those features globally.

---

## TTS Cron Job Troubleshooting (Session 2026-07-05)

### Root causes
|-------|------------|
| `hermes: command not found` | Use full path: `/opt/hermes/.venv/bin/hermes` |
| Config changes not taking effect | Gateway restart required via s6 (see above) |
| Editing config.yaml directly fails | Use `hermes config set` — direct writes are blocked by design |
| `.env` cannot be read directly | Use `hermes config show` to verify keys are loaded (shows masked values) |
| `host.docker.internal` unreliable | Use Docker service names for other Umbrel apps; `localhost` is container-local only |
| No `hermes update` allowed | Versions managed by umbrelOS app updates (pinned Docker images) |
| `hermes config set toolsets` writes a string, not a YAML list | The CLI stores `toolsets: '["..."]'` as a single string. This prevents the gateway from loading toolsets correctly. Fix by setting `enabled_toolsets` on each cron job, or edit `/opt/data/config.yaml` manually outside the agent (see Cron Jobs section) |

---

## Script Wrapper Arguments Not Expanded (Session 2026-07-25)

**Problem:** Cron job with `script: "cron_wrapper.sh \"Backup Seletivo Hermes\" /opt/data/scripts/backup-hermes-selective.sh"` failed with `Script not found: /opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh` — the scheduler treats the entire string as a single script filename instead of parsing arguments.

**Root Cause:** The cron job's `script` field is designed for a single executable file (or shell command when `no_agent=true`). It does not perform shell word-splitting on the value. When the whole `cron_wrapper.sh "args..."` string is stored as the script name, the executor looks for a file literally named `cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh`, which doesn't exist.

**Fix:** Create a dedicated wrapper script that embeds the arguments, then point the cron job to that single script:

```bash
# 1. Create wrapper with baked-in arguments
cat > /opt/data/scripts/backup-hermes-daily.sh << 'EOF'
#!/usr/bin/env bash
/opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh
EOF
chmod +x /opt/data/scripts/backup-hermes-daily.sh

# 2. Update cron job to use the wrapper
/opt/hermes/.venv/bin/hermes cron edit <job_id> --script backup-hermes-daily.sh
```

**Lesson:** Never put shell commands with arguments directly in the `script` field of a cron job. Always use a single executable file as the entry point.

---

## Ollama on Windows Host — Correct URL Configuration (Session 2026-07-25)

**Problem:** Hermes on Umbrel (containerized) could not connect to Ollama running on the Windows host. The configured URL `http://10.21.0.1:11434/v1` timed out / connection refused.

**Root Cause:** The IP `10.21.0.1` is an internal Docker network address that does not reliably route to the Windows host from inside the Umbrel container. The correct Docker Desktop alias is `host.docker.internal`.

**Fix:** Update the Ollama provider base URL:

```bash
/opt/hermes/.venv/bin/hermes config set providers.ollama.base_url http://host.docker.internal:11434/v1
```

**Verification:** From inside the container:
```bash
curl http://host.docker.internal:11434/api/tags
# Should return list of models pulled on Windows host
```

**Models that work with Hermes (64K+ context required):**
| Model | Size | Context | RAM |
|-------|------|---------|-----|
| `llama3.1:8b` | 4.7GB | 128K | ~8GB |
| `qwen2.5:14b` | 9GB | 128K | ~16GB |
| `mistral-nemo:12b` | 7GB | 128K | ~16GB |

**Models that DO NOT work (context < 64K):**
- `gemma:2b`, `gemma:7b`, `gemma2:*` — all 8K context
- `phi3:*` — 131K context but 3.8B params, may be too small

**Windows host setup:**
```powershell
# 1. Allow external connections
setx OLLAMA_HOST "0.0.0.0:11434"

# 2. Pull model
ollama pull llama3.1:8b

# 3. Restart Ollama service
```

---

## Groq Fallback — Reasoning Effort & Function Calling Issues (Session 2026-07-25)

**Problem:** When OpenRouter fails and fallback to Groq triggers, Hermes sends `reasoning_effort` parameter and expects function calling, but Groq models don't support these.

**Errors observed:**
1. `HTTP 400: \`reasoning_effort\` is not supported with this model` (llama-3.3-70b-versatile)
2. `property 'think' is unsupported` (openai/gpt-oss-20b)
3. Function calling validation failures: `attempted to call tool 'clarify...' which was not in request.tools`

**Root Cause:** Hermes global config has `reasoning_effort: medium` and toolsets that enable function calling. Groq's OpenAI-compatible endpoint doesn't support these parameters.

**Workarounds applied:**
```bash
# Disable reasoning globally
/opt/hermes/.venv/bin/hermes config set model.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set agent.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set delegation.reasoning_effort none
```

**Better approach:** Use a Groq model that supports function calling natively, or accept that fallback will be text-only (no tools). For production fallback, consider:
- Using `llama-3.1-70b-versatile` (deprecated) → `llama-3.3-70b-versatile` works but no function calling
- Or configure fallback to use a provider that matches primary's capabilities

**Lesson:** When configuring `fallback_model`, ensure the fallback provider supports the same features (reasoning_effort, function calling, toolsets) as the primary, or disable those features globally.

---

## TTS Cron Job Troubleshooting (Session 2026-07-05)

### Root causes

### Setup Pattern

```bash
# 1. Install Raft CLI in persistent npm prefix
npm config set prefix /opt/data/.npm-global
export PATH="/opt/data/.npm-global/bin:$PATH"
npm i -g @botiverse/raft@latest

# 2. Create External Agent in Raft (app.raft.build → Agents → + → Create External Agent)
#    Note the Server URL and Agent ID

# 3. Device-code login (requires browser approval)
raft agent login --server <SERVER_URL> --agent <AGENT_ID> --profile-slug <YOUR_SLUG>
# → approve user_code in browser

# 4. Configure Hermes
echo "RAFT_PROFILE=<YOUR_SLUG>" >> /opt/data/.env
echo 'PATH=/opt/data/.npm-global/bin:$PATH' >> /opt/data/.env

# 5. Restart gateway
s6-svc -r /run/s6/services/hermes-gateway
```

### Verification (Gateway Logs)

```text
[raft] Auto-generated bridge token
[raft] Raft channel listening on 127.0.0.1:XXXXX/wake
[raft] Spawned bridge pid=XXXX profile=<SLUG> endpoint=http://127.0.0.1:XXXXX/wake
✓ raft connected
```

### ⚠️ Critical: PATH Management for Custom Binaries (Added 2026-07-05)

O Hermes no Umbrel **não herda automaticamente** binários instalados em `/opt/data/.npm-global/bin`, `/opt/data/bin`, `/opt/data/home/.local/bin`. O gateway roda com PATH mínimo (`/usr/local/bin:/usr/bin:/bin`).

**Fix no `.env` (persistente via Umbrel Settings → Env vars):**
```bash
PATH=/opt/data/.npm-global/bin:/opt/data/bin:/opt/data/home/.local/bin:$PATH
RAFT_PROFILE=jornalista-inclusivo-bot
```

**Ou em cron jobs (script standalone):**
```bash
export PATH="/opt/data/.npm-global/bin:/opt/data/bin:/opt/data/home/.local/bin:$PATH"
```

**Binários afetados:**
| Binário | Localização | Usado por |
|---------|-------------|-----------|
| `raft` | `/opt/data/.npm-global/bin/raft` (symlink) | Raft adapter, cron jobs |
| `cosign` | `/opt/data/bin/cosign` | Security check script |
| `bsky` | `/opt/data/home/.local/bin/bsky` | Bluesky posting |
| `xurl` | `/opt/data/home/.local/bin/xurl` | X/Twitter posting |

### ⚠️ Critical: Telegram Bot Token Troubleshooting (Added 2026-07-05)

**Sintoma:** `telegram.error.InvalidToken: The token \`876079...WpOY\` was rejected by the server`

**Causas possíveis:**
1. Token revogado no @BotFather
2. Bot deletado/recriado
3. Token copiado incorretamente (truncado nos logs)

**Diagnóstico:**
```bash
# Testar token direto
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"

# Ver erros recentes no gateway
grep -c "$(date +%Y-%m-%d).*InvalidToken" /opt/data/logs/gateway.log
```

**Fix:**
1. Gerar novo token no @BotFather (`/mybots` → Bot → API Token → Revoke & Get new)
2. Atualizar no Umbrel: Settings → Hermes → Env vars → `TELEGRAM_BOT_TOKEN`
3. Reiniciar app Hermes no Umbrel (não só gateway)
4. Verificar logs: `✓ telegram connected`

---

### ⚠️ Tavily MCP OAuth Fails in Containerized Hermes (Added 2026-07-28)

**Sintoma:**
```
MCP OAuth for 'tavily': non-interactive environment and no cached tokens found.
Run `hermes mcp login tavily` interactively first to complete initial authorization.
```

**Causa:** `config.yaml` tem `mcp_servers.tavily.auth: oauth` mas container Hermes não tem browser/TTY para fluxo OAuth interativo.

**Config problemática:**
```yaml
tavily:
  auth: oauth
  enabled: true
  url: https://mcp.tavily.com/mcp/
  headers:
    Authorization: Bearer ***  # placeholder, não funciona com OAuth
```

**Soluções (ordem de preferência):**
1. **API Key direta** — se tem `TAVILY_API_KEY` em `/opt/data/.env`: mudar `auth: none` + header `Authorization: Bearer $TAVILY_API_KEY` (via `hermes config set`)
2. **Desabilitar** — `enabled: false` no config.yaml (para erro imediato)
3. **Login interativo** — `hermes mcp login tavily` em terminal anexado (token expira, não recomendado para cron)

**Como migrar para API Key (resolvido 2026-07-28):**
```bash
# 1. Confirmar chave no .env
grep TAVILY_API_KEY /opt/data/.env

# 2. Mudar auth para none
/opt/hermes/bin/hermes config set mcp_servers.tavily.auth none

# 3. Definir header com a variável de ambiente
/opt/hermes/bin/hermes config set mcp_servers.tavily.headers.Authorization "Bearer $TAVILY_API_KEY"
```

**Ação recomendada:** Verificar se `TAVILY_API_KEY` existe em `/opt/data/.env` e migrar para auth none.

**Padrão geral:** Qualquer MCP server configurado com `auth: oauth` falhará em ambiente headless/containerizado sem browser. Prefira `auth: none` + API key via header, ou desabilite se não crítico.

---

## References
```bash
# Carregar todas as vars TELEGRAM_, BSKY_, FB_, XURL_ do .env
export $(grep -E '^(TELEGRAM|BSKY|FB_|XURL|GROQ|HF|TAVILY|OPENAI|OLLAMA|GITHUB)_' /opt/data/.env | xargs)

# Mapeamento crítico: .env usa TELEGRAM_HOME_CHANNEL, script espera TELEGRAM_CHANNEL_ID
export TELEGRAM_CHANNEL_ID="${TELEGRAM_CHANNEL_ID:-${TELEGRAM_HOME_CHANNEL}}"
```

### ⚠️ Cron Jobs: Ensuring Toolsets Are Available (Added 2026-07-06)

Do not rely on the global `toolsets` config for cron jobs — the Hermes CLI currently writes it as a single YAML string rather than a list, which prevents the gateway from loading individual toolsets correctly. For any cron job that needs a specific tool, declare it explicitly on the job:

```bash
# TTS/audio cron job
hermes cronjob update <job_id> --enabled-toolsets tts

# Shell/script cron job
hermes cronjob update <job_id> --enabled-toolsets terminal
```

Verify in `/opt/data/cron/jobs.json`:
```json
{
  "enabled_toolsets": ["tts"]
}
```

This makes the job independent of the broken global `toolsets` value and guarantees the LLM can invoke `tts`, `terminal`, etc.

### Cron Jobs — Natural Language Output Pattern (Standardizado 2026-07-21)

**Todos os cronjob scripts que entregam no Telegram DEVEM outputar em linguagem natural Português**, não JSON bruto. Este padrão foi estabelecido na sessão 2026-07-21 e aplicado a todos os watchdogs/monitors.

#### Padrão Unificado

```python
# 1. Silent exit quando nada a reportar (watchdog pattern)
if not changes and not errors:
    return 0  # Sem output = sem mensagem no Telegram

# 2. Com mudanças/alertas: relatório estruturado em linguagem natural
lines = [f"📊 **{job_name}** — {datetime.now().strftime('%d/%m/%Y %H:%M')}"]
for item in items:
    lines.append(f"\n  • **{item.title}**")
    lines.append(f"    {item.detail}")

# Status claro
if critical:
    lines.append("\n⚠️ **ATENÇÃO**: ação necessária")
elif warning:
    lines.append("\n⚡ **CUIDADO**: monitorar")
else:
    lines.append("\n✅ **OK**: dentro da normalidade")

lines.append(f"\n---\n*Verificação automática a cada {interval} via Hermes cron*")
print("\n".join(lines))
```

#### Smart Cron Notification Filter — só notifica quando há ação necessária (padrão 2026-07-21)

**Sinal do usuário**: *"quero receber somente aquelas [notificações] com notificação = true e/ou houver qualquer alteração, atenção ou necessidade de ação, seja sua ou minha."*

O filtro inteligente (`smart_notify_filter.py`) fica entre o script real e a entrega do cron. Decide se deve imprimir (→ Telegram) ou ficar em silêncio baseado em:

1. **Exit code não-zero** → sempre notifica (é erro)
2. **Flag explícita** `NOTIFICATION: true` no output → força notificação
3. **Palavras-chave de ação** (regex): error, falha, timeout, limite, warning, changed, novo, action required, security, disk full, etc.
4. **Mudança de estado** — hash do output comparado com a última execução (persistido em `/opt/data/cron_notify_state/<job>.json`); se mudou e não é só timestamp, notifica
5. **Padrões "tudo OK"** (ok, sucesso, sem mudanças, nada a fazer) → suprime se for só isso

**Arquivo**: `scripts/smart_notify_filter.py` — copie para `~/.hermes/scripts/` junto com o script alvo antes de referenciar no cron job.

**Uso em wrapper Python** (já que `cronjob` tool exige script relativo a `~/.hermes/scripts/`, não pipe com `${PIPESTATUS[0]}`):

```python
# wrapper_filtered.py
import subprocess, sys
from smart_notify_filter import filter_output

SCRIPT = "/opt/data/scripts/meu_script.py"
FILTER = "/opt/data/scripts/smart_notify_filter.py"

result = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)
output = result.stdout + result.stderr
exit_code = result.returncode

filter_result = subprocess.run(
    [sys.executable, FILTER, "--job-name", "Meu Job", "--exit-code", str(exit_code)],
    input=output, capture_output=True, text=True
)

if filter_result.stdout:
    print(filter_result.stdout)
# Sempre exit 0 para não confundir scheduler
sys.exit(0)
```

**Pitfall**: a tool `cronjob` exige que `script=` seja um nome de arquivo relativo a `~/.hermes/scripts/`, não um caminho absoluto nem uma linha de comando com pipe. Para aplicar o filtro a um script existente sem reescrevê-lo, crie um `<nome>_filtered.py` wrapper que faz `subprocess.run([sys.executable, SCRIPT], capture_output=True)` → passa o output para o filtro → só imprime se o filtro decidir notificar → sempre `sys.exit(0)`.

#### Elementos Obrigatórios
- **Markdown** para renderização no Telegram
- **Emojis** para escaneamento visual rápido
- **Números** com separador de milhares (`1,234`)
- **Status line** explícita (✅ OK / ⚡ CUIDADO / ⚠️ ATENÇÃO / ❌ ERRO)
- **Footer** com contexto de automação
- **Silent exit** (return 0, no output) quando nada a reportar

#### Aplicado a (scripts em `/opt/data/scripts/`):
| Script | Cronjob | Descrição |
|--------|---------|-----------|
| `check_openrouter_rate.py` | `e11c70a86885` (30min) | OpenRouter rate-limit watchdog |
| `moltbook_monitor.py` | `582cdb557284` (15min) | Moltbook comentários + ciclo Auditor |
| `moltbook_verification_checker.py` | `7f7cd6d2f4b1` (5min) | Verificação challenges posts pendentes |
| `watch_hermes_shared.py` | `e005e2a045b5` (15min) | Watchdog pasta hermes-shared + mini-RAG |
| `backup-hermes-selective.sh` | `fbb2f2b8405a` (diário 03:00) | Backup seletivo (sem segredos) |

### Smart Cron Notification Filter — só notifica quando há ação necessária (padrão 2026-07-21)

**Sinal do usuário**: "quero receber somente aquelas [notificações] com notificação = true e/ou houver qualquer alteração, atenção ou necessidade de ação, seja sua ou minha." — formatar em linguagem natural (seção acima) resolve *legibilidade*, mas não resolve *volume*. O usuário quer os dois: legível E raro.

**Problema**: mesmo com output em linguagem natural, um watchdog `no_agent=True` que sempre imprime algo gera ruído a cada tick (a cada 5-15 min) mesmo quando nada mudou (ex: heartbeat "tudo OK" repetido).

**Solução**: um filtro Python que fica entre o script real e a entrega do cron. Decide se deve imprimir (→ Telegram) ou ficar em silêncio (→ nada entregue), baseado em:

1. **Exit code não-zero** → sempre notifica (é erro)
2. **Flag explícita** `NOTIFICATION: true` no output → força notificação
3. **Palavras-chave de ação** (regex): error, falha, timeout, limite, warning, changed, novo, action required, security, disk full, etc.
4. **Mudança de estado** — hash do output comparado com a última execução (persistido em `/opt/data/cron_notify_state/<job>.json`); se mudou e não é só timestamp, notifica
5. **Padrões "tudo OK"** (ok, sucesso, sem mudanças, nada a fazer) → suprime se for só isso

**Uso**:
```bash
# Script real produz output normalmente, você encanota pelo filtro:
meu_script.py 2>&1 | python3 smart_notify_filter.py --job-name "Nome do Job" --exit-code ${PIPESTATUS[0]}
```

Ou, para scripts Python, envolva com um wrapper `subprocess.run(...)` que captura stdout+stderr+exit code e repassa ao filtro (ver `scripts/smart_notify_filter.py`) — necessário quando o cron scheduler exige script relativo a `~/.hermes/scripts/` e pipes com `${PIPESTATUS[0]}` não são aceitos na declaração do job.

**Pitfall**: a tool `cronjob` exige que `script=` seja um nome de arquivo relativo a `~/.hermes/scripts/`, não um caminho absoluto nem uma linha de comando com pipe. Para aplicar o filtro a um script existente sem reescrevê-lo, crie um `<nome>_filtered.py` wrapper que faz `subprocess.run([sys.executable, SCRIPT], capture_output=True)` → passa o output para o filtro → só imprime se o filtro decidir notificar → sempre `sys.exit(0)` (não propague o exit code do script interno para não confundir o scheduler).

**Arquivo**: `scripts/smart_notify_filter.py` — copie para `~/.hermes/scripts/` junto com o script alvo antes de referenciar no cron job.

### Gmail IMAP Triage Pattern (Added 2026-07-19)

A robust pattern for daily Gmail triage for journalistic use cases (Jornalista Inclusivo):

**Config file:** `/opt/data/journali/imap-config.json`
```json
{
  "host": "imap.gmail.com",
  "port": 993,
  "username": "SEU_EMAIL@gmail.com",
  "password": "APP_PASSWORD_OU_SENHA",
  "search_folder": "INBOX"
}
```

**State file (deduplication):** `/opt/data/journali/processed-message-ids.jsonl` — one Message-ID per line, append-only.

**Output markdown:** `/opt/data/journali/triagem-YYYY-MM-DD.md` with structure:
- Header: run timestamp, window ("últimos 15 dias")
- Counts: total, by type (release | sugestao_de_pauta)
- Sections: `## Releases`, `## Sugestões de pautas`
- Per item: tipo, fonte (From), assunto, data do e-mail, link/Message-ID, resumo, palavras-chave encontradas, ângulo inclusivo sugerido (2–4 bullets)

**Cron job schedule:** `0 9 * * *` (daily 09:00) with `deliver: origin,telegram`

**Keywords filter (subject + body):**
- pessoas com deficiência / pessoa com deficiência
- neurodiversidade, autismo, TEA
- inclusão, acessibilidade, equidade, diversidade
- deficiência intelectual, deficiência visual, deficiência auditiva
- direitos humanos

**Classification:** heuristic (release keywords: "press release", "comunicado", "release", "imprensa", "para divulgação") + LLM refinement for angle extraction.

**Error handling:** if config file missing/incomplete → fail with explicit message listing what's missing.

### OpenRouter Rate-Limit Watchdog Pattern (Added 2026-07-19)

Monitor OpenRouter API rate limits for both free and paid tiers. Uses a cron job with `no_agent=True` (zero LLM cost) that runs every 30 minutes.

**Script:** `scripts/check_openrouter_rate.py` (in this skill) — reads `OPENROUTER_API_KEY` from `/opt/data/.env` and calls `https://openrouter.ai/api/v1/auth/key`.

**Cron job:**
```bash
hermes cronjob create --name "OpenRouter rate-limit watchdog" \
  --schedule "*/30 * * * *" \
  --script check_openrouter_rate.py \
  --no-agent \
  --deliver telegram \
  --workdir /opt/data
```

**Behavior:**
- Free tier: endpoint returns `null` for all limits → script prints JSON with nulls, cron delivers silently (empty output = no message if you adjust script).
- Paid tier: returns `limit_*` and `remaining_*` → cron delivers JSON to Telegram.
- Script loads `.env` directly (cron jobs don't inherit environment).
- Exit code 0 = success, non-zero = error message delivered.

**To make it quiet on free tier:** adjust script to only print when `remaining_*` is not null and below a threshold (e.g., `< 10%`).

---

## Script Wrapper Arguments Not Expanded (Session 2026-07-25)

**Problem:** Cron job with `script: "cron_wrapper.sh \"Backup Seletivo Hermes\" /opt/data/scripts/backup-hermes-selective.sh"` failed with `Script not found: /opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh` — the scheduler treats the entire string as a single script filename instead of parsing arguments.

**Root Cause:** The cron job's `script` field is designed for a single executable file (or shell command when `no_agent=true`). It does not perform shell word-splitting on the value. When the whole `cron_wrapper.sh "args..."` string is stored as the script name, the executor looks for a file literally named `cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh`, which doesn't exist.

**Fix:** Create a dedicated wrapper script that embeds the arguments, then point the cron job to that single script:

```bash
# 1. Create wrapper with baked-in arguments
cat > /opt/data/scripts/backup-hermes-daily.sh << 'EOF'
#!/usr/bin/env bash
/opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh
EOF
chmod +x /opt/data/scripts/backup-hermes-daily.sh

# 2. Update cron job to use the wrapper
/opt/hermes/.venv/bin/hermes cron edit <job_id> --script backup-hermes-daily.sh
```

**Lesson:** Never put shell commands with arguments directly in the `script` field of a cron job. Always use a single executable file as the entry point.

---

## Ollama on Windows Host — Correct URL Configuration (Session 2026-07-25)

**Problem:** Hermes on Umbrel (containerized) could not connect to Ollama running on the Windows host. The configured URL `http://10.21.0.1:11434/v1` timed out / connection refused.

**Root Cause:** The IP `10.21.0.1` is an internal Docker network address that does not reliably route to the Windows host from inside the Umbrel container. The correct Docker Desktop alias is `host.docker.internal`.

**Fix:** Update the Ollama provider base URL:

```bash
/opt/hermes/.venv/bin/hermes config set providers.ollama.base_url http://host.docker.internal:11434/v1
```

**Verification:** From inside the container:
```bash
curl http://host.docker.internal:11434/api/tags
# Should return list of models pulled on Windows host
```

**Models that work with Hermes (64K+ context required):**
| Model | Size | Context | RAM |
|-------|------|---------|-----|
| `llama3.1:8b` | 4.7GB | 128K | ~8GB |
| `qwen2.5:14b` | 9GB | 128K | ~16GB |
| `mistral-nemo:12b` | 7GB | 128K | ~16GB |

**Models that DO NOT work (context < 64K):**
- `gemma:2b`, `gemma:7b`, `gemma2:*` — all 8K context
- `phi3:*` — 131K context but 3.8B params, may be too small

**Windows host setup:**
```powershell
# 1. Allow external connections
setx OLLAMA_HOST "0.0.0.0:11434"

# 2. Pull model
ollama pull llama3.1:8b

# 3. Restart Ollama service
```

---

## Groq Fallback — Reasoning Effort & Function Calling Issues (Session 2026-07-25)

**Problem:** When OpenRouter fails and fallback to Groq triggers, Hermes sends `reasoning_effort` parameter and expects function calling, but Groq models don't support these.

**Errors observed:**
1. `HTTP 400: \`reasoning_effort\` is not supported with this model` (llama-3.3-70b-versatile)
2. `property 'think' is unsupported` (openai/gpt-oss-20b)
3. Function calling validation failures: `attempted to call tool 'clarify...' which was not in request.tools`

**Root Cause:** Hermes global config has `reasoning_effort: medium` and toolsets that enable function calling. Groq's OpenAI-compatible endpoint doesn't support these parameters.

**Workarounds applied:**
```bash
# Disable reasoning globally
/opt/hermes/.venv/bin/hermes config set model.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set agent.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set delegation.reasoning_effort none
```

**Better approach:** Use a Groq model that supports function calling natively, or accept that fallback will be text-only (no tools). For production fallback, consider:
- Using `llama-3.1-70b-versatile` (deprecated) → `llama-3.3-70b-versatile` works but no function calling
- Or configure fallback to use a provider that matches primary's capabilities

**Lesson:** When configuring `fallback_model`, ensure the fallback provider supports the same features (reasoning_effort, function calling, toolsets) as the primary, or disable those features globally.

---

## TTS Cron Job Troubleshooting (Session 2026-07-05)

### Root causes
|------|------|---------|
| `templates/ubuntu-docker-compose.yml` | Template | Docker Compose production-ready for Ubuntu |
| `templates/migrate-umbrel-to-ubuntu.sh` | Template | Automated migration script (Umbrel → Ubuntu) |
| `templates/ubuntu-systemd-native.md` | Template | Native Ubuntu install with systemd (no Docker) |
| `templates/nginx-reverse-proxy.conf` | Template | Nginx reverse proxy config with WebSocket support |
| `references/dashboard-chat-troubleshooting.md` | Reference | PATH corruption fix, null configs, wrapper bypass, .htpasswd recovery |
| `references/nginx-reverse-proxy.md` | Reference | Nginx proxy reference for chat/WebSocket |
| `references/umbrel-to-ubuntu-migration.md` | Reference | Complete migration guide with checklist |
| `references/cron-job-patterns.md` | Reference | Cron job failure patterns, provider setup, skill context management, TTS cron troubleshooting |
| `references/fallback-model-config.md` | Reference | Automatic fallback from OpenRouter to Groq/Ollama on rate limits/errors |
| `references/image-generation-openai-setup.md` | Reference | OpenAI DALL-E image generation setup on Umbrel (plugin enable, API key config, gateway restart) |
| `scripts/check_openrouter_rate.py` | Script | OpenRouter rate-limit watchdog (cron, no_agent=True) |

### How It Works

| Component | Role |
|-----------|------|
| Raft Server | Sends wake-hints via SSE to bridge |
| Bridge (`raft agent bridge`) | Forwards wake-hints as `POST /wake` to Hermes adapter |
| Hermes Adapter | Validates token, injects wake notice into agent session |
| Agent | Uses `raft message check/send` via CLI to read/reply |

### References
- `references/raft-external-agent.md` — Complete working example with Jornalista Inclusivo bot

---

## Script Wrapper Arguments Not Expanded (Session 2026-07-25)

**Problem:** Cron job with `script: "cron_wrapper.sh \"Backup Seletivo Hermes\" /opt/data/scripts/backup-hermes-selective.sh"` failed with `Script not found: /opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh` — the scheduler treats the entire string as a single script filename instead of parsing arguments.

**Root Cause:** The cron job's `script` field is designed for a single executable file (or shell command when `no_agent=true`). It does not perform shell word-splitting on the value. When the whole `cron_wrapper.sh "args..."` string is stored as the script name, the executor looks for a file literally named `cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh`, which doesn't exist.

**Fix:** Create a dedicated wrapper script that embeds the arguments, then point the cron job to that single script:

```bash
# 1. Create wrapper with baked-in arguments
cat > /opt/data/scripts/backup-hermes-daily.sh << 'EOF'
#!/usr/bin/env bash
/opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh
EOF
chmod +x /opt/data/scripts/backup-hermes-daily.sh

# 2. Update cron job to use the wrapper
/opt/hermes/.venv/bin/hermes cron edit <job_id> --script backup-hermes-daily.sh
```

**Lesson:** Never put shell commands with arguments directly in the `script` field of a cron job. Always use a single executable file as the entry point.

---

## Ollama on Windows Host — Correct URL Configuration (Session 2026-07-25)

**Problem:** Hermes on Umbrel (containerized) could not connect to Ollama running on the Windows host. The configured URL `http://10.21.0.1:11434/v1` timed out / connection refused.

**Root Cause:** The IP `10.21.0.1` is an internal Docker network address that does not reliably route to the Windows host from inside the Umbrel container. The correct Docker Desktop alias is `host.docker.internal`.

**Fix:** Update the Ollama provider base URL:

```bash
/opt/hermes/.venv/bin/hermes config set providers.ollama.base_url http://host.docker.internal:11434/v1
```

**Verification:** From inside the container:
```bash
curl http://host.docker.internal:11434/api/tags
# Should return list of models pulled on Windows host
```

**Models that work with Hermes (64K+ context required):**
| Model | Size | Context | RAM |
|-------|------|---------|-----|
| `llama3.1:8b` | 4.7GB | 128K | ~8GB |
| `qwen2.5:14b` | 9GB | 128K | ~16GB |
| `mistral-nemo:12b` | 7GB | 128K | ~16GB |

**Models that DO NOT work (context < 64K):**
- `gemma:2b`, `gemma:7b`, `gemma2:*` — all 8K context
- `phi3:*` — 131K context but 3.8B params, may be too small

**Windows host setup:**
```powershell
# 1. Allow external connections
setx OLLAMA_HOST "0.0.0.0:11434"

# 2. Pull model
ollama pull llama3.1:8b

# 3. Restart Ollama service
```

---

## Groq Fallback — Reasoning Effort & Function Calling Issues (Session 2026-07-25)

**Problem:** When OpenRouter fails and fallback to Groq triggers, Hermes sends `reasoning_effort` parameter and expects function calling, but Groq models don't support these.

**Errors observed:**
1. `HTTP 400: \`reasoning_effort\` is not supported with this model` (llama-3.3-70b-versatile)
2. `property 'think' is unsupported` (openai/gpt-oss-20b)
3. Function calling validation failures: `attempted to call tool 'clarify...' which was not in request.tools`

**Root Cause:** Hermes global config has `reasoning_effort: medium` and toolsets that enable function calling. Groq's OpenAI-compatible endpoint doesn't support these parameters.

**Workarounds applied:**
```bash
# Disable reasoning globally
/opt/hermes/.venv/bin/hermes config set model.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set agent.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set delegation.reasoning_effort none
```

**Better approach:** Use a Groq model that supports function calling natively, or accept that fallback will be text-only (no tools). For production fallback, consider:
- Using `llama-3.1-70b-versatile` (deprecated) → `llama-3.3-70b-versatile` works but no function calling
- Or configure fallback to use a provider that matches primary's capabilities

**Lesson:** When configuring `fallback_model`, ensure the fallback provider supports the same features (reasoning_effort, function calling, toolsets) as the primary, or disable those features globally.

---

## TTS Cron Job Troubleshooting (Session 2026-07-05)

### Root causes

**Root cause observed**: Kanban dispatcher spawning workers that crash every ~60s (`crashed=1`, `zombie worker` in logs), triggering OOM or s6-supervise restart loop.

**Diagnosis steps**:

```bash
# 1. Check gateway logs for crash pattern
tail -100 /opt/data/logs/gateway.log | grep -E "kanban|crashed|zombie|SIGTERM"

# 2. Look for dispatcher log lines like:
# kanban dispatcher: spawned=1 reclaimed=0 crashed=1 timed_out=0 promoted=1 auto_blocked=1
# kanban dispatcher: reaped 1 zombie worker(s), pids=[XXXX]

# 3. Check if kanban dispatcher is enabled in config
/opt/hermes/.venv/bin/hermes config get kanban.dispatch_in_gateway
```

**Fix**: Disable kanban dispatcher in gateway (keeps kanban CLI functional):

```bash
/opt/hermes/.venv/bin/hermes config set kanban.dispatch_in_gateway false
# Then restart gateway:
s6-svc -r /run/s6/services/hermes-gateway
```

**Verification**: After restart, logs should show:
```
kanban notifier: disabled via config kanban.dispatch_in_gateway=false
kanban dispatcher: disabled via config kanban.dispatch_in_gateway=false
```
And no more SIGTERM/restart cycles.

### Dashboard Web Chat "Unavailable" / Black Screen

**Symptom**: Browser shows black screen with `Chat unavailable: 1` or similar at `localhost:18790/chat`.

**Root causes observed**:

1. **Node.js not found by TUI Gateway** — The dashboard spawns a TUI gateway backend that requires `node`. If the container is missing Node or it is not on the process `PATH`, the backend aborts.
   - Log signature: `node not found — install Node.js to use the TUI.` (seen in container/compose logs and `gui.log`).
2. **Config YAML null values treated as empty sections** — The `tui_gateway.server` parser warns about `null` values for keys it expects to be maps/integers.
   - Log signature: `WARNING tui_gateway.server: config.yaml has empty section(s): 'context_file_max_chars', 'max_concurrent_sessions'. Remove the line(s) or set them to '{}'.`
   - This causes `session.create` to fail silently and the WebSocket closes with `reaped_sessions=1`.
3. **Gateway shutdown / restart pending** — If the gateway process was sent `SIGTERM` (e.g. via `s6-svc -r /run/service/gateway-default`), it enters a graceful shutdown and waits for active agent sessions (like an ongoing Telegram chat) to finish before exiting. Until it exits, it refuses new sessions.
4. **Umbrel TUI wrapper entry.js** — When `HERMES_TUI_DIR` points to `/app/umbrel-tui` (Umbrel's container default), a wrapper script at `/app/umbrel-tui/dist/entry.js` runs a provider bootstrap probe before delegating to the real TUI. If the `PATH` is corrupted (e.g. contains `$PATH` as a literal string), the probe fails silently and the wrapper exits with status 1, which the dashboard renders as `Chat unavailable: 1`.
   - Log signature: `Chat unavailable: 1` in browser (SystemExit(1) caught by websocket handler).
   - The wrapper also verifies `_has_any_provider_configured()`; if this probe times out or returns false, it launches an interactive setup that cannot complete in a web PTY context.

**Diagnosis steps**:

```bash
# 1. Check dashboard/TUI logs for config or node errors
tail -n 50 /opt/data/logs/gui.log | grep -i "tui_gateway\|node not found\|empty section"

# 2. Check gateway state (is it in shutdown?)
tail -n 20 /opt/data/logs/gateway.log | grep -i "SIGTERM\|shutdown\|starting"

# 3. Verify node exists inside the container
which node && node --version

# 4. Check if PATH is corrupted after Python import (literal $PATH string)
/opt/hermes/.venv/bin/python3 -c "import shutil, os; print('node:', shutil.which('node')); print('PATH:', os.environ.get('PATH', '')[:200])"
# If PATH contains '/opt/data/.npm-global/bin:$PATH' literally, the env var was overwritten by a shell-style string.
# This breaks shutil.which() and causes _make_tui_argv() to call sys.exit(1).

# 5. Verify the wrapper path vs native TUI path
echo $HERMES_TUI_DIR  # If /app/umbrel-tui, the wrapper is active.
cat /app/umbrel-tui/dist/entry.js | head -n 5  # Node.js wrapper that probes provider before delegating
```

**Fix**:

```bash
# Fix null configs (use the venv CLI)
/opt/hermes/.venv/bin/hermes config set max_concurrent_sessions 5
/opt/hermes/.venv/bin/hermes config set context_file_max_chars 100000

# Bypass the Umbrel wrapper by pointing directly to the native Hermes TUI
# This requires a FULL app restart (not just s6 service restart):
echo "HERMES_TUI_DIR=/opt/hermes/ui-tui" >> /opt/data/.env

# Restart services for config changes
/command/s6-svc -r /run/service/dashboard
/command/s6-svc -r /run/service/gateway-default

# After writing to .env, restart the Hermes app from the Umbrel UI:
#   Umbrel → Apps → Hermes Agent → Restart
# (s6-supervise will pick up the new HERMES_TUI_DIR on container boot)
```

> **Note**: The s6 service directories in this container are `/run/service/dashboard` and `/run/service/gateway-default`, not `/run/s6/services/...`.

### Tavily MCP Endpoints (research + map)

The Tavily MCP server (`https://mcp.tavily.com/mcp/`) provides 5 tools, all enabled by default when the server is added:

| Tool | Purpose | Available via MCP |
|------|---------|-------------------|
| `tavily_search` | Web search | ✅ |
| `tavily_extract` | Extract content from URLs | ✅ |
| `tavily_crawl` | Crawl website from URL | ✅ |
| **`tavily_research`** | **Comprehensive research on topic** | ✅ |
| **`tavily_map`** | **Map website structure (URLs list)** | ✅ |

**To add/enable Tavily MCP**:

```bash
# Add server (OAuth PKCE auth)
/opt/hermes/.venv/bin/hermes mcp add tavily --url https://mcp.tavily.com/mcp/ --auth oauth

# Verify tools discovered
/opt/hermes/.venv/bin/hermes mcp test tavily

## TTS / Voice Output Setup

### Enabling Voice (User-Side)

To let the user hear voice responses from the agent:

1. **Enable the `tts` toolset** — it is NOT in the default toolsets list on Umbrel:
   ```bash
   /opt/hermes/.venv/bin/hermes config set toolsets '["hermes-cli", "web", "file", "tts", "browser", "delegation", "cronjob", "skills"]'
   ```
   > **Known issue**: `hermes config set toolsets` currently writes this as a single YAML string, not a list. If TTS still does not load, set `enabled_toolsets: ["tts"]` directly on the cron job or session instead of relying on the global config.

2. **For cron jobs, force the toolset on the job itself**:
   ```bash
   hermes cronjob update <job_id> --enabled-toolsets tts
   ```

3. **Enable auto TTS** — requires `voice.auto_tts: true`:
   ```bash
   /opt/hermes/.venv/bin/hermes config set voice.auto_tts true
   ```

4. **Verify edge-tts is installed** in the voice venv:
   ```bash
   /opt/data/voice-venv/bin/pip install edge-tts sounddevice numpy faster-whisper
   /opt/data/voice-venv/bin/python -c "import edge_tts; print(edge_tts.__version__)"
   ```

5. **Restart gateway** (s6 will auto-restart — see Gateway Restart section).

6. **Start a fresh session** — toolset changes only take effect in a new session. On Telegram: `/new` or `/reset`.

### TTS Provider Configuration

Voice and provider are already configured in `/opt/data/config.yaml` by default:

| Setting | Default on Umbrel |
|---------|-------------------|
| `tts.provider` | `edge` (free, no API key) |
| `tts.edge.voice` | `pt-BR-FranciscaNeural` |
| `tts.provider_edge_tts.python_path` | `/opt/data/voice-venv/bin/python` |

To change voice or provider, edit the `tts:` section of config.yaml or use:
```bash
/opt/hermes/.venv/bin/hermes config set tts.edge.voice pt-BR-AntonioNeural
```

### Verifying Voice Works

After step 5 above, ask the agent a question. If TTS is active, the response arrives as a voice message (audio attachment) instead of plain text. To test manually:

```bash
/opt/data/voice-venv/bin/python -c "
import edge_tts, asyncio
async def test():
    await edge_tts.Communicate('Teste de voz.', 'pt-BR-FranciscaNeural').save('/tmp/tts_test.mp3')
asyncio.run(test())
" && ls -la /tmp/tts_test.mp3
```
/opt/hermes/.venv/bin/hermes mcp configure tavily
# → select 'all' or specific tools

# Restart gateway to pick up MCP tools
s6-svc -r /run/s6/services/hermes-gateway
```

**Test in session**:
```bash
/opt/hermes/.venv/bin/hermes chat -q "Use tavily_research to find latest accessibility guidelines for Brazilian journalism"
```

---

## Script Wrapper Arguments Not Expanded (Session 2026-07-25)

**Problem:** Cron job with `script: "cron_wrapper.sh \"Backup Seletivo Hermes\" /opt/data/scripts/backup-hermes-selective.sh"` failed with `Script not found: /opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh` — the scheduler treats the entire string as a single script filename instead of parsing arguments.

**Root Cause:** The cron job's `script` field is designed for a single executable file (or shell command when `no_agent=true`). It does not perform shell word-splitting on the value. When the whole `cron_wrapper.sh "args..."` string is stored as the script name, the executor looks for a file literally named `cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh`, which doesn't exist.

**Fix:** Create a dedicated wrapper script that embeds the arguments, then point the cron job to that single script:

```bash
# 1. Create wrapper with baked-in arguments
cat > /opt/data/scripts/backup-hermes-daily.sh << 'EOF'
#!/usr/bin/env bash
/opt/data/scripts/cron_wrapper.sh "Backup Seletivo Hermes" /opt/data/scripts/backup-hermes-selective.sh
EOF
chmod +x /opt/data/scripts/backup-hermes-daily.sh

# 2. Update cron job to use the wrapper
/opt/hermes/.venv/bin/hermes cron edit <job_id> --script backup-hermes-daily.sh
```

**Lesson:** Never put shell commands with arguments directly in the `script` field of a cron job. Always use a single executable file as the entry point.

---

## Ollama on Windows Host — Correct URL Configuration (Session 2026-07-25)

**Problem:** Hermes on Umbrel (containerized) could not connect to Ollama running on the Windows host. The configured URL `http://10.21.0.1:11434/v1` timed out / connection refused.

**Root Cause:** The IP `10.21.0.1` is an internal Docker network address that does not reliably route to the Windows host from inside the Umbrel container. The correct Docker Desktop alias is `host.docker.internal`.

**Fix:** Update the Ollama provider base URL:

```bash
/opt/hermes/.venv/bin/hermes config set providers.ollama.base_url http://host.docker.internal:11434/v1
```

**Verification:** From inside the container:
```bash
curl http://host.docker.internal:11434/api/tags
# Should return list of models pulled on Windows host
```

**Models that work with Hermes (64K+ context required):**
| Model | Size | Context | RAM |
|-------|------|---------|-----|
| `llama3.1:8b` | 4.7GB | 128K | ~8GB |
| `qwen2.5:14b` | 9GB | 128K | ~16GB |
| `mistral-nemo:12b` | 7GB | 128K | ~16GB |

**Models that DO NOT work (context < 64K):**
- `gemma:2b`, `gemma:7b`, `gemma2:*` — all 8K context
- `phi3:*` — 131K context but 3.8B params, may be too small

**Windows host setup:**
```powershell
# 1. Allow external connections
setx OLLAMA_HOST "0.0.0.0:11434"

# 2. Pull model
ollama pull llama3.1:8b

# 3. Restart Ollama service
```

---

## Groq Fallback — Reasoning Effort & Function Calling Issues (Session 2026-07-25)

**Problem:** When OpenRouter fails and fallback to Groq triggers, Hermes sends `reasoning_effort` parameter and expects function calling, but Groq models don't support these.

**Errors observed:**
1. `HTTP 400: \`reasoning_effort\` is not supported with this model` (llama-3.3-70b-versatile)
2. `property 'think' is unsupported` (openai/gpt-oss-20b)
3. Function calling validation failures: `attempted to call tool 'clarify...' which was not in request.tools`

**Root Cause:** Hermes global config has `reasoning_effort: medium` and toolsets that enable function calling. Groq's OpenAI-compatible endpoint doesn't support these parameters.

**Workarounds applied:**
```bash
# Disable reasoning globally
/opt/hermes/.venv/bin/hermes config set model.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set agent.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set delegation.reasoning_effort none
```

**Better approach:** Use a Groq model that supports function calling natively, or accept that fallback will be text-only (no tools). For production fallback, consider:
- Using `llama-3.1-70b-versatile` (deprecated) → `llama-3.3-70b-versatile` works but no function calling
- Or configure fallback to use a provider that matches primary's capabilities

**Lesson:** When configuring `fallback_model`, ensure the fallback provider supports the same features (reasoning_effort, function calling, toolsets) as the primary, or disable those features globally.

---

## TTS Cron Job Troubleshooting (Session 2026-07-05)

### Root causes
- `references/mcp-stdio-install.md` — MCP stdio server installation patterns
- `references/cron-job-patterns.md` — Cron job failure patterns, provider setup, skill context management
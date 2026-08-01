# Hermes Agent on Umbrel — Detailed Configuration & Operations Reference

## Key Paths

| Purpose | Path |
|---------|------|
| Persistent Hermes home (config, sessions, skills, logs) | `/opt/data` |
| Hermes CLI binary (venv) | `/opt/hermes/.venv/bin/hermes` |
| Hermes CLI symlink | `/opt/hermes/bin/hermes` |
| Config file | `/opt/data/config.yaml` |
| Secrets / API keys | `/opt/data/.env` (managed via `hermes auth` / `hermes config`) |
| Gateway logs | `/opt/data/logs/gateway.log` |
| Skills directory | `/opt/data/skills/` |

## Safe Configuration Pattern

**Never edit `/opt/data/config.yaml` directly** — Hermes blocks agent writes to security-sensitive config. Use the CLI:

```bash
# Use the venv hermes binary (not host PATH)
/opt/hermes/.venv/bin/hermes config set <key> <value>

# Examples from this session:
/opt/hermes/.venv/bin/hermes config set toolsets '[\"hermes-cli\", \"web\"]'
/opt/hermes/.venv/bin/hermes config set web.backend tavily
/opt/hermes/.venv/bin/hermes config set mcp_servers.tavily.url 'https://mcp.tavily.com/mcp/'
/opt/hermes/.venv/bin/hermes config set mcp_servers.tavily.auth oauth

# View current config
/opt/hermes/.venv/bin/hermes config show
```

## Gateway Restart (Required After Toolset/Backend Changes)

The gateway runs under **s6 supervision**. Config changes to toolsets, web backend, MCP servers, etc. require a gateway restart:

```bash
# Restart gateway service only (fast, preserves other services)
s6-svc -r /run/s6/services/hermes-gateway

# Or restart entire app via Umbrel UI:
# Settings → Apps → Hermes Agent → Restart
# (or right-click/long-press app icon on homescreen)
```

## Common Workflows

### Switching Web Backend to Tavily
```bash
/opt/hermes/.venv/bin/hermes config set toolsets '[\"hermes-cli\", \"web\"]'
/opt/hermes/.venv/bin/hermes config set web.backend tavily
# Ensure TAVILY_API_KEY is in /opt/data/.env (via `hermes auth add tavily` or manual)
s6-svc -r /run/s6/services/hermes-gateway
```

### Adding MCP Server (e.g., Tavily for /research + /map)
```bash
/opt/hermes/.venv/bin/hermes config set mcp_servers.tavily.url 'https://mcp.tavily.com/mcp/'
/opt/hermes/.venv/bin/hermes config set mcp_servers.tavily.auth oauth
s6-svc -r /run/s6/services/hermes-gateway
```

### Verifying Config Took Effect
```bash
/opt/hermes/.venv/bin/hermes config show | grep -A2 -E 'toolsets|web:|mcp_servers'
```

## Pitfalls & Gotchas

| Issue | Resolution |
|-------|------------|
| `hermes: command not found` | Use full path: `/opt/hermes/.venv/bin/hermes` |
| Config changes not taking effect | Gateway restart required via s6 (see above) |
| Editing config.yaml directly fails | Use `hermes config set` — direct writes are blocked |
| `.env` cannot be read directly | Use `hermes config show` to verify keys are loaded (shows masked values) |
| `host.docker.internal` unreliable | Use Docker service names for other Umbrel apps; `localhost` is container-local only |
| Windows host Ollama from Umbrel container | See **Connecting to Windows Host Ollama** section below |

---

## Gateway Crash Diagnosis & Recovery (Session 2026-06-23)

### Symptom: `gateway exited — recovering your session` / websocket closed (1011)

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

---

## Tavily MCP Endpoints (research + map) — Verified Working

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

# Enable all tools (or select subset via interactive configure)
/opt/hermes/.venv/bin/hermes mcp configure tavily
# → select 'all' or specific tools

# Restart gateway to pick up MCP tools
s6-svc -r /run/s6/services/hermes-gateway
```

**Test in session**:
```bash
/opt/hermes/.venv/bin/hermes chat -q "Use tavily_research to find latest accessibility guidelines for Brazilian journalism"
```

## Local MCP Server Installation (Filesystem, Memory, etc.)

**Key finding**: Remote `npx` installs (`npx -y @modelcontextprotocol/server-<name>`) often fail in the Umbrel container due to stdio transport issues. **Local installation via npm in `/opt/data/node_modules` works reliably.**

### Pattern for Local MCP Server Install

```bash
# 1. Install package locally in persistent home
cd /opt/data && npm install @modelcontextprotocol/server-filesystem @modelcontextprotocol/server-memory

# 2. Verify local binary exists
ls /opt/data/node_modules/.bin/
# → mcp-server-filesystem, mcp-server-memory, etc.

# 3. Add MCP server using local binary (stdio transport)
/opt/hermes/.venv/bin/hermes mcp add filesystem --command /opt/data/node_modules/.bin/mcp-server-filesystem --args /opt/data
/opt/hermes/.venv/bin/hermes mcp add memory --command /opt/data/node_modules/.bin/mcp-server-memory --args='["--memory-file", "/opt/data/mcp/memory.json"]'

# 4. Enable all tools (interactive prompt)
# → press 'y' to enable all

# 5. Verify connection
/opt/hermes/.venv/bin/hermes mcp test filesystem
/opt/hermes/.venv/bin/hermes mcp test memory

# 6. Restart gateway to pick up tools
s6-svc -r /run/s6/services/hermes-gateway
```

### Verified Local MCP Servers (Session 2026-06-23)

| Server | Binary | Tools | Persistence |
|--------|--------|-------|-------------|
| `filesystem` | `/opt/data/node_modules/.bin/mcp-server-filesystem` | 14 (read_file, write_file, edit_file, list_directory, search_files, create_directory, move_file, get_file_info, list_allowed_directories, ...) | Root: `/opt/data` |
| `memory` | `/opt/data/node_modules/.bin/mcp-server-memory` | 9 (create_entities, create_relations, read_graph, search_nodes, open_nodes, add_observations, delete_entities, delete_relations, delete_observations) | File: `/opt/data/mcp/memory.json` |

### Why Local Install Works

- Container has Node.js (`v22.22.3`) and `npm` available
- `/opt/data` is persistent across app updates
- Local binary avoids stdio handshake failures with remote `npx`
- Tools discovered immediately on `hermes mcp test`

---

## Connecting to Windows Host Ollama from Umbrel Container

**Scenario**: Hermes runs in Umbrel container (inside Docker Desktop VM on Windows). Ollama runs on Windows host. You want Hermes to use Ollama models.

### The Networking Problem

```
Windows Host (Ollama on 127.0.0.1:11434)
    ↓ Docker Desktop VM (host.docker.internal → VM IP)
    ↓ Umbrel VM
    ↓ Hermes Container
```

- `host.docker.internal` resolves to Docker Desktop VM IP (e.g., `fdc4:f303:9324::254`), **not** Windows host
- Ollama by default binds only to `127.0.0.1` on Windows
- Firewall blocks inbound connections to Windows host IP

### Solution Steps

#### 1. Find Windows Host IP (from Windows PowerShell)

```powershell
ipconfig
```
Look for the adapter **"vEthernet (WSL)"** or **"Docker Desktop"** — note its IPv4 address (e.g., `192.168.56.1`, `172.18.0.1`, `10.x.x.x`).

#### 2. Configure Ollama to Listen on All Interfaces (Windows PowerShell Admin)

```powershell
# Temporary (current session)
$env:OLLAMA_HOST = "0.0.0.0:11434"

# Permanent (survives reboot)
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "Machine")
```

#### 3. Open Windows Firewall for Ollama Port

```powershell
New-NetFirewallRule -DisplayName "Ollama" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow
```

#### 4. Restart Ollama (close/reopen terminal or reboot Windows)

#### 5. Verify from Windows Host

```powershell
curl http://<WINDOWS_IP>:11434/api/tags
# Should return your models: deepseek-rl, gemma, gemma4, llama3, nomic-embed-text, phi3, etc.
```

#### 6. Configure Hermes Provider (in Hermes container)

```bash
/opt/hermes/.venv/bin/hermes config set providers.ollama.base_url http://<WINDOWS_IP>:11434/v1
/opt/hermes/.venv/bin/hermes config set providers.ollama.api_key ollama
```

#### 7. Test from Hermes

```bash
# Use model name as shown in Ollama (e.g., 'llama3' not 'llama3.1:8b')
/opt/hermes/.venv/bin/hermes chat -q "Olá" --provider ollama --model llama3
```

### Quick Connectivity Test from Hermes Container

```bash
timeout 10 curl -s http://<WINDOWS_IP>:11434/api/tags
# Should return JSON with models array
```

### Common Issues

| Issue | Fix |
|-------|-----|
| `curl` timeout from container | Windows firewall not allowing port 11434, or Ollama not bound to 0.0.0.0 |
| `model 'llama3.1:8b' not found` | Use exact model name from `ollama list` (e.g., `llama3`, `gemma`, `phi3`) |
| `host.docker.internal` returns IPv6 | Use Windows host LAN IP instead |
| Models not showing after pull | Restart Ollama after setting `OLLAMA_HOST` |

### Alternative: Use Different Ollama Port

If port 11434 conflicts, run Ollama on different port:

```powershell
$env:OLLAMA_HOST = "0.0.0.0:11435"
# Update Hermes config accordingly:
# http://<WINDOWS_IP>:11435/v1
```
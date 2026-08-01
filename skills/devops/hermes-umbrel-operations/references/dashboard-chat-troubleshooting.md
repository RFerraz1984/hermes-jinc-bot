# Dashboard Web Chat "Unavailable" / Black Screen

Session reference: 2026-07-05. Issue reported via Telegram screenshot showing black screen with `Chat unavailable: 1` in Hermes web dashboard.

---

## Observed logs & error signatures

### 1. Container log (umbrel_hermes-agent compose log)
Tail of the log showed repeated:

```
hermes-agent_web_1 | WARNING tools.mcp_tool: MCP server ... initial connection failed ...
hermes-agent_web_1 | env: 'node': No such file or directory
hermes-agent_web_1 | node not found — install Node.js to use the TUI.
```

This indicates the TUI Gateway backend (used by the web chat) could not find a `node` executable.

### 2. gui.log (dashboard/TUI gateway log)
Repeated warning on every WebSocket connect:

```
WARNING tui_gateway.server: config.yaml has empty section(s): `context_file_max_chars`, `max_concurrent_sessions`. Remove the line(s) or set them to `{}` — empty sections silently drop nested settings.
```

After this warning, WebSocket connections closed with `reaped_sessions=1`, meaning the server accepted the client but then immediately discarded the session because config parsing failed.

### 3. tui_gateway_crash.log
Historical pattern (not necessarily the direct cause today):
```
[tui-parent] graceful-exit received signal=SIGHUP → killing gateway
[tui-parent] unhandledRejection: Error: EIO: i/o error, write
```
These are terminal I/O errors from past shutdown cycles and are usually harmless.

---

## Diagnosis procedure

```bash
# Verify node is present inside the container
which node
node --version

# Check dashboard/TUI logs for config warnings
tail -n 30 /opt/data/logs/gui.log

# Check gateway state (shutdown vs running)
tail -n 20 /opt/data/logs/gateway.log
```

---

## Fixes applied

### Fix 1: Null-valued config keys (2026-07-05)
```bash
/opt/hermes/.venv/bin/hermes config set max_concurrent_sessions 5
/opt/hermes/.venv/bin/hermes config set context_file_max_chars 100000
/command/s6-svc -r /run/service/dashboard
/command/s6-svc -r /run/service/gateway-default
```

### Fix 2: PATH corruption from literal `$PATH` in `.env` (2026-07-05 — this session)

**Root cause**: The `/opt/data/.env` file contained:
```bash
PATH=/opt/data/.npm-global/bin:$PATH
```

When `dotenv` loads this, the `$PATH` is stored **literally** (not expanded). Then `_ensure_tui_node()` in `hermes_cli/main.py` runs on import:
```python
parts = os.environ.get("PATH", "").split(os.pathsep)
# ... adds extra paths ...
os.environ["PATH"] = os.pathsep.join(parts)  # preserves literal "$PATH"
```

This corrupts the PATH, breaking `shutil.which("node")` in `_make_tui_argv()`, which calls `sys.exit(1)` with message `"node not found — install Node.js to use the TUI."`

**Symptoms**: Dashboard chat shows black screen with `Chat unavailable: 1`. Browser WebSocket receives `SystemExit(1)`.

**Diagnosis**:
```bash
# Check for literal $PATH in environment
/opt/hermes/.venv/bin/python3 -c "import shutil, os; print('node:', shutil.which('node')); print('PATH:', os.environ.get('PATH', '')[:200])"
# If PATH contains '/opt/data/.npm-global/bin:$PATH' literally, the env var was overwritten by a shell-style string.
```

**Fix**:
```bash
# 1. Remove the problematic PATH line from .env
sed -i '/^PATH=/d' /opt/data/.env

# 2. Add correct config to bypass Umbrel wrapper
echo "HERMES_TUI_DIR=/opt/hermes/ui-tui" >> /opt/data/.env
echo "HERMES_NODE=/usr/local/bin/node" >> /opt/data/.env

# 3. FULL app restart required (not just s6 service restart)
# Umbrel UI → Apps → Hermes Agent → Restart
# (s6-supervise will pick up the new HERMES_TUI_DIR on container boot)
```

---

## S6 service paths in this container

| Service | s6 servicedir |
|---------|---------------|
| Dashboard (hermes dashboard) | `/run/service/dashboard` |
| Gateway (hermes gateway run) | `/run/service/gateway-default` |

The `s6-svc` binary is at `/command/s6-svc`.

---

## Cross-symptom: MCP servers failing

In the same logs, many MCP stdio servers (`filesystem`, `memory`, `sequentialthinking`, `fetch`, `git`, `time`) fail with `Connection closed` / `Connection lost`. This is a **separate issue** and does not cause the black chat screen. Those are optional MCP integrations that error out when Node MCP packages are missing or OAuthed (tavily). Do not confuse the two.

---

## PATH corruption deep-dive

The corruption chain:

1. `.env` contains `PATH=/opt/data/.npm-global/bin:$PATH` (literal `$PATH`)
2. `load_dotenv()` loads this into `os.environ["PATH"]` as literal string
3. On `import hermes_cli.main`, `_ensure_tui_node()` runs:
   ```python
   parts = os.environ.get("PATH", "").split(os.pathsep)
   # parts = ['/opt/data/.npm-global/bin', '$PATH', ...]
   extras = [Path(hermes_home) / "node" / "bin", Path.home() / ".local" / "bin"]
   for extra in extras:
       if str(extra) not in parts:
           parts.insert(0, str(extra))
   os.environ["PATH"] = os.pathsep.join(parts)
   ```
4. Result: `PATH` now contains literal `$PATH` which doesn't exist on filesystem
5. `_make_tui_argv()` calls `_node_bin("node")` → `shutil.which("node")` → searches `$PATH` literally → fails → `sys.exit(1)`
6. WebSocket handler catches `SystemExit(1)` → sends `Chat unavailable: 1` → closes with code 1011

---

## Prevention

1. **Never put unexpanded shell variables in `.env`** — dotenv does not expand them
2. **Use `HERMES_NODE` env var** to explicitly point to node binary (bypasses PATH lookup)
3. **Use `HERMES_TUI_DIR=/opt/hermes/ui-tui`** to bypass the Umbrel wrapper (`/app/umbrel-tui/dist/entry.js`) which runs a provider probe that imports `hermes_cli.main` and corrupts PATH
4. **If PATH must be extended**, do it in the service run script or container entrypoint where shell expansion works

---

## Template files

- `templates/migrate-umbrel-to-ubuntu.sh` — Automated migration script including PATH cleanup
- `templates/ubuntu-systemd-native.md` — Native Ubuntu install with systemd (no Docker)
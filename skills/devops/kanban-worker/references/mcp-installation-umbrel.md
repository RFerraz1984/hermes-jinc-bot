# MCP Server Installation on Hermes (Umbrel)

Reference for kanban tasks that install MCP servers on Hermes running as an Umbrel app.

## Pattern

```bash
# Add each server via Hermes MCP CLI (saves to internal config)
hermes mcp add <name> --command npx --args '["-y", "<package>", <args...>]'
```

## Servers Installed (June 2025)

| Server | Package | Args | Persistent Path | API Key |
|--------|---------|------|-----------------|---------|
| filesystem | @modelcontextprotocol/server-filesystem | /opt/data | — | — |
| git | @modelcontextprotocol/server-git | --repository /opt/data | — | — |
| fetch | @modelcontextprotocol/server-fetch | — | — | — |
| sequentialthinking | @modelcontextprotocol/server-sequentialthinking | — | — | — |
| memory | @modelcontextprotocol/server-memory | --memory-file /opt/data/mcp/memory.json | /opt/data/mcp/memory.json | — |
| time | @modelcontextprotocol/server-time | — | — | — |
| brave-search | @brave/brave-search-mcp-server | — | — | BRAVE_API_KEY (via `hermes auth add brave-search`) |

## Key Points

- **All servers show "disabled"** in `hermes mcp list` — this is EXPECTED for stdio servers. They start on-demand when tools are invoked.
- **Config lives in Hermes internal registry**, not in `/opt/data/mcp/settings.json` (that file was created for documentation only).
- **Memory file auto-created** on first use at `/opt/data/mcp/memory.json`.
- **Brave Search requires API key** — get from https://brave.com/search/api/ then `hermes auth add brave-search`.
- **Provider must work** — if `openai-codex` is rate-limited (HTTP 429), switch to OpenRouter first:
  ```bash
  hermes config set model openrouter/auto
  hermes config set fallback_providers '["openrouter"]'
  ```

## Verification

```bash
hermes mcp list
# Should show all 7 servers with "✗ disabled" status (expected)
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Connection closed" during `hermes mcp add` | Press `y` to save config anyway — stdio servers connect on-demand |
| Tools not available in chat | Restart gateway: `hermes gateway restart` or restart Umbrel app |
| Brave Search fails | Add API key: `hermes auth add brave-search` |
| Memory not persisting | Verify `/opt/data/mcp/memory.json` exists and is writable |
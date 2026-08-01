# MCP Stdio Server Installation on Umbrel (Containerized Environments)

## Problem

MCP servers that run via `npx` (e.g., `@modelcontextprotocol/server-filesystem`, `@modelcontextprotocol/server-time`, `@modelcontextprotocol/server-memory`, `@modelcontextprotocol/server-sequentialthinking`) often fail with **"Connection closed"** in the Hermes container. The stdio transport cannot properly hand off to the npx-spawned process.

**Observed error**:
```
Testing 'filesystem'...
  Transport: stdio → npx
  Auth: none
  ✗ Connection failed (10275ms): Connection closed
```

## Root Cause

Container isolation / stdio handling differences between npx's child process spawning and Hermes's MCP client. The npx wrapper adds an extra process layer that breaks stdio handoff in this environment.

## Solution: Local npm Install + Direct Binary Reference

Install the MCP server package locally via npm under `/opt/data` (persistent), then reference the local binary directly in the MCP server configuration.

```bash
# 1. Install package locally (persists across app updates)
cd /opt/data
npm install @modelcontextprotocol/server-filesystem  # or server-time, server-memory, etc.

# 2. Find the installed binary
ls /opt/data/node_modules/.bin/
# e.g., mcp-server-filesystem

# 3. Add MCP server pointing to LOCAL binary (not npx)
/opt/hermes/.venv/bin/hermes mcp add filesystem \
  --command /opt/data/node_modules/.bin/mcp-server-filesystem \
  --args /opt/data

# 4. Enable tools and restart gateway
/opt/hermes/.venv/bin/hermes mcp configure filesystem  # select 'all' or specific tools
s6-svc -r /run/s6/services/hermes-gateway
```

## Verified Working Servers with This Pattern

| Package | Local Binary | Tools Provided |
|---------|--------------|----------------|
| `@modelcontextprotocol/server-filesystem` | `mcp-server-filesystem` | 14 tools (read, write, edit, list, search, tree, move, create_dir, get_info, list_allowed) |
| `@modelcontextprotocol/server-time` | `mcp-server-time` | Time/date utilities |
| `@modelcontextprotocol/server-memory` | `mcp-server-memory` | Persistent memory/key-value |
| `@modelcontextprotocol/server-sequentialthinking` | `mcp-server-sequentialthinking` | Structured reasoning |

## Notes

- **HTTP-based MCP servers** (like Tavily at `https://mcp.tavily.com/mcp/`) work natively and don't need this workaround.
- **Persistence**: Packages installed under `/opt/data/node_modules/` survive Umbrel app updates.
- **Binary path**: Always use the absolute path `/opt/data/node_modules/.bin/<binary-name>` in the MCP server config.
- **Args**: Pass allowed directories as args (e.g., `/opt/data` for filesystem server).
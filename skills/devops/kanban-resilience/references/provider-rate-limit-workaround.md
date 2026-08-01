# Provider Rate Limit Workaround — Case Study

**Task:** t_49cb899b — Research and list available MCP tools/servers
**Date:** June 22, 2026
**Provider:** openai-codex (gpt-5.5)
**Error:** HTTP 429 — "The usage limit has been reached" (free tier)
**Reset:** ~2026-07-21 (unix 1784752679)

## Failure Sequence

1. Worker spawned with `kanban-worker` skill
2. Attempted research via LLM-driven searches (3 web_search calls)
3. Attempted GitHub fetches (3 fetch calls, 83s → 151s → 353s)
4. Hit rate limit on 4th API call — 3 retries with backoff (2.3s, 4.5s, 5.3s) all failed
5. Task marked `blocked` with `consecutive_failures: 2`

## Recovery Approach

**Switched to provider-agnostic tools:**
- `web_search` — uses configured search backend (Brave/DDGS/Exa), not Codex
- `web_extract` — fetches and converts pages to markdown, no LLM needed
- `write_file` — local artifact creation
- `execute_code` + SQLite — direct database completion

**Search queries used:**
```
"Model Context Protocol official servers filesystem postgres google maps slack GitHub repository"
"site:github.com/modelcontextprotocol servers MCP filesystem postgres slack google maps"
"high utility MCP servers GitHub repository filesystem postgres slack github google maps brave search puppeteer sqlite"
"brave-search-mcp-server official github"
"zencoderai slack-mcp-server github"
```

**Extraction targets:**
- https://modelcontextprotocol.io/examples
- https://github.com/modelcontextprotocol/servers/issues/4353 (verification audit)
- https://github.com/brave/brave-search-mcp-server
- https://github.com/zencoderai/slack-mcp-server

## Result

Completed research in ~5 tool calls (vs 10+ failed LLM calls). Produced comprehensive report with:
- 7 actively maintained official servers
- 13 archived servers with vendor/community alternatives
- 6 community discovery resources
- Recommendations for Hermes/Umbrel integration

**Artifact:** `/opt/data/kanban/workspaces/t_49cb899b/mcp_servers_report.md`

## Key Insight

`web_search`/`web_extract` are **provider-independent** — they use the search/extract toolset configured in Hermes (web toolset), not the active LLM provider. This makes them reliable fallbacks when the LLM provider is rate-limited or unavailable.
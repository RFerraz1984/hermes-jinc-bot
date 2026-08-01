# MCP Server Research Methodology — Case Study

**Task:** t_49cb899b — Research and list available Model Context Protocol (MCP) tools/servers
**Completed:** June 22, 2026 via kanban-resilience fallback

## Source Hierarchy (Most → Least Authoritative)

| Tier | Source | Access Method | Reliability |
|------|--------|---------------|-------------|
| 1 | Official MCP docs | `web_extract(https://modelcontextprotocol.io/examples)` | Canonical |
| 2 | Official GitHub issues | `web_extract(https://github.com/modelcontextprotocol/servers/issues/4353)` | Verified audit |
| 3 | Vendor-maintained repos | `web_search` + `web_extract` (brave/brave-search-mcp-server, zencoderai/slack-mcp-server) | Active maintenance |
| 4 | Community aggregations | `web_search` (awesome-mcp-servers-2, punkpeye, mcpservers.org, Glama, PulseMCP) | Discovery only |

## Search Strategy

### Phase 1: Official Reference Servers
```bash
# Primary source
web_extract("https://modelcontextprotocol.io/examples")

# Verification audit (shows active vs archived)
web_extract("https://github.com/modelcontextprotocol/servers/issues/4353")
```

### Phase 2: Vendor Alternatives for Archived Servers
```bash
# For each archived server with known vendor takeover:
web_search("brave-search-mcp-server official github")
web_search("zencoderai slack-mcp-server github")
web_search("postgresql mcp server community fork")
```

### Phase 3: Community Discovery Resources
```bash
web_search("awesome-mcp-servers github")
web_search("mcpservers.org")
web_search("glama.ai mcp servers")
web_search("pulsemcp.com servers")
```

## Output Structure

| Section | Content | Source Tier |
|---------|---------|-------------|
| Active Official | 7 servers with descriptions + repo paths | Tier 1-2 |
| Archived Official | 13 servers with status + alternatives | Tier 2 |
| Vendor Alternatives | 2+ vendor-maintained replacements | Tier 3 |
| Discovery Resources | 6 community aggregations | Tier 4 |
| Summary Stats | Counts, percentages, transitions | Computed |
| Recommendations | Context-specific guidance | Synthesized |

## Key Findings Template

```
Actively maintained (official): X servers (Y%)
Archived (official): Z servers
Total official reference: N
Key transitions: [Archived → Vendor] mappings
Discovery resources: M curated lists
```

## Hermes/Umbrel Integration Notes

- **Filesystem** server: Native local file access — ideal for Umbrel persistent storage
- **Git** server: Repository operations — useful for git-based workflows
- **Brave Search** (vendor): Web search capability — requires BRAVE_API_KEY
- **Slack** (Zencoder): Team messaging — requires Slack app + tokens
- **Memory** server: Knowledge graph — potential for persistent agent memory

## Time Investment

- Official sources: ~3 min (2 extracts)
- Vendor alternatives: ~2 min (2 searches + 2 extracts)
- Community resources: ~1 min (1 search)
- Synthesis + write: ~2 min
- **Total: ~8 minutes** vs 30+ minutes for failed LLM-driven approach
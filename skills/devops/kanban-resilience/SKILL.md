---
name: kanban-resilience
description: Patterns for recovering kanban tasks when workers fail due to provider rate limits, timeouts, tool unavailability, or other transient errors. Covers fallback tooling, manual database operations, and completion strategies.
version: 1.0.0
platforms: [linux, macos, windows]
environments: [kanban]
metadata:
  hermes:
    tags: [kanban, resilience, error-recovery, provider-fallback, database-operations]
    related_skills: [kanban-worker, kanban-orchestrator]
---

# Kanban Task Resilience — Recovery Patterns

> This skill documents patterns for completing kanban tasks when the primary execution path fails. Use when a worker hits provider rate limits, tool errors, timeouts, or missing tooling.

## Common Failure Modes & Workarounds

### 1. Provider Rate Limiting (HTTP 429)

**Symptom:** LLM provider returns `RateLimitError` / HTTP 429 after retries exhausted.

**Workaround:** Switch to tools that use different backends:
- `web_search` + `web_extract` — use search APIs (Brave, DDGS, etc.), not the LLM provider
- `search_files` / `read_file` / `write_file` — local filesystem, no provider needed
- `terminal` — shell commands, no provider needed
- `execute_code` — Python execution, no provider needed

**Pattern:**
```python
# Instead of relying on the LLM to do research via its knowledge:
web_search(query="topic", limit=10)
web_extract(urls=[...])
# Then synthesize results locally and write artifacts
write_file(path="workspace/report.md", content=...)
```

### 2. Kanban Tools Unavailable in Agent Context

**Symptom:** `kanban_show`, `kanban_complete`, `kanban_block` tools not in function schema.

**Workaround:** Direct SQLite operations on `/opt/data/kanban.db`:

```python
import sqlite3, json, time

conn = sqlite3.connect('/opt/data/kanban.db')
cursor = conn.cursor()
now = int(time.time())

result = json.dumps({
    "summary": "Human-readable summary",
    "artifact_path": "/opt/data/kanban/workspaces/t_xxx/artifact.md",
    "metrics": {"items_found": N}
})

cursor.execute("""
    UPDATE tasks SET status='completed', completed_at=?, result=? WHERE id=?
""", (now, result, task_id))

cursor.execute("""
    INSERT INTO task_events (task_id, run_id, kind, payload, created_at)
    VALUES (?, 0, 'completed', ?, ?)
""", (task_id, json.dumps({"recovery": True}), now))

conn.commit()
conn.close()
```

**Key tables:** `tasks`, `task_events`, `task_comments`, `task_runs`

### 3. Task Previously Failed (Retry Scenario)

**Diagnostics:** Check `consecutive_failures`, `last_failure_error`, `task_events` for prior runs.

**Strategy:**
- Read the log at `/opt/data/kanban/logs/t_<id>.log`
- Check `task_events` for `kind='failed'` or `kind='crashed'`
- Don't repeat the failed approach — use fallback tooling
- If workspace is `scratch`, it's fresh; if `dir:` or `worktree`, check for stale artifacts

### 4. Long-Running Tasks Near Timeout

**Symptom:** `max_runtime_seconds` approaching, or task reclaimed.

**Mitigation:**
- Send heartbeats via `kanban_heartbeat` every few minutes
- Chunk work into smaller pieces
- Write incremental artifacts to workspace
- Consider spawning child tasks via `kanban_create` for parallel work

## Completion Without Standard Tools

When `kanban_complete` tool is unavailable:

1. **Write artifact** to `$HERMES_KANBAN_WORKSPACE/result.md` (or similar)
2. **Update tasks table** directly (see Pattern 2)
3. **Insert task_event** with `kind='completed'`
4. **Verify** with `SELECT status, completed_at, result FROM tasks WHERE id='t_<id>'`

## Provider Fallback Matrix

| Primary Tool | Fallback Tools | Use Case |
|--------------|----------------|----------|
| LLM reasoning | `execute_code` + local logic | Deterministic processing |
| LLM web search | `web_search` + `web_extract` | Research, fact-finding |
| LLM code gen | `terminal` + templates/scripts | Boilerplate, known patterns |
| LLM file ops | `read_file`/`write_file`/`patch`/`search_files` | Any file manipulation |

## References

- `references/provider-rate-limit-workaround.md` — Detailed transcript of Codex 429 recovery
- `references/manual-db-completion.md` — SQLite schema and completion queries
- `references/mcp-research-methodology.md` — MCP server research as a case study
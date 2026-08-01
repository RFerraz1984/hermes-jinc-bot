# Manual Kanban Database Completion — SQLite Reference

**Database:** `/opt/data/kanban.db`
**Primary Tables:** `tasks`, `task_events`, `task_comments`, `task_runs`, `task_links`, `task_attachments`

## Tasks Table Schema

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,              -- t_<hex>
    title TEXT NOT NULL,
    body TEXT,
    assignee TEXT,                    -- profile name
    status TEXT,                      -- ready, running, blocked, completed, archived
    priority INTEGER DEFAULT 0,
    created_by TEXT,
    created_at INTEGER,               -- unix timestamp
    started_at INTEGER,
    completed_at INTEGER,
    workspace_kind TEXT,              -- scratch, dir:<path>, worktree
    workspace_path TEXT,
    branch_name TEXT,
    claim_lock TEXT,
    claim_expires INTEGER,
    tenant TEXT,
    result TEXT,                      -- JSON result payload
    idempotency_key TEXT,
    consecutive_failures INTEGER DEFAULT 0,
    worker_pid INTEGER,
    last_failure_error TEXT,
    max_runtime_seconds INTEGER,
    last_heartbeat_at INTEGER,
    current_run_id INTEGER,
    workflow_template_id TEXT,
    current_step_key TEXT,
    skills TEXT,                      -- JSON array
    model_override TEXT,              -- JSON
    max_retries INTEGER,
    goal_mode INTEGER DEFAULT 0,
    goal_max_turns INTEGER,
    session_id TEXT
);
```

## Task Events Table Schema

```sql
CREATE TABLE task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    run_id INTEGER DEFAULT 0,
    kind TEXT NOT NULL,               -- created, started, heartbeat, blocked, unblocked, completed, failed, crashed, reclaimed
    payload TEXT,                     -- JSON
    created_at INTEGER NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

## Completion Query (Copy-Paste Ready)

```python
import sqlite3, json, time

TASK_ID = "t_49cb899b"  # <-- CHANGE THIS
ARTIFACT_PATH = "/opt/data/kanban/workspaces/t_49cb899b/mcp_servers_report.md"  # <-- CHANGE THIS
SUMMARY = "Completed research. Found 20 MCP servers (7 active, 13 archived)."  # <-- CHANGE THIS

conn = sqlite3.connect('/opt/data/kanban.db')
cursor = conn.cursor()
now = int(time.time())

result_json = json.dumps({
    "summary": SUMMARY,
    "artifact_path": ARTIFACT_PATH,
    "servers_found": 20,
    "active_servers": 7,
    "archived_servers": 13,
    "discovery_resources": 6
})

# Update task
cursor.execute("""
    UPDATE tasks
    SET status = 'completed',
        completed_at = ?,
        result = ?
    WHERE id = ?
""", (now, result_json, TASK_ID))

# Insert completion event
cursor.execute("""
    INSERT INTO task_events (task_id, run_id, kind, payload, created_at)
    VALUES (?, 0, 'completed', ?, ?)
""", (TASK_ID, json.dumps({"recovery": True, "method": "manual_db"}), now))

conn.commit()

# Verify
cursor.execute("SELECT id, status, completed_at, result FROM tasks WHERE id = ?", (TASK_ID,))
print("Verified:", cursor.fetchone())

conn.close()
```

## Status Values

| Status | Meaning |
|--------|---------|
| `ready` | Queued, not yet claimed |
| `running` | Worker actively executing |
| `blocked` | Waiting on human decision (see `task_comments`) |
| `completed` | Finished successfully |
| `archived` | Removed from active board |
| `failed` | Worker exited with error |

## Useful Diagnostic Queries

```sql
-- Task with recent events
SELECT t.id, t.title, t.status, t.consecutive_failures, t.last_failure_error,
       e.kind, e.payload, e.created_at
FROM tasks t
LEFT JOIN task_events e ON e.task_id = t.id
WHERE t.id = 't_49cb899b'
ORDER BY e.created_at DESC;

-- All blocked tasks needing attention
SELECT id, title, assignee, last_failure_error
FROM tasks
WHERE status = 'blocked';

-- Tasks with high failure count
SELECT id, title, consecutive_failures, last_failure_error
FROM tasks
WHERE consecutive_failures > 1;
```
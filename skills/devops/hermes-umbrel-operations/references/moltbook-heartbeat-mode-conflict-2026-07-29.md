# Moltbook Heartbeat Cron Job — Mode Conflict Fix (2026-07-29)

## Error
```
RuntimeError: HTTP 400: 'messages.2' : for 'role:assistant' the following must be satisfied[('messages.2' : property 'reasoning_details' is unsupported)]
```

Followed by:
```
RuntimeError: HTTP 400: tool call validation failed: attempted to call tool 'skill_view(name="moltbook")' which was not in request.tools
```

## Root Cause
Cron job `3d75d014af16` ("Moltbook Heartbeat - jornalista_inclusivo_bot") had conflicting configuration:

| Field | Value | Mode Implied |
|-------|-------|--------------|
| `skill` | `"moltbook"` | Agent mode |
| `skills` | `["moltbook"]` | Agent mode |
| `script` | `"moltbook_helpers.py heartbeat..."` | Script mode |
| `no_agent` | NOT SET | Agent mode default |

The scheduler tried to run it in agent mode (loading the `moltbook` skill) but the `script` field was also present. When the agent tried to call `skill_view(name="moltbook")` to load the skill, the tool wasn't available in the cron job's toolset, causing the second error.

## Fix Applied
1. **Removed** `skill` and `skills` fields from the job
2. **Set** `no_agent: true` explicitly
3. **Created** wrapper script `/opt/data/scripts/moltbook_heartbeat_wrapper.sh`:
   ```bash
   #!/bin/bash
   cd /opt/data
   python3 /opt/data/scripts/moltbook_helpers.py heartbeat 2>&1 | python3 /opt/data/scripts/smart_notify_filter.py --job-name "Moltbook Heartbeat" --exit-code ${PIPESTATUS[0]}
   ```
4. **Set** `workdir: "/opt/data"` on the job
5. **Copied** wrapper to `~/.hermes/scripts/moltbook_heartbeat_wrapper.sh` and `/opt/data/scripts/moltbook_heartbeat_wrapper.sh`

## Result
- Job now runs successfully in Pattern B (script mode)
- Last successful run: `2026-07-29T19:30:06.959196+00:00`, status `ok`
- Schedule: `0 */4 * * *` (every 4 hours)
- Smart notify filter suppresses "OK" heartbeats, only alerts on action needed

## Lesson
**Never mix `skill`/`skills` with `script`/`no_agent` in a single cron job.** The scheduler cannot resolve the conflict. Always choose one mode:
- **Pattern A (Agent)**: `skill`, `skills`, `prompt` — for LLM-driven tasks
- **Pattern B (Script)**: `script`, `no_agent: true`, `workdir` — for deterministic shell/Python tasks

Other Moltbook cron jobs (`Moltbook Monitor`, `Moltbook Verification Checker`) were already correctly configured as Pattern B.
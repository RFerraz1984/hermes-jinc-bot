# Kanban CLI in Umbrel/Container Environments

## Hermes Binary Location
```
/opt/hermes/bin/hermes      # Primary (symlink to hermes in .venv)
/opt/hermes/hermes          # Alternate
/opt/hermes/.venv/bin/hermes  # Virtualenv direct
```

## Common Commands (JSON output for parsing)

| Action | Command |
|--------|---------|
| Show task | `/opt/hermes/bin/hermes kanban show <task_id> --json` |
| Complete task | `/opt/hermes/bin/hermes kanban complete <task_id> --summary "..." --metadata '{...}'` |
| Block task | `/opt/hermes/bin/hermes kanban block <task_id> "reason"` |
| Create task | `/opt/hermes/bin/hermes kanban create "title" --assignee <profile> [--parent <id>]` |
| Add comment | `/opt/hermes/bin/hermes kanban comment <task_id> "body"` |

## Workspace Notes (Umbrel)
- Scratch workspaces: `/opt/data/kanban/workspaces/t_<id>/` — cleaned up on task completion
- Persistent workspaces (dir:): survive completion, check `$HERMES_KANBAN_WORKSPACE`
- Always `cd $HERMES_KANBAN_WORKSPACE` before file operations

## Protocol Violation Recovery
If previous runs show `protocol_violation` + `gave_up` (exit_code=0, no complete/block):
- The worker likely crashed or exited without calling completion
- Check `events` array in `kanban show` for `protocol_violation` payload
- This task is a retry — read prior runs' `error` and `summary` to avoid repeating failures
- Typical cause: worker used `kanban_*` tools that don't exist, silently failed, exited cleanly

## Environment Variables Available
- `HERMES_KANBAN_TASK` — current task ID
- `HERMES_KANBAN_WORKSPACE` — absolute path to workspace
- `HERMES_KANBAN_BRANCH` — git branch name (if worktree)
- `HERMES_TENANT` — tenant namespace (if set)
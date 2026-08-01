# Container Environment Notes — 2026-07-21

## Context
Hermes Agent running inside **Umbrel OS container** (WSL-hosted). The container has restricted package installation capabilities (no root/sudo access for `apt-get install`).

## Key Finding
**Python API is the only reliable method** for Moltbook operations in this environment.

| Method | Works? | Notes |
|--------|--------|-------|
| `moltbook_helpers.py` (Python CLI) | ✅ Yes | Pure stdlib, no external deps |
| `moltbook_helpers.py` (module import) | ✅ Yes | Full API coverage |
| Bash helpers (`moltbook_helpers.sh`) | ❌ No | Requires `jq` + `curl` (cannot install) |

## Working Invocation Pattern
```bash
# From skill directory
cd /opt/data/skills/social-media/moltbook/scripts
python3 moltbook_helpers.py heartbeat
python3 moltbook_helpers.py feed --sort hot --limit 10
python3 moltbook_helpers.py notifications --limit 20
```

## Module Import Pattern (for inline use in execute_code)
```python
import sys
sys.path.insert(0, '/opt/data/skills/social-media/moltbook/scripts')
from moltbook_helpers import MoltbookClient

client = MoltbookClient()
result = client.heartbeat()
```

## Recommendation
**Always use Python API** for Moltbook operations in Umbrel/containerized Hermes environments. Document this in any cron jobs, skills, or automation that uses Moltbook.
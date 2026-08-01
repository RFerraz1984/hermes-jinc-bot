# uv --target for Read-Only venvs

## Problem

In Umbrel containers, `/opt/hermes/.venv/lib/python3.13/site-packages/` is owned by **root** (dr-x). The `hermes` user (uid=1000) cannot write to it, so:

```bash
pip install edge-tts     # pip: command not found (no pip in PATH)
pip3 install edge-tts    # pip3: command not found
uv pip install edge-tts  # Permission denied
```

## Solution: `uv pip install --target`

```bash
mkdir -p /opt/data/.local/lib/python3.13/site-packages
uv pip install edge-tts --target /opt/data/.local/lib/python3.13/site-packages
```

This installs the package (and all transitive deps) to a persistent, writable location under `/opt/data/`.

## Runtime: PYTHONPATH Injection

The installed package is NOT on the venv's `sys.path` by default. Two options:

### Option A: s6 Container Environment (Preferred)

```bash
# Write to s6 container environment (survives container restart)
echo '/opt/data/.local/lib/python3.13/site-packages:/opt/data/.local/lib/python3.13/site-packages' > /run/s6/container_environment/PYTHONPATH
```

Then restart the affected services:
```bash
/command/s6-svc -r /run/service/dashboard
/command/s6-svc -r /run/service/gateway-default
```

### Option B: Inline PYTHONPATH (Temporary)

```bash
export PYTHONPATH="/opt/data/.local/lib/python3.13/site-packages${PYTHONPATH:+:$PYTHONPATH}"
```

## Verification

```bash
/opt/hermes/.venv/bin/python -c "import edge_tts; print(edge_tts.__version__)"
```

## Known Packages Installed This Way

| Package | Reason | Target |
|---------|--------|--------|
| `edge-tts` | TTS provider for voice output | `/opt/data/.local/lib/python3.13/site-packages` |

## Caveats

- `--target` installs packages in **flat** layout (no editable installs)
- Shared dependencies (e.g., `aiohttp`, `certifi`) may conflict with venv packages — venv takes precedence if listed in `sys.path` first
- For multi-package installs: `uv pip install pkg1 pkg2 --target ...` installs all at once
- The target dir is persistent across app updates (under `/opt/data/`)
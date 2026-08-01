# Image Generation with OpenAI (DALL-E) on Hermes Umbrel

## Overview

This reference documents the working pattern for configuring **OpenAI DALL-E** as the image generation backend on Hermes Agent running in Umbrel container.

## Problem Context

- Default FAL.ai backend requires `FAL_KEY` (not available)
- User has OpenAI API key (`sk-...`)
- Need to enable OpenAI image generation plugin and configure API key

## Solution Steps

### 1. Enable OpenAI Image Generation Plugin

```bash
/opt/hermes/.venv/bin/hermes plugins enable openai
```

**Result**: `✓ Plugin image_gen/openai enabled. Takes effect on next session.`

### 2. Configure OpenAI Provider in config.yaml

**Never hardcode the API key.** If the user already has `OPENAI_API_KEY` in `/opt/data/.env` (check with `grep OPENAI_API_KEY /opt/data/.env` — value is masked in output), reference it as a variable, not a literal:

```bash
# Set base URL
/opt/hermes/.venv/bin/hermes config set providers.openai.base_url https://api.openai.com/v1

# Reference the .env variable — do NOT paste the raw key into config.yaml
/opt/hermes/.venv/bin/hermes config set providers.openai.api_key '${OPENAI_API_KEY}'
```

### 3. Verify image_gen Toolset is Enabled

```bash
/opt/hermes/.venv/bin/hermes tools list | grep image_gen
# Should show: ✓ enabled  image_gen  🎨 Image Generation
```

The `image_gen` toolset was already enabled in `platform_toolsets.cli` and `platform_toolsets.telegram`.

### 4. Set the Active image_gen Provider (Critical — Easy to Miss)

Enabling the `image_gen/openai` plugin and configuring `providers.openai.*` is **NOT enough on its own**. The `image_generate` tool has an in-tree FAL fallback that keeps firing (`FAL_KEY não configurada...`) unless you explicitly tell it which registered plugin provider to route to:

```bash
/opt/hermes/.venv/bin/hermes config set image_gen.provider openai
```

Without this key, every `image_generate` call resolves to the FAL path regardless of which plugins are enabled, and fails with a "FAL_KEY not configured / no Nous credits" error — even though the OpenAI plugin is enabled and its provider is fully configured. This is the #1 symptom to check first when image generation "does nothing" after plugin setup.

### 5. Restart Gateway (Required for Telegram/gateway sessions)

```bash
s6-svc -r /run/s6/services/hermes-gateway
```

> Not needed to test from a fresh CLI invocation — `hermes chat -q "..."` starts a new process and reads the current config.yaml directly. Gateway restart is only required for the long-lived gateway process (Telegram, etc.) to pick up the change.

### 6. Test Image Generation

```bash
/opt/hermes/.venv/bin/hermes chat -q "Gere uma imagem de robô jornalista inclusivo, estilo ilustração amigável" --toolsets image_gen
```

Confirm success by checking the output file actually exists (don't just trust the agent's "imagem gerada com sucesso" claim):

```bash
ls -la /opt/data/cache/images/openai_*.png
```

## Verified Working Configuration (config.yaml snippet)

```yaml
providers:
  openai:
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}  # references .env, never a literal key
image_gen:
  provider: openai  # REQUIRED — without this, image_generate silently routes to FAL
...
platform_toolsets:
  cli:
    - image_gen
  telegram:
    - image_gen
plugins:
  enabled:
    - openai  # image_gen/openai plugin
```

## Pitfalls & Gotchas

| Issue | Resolution |
|-------|------------|
| Plugin `openai` not listed in `hermes plugins list` | Use `hermes plugins list | grep -i openai` to find the exact name (`openai` for image_gen, `openai-codex-provider` for Codex) |
| `FAL_KEY` error persists after enabling the openai plugin + setting provider creds | Set `image_gen.provider openai` explicitly — plugin enable + provider config alone does not switch the active backend away from the FAL fallback |
| `FAL_KEY` error persists after config | Gateway restart required (`s6-svc -r /run/s6/services/hermes-gateway`) — only matters for the long-lived gateway, not a fresh `hermes chat -q` |
| Image generation fails silently | Check gateway logs: `tail -f /opt/data/logs/gateway.log` |
| `hermes: command not found` | Always use full path: `/opt/hermes/.venv/bin/hermes` |
| Config writes as string not list | `hermes config set toolsets '[...]'` writes a string; prefer setting `enabled_toolsets` per cron job/session |
| User already has the provider's API key in `.env` | Reference it (`'${OPENAI_API_KEY}'`) via `hermes config set providers.<name>.api_key`, never paste the raw key into config.yaml or into chat |

## Notes

- DALL-E 3 is the default model for OpenAI image generation
- No additional model selection needed — the OpenAI image_gen plugin handles model selection
- The `image_gen` toolset uses the `image_generate` tool internally
- Works in both CLI sessions and Telegram gateway messages (if `platform_toolsets.telegram` includes `image_gen`)

## Related

- `references/hermes-on-umbrel.md` — General Umbrel operations
- `hermes-agent` skill — Core CLI reference
- `skill_view(name="hermes-agent", file_path="references/native-mcp.md")` — For MCP server integration patterns
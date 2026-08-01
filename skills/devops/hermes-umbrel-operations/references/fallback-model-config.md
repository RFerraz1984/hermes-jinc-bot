# Fallback Model Configuration — OpenRouter → Groq/Ollama

## Scenario
Primary model: `nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter
Fallback: Groq (`llama-3.3-70b-versatile`) or Ollama local

## Configuration in `/opt/data/config.yaml`

```yaml
model:
  default: nvidia/nemotron-3-ultra-550b-a55b:free
  provider: openrouter
  base_url: ''
  reasoning_effort: none  # Critical for Groq fallback

providers:
  ollama:
    base_url: http://host.docker.internal:11434/v1
    api_key: ollama
  groq:
    base_url: https://api.groq.com/openai/v1
    api_key: ${GROQ_API_KEY}

fallback_model:
  provider: groq
  model: llama-3.3-70b-versatile
  base_url: https://api.groq.com/openai/v1
  api_key: ${GROQ_API_KEY}
```

## Key Settings for Groq Compatibility

| Setting | Value | Why |
|---------|-------|-----|
| `model.reasoning_effort` | `none` | Groq rejects `reasoning_effort` parameter |
| `agent.reasoning_effort` | `none` | Same |
| `delegation.reasoning_effort` | `none` | Same |

Set via:
```bash
/opt/hermes/.venv/bin/hermes config set model.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set agent.reasoning_effort none
/opt/hermes/.venv/bin/hermes config set delegation.reasoning_effort none
```

## Trigger Conditions
Fallback activates on:
- HTTP 429 (rate limit)
- HTTP 503 (service unavailable)
- HTTP 529 (overloaded)
- Connection failures

## Testing Fallback
```bash
# Temporarily invalidate OpenRouter key
OPENROUTER_API_KEY="invalid" /opt/hermes/.venv/bin/hermes chat -q "Test fallback"
```

## Known Limitations with Groq Fallback
- No function calling support (tool calls fail validation)
- No `reasoning_effort` parameter
- No `think` / structured reasoning
- Text-only responses

For full feature parity, consider Ollama with a 128K context model (e.g., `llama3.1:8b`) on the host.
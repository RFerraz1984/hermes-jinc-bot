# Groq as Custom Provider in Hermes

Groq is **not a built-in provider** in Hermes. It must be configured via `custom_providers` in `config.yaml`.

## Configuration

### config.yaml
```yaml
custom_providers:
  - name: groq
    base_url: https://api.groq.com/openai/v1
    key_env: GROQ_API_KEY
```

### .env
```bash
GROQ_API_KEY=your-groq-api-key
```

### Model Selection
```bash
# Via CLI
hermes chat -q "..." --provider custom:groq --model llama-3.3-70b-versatile

# Or in session
/model custom:groq:llama-3.3-70b-versatile
```

## Available Models (as of 2026)
- `llama-3.3-70b-versatile` — Best general purpose
- `llama-3.1-70b-versatile` — Previous generation
- `qwen/qwen3-32b` — Better function calling support
- `gemma2-9b-it` — Smaller, faster

Check current catalog: https://console.groq.com/docs/models

## Function Calling Limitation

⚠️ **Most Groq models have limited/broken function calling**. They may:
- Hallucinate tool calls
- Call tools not in the schema
- Fail tool call validation

**Workarounds:**
1. Use `qwen/qwen3-32b` for better tool calling
2. Disable tools for Groq sessions (`--toolsets=""` or `/tools` to disable)
3. Use Groq via OpenRouter (`provider: openrouter`, model: `groq/llama-3.3-70b-versatile`) for more stable tool calling
4. Use Together AI or other providers for tool-heavy workloads

## Why Not Built-in?

Hermes built-in providers require:
- Standardized `/v1/models` endpoint for auto-discovery
- Stable model catalog
- Provider-specific auth handling

Groq lacks a standard `/v1/models` endpoint, so it's configured as a custom OpenAI-compatible endpoint.

## Related
- `hermes-agent` skill — provider configuration reference
- `container-oauth` — for container-specific auth patterns
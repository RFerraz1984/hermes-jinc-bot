# Groq as Custom Provider on Hermes

## Configuration

Add to `/opt/data/config.yaml`:

```yaml
custom_providers:
  - name: groq
    base_url: https://api.groq.com/openai/v1
    key_env: GROQ_API_KEY

# Optional: set as default model
model:
  default: llama-3.3-70b-versatile
  provider: custom:groq
```

Add to `/opt/data/.env`:
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

## Available Models (as of 2026)

| Model ID | Context | Notes |
|----------|---------|-------|
| `llama-3.3-70b-versatile` | 128k | Best general purpose |
| `llama-3.1-70b-versatile` | 128k | Previous gen |
| `llama-3.1-8b-instant` | 128k | Fast, smaller |
| `mixtral-8x7b-32768` | 32k | MoE model |
| `gemma2-9b-it` | 8k | Google Gemma |
| `qwen/qwen3-32b` | 32k | Better tool calling |

## Usage

```bash
# One-shot
hermes chat -q "Hello" --provider custom:groq --model llama-3.3-70b-versatile

# Interactive switch
/model custom:groq:llama-3.3-70b-versatile

# Via hermes model menu
hermes model
# Select "custom:groq" then choose model
```

## Function Calling Limitations

**Known issue**: Groq-hosted Llama models have limited/broken function calling support.

Symptoms:
- Model attempts to call tools not in `request.tools` (e.g., `clarify`)
- "Failed to call a function" errors
- Tool calls with malformed arguments

**Workarounds**:
1. Use simpler prompts without tool requirements
2. Disable toolsets for Groq sessions: `hermes tools disable all` (temporary)
3. Use models with better tool calling: `qwen/qwen3-32b` on Groq, or Together AI/OpenRouter
4. Use Groq for pure chat/completion, not agent workflows

## Performance

- **Speed**: ~500 tokens/sec on 70B models (LPU inference)
- **Latency**: Extremely low, great for interactive use
- **Cost**: Free tier generous, paid very cheap

## Context Length

All Groq models: 128k context (except Mixtral 32k, Gemma 8k).

Set explicitly in config if auto-detection fails:
```yaml
custom_providers:
  - name: groq
    base_url: https://api.groq.com/openai/v1
    key_env: GROQ_API_KEY
    models:
      llama-3.3-70b-versatile:
        context_length: 131072
```

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| "Failed to call a function" | Tool calling not supported | Use simpler prompts or different model |
| 401 Unauthorized | Invalid/expired API key | Check `GROQ_API_KEY` in `.env` |
| 429 Rate Limited | Free tier limit | Wait or upgrade |
| Model not found | Wrong model ID | Use exact ID from Groq console |

## Combining with Other Providers

```yaml
custom_providers:
  - name: groq
    base_url: https://api.groq.com/openai/v1
    key_env: GROQ_API_KEY
  - name: together
    base_url: https://api.together.xyz/v1
    key_env: TOGETHER_API_KEY
  - name: perplexity
    base_url: https://api.perplexity.ai
    key_env: PERPLEXITY_API_KEY

model:
  default: llama-3.3-70b-versatile
  provider: custom:groq
```

Switch at runtime:
```
/model custom:groq:llama-3.3-70b-versatile
/model custom:together:meta-llama/Llama-3.3-70B-Instruct-Turbo
/model custom:perplexity:sonar
```
---
name: hermes-stt-setup
description: Configure Speech-to-Text (STT) providers in Hermes Agent, including Groq Whisper, local faster-whisper, OpenAI Whisper, Mistral Voxtral, and ElevenLabs Scribe. Covers API key management via .env, provider selection in config.yaml, and Umbrel-specific paths.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [hermes, stt, speech-to-text, voice, groq, whisper, umbrel, configuration]
    related_skills: [hermes-agent, umbrel]
---

# Hermes STT (Speech-to-Text) Setup

Configure Speech-to-Text providers for Hermes voice features. Hermes supports multiple STT backends with different cost/performance trade-offs.

## Provider Priority (Auto-Detected)

1. **Local faster-whisper** — Free, no API key needed. `pip install faster-whisper`
2. **Groq Whisper** — Free tier, fast. Set `GROQ_API_KEY`
3. **OpenAI Whisper** — Paid. Set `VOICE_TOOLS_OPENAI_KEY`
4. **Mistral Voxtral** — Paid. Set `MISTRAL_API_KEY`
5. **ElevenLabs Scribe** — Paid. Set `ELEVENLABS_API_KEY`

## Quick Setup (Groq - Recommended Free Tier)

```bash
# 1. Get API key from https://console.groq.com/keys
# 2. Add to Hermes .env (Umbrel path shown):
echo 'GROQ_API_KEY="gsk_..."' >> /opt/data/.env

# 3. Set Groq as STT provider
hermes config set stt.provider groq

# 4. Verify
hermes config check | grep GROQ
```

## Configuration (config.yaml)

```yaml
stt:
  enabled: true
  provider: groq        # local | groq | openai | mistral | elevenlabs
  local:
    model: base         # tiny, base, small, medium, large-v3
    language: ''        # auto-detect if empty
  openai:
    model: whisper-1
  mistral:
    model: voxtral-mini-latest
  elevenlabs:
    model_id: scribe_v2
    language_code: ''
    tag_audio_events: false
    diarize: false
```

## Umbrel-Specific Notes

- **Hermes binary**: `/opt/hermes/bin/hermes` (not in PATH by default)
- **Config file**: `/opt/data/config.yaml`
- **Env file**: `/opt/data/.env` (protected - use `hermes config env-path` to locate)
- **Gateway logs**: `/opt/data/logs/gateway.log`
- Do NOT run `hermes update` — Umbrel manages versions via Docker images

### ⚠️ Voice Mode (STT + TTS) no Umbrel — Workaround de Permissão

O venv principal `/opt/hermes/.venv` é **owned by root, read-only** (imagem Docker). Pacotes de áudio (`sounddevice`, `numpy`, `edge-tts`, `faster-whisper`) **não instalam** lá.

**Workaround**: Criar venv do usuário em `/opt/data/voice-venv` (persistente, writable):

```bash
# No terminal do container Hermes:
uv venv /opt/data/voice-venv --python 3.13
/opt/data/voice-venv/bin/python3 -m pip install sounddevice numpy edge-tts faster-whisper
```

**Para usar no CLI/TUI interativo**:
```bash
PYTHONPATH=/opt/data/voice-venv/lib/python3.13/site-packages \
/opt/hermes/.venv/bin/hermes chat --tui
# Dentro do TUI: /voice on
```

**Limitação**: Gateway (serviço s6) roda no venv principal → **TTS no Telegram NÃO funciona** (precisaria rebuild da imagem Docker ou instalar no venv principal como root).
```

> **Nota**: TTS via `text_to_speech` tool funciona (usa backend FAL), mas `/voice tts` no chat usa `edge-tts` local → precisa do venv workaround.

## CLI Commands Reference

| Command | Purpose |
|---------|---------|
| `hermes config set stt.provider groq` | Set STT provider |
| `hermes config set stt.enabled true` | Enable STT |
| `hermes config set stt.local.model base` | Set local model size |
| `hermes config show` | View full config |
| `hermes config check` | Verify API keys detected |
| `hermes auth add <provider>` | Add OAuth/API-key for native providers |

## Non-Native Providers (Groq, etc.)

Providers not in `hermes auth add` list (like Groq for STT) are configured via:
1. Environment variable in `.env` (e.g., `GROQ_API_KEY`)
2. `stt.provider` in config.yaml pointing to that provider

The `hermes auth` system is only for providers with native OAuth/API-key pooling (Anthropic, OpenRouter, Nous, Copilot, Qwen, etc.).

## Voice Commands (In-Session)

- `/voice on` — Voice-to-voice mode
- `/voice tts` — Always respond with TTS
- `/voice off` — Text only
- `/stt` — Toggle STT on/off

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Voice not working | Check `stt.enabled: true` and provider API key |
| Groq not detected | Verify `GROQ_API_KEY` in `.env` and `stt.provider: groq` |
| Local whisper fails | `pip install faster-whisper` inside container |
| Gateway restart needed | Restart Hermes app from Umbrel dashboard after config changes |

## Related Skills

- `hermes-agent` — General Hermes configuration, CLI, gateway, tools
- `umbrel` — Umbrel paths, persistence, networking, container behavior

## References

- `references/notebooklm-py-mcp.md` — notebooklm-py MCP server analysis: why it's problematic on Umbrel, recommended alternative (Drive API + local RAG), and fallback setup if needed
- `references/voice-venv-workaround.md` — **Workaround para voice mode no Umbrel: venv do usuário em /opt/data/voice-venv (venv principal é root-readonly)**
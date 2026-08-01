# Voice Venv Workaround — Hermes no Umbrel

## O Problema

O venv principal do Hermes (`/opt/hermes/.venv`) é **owned by root, read-only** (vem da imagem Docker do app Umbrel). Não é possível instalar pacotes lá:

```bash
/opt/hermes/.venv/bin/pip install sounddevice numpy edge-tts faster-whisper
# Permission denied: /opt/hermes/.venv/lib/python3.13/site-packages/...
```

Pacotes necessários para voice mode (STT + TTS local):
- `sounddevice` — captura de áudio do microfone
- `numpy` — dependência do sounddevice
- `edge-tts` — Microsoft Edge TTS (grátis, pt-BR)
- `faster-whisper` — Whisper local (opcional, para STT offline)

---

## Workaround: Venv do Usuário em `/opt/data/voice-venv`

Como `/opt/data` é persistente e writable pelo usuário `hermes` (UID 1000), criamos um venv separado lá:

```bash
# No terminal do container Hermes (Umbrel Dashboard → Hermes → Terminal):
uv venv /opt/data/voice-venv --python 3.13
/opt/data/voice-venv/bin/python3 -m pip install sounddevice numpy edge-tts faster-whisper
```

### Verificar

```bash
/opt/data/voice-venv/bin/python3 -c "import sounddevice, numpy, edge_tts, faster_whisper; print('OK')"
```

---

## Como Usar

### 1. CLI/TUI Interativo (chat com /voice on)

```bash
PYTHONPATH=/opt/data/voice-venv/lib/python3.13/site-packages \
/opt/hermes/.venv/bin/hermes chat --tui

# Dentro do TUI:
/voice on
```

> O `PYTHONPATH` injeta os pacotes do venv do usuário no processo do Hermes.

### 2. TTS Local via Script (Funciona Hoje)

```bash
/opt/data/voice-venv/bin/python3 -c "
import edge_tts, asyncio
asyncio.run(edge_tts.Communicate('Texto em português', 'pt-BR-FranciscaNeural').save('audio.mp3'))
"
```

---

## Limitação Crítica: Gateway (Telegramado do Telegram)

O **gateway do Hermes** (serviço s6 que recebe mensagens do Telegram) roda no **venv principal** (`/opt/hermes/.venv`), não no venv do usuário.

**Resultado:**
- ✅ STT no Telegram funciona (Groq Whisper = API, não precisa libs locais)
- ✅ `/voice on` no TUI/CLI funciona (com PYTHONPATH workaround)
- ❌ **TTS no Telegram NÃO funciona** — gateway tenta usar `edge-tts` local e falha

### Opções para TTS no Telegram

| Opção | Viabilidade | Como |
|-------|-------------|------|
| Rebuild imagem Docker do app Umbrel | **Solução definitiva** | Precisa PR no repo do app Umbrel (getumbrel/umbrel-apps) adicionando `sounddevice numpy edge-tts` no Dockerfile |
| TTS via API externa (ElevenLabs, OpenAI) | Config no `config.yaml` | `tts.provider: elevenlabs` + API key — não usa libs locais |
| Gerar áudio local + enviar manual | Workaround manual | Script gera .mp3 → envia como anexo no Telegram |

---

## Configuração TTS Atual (config.yaml)

```yaml
tts:
  provider: edge          # Usa edge-tts (precisa lib local)
  edge:
    voice: pt-BR-FranciscaNeural
```

Para usar ElevenLabs (API, não precisa lib local):

```yaml
tts:
  provider: elevenlabs
  elevenlabs:
    voice_id: pNInz6obpgDQGcFmaJgB
    model_id: eleven_multilingual_v2
# Adicionar ELEVENLABS_API_KEY no /opt/data/.env
```

---

## Resumo: O Que Funciona Hoje

| Funcionalidade | STT (Entrada) | TTS (Saída) |
|----------------|---------------|-------------|
| **Telegram (gateway)** | ✅ Groq Whisper (API) | ❌ edge-tts local falha |
| **CLI/TUI interativo** | ✅ Com PYTHONPATH workaround | ✅ Com PYTHONPATH workaround |
| **Script standalone** | ✅ faster-whisper local | ✅ edge-tts local |

---

## Próximos Passos Para TTS no Telegram

1. **Opção rápida**: Configurar `tts.provider: elevenlabs` + `ELEVENLABS_API_KEY` no `.env` (usa API, não lib local)
2. **Opção definitiva**: Abrir issue/PR no repo do app Hermes no Umbrel pedindo `RUN pip install sounddevice numpy edge-tts` no Dockerfile
3. **Workaround manual**: Script gera áudio → você envia como anexo de voz no Telegram
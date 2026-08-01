# Configuração LLM Hermes: OpenRouter Primário (Sem Fallback Groq)

## Problema
Cron jobs Hermes em modo agente (`no_agent=false`) usavam fallback automático para Groq quando OpenRouter falhava. Groq retornava erro 401/429 → cron job falhava com erro "LLM unavailable".

## Solução: Configurar OpenRouter como Único Provider

Editar `~/.hermes/config.yaml`:

```yaml
model:
  default: openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
  provider: openrouter
  base_url: ''
  reasoning_effort: none
  fallback_provider: ''  # VAZIO = sem fallback
  context_length: 131072
fallback_providers: '["openrouter"]'  # APENAS OpenRouter
```

## Variáveis de Ambiente Necessárias (`.env`)

```bash
OPENROUTER_API_KEY=sk-or-...bf1b
# GROQ_API_KEY=...  # Pode remover ou deixar, não será usado
```

## Verificação

```bash
# Testar modelo ativo
hermes chat -q "Qual o modelo atual?" --provider openrouter

# Verificar config
hermes config | grep -A5 "model:"
```

## Boas Práticas

1. **Cron jobs críticos → `no_agent=true`**: Script standalone Python, stdout entregue direto no Telegram — zero dependência de LLM
2. **Se precisa LLM no cron**: Use `model`/`provider` override no job: `hermes cron create ... --model "openrouter/anthropic/claude-3.5-sonnet" --provider openrouter`
3. **Budget guard**: Skill `openrouter-cost-governance` monitora gasto ($10/mês ≈ $0.33/dia)
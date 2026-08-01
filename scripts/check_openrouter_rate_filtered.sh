#!/usr/bin/env bash
# Wrapper que executa check_openrouter_rate.py e passa pelo filtro inteligente

SCRIPT="/opt/data/scripts/check_openrouter_rate.py"
FILTER="/opt/data/scripts/smart_notify_filter.py"

if [[ ! -f "$SCRIPT" || ! -f "$FILTER" ]]; then
    echo "❌ Script ou filtro não encontrado" >&2
    exit 1
fi

# Executa script original e captura saída
OUTPUT=$("$SCRIPT" 2>&1)
EXIT_CODE=$?

# Passa pelo filtro inteligente com argumentos corretos
echo "$OUTPUT" | python3 "$FILTER" \
    --job-name "OpenRouter Rate Limit Watchdog" \
    --exit-code $EXIT_CODE \
    --state-dir /opt/data/cron_notify_state
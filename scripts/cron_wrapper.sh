#!/usr/bin/env bash
# cron_wrapper.sh — Wrapper para cron jobs com filtro inteligente de notificações
# Uso: cron_wrapper.sh "nome_do_job" "comando_completo"
# Exemplo: cron_wrapper.sh "backup" "/opt/data/scripts/backup-hermes-selective.sh"
# O script executa o comando e passa a saída pelo smart_notify_filter.py
# Só notifica no Telegram se o filtro detectar necessidade de ação.

set -euo pipefail

JOB_NAME="${1:-cron_job}"
shift
COMMAND=("$@")

FILTER="/opt/data/scripts/smart_notify_filter.py"
LOG_DIR="/opt/data/cron_logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/${JOB_NAME//\//_}-$(date +%Y%m%d-%H%M%S).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando: $JOB_NAME" | tee "$LOG_FILE"
echo "Comando: ${COMMAND[*]}" | tee -a "$LOG_FILE"
echo "---" | tee -a "$LOG_FILE"

# Executa o comando e captura saída
set +e
"${COMMAND[@]}" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
set -e

echo "---" | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Finalizado: $JOB_NAME (exit code: $EXIT_CODE)" | tee -a "$LOG_FILE"

# Passa a saída completa pelo filtro inteligente
# O filtro decide se imprime algo (que vai pro Telegram via cron) ou fica silencioso
FULL_OUTPUT=$(cat "$LOG_FILE")
FILTERED=$(echo "$FULL_OUTPUT" | python3 "$FILTER" --job-name "$JOB_NAME" --exit-code "$EXIT_CODE")

# Se o filtro retornou algo, imprime (isso vai para o Telegram)
if [[ -n "$FILTERED" && "$FILTERED" != " " ]]; then
    echo "$FILTERED"
fi

# Mantém apenas últimos 50 logs por job
cd "$LOG_DIR"
ls -1t "${JOB_NAME//\//_}-"*.log 2>/dev/null | tail -n +51 | xargs -r rm -f

exit $EXIT_CODE
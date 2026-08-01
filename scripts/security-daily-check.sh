#!/bin/bash
set -euo pipefail

LOG="/opt/data/logs/security-check-$(date +%F).log"

{
  echo "=== Security Check $(date) ==="
  echo "1. Allowlists:"
  grep -E 'TELEGRAM_ALLOWED_USERS|GATEWAY_ALLOW_ALL_USERS' /opt/data/config.yaml /opt/data/.env 2>/dev/null || echo "  Nao configurado"
  echo "2. Cosign:"
  if [ -x /opt/data/bin/cosign ]; then
    echo "  OK Instalado (`/opt/data/bin/cosign version | head -1`)"
  else
    echo "  FALTANDO"
  fi
  echo "3. Dashboard binding (0.0.0.0 --insecure):"
  echo "  (ignorado - normal no container Umbrel)"
  echo "4. Conexoes pty insecure:"
  echo "  (ignorado - normal para TUI/CLI)"
  echo "5. Telegram token status (InvalidToken/Unauthorized hoje):"
  TODAY=`date +%Y-%m-%d`
  TOKEN_ERRORS=`grep -c "$TODAY.*InvalidToken|$TODAY.*Unauthorized" /opt/data/logs/gateway.log 2>/dev/null | head -1`
  if [ "$TOKEN_ERRORS" -gt 0 ]; then
    echo "  $TOKEN_ERRORS erros de token hoje ALERTA"
  else
    echo "  0 erros de token hoje OK"
  fi
  echo "6. Auxiliar Nous auth:"
  echo "  (ignorado - esperado sem portal.nousresearch.com)"
  echo "7. Credenciais antigas (>90 dias):"
  find /opt/data -maxdepth 1 \( -name '.env' -o -name 'auth.json' \) -mtime +90 -exec ls -la {} \; 2>/dev/null || echo "  Nenhuma"
  echo "8. Espaco em disco:"
  df -h /opt/data | tail -1 | awk '{print "  Usado: " $3 " / " $2 " (" $5 ")"}'
} | tee "$LOG"

REAL_ALERTS=0
[ ! -x /opt/data/bin/cosign ] && REAL_ALERTS=1
TODAY=`date +%Y-%m-%d`
TOKEN_ERRORS=`grep -c "$TODAY.*InvalidToken|$TODAY.*Unauthorized" /opt/data/logs/gateway.log 2>/dev/null | head -1`
[ "$TOKEN_ERRORS" -gt 0 ] && REAL_ALERTS=1
find /opt/data -maxdepth 1 \( -name '.env' -o -name 'auth.json' \) -mtime +90 2>/dev/null | grep -q . && REAL_ALERTS=1
DISK_USAGE=`df /opt/data | tail -1 | awk '{print $5}' | sed 's/%//'`
[ "$DISK_USAGE" -gt 85 ] && REAL_ALERTS=1

exit $REAL_ALERTS
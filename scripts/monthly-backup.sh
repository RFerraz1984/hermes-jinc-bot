#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/data/backups"
DATE=$(date +%F)
BACKUP_FILE="$BACKUP_DIR/hermes-backup-$DATE.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "=== Monthly Backup $(date) ==="
echo "Criando backup de configurações essenciais..."

# Backup apenas do essencial: config, scripts, skills, plugins, mcp, small data
tar -czf "$BACKUP_FILE" \
  -C /opt/data \
  .env* \
  auth.json* \
  config.yaml* \
  config.yaml.bak* \
  SOUL.md \
  Hermes-Agent-Umbrel-Configuracao.md \
  umbrel-runtime-context.txt \
  scripts/ \
  skills/ \
  plugins/ \
  mcp/ \
  hooks/ \
  memories/ \
  state/ \
  plans/ \
  kanban/ \
  pairing/ \
  platforms/ \
  cron/ \
  bin/ \
  rag/ \
  2>/dev/null || true

echo "Backup criado: $BACKUP_FILE"
ls -lh "$BACKUP_FILE"

# Manter apenas últimos 3 backups mensais
echo "Limpando backups antigos (>3 meses)..."
ls -1t "$BACKUP_DIR"/hermes-backup-*.tar.gz 2>/dev/null | tail -n +4 | xargs -r rm -f

echo "Backups mantidos:"
ls -lh "$BACKUP_DIR"/hermes-backup-*.tar.gz 2>/dev/null || echo "  (nenhum)"

echo "=== Backup concluído ==="
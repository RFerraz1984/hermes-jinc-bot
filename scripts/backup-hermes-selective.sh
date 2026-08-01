#!/usr/bin/env bash
# Backup seletivo do Hermes (sem segredos, sem cache, sem logs)
# Salva em /opt/data/backups/hermes-selective-YYYYMMDD.tar.gz
# Mantém últimos 30 backups

set -euo pipefail

BACKUP_DIR="/opt/data/backups"
mkdir -p "${BACKUP_DIR}"

DATE=$(date +%Y%m%d)
OUT="${BACKUP_DIR}/hermes-selective-${DATE}.tar.gz"

# O que INCLUIR (essencial para restaurar estado útil)
INCLUDE=(
    ".env"
    "auth.json"
    "auth_spotify.json"
    "config.yaml"
    "cron/jobs.json"
    "skills"
    "scripts"
    "journali"
    "state.db"
    "state.db-shm"
    "state.db-wal"
    "kanban.db"
    "plugins"
    "mcp"
    "rag"
)

# O que EXCLUIR explicitamente (mesmo se estiver nos dirs acima)
EXCLUDE=(
    "--exclude=**/node_modules/**"
    "--exclude=**/__pycache__/**"
    "--exclude=**/.cache/**"
    "--exclude=**/.venv/**"
    "--exclude=**/venv/**"
    "--exclude=**/.npm/**"
    "--exclude=**/.local/**"
    "--exclude=**/logs/**"
    "--exclude=**/cache/**"
    "--exclude=**/backups/**"
    "--exclude=**/tmp/**"
    "--exclude=**/audio_cache/**"
    "--exclude=**/image_cache/**"
    "--exclude=**/sandboxes/**"
    "--exclude=**/hermes-migration/**"
    "--exclude=**/home/.cache/**"
    "--exclude=**/home/.npm/**"
    "--exclude=**/home/.local/**"
    "--exclude=**/home/.config/bsky/**"
)

echo "📦 **Backup Seletivo Hermes** — $(date '+%d/%m/%Y %H:%M')"
echo "   Destino: ${OUT}"

cd /opt/data

# Verifica se arquivos essenciais existem
MISSING=()
for f in "${INCLUDE[@]}"; do
    if [[ ! -e "$f" ]]; then
        MISSING+=("$f")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "   ⚠️ Itens não encontrados (serão ignorados):"
    printf '      - %s\n' "${MISSING[@]}"
fi

# Cria o tar.gz
tar -czf "${OUT}" "${EXCLUDE[@]}" "${INCLUDE[@]}" 2>/dev/null || true

# Verifica resultado
if [[ -f "${OUT}" ]]; then
    SIZE=$(du -h "${OUT}" | cut -f1)
    echo "   ✅ Backup criado com sucesso (${SIZE})"
else
    echo "   ❌ Falha ao criar backup"
    exit 1
fi

# Rotação: mantém últimos 30
cd "${BACKUP_DIR}"
ls -1t hermes-selective-*.tar.gz 2>/dev/null | tail -n +31 | xargs -r rm -f
REMAINING=$(ls -1 hermes-selective-*.tar.gz 2>/dev/null | wc -l)
echo "   🗂️ Backups retidos: ${REMAINING}/30"

echo "   ✅ Concluído"
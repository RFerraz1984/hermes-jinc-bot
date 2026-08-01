#!/usr/bin/env bash
# ============================================================================
# migrate-umbrel-to-ubuntu.sh
# Migra dados do Hermes Agent (Umbrel/Docker) para Ubuntu nativo ou Docker
# ============================================================================
#
# Uso:
#   1. No Umbrel: pare o app Hermes Agent
#   2. Copie este script + templates/ para o Ubuntu
#   3. Rode: ./migrate-umbrel-to-ubuntu.sh
#
# O script:
#   - Copia /opt/data/* do Umbrel para ./data/ no Ubuntu
#   - Ajusta paths no config.yaml (HERMES_HOME, etc.)
#   - Remove configs específicas do Umbrel (container_environment)
#   - Prepara .env limpo para Ubuntu
#   - Valida estrutura antes de subir
#
# ============================================================================

set -euo pipefail

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---------------------------------------------------------------------------
# Configuração — AJUSTE ANTES DE RODAR
# ---------------------------------------------------------------------------
UMBREL_SOURCE="/mnt/umbrel-data"   # Onde o /opt/data do Umbrel está montado no Ubuntu
DEST_DIR="./data"                  # Destino relativo ao script (volume Docker)
HERMES_USER="${HERMES_USER:-hermes}"  # UID/GID do container (padrão 1000:1000)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
confirm() {
    local prompt="${1:-Continue?}"
    read -rp "$prompt [y/N]: " reply
    [[ "$reply" =~ ^[Yy]$ ]]
}

backup_file() {
    local file="$1"
    if [[ -f "$file" ]]; then
        cp "$file" "${file}.bak.$(date +%s)"
        log_info "Backup: $file → ${file}.bak.*"
    fi
}

# ---------------------------------------------------------------------------
# Início
# ---------------------------------------------------------------------------
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  Hermes Agent — Migração Umbrel → Ubuntu                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo

# Verifica origem
if [[ ! -d "$UMBREL_SOURCE" ]]; then
    log_error "Origem não encontrada: $UMBREL_SOURCE"
    log_info "Monte o volume do Umbrel no Ubuntu antes de rodar."
    log_info "Exemplo: sudo mount -t 9p -o trans=virtio,version=9p2000.L hermes-data /mnt/umbrel-data"
    log_info "Ou se for Docker: docker cp hermes-container:/opt/data ./umbrel-data"
    exit 1
fi

log_ok "Origem encontrada: $UMBREL_SOURCE"

# Verifica estrutura esperada
required_dirs=("config.yaml" ".env" "auth.json" "skills" "memories" "scripts" "logs")
missing=()
for d in "${required_dirs[@]}"; do
    if [[ ! -e "$UMBREL_SOURCE/$d" ]]; then
        missing+=("$d")
    fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
    log_warn "Itens não encontrados na origem (podem ser opcionais): ${missing[*]}"
fi

# Confirmação
echo
log_info "Origem:  $UMBREL_SOURCE"
log_info "Destino: $(pwd)/$DEST_DIR"
echo
if ! confirm "Continuar com a migração?"; then
    log_info "Abortado."
    exit 0
fi

# ---------------------------------------------------------------------------
# Cria estrutura de destino
# ---------------------------------------------------------------------------
log_info "Criando estrutura em $DEST_DIR..."
mkdir -p "$DEST_DIR"/{skills,memories,scripts,logs,cache,plugins,cron}

# ---------------------------------------------------------------------------
# Copia arquivos principais
# ---------------------------------------------------------------------------
log_info "Copiando arquivos de configuração..."

# config.yaml
if [[ -f "$UMBREL_SOURCE/config.yaml" ]]; then
    backup_file "$DEST_DIR/config.yaml"
    cp "$UMBREL_SOURCE/config.yaml" "$DEST_DIR/config.yaml"
    log_ok "config.yaml copiado"
fi

# .env — limpa variáveis específicas do Umbrel
if [[ -f "$UMBREL_SOURCE/.env" ]]; then
    backup_file "$DEST_DIR/.env"
    log_info "Processando .env (removendo configs Umbrel)..."
    grep -vE '^(HERMES_TUI_DIR=|PATH=|HERMES_UPSTREAM_TUI_ENTRY=|HERMES_WEB_DIST=|HERMES_WRITE_SAFE_ROOT=|HERMES_GATEWAY_BOOTSTRAP_STATE=|HERMES_DISABLE_LAZY_INSTALLS=|npm_config_install_links=)' \
        "$UMBREL_SOURCE/.env" > "$DEST_DIR/.env" || true
    {
        echo ""
        echo "# --- Configs Ubuntu (adicionadas pela migração) ---"
        echo "HERMES_TUI_DIR=/opt/hermes/ui-tui"
        echo "HERMES_NODE=/usr/bin/node"
        echo "TZ=America/Sao_Paulo"
    } >> "$DEST_DIR/.env"
    log_ok ".env processado e limpo"
fi

# auth.json
if [[ -f "$UMBREL_SOURCE/auth.json" ]]; then
    backup_file "$DEST_DIR/auth.json"
    cp "$UMBREL_SOURCE/auth.json" "$DEST_DIR/auth.json"
    log_ok "auth.json copiado"
fi

# state.db (sessões, kanban, etc.)
if [[ -f "$UMBREL_SOURCE/state.db" ]]; then
    backup_file "$DEST_DIR/state.db"
    cp "$UMBREL_SOURCE/state.db" "$DEST_DIR/state.db"
    log_ok "state.db copiado"
fi

# ---------------------------------------------------------------------------
# Copia diretórios
# ---------------------------------------------------------------------------
for dir in skills memories scripts logs cache plugins cron; do
    if [[ -d "$UMBREL_SOURCE/$dir" ]]; then
        rsync -a --delete "$UMBREL_SOURCE/$dir/" "$DEST_DIR/$dir/"
        log_ok "Diretório $dir sincronizado"
    else
        log_warn "Diretório $dir não existe na origem (pulando)"
    fi
done

# ---------------------------------------------------------------------------
# Ajusta config.yaml para Ubuntu
# ---------------------------------------------------------------------------
if [[ -f "$DEST_DIR/config.yaml" ]]; then
    log_info "Ajustando config.yaml para Ubuntu..."
    backup_file "$DEST_DIR/config.yaml"

    if command -v yq &>/dev/null; then
        yq -i 'del(.container_environment)' "$DEST_DIR/config.yaml" 2>/dev/null || true
        yq -i 'del(.umbrel)' "$DEST_DIR/config.yaml" 2>/dev/null || true
    else
        sed -i '/container_environment:/,/^[^ ]/d' "$DEST_DIR/config.yaml" 2>/dev/null || true
        sed -i '/umbrel:/,/^[^ ]/d' "$DEST_DIR/config.yaml" 2>/dev/null || true
    fi

    if command -v yq &>/dev/null; then
        yq -i '.max_concurrent_sessions //= 5' "$DEST_DIR/config.yaml"
        yq -i '.context_file_max_chars //= 100000' "$DEST_DIR/config.yaml"
    else
        grep -q "max_concurrent_sessions:" "$DEST_DIR/config.yaml" || echo "max_concurrent_sessions: 5" >> "$DEST_DIR/config.yaml"
        grep -q "context_file_max_chars:" "$DEST_DIR/config.yaml" || echo "context_file_max_chars: 100000" >> "$DEST_DIR/config.yaml"
    fi

    log_ok "config.yaml ajustado"
fi

# ---------------------------------------------------------------------------
# Corrige permissões para o usuário do container (hermes:hermes = 1000:1000)
# ---------------------------------------------------------------------------
log_info "Corrigindo permissões (UID/GID 1000:1000)..."
if command -v docker &>/dev/null; then
    docker run --rm \
        -v "$(pwd)/$DEST_DIR:/data" \
        alpine:latest \
        sh -c "chown -R 1000:1000 /data && find /data -type d -exec chmod 755 {} \; && find /data -type f -exec chmod 644 {} \;" 2>/dev/null \
        || sudo chown -R 1000:1000 "$DEST_DIR" 2>/dev/null \
        || log_warn "Não foi possível ajustar permissões automaticamente. Rode manualmente: sudo chown -R 1000:1000 $DEST_DIR"
else
    sudo chown -R 1000:1000 "$DEST_DIR" 2>/dev/null || log_warn "Ajuste permissões manualmente: sudo chown -R 1000:1000 $DEST_DIR"
fi
log_ok "Permissões corrigidas"

# ---------------------------------------------------------------------------
# Validação final
# ---------------------------------------------------------------------------
log_info "Validação final..."

checks=(
    "config.yaml:arquivo de configuração principal"
    ".env:variáveis de ambiente"
    "auth.json:autenticação Nous Portal"
    "state.db:banco de sessões/kanban"
    "skills:diretório de skills"
    "memories:diretório de memórias"
    "scripts:scripts de cron"
)

all_ok=true
for check in "${checks[@]}"; do
    file="${check%%:*}"
    desc="${check#*:}"
    if [[ -e "$DEST_DIR/$file" ]]; then
        log_ok "  ✓ $file ($desc)"
    else
        log_warn "  ⚠ $file ($desc) — NÃO ENCONTRADO"
        all_ok=false
    fi
done

echo
if $all_ok; then
    log_ok "Migração concluída com sucesso!"
else
    log_warn "Migração concluída com avisos. Verifique itens acima."
fi

# ---------------------------------------------------------------------------
# Próximos passos
# ---------------------------------------------------------------------------
cat <<EOF

╔══════════════════════════════════════════════════════════════════╗
║  PRÓXIMOS PASSOS                                                 ║
╚══════════════════════════════════════════════════════════════════╝

1. SUBIR O CONTAINER:
   cd $(pwd)
   docker compose up -d

2. VERIFICAR LOGS:
   docker compose logs -f hermes

3. TESTAR DASHBOARD:
   http://localhost:9119
   http://SEU_IP:9119

4. TESTAR CHAT:
   http://localhost:9119/chat

5. CONFIGURAR RAFT (se usava):
   docker compose exec hermes raft agent login start
   # Aguarde, depois:
   docker compose exec hermes raft agent login wait dvc_XXXXXXXX

6. CONFIGURAR PROXY REVERSO (opcional, para domínio próprio):
   - Edite nginx.conf (exemplo em docker-compose.yml comentado)
   - Aponte DNS para este servidor
   - Rode certbot para SSL

7. CRON JOBS:
   Os scripts em ./data/scripts/ precisam ser recriados via:
   docker compose exec hermes hermes cron create ...

   Ou use systemd timers no host Ubuntu (mais robusto).

8. BACKUP REGULAR:
   Adicione ao crontab do host:
   0 3 * * * tar -czf /backup/hermes-\$(date +\%F).tar.gz -C $(pwd) data/

═══════════════════════════════════════════════════════════════════
EOF

# Mostra resumo do que foi migrado
echo
log_info "Resumo do destino ($DEST_DIR):"
du -sh "$DEST_DIR"/* 2>/dev/null | sort -hr
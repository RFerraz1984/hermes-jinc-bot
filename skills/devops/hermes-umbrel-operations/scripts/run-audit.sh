# Padrão de Auditoria de Acessibilidade — Execução em Umbrel (Hermes Agent)

Este script encapsula o padrão validado para rodar auditorias completas do `accessibility-audit-toolkit` no ambiente Hermes/Umbrel, lidando com:
- PATH do npm global (`/opt/data/.npm-global/bin`)
- Playwright browsers path (`/opt/data/.playwright`)
- Python venv do Hermes (`/opt/data/.venv/bin/python`)

## Uso

```bash
# Auditoria rápida (auto-only) de uma URL
/opt/data/scripts/run-audit.sh --url https://jornalistainclusivo.com --auto-only --output /opt/data/audits/jinc_$(date +%F)

# Auditoria completa (auto + manual) com crawl depth 3
/opt/data/scripts/run-audit.sh --url https://pcd.dataverso.org --depth 3 --output /opt/data/audits/dataverso_$(date +%F)

# Auditoria de lista de URLs (arquivo com uma URL por linha)
/opt/data/scripts/run-audit.sh --url-list /opt/data/urls_legislativo.txt --auto-only --output /opt/data/audits/legislativo_$(date +%F)
```

## Script

```bash
#!/usr/bin/env bash
# /opt/data/scripts/run-audit.sh
# Wrapper padronizado para accessibility-audit-toolkit no Hermes/Umbrel

set -euo pipefail

# Configuração de ambiente
export PATH="/opt/data/.npm-global/bin:$PATH"
export PLAYWRIGHT_BROWSERS_PATH="/opt/data/.playwright"
PYTHON="/opt/data/.venv/bin/python"
TOOLKIT_DIR="/opt/data/skills/journalism/accessibility-audit-toolkit"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Defaults
AUTO_ONLY=false
DEPTH=3
MAX_URLS=20
OUTPUT_BASE="/opt/data/audits"
URL=""
URL_LIST=""

usage() {
    cat <<EOF
Uso: $0 [opções]

Opções:
  --url URL              URL única para auditar
  --url-list FILE        Arquivo com URLs (uma por linha)
  --auto-only            Apenas testes automatizados (axe, pa11y, lighthouse, contraste)
  --depth N              Profundidade do crawl (padrão: 3)
  --max-urls N           Máximo de URLs para auditar (padrão: 20)
  --output DIR           Diretório base de saída (padrão: /opt/data/audits)
  -h, --help             Mostra esta ajuda

Exemplos:
  $0 --url https://jornalistainclusivo.com --auto-only
  $0 --url-list /opt/data/urls.txt --depth 2 --max-urls 50
EOF
}

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --url) URL="$2"; shift 2 ;;
        --url-list) URL_LIST="$2"; shift 2 ;;
        --auto-only) AUTO_ONLY=true; shift ;;
        --depth) DEPTH="$2"; shift 2 ;;
        --max-urls) MAX_URLS="$2"; shift 2 ;;
        --output) OUTPUT_BASE="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Opção desconhecida: $1"; usage; exit 1 ;;
    esac
done

# Validação
if [[ -z "$URL" && -z "$URL_LIST" ]]; then
    echo "Erro: --url ou --url-list é obrigatório"
    usage
    exit 1
fi

# Diretório de saída com timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SITE_NAME=$(echo "${URL:-$URL_LIST}" | sed -E 's|https?://||' | sed -E 's|/.*||' | sed 's/[^a-zA-Z0-9._-]/_/g')
OUTPUT_DIR="${OUTPUT_BASE}/${SITE_NAME}_${TIMESTAMP}"

mkdir -p "$OUTPUT_DIR"

echo "📊 Iniciando auditoria de acessibilidade"
echo "   Site: ${URL:-$URL_LIST}"
echo "   Saída: $OUTPUT_DIR"
echo "   Auto-only: $AUTO_ONLY"
echo "   Depth: $DEPTH"
echo "   Max URLs: $MAX_URLS"

cd "$TOOLKIT_DIR"

# Construir comando
CMD=("$PYTHON" "-m" "scripts.audit")

if [[ -n "$URL" ]]; then
    CMD+=("$URL")
fi

if [[ -n "$URL_LIST" ]]; then
    CMD+=("--url-list" "$URL_LIST")
fi

if [[ "$AUTO_ONLY" == "true" ]]; then
    CMD+=("--auto-only")
fi

CMD+=("--depth" "$DEPTH")
CMD+=("--max-urls" "$MAX_URLS")
CMD+=("--output" "$OUTPUT_DIR")

# Executar com timeout (30 min max)
timeout 1800 "${CMD[@]}" 2>&1 | tee "$OUTPUT_DIR/audit.log"

EXIT_CODE=${PIPESTATUS[0]}

if [[ $EXIT_CODE -eq 0 ]]; then
    echo ""
    echo "✅ Auditoria concluída com sucesso"
    echo "📁 Relatórios em: $OUTPUT_DIR/reports/"
    ls -la "$OUTPUT_DIR/reports/"
elif [[ $EXIT_CODE -eq 124 ]]; then
    echo ""
    echo "⏱️ Timeout (30 min) — auditoria parcial salva em $OUTPUT_DIR"
    exit 1
else
    echo ""
    echo "❌ Auditoria falhou (exit code: $EXIT_CODE)"
    echo "📋 Log: $OUTPUT_DIR/audit.log"
    exit $EXIT_CODE
fi
```

## Instalação

```bash
# 1. Criar script
mkdir -p /opt/data/scripts
cat > /opt/data/scripts/run-audit.sh << 'EOF'
[conteúdo do script acima]
EOF
chmod +x /opt/data/scripts/run-audit.sh

# 2. Testar
/opt/data/scripts/run-audit.sh --url https://jornalistainclusivo.com --auto-only --output /opt/data/audits/test

# 3. Usar em cron job (hermes)
/opt/hermes/bin/hermes cron create --name "audit-daily-jinc-wrapper" \
  --skill "accessibility-audit-toolkit" \
  --deliver "telegram:965862678" \
  "0 3 * * *" \
  "/opt/data/scripts/run-audit.sh --url-list /opt/data/urls_jinc.txt --auto-only --output /opt/data/audits/jinc_daily"
```

## Variáveis de Ambiente Necessárias (no .env do Umbrel)

```bash
PATH=/opt/data/.npm-global/bin:/opt/data/bin:/opt/data/home/.local/bin:$PATH
PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright
TELEGRAM_BOT_TOKEN=seu_token_aqui
TELEGRAM_HOME_CHANNEL=965862678
OPENROUTER_API_KEY=sua_key_aqui
```
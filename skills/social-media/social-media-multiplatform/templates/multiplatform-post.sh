#!/usr/bin/env bash
# Multi-Platform RSS → Social Media Poster
# Copiar para /opt/data/scripts/multiplatform-post.sh && chmod +x
# Suporta: Bluesky, Telegram Channel, X/Twitter, Facebook Page
# Estado persistente em /opt/data/multiplatform-posted-ids.txt

set -euo pipefail

# ====== CONFIGURAÇÃO ======
RSS_URL="${RSS_URL:-https://jornalistainclusivo.com.br/feed}"
STATE_FILE="/opt/data/multiplatform-posted-ids.txt"
MAX_POSTS_PER_RUN="${MAX_POSTS_PER_RUN:-3}"

# Binários (ajustar se instalados em locais diferentes)
BSKY_BIN="${HOME}/.local/bin/bsky"          # ou $(go env GOPATH)/bin/bsky
XURL_BIN="${HOME}/.local/bin/xurl"          # ou $(which xurl)
CURL_BIN="$(which curl)"

# ====== FUNÇÕES UTILITÁRIAS ======
log() { echo "[$(date '+%H:%M:%S')] $*"; }
warn() { log "⚠️  $*"; }
error() { log "❌ $*"; }
success() { log "✅ $*"; }

# Carregar IDs já postados
declare -A posted_ids
if [[ -f "$STATE_FILE" ]]; then
    while IFS= read -r line; do
        posted_ids["$line"]=1
    done < "$STATE_FILE"
fi

# ====== RSS PARSER ======
# Usa Python (xml.etree.ElementTree) em vez de xmllint — container não tem libxml2-utils
# curl -L para seguir redirect 301 do WordPress (Cloudflare)
# User-Agent para bypass Cloudflare 403
get_rss_items() {
    python3 -c "
import sys
import xml.etree.ElementTree as ET
import urllib.request

try:
    req = urllib.request.Request(
        '$RSS_URL',
        headers={'User-Agent': 'Mozilla/5.0 (compatible; JINC-RSS-Bot/1.0)'}
    )
    response = urllib.request.urlopen(req)
    xml_data = response.read()
    root = ET.fromstring(xml_data)

    for item in root.findall('.//item'):
        title_elem = item.find('title')
        link_elem = item.find('link')
        guid_elem = item.find('guid')

        title = title_elem.text if title_elem is not None else ''
        link = link_elem.text if link_elem is not None else ''
        guid = guid_elem.text if guid_elem is not None else ''

        id_val = guid if guid else link
        if id_val and title and link:
            # Escape pipes in content
            title = title.replace('|', ' ')
            link = link.replace('|', ' ')
            print(f'{id_val}|{title}|{link}')
except Exception as e:
    print(f'Error parsing RSS: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# ====== PLATAFORMAS ======

# --- Bluesky ---
post_bluesky() {
    local title="$1" link="$2"
    local text="Novo artigo no Jornalista Inclusivo: \"$title\" 🔗 $link #Acessibilidade #PcD #Inclusão #JornalismoInclusivo"

    if [[ -x "$BSKY_BIN" ]]; then
        if HOME=/opt/data/home "$BSKY_BIN" post "$text" >/dev/null 2>&1; then
            success "Bluesky: $title"
            return 0
        else
            error "Bluesky falhou: $title"
            return 1
        fi
    else
        warn "Bluesky: bsky CLI não encontrado em $BSKY_BIN (pular)"
        return 2  # skipped
    fi
}

# --- Telegram Channel ---
post_telegram() {
    local title="$1" link="$2"
    local text="📰 *Novo artigo no Jornalista Inclusivo*%0A%0A\"$title\"%0A%0A🔗 $link%0A%0A#Acessibilidade #PcD #Inclusão #JornalismoInclusivo"

    if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHANNEL_ID:-}" ]]; then
        local resp
        resp=$("$CURL_BIN" -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHANNEL_ID}" \
            -d "text=${text}" \
            -d "parse_mode=Markdown" \
            -d "disable_web_page_preview=false")
        if echo "$resp" | jq -e '.ok == true' >/dev/null 2>&1; then
            success "Telegram: $title"
            return 0
        else
            error "Telegram falhou: $(echo "$resp" | jq -r '.description // "unknown"')"
            return 1
        fi
    else
        warn "Telegram: TELEGRAM_BOT_TOKEN ou TELEGRAM_CHANNEL_ID não definidos (pular)"
        return 2
    fi
}

# --- X/Twitter (xurl) ---
post_x() {
    local title="$1" link="$2"
    local text="📰 Novo artigo no Jornalista Inclusivo:%0A%0A\"$title\"%0A%0A🔗 $link%0A%0A#JornalismoInclusivo #Acessibilidade #PcD #Inclusão"

    if [[ -x "$XURL_BIN" ]]; then
        if HOME=/opt/data/home "$XURL_BIN" post "$text" >/dev/null 2>&1; then
            success "X/Twitter: $title"
            return 0
        else
            error "X/Twitter falhou: $title"
            return 1
        fi
    else
        warn "X/Twitter: xurl não encontrado em $XURL_BIN (pular)"
        return 2
    fi
}

# --- Facebook Page ---
post_facebook() {
    local title="$1" link="$2"
    local text="Novo artigo no Jornalista Inclusivo: \"$title\" 🔗 $link #Acessibilidade #PcD #Inclusão"

    if [[ -n "${FB_PAGE_ACCESS_TOKEN:-}" && -n "${FB_PAGE_ID:-}" ]]; then
        local resp
        resp=$("$CURL_BIN" -s -X POST "https://graph.facebook.com/v19.0/${FB_PAGE_ID}/feed" \
            -d "message=${text}" \
            -d "access_token=${FB_PAGE_ACCESS_TOKEN}")
        if echo "$resp" | jq -e '.id' >/dev/null 2>&1; then
            success "Facebook: $title"
            return 0
        else
            error "Facebook falhou: $(echo "$resp" | jq -r '.error.message // "unknown"')"
            return 1
        fi
    else
        warn "Facebook: FB_PAGE_ACCESS_TOKEN ou FB_PAGE_ID não definidos (pular)"
        return 2
    fi
}

# ====== MAIN ======
log "=== Multi-Platform Post Started ==="
log "RSS: $RSS_URL | Max posts: $MAX_POSTS_PER_RUN"

count=0
skipped=0

while IFS='|' read -r id title link; do
    [[ -z "$id" ]] && continue
    [[ -n "${posted_ids[$id]:-}" ]] && continue

    log "Novo artigo detectado: $title"

    # Tentar postar em cada plataforma (continuar mesmo se uma falhar)
    # || true evita que set -e saia do script quando uma plataforma falha/skip (exit code 2)
    platform_results=()

    post_bluesky "$title" "$link" || true; platform_results+=("Bluesky:$?")
    post_telegram "$title" "$link" || true; platform_results+=("Telegram:$?")
    post_x "$title" "$link" || true; platform_results+=("X:$?")
    post_facebook "$title" "$link" || true; platform_results+=("Facebook:$?")

    # Verificar se pelo menos uma plataforma succeeded (exit code 0)
    success_any=false
    for result in "${platform_results[@]}"; do
        platform="${result%%:*}"
        code="${result##*:}"
        [[ "$code" == "0" ]] && success_any=true
    done

    if [[ "$success_any" == "true" ]]; then
        echo "$id" >> "$STATE_FILE"
        ((count++))
        log "--- Artigo processado ($count/$MAX_POSTS_PER_RUN) ---"
    else
        warn "Todas as plataformas falharam/skipped para: $title"
    fi

    (( count >= MAX_POSTS_PER_RUN )) && break

    sleep 2  # rate limit amigável entre artigos
done < <(get_rss_items)

log "=== Concluído: $count novos artigos postados, $skipped skipped ==="
exit 0
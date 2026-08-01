#!/usr/bin/env bash
# Template: RSS → X/Twitter auto-post para Jornalista Inclusivo
# Copiar para /opt/data/scripts/rss-to-x.sh e dar chmod +x
# Requer: xurl instalado e autenticado (ver skill xurl)

set -euo pipefail

RSS_URL="https://jornalistainclusivo.com.br/feed"
STATE_FILE="/opt/data/rss-posted-ids.txt"
XURL_BIN="${HOME}/.local/bin/xurl"
MAX_POSTS_PER_RUN=3

# Verificar xurl
if [[ ! -x "$XURL_BIN" ]]; then
    echo "xurl não encontrado em $XURL_BIN"
    echo "Instale: curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh | bash"
    exit 1
fi

# Verificar auth (usa HOME do container Hermes)
if ! HOME=/opt/data/home "$XURL_BIN" auth status >/dev/null 2>&1; then
    echo "xurl não autenticado. Configure com HOME=/opt/data/home xurl auth oauth2 --app jinc-app @seu_usuario"
    exit 1
fi

# Carregar IDs já postados
declare -A posted_ids
if [[ -f "$STATE_FILE" ]]; then
    while IFS= read -r line; do
        posted_ids["$line"]=1
    done < "$STATE_FILE"
fi

# Buscar itens do RSS (usa xmllint se disponível, senão grep/sed básico)
get_rss_items() {
    curl -s "$RSS_URL" | \
    xmllint --xpath '//item' - 2>/dev/null | \
    sed 's/<item>/\n<item>/g' | \
    grep '^<item>' | \
    while IFS= read -r item; do
        title=$(echo "$item" | xmllint --xpath 'string(title)' - 2>/dev/null)
        link=$(echo "$item" | xmllint --xpath 'string(link)' - 2>/dev/null)
        guid=$(echo "$item" | xmllint --xpath 'string(guid)' - 2>/dev/null)
        id="${guid:-$link}"
        echo "$id|$title|$link"
    done
}

# Processar itens novos
count=0
while IFS='|' read -r id title link; do
    [[ -z "$id" ]] && continue
    [[ -n "${posted_ids[$id]:-}" ]] && continue

    tweet="📰 Novo artigo no Jornalista Inclusivo:\n\n\"$title\"\n\n🔗 $link\n\n#JornalismoInclusivo #Acessibilidade #PcD #Inclusão"

    echo "Postando: $title"
    if HOME=/opt/data/home "$XURL_BIN" post "$tweet"; then
        echo "$id" >> "$STATE_FILE"
        ((count++))
        sleep 2
    else
        echo "Erro ao postar: $title"
    fi

    (( count >= MAX_POSTS_PER_RUN )) && break
done < <(get_rss_items)

echo "Concluído. $count novos posts publicados."
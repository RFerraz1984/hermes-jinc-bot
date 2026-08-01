#!/usr/bin/env bash
set -euo pipefail

# Configurações
RSS_URL="https://jornalistainclusivo.com.br/feed"
STATE_FILE="/opt/data/rss-state.json"
XURL_BIN="${HOME}/.local/bin/xurl"

# Verificar se xurl existe
if [[ ! -x "$XURL_BIN" ]]; then
    echo "xurl não encontrado em $XURL_BIN. Instale com: curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh | bash"
    exit 1
fi

# Verificar auth
if ! HOME=/opt/data/home "$XURL_BIN" auth status >/opt/data/opt/data/home >/dev/null 2>&1; then
    echo "xurl não autenticado. Configure com: HOME=/opt/data/home xurl auth oauth2 --app meu-app @seu_usuario"
    exit 1
fi

# Função para obter posts do RSS
get_rss_items() {
    curl -s "$RSS_URL" | \
    xmllint --xpath '//item' - 2>/dev/null | \
    sed 's/<item>/\n<item>/g' | \
    grep -E '^<item>' | \
    while IFS= read -r item; do
        title=$(echo "$item" | xmllint --xpath 'string(title)' - 2>/dev/null)
        link=$(echo "$item" | xmllint --xpath 'string(link)' - 2>/dev/null)
        pubDate=$(echo "$item" | xmllint --xpath 'string(pubDate)' - 2>/dev/null)
        guid=$(echo "$item" | xmllint --xpath 'string(guid)' - 2>/dev/null)
        
        # Usar GUID ou link como ID único
        id="${guid:-$link}"
        echo "$id|$title|$link|$pubDate"
    done
}

# Carregar estado anterior
declare -A posted_ids
if [[ -f "$STATE_FILE" ]]; then
    while IFS= read -r line; do
        posted_ids["$line"]=1
    done < "$STATE_FILE"
fi

# Processar itens novos
new_items=()
while IFS='|' read -r id title link pubDate; do
    if [[ -z "${posted_ids[$id]:-}" ]]; then
        new_items+=("$id|$title|$link|$pubDate")
    fi
done < <(get_rss_items)

# Postar itens novos (máximo 3 por execução para não spammar)
count=0
for item in "${new_items[@]}"; do
    if (( count >= 3 )); then
        break
    fi
    
    IFS='|' read -r id title link pubDate <<< "$item"
    
    # Criar tweet
    tweet="📰 Novo artigo no Jornalista Inclusivo:\n\n\"$title\"\n\n🔗 $link\n\n#JornalismoInclusivo #Acessibilidade #PcD #Inclusão"
    
    echo "Postando: $title"
    if HOME=/opt/data/home "$XURL_BIN" post "$tweet"; then
        echo "$id" >> "$STATE_FILE"
        ((count++))
        sleep 2  # Rate limit amigável
    else
        echo "Erro ao postar: $title"
    fi
done

echo "Concluído. $count novos posts publicados."

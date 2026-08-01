#!/bin/bash
set -euo pipefail

# Configurações
RSS_URL="https://jornalistainclusivo.com.br/feed"
MARKDOWN_FILE="/opt/data/rss-articles.md"

today=$(date +%Y-%m-%d)

# Extrair itens do RSS
get_rss_items() {
    curl -s "$RSS_URL" | \
    xmllint --xpath '//channel/item' - 2>/dev/null | \
    sed 's/<item>/\n<item>/g' | \
    while IFS= read -r item; do
        title=$(echo "$item" | xmllint --xpath 'string(title)' - 2>/dev/null) 
        link=$(echo "$item" | xmllint --xpath 'string(link)' - 2>/dev/null) 
        pubDate=$(echo "$item" | xmllint --xpath 'string(pubDate)' - 2>/dev/null) 
        description=$(echo "$item" | xmllint --xpath 'string(description)' - 2>/dev/null) 
        
        [[ -z $title || -z $link || -z $pubDate || -z $description ]] && continue
        
        printf "%s|%s|%s|%s\n" "$(echo "$pubDate" | date +%-Y-%-m-%-d)" "$title" "$link" "$description"
    done
}


# Formatar itens como markdown
format_as_markdown() {
    echo "\n## $today"
    echo "---"
    
    while IFS='|' read -r pubDate title link description; do
        date_formatted=$(date -d "$pubDate" +"%d/%m/%Y")
        
        echo "### ["$title"]("$link")"
        echo "**Publicado em:** $date_formatted"
        echo "\n$date_formatted"
        echo "$description"
        echo "\n\n"
    done
}


# Pasta de trabalho do Hermes-agent
HERMES_Tools_DIR="$HOME/hermes-agent"

# Executar pipeline
get_rss_items | format_as_markdown >> $MARKDOWN_FILE
chmod 644 $MARKDOWN_FILE

# Compactar (maneira mais segura do que truncate)
grep -n "## [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]" $MARKDOWN_FILE | \
    sort -u | \
    sed 's/\x1b$$$$[0-9;]*m//g' | \
    cat > $MARKDOWN_FILE

# Configuração Mensal
cat << EOF | fold -s -w 80 >> $MARKDOWN_FILE

// ====================================================================
// Archives: $(date -d "-30 days" +%Y-%m-%d) a $today,
// Total de posts acumulados no arquivo: $(wc -l $MARKDOWN_FILE | awk '{print $1}')
// Arquivo salvo em: $MARKDOWN_FILE
// ====================================================================
EOF


# Final
if [[ $? -eq 0 ]]; then
    echo "✅ Artigos no Jornalista Inclusivo persistidos com sucesso como Markdown"
else
    echo "⚠️ Apenas o último ciclo completo foi salvo"
fi
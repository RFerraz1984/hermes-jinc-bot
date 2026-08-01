# State File Format & Deduplication Logic — multiplatform-post.sh

## Formato do Arquivo de Estado

**Local**: `/opt/data/multiplatform-posted-ids.txt`

**Formato por linha**: `GUID|title|link`

```text
https://jornalistainclusivo.com.br/?p=3379|O carrossel do seu site pode estar excluindo milhões de pessoas|https://jornalistainclusivo.com.br/2026/06/29/o-carrossel-do-seu-site-pode-estar-excluindo-milhoes-de-pessoas/
https://jornalistainclusivo.com.br/?p=2983|Os 5 Pilares do Jornalismo Inclusivo na Cobertura sobre Autismo|https://jornalistainclusivo.com.br/2026/05/07/os-5-pilares-do-jornalismo-inclusivo-na-cobertura-sobre-autismo/
https://jornalistainclusivo.com.br/?p=2794|Guia de Acessibilidade Aldir Blanc: MinC lança manual para fortalecer inclusão na cultura|https://jornalistainclusivo.com.br/2025/11/03/guia-de-acessibilidade-aldir-blanc-minc/
```

## Por que GUID (não índice numérico)

**Problema original**: Script usava índice 1,2,3... do RSS como ID. Quando novos artigos entram no topo do feed, todos os índices mudam → deduplicação quebra.

**Solução**: Usar `<guid isPermaLink="false">` do RSS (ex: `https://jornalistainclusivo.com.br/?p=3379`) como chave estável.

## Parser de Estado (Bash)

```bash
declare -A posted_ids
while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    id_only="${line%%|*}"  # Extrai primeira coluna (GUID)
    posted_ids["$id_only"]=1
done < "$STATE_FILE"

# Verificação no loop principal
while IFS='|' read -r id title link; do
    [[ -z "$id" ]] && continue
    [[ -n "${posted_ids[$id]:-}" ]] && continue  # Skip se já postado
    # ... processar novo artigo
done < <(get_rss_items)
```

## Parser RSS (Python) — Extrai GUID

```python
for item in root.findall('.//item'):
    title_elem = item.find('title')
    link_elem = item.find('link')
    guid_elem = item.find('guid')
    
    title = title_elem.text if title_elem is not None else ''
    link = link_elem.text if link_elem is not None else ''
    guid = guid_elem.text if guid_elem is not None else ''
    
    id_val = guid if guid else link  # Fallback para link se sem GUID
    if id_val and title and link:
        print(f'{id_val}|{title}|{link}')
```

## Escrita no State File (após sucesso em pelo menos 1 plataforma)

```bash
echo "$id|$title|$link" >> "$STATE_FILE"
```

## Lições Aprendidas

1. **Nunca use índices posicionais** para deduplicação em feeds RSS/Atom
2. **GUID é estável** — WordPress usa `?p=POST_ID` como GUID permanente
3. **Formato `GUID|title|link`** permite debug humano + parse rápido em Bash
4. **Escrita condicional** (só se `success_any == true`) evita marcar como postado artigos que falharam em todas as plataformas
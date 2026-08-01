# Fix: Crawl Site Depth=0 Respect

## Problema
`scripts/crawl_site.py` ignorava `max_depth=0` e sempre tentava buscar sitemap.xml + crawl, descoberto centenas de URLs mesmo quando só queria auditar a home page.

## Fix Aplicado
```python
# ANTES
sitemap_urls = await fetch_sitemap(base_url)
for url in sitemap_urls:
    if should_include(...):
        discovered.append(url)

# DEPOIS
# 1. Tenta sitemap.xml (apenas se max_depth > 0)
sitemap_urls = []
if max_depth > 0:
    sitemap_urls = await fetch_sitemap(base_url)
    for url in sitemap_urls:
        if should_include(...):
            discovered.append(url)
```

## Impacto no Cron
- `audit_cron.py` usa `depth=0` → agora audita **apenas a URL passada** (home page)
- Antes: crawl descobria 100+ URLs, auditoria demorava 15+ min
- Depois: 1 URL, auditoria ~2 min para 3 sites

## Arquivos Modificados
- `scripts/crawl_site.py` — linhas ~120-130
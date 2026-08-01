# Automação: dataverso-sync

**Descrição:** Sincroniza datasets do CKAN (dados.dataverso.org) → gera site estático acessível (HTML + CSV/JSON) + sitemap + feed RSS + cards para newsletter.

**Input (JSON):**
```json
{
  "ckan_url": "https://dados.dataverso.org",
  "api_key": "string (opcional, para datasets privados)",
  "output_dir": "/opt/data/jinc-state/dataverso-site/",
  "include_tags": ["pcdeficiencia", "acessibilidade", "dados-abertos"],
  "exclude_private": true,
  "generate": ["html", "csv", "json", "rss", "sitemap", "cards"]
}
```

**Output (arquivos em output_dir):**
```
/index.html                 # Home: busca, categorias, datasets em destaque
/datasets/index.html        # Lista paginada (20/pág) com filtros acessíveis
/datasets/{slug}/index.html # Detalhe dataset: metadados, preview, download, API
/datasets/{slug}/data.csv   # CSV limpo (UTF-8, BOM, cabeçalhos pt-BR)
/datasets/{slug}/data.json  # JSON normalizado
/datasets/{slug}/metadata.json # DCAT-AP + acessibilidade
/rss.xml                    # Feed novos datasets
/sitemap.xml                # Sitemap Google
/cards/                     # HTML snippets para newsletter (um por dataset)
/search.json                # Índice cliente-side (algolia/lunr compatível)
```

**Prompt para Hermes:**
---
Você é mantenedor do **Dataverso PcD** (dados.dataverso.org). Sincronize datasets públicos e gere portal estático acessível.

**PASSOS:**
1. **Fetch CKAN** — `package_search` (rows=1000, fq=tags:pcdeficiencia OR acessibilidade OR "dados abertos")
2. **Normalizar** cada dataset:
   - Título, descrição (limpar HTML, linguagem simples)
   - Recursos: filtrar CSV/JSON/XLSX/GeoJSON → padronizar encoding UTF-8, cabeçalhos pt-BR
   - Metadados: organização, frequência, licença, cobertura temporal/geo, qualidade (completude, frescor)
   - **Acessibilidade do dado**: tem dicionário de variáveis? códigos explicados? outliers documentados?
3. **Gerar HTML acessível** (Astro/11ty ou template Jinja2 puro):
   - Semantic HTML: `<main>`, `<article>`, `<section>`, `<nav aria-label>`
   - Busca: `<input type="search">` + `<datalist>` sugestões
   - Tabelas: `<table><caption><thead><th scope="col">`
   - Downloads: `<a href="..." download>CSV (UTF-8)</a>` + tamanho + linhas
   - API: exemplo curl + resposta JSON documentada
   - Microdata: `Dataset` (schema.org) + DCAT-AP
4. **Cards para newsletter** — snippet HTML inline (sem CSS externo):
   ```html
   <article class="dataverso-card">
     <h3><a href="https://dados.dataverso.org/dataset/{slug}">{Título}</a></h3>
     <p>{Descrição 160 chars}</p>
     <dl>
       <dt>Fonte</dt><dd>{Organização}</dd>
       <dt>Atualizado</dt><dd>{data}</dd>
       <dt>Registros</dt><dd>{N:,}</dd>
     </dl>
     <a href=".../data.csv">Baixar CSV</a> | <a href=".../api">API</a>
   </article>
   ```
5. **Validação** — axe-core headless + WCAG 2.1 AA checklist (contraste, foco, landmarks, idioma)
6. **Deploy** — rsync para servidor estático / Cloudflare Pages / Netlify (configurar via env)

**SCHEDULE SUGERIDO (cron Hermes):** Diário 03:00 BRT

**RETORNE:** Resumo: datasets processados, novos, atualizados, erros, tempo execução, caminho output.
---
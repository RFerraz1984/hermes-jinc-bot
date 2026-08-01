---
name: web-scraping-pipeline
version: "1.0.0"
description: Pipeline robusto de coleta automatizada para portais governamentais, Diários Oficiais, sites de acessibilidade e legislação PcD no Brasil. Extração estruturada, deduplicação, alertas Telegram.
category: journalism
tags: [web-scraping, journalism, government-data, accessibility, legislation, brazil, telegram, cron]
author: Hermes Agent
license: MIT
---

# Web Scraping Pipeline — Jornalista Inclusivo

Pipeline robusto de coleta automatizada para portais governamentais, Diários Oficiais, sites de acessibilidade e legislação PcD no Brasil.

## Objetivo

- Coleta diária/horária de fontes oficiais (GOV.BR, Diário Oficial da União, Câmara, Senado, MDH, CONADE, TSE, IBGE)
- Deduplicação por hash de conteúdo (SHA-256) + metadados
- Extração estruturada: título, data, órgão, texto, links, tags (PcD, acessibilidade, inclusão, cotas, lei, decreto, portaria)
- Alerta imediato via Telegram para itens relevantes
- Armazenamento append-only (JSONL) + índice SQLite para busca
- Agendamento via cron Hermes (30min / 1h / 6h conforme criticidade)

## Arquitetura

```
/opt/data/skills/web-scraping-pipeline/
├── SKILL.md
├── scripts/
│   ├── fetch.py          # Playwright + httpx (com retry/backoff)
│   ├── parse.py          # BeautifulSoup + seletores CSS por fonte
│   ├── dedup.py          # SHA-256 + SQLite (seen_hashes.db)
│   ├── enrich.py         # NER leve (spaCy pt) + tags automáticas
│   ├── alert.py          # Telegram (Markdown) + arquivo daily digest
│   └── pipeline.py       # Orquestrador principal
├── templates/
│   └── sources.yaml      # Configuração de fontes (URL, seletores, frequência, tags)
├── cron/
│   └── scraper-cron.yaml # Definições de cron jobs
└── tests/
    └── test_pipeline.py  # Testes unitários de parse/dedup
```

## Configuração (sources.yaml)

```yaml
sources:
  - id: dou_secao1
    name: "Diário Oficial da União - Seção 1"
    url: "https://www.in.gov.br/leiturajornal?data={date}&secao1"
    schedule: "0 6 * * 1-5"  # 6h dias úteis
    selectors:
      list: "article.article-item"
      title: "h3 a"
      link: "h3 a@href"
      date: "time@datetime"
      content: "div.article-content"
    tags: ["oficial", "legislacao", "federal"]
    keywords: ["pessoa com deficiência", "PcD", "acessibilidade", "inclusão", "cota", "LBI", "Lei Brasileira de Inclusão"]
    enabled: true

  - id: camara_proposicoes
    name: "Câmara dos Deputados - Proposições"
    url: "https://dadosabertos.camara.leg.br/api/v2/proposicoes?dataInicio={date}&itens=100&ordenarPor=id&ordem=DESC"
    schedule: "0 */4 * * *"  # 4 em 4h
    type: "json_api"
    json_path: "$.dados[*]"
    fields:
      id: "id"
      title: "ementa"
      link: "uriProposicao"
      date: "dataApresentacao"
      autor: "autor.nome"
      tipo: "siglaTipo"
      tema: "temas[0].tema"
    tags: ["legislativo", "proposicao", "federal"]
    keywords: ["deficiência", "acessibilidade", "inclusão", "cota", "LBI", "PCd"]
    enabled: true

  - id: senado_proposicoes
    name: "Senado Federal - Proposições"
    url: "https://legis.senado.leg.br/dadosabertos/materia/pesquisa/lista?dataInicial={date}&itens=100"
    schedule: "0 */4 * * *"
    type: "xml_api"
    xpath:
      list: "//Materia"
      id: "IdentificacaoMateria/CodigoMateria"
      title: "IdentificacaoMateria/EmentaMateria"
      link: "IdentificacaoMateria/LinkInteiroTeor"
      date: "IdentificacaoMateria/DataApresentacao"
      autor: "IdentificacaoMateria/Autores/Autor/NomeAutor"
    tags: ["legislativo", "proposicao", "federal"]
    keywords: ["deficiência", "acessibilidade", "inclusão", "cota", "LBI"]
    enabled: true

  - id: mdh_noticias
    name: "Ministério dos Direitos Humanos - Notícias"
    url: "https://www.gov.br/mdh/pt-br/noticias"
    schedule: "0 8 * * *"  # 8h diário
    selectors:
      list: "article.tileItem"
      title: "h2 a"
      link: "h2 a@href"
      date: "span.documentPublished@content"
      content: "div.tileBody"
    tags: ["executivo", "politicas", "direitos-humanos"]
    keywords: ["pessoa com deficiência", "PcD", "acessibilidade", "inclusão", "conade", "conselho"]
    enabled: true

  - id: conade_resolucoes
    name: "CONADE - Resoluções e Deliberações"
    url: "https://www.gov.br/mdh/pt-br/assuntos/pessoa-com-deficiencia/conade/resolucoes"
    schedule: "0 12 * * 1"  # 12h segundas
    selectors:
      list: "article"
      title: "h2 a"
      link: "h2 a@href"
      date: "span.documentPublished@content"
    tags: ["conade", "resolucao", "normativo"]
    keywords: []
    enabled: true

  - id: tse_acessibilidade
    name: "TSE - Acessibilidade Eleitoral"
    url: "https://www.tse.jus.br/eleicoes/acessibilidade"
    schedule: "0 10 * * 1"  # 10h segundas
    selectors:
      list: "div.item-noticia"
      title: "h3 a"
      link: "h3 a@href"
      date: "span.data"
    tags: ["eleitoral", "acessibilidade", "voto"]
    keywords: ["acessibilidade", "urna", "voto", "seção", "mesário", "deficiência"]
    enabled: true

  - id: ibge_sidra_pcd
    name: "IBGE SIDRA - Tabelas PcD"
    url: "https://apisidra.ibge.gov.br/values/t/6579/n1/all/v/9324/p/all/c11255/all"
    schedule: "0 9 1 * *"  # 9h dia 1 mensal
    type: "json_api"
    json_path: "$.result[*]"
    fields:
      periodo: "D1N"
      variavel: "V"
      valor: "Valor"
      classificacao: "C11255"
    tags: ["dados", "estatistica", "censo", "pnad"]
    keywords: []
    enabled: true
```

## Uso

```bash
# Rodar pipeline completo (todas as fontes habilitadas)
cd /opt/data/skills/web-scraping-pipeline
python3 scripts/pipeline.py --all

# Rodar apenas uma fonte
python3 scripts/pipeline.py --source dou_secao1

# Rodar com dry-run (não salva, só mostra o que faria)
python3 scripts/pipeline.py --all --dry-run

# Ver estatísticas
python3 scripts/pipeline.py --stats

# Limpar hashes antigos (>30 dias)
python3 scripts/dedup.py --cleanup --days 30
```

## Integração com Cron Hermes

Adicione ao crontab do Hermes (via `hermes cron create` ou skill `cronjob-python-environment`):

```bash
# Coleta DOU - 6h dias úteis
0 6 * * 1-5 cd /opt/data/skills/web-scraping-pipeline && python3 scripts/pipeline.py --source dou_secao1

# Câmara/Senado - 4 em 4h
0 */4 * * * cd /opt/data/skills/web-scraping-pipeline && python3 scripts/pipeline.py --source camara_proposicoes,senado_proposicoes

# MDH - 8h diário
0 8 * * * cd /opt/data/skills/web-scraping-pipeline && python3 scripts/pipeline.py --source mdh_noticias

# CONADE - 12h segundas
0 12 * * 1 cd /opt/data/skills/web-scraping-pipeline && python3 scripts/pipeline.py --source conade_resolucoes

# TSE - 10h segundas
0 10 * * 1 cd /opt/data/skills/web-scraping-pipeline && python3 scripts/pipeline.py --source tse_acessibilidade

# IBGE - 9h dia 1 mensal
0 9 1 * * cd /opt/data/skills/web-scraping-pipeline && python3 scripts/pipeline.py --source ibge_sidra_pcd

# Digest diário - 18h
0 18 * * * cd /opt/data/skills/web-scraping-pipeline && python3 scripts/alert.py --daily-digest
```

## Dependências

```bash
# No container Hermes (via pip user ou venv)
pip install --user playwright beautifulsoup4 lxml httpx tenacity python-telegram-bot apscheduler sqlite-utils

# Playwright browsers
playwright install chromium

# Opcional: spaCy para NER/tags automáticas
pip install --user spacy
python -m spacy download pt_core_news_sm
```

## Alertas Telegram

Formato da mensagem:
```
📰 **NOVA COLETA: Diário Oficial da União - Seção 1**
📅 2026-07-24 06:15:23
🔍 47 itens processados | 3 novos relevantes

**🎯 PORTARIA MDH Nº 123/2026** — Institui grupo de trabalho para revisão de normas de acessibilidade em transportes
🏷️ Tags: #acessibilidade #transporte #portaria #MDH
🔗 https://www.in.gov.br/web/dou/-/portaria-mdh-n-123-2026

**🎯 DECRETO Nº 11.987/2026** — Altera o Decreto nº 10.098/2019 para ampliar cotas de acessibilidade em edificações públicas
🏷️ Tags: #cotas #edificacoes #decreto #acessibilidade
🔗 https://www.in.gov.br/web/dou/-/decreto-n-11.987-2026
```

## Persistência

- `/opt/data/web-scraping/seen_hashes.db` — SQLite com hashes vistos (dedup)
- `/opt/data/web-scraping/items.jsonl` — Append-only JSONL (um por linha)
- `/opt/data/web-scraping/digest/` — Markdowns diários por data
- `/opt/data/web-scraping/logs/` — Logs de execução (rotacionados 7 dias)

## Tags Automáticas (enrich.py)

Mapeamento de palavras-chave → tags:
- `pessoa com deficiência`, `PcD`, `deficiência` → `#PcD`
- `acessibilidade`, `acessível`, `barreira` → `#acessibilidade`
- `inclusão`, `inclusiva`, `inclusivo` → `#inclusão`
- `cota`, `cotista`, `reserva de vaga` → `#cotas`
- `LBI`, `Lei Brasileira de Inclusão`, `Lei 13.146` → `#LBI`
- `CONADE`, `Conselho Nacional dos Direitos` → `#CONADE`
- `transporte`, `ônibus`, `metrô`, `estação` → `#transporte`
- `educação`, `escola`, `universidade`, `ENEM` → `#educação`
- `trabalho`, `emprego`, `CLT`, `contratação` → `#trabalho`
- `saúde`, `SUS`, `reabilitação`, `ortopedia` → `#saúde`
- `eleitoral`, `voto`, `urna`, `seção`, `mesário` → `#eleitoral`

## Testes

```bash
python3 -m pytest tests/test_pipeline.py -v
```

Cobre:
- Parse de HTML/XML/JSON de cada fonte
- Deduplicação (hash idêntico = skip)
- Extração de campos obrigatórios
- Tagging automático
- Formatação de alerta Telegram
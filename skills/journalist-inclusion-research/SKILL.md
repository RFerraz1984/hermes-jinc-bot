---
name: journalist-inclusion-research
description: "Skill para pesquisa jornalística sobre inclusão e acessibilidade de pessoas com deficiência (PcD) — coleta, triagem e resumo de notícias, dados e políticas no Brasil."
version: 1.1.0
author: Rafael Ferraz / Hermes Agent
license: MIT
platforms: [linux]
prerequisites:
  commands: []
metadata:
  hermes:
    tags: [jornalismo, inclusao, acessibilidade, pcd, pesquisa]
    homepage: https://jornalistainclusivo.com
---

# Journalist Skill — Inclusion Research (Classe)

## Cron Job Best Practices 2026

| Prática | Por que | Exemplo |
|---------|---------|---------|
| **Provider + Model explícitos** | Evita fallback para modelos sem controle de contexto | `provider=groq, model=llama-3.3-70b-versatile` |
| **Filtro de data OBRIGATÓRIO** | Jornalismo factual exige recência | `queries` com `"2026"` explícito + regra "descarte 2023/2024/2025" |
| **Skills vazios em cron jobs** | Evita explosão de context_length com skills padrão | `skills: []` em jobs de pesquisa automatizada |
| **Filtro estrutural de feeds RSS** | Trata struct_time (parsed_dates) corretamente | Função `format_date(entry)` com fallbacks |

## Formatting Dates for RSS Feeds

```python
from time import strftime

def format_date(entry):
    if hasattr(entry, 'date'):
        return strftime('%Y-%m-%d %H:%M:%S', feedparser._parse_date_value(entry.date))
    elif hasattr(entry, 'published_parsed'):
        return strftime('%Y-%m-%d %H:%M:%S', entry.published_parsed)
    elif hasattr(entry, 'updated_parsed'):
        return strftime('%Y-%m-%d %H:%M:%S', entry.updated_parsed)
    return 'Data não disponível'
```


### References

- `references/feeds/date-parsing.md` — Fallback para published_parsed e updated_parsed
- `references/feeds/feedparser-patterns.md` — Tratamento correto de feeds não padronizados

### Templates

- `templates/rss-pipeline.md` — Modelo para cron jobs com fallbacks estruturais

### Scripts

- `scripts/run_feed_parser.sh` — Execução segura com virtualenv isolado
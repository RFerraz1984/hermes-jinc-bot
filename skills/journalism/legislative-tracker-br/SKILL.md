---
name: legislative-tracker-br
version: "1.0.0"
description: Monitoramento automatizado de proposições legislativas (PLs, PLPs, PECs, REQs) na Câmara e Senado sobre PcD, acessibilidade, inclusão, cotas, LBI. Alertas Telegram + dashboard local.
category: journalism
tags: [legislative, congress, brazil, accessibility, disability-rights, monitoring, telegram, cron]
author: Hermes Agent
license: MIT
---

# Legislative Tracker BR — Monitoramento Legislativo PcD

Monitora proposições na Câmara dos Deputados e Senado Federal relacionadas a pessoa com deficiência, acessibilidade, inclusão, cotas, Lei Brasileira de Inclusão (LBI/Lei 13.146).

## Fontes Monitoradas

| Fonte | API/Endpoint | Frequência | Cobertura |
|-------|--------------|------------|-----------|
| **Câmara dos Deputados** | Dados Abertos v2 `/proposicoes` | 4h | PL, PLP, PEC, PDC, REQ, MSC, MSP |
| **Senado Federal** | Dados Abertos `/materia/pesquisa` | 4h | PL, PEC, PFL, REQ, RIC, MSF |
| **Diário Oficial** | DOU Seção 1 (leis sancionadas) | 6h dias úteis | Leis, Decretos, MPs publicadas |

## Palavras-chave Rastreadas

```yaml
keywords:
  high_priority:
    - "pessoa com deficiência"
    - "PcD"
    - "deficiência"
    - "acessibilidade"
    - "inclusão"
    - "inclusiva"
    - "inclusivo"
    - "cota"
    - "cotista"
    - "reserva de vaga"
    - "LBI"
    - "Lei Brasileira de Inclusão"
    - "Lei 13.146"
    - "Decreto 10.098"
    - "CONADE"
    - "Conselho Nacional dos Direitos da Pessoa com Deficiência"
  
  medium_priority:
    - "barreira"
    - "desenho universal"
    - "tecnologia assistiva"
    - "libras"
    - "braille"
    - "audiodescrição"
    - "legendagem"
    - "acesso à informação"
    - "acesso à justiça"
    - "capacitismo"
    - "discriminação por deficiência"
    - "educação inclusiva"
    - "emprego apoiado"
    - "benefício de prestação continuada"
    - "BPC"
    - "LOAS"
  
  thematic:
    transporte: ["transporte", "ônibus", "metrô", "estação", "terminal", "veículo", "frota", "bilhete", "passe livre"]
    educacao: ["educação", "escola", "universidade", "ENEM", "vestibular", "matrícula", "sala de aula", "professor", "AEI"]
    trabalho: ["trabalho", "emprego", "CLT", "contratação", "concurso", "cargo", "estabilidade", "readaptação"]
    saude: ["saúde", "SUS", "reabilitação", "ortopedia", "fisioterapia", "fonoaudiologia", "prótese", "órtese"]
    eleitoral: ["eleitoral", "voto", "urna", "seção", "mesário", "candidato", "campanha", "propaganda"]
    habitacao: ["habitação", "moradia", "casa própria", "financiamento", "MCMV", "acessibilidade arquitetônica"]
    tecnologia: ["tecnologia", "app", "site", "portal", "sistema", "software", "WCAG", "e-MAG"]
```

## Arquitetura

```
/opt/data/skills/legislative-tracker-br/
├── SKILL.md
├── scripts/
│   ├── fetch_camara.py       # API JSON Câmara
│   ├── fetch_senado.py       # API XML Senado
│   ├── fetch_dou.py          # DOU leis sancionadas
│   ├── normalize.py          # Normaliza campos para schema comum
│   ├── score.py              # Score de relevância (0-100)
│   ├── dedup.py              # Dedup por ID oficial + hash conteúdo
│   ├── enrich.py             # Tags temáticas + categoria
│   ├── alert.py              # Telegram + daily digest
│   └── tracker.py            # Orquestrador
├── templates/
│   ├── keywords.yaml         # Palavras-chave + pesos
│   └── templates.yaml        # Templates de alerta Telegram
├── cron/
│   └── tracker-cron.yaml
└── tests/
    └── test_tracker.py
```

## Schema Unificado (Proposição)

```python
@dataclass
class Proposition:
    id_externo: str           # Ex: "PL-1234/2026", "PEC-45/2025"
    casa: str                 # "camara" | "senado"
    tipo: str                 # "PL" | "PLP" | "PEC" | "PDC" | "REQ" | ...
    numero: int
    ano: int
    ementa: str               # Título/resumo oficial
    autor: str
    partido_autor: str
    uf_autor: str
    data_apresentacao: date
    situacao_atual: str       # "Em tramitação", "Aprovada", "Arquivada", "Sancionada"
    ultima_tramitacao: str
    data_ultima_tramitacao: date
    url_oficial: str
    url_texto_inteiro: str
    temas_oficiais: list[str] # Temas da casa
    tags_derivadas: list[str] # Nossas tags (high/medium/thematic)
    score_relevancia: int     # 0-100
    hash_conteudo: str        # SHA-256 para dedup
    criado_em: datetime
    atualizado_em: datetime
```

## Score de Relevância (0-100)

```python
def calculate_score(prop: Proposition) -> int:
    score = 0
    text = f"{prop.ementa} {' '.join(prop.temas_oficiais)}".lower()
    
    # High priority keywords (15 pts each)
    for kw in HIGH_PRIORITY:
        if kw in text:
            score += 15
    
    # Medium priority (8 pts each)
    for kw in MEDIUM_PRIORITY:
        if kw in text:
            score += 8
    
    # Thematic bonuses (5 pts each category matched)
    for cat, kws in THEMATIC.items():
        if any(kw in text for kw in kws):
            score += 5
    
    # Bonus: autor conhecido (deputados/senadores da frente PcD)
    if prop.autor in FRENTE_PCD_AUTHORS:
        score += 10
    
    # Bonus: tramitação recente (<7 dias)
    if (date.today() - prop.data_ultima_tramitacao).days <= 7:
        score += 5
    
    return min(score, 100)
```

## Alertas Telegram

### Alerta Imediato (score ≥ 50)
```
🚨 **ALERTA LEGISLATIVO — ALTA RELEVÂNCIA (87/100)**

**PL 1234/2026** — "Institui o Programa Nacional de Tecnologia Assistiva no SUS"
🏛️ Câmara | Dep. Maria Silva (PT-SP) | Apresentado: 2026-07-20
📋 Situação: Em tramitação (CCJ) | Última: 2026-07-22
🏷️ Tags: #PcD #tecnologia-assistiva #saúde #SUS #LBI
🔗 https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=123456
```

### Digest Diário (18h)
```
📊 **DIGEST LEGISLATIVO PcD — 2026-07-24**

**🔴 ALTA (3)**
• PL 1234/2026 — Tecnologia Assistiva no SUS (87)
• PEC 45/2025 — Cotas em universidades privadas (82)
• REQ 987/2026 — Audiência pública sobre transporte acessível (75)

**🟡 MÉDIA (7)**
• PL 567/2026 — Acessibilidade em apps bancários (58)
• PDC 12/2026 — Susta portaria que reduziu cotas (55)
...

**📈 ESTATÍSTICAS**
Novas hoje: 12 | Relevantes: 10 | Em tramitação ativa: 147
Total monitoradas: 2.847 | Arquivadas este mês: 23
```

## Cron Jobs (Hermes)

```bash
# Câmara/Senado - 4 em 4h
0 */4 * * * cd /opt/data/skills/legislative-tracker-br && python3 scripts/tracker.py --source camara,senado

# DOU - 6h dias úteis (leis sancionadas)
0 6 * * 1-5 cd /opt/data/skills/legislative-tracker-br && python3 scripts/tracker.py --source dou

# Digest diário - 18h
0 18 * * * cd /opt/data/skills/legislative-tracker-br && python3 scripts/alert.py --daily-digest

# Limpeza semanal - domingos 3h
0 3 * * 0 cd /opt/data/skills/legislative-tracker-br && python3 scripts/dedup.py --cleanup --days 90
```

## Persistência

- `/opt/data/legislative-tracker/proposicoes.db` — SQLite (schema unificado + índices)
- `/opt/data/legislative-tracker/alerts.jsonl` — Alertas enviados (dedup)
- `/opt/data/legislative-tracker/digest/` — Markdowns diários
- `/opt/data/legislative-tracker/logs/` — Logs rotacionados

## Dependências

```bash
pip install --user httpx lxml beautifulsoup4 python-telegram-bot apscheduler sqlite-utils tenacity pyyaml
```

## Uso

```bash
# Execução manual completa
cd /opt/data/skills/legislative-tracker-br
python3 scripts/tracker.py --all

# Apenas Câmara
python3 scripts/tracker.py --source camara

# Apenas Senado
python3 scripts/tracker.py --source senado

# Dry-run
python3 scripts/tracker.py --all --dry-run

# Estatísticas
python3 scripts/tracker.py --stats

# Buscar proposições
python3 scripts/tracker.py --search "tecnologia assistiva" --limit 20
```
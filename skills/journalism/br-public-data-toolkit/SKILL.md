---
name: br-public-data-toolkit
version: "1.0.0"
description: Toolkit para acesso, cache e export de dados públicos brasileiros (IBGE/SIDRA, Censo, PNAD, PNS, DATASUS, TSE, Transparência) — pronto para análises de PcD, inclusão, acessibilidade.
category: journalism
tags: [brazil, public-data, ibge, sidra, census, pnad, datasus, tse, transparency, disability-data, csv, parquet, api]
author: Hermes Agent
license: MIT
---

# BR Public Data Toolkit — Dados Públicos Brasileiros para Jornalismo Inclusivo

Acesso unificado, cache local e export padronizado (CSV/Parquet) das principais bases de dados públicos do Brasil, com foco em indicadores de pessoa com deficiência, acessibilidade, inclusão escolar, mercado de trabalho, saúde e representação política.

## Fontes Cobertas

| Fonte | API/Endpoint | Dados PcD/Inclusão | Atualização |
|-------|--------------|-------------------|-------------|
| **IBGE SIDRA** | `https://api.sidra.ibge.gov.br` | Censo 2010/2022, PNAD Contínua, PNS, POF — deficiência, limitação, acessibilidade domiciliar | Trimestral/Anual |
| **IBGE Censo 2022** | Aggregados + microdados (quando liberados) | Deficiência por tipo, idade, sexo, cor, região, domicílio | Decenal |
| **PNAD Contínua** | SIDRA Tabela 6389+ | Mercado de trabalho PcD, rendimento, ocupação, informalidade | Trimestral |
| **PNS (Saúde)** | SIDRA Tabela 6579+ | Deficiência funcional, limitação, uso de serviços, reabilitação | 5 anos |
| **DATASUS/SIH/SIA** | `https://datasus.saude.gov.br` + FTP | Internações/atendimentos PcD, reabilitação, próteses/órteses | Mensal |
| **TSE** | `https://dados.tse.jus.br` | Eleitores PcD, candidatos PcD, seções acessíveis, voto em trânsito | Eleitoral |
| **Portal da Transparência** | `https://api.portaldatransparencia.gov.br` | Convênios/termos PcD, emendas parlamentares, repasses | Diário |
| **Dados.gov.br (CKAN)** | `https://dados.gov.br/api/3` | Catálogo de datasets PcD de ministérios/estados/municípios | Contínuo |
| **INEP/Mec** | Microdados Censo Escolar, Enem, Censo Superior | Matrículas PcD, AEE, acessibilidade escolas/universidades | Anual |
| **MTE/Rais/Caged** | `https://dadosabertos.rais.gov.br` | Admissões/desligamentos PcD, lei de cotas (8213/91) | Anual/Mensal |

## Arquitetura

```
/opt/data/skills/br-public-data-toolkit/
├── SKILL.md
├── scripts/
│   ├── ibge_sidra.py       # Cliente SIDRA (cache + paginação + rate limit)
│   ├── ibge_censo.py       # Censo 2022 agregados + microdados
│   ├── pnad_continua.py    # PNAD Contínua trimestral
│   ├── pns_saude.py        # Pesquisa Nacional de Saúde
│   ├── datasus.py          # SIH/SIA/CNES (FTP + API)
│   ├── tse_eleicoes.py     # Eleitores/candidatos PcD + acessibilidade
│   ├── transparencia.py    # Portal da Transparência (convênios/emendas)
│   ├── inep_educacao.py    # Censo Escolar/Enem/Superior PcD
│   ├── mte_trabalho.py     # RAIS/Caged/Lei de Cotas
│   ├── ckan_catalog.py     # Busca no dados.gov.br
│   ├── cache.py            # Cache local (SQLite + arquivos Parquet)
│   ├── export.py           # Export CSV/Parquet/JSON/Excel
│   ├── validate.py         # Validação de esquema + qualidade
│   └── toolkit.py          # CLI unificado
├── templates/
│   ├── queries.yaml        # Queries SIDRA pré-definidas por tema
│   ├── schemas.yaml        # Schemas de validação (Pydantic)
│   └── exports.yaml        # Config de export (colunas, tipos, particionamento)
├── cron/
│   └── toolkit-cron.yaml
└── tests/
    └── test_toolkit.py
```

## Uso Rápido (CLI)

```bash
cd /opt/data/skills/br-public-data-toolkit

# Listar datasets disponíveis
python3 scripts/toolkit.py list

# IBGE SIDRA: Deficiência por UF (Censo 2022)
python3 scripts/toolkit.py fetch sidra --table 9606 --vars 93,202 --period 2022 --classif 2:all,86:all --output censo2022_deficiencia_uf.parquet

# PNAD Contínua: PcD no mercado de trabalho (último trimestre)
python3 scripts/toolkit.py fetch pnad --vars VD4001,VD4002,VD4003 --classif deficiencia:all --output pnad_pcd_trabalho.parquet

# TSE: Eleitores com deficiência por UF
python3 scripts/toolkit.py fetch tse --dataset eleitores_pcd --output tse_eleitores_pcd.parquet

# DATASUS: Internações PcD (último ano)
python3 scripts/toolkit.py fetch datasus --dataset sih --filter "cid10 like 'Q%' or cid10 like 'G80%'" --output datasus_internacoes_pcd.parquet

# Portal Transparência: Convênios PcD (último mês)
python3 scripts/toolkit.py fetch transparencia --dataset convenios --query "pessoa com deficiência" --output transparencia_convenios_pcd.parquet

# INEP: Escolas com AEE (Atendimento Educacional Especializado)
python3 scripts/toolkit.py fetch inep --dataset censo_escolar --filter "AEE==1" --output inep_escolas_aee.parquet

# Exportar tudo para CSV (para Excel/Tableau)
python3 scripts/toolkit.py export --all --format csv --output-dir /opt/data/exports/pcd_2026-07

# Validar dataset
python3 scripts/toolkit.py validate --file censo2022_deficiencia_uf.parquet --schema censo_deficiencia

# Estatísticas rápidas
python3 scripts/toolkit.py stats --file censo2022_deficiencia_uf.parquet --groupby UF --measure total_pcd
```

## Schemas de Exportação Padronizados

### Censo 2022 — Deficiência
```yaml
# templates/schemas.yaml
censo_deficiencia:
  columns:
    - name: UF
      type: string
      description: "Unidade da Federação (sigla)"
    - name: COD_UF
      type: integer
    - name: TIPO_DEEFICIENCIA
      type: string
      description: "Visual, Auditiva, Física, Intelectual, Múltipla, Não informada"
    - name: SEXO
      type: string
    - name: GRUPO_IDADE
      type: string
    - name: COR_RACA
      type: string
    - name: TOTAL_PESSOAS
      type: integer
    - name: TOTAL_COM_DEEFICIENCIA
      type: integer
    - name: PERCENTUAL
      type: float
    - name: ANO_CENSO
      type: integer
  partition_by: [UF, TIPO_DEEFICIENCIA]
  format: parquet
```

### PNAD Contínua — Mercado de Trabalho PcD
```yaml
pnad_pcd_trabalho:
  columns:
    - name: TRIMESTRE
      type: string
    - name: UF
      type: string
    - name: TIPO_DEEFICIENCIA
      type: string
    - name: OCUPADO
      type: boolean
    - name: DESOCUPADO
      type: boolean
    - name: FORA_FORCA
      type: boolean
    - name: RENDIMENTO_MEDIO
      type: float
    - name: INFORMALIDADE
      type: boolean
    - name: SETOR_ATIVIDADE
      type: string
    - name: OCUPACAO_CBO
      type: string
  partition_by: [TRIMESTRE, UF]
  format: parquet
```

### TSE — Eleitores/Candidatos PcD
```yaml
tse_pcd:
  columns:
    - name: ANO_ELEICAO
      type: integer
    - name: UF
      type: string
    - name: MUNICIPIO
      type: string
    - name: TIPO_ELEITOR
      type: string
      description: "Eleitor | Candidato | Eleito"
    - name: TIPO_DEEFICIENCIA
      type: string
    - name: QTD
      type: integer
    - name: SECAO_ACESSIVEL
      type: boolean
  partition_by: [ANO_ELEICAO, UF]
  format: parquet
```

## Cache Local

```
/opt/data/br-public-data/
├── cache/
│   ├── sidra/           # Respostas JSON brutas (TTL 7 dias)
│   ├── tse/             # CSVs/zip originais
│   ├── datasus/         # DBF/CSV originais
│   └── transparencia/   # JSONs
├── processed/
│   ├── censo2022/
│   ├── pnad/
│   ├── pns/
│   ├── tse/
│   ├── datasus/
│   ├── transparencia/
│   ├── inep/
│   └── mte/
├── exports/             # CSVs/Parquets prontos para análise
└── metadata/
    ├── sources.yaml     # Última atualização por fonte
    └── schemas/         # Schemas Pydantic compilados
```

## Queries SIDRA Pré-definidas (templates/queries.yaml)

```yaml
queries:
  censo2022_deficiencia_uf:
    table: 9606
    description: "Pessoas com deficiência por tipo, sexo, idade, cor - UF"
    variables: [93, 202]  # Total, Percentual
    classifications:
      - id: 2    # Tipo de deficiência
        values: "all"
      - id: 86   # Sexo
        values: "all"
      - id: 227  # Idade
        values: "all"
      - id: 292  # Cor/raça
        values: "all"
    period: "2022"
    geo: "1"  # UF

  pnad_pcd_trabalho:
    table: 6389
    description: "Pessoas com deficiência no mercado de trabalho - Brasil/UF"
    variables: [93, 6941, 6942, 6943]  # Total, Ocupado, Desocupado, Fora da força
    classifications:
      - id: 11046  # Tipo de deficiência
        values: "all"
      - id: 227    # Idade
        values: "all"
    period: "last"  # Último trimestre disponível
    geo: "1"

  pns_limitacao_funcional:
    table: 6579
    description: "Limitação funcional por grau - Brasil/UF"
    variables: [93, 6578]  # Total, Grau de limitação
    classifications:
      - id: 11046
        values: "all"
    period: "2019"
    geo: "1"
```

## Cron Jobs (Hermes)

```bash
# SIDRA/Censo - mensal (1º dia, 6h)
0 6 1 * * cd /opt/data/skills/br-public-data-toolkit && python3 scripts/toolkit.py fetch sidra --all-cached --update

# PNAD Contínua - trimestral (dia 15 do mês seguinte ao trimestre, 8h)
0 8 15 1,4,7,10 * cd /opt/data/skills/br-public-data-toolkit && python3 scripts/toolkit.py fetch pnad --latest

# TSE - pós-eleição + atualização mensal de eleitores
0 9 1 * * cd /opt/data/skills/br-public-data-toolkit && python3 scripts/toolkit.py fetch tse --update

# DATASUS - mensal (dia 5, 7h)
0 7 5 * * cd /opt/data/skills/br-public-data-toolkit && python3 scripts/toolkit.py fetch datasus --latest-month

# Portal Transparência - semanal (segundas 9h)
0 9 * * 1 cd /opt/data/skills/br-public-data-toolkit && python3 scripts/toolkit.py fetch transparencia --last-week

# INEP Censo Escolar - anual (março, quando liberado)
0 10 1 3 * cd /opt/data/skills/br-public-data-toolkit && python3 scripts/toolkit.py fetch inep --latest

# Export consolidado mensal (dia 2, 10h)
0 10 2 * * cd /opt/data/skills/br-public-data-toolkit && python3 scripts/toolkit.py export --all --format parquet --output-dir /opt/data/exports/pcd_$(date +%Y-%m)

# Validação semanal (sábados 4h)
0 4 * * 6 cd /opt/data/skills/br-public-data-toolkit && python3 scripts/toolkit.py validate --all
```

## Dependências

```bash
pip install --user \
  httpx \
  beautifulsoup4 \
  lxml \
  pandas \
  pyarrow \
  pydantic \
  pydantic-settings \
  python-dotenv \
  tenacity \
  apscheduler \
  sqlite-utils \
  py7zr \
  rarfile \
  python-telegram-bot \
  pyyaml \
  tqdm
```

## Exemplos de Análise Pronta

```python
# Notebook: pcd_dashboard.ipynb
import pandas as pd

# 1. Censo 2022: Deficiência por UF + tipo
censo = pd.read_parquet("/opt/data/br-public-data/processed/censo2022/deficiencia_uf.parquet")
print(censo.groupby("TIPO_DEEFICIENCIA")["TOTAL_COM_DEEFICIENCIA"].sum().sort_values(ascending=False))

# 2. PNAD: Taxa de desocupação PcD vs geral
pnad = pd.read_parquet("/opt/data/br-public-data/processed/pnad/pcd_trabalho.parquet")
taxa_pcd = pnad[pnad["TIPO_DEEFICIENCIA"]!="Sem deficiência"]["DESOCUPADO"].mean()
taxa_geral = pnad[pnad["TIPO_DEEFICIENCIA"]=="Sem deficiência"]["DESOCUPADO"].mean()
print(f"Desocupação PcD: {taxa_pcd:.1%} | Geral: {taxa_geral:.1%}")

# 3. TSE: % seções acessíveis por UF
tse = pd.read_parquet("/opt/data/br-public-data/processed/tse/secoes_acessiveis.parquet")
print(tse.groupby("UF")["SECAO_ACESSIVEL"].mean().sort_values(ascending=False) * 100)

# 4. DATASUS: Internações por CID-10 capítulo (Q00-Q99 = malformações/congenitas)
datasus = pd.read_parquet("/opt/data/br-public-data/processed/datasus/sih_pcd.parquet")
print(datasus["CAPITULO_CID10"].value_counts().head(10))

# 5. INEP: % escolas com AEE por rede
inep = pd.read_parquet("/opt/data/br-public-data/processed/inep/escolas_aee.parquet")
print(inep.groupby("REDE")["AEE"].mean() * 100)
```

## Alertas Telegram (quando houver atualização)

```
📊 **ATUALIZAÇÃO: DADOS PÚBLICOS PcD**

✅ **IBGE SIDRA** — PNAD Contínua Q2/2026 disponível
   • 8.9M PcD ocupadas (↑ 2.3% vs Q1)
   • Taxa desocupação PcD: 9.1% (vs 6.8% geral)
   • Rendimento médio PcD: R$ 2.340 (74% da média geral)

✅ **TSE** — Eleitores PcD atualizados (jul/2026)
   • 1.4M eleitores com deficiência cadastrados
   • 87% seções com acessibilidade (meta 100%)

✅ **DATASUS** — SIH junho/2026
   • 12.4k internações PcD (cid Q/G80/F70-F79)
   • Top 3: G80 (paralisia cerebral), Q90 (Down), F71 (intelectual moderada)

📁 Exports atualizados: /opt/data/exports/pcd_2026-07/
```
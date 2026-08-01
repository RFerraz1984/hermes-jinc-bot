---
name: jinc-financial-plan
description: Plano de independência financeira para Rafael Ferraz Carpi (Jornalista Inclusivo) + automações Hermes para execução
category: journalism
version: "1.0.0"
author: Hermes Agent
tags:
  - financial-planning
  - accessibility
  - journalism
  - automation
  - income-diversification
---

# Skill: jinc-financial-plan

**Propósito:** Operacionalizar o Plano de Independência Financeira do Rafael (Jornalista Inclusivo / Dataverso PcD) através de automações Hermes, templates e checklists reutilizáveis.

## Estrutura do Plano (Resumo)

| Pilar | Meta 6 meses | Automação Hermes |
|-------|--------------|------------------|
| 1. Consultoria Acessibilidade (Retainers) | R$ 8-15k/mês | `proposal-gen`, `audit-report-gen`, `lead-enrichment` |
| 2. Plataforma JINC + Dataverso (Assinaturas/Patrocínio) | R$ 3-8k/mês | `newsletter-draft`, `dataverso-sync`, `media-kit-gen` |
| 3. Testes Usabilidade PcD | R$ 2-5k/mês | `test-report-gen`, `tester-crm` |
| 4. Produtos Digitais (IA + Acessibilidade) | R$ 1-3k/mês passivo | `product-builder`, `checkout-automation` |

## Automações Incluídas (Scripts / Prompts)

### 1. `newsletter-draft`
**Input:** Tópico / URL / notas brutas
**Output:** Rascunho newsletter acessível (HTML + texto plano) com:
- Estrutura semântica (h1-h3)
- Alt text para imagens sugerido
- Linguagem simples (Flesch-Kincaid PT-BR < 60)
- Links com texto descritivo
- Versão PDF/UA opcional
**Salva em:** Beehiiv/Substack via API ou arquivo local

### 2. `audit-report-gen`
**Input:** Checklist WCAG preenchido (JSON) + achados
**Output:** Relatório Word (.docx) + PDF/UA válido com:
- Sumário executivo
- Detalhamento por critério WCAG
- Roadmap priorizado (crítico/alto/médio/baixo)
- Estimativa esforço correção
- Modelo de validação pós-correção

### 3. `proposal-gen`
**Input:** Perfil cliente (Notion CRM) + pacote escolhido
**Output:** Proposta comercial PDF/UA + email personalizado
**Templates:** 4 pacotes (Auditoria, Retainer, Treinamento, Dados PcD)

### 4. `lead-enrichment`
**Input:** LinkedIn URL ou email
**Output:** Dados enriquecidos no Notion CRM:
- Cargo, empresa, tamanho, tech stack
- Possíveis dores acessibilidade (baseado em setor)
- Icebreaker personalizado (conexão PcD, artigo recente, etc.)

### 5. `dataverso-sync`
**Input:** CKAN API (dados.dataverso.org)
**Output:** 
- Dataset cards HTML acessíveis (para site estático)
- CSV/JSON normalizados
- Sitemap.xml atualizado
- Feed RSS de novos datasets

### 6. `invoice-gen`
**Input:** Projeto fechado (Notion) + dados fiscais
**Output:** NFS-e JSON (padrão nacional) + email cliente + backup Notion

### 7. `test-report-gen`
**Input:** Gravação teste + anotações moderador + feedback testadores
**Output:** Relatório acessível (HTML + PDF/UA) com:
- Perfil testadores (tech assistiva, deficiência)
- Tarefas, sucessos, falhas, citações
- Recomendações priorizadas
- Evidências (timestamps, screenshots com alt text)

### 8. `product-builder`
**Input:** Conceito produto (markdown)
**Output:** Estrutura completa:
- Landing page acessível (Astro/HTML estático)
- Checkout Stripe/Asaas configurado
- Email sequence (boas-vindas, onboarding, upsell)
- Assets: checklist, templates, guia

## Templates Disponíveis (em `/references/templates/`)

- `proposta-consultoria-acessibilidade.md`
- `relatorio-auditoria-wcag.docx` (modelo)
- `newsletter-edicao-template.html`
- `media-kit-jinc.pdf`
- `checklist-wcag-redacoes.csv`
- `ficha-testador-pcd.md`
- `contrato-retainer-modelo.docx`

## Como Usar

```bash
# Ver plano completo
hermes skill view jinc-financial-plan

# Rodar automação newsletter
hermes run skill:jinc-financial-plan:newsletter-draft --topic "WCAG 2.2 - o que muda para redações"

# Gerar proposta para lead
hermes run skill:jinc-financial-plan:proposal-gen --lead "linkedin.com/in/gestor-diversidade-xyz" --pacote "retainer"

# Sincronizar Dataverso
hermes run skill:jinc-financial-plan:dataverso-sync

# Criar skill a partir deste plano (já feito)
# hermes skill create jinc-financial-plan --category journalism
```

## Cron Jobs Sugeridos (via `hermes cron create`)

| Job | Schedule | Skill | Prompt |
|-----|----------|-------|--------|
| `jinc-weekly-newsletter` | `0 9 * * 1` (seg 9h) | jinc-financial-plan | "Gere rascunho newsletter semanal: 1 artigo principal (acessibilidade), 1 dado Dataverso, 1 dica prática, 1 call-to-action. Salve em /opt/data/newsletter/drafts/week-{{date}}.md" |
| `jinc-monthly-metrics` | `0 9 1 * *` (dia 1, 9h) | jinc-financial-plan | "Compile métricas do mês: MRR por pilar, pipeline consultoria, assinantes newsletter, testes realizados, produtos vendidos. Salve em /opt/data/plans/metrics/{{date}}.md e envie resumo por email." |
| `jinc-dataverso-sync` | `0 3 * * *` (diário 3h) | jinc-financial-plan | "Execute dataverso-sync completo. Atualize site estático e sitemap." |
| `jinc-lead-outreach` | `0 10 * * 2,4` (ter/qui 10h) | jinc-financial-plan | "Para 5 leads no CRM status 'novo': enriqueça, gere icebreaker, salve rascunho email no Notion. Notifique no Telegram." |

## Checklist Semanal (Executar 2ª feira 9h)

- [ ] Revisar pipeline consultoria (Notion CRM) — mover cards, agendar calls
- [ ] Verificar métricas newsletter (abertos, cliques, churn, novos pagos)
- [ ] Conferir faturamento PJ vs. pró-labore vs. reserva (planilha/contador)
- [ ] Rodar `dataverso-sync` manual se automático falhou
- [ ] Produzir 1 conteúdo "evergreen" para produto digital (checklist, template, aula)
- [ ] 1 call estratégica (lead quente, parceiro, conector)
- [ ] Verificar saúde tech assistiva (eye-tracking, voice, switch) — 15 min teste
- [ ] Atualizar dashboard métricas (Notion / arquivo local)

## Integração com Outras Skills

- `jinc-gmail-triagem` → leads de email para CRM
- `social-media-multiplatform` → distribuição conteúdo newsletter/produtos
- `hermes-umbrel-operations` → saúde do sistema, logs, backup
- `rag-pipeline` → indexar conteúdos JINC/Dataverso para RAG local

## Arquivos de Estado (Persistentes em `/opt/data/`)

| Arquivo | Descrição |
|---------|-----------|
| `/opt/data/plans/plano-independencia-financeira-rafael.md` | Plano mestre (este documento fonte) |
| `/opt/data/jinc-state/crm-leads.json` | Pipeline leads (Notion sync) |
| `/opt/data/jinc-state/metrics-history.json` | Histórico métricas mensais |
| `/opt/data/jinc-state/newsletter-queue.json` | Fila edições (tópico, status, data) |
| `/opt/data/jinc-state/product-ideas.md` | Backlog produtos digitais |

## Notas de Manutenção

- **Atualize o plano mestre** a cada sprint (2 semanas) — edite o .md e rode `hermes skill patch jinc-financial-plan` se mudar automações
- **Teste acessibilidade** de todo output gerado (axe-core, PAC 3, leitor de tela)
- **Backup semanal** de `/opt/data/jinc-state/` e `/opt/data/plans/`
- **Contador no loop:** compartilhe métricas financeiras mensais para ajuste pró-labore/distribuição

## Contato / Contexto do Usuário

- **Usuário:** Rafael Ferraz Carpi (tetraplégico, 42 anos, jornalista, ativista PcD)
- **Contato:** editor@jornalistainclusivo.com / (11) 99866-4939
- **Sites:** jornalistainclusivo.com, jornalistainclusivo.com.br, pcd.dataverso.org, dados.dataverso.org, pcd.chat
- **LinkedIn:** linkedin.com/in/rafaelferrazcarpi
- **Tech:** Hermes Agent no Umbrel (local), eye-tracking / voice control, Ollama local
- **Benefícios:** Verificar status BPC/LOAS com contador antes de faturar PJ
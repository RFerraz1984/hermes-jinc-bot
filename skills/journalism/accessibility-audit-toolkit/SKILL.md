---
name: accessibility-audit-toolkit
version: "1.0.0"
description: Kit de auditoria de acessibilidade digital (WCAG 2.1/2.2, e-MAG, EN 301 549) — testes automatizados, manuais, relatórios e monitoramento contínuo para portais governamentais, sites de notícias e plataformas públicas.
category: journalism
tags: [accessibility, wcag, e-mag, audit, testing, axe, pa11y, lighthouse, screen-reader, keyboard, contrast, journalism, compliance]
author: Hermes Agent
license: MIT
---

# Accessibility Audit Toolkit — Auditoria de Acessibilidade Digital

Kit completo para auditoria de acessibilidade (WCAG 2.1 AA, WCAG 2.2 AA, e-MAG 3.1, EN 301 549) com testes automatizados, checklist manual, relatórios executivos e monitoramento contínuo — focado em portais governamentais, sites de notícias e plataformas de interesse público.

## Objetivo

- Auditar sites de governo (GOV.BR, portais estaduais/municipais), veículos de imprensa, plataformas de serviços públicos
- Gerar relatórios técnicos + executivos (para gestores, jurídico, imprensa)
- Monitorar regressões (CI/CD + cron jobs)
- Evidenciar violações de lei (LBI Art. 63, Decreto 10.098/2019, Marco Civil Art. 9º)

## Normas Cobertas

| Norma | Versão | Nível | Escopo |
|-------|--------|-------|--------|
| **WCAG** | 2.2 | AA | Internacional (W3C) |
| **e-MAG** | 3.1 | — | Governo Federal Brasil |
| **EN 301 549** | 3.2.1 | — | Compras públicas EU (referência) |
| **ISO 40500** | 2012 | — | Norma ISO baseada no WCAG 2.0 |

## Arquitetura

```
/opt/data/skills/accessibility-audit-toolkit/
├── SKILL.md
├── scripts/
│   ├── axe_cli.py          # Wrapper axe-core (Playwright + axe)
│   ├── pa11y_cli.py        # Wrapper pa11y (multi-página)
│   ├── lighthouse_cli.py   # Lighthouse CI (performance + a11y)
│   ├── contrast_check.py   # Verificador de contraste (WCAG AA/AAA)
│   ├── keyboard_nav.py     # Teste de navegação por teclado (Tab order, focus visible)
│   ├── screen_reader.py    # Teste com NVDA/JAWS/Orca (via speech-dispatcher)
│   ├── emag_checklist.py   # Checklist e-MAG 3.1 (itens obrigatórios)
│   ├── wcag_report.py      # Gerador de relatório unificado (JSON + HTML + PDF)
│   ├── diff_report.py      # Comparação entre auditorias (regressão)
│   ├── crawl_site.py       # Descobrir URLs (sitemap + crawl limitado)
│   └── audit.py            # Orquestrador principal
├── templates/
│   ├── wcag_criteria.yaml  # Critérios WCAG 2.2 + mapeamento e-MAG
│   ├── report_template.html
│   ├── report_executive.md
│   ├── report_technical.md
│   └── checklist_emag.md
├── cron/
│   └── audit-cron.yaml
└── tests/
    └── test_audit.py
```

## Uso Rápido

```bash
cd /opt/data/skills/accessibility-audit-toolkit

# Auditoria completa de um site (auto + checklist manual)
python3 scripts/audit.py --url https://www.gov.br/pt-br --depth 3 --output /opt/data/audits/govbr_2026-07

# Apenas testes automatizados (axe + pa11y + lighthouse)
python3 scripts/audit.py --url https://www.planalto.gov.br --auto-only --output /opt/data/audits/planalto_auto

# Apenas checklist e-MAG (manual)
python3 scripts/emag_checklist.py --url https://www.saude.gov.br --output /opt/data/audits/saude_emag

# Verificar contraste de uma página específica
python3 scripts/contrast_check.py --url https://www.camara.leg.br --threshold AA --output /opt/data/audits/camara_contrast

# Teste de navegação por teclado
python3 scripts/keyboard_nav.py --url https://www.senado.leg.br --output /opt/data/audits/senado_keyboard

# Comparar duas auditorias (regressão)
python3 scripts/diff_report.py --before /opt/data/audits/govbr_2026-06 --after /opt/data/audits/govbr_2026-07 --output /opt/data/audits/govbr_diff_jul
```

## Critérios WCAG 2.2 + Mapeamento e-MAG

```yaml
# templates/wcag_criteria.yaml
criteria:
  1.1.1:
    name: "Conteúdo Não-Textual"
    level: A
    emag: "Item 1.1"
    description: "Todo conteúdo não-textual tem alternativa textual equivalente"
    automated: true  # axe detecta img sem alt, svg sem title
    test: "axe: image-alt, svg-img-alt"
  
  1.2.1:
    name: "Apenas Áudio e Apenas Vídeo (Pré-gravado)"
    level: A
    emag: "Item 1.2"
    automated: false
    manual_test: "Verificar transcrição/legendas em áudio/vídeo isolados"
  
  1.3.1:
    name: "Informação e Relacionamentos"
    level: A
    emag: "Item 1.3"
    automated: true
    test: "axe: label, table-headers, landmark-one-main, region"
  
  1.4.3:
    name: "Contraste (Mínimo)"
    level: AA
    emag: "Item 1.4"
    automated: true
    test: "axe: color-contrast"
    threshold: 4.5  # normal text
  
  1.4.11:
    name: "Contraste de Componentes Não-Textuais"
    level: AA
    emag: "Item 1.5"
    automated: true
    test: "axe: color-contrast"  # UI components
    threshold: 3.0
  
  2.1.1:
    name: "Teclado"
    level: A
    emag: "Item 2.1"
    automated: false
    manual_test: "Tab por toda a página — todos os elementos interativos acessíveis e operáveis"
  
  2.1.2:
    name: "Sem Armadilha de Teclado"
    level: A
    automated: true
    test: "axe: keyboard-trap"
  
  2.4.1:
    name: "Blocos de Ignorar"
    level: A
    emag: "Item 2.2"
    automated: true
    test: "axe: skip-link, bypass-blocks"
  
  2.4.3:
    name: "Ordem de Foco"
    level: A
    automated: false
    manual_test: "Tab order lógico (visual = DOM order)"
  
  2.4.6:
    name: "Cabeçalhos e Rótulos"
    level: AA
    emag: "Item 2.3"
    automated: true
    test: "axe: heading-order, label, aria-required-attr"
  
  2.4.7:
    name: "Foco Visível"
    level: AA
    emag: "Item 2.4"
    automated: true
    test: "axe: focus-visible, focus-order"
  
  2.5.3:
    name: "Rótulo no Nome"
    level: A
    automated: true
    test: "axe: label-in-name"
  
  3.1.1:
    name: "Idioma da Página"
    level: A
    emag: "Item 3.1"
    automated: true
    test: "axe: html-has-lang, html-lang-valid"
  
  3.2.1:
    name: "No Foco"
    level: A
    automated: true
    test: "axe: onfocus"
  
  3.3.1:
    name: "Identificação de Erros"
    level: A
    emag: "Item 3.2"
    automated: true
    test: "axe: error-message, form-field"
  
  4.1.1:
    name: "Processamento"
    level: A
    automated: true
    test: "axe: duplicate-id, duplicate-id-active, duplicate-id-aria"
  
  4.1.2:
    name: "Nome, Função, Valor"
    level: A
    emag: "Item 4.1"
    automated: true
    test: "axe: aria-allowed-attr, aria-required-attr, aria-valid-attr-value"
  
  # WCAG 2.2 novos
  2.4.11:
    name: "Foco Não Encoberto (Mínimo)"
    level: AA
    automated: false
    manual_test: "Elemento focado não totalmente encoberto por conteúdo sticky/overlay"
  
  2.5.7:
    name: "Movimentos de Arrastar"
    level: AA
    automated: false
    manual_test: "Funcionalidade de arrastar tem alternativa por ponto único"
  
  3.2.6:
    name: "Ajuda Consistente"
    level: A
    automated: true
    test: "axe: consistent-help"
  
  3.3.7:
    name: "Entrada Redundante"
    level: A
    automated: false
    manual_test: "Não pedir mesma informação duas vezes no mesmo processo"
```

## Checklist e-MAG 3.1 (Obrigatórios)

```markdown
# templates/checklist_emag.md

## 1. Alternativas Textuais
- [ ] 1.1 Imagens com `alt` relevante (não "imagem", "figura")
- [ ] 1.2 Gráficos/complexos com descrição longa (`longdesc` ou texto adjacente)
- [ ] 1.3 CAPTCHA com alternativa acessível

## 2. Tempo e Navegação
- [ ] 2.1 "Pular para conteúdo principal" (skip link) visível no foco
- [ ] 2.2 Ordem de tabulação lógica
- [ ] 2.3 Foco visível em todos os elementos interativos
- [ ] 2.4 Sem armadilhas de teclado (modais, carrosséis)
- [ ] 2.5 Tempo ajustável (auto-refresh, timeouts)

## 3. Legibilidade e Compreensão
- [ ] 3.1 Idioma definido (`lang="pt-br"`)
- [ ] 3.2 Mudanças de idioma marcadas (`lang="en"`)
- [ ] 3.3 Abreviações/siglas com expansão (`<abbr title="...">`)
- [ ] 3.4 Nível de leitura adequado (português claro)

## 4. Previsibilidade e Consistência
- [ ] 4.1 Navegação consistente (mesma ordem, mesmo design)
- [ ] 4.2 Identificação consistente (mesmo rótulo = mesma função)
- [ ] 4.3 Mudança só sob solicitação (não auto-redirect)

## 5. Ajuda à Entrada de Dados
- [ ] 5.1 Rótulos associados (`<label for>` ou `aria-label`)
- [ ] 5.2 Instruções claras antes dos campos
- [ ] 5.3 Erros identificados + descritos + sugestão de correção
- [ ] 5.4 Prevenção de erros graves (confirmação, revisão, desfazer)

## 6. Compatibilidade
- [ ] 6.1 HTML válido (W3C validator)
- [ ] 6.2 ARIA usado corretamente (não sobrescrever semântica nativa)
- [ ] 6.3 Nome/função/valor expostos (4.1.2)

## 7. Específicos GOV.BR
- [ ] 7.1 Barra de identidade GOV.BR funcional
- [ ] 7.2 Rodapé padronizado com links de acessibilidade
- [ ] 7.3 Mapa do site acessível
- [ ] 7.4 Declaração de acessibilidade pública (link no rodapé)
- [ ] 7.5 Canal de relato de barreiras (formulário/e-mail)
```

## Relatório Unificado (JSON)

```json
{
  "audit_id": "govbr_2026-07-24_14-30",
  "url": "https://www.gov.br/pt-br",
  "timestamp": "2026-07-24T14:30:00-03:00",
  "tools": {
    "axe_version": "4.8.2",
    "pa11y_version": "6.2.3",
    "lighthouse_version": "11.5.0",
    "wcag_version": "2.2",
    "emag_version": "3.1"
  },
  "scope": {
    "pages_crawled": 47,
    "pages_audited": 47,
    "depth": 3,
    "excluded": ["login", "admin", "api"]
  },
  "summary": {
    "total_violations": 234,
    "by_level": { "A": 89, "AA": 112, "AAA": 33 },
    "by_tool": { "axe": 156, "pa11y": 67, "lighthouse": 11 },
    "emag_coverage": 0.78,
    "pages_compliant_aa": 12,
    "pages_non_compliant": 35
  },
  "violations": [
    {
      "id": "color-contrast",
      "wcag": "1.4.3",
      "level": "AA",
      "emag": "1.4",
      "impact": "serious",
      "description": "Contraste insuficiente: 3.2:1 (mínimo 4.5:1)",
      "help": "https://dequeuniversity.com/rules/axe/4.8/color-contrast",
      "nodes": 23,
      "pages": [
        { "url": "https://www.gov.br/pt-br", "count": 5, "selector": ".btn-secondary" },
        { "url": "https://www.gov.br/pt-br/servicos", "count": 3, "selector": "footer a" }
      ]
    }
  ],
  "manual_checks": [
    {
      "wcag": "2.1.1",
      "emag": "2.1",
      "page": "https://www.gov.br/pt-br/servicos",
      "status": "fail",
      "evidence": "Modal de login prende foco — Esc não fecha, Tab não sai",
      "severity": "critical"
    }
  ],
  "emag_checklist": {
    "total_items": 42,
    "passed": 28,
    "failed": 11,
    "na": 3,
    "items": [
      { "id": "2.1", "description": "Skip link visível no foco", "status": "pass", "evidence": "Skip link aparece no 1º Tab" },
      { "id": "2.4", "description": "Foco visível em todos elementos", "status": "fail", "evidence": "Botões .btn-ghost sem outline no :focus" }
    ]
  }
}
```

## Relatório Executivo (Markdown)

```markdown
# 📋 Relatório de Auditoria de Acessibilidade — GOV.BR
**Data:** 24/07/2026 | **Auditor:** Hermes Agent (Jornalista Inclusivo)  
**Normas:** WCAG 2.2 AA + e-MAG 3.1 | **Ferramentas:** axe 4.8, pa11y 6.2, Lighthouse 11.5

---

## 🎯 Resumo Executivo

| Métrica | Valor | Status |
|---------|-------|--------|
| Páginas auditadas | 47 | ✅ |
| Violações totais | 234 | 🔴 |
| Críticas (impacto critical/serious) | 67 | 🔴 |
| Conformidade WCAG 2.2 AA | 25% | 🔴 |
| Cobertura e-MAG 3.1 | 78% | 🟡 |

**Principais riscos jurídicos:**
1. **LBI Art. 63 / Decreto 10.098** — Falhas de contraste (1.4.3) e foco visível (2.4.7) em 35 páginas
2. **Marco Civil Art. 9º** — Armadilha de teclado em modal de login (2.1.2)
3. **Decreto 5.296/2004** — Ausência de skip link em 12 páginas de serviços

---

## 📊 Top 5 Violações por Impacto

| Critério | WCAG | Nível | Páginas | Impacto | Ajuste |
|----------|------|-------|---------|----------|
| Contraste texto | 1.4.3 | AA | 35 | Ajustar cores `.btn-secondary`, `footer a` para 4.5:1 |
| Foco visível | 2.4.7 | AA | 28 | Adicionar `:focus-visible { outline: 3px solid #005EA2 }` |
| Skip link | 2.4.1 | A | 12 | Incluir `<a href="#main" class="skip-link">Pular para conteúdo</a>` |
| Rótulos formulário | 3.3.2 | A | 19 | Associar `<label for>` ou `aria-label` em inputs sem label |
| Ordem de cabeçalhos | 1.3.1 | A | 15 | Corrigir hierarquia h1→h2→h3 (pular níveis) |

---

## ✅ Checklist e-MAG 3.1 (Itens Obrigatórios)

| Item | Descrição | Status | Evidência |
|------|-----------|--------|-----------|
| 1.1 | Alternativas textuais | ✅ | 94% imgs com alt relevante |
| 2.1 | Skip link | ❌ | Ausente em 12/47 páginas |
| 2.2 | Ordem de tab | ⚠️ | 3 páginas com ordem ilógica |
| 2.3 | Foco visível | ❌ | 28 páginas sem outline |
| 2.4 | Sem armadilha teclado | ❌ | Modal login prende foco |
| 3.1 | Idioma da página | ✅ | `lang="pt-br"` em todas |
| 4.1 | HTML válido | ⚠️ | 12 erros W3C (attrs obsoletos) |
| 7.1 | Barra GOV.BR | ✅ | Funcional |
| 7.4 | Declaração acessibilidade | ⚠️ | Link existe mas página 404 |

---

## 📋 Plano de Ação Prioritário

| Prioridade | Ação | Responsável | Prazo | Critério |
|------------|------|-------------|-------|----------|
| 🔴 **Crítica** | Corrigir armadilha de teclado no modal login | Dev Frontend | 48h | 2.1.2, 2.1.1 |
| 🔴 **Crítica** | Implementar skip link global | Dev Frontend | 72h | 2.4.1, e-MAG 2.1 |
| 🔴 **Crítica** | Corrigir contraste (botões, footer) | Design System | 5 dias | 1.4.3, e-MAG 1.4 |
| 🟠 **Alta** | Foco visível global (CSS) | Dev Frontend | 5 dias | 2.4.7, e-MAG 2.4 |
| 🟠 **Alta** | Rótulos em formulários de serviços | Dev Backend | 10 dias | 3.3.2, e-MAG 5.1 |
| 🟡 **Média** | Corrigir ordem de cabeçalhos | Content/Dev | 15 dias | 1.3.1 |
| 🟡 **Média** | Declaração de acessibilidade (página 404) | Jurídico/Comms | 10 dias | e-MAG 7.4 |
| 🟢 **Baixa** | HTML válido (W3C) | Dev Frontend | 30 dias | 4.1.1 |

---

## 📎 Anexos
- `govbr_2026-07-24_technical.json` — Dados completos para desenvolvedores
- `govbr_2026-07-24_emag_checklist.md` — Checklist detalhado
- `govbr_2026-07-24_diff_vs_jun.md` — Regressões vs auditoria anterior
- `screenshots/` — Evidências visuais (antes/depois)
```

## Monitoramento Contínuo (Cron)

```bash
# Auditoria semanal completa (segundas 2h)
0 2 * * 1 cd /opt/data/skills/accessibility-audit-toolkit && python3 scripts/audit.py --url https://www.gov.br/pt-br --depth 3 --output /opt/data/audits/govbr_weekly_$(date +%Y-%m-%d)

# Auditoria diária só páginas críticas (serviços, login, formulários)
0 6 * * * cd /opt/data/skills/accessibility-audit-toolkit && python3 scripts/audit.py --url-list /opt/data/audit/critical_urls.txt --auto-only --output /opt/data/audits/govbr_daily_$(date +%Y-%m-%d)

# Comparação semanal (regressão)
0 4 * * 2 cd /opt/data/skills/accessibility-audit-toolkit && python3 scripts/diff_report.py --before /opt/data/audits/govbr_weekly_$(date -d '7 days ago' +%Y-%m-%d) --after /opt/data/audits/govbr_weekly_$(date +%Y-%m-%d) --output /opt/data/audits/govbr_regression_$(date +%Y-%m-%d)

# Alerta Telegram se regressão crítica
# (integrar no diff_report.py --alert-webhook)
```

## Dependências

```bash
# Node (para axe-cli, pa11y, lighthouse)
npm install -g @axe-core/cli pa11y @lhci/cli

# Python
pip install --user \
  playwright \
  beautifulsoup4 \
  lxml \
  python-telegram-bot \
  apscheduler \
  pyyaml \
  jinja2 \
  weasyprint \
  pandas \
  tqdm

# Playwright browsers
playwright install chromium firefox webkit

# Opcional: NVDA (Windows) / Orca (Linux) para teste real de leitor de tela
# Opcional: speech-dispatcher + espeak-ng para TTS automatizado
```

## Integração com CI/CD (GitHub Actions / GitLab CI)

```yaml
# .github/workflows/accessibility.yml
name: Accessibility Audit
on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 2 * * 1'  # weekly

jobs:
  a11y:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - run: npm install -g @axe-core/cli pa11y @lhci/cli
      - name: Audit staging
        run: |
          python3 scripts/audit.py --url https://staging.gov.br --auto-only --output /tmp/audit
      - name: Compare with baseline
        run: |
          python3 scripts/diff_report.py --before /opt/data/baseline --after /tmp/audit --fail-on-regression
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: a11y-report
          path: /tmp/audit/*.json
      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('/tmp/audit/audit.json'));
            const summary = `## ♿ Accessibility Audit\nViolations: ${report.summary.total_violations} (Critical: ${report.summary.by_level.A || 0})`;
            github.rest.issues.createComment({ issue_number: context.issue.number, owner: context.repo.owner, repo: context.repo.repo, body: summary });
```

## Testes

```bash
python3 -m pytest tests/test_audit.py -v
```

Cobre:
- axe/pa11y/lighthouse output parsing
- WCAG criteria mapping
- e-MAG checklist parsing
- Diff report accuracy
- Report generation (HTML/PDF/Markdown)
- Telegram alert formatting
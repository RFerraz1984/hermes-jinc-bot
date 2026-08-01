# 📋 Relatório de Auditoria de Acessibilidade — {{ data.url }}

**Data:** {{ today }} | **Auditor:** Hermes Agent (Jornalista Inclusivo)  
**Normas:** WCAG 2.2 AA + e-MAG 3.1 | **Ferramentas:** axe 4.8, pa11y 6.2, Lighthouse 11.5

---

## 🎯 Resumo Executivo

| Métrica | Valor | Status |
|---------|-------|--------|
| Páginas auditadas | {{ data.scope.urls_tested }} | ✅ |
| Violações totais | {{ data.summary.total_violations }} | {% if data.summary.total_violations > 0 %}🔴{% else %}✅{% endif %} |
| Críticas (impacto critical/serious) | {{ data.summary.by_level.A + data.summary.by_level.AA }} | {% if data.summary.by_level.A + data.summary.by_level.AA > 0 %}🔴{% else %}✅{% endif %} |
| Conformidade WCAG 2.2 AA | {{ compliance_pct }}% | {% if compliance_pct < 50 %}🔴{% elif compliance_pct < 90 %}🟡{% else %}✅{% endif %} |
| Cobertura e-MAG 3.1 | {{ "%.0f"|format(data.summary.emag_coverage * 100) }}% | {% if data.summary.emag_coverage < 0.7 %}🔴{% elif data.summary.emag_coverage < 0.9 %}🟡{% else %}✅{% endif %} |

**Principais riscos jurídicos:**

{% for risk in risks %}
{{ loop.index }}. **{{ risk.law }}** — {{ risk.description }}
{% endfor %}

---

## 📊 Top 5 Violações por Impacto

| Critério | WCAG | Nível | Páginas | Impacto | Ajuste Necessário |
|----------|------|-------|---------|----------|-------------------|
{% for v in top_violations %}
| {{ v.name }} | {{ v.wcag }} | {{ v.level }} | {{ v.pages }} | {{ v.impact }} | {{ v.fix }} |
{% endfor %}

---

## ✅ Checklist e-MAG 3.1 (Itens Obrigatórios)

| Item | Descrição | Status | Evidência |
|------|-----------|--------|-----------|
{% for item in data.emag_checklist.items %}
| {{ item.id }} | {{ item.name }} | {% if item.status == 'pass' %}✅{% elif item.status == 'fail' %}❌{% elif item.status == 'manual' %}📝{% else %}⚠️{% endif %} {{ item.status }} | {{ item.evidence[:80] }} |
{% endfor %}

---

## 📋 Plano de Ação Prioritário

| Prioridade | Ação | Responsável | Prazo | Critério |
|------------|------|-------------|-------|----------|
{% for action in actions %}
| {{ action.priority }} | {{ action.action }} | {{ action.owner }} | {{ action.deadline }} | {{ action.criterion }} |
{% endfor %}

---

## 📎 Anexos

- `{{ data.audit_id }}_technical.json` — Dados completos para desenvolvedores
- `{{ data.audit_id }}_technical.md` — Relatório técnico detalhado
- `{{ data.audit_id }}_emag_checklist.md` — Checklist detalhado
- `{{ data.audit_id }}_report.html` — Relatório HTML navegável
- `screenshots/` — Evidências visuais (antes/depois)
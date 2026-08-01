# Hermes Cron Deployment for Accessibility Audit (no_agent mode)

Guia prático para rodar auditorias contínuas via Hermes cron (no_agent=true) — evita LLM, fallback Groq, e entrega direto no Telegram.

---

## Visão Geral

O toolkit `accessibility-audit-toolkit` inclui:
- `scripts/audit_cron.py` — Script standalone Python (sem LLM)
- `scripts/audit_cron_wrapper.sh` — Wrapper shell configura ambiente (PATH, venv, Playwright)

Cron jobs Hermes rodam em modo `no_agent=true`: o stdout do script é entregue direto no Telegram — sem LLM, sem fallback, sem custo de tokens.

---

## 1. Preparação do Ambiente

### Wrapper shell (`audit_cron_wrapper.sh`)

```bash
#!/bin/bash
export PATH="/opt/data/.npm-global/bin:$PATH"
export PLAYWRIGHT_BROWSERS_PATH="/opt/data/.playwright"
cd /opt/data/skills/journalism/accessibility-audit-toolkit
/opt/data/.venv/bin/python scripts/audit_cron.py
```

Instalar no Hermes:
```bash
cp scripts/audit_cron_wrapper.sh /opt/data/scripts/
chmod +x /opt/data/scripts/audit_cron_wrapper.sh
```

### URLs de Produção (`/opt/data/urls_production.txt`)

```text
https://jornalistainclusivo.com
https://pcd.dataverso.org
https://dados.dataverso.org/pcd
```

O script `audit_cron.py` lê este arquivo (fallback para URLs hardcoded se não existir).

---

## 2. Deploy dos Cron Jobs Hermes

```bash
# Diário 03:00 — home page dos 3 sites
/opt/hermes/bin/hermes cron create "0 3 * * *" --name "audit-daily-jinc" --script "audit_cron_wrapper.sh" --no-agent --deliver "telegram:965862678"

# Semanal profunda (segundas 02:00) — crawl depth > 0
/opt/hermes/bin/hermes cron create "0 2 * * 1" --name "audit-weekly-deep" --script "audit_cron_wrapper.sh" --no-agent --deliver "telegram:965862678"

# Legislativo (ter/qui 06:00) — mesmo script, URLs diferentes via env/args se necessário
/opt/hermes/bin/hermes cron create "0 6 * * 2,4" --name "audit-legislative" --script "audit_cron_wrapper.sh" --no-agent --deliver "telegram:965862678"
```

Verificar:
```bash
/opt/hermes/bin/hermes cron list | grep audit-
```

Testar execução imediata:
```bash
/opt/hermes/bin/hermes cron run <JOB_ID>
```

---

## 3. Configuração LLM (Evitar Fallback Groq)

Editar `~/.hermes/config.yaml`:

```yaml
model:
  default: openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
  provider: openrouter
  fallback_provider: ''  # vazio = sem fallback
  context_length: 131072
fallback_providers: '["openrouter"]'  # apenas OpenRouter
```

Requer `OPENROUTER_API_KEY` no `.env`.

---

## 4. Formato de Saída (Human-Readable)

O script gera relatórios em `/opt/data/audits/cron_YYYYMMDD_HHMMSS/`:

| Arquivo | Descrição |
|---------|-----------|
| `*_executive.md` | Resumo executivo (Markdown limpo, ~20 linhas) |
| `*_technical.md` | Detalhes técnicos |
| `*_report.html` | Relatório visual HTML |
| `audit.json` | Dados brutos completos (para diff/regressão) |

**Stdout entregue no Telegram:**
```
🤖 **Auditoria Automática JINC** — 20260728_220958

## 📍 https://jornalistainclusivo.com
# Relatório Executivo...
- Violações totais: **39**
- Conformidade WCAG 2.2 AA: **22%**

## 📍 https://pcd.dataverso.org
# Relatório Executivo...
- Violações totais: **3**
- Conformidade WCAG 2.2 AA: **94%**

## 📍 https://dados.dataverso.org/pcd
# Relatório Executivo...
- Violações totais: **0**
- Conformidade WCAG 2.2 AA: **100%**

📁 Relatórios completos em: `/opt/data/audits/cron_20260728_220958`
```

---

## 5. Troubleshooting

| Problema | Solução |
|----------|---------|
| `Script not found: /opt/data/scripts/...` | Colocar wrapper em `~/.hermes/scripts/` OU `/opt/data/scripts/` |
| `No module named 'numpy'` | `uv pip install numpy` no venv `/opt/data/.venv` |
| Playwright browser not found | `PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright /opt/data/.venv/bin/playwright install chromium` |
| `axe/pa11y/lhci: command not found` | `export PATH="/opt/data/.npm-global/bin:$PATH"` no wrapper |
| Cron roda mas stdout vazio | Verificar `hermes cron list` → `Last run: error: ...` — o script deve fazer `print()` para stdout |
| Fallback Groq no log | Configurar `fallback_provider: ''` e `fallback_providers: '["openrouter"]'` no config.yaml |

---

## 6. Próximos Passos

- [ ] Adicionar `--compare-with` no `audit_cron.py` para alertar regressão automática
- [ ] Incluir screenshot Playwright no HTML report (evidência visual)
- [ ] Webhook para Notion/Airtable com summary + link relatório
- [ ] Job `audit-on-deploy` via webhook GitHub Actions → Hermes
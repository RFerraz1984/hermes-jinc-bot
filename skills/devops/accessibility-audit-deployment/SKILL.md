---
name: accessibility-audit-deployment
description: "Deployment patterns for accessibility-audit-toolkit on Hermes/Umbrel — cron jobs, dependency installation, runtime environment, and CLI execution."
version: "1.0.0"
author: Hermes Agent
license: MIT
tags: [accessibility, audit, wcag, emag, cron, umbrel, hermes, deployment]
---

# Accessibility Audit Toolkit — Deployment Patterns (Hermes/Umbrel)

Session: 2026-07-28 — Full install, test, and cron deploy of `accessibility-audit-toolkit`.

## 1. Hermes Cron — Criação Individual (não `--from-file`)

`hermes cron create --from-file` **não existe** na CLI. Crie jobs um a um:

```bash
/opt/hermes/bin/hermes cron create \
  --name "audit-daily-jinc" \
  --schedule "0 3 * * *" \
  --skill accessibility-audit-toolkit \
  --prompt "Auditoria diária automática (axe + pa11y + lighthouse) dos sites Jornalista Inclusivo. Use --url-list /opt/data/urls_production.txt --auto-only --output /opt/data/audits/daily_$(date +%F)" \
  --deliver "telegram:965862678"

/opt/hermes/bin/hermes cron create \
  --name "audit-weekly-deep" \
  --schedule "0 2 * * 1" \
  --skill accessibility-audit-toolkit \
  --prompt "Auditoria semanal profunda (com crawl + checklist e-MAG) dos sites Jornalista Inclusivo." \
  --deliver "telegram:965862678"

/opt/hermes/bin/hermes cron create \
  --name "audit-legislative" \
  --schedule "0 6 * * 2,4" \
  --skill accessibility-audit-toolkit \
  --prompt "Auditoria de acessibilidade dos portais legislativos (Câmara, Senado) em dias de sessão." \
  --deliver "telegram:965862678"
```

## 2. Playwright Browser Path no Container Hermes

Container Hermes não tem write em `/opt/hermes/.playwright`. Use **sempre**:

```bash
# Instalação
PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright playwright install chromium

# Runtime (CLI e cron)
PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright python -m scripts.audit ...

# No prompt do cron job:
export PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright
```

## 3. Gerenciamento Python com `uv` (PEP 668)

Sistema usa `externally-managed-environment`. Use `uv`:

```bash
uv pip install -r requirements.txt
uv pip install pytest pytest-asyncio
```

## 4. Node Binaries Path

`npm install -g` instala em `/opt/data/.npm-global/bin/`. Exporte:

```bash
export PATH="/opt/data/.npm-global/bin:$PATH"
axe --version && pa11y --version && lhci --version
```

## 5. Variáveis de Ambiente no Prompt do Cron Job

Inclua setup completo no `--prompt`:

```bash
export PATH="/opt/data/.npm-global/bin:$PATH"
export PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright
cd /opt/data/skills/journalism/accessibility-audit-toolkit
python -m scripts.audit --url-list /opt/data/urls_production.txt --auto-only --output /opt/data/audits/daily_$(date +%F)
```

## 6. URL List para Produção

Mantenha `/opt/data/urls_production.txt`:

```
https://jornalistainclusivo.com
https://pcd.dataverso.org
https://dados.dataverso.org/pcd
```

Use `--url-list` (evita crawl/discovery que pode travar em timeout).

## 7. Testes Unitários (pytest)

```bash
cd /opt/data/skills/journalism/accessibility-audit-toolkit
PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright /opt/data/.venv/bin/python -m pytest tests/test_audit.py -v
```

## 8. Estrutura de Arquivos do Toolkit (27 arquivos)

```\n/opt/data/skills/journalism/accessibility-audit-toolkit/\n├── SKILL.md\n├── scripts/\n│   ├── __init__.py           # Lazy imports para deps pesadas\n│   ├── audit.py              # Orquestrador principal\n│   ├── axe_cli.py\n│   ├── pa11y_cli.py\n│   ├── lighthouse_cli.py\n│   ├── contrast_check.py     # FIX: hex parsing (#rgb, #rgba, #rrggbb, #rrggbbaa)\n│   ├── keyboard_nav.py\n│   ├── screen_reader.py\n│   ├── emag_checklist.py     # EMAG_ITENS com chave wcag_level\n│   ├── wcag_report.py        # BASE_DIR = Path(__file__).parent.parent\n│   ├── diff_report.py\n│   ├── crawl_site.py         # FIX: respeita max_depth=0\n│   ├── audit_cron.py         # Script standalone cron (no_agent)\n│   ├── audit_cron_wrapper.sh # Wrapper shell (PATH, venv, Playwright)\n│   └── audit_cron_isolated.sh\n├── templates/\n│   ├── wcag_criteria.yaml\n│   ├── checklist_emag.md\n│   ├── report_template.html  # usa audit_data.totals\n│   └── report_executive.md\n├── cron/\n│   └── audit-cron.yaml\n├── tests/\n│   └── test_audit.py         # 12/13 passing (test_discover_urls_mock flaky)\n├── requirements.txt          # 41 deps Python\n├── package.json              # Node deps + scripts\n└── README.md\n```

## 9. Referências Técnicas (references/)

- `references/hermes-cron-deployment.md` — Deploy completo Hermes cron (no_agent)
- `references/hermes-llm-openrouter-primary.md` — Config LLM OpenRouter sem fallback Groq
- `references/contrast-hex-parsing-fix.md` — Fix regex cores hex (#ff0000 truncado)
- `references/crawl-depth-zero-fix.md` — Fix crawl_site max_depth=0
- `references/session-2026-07-28-deployment.md` — Log completo da sessão
# Lições de Deploy no Umbrel (Hermes Agent) — Sessão 2026-07-28

## Contexto
Deploy do `accessibility-audit-toolkit` no Hermes Agent rodando em Umbrel OS (container Docker, WSL2).
Persistent path: `/opt/data` (mapeado de `C:\Users\RFERRAZ\Homelab-Umbrel\umbrel\app-data\hermes-agent\data`).

## Problemas Encontrados e Soluções

### 1. pip não disponível globalmente — usar `uv`
```bash
# Erro: /usr/bin/bash: line 3: pip: command not found
# Solução: uv está disponível em /usr/local/bin/uv
uv pip install -r requirements.txt
```

### 2. Playwright browsers — permissão negada em `/opt/hermes/.playwright`
```bash
# Erro: EACCES: permission denied, mkdir '/opt/hermes/.playwright/__dirlock'
# Solução: definir PLAYWRIGHT_BROWSERS_PATH para diretório persistente em /opt/data
PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright /opt/data/.venv/bin/playwright install chromium
```

### 3. npm global — binários não no PATH
```bash
# npm prefix -g retorna /opt/data/.npm-global
# Binários em /opt/data/.npm-global/bin/ (axe, pa11y, lhci, lighthouse)
# Solução: export PATH="/opt/data/.npm-global/bin:$PATH" antes de rodar auditorias
```

### 4. Hermes CLI — caminho absoluto necessário
```bash
# hermes não está no PATH
# Caminho real: /opt/hermes/bin/hermes
/opt/hermes/bin/hermes cron create --name "audit-daily-jinc" --skill "accessibility-audit-toolkit" --deliver "telegram:965862678" "0 3 * * *" "prompt..."
```

### 5. Cron jobs — `on_webhook` não suportado
```bash
# Erro: Invalid schedule 'on_webhook'
# Use apenas: duration ('30m'), interval ('every 2h'), cron ('0 9 * * *'), timestamp ('2026-02-03T14:00:00')
# Para webhook: criar job separado que roda script + webhook handler externo chama hermes cron run <job_id>
```

### 6. Python imports — lazy loading em `scripts/__init__.py`
```python
# playwright, jinja2, weasyprint são pesados e falham import se não instalados
# Solução: import lazy dentro das funções que precisam
def get_playwright():
    from playwright.async_api import async_playwright
    return async_playwright
```

### 7. Templates Jinja2 — variável `summary` vs `data.summary`
```jinja2
# Template original usava {{ data.summary.total_violations }} — falha com UndefinedError
# Relatório gera dict `summary` separado e passa para template
# Fix: usar {{ summary.total_violations }} no template
```

### 8. pa11y_cli.py — assinatura espera lista de URLs
```python
# audit.py chamava run_pa11y(url) — string
# run_pa11y espera List[str]
# Fix: run_pa11y([url])
```

### 9. emag_checklist.py — chave `level` vs `wcag_level`
```python
# Itens usam "level": "A" mas testes/outros esperam "wcag_level"
# Padronizar para "wcag_level" em todo código
```

### 10. Testes unitários — assinaturas divergentes
- `parse_color("#ff000080")` retorna alpha 0.502 vs teste 0.5
- `is_large_text(18.66, "bold")` retorna False (threshold WCAG: 14pt bold = 18.66px ≈ 14pt, mas implementação usa ≥14pt)
- `discover_urls` mock não resolve links relativos

## Comandos de Validação Pós-Deploy
```bash
# 1. Verificar imports
PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright /opt/data/.venv/bin/python -c "
import sys
sys.path.insert(0, '/opt/data/skills/journalism/accessibility-audit-toolkit/scripts')
from scripts import run_axe, run_pa11y, run_lighthouse, check_contrast, test_keyboard_navigation, run_emag_checklist, generate_reports, discover_urls, run_screen_reader_test
print('✓ Core imports OK')
"

# 2. Test run rápido
export PATH="/opt/data/.npm-global/bin:$PATH"
PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright /opt/data/.venv/bin/python -m scripts.audit --url-list /opt/data/urls_test.txt --auto-only --output /opt/data/audits/test

# 3. Listar cron jobs
/opt/hermes/bin/hermes cron list

# 4. Rodar testes unitários
export PATH="/opt/data/.npm-global/bin:$PATH"
PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright /opt/data/.venv/bin/python -m pytest /opt/data/skills/journalism/accessibility-audit-toolkit/tests/test_audit.py -v
```

## Arquivos Criados/Modificados nesta Sessão (27 total no toolkit)
```
templates/
├── wcag_criteria.yaml          # 142 linhas - WCAG 2.2 + mapeamento e-MAG
├── checklist_emag.md           # 42 linhas - checklist e-MAG 3.1
├── report_template.html        # 140 linhas - Jinja2 HTML report
└── report_executive.md         # 62 linhas - Markdown executivo

scripts/
├── __init__.py                 # 88 linhas - lazy imports + exports
├── audit.py                    # 256 linhas - orquestrador (imports corrigidos)
├── wcag_report.py              # 353 linhas - BASE_DIR fixado
├── keyboard_nav.py             # 248 linhas - test_keyboard_navigation + CLI
├── screen_reader.py            # 227 linhas - speech-dispatcher stub
├── emag_checklist.py           # original - export EMAG_ITEMS
├── axe_cli.py                  # original
├── pa11y_cli.py                # original
├── lighthouse_cli.py           # original
├── contrast_check.py           # original
├── crawl_site.py               # original
└── diff_report.py              # original

tests/
└── test_audit.py               # 198 linhas - pytest unit/integration

cron/
└── audit-cron.yaml             # 99 linhas - 4 jobs (diário, semanal, deploy, legislativo)

README.md                       # 228 linhas - documentação completa
requirements.txt                # 41 linhas - Python deps
package.json                    # 44 linhas - Node deps + scripts
```

## Cron Jobs Criados no Hermes
| Job ID | Name | Schedule | Skills | Delivery |
|--------|------|----------|--------|----------|
| 6e136eb984ca | audit-daily-jinc | 0 3 * * * | accessibility-audit-toolkit | telegram:965862678 |
| 3e52f9ff1217 | audit-weekly-deep | 0 2 * * 1 | accessibility-audit-toolkit | telegram:965862678 |
| 60d3fd3e3c28 | audit-legislative | 0 6 * * 2,4 | accessibility-audit-toolkit | telegram:965862678 |
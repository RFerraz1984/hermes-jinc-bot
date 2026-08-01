# Accessibility Audit Toolkit

> WCAG 2.2 AA + e-MAG 3.1 accessibility audit toolkit for inclusive journalism (Jornalista Inclusivo / JINC Apps).

## Overview

Complete accessibility auditing pipeline combining:
- **axe-core** (Deque) — automated WCAG 2.1/2.2 rules
- **pa11y** — multi-page WCAG 2.0/2.1/Section 508 testing
- **Lighthouse CI** — accessibility + performance + best practices + SEO
- **Custom contrast checker** — WCAG 2.1/2.2 AA/AAA via Playwright
- **Keyboard navigation test** — tab order, focus visible, skip links, keyboard traps
- **e-MAG 3.1 checklist** — Brazilian government accessibility mandatory items
- **Screen reader simulation** — speech-dispatcher (CI) / NVDA/Orca (local)
- **Unified reports** — HTML executive, Markdown technical, JSON raw, PDF (via WeasyPrint)
- **Diff reports** — regression detection between audits
- **Scheduled audits** — cron jobs for continuous monitoring

## Quick Start

### Prerequisites

```bash
# Node tools (axe, pa11y, lighthouse)
npm install -g @axe-core/cli@4.8 pa11y@6.2 @lhci/cli@0.13

# Python deps
uv pip install -r requirements.txt
# or
pip install -r requirements.txt

# Playwright browser
playwright install chromium
```

### Run Audit

```bash
# Single URL, full audit
python -m scripts.audit https://jornalistainclusivo.com --output ./audit_results

# Auto-only (fast, CI-friendly)
python -m scripts.audit https://example.com --auto-only --output ./ci_results

# Manual-only (human review items)
python -m scripts.audit https://example.com --manual-only --output ./manual_results

# From URL list
python -m scripts.audit --url-list urls.txt --output ./batch_results
```

### Individual Tools

```bash
# axe-core only
python -m scripts.axe_cli https://example.com --output axe.json

# pa11y multi-page
python -m scripts.pa11y_cli https://example.com https://example.com/about --standard WCAG2AA

# Lighthouse
python -m scripts.lighthouse_cli https://example.com --preset mobile --categories accessibility performance

# Contrast check
python -m scripts.contrast_check https://example.com --threshold AA

# Keyboard navigation
python -m scripts.keyboard_nav https://example.com

# e-MAG checklist
python -m scripts.emag_checklist https://example.com

# Screen reader (speech-dispatcher)
python -m scripts.screen_reader https://example.com --method speech-dispatcher

# Generate reports from existing audit JSON
python -m scripts.wcag_report --input audit.json --output ./reports
```

## Project Structure

```
accessibility-audit-toolkit/
├── scripts/                    # Core Python modules
│   ├── __init__.py            # Package exports
│   ├── audit.py               # Main orchestrator
│   ├── axe_cli.py             # axe-core wrapper
│   ├── pa11y_cli.py           # pa11y wrapper
│   ├── lighthouse_cli.py      # Lighthouse CI wrapper
│   ├── contrast_check.py      # WCAG contrast via Playwright
│   ├── keyboard_nav.py        # Keyboard navigation test
│   ├── emag_checklist.py      # e-MAG 3.1 checklist
│   ├── wcag_report.py         # Report generator (HTML/MD/PDF/JSON)
│   ├── diff_report.py         # Audit comparison
│   ├── crawl_site.py          # URL discovery (sitemap + crawl)
│   └── screen_reader.py       # Screen reader simulation
├── templates/                  # Jinja2/Markdown templates
│   ├── wcag_criteria.yaml     # WCAG 2.2 ↔ e-MAG mapping
│   ├── checklist_emag.md      # e-MAG checklist template
│   ├── report_template.html   # Executive HTML report
│   └── report_executive.md    # Executive Markdown report
├── tests/
│   └── test_audit.py          # Unit + integration tests
├── cron/
│   └── audit-cron.yaml        # Scheduled audit jobs (Hermes/Umbrel)
├── requirements.txt           # Python dependencies
├── package.json               # Node dependencies
└── SKILL.md                   # This file
```

## Cron Jobs (Hermes / Umbrel)

Deploy scheduled audits via the skill's cron definitions:

```bash
# Via Hermes CLI
hermes cron create --from-file cron/audit-cron.yaml

# Or via skill
cronjob(action='create', schedule='0 3 * * *', prompt='...', skills=['accessibility-audit-toolkit'])
```

**Included jobs:**
- `audit-daily-jinc` — Daily 03:00, JINC sites (5 sites, 20 URLs each)
- `audit-weekly-full` — Weekly Mon 02:00, deep crawl (50 URLs, depth 5)
- `audit-on-deploy` — Webhook-triggered post-deploy smoke test
- `audit-legislative-portals` — Mon/Wed/Fri 06:00, federal legislative portals

## Outputs

Each audit generates:

```
audit_results/
├── audit_<id>_technical.json      # Raw data for developers
├── audit_<id>_technical.md        # Detailed technical report
├── audit_<id>_executive.md        # Executive summary (PT-BR)
├── audit_<id>_report.html         # Navigable HTML report
├── audit_<id>_emag_checklist.md   # e-MAG 3.1 checklist
├── audit_<id>_diff.md             # vs previous audit (if exists)
└── screenshots/                   # Visual evidence
```

## WCAG 2.2 + e-MAG 3.1 Coverage

| WCAG Criterion | Level | e-MAG Item | Automated |
|---|---|---|---|
| 1.1.1 Non-text Content | A | 1.1 | ✅ axe |
| 1.3.1 Info & Relationships | A | 1.3 | ✅ axe |
| 1.4.3 Contrast (Minimum) | AA | 1.4 | ✅ axe + custom |
| 1.4.11 Non-text Contrast | AA | 1.5 | ✅ axe |
| 2.1.1 Keyboard | A | 2.1 | ⚠️ manual |
| 2.1.2 No Keyboard Trap | A | — | ✅ axe |
| 2.4.1 Bypass Blocks | A | 2.2 | ✅ axe |
| 2.4.3 Focus Order | A | 2.3 | ⚠️ manual |
| 2.4.6 Headings & Labels | AA | 2.3 | ✅ axe |
| 2.4.7 Focus Visible | AA | 2.4 | ✅ custom |
| 2.5.3 Label in Name | A | — | ✅ axe |
| 3.1.1 Language of Page | A | 3.1 | ✅ axe |
| 3.2.1 On Focus | A | — | ✅ axe |
| 3.3.1 Error Identification | A | 3.2 | ✅ axe |
| 4.1.1 Parsing | A | — | ✅ axe |
| 4.1.2 Name, Role, Value | A | 4.1 | ✅ axe |
| **2.4.11 Focus Not Obscured (Min)** | AA | — | ⚠️ manual |
| **2.5.7 Dragging Movements** | AA | — | ⚠️ manual |
| **3.2.6 Consistent Help** | A | — | ✅ axe |
| **3.3.7 Redundant Entry** | A | — | ⚠️ manual |

## Configuration

### Environment Variables

```bash
# Telegram notifications (for cron jobs)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=965862678

# OpenRouter (for AI-enhanced reports)
OPENROUTER_API_KEY=sk-...

# Speech-dispatcher (screen reader tests)
SPEECHD_VOICE=pt-br
```

### Customize Criteria

Edit `templates/wcag_criteria.yaml` to add/remove/modify criteria mapping.

## CI/CD Integration

```yaml
# .github/workflows/accessibility.yml
name: Accessibility Audit
on: [push, pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm install -g @axe-core/cli pa11y @lhci/cli
      - uses: actions/setup-python@v5
        with: { python-version: '3.13' }
      - run: pip install -r requirements.txt
      - run: playwright install chromium
      - run: python -m scripts.audit https://staging.example.com --auto-only --output ./results
      - uses: actions/upload-artifact@v4
        with: { name: a11y-report, path: results/ }
```

## Contributing

1. Fork → feature branch → PR
2. Run tests: `pytest tests/ -v`
3. Lint: `ruff check scripts/ tests/`
4. Format: `ruff format scripts/ tests/`

## License

MIT — Jornalista Inclusivo (JINC Apps) / Rafael Ferraz Carpi

## Links

- **Jornalista Inclusivo**: https://jornalistainclusivo.com
- **Dataverso PcD**: https://pcd.dataverso.org
- **GitHub Org**: https://github.com/jornalistainclusivo
- **Dataset Capacitismo Algorítmico**: https://github.com/jornalistainclusivo/capacitismo-algoritmico
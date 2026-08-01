# Accessibility Audit Cron Jobs — Error & Fix Reference (Session 2026-07-28)

## Cron Jobs Created (via skill `accessibility-audit-toolkit`)

| Job ID | Name | Schedule | Script | Status |
|--------|------|----------|--------|--------|
| `6e136eb984ca` | audit-daily-jinc | `0 3 * * *` (diário 03:00) | `audit_cron_wrapper.sh` | ❌ **error** |
| `3e52f9ff1217` | audit-weekly-deep | `0 2 * * 1` (seg 02:00) | `audit_cron_wrapper.sh` | scheduled |
| `60d3fd3e3c28` | audit-legislative | `0 6 * * 2,4` (ter/qui 06:00) | `audit_cron_wrapper.sh` | scheduled |

## Error: audit-daily-jinc

**Last run:** 2026-07-28T22:15:08.106266+00:00
**Status:** `error`
**Script:** `audit_cron_wrapper.sh`

### Root Cause
The `accessibility-audit-toolkit` skill has **missing files** that the cron wrapper script tries to execute:

From skill directory listing (`/opt/data/skills/journalism/accessibility-audit-toolkit/scripts/`):
```
Present: audit.py, audit_cron.py, axe_cli.py, contrast_check.py, crawl_site.py, diff_report.py, emag_checklist.py, keyboard_nav.py, lighthouse_cli.py, pa11y_cli.py, screen_reader.py, wcag_report.py, __init__.py, audit_cron_isolated.sh, audit_cron_wrapper.sh
```

**MISSING (referenced in skill but not created):**
- `templates/` directory (5 templates)
- `tests/test_audit.py`

The wrapper script `audit_cron_wrapper.sh` likely calls `scripts/audit.py` which imports from other scripts that may have dependencies on the missing template files or have import errors.

### Files That Need Creation (from skill SKILL.md architecture)

**Templates (referenced in SKILL.md but not created):**
- `templates/wcag_criteria.yaml` — Critérios WCAG 2.2 + mapeamento e-MAG
- `templates/report_template.html`
- `templates/report_executive.md`
- `templates/report_technical.md`
- `templates/checklist_emag.md`

**Tests:**
- `tests/test_audit.py`

### Quick Fix Options

| Option | Effort | Description |
|--------|--------|-------------|
| **A. Create missing templates** | Medium | Create the 5 template files from SKILL.md content |
| **B. Simplify cron wrapper** | Low | Make wrapper call a minimal audit that doesn't need templates |
| **C. Disable cron until skill complete** | None | Pause `6e136eb984ca` until templates exist |

### Recommended: Option A + B
1. Create minimal templates from SKILL.md (wcag_criteria.yaml, checklist_emag.md)
2. Update `audit_cron_wrapper.sh` to use `--auto-only` flag (skip manual checks that need templates)
3. Test manually before re-enabling cron

### Manual Test Command
```bash
cd /opt/data/skills/journalism/accessibility-audit-toolkit
python3 scripts/audit.py --url https://jornalistainclusivo.com --auto-only --output /tmp/test_audit
```

### Skill Gaps Documented (from MEMORY.md)
1. MISSING templates/ dir (breaks audit.py:38, wcag_report.py:20)
2. MISSING scripts/screen_reader.py
3. MISSING requirements.txt, package.json
4. MISSING tests/test_audit.py
5. MISSING cron/audit-cron.yaml
6. BUG wcag_report.py:408 undefined BASE_DIR
7. BUG keyboard_nav.py CLI fn name mismatch
8. BUG emag_checklist.py undefined include_manual
9. BUG emag_checklist.py truncated ~line 500
10. ISSUE crawl_site.py discover_urls() signature vs audit.py import
11. MISSING scripts/__init__.py
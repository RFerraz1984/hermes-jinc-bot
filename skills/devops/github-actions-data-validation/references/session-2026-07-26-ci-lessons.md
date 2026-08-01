# GitHub Actions Data Validation — Session 2026-07-26 Learnings

> **Session**: 2026-07-25 to 2026-07-26 — Completed Phase 1 expansion of `capacitismo-algoritmico` dataset (14 new incidents across 8 platforms, all 8 categories covered)
> **Skill**: `github-actions-data-validation` (devops)

---

## What Worked This Session

### 1. Modular Validation Scripts — Best Practice Confirmed
Split validation into separate files (created in Phase 1):
| Script | Purpose | Called By |
|--------|---------|-----------|
| `scripts/validate.py` | Main orchestrator | CI workflow + local |
| `scripts/validate_raw.py` | JSONL syntax validation | `validate.py` |
| `scripts/check_fields.py` | Required fields in Parquet | `validate.py` |
| `scripts/validate_schemas.py` | JSON Schema validation | `validate.py` |
| `scripts/generate_report.py` | Markdown CI summary | CI workflow |

**Why this works**: Avoids YAML escaping hell with inline Python in `run:` steps. Each script testable locally.

### 2. Workflow YAML Now Clean
```yaml
# CI now calls scripts directly — NO inline python -c "..."
- name: Validate dataset
  run: python scripts/validate.py data/processed/
- name: Check external links
  run: lychee --verbose --max-concurrency 5 .
```

### 3. Schema Evolution Handled Correctly
When adding new platforms (`discord`, `xai`) and new categories (`CD-IND`):
1. Updated `schemas/incidents.json` enum **before** collecting data
2. Made `impact` fields nullable (`["integer", "null"]`)
3. Re-ran validation locally → passed
4. Committed schema + data together → CI passed

### 4. Data Files Committed (gitignore Fixed)
`.gitignore` had `data/raw/` and `data/processed/` commented out to allow CI access to example/real data.

---

## Schema Fixes Applied (Must Replicate for Future Phases)

### Impact Fields → Nullable
```json
// Before (caused validation failures)
"impact": {
  "requests_blocked": {"type": "integer"},
  "tokens_lost": {"type": "integer"},
  "context_lost": {"type": "boolean"}
}

// After (allows incidents without quantifiable impact)
"impact": {
  "requests_blocked": {"type": ["integer", "null"]},
  "tokens_lost": {"type": ["integer", "null"]},
  "context_lost": {"type": ["boolean", "null"]},
  "reputation_damage": {"type": ["string", "null"]},
  "financial_loss_usd": {"type": ["number", "null"]},
  "downtime_minutes": {"type": ["integer", "null"]}
}
```

### Platform Enum Extended
```json
"platform": {
  "name": {
    "enum": [
      "openai", "anthropic", "moltbook", "x-twitter", "bluesky",
      "github-copilot", "openrouter", "other", "huggingface",
      "meta", "discord", "google", "microsoft", "replicate",
      "cohere", "xai"   // ← NEW: discord, xai added this session
    ]
  }
}
```

### Category Enum Already Complete
All 8 categories present in schema enum — validated by CI.

---

## CI Run History This Session

| Run | Trigger | Status | Records |
|-----|---------|--------|---------|
| #17 | Push (HF incidents) | ✅ | 3 |
| #18 | Push (X + Meta incidents) | ✅ | 8 |
| #19 | Push (Discord incidents) | ✅ | 11 |
| #20 | Push (CD-IND: OpenAI, Anthropic, xAI) | ✅ | 14 |

**All 4 runs passed** — validates modular script approach + schema fixes.

---

## Commands That Worked (Reusable)

### Local Validation
```bash
cd /opt/data/datasets/capacitismo-algoritmico
/opt/data/.venv/bin/python scripts/validate.py data/processed/
# ✅ All validations passed!
```

### Schema Check Before Collection
```bash
# Quick enum check
python -c "
import json
with open('schemas/incidents.json') as f:
    s = json.load(f)
print('Platforms:', s['properties']['platform']['properties']['name']['enum'])
print('Categories:', s['properties']['category']['enum'])
"
```

### Add New Platform to Schema (Template)
```bash
# Before collecting from new platform (e.g., Google, Microsoft)
python -c "
import json
with open('schemas/incidents.json') as f:
    s = json.load(f)
# Add to platform enum
platforms = s['properties']['platform']['properties']['name']['enum']
new = ['google', 'microsoft', 'replicate', 'cohere']
for p in new:
    if p not in platforms:
        platforms.append(p)
with open('schemas/incidents.json', 'w') as f:
    json.dump(s, f, indent=2)
print('Updated:', platforms)
"
```

### Trigger Manual Workflow Dispatch
```bash
# After fixing YAML syntax, wait ~30s then:
gh workflow run validate-dataset.yml --ref master -R jornalistainclusivo/capacitismo-algoritmico
```

---

## Pitfalls Re-Confirmed (From Lesson #7)

### ❌ NEVER DO THIS in GitHub Actions YAML:
```yaml
# BROKEN: Inline multi-line Python with special chars
- name: Validate
  run: |
    python -c "
    import json
    from jsonschema import validate
    for f in Path('data/raw').glob('*.jsonl'):
        # YAML parser chokes on :, {, }, #, f-strings
    "
```

### ✅ ALWAYS DO THIS:
```yaml
# WORKS: Call separate script file
- name: Validate
  run: python scripts/validate.py data/processed/
```

**Root cause**: YAML simple key scanning conflicts with Python syntax. Extracting to `.py` files is the only robust pattern.

---

## Next Session (Phase 2) — Pre-Work

-checklist

### Schema Updates Needed Before Collecting
```bash
# Add these to platform enum:
# - "google" (Gemini/Vertex AI)
# - "microsoft" (Copilot/Azure OpenAI)
# - "replicate" (GPU marketplace)
# - "cohere" (Together.ai/OpenRouter aggregator)
```

### Validation Script Updates
- [ ] Ensure `check_fields.py` extracts `agent_id_hash` from `agent_profile.architecture_hash` (already done)
- [ ] Verify `validate_schemas.py` handles new platforms
- [ ] Test locally with dummy data before CI

### Workflow Enhancements
- [ ] Add `needs: [validate]` to link check job (sequential)
- [ ] Upload `validation-report.md` as artifact
- [ ] PR comment job depends on validate job

---

## Related Files This Session

| File | Purpose |
|------|---------|
| `/opt/data/datasets/capacitismo-algoritmico/schemas/incidents.json` | Updated platform enum + nullable impact |
| `/opt/data/datasets/capacitismo-algoritmico/scripts/validate.py` | Orchestrator (unchanged, worked) |
| `/opt/data/datasets/capacitismo-algoritmico/scripts/validate_raw.py` | JSONL syntax |
| `/opt/data/datasets/capacitismo-algoritmico/scripts/check_fields.py` | Required fields + agent_id_hash derivation |
| `/opt/data/datasets/capacitismo-algoritmico/scripts/validate_schemas.py` | JSON Schema validation |
| `/opt/data/datasets/capacitismo-algoritmico/scripts/generate_report.py` | CI Markdown report |
| `.github/workflows/validate-dataset.yml` | Clean workflow calling scripts |

---

*This reference captures the successful CI/CD pattern for dataset validation evolved during Phase 1. Use as blueprint for Phase 2 platforms.*
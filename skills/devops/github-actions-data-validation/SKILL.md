---
name: github-actions-data-validation
description: GitHub Actions workflows for continuous validation of datasets — schema enforcement, data quality checks, link validation, and automated failure notification.
version: "1.0"
author: Hermes Agent
license: MIT
tags: [github-actions, ci-cd, data-validation, dataset, schema-enforcement, data-quality]
---

# GitHub Actions Data Validation

> **Origin**: Session 2026-07-25 — Created CI pipeline for `jornalistainclusivo/capacitismo-algoritmico` dataset with schema validation, link checking, and failure notifications.

## Overview

Class-level skill for building GitHub Actions workflows that validate datasets on every push/PR/schedule. Covers:
- JSON Schema validation for structured data
- Data quality checks (required fields, null checks, type consistency)
- External link validation
- Automated failure notifications via GitHub Issues
- Manual workflow dispatch for on-demand runs

## Workflow Template: `.github/workflows/validate-dataset.yml`

### Triggers
```yaml
on:
  push:
    branches: [master, main]
  pull_request:
    branches: [master, main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 02:00 UTC
  workflow_dispatch:  # Manual trigger via UI/API
```

### Permissions
```yaml
permissions:
  contents: read
  issues: write
  pull-requests: write
```

### Jobs

#### 1. `validate` — Dataset Validation
```yaml
jobs:
  validate:
    name: Validate Dataset
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pandas pyarrow jsonschema pyyaml
      - name: Validate JSON schemas
        run: python scripts/validate.py data/processed/
        env:
          PYTHONPATH: .
      - name: Validate raw data format
        run: |
          python -c "
import json, sys
from pathlib import Path
raw_dir = Path('data/raw')
errors = 0
for file in raw_dir.glob('*.jsonl'):
    with open(file) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line: continue
            try: json.loads(line)
            except json.JSONDecodeError as e:
                print(f'❌ {file}:{i}: {e}')
                errors += 1
if errors: sys.exit(1)
print('✅ All JSONL files valid')
          "
      - name: Check required fields
        run: |
          python -c "
import pandas as pd
from pathlib import Path
proc_dir = Path('data/processed')
required_fields = ['incident_id', 'platform', 'category', 'agent_id_hash', 'timestamp', 'description']
for file in proc_dir.glob('*.parquet'):
    df = pd.read_parquet(file)
    missing = [f for f in required_fields if f not in df.columns]
    if missing:
        print(f'❌ {file}: missing fields {missing}')
        sys.exit(1)
    nulls = df[required_fields].isnull().sum()
    if nulls.any():
        print(f'⚠️  {file}: null values in {nulls[nulls > 0].to_dict()}')
    print(f'✅ {file}: {len(df)} records, all required fields present')
          "
      - name: Validate against schemas
        run: |
          python -c "
import json
from pathlib import Path
from jsonschema import validate, ValidationError
import pandas as pd

schemas_dir = Path('schemas')
data_dir = Path('data/processed')

for schema_file in schemas_dir.glob('*.json'):
    with open(schema_file) as f:
        schema = json.load(f)
    data_file = data_dir / f'{schema_file.stem}.parquet'
    if not data_file.exists():
        print(f'⚠️  No data file for schema {schema_file.name}')
        continue
    df = pd.read_parquet(data_file)
    errors = 0
    for idx, row in df.iterrows():
        # Convert row to dict with proper serialization
        row_dict = {}
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                row_dict[col] = None
            elif isinstance(val, pd.Timestamp):
                row_dict[col] = val.isoformat()
            elif isinstance(val, str):
                if col in ['platform', 'agent_profile', 'evidence', 'impact', 'remediation', 'tags']:
                    try: row_dict[col] = json.loads(val)
                    except: row_dict[col] = val
                else:
                    row_dict[col] = val
            else:
                row_dict[col] = val
        try:
            validate(instance=row_dict, schema=schema)
        except ValidationError as e:
            print(f'❌ {data_file.name} row {idx}: {e.message}')
            errors += 1
    if errors == 0:
        print(f'✅ {data_file.name}: {len(df)} records valid')
    else:
        sys.exit(1)
          "
      - name: Generate validation report
        if: always()
        run: |
          python -c "
from pathlib import Path
import pandas as pd
print('## Dataset Validation Report')
print()
print(f'Repository: jornalistainclusivo/capacitismo-algoritmico')
print(f'Branch: ${{{{ github.ref_name }}}}')
print(f'Commit: ${{{{ github.sha }}}}')
print()
raw_files = list(Path('data/raw').glob('*.jsonl'))
proc_files = list(Path('data/processed').glob('*.parquet'))
schema_files = list(Path('schemas').glob('*.json'))
print(f'📁 Raw files: {len(raw_files)}')
print(f'📁 Processed files: {len(proc_files)}')
print(f'📋 Schemas: {len(schema_files)}')
print()
total_records = 0
for f in proc_files:
    df = pd.read_parquet(f)
    total_records += len(df)
    print(f'  - {f.name}: {len(df)} records')
print(f'📊 Total records: {total_records}')
          " > validation-report.md
      - name: Post validation report to PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('validation-report.md', 'utf8');
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            })

#### 2. `check-links` — External Link Validation
```yaml
  check-links:
    name: Check External Links
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check links
        uses: lycheeverse/lychee-action@v1
        with:
          args: '--verbose --max-concurrency 5'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### 3. `notify-failure` — Failure Notification
```yaml
  notify-failure:
    name: Notify on Failure
    if: failure()
    needs: [validate, check-links]
    runs-on: ubuntu-latest
    steps:
      - name: Notify via GitHub Issue
        uses: actions/github-script@v7
        with:
          script: |
            const { owner, repo } = context.repo;
            const run = await github.rest.actions.getWorkflowRun({
              owner, repo, run_id: context.runId
            });
            const body = `
            ❌ **Dataset Validation Failed**
            
            **Workflow:** ${context.workflow}
            **Run:** #${context.runId}
            **Branch:** ${context.ref}
            **Commit:** ${context.sha.substring(0,7)}
            
            [View Logs](${run.data.html_url})
            
            Please check the validation logs and fix any issues.
            `;
            await github.rest.issues.create({
              owner, repo,
              title: `[CI] Dataset Validation Failed - ${context.ref}`,
              body,
              labels: ['ci-failure', 'dataset', 'automated']
            });
```

---

## Validation Script: `scripts/validate.py`

### Features
- Validates JSONL in `data/raw/`
- Validates Parquet in `data/processed/` against schemas in `schemas/`
- Extracts `agent_id_hash` from `agent_profile.architecture_hash` (first 16 chars)
- Handles type conversion for schema validation:
  - `pd.Timestamp` → ISO string
  - JSON strings (`platform`, `agent_profile`, `evidence`, `impact`, `remediation`, `tags`) → parsed objects

### Usage
```bash
cd /path/to/dataset
python scripts/validate.py data/processed/
# ✅ All validations passed!
```

### Requirements
```txt
# requirements.txt
requests>=2.31.0
pydantic>=2.5.0
jsonschema>=4.20.0
pyyaml>=6.0.1
pandas>=2.1.0
pyarrow>=14.0.0
tqdm>=4.66.0
python-dotenv>=1.0.0

# CI extra (installed in workflow)
pandas pyarrow jsonschema pyyaml
```

---

## Data Structure Requirements

### Directory Layout
```
dataset/
├── README.md
├── LICENSE
├── requirements.txt
├── .github/
│   └── workflows/
│       └── validate-dataset.yml
├── data/
│   ├── raw/
│   │   └── incidents.jsonl          # Full nested objects (JSONL)
│   └── processed/
│       └── incidents.parquet        # Nested fields as JSON strings
├── schemas/
│   └── incidents.json               # JSON Schema for validation
└── scripts/
    └── validate.py                  # Validation script
```

### Schema Requirements (`schemas/incidents.json`)
- **Required fields**: `incident_id`, `timestamp`, `platform`, `agent_profile`, `category`, `severity`, `description`, `evidence`
- **Platform enum**: `openai`, `anthropic`, `moltbook`, `x-twitter`, `bluesky`, `github-copilot`, `openrouter`, `other`
- **Category enum**: `RL-SEL`, `SB-OPQ`, `SS-ARB`, `CTX-RET`, `CD-IND`, `CP-DEN`, `POL-DRIFT`, `APP-DEN`
- **Severity enum**: `low`, `medium`, `high`, `critical`

### Processed Data Format (Parquet)
Nested objects stored as JSON strings for Parquet compatibility:
- `platform` → JSON string
- `agent_profile` → JSON string
- `evidence` → JSON string
- `impact` → JSON string
- `remediation` → JSON string
- `tags` → JSON string

Validation script auto-parses these JSON strings during validation.

---

## Local Testing

```bash
# Install dependencies
pip install -r requirements.txt
pip install pandas pyarrow jsonschema pyyaml

# Run validation
python scripts/validate.py data/processed/

# Expected output:
# 🔍 Validating dataset...
#    Processed: data/processed
#    Raw: data/raw
#    Schemas: schemas
# 
# 📄 Validating JSONL: incidents.jsonl
# ✅ incidents.jsonl: valid JSONL
# 
# ✅ incidents.parquet: all required fields present (3 records)
# 
# 📋 Validating incidents.parquet against incidents.json...
# ✅ incidents.parquet: 3 records valid
# 
# ✅ All validations passed!
```

---

## Branch Protection Setup (GitHub UI)

1. **Settings → Branches → Add rule**
2. Branch pattern: `master` (or `main`)
3. ☑ **Require a pull request before merging**
   - Required approvals: 1
   - ☑ Dismiss stale PR approvals when new commits are pushed
4. ☑ **Require status checks to pass before merging**
   - Search for: `Validate Dataset` (job name from workflow)
5. ☑ **Require branches to be up to date before merging**
6. ☑ **Include administrators**

---

## Manual Workflow Dispatch

```bash
# Trigger manually via GitHub CLI
gh workflow run validate-dataset.yml --ref master -R owner/repo

# Or via GitHub UI: Actions → Validate Dataset → Run workflow
```

---

## Failure Notification

On workflow failure, an Issue is automatically created with:
- Workflow name
- Run number
- Branch
- Commit SHA (short)
- Direct link to logs
- Labels: `ci-failure`, `dataset`, `automated`

---

## Lessons Learned

1. **Data files must be committed** — `.gitignore` often ignores `data/`; comment out for CI access
2. **Nested objects in Parquet** — Store as JSON strings, parse during validation
3. **Type conversion critical** — `pd.Timestamp` → ISO string, JSON strings → objects
5. **Derived fields** — Compute `agent_id_hash` from `agent_profile.architecture_hash` at validation time
6. **Silent exit on success** — CI scripts should only output on failure (or summary)
7. **YAML INLINE PYTHON PITFALL** — Embedding multi-line Python scripts with `python -c \"...\"` in YAML `run:` steps breaks the YAML parser when the script contains special characters (`import`, `:`, `#`, f-strings with braces). **Fix**: Extract to separate `.py` files in `scripts/` and call them directly with `run: python scripts/xxx.py`. This is the #1 cause of `ScannerError: while scanning a simple key ... could not find expected ':'` in GitHub Actions YAML validation.
8. **workflow_dispatch not recognized** — If the API returns "Workflow does not have 'workflow_dispatch' trigger" but the YAML has it, the YAML is likely invalid (see #7). Fix the YAML syntax, push, wait ~30s for GitHub to re-parse, then dispatch works.
9. **Schema must allow nullable impact fields** — The `impact` object properties (`requests_blocked`, `tokens_lost`, `context_lost`, `reputation_damage`, `financial_loss_usd`, `downtime_minutes`) should be defined as `[\"type\", \"null\"]` arrays in JSON Schema, since real incidents often lack quantifiable impact metrics.
10. **Modular validation scripts** — Split validation into separate scripts: `validate.py` (orchestrator), `validate_raw.py` (JSONL), `check_fields.py` (required fields), `validate_schemas.py` (JSON Schema), `generate_report.py` (Markdown report). This avoids YAML escaping issues and enables local testing.
11. **Raw JSONL must match schema structure** — Raw data in `data/raw/` should contain fully nested objects; processed data in `data/processed/` stores nested fields as JSON strings for Parquet compatibility.
12. **Platform enum extensibility** — The schema's `platform.name` enum should include all known platforms (`openai`, `anthropic`, `moltbook`, `x-twitter`, `bluesky`, `github-copilot`, `openrouter`, `other`) and be updated when new platforms are added.
13. **workflow_dispatch trigger requires valid YAML** — Even with `workflow_dispatch:` in the `on:` block, GitHub won't recognize it if the workflow YAML has syntax errors. Always validate YAML locally (`yamllint` or `python -c \"import yaml; yaml.safe_load(open(...))\""`) before pushing.
14. **Sequential job dependencies for report posting** — The `generate_report.py` output should be uploaded as an artifact and the PR comment job should depend on the validation job completing. Use `needs: [validate-dataset]` in the workflow.
15. **Dataset collection via browser automation** — For platforms without public APIs (or rate-limited ones), browser automation (`browser_navigate`, `browser_click`, `browser_snapshot`) can extract structured data from docs, pricing pages, transparency reports. Save extracted data as JSONL in `data/raw/{platform}_{category}_{date}.jsonl` for schema-compliant ingestion.
16. **Schema evolution for new categories** — When adding new incident categories (e.g., `CD-IND` for Content Drift Induzido), update both the JSON Schema enum AND the validation scripts' category handling before collecting data.

---

## Related Skills

- `openrouter-cost-governance` — GitHub Actions cron patterns, natural language Telegram output
- `moltbook` — Moltbook API patterns, comment editing via `PATCH /comments/{id}`
- `cron-rss-multi-feed-telegram` — Cron job patterns with natural language output
- `cronjob-python-environment` — Python environment management for cron jobs
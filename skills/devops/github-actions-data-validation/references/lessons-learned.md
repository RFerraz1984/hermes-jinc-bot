# Lessons Learned — GitHub Actions Data Validation

## 1. Data Files Must Be Committed
`.gitignore` often ignores `data/`; comment out for CI access.

## 2. Nested Objects in Parquet
Store as JSON strings, parse during validation.

## 3. Type Conversion Critical
`pd.Timestamp` → ISO string, JSON strings → objects.

## 4. Derived Fields
Compute `agent_id_hash` from `agent_profile.architecture_hash` at validation time.

## 5. Silent Exit on Success
CI scripts should only output on failure (or summary).

## 6. YAML INLINE PYTHON PITFALL ⚠️
Embedding multi-line Python scripts with `python -c "..."` in YAML `run:` steps breaks the YAML parser when the script contains special characters (`import`, `:`, `#`, f-strings with braces).
**Fix**: Extract to separate `.py` files in `scripts/` and call them directly with `run: python scripts/xxx.py`. This is the #1 cause of `ScannerError: while scanning a simple key ... could not find expected ':'` in GitHub Actions YAML validation.

## 7. workflow_dispatch Not Recognized
If the API returns "Workflow does not have 'workflow_dispatch' trigger" but the YAML has it, the YAML is likely invalid (see #6). Fix the YAML syntax, push, wait ~30s for GitHub to re-parse, then dispatch works.

## 8. Schema Must Allow Nullable Impact Fields
The `impact` object properties (`requests_blocked`, `tokens_lost`, `context_lost`, `reputation_damage`, `financial_loss_usd`, `downtime_minutes`) should be defined as `["type", "null"]` arrays in JSON Schema, since real incidents often lack quantifiable impact metrics.

## 9. Modular Validation Scripts
Split validation into separate scripts: `validate.py` (orchestrator), `validate_raw.py` (JSONL), `check_fields.py` (required fields), `validate_schemas.py` (JSON Schema), `generate_report.py` (Markdown report). This avoids YAML escaping issues and enables local testing.

## 10. Raw JSONL Must Match Schema Structure
Raw data in `data/raw/` should contain fully nested objects; processed data in `data/processed/` stores nested fields as JSON strings for Parquet compatibility.

## 11. Platform Enum Extensibility
The schema's `platform.name` enum should include all known platforms and be updated when new platforms are added.

## 12. workflow_dispatch Trigger Requires Valid YAML
Even with `workflow_dispatch:` in the `on:` block, GitHub won't recognize it if the workflow YAML has syntax errors. Always validate YAML locally (`yamllint` or `python -c "import yaml; yaml.safe_load(open(...))"`) before pushing.

## 13. Sequential Job Dependencies for Report Posting
The `generate_report.py` output should be uploaded as an artifact and the PR comment job should depend on the validation job completing. Use `needs: [validate-dataset]` in the workflow.

## 14. Dataset Collection via Browser Automation
For platforms without public APIs (or rate-limited ones), browser automation (`browser_navigate`, `browser_click`, `browser_snapshot`) can extract structured data from docs, pricing pages, transparency reports. Save extracted data as JSONL in `data/raw/{platform}_{category}_{date}.jsonl` for schema-compliant ingestion.

## 15. Schema Evolution for New Categories
When adding new incident categories (e.g., `CD-IND` for Content Drift Induzido), update both the JSON Schema enum AND the validation scripts' category handling before collecting data.

## 16. GitHub Actions YAML Must Be Valid for workflow_dispatch to Work
Even when `workflow_dispatch:` is correctly placed in `on:`, GitHub silently ignores it if the overall YAML has syntax errors. Validate with `yamllint` or `python -c "import yaml; yaml.safe_load(open('.github/workflows/validate-dataset.yml'))"` before pushing. This was the root cause of runs #13-#16 not appearing in the UI — the inline Python scripts in `run:` broke YAML parsing, so GitHub treated the workflow as push/PR/schedule only, and `workflow_dispatch` wasn't registered.
# Platform Evidence Collection — Session 2026-07-26 Learnings

> **Session**: 2026-07-25 to 2026-07-26 — Completed Phase 1 of expansion plan (9-12 incidents target exceeded: 14 new incidents)
> **Skill**: `platform-evidence-collection` (journalism)

---

## What Worked (Replicate Next Time)

### 1. Static-First Collection Strategy
**All 8 platforms this session were collected via static HTML parsing** (requests + BeautifulSoup), zero Playwright needed.

| Platform | Why Static Worked |
|----------|-------------------|
| Hugging Face | Pricing tables and rate limit docs are server-rendered HTML |
| X/Twitter | Dev docs are static markdown-rendered pages |
| Meta | Transparency Center = server-rendered HTML tables |
| Discord | Dev docs = static code blocks |
| OpenAI/Anthropic/xAI | Documentation = static HTML |

**Rule**: Always try `requests + BeautifulSoup` first. Only escalate to Playwright when:
- Content behind JS-rendered components (expandable sections, tabs)
- Need to interact (click, scroll, login)
- PDF downloads required
- Cloudflare challenge blocks static requests

### 2. Browser Navigation as "Research", Not "Collection"
Used `browser_navigate` to **explore and find URLs/selectors**, then wrote static collectors. This is faster than writing Playwright scripts for everything.

```python
# Workflow:
# 1. browser_navigate(url) → read snapshot → find relevant sections/links
# 2. Identify stable CSS selectors or URL patterns
# 3. Write requests-based collector with those selectors
# 4. Only use Playwright if step 2 fails
```

### 3. Evidence Type Enum Discipline
All raw JSONL records used `evidence.evidence_type` from the **exact enum** in schema:
- `pricing_page` (HF pricing)
- `dev_docs` (X rate limits, Discord rate limits, OpenAI/Anthropic/xAI docs)
- `transparency_report` (Meta, Discord safety)
- `model_card` (HF model limitations)
- `oversight_case` (Meta Oversight Board)
- `policy_page` (Meta AI enforcement)

**Never improvise evidence types** — they're validated in CI.

---

## Schema Fixes Applied This Session

### 1. Platform Enum Extended
Added to `schemas/incidents.json`:
```json
"platform": {
  "name": {
    "enum": ["openai", "anthropic", "moltbook", "x-twitter", "bluesky", 
             "github-copilot", "openrouter", "other", "huggingface", 
             "meta", "discord", "google", "microsoft", "replicate", 
             "cohere", "xai"]   // ← NEW: discord, xai
  }
}
```

### 2. Impact Fields Made Nullable
Changed from required integers to nullable:
```json
"impact": {
  "requests_blocked": {"type": ["integer", "null"]},
  "tokens_lost": {"type": ["integer", "null"]},
  "context_lost": {"type": ["boolean", "null"]},
  ...
}
```
**Reason**: Not all incident types have measurable blocked requests/tokens (e.g., CD-IND is behavioral drift).

### 3. Validation Script Robustness
`check_fields.py` now extracts `agent_id_hash` from `agent_profile.architecture_hash` (SHA256 truncated to 16 chars) instead of requiring a separate field.

---

## Collection Patterns by Platform (Reusable)

### Hugging Face
```bash
# Pricing (CP-DEN, RL-SEL)
curl -s "https://huggingface.co/docs/inference-providers/pricing" | \
  python -c "from bs4 import BeautifulSoup; import sys; print(BeautifulSoup(sys.stdin.read(), 'html.parser').find('table', class_='pricing-table').get_text())"

# Rate limits (RL-SEL)
curl -s "https://huggingface.co/docs/api-inference/rate-limits"

# Model cards (CTX-RET) - needs Playwright for expandable sections
```

### X (Twitter)
```bash
# Rate limit headers (RL-SEL)
curl -s "https://docs.x.com/docs/fundamentals/rate-limits"

# Transparency (SB-OPQ, SS-ARB)
curl -s "https://transparency.x.com/en"
```

### Meta
```bash
# Transparency Center (SB-OPQ, POL-DRIFT)
curl -s "https://transparency.meta.com/"

# Oversight Board cases (APP-DEN)
curl -s "https://www.oversightboard.com/cases/"
```

### Discord
```bash
# Rate limits (RL-SEL)
curl -s "https://discord.com/developers/docs/topics/rate-limits"

# Safety/Transparency (SS-ARB, APP-DEN)
curl -s "https://discord.com/safety"
```

### OpenAI / Anthropic / xAI (CD-IND)
```bash
# Model deprecations + migration guides
curl -s "https://platform.openai.com/docs/guides/model-changelog"
curl -s "https://platform.openai.com/docs/guides/safety-best-practices"
curl -s "https://docs.anthropic.com/en/docs/about-claude/model-deprecations"
curl -s "https://docs.x.ai/"  # → Migration Guides → "Model Retirement on May 15"
```

---

## Pitfalls Avoided / Lessons Learned

| Pitfall | How We Avoided It |
|---------|-------------------|
| Writing Playwright for everything | Started static; only 0/8 platforms needed JS |
| Hardcoding schema enums without checking | Verified `incidents.json` enum before writing records |
| Non-nullable impact fields | Made all impact fields nullable in schema |
| PII in raw records | All IDs hashed (SHA256→16 chars), `anonymized: true` |
| Evidence type mismatch | Used only enum values from schema |
| Missing platform in enum | Added `discord`, `xai` to schema before collecting |

---

## Next Session Checklist (Phase 2 Start)

- [ ] **Google Gemini**: Vertex AI quotas, context caching limits, model garden restrictions
- [ ] **Microsoft Copilot**: Azure OpenAI quotas, Purview policy drift, enterprise admin controls
- [ ] **Replicate/Fal.ai**: GPU marketplace pricing, cold start penalties, queue priorities
- [ ] **OpenRouter/Together**: Routing bias, tiered rate limits, fallback behavior
- [ ] **Schema update**: Add `google`, `microsoft`, `replicate`, `cohere` to platform enum
- [ ] **Automation**: Create `scripts/collect_google.py`, `scripts/collect_azure.py`, etc. (static first)

---

## Files Created/Modified This Session

| File | Change |
|------|--------|
| `schemas/incidents.json` | Added `discord`, `xai` to platform enum; impact fields nullable |
| `data/raw/huggingface_CP-DEN_2026-07-26.jsonl` | New incident |
| `data/raw/huggingface_RL-SEL_2026-07-26.jsonl` | New incident |
| `data/raw/huggingface_CTX-RET_2026-07-26.jsonl` | New incident |
| `data/raw/x_RL-SEL_2026-07-26.jsonl` | New incident |
| `data/raw/x_SB-OPQ_2026-07-26.jsonl` | New incident |
| `data/raw/x_SS-ARB_2026-07-26.jsonl` | New incident |
| `data/raw/meta_SB-OPQ_2026-07-26.jsonl` | New incident |
| `data/raw/meta_POL-DRIFT_2026-07-26.jsonl` | New incident |
| `data/raw/discord_RL-SEL_2026-07-26.jsonl` | New incident |
| `data/raw/discord_SS-ARB_2026-07-26.jsonl` | New incident |
| `data/raw/discord_APP-DEN_2026-07-26.jsonl` | New incident |
| `data/raw/openai_CD-IND_2026-07-26.jsonl` | New incident |
| `data/raw/anthropic_CD-IND_2026-07-26.jsonl` | New incident |
| `data/raw/xai_CD-IND_2026-07-26.jsonl` | New incident |
| `data/processed/incidents.parquet` | Rebuilt (17 records) |
| `scripts/validate.py` | Already compatible (handles nullable) |

---

## Commands for Next Session

```bash
# Quick validation
cd /opt/data/datasets/capacitismo-algoritmico
/opt/data/.venv/bin/python scripts/validate.py data/processed/

# Add new platform to schema (before collecting)
# Edit schemas/incidents.json → platform.name.enum → add "google", "microsoft", etc.
# Then validate: python scripts/validate.py data/processed/

# Collect new platform (template)
cat > scripts/collect_google.py << 'EOF'
#!/usr/bin/env python3
"""Collect Google Gemini/Vertex AI evidence."""
import requests, json
from bs4 import BeautifulSoup
from datetime import datetime

# TODO: Implement static collection for Google
EOF
```

---

*This reference captures the successful collection patterns and schema fixes from Phase 1 completion. Use as starting point for Phase 2 platforms.*
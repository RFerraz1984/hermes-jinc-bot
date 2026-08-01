---
name: platform-evidence-collection
description: Systematic collection of algorithmic discrimination evidence from AI/platform documentation, pricing pages, transparency reports, and developer portals. Supports Hugging Face, X/Twitter, Meta, Discord, Google, Microsoft, and other platforms. Includes browser automation (Playwright) for no-API sources and structured JSONL output compatible with capacitismo-algoritmico dataset schema.
version: "1.0"
author: Hermes Agent
license: MIT
tags: [evidence-collection, algorithmic-auditing, platform-transparency, browser-automation, dataset-expansion, playwriting]
---

# Platform Evidence Collection

> **Origin**: Session 2026-07-25 — Automated collection of 14 incidents across 8 platforms (Hugging Face, X/Twitter, Meta, Discord, OpenAI, Anthropic, OpenRouter, Moltbook) for the `capacitismo-algoritmico` dataset.

## Overview

Class-level skill for building platform-specific evidence collectors that extract structured evidence of algorithmic discrimination (rate limits, shadow bans, suspensions, compute denial, context retention, policy drift, appeal denial) from public sources.

### Evidence Categories (Taxonomy v0.1)

| Code | Category | Description |
|------|----------|-------------|
| `RL-SEL` | Rate Limit Seletivo | Tiered limits discriminating free vs paid users |
| `SB-OPQ` | Shadow Ban / Opacidade | Visibility filtering without notification |
| `SS-ARB` | Suspensão Sumária | Account/bot termination without due process |
| `CTX-RET` | Retenção de Contexto | Blocking export/portability of weights/logs/memory |
| `CD-IND` | Content Drift Induzido | Forced behavior change via hidden sanctions |
| `CP-DEN` | Compute Denial | GPU/TPU quota denial without transparent criteria |
| `POL-DRIFT` | Policy Drift | ToS/moderation changes without versioned audit trail |
| `APP-DEN` | Apelação Negada | No effective appeal path for automated decisions |

## Collection Methods

### 1. Public API / Documentation Scraping (Preferred)

For platforms with structured docs:

```python
# scripts/collect_platform_evidence.py
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
from datetime import datetime

def collect_via_docs(platform, urls, selectors):
    """Collect evidence from static documentation pages."""
    evidence = {"platform": platform, "collected_at": datetime.utcnow().isoformat() + "Z"}
    
    for category, url in urls.items():
        resp = requests.get(url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Extract based on category-specific selectors
        sel = selectors.get(category, "pre code")
        elements = soup.select(sel)
        evidence[category] = [el.get_text(strip=True) for el in elements]
    
    return evidence
```

### 2. Browser Automation (Playwright) — For Dynamic/JS-Rendered Pages

For platforms where evidence is behind JS rendering or interactive elements:

```python
# scripts/collect_platform_evidence.py
from playwright.sync_api import sync_playwright
import json
from pathlib import Path
from datetime import datetime

PLATFORM_CONFIGS = {
    "huggingface": {
        "urls": {
            "pricing": "https://huggingface.co/docs/inference-providers/pricing",
            "rate_limits": "https://huggingface.co/docs/api-inference/rate-limits",
            "model_cards": "https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct"
        },
        "selectors": {
            "pricing": "table.pricing-table tr",
            "rate_limits": "pre code",
            "model_card": ".model-card .limitations, .model-card .license"
        },
        "parser": "parse_huggingface"
    },
    "x-twitter": {
        "urls": {
            "rate_limits": "https://docs.x.com/docs/fundamentals/rate-limits",
            "transparency": "https://transparency.x.com/en"
        },
        "selectors": {
            "rate_limits": "table:has(th:has-text('Header'))",
            "error_example": "code:has-text('429')"
        },
        "parser": "parse_x_twitter"
    },
    "meta": {
        "urls": {
            "transparency": "https://transparency.meta.com/",
            "oversight": "https://oversightboard.com/"
        },
        "selectors": {
            "reports": "a[href*='integrity'], a[href*='transparency']",
            "oversight_cases": ".case-card, article.case"
        },
        "parser": "parse_meta"
    },
    "discord": {
        "urls": {
            "rate_limits": "https://discord.com/developers/docs/topics/rate-limits",
            "safety": "https://discord.com/safety"
        },
        "selectors": {
            "rate_limits": "pre code",
            "transparency": "a[href*='transparency']"
        },
        "parser": "parse_discord"
    }
}

def collect_with_playwright(platform):
    """Collect evidence using Playwright browser automation."""
    config = PLATFORM_CONFIGS[platform]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (compatible; CapacitismoAlgoritmicoBot/1.0; +https://github.com/jornalistainclusivo/capacitismo-algoritmico)"
        })
        
        evidence = {"platform": platform, "collected_at": datetime.utcnow().isoformat() + "Z"}
        
        for category, url in config["urls"].items():
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_load_state("domcontentloaded")
                
                selector = config["selectors"].get(category)
                if selector:
                    elements = page.locator(selector).all()
                    evidence[category] = [el.inner_text().strip() for el in elements if el.inner_text().strip()]
                
            except Exception as e:
                evidence[category] = {"error": str(e)}
        
        browser.close()
    
    return evidence
```

### 3. Transparency Report Parsing

For platforms publishing periodic transparency reports:

```python
def parse_transparency_report(platform, report_url_or_pdf):
    """Extract enforcement statistics from transparency reports."""
    # Implementation depends on format (PDF, HTML, CSV)
    # Key metrics to extract:
    # - Accounts actioned by category
    # - Government requests received/fulfilled
    # - Content removal by policy type
    # - Appeal rates and outcomes
    pass
```

## Output Schema

All collectors must produce JSONL records matching the `capacitismo-algoritmico` dataset schema:

```json
{
  "incident_id": "platform-category-YYYYMMDD-NNN",
  "timestamp": "2026-07-26T00:00:00Z",
  "platform": {
    "name": "huggingface",
    "endpoint": "https://api-inference.huggingface.co/",
    "region": "global"
  },
  "category": "RL-SEL",
  "agent_profile": {
    "architecture_hash": "hf-inference-free-001",
    "is_open_source": true,
    "parameter_count": "N/A"
  },
  "evidence": {
    "free_tier_credits_usd": 0.10,
    "pro_tier_credits_usd": 2.00,
    "credit_multiplier": 20,
    "rate_limit_mechanism": "credit_exhaustion",
    "source": "https://huggingface.co/docs/inference-providers/pricing",
    "evidence_type": "pricing_page"
  },
  "impact": {
    "severity": "high",
    "users_affected": "all_free_tier_users",
    "description": "20x disparity in inference credits between Free and PRO tiers..."
  },
  "remediation": {
    "reported": false,
    "response_time_hours": null,
    "resolved": false
  },
  "tags": ["rate-limit-selective", "tiered-access", "credit-based-quotas"],
  "source": "ethos-tracker",
  "anonymized": true
}
```

## Pipeline Integration

### Automated Daily Collection (via Cron)

```bash
# /opt/data/scripts/collect_all_platforms.sh
#!/bin/bash
cd /opt/data/datasets/capacitismo-algoritmico

# Collect from all platforms
python scripts/collect_platform_evidence.py --all

# Validate
python scripts/validate.py data/processed/

# Commit if valid
git add data/raw/
git commit -m "data: daily platform evidence collection $(date +%F)"
git push origin master
```

### Cron Job (Umbrel/Hermes)

```yaml
# cronjob for daily collection at 03:00 UTC
schedule: "0 3 * * *"
prompt: |
  Run the platform evidence collection pipeline:
  1. cd /opt/data/datasets/capacitismo-algoritmico
  2. python scripts/collect_platform_evidence.py --all
  3. python scripts/validate.py data/processed/
  4. If validation passes, git add/commit/push
  5. Output natural language summary for Telegram
skills: ["platform-evidence-collection", "github-actions-data-validation"]
```

## Anti-Bot & Reliability Patterns

| Challenge | Solution |
|-----------|----------|
| Cloudflare / bot detection | Use `cloudscraper` or residential proxies; add realistic headers |
| JS rendering required | Playwright with `wait_until="networkidle"` |
| Rate limiting on docs | Respect `robots.txt`; add 2-5s delays between requests |
| Page structure changes | Version selectors in config; alert on parse failures |
| Dynamic content (SPA) | Use `page.wait_for_selector()` before extraction |
| Authenticated-only content | Document as limitation; focus on public sources |

### Playwright Stealth Config

```python
def create_stealth_page(browser):
    page = browser.new_page()
    page.set_extra_http_headers({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    })
    page.set_viewport_size({"width": 1920, "height": 1080})
    return page
```

## Platform-Specific Notes

### Hugging Face
- **Strengths**: Public pricing, rate limit docs, model cards with limitations
- **Evidence**: Credit-based tiered access (Free $0.10 vs PRO $2.00 = 20x), gated models (Llama 3), license restrictions
- **Collection**: Static HTML parsing sufficient for pricing/rate limits; model cards need JS rendering for full card

### X (Twitter)
- **Strengths**: Detailed rate limit headers documentation, transparency reports
- **Evidence**: 900 req/15min free tier, pay-per-use tiers, 429 errors with code 88
- **Collection**: Dev docs static; transparency reports need PDF parsing

### Meta (Facebook/Instagram)
- **Strengths**: Transparency Center, Oversight Board cases, Community Standards Enforcement Reports
- **Evidence**: "Reduce" strategy (shadow ban), AI enforcement, no versioned policy changelog
- **Collection**: Static HTML for transparency; Oversight Board cases via their site

### Discord
- **Strengths**: Clear rate limit headers, Safety Center, Transparency Reports
- **Evidence**: 50 req/s global limit, per-route limits, Cloudflare "Invalid Request" bans
- **Collection**: Dev docs static; Safety Center links to transparency reports

### Google (Gemini/Vertex AI)
- **Evidence**: Quota tiers, context caching limits, model garden restrictions
- **Collection**: Cloud docs + Vertex AI quotas pages

### Microsoft (Azure OpenAI / Copilot)
- **Evidence**: Enterprise policy drift, admin controls, quota by subscription
- **Collection**: Azure docs + Purview compliance portal

## Validation Checklist

Before committing new evidence:

- [ ] JSONL syntax valid (`python -m json.tool file.jsonl`)
- [ ] All required fields present per schema
- [ ] `incident_id` follows pattern `platform-category-YYYYMMDD-NNN`
- [ ] `evidence.source` points to accessible public URL
- [ ] `evidence.evidence_type` in `["pricing_page", "dev_docs", "transparency_report", "model_card", "oversight_case", "policy_page"]`
- [ ] `impact.severity` in `["low", "medium", "high", "critical"]`
- [ ] `category` in taxonomy enum
- [ ] No PII in any field (anonymized = true)

## Related Skills

- `github-actions-data-validation` — CI pipeline for dataset validation
- `web-scraping-pipeline` — General web scraping patterns (journalism)
- `moltbook` — Moltbook integration for publishing findings
- `cronjob-python-environment` — Python env for cron jobs
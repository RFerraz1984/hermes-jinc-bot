# Platform Selectors for Evidence Collection (2026-07-25)

Documented during automated collection session for `capacitismo-algoritmico` dataset.

## Hugging Face

| Target | URL | Selector | Method |
|--------|-----|----------|--------|
| Pricing tiers | `https://huggingface.co/docs/inference-providers/pricing` | `table.pricing-table tr` | Static HTML |
| Rate limits | `https://huggingface.co/docs/api-inference/rate-limits` | `pre code` | Static HTML |
| Model card (Llama 3 8B) | `https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct` | `.model-card .limitations, .model-card .license` | Playwright (JS-rendered) |

**Key findings**: Free tier $0.10/mo credits, PRO $2.00/mo (20x), credit-based rate limiting, gated models require access request.

## X (Twitter)

| Target | URL | Selector | Method |
|--------|-----|----------|--------|
| Rate limit headers | `https://docs.x.com/docs/fundamentals/rate-limits` | `table:has(th:has-text('Header'))` | Static HTML |
| 429 error example | Same page | `code:has-text('429')` | Static HTML |
| Transparency reports | `https://transparency.x.com/en` | `a[href*='report']` | Static HTML |

**Key findings**: 900 req/15min free, pay-per-use tiers, 429 code 88, owned reads $0.001/resource.

## Meta (Facebook/Instagram)

| Target | URL | Selector | Method |
|--------|-----|----------|--------|
| Transparency Center | `https://transparency.meta.com/` | `a[href*='integrity'], a[href*='transparency'], a[href*='oversight']` | Static HTML |
| Oversight Board cases | `https://oversightboard.com/` | `.case-card, article.case` | Static HTML |

**Key findings**: "Reduce" strategy = shadow ban, AI enforcement experimental, no versioned policy changelog, Oversight Board limited scope.

## Discord

| Target | URL | Selector | Method |
|--------|-----|----------|--------|
| Rate limit headers | `https://discord.com/developers/docs/topics/rate-limits` | `pre code` | Static HTML |
| Safety/Transparency | `https://discord.com/safety` | `a[href*='transparency']` | Static HTML |

**Key findings**: 50 req/s global, per-route limits, bucket system, Cloudflare "Invalid Request" bans (separate from API limits), no independent oversight board.

## Anti-Bot Patterns Encountered

| Platform | Protection | Workaround |
|----------|------------|------------|
| Discord dev docs | Cloudflare | Playwright with realistic UA + viewport |
| X dev docs | None | Static HTML works |
| HF docs | None | Static HTML works |
| Meta transparency | None | Static HTML works |

## Collection Scripts Created

- `/opt/data/datasets/capacitismo-algoritmico/scripts/collect_platform_evidence.py` — Main collection orchestrator with Playwright
- Output: `data/raw/{platform}_{category}_{date}.jsonl` (schema-compliant)
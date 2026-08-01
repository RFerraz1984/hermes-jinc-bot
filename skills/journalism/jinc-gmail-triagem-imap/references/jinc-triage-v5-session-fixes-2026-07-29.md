# JINC Gmail Triagem v5 — Session Fixes & Current State (2026-07-29)

## Script Version: v5 Cumulative (LLM-Enhanced)

**Main script**: `/opt/data/scripts/jinc_gmail_triagem_15d.py` (~600 lines)
**Wrapper**: `/opt/data/scripts/jinc_gmail_triagem_15d_filtered.py` (51 lines)
**Cron Job ID**: `12d59b921ae1` — schedule `0 12,17,21 * * *` (3x/day UTC)

## Key Fixes Applied This Session

| Fix | File/Location | Description |
|-----|---------------|-------------|
| **max_tokens 1200 → 2000** | `call_llm()` function | Allows complete JSON responses from LLM classification |
| **Filename timestamp** | `generate_cumulative_markdown()` + main | `triagem-YYYY-MM-DD-HH-MM.md` — keeps 3 daily files distinct |
| **Telegram message timestamp** | Main return string | Shows `/opt/data/journali/triagem-{date}-{time}.md` |
| **Prompt brace escape** | `CLASSIFICATION_PROMPT` template | `{}` → `{{}}` to avoid `.format()` conflict |
| **Cumulative + delta reports** | `generate_cumulative_markdown()` + `generate_delta_markdown()` | Full 15-day history + new items this run |
| **Parse JSON robusto v2** | `parse_llm_response()` | Regex extraction + pipe-delimited fallback |
| **IMAP search optimization** | `search_emails_optimized()` | `SEARCH SINCE` + header fetch + keyword filter + selective RFC822 |
| **Execution limits** | `MAX_EMAILS_PER_RUN=100`, `MAX_PROCESSING_TIME=240s` | Prevents cron timeout (5 min) |

## Current Blockers

### 1. LLM Classification Discards Legitimate Emails
**Symptom**: 93 emails with "acessibilidade" found → 0 items classified as relevant (`Total de itens: 0`)
**Root cause**: `openrouter/auto` model classifies keyword-containing emails as `irrelevante`
**Solutions in progress**:
- Prompt rule: "se contém keyword monitorada → NUNCA irrelevante"
- Fallback: keyword-based forced classification when LLM returns `irrelevante` but body/subject has IMAP_KEYWORDS
- Test Brazilian models: `sabia-3`, `portuguese-gpt`, `meta-llama/llama-3.1-8b-instruct:free`, `google/gemma-2-9b-it:free`

### 2. Label Filter "JINC" Causes IMAP Timeout
**Symptom**: `SEARCH SINCE ... LABEL JINC` exceeds 30s timeout
**Workaround**: Search without label filter (finds 93 emails), then filter client-side
**Status**: Investigating if label filter removes relevant emails or is server-side slowness

## Cache State
- **Dedupe file**: `/opt/data/journali/processed-message-ids.jsonl` — 11 Message-IDs (proves emails read & processed)
- **Cumulative cache**: `/opt/data/journali/processed_items_cache.json` — 13 items persisted

## Output Samples (Latest Runs)
| File | Size | Type |
|------|------|------|
| `triagem-2026-07-28-21-19.md` | 11.9K | Cumulative (15 days) |
| `triagem-2026-07-28-21-24.md` | 11.9K | Cumulative (15 days) |
| `triagem-delta-2026-07-28-21-19.md` | ~500B | Delta (new this run) |
| `triagem-delta-2026-07-28-21-24.md` | ~500B | Delta (new this run) |

Markdown structure: tables, sections, metadata (Message-ID, date, subject, sender, keywords, summary, angles), grouped by type (releases/pautas), chronological order.

## MCP Server Fixes (This Session)

### Tavily MCP — FIXED ✅
```yaml
# Before (broken in headless container)
auth: oauth
headers:
  Authorization: ''  # empty

# After (working)
auth: none
headers:
  Authorization: 'Bearer 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'
```
**Cause**: OAuth flow requires interactive TTY — impossible in container
**Fix**: `auth: none` + API key in header (from `/opt/data/.env` `TAVILY_API_KEY`)

### Time MCP — Config Updated ⚠️ AWAITING TEST
```yaml
time:
  args: ["-y", "@modelcontextprotocol/server-time"]
  command: npx
  enabled: true
```
**Issue**: `Connection closed` when Hermes tries to connect to stdio npx process
**Status**: Config fixed (args as proper YAML array), user confirmed "sim, teste" — awaiting verification

## Cron Job Verification
```
✅ hermes cron run 12d59b921ae1 → exit 0, generated triagem-2026-07-28-21-24.md
✅ python3 scripts/jinc_gmail_triagem_15d_filtered.py → exit 0, smart_notify_filter integration OK
```

## Next Steps Priority
1. **Fix LLM classification** — adjust prompt + fallback keyword-based
2. **Validate Markdown rendering** — confirm tables/sections/metadata format clean, metadata complete
3. **Test MCP Time Server** — verify `get_current_time`, `convert_time` tools work
4. **IMAP label filter debug** — isolate `SEARCH SINCE + LABEL JINC` behavior
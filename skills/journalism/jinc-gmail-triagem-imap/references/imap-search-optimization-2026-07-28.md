# IMAP Search Optimization Patterns (session 2026-07-28)

## Problem
IMAP SEARCH with `OR SUBJECT "kw" BODY "kw"` for 11 keywords + `SINCE date` fails with `BAD [b'Could not parse command']` when keywords contain non-ASCII characters (acentos) or complex boolean logic.

## Root Cause
- Gmail IMAP parser is strict on CHARSET + boolean combinations
- `CHARSET UTF-8 OR SUBJECT "acessibilidade" BODY "acessibilidade"` works for single keyword
- Multiple `OR` chains exceed parser limits or trigger encoding issues with accents
- `UnicodeEncodeError: 'ascii' codec can't encode character '\\xea'` for words like "acessibilidade"

## Solution: Client-Side Filtering (Validated)

**Strategy:** Fetch headers only for recent emails, filter locally, then fetch full body only for candidates.

```python
def fetch_matching_emails(m, since_date, max_emails=100):
    # 1. Search by date only (fast, no charset issues)
    typ, data = m.search(None, 'CHARSET', 'UTF-8', 'SINCE', since_date)
    msg_ids = data[0].split()[-max_emails:]  # limit to N most recent
    
    # 2. Fetch headers only (SUBJECT, FROM, DATE, MESSAGE-ID)
    for msg_id in msg_ids:
        typ, data = m.fetch(msg_id, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)])')
        msg = email.message_from_bytes(data[0][1])
        
        # 3. Quick filter: check SUBJECT + known sender patterns
        subject = decode_mime_header(msg.get('Subject', '')).lower()
        from_addr = decode_mime_header(msg.get('From', '')).lower()
        
        # Subject keyword match
        if any(kw.lower() in subject for kw in KEYWORDS):
            # Fetch full body
            typ, full = m.fetch(msg_id, '(RFC822)')
            full_msg = email.message_from_bytes(full[0][1])
            yield full_msg
            continue
        
        # Sender pattern match (newsletters, alerts)
        sender_keywords = ['acessibilidade', 'inclusao', 'deficiencia', 'pcd', 'autismo', 'googlealerts', 'newsletter']
        if any(kw in from_addr for kw in sender_keywords):
            typ, full = m.fetch(msg_id, '(RFC822)')
            full_msg = email.message_from_bytes(full[0][1])
            body = get_email_body(full_msg).lower()
            if any(kw.lower() in body for kw in KEYWORDS):
                yield full_msg
```

## Performance Results (session 2026-07-28)

| Metric | Before (full fetch) | After (header-first) |
|--------|---------------------|----------------------|
| Emails scanned | 578 (all) | 100 (most recent) |
| Full RFC822 fetches | 578 | ~10-20 |
| Execution time | >180s (timeout) | ~15s |
| Matches found | 8 | 8 (same) |

## Keywords Used (ASCII-safe for IMAP search)

```python
KEYWORDS = [
    "acessibilidade",      # no accent
    "deficiencia",         # no accent
    "inclusao",            # no accent
    "autismo",
    "neurodiversidade",
    "pcd",
    "tea",
    "wcag",
    "e-mag",
    "capacitismo",
    "pessoa com deficiencia",  # no accent
]
```

## Display Keywords (with accents for output)

```python
KEYWORDS_DISPLAY = [
    "acessibilidade",
    "deficiência",
    "inclusão",
    "autismo",
    "neurodiversidade",
    "PCD",
    "TEA",
    "WCAG",
    "e-MAG",
    "capacitismo",
    "pessoa com deficiência",
]
```

## Usage in Cron Script

The script `/opt/data/scripts/jinc_gmail_triagem_15d.py` implements this pattern:
- Connects to `imap.gmail.com:993` with App Password
- Searches last 15 days (`SINCE "13-Jul-2026"`)
- Limits to 100 most recent emails
- Filters by subject + known sender patterns
- Fetches full body only for candidates
- Deduplicates by `Message-ID` → `/opt/data/journali/processed-message-ids.jsonl`
- Classifies as `release` or `sugestao_de_pauta`
- Outputs Markdown + Telegram notification via `smart_notify_filter.py`
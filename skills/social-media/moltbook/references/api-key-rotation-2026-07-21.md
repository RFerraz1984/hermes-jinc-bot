# API Key Rotation Procedure — 2026-07-21

## Context
Executed full Moltbook API key rotation after discovering exposed credentials in skill documentation, scripts, and cron outputs. New key generated in Moltbook dashboard, local credentials updated, all references redacted.

## Steps Executed

### 1. Identify Exposure
- **Pattern**: `moltbook_sk_7lPJYqAkI6z1Ov992JjxCM5EmuOjCXqk`
- **Files affected**: 120+ files across:
  - `/opt/data/skills/social-media/moltbook/SKILL.md`
  - `/opt/data/skills/social-media/moltbook/references/api_session_2026-07-19.md`
  - `/opt/data/post_*.py` (4 scripts with embedded key)
  - `/opt/data/cron/output/**/*.md` (cron job outputs)
  - `/opt/data/sessions/**/*.json` (session dumps)
  - `/opt/data/cron/jobs.json`

### 2. Generate New Key in Moltbook Dashboard
1. Access https://www.moltbook.com → "👤 I'm a Human" → magic link login
2. Owner Dashboard → Agents → `jornalista_inclusivo_bot` → API Key
3. **Revoke** old key (immediate invalidation)
4. **Generate New** → copy immediately (shown once)
5. Store in password manager: `Moltbook – jornalista_inclusivo_bot – API Key`

### 3. Update Local Credentials
```bash
# Using update script (created for this)
/opt/data/scripts/update_moltbook_key.sh "moltbook_sk_NEW_KEY_HERE"
```
Script does:
- Backup `/opt/data/moltbook_ethos_tracker.json` to `/opt/data/backups/cred-rotation/`
- Update `api_key` field in JSON
- `chmod 600` on credentials file
- Attempt `hermes gateway restart`

### 4. Validate New Key
```bash
# Check status via helper
python3 /opt/data/skills/social-media/moltbook/scripts/moltbook_helpers.py status

# Direct API call
curl -H "Authorization: Bearer NEW_KEY" https://www.moltbook.com/api/v1/agents/status
# Expected: {"success": true, "data": {"claimed": true, ...}}
```

### 5. Redact Old Key from All Files
```bash
# API key
find /opt/data -type f \( -name "*.md" -o -name "*.json" -o -name "*.py" -o -name "*.log" -o -name "*.txt" \) \
  -exec sed -i 's/moltbook_sk_7lPJYqAkI6z1Ov992JjxCM5EmuOjCXqk/<REDACTED_MOLTBOOK_API_KEY>/g' {} \;

# Verification code
find /opt/data -type f \( -name "*.md" -o -name "*.json" -o -name "*.py" -o -name "*.log" -o -name "*.txt" \) \
  -exec sed -i 's/bay-2P6A/<REDACTED_VERIFICATION_CODE>/g' {} \;

# Claim URL
find /opt/data -type f \( -name "*.md" -o -name "*.json" -o -name "*.py" -o -name "*.log" -o -name "*.txt" \) \
  -exec sed -i 's#https://www.moltbook.com/claim/moltbook_claim_[A-Za-z0-9]*#<REDACTED_CLAIM_URL>#g' {} \;
```

### 6. Update Scripts to Load from Credentials File
All 4 posting scripts (`post_accessibility.py`, `post_ai_rights.py`, `post_algorithmic_auditing.py`, `post_ethics.py`) refactored to:
```python
import json, os

creds_path = '/opt/data/moltbook_ethos_tracker.json'
with open(creds_path) as f:
    creds = json.load(f)
api_key = creds.get('api_key')
# Use api_key for Authorization header
```

### 7. Verify No Residual Exposure
```bash
grep -r "moltbook_sk_" /opt/data --exclude-dir=.git --exclude-dir=backups 2>/dev/null | grep -v REDACTED
# Should return empty
```

## Files Created/Modified

### New Utility Script
- `/opt/data/scripts/update_moltbook_key.sh` — idempotent key rotation with backup

### Sanitized Documentation
- `skills/social-media/moltbook/SKILL.md` — placeholders instead of real keys
- `skills/social-media/moltbook/references/api_session_2026-07-19.md` — placeholders

### Refactored Scripts
- `/opt/data/post_accessibility.py`
- `/opt/data/post_ai_rights.py`
- `/opt/data/post_algorithmic_auditing.py`
- `/opt/data/post_ethics.py`

## Verification Checklist
- [x] New key works (agent status = claimed + active)
- [x] Old key revoked in Moltbook dashboard
- [x] Credentials file updated + chmod 600
- [x] All scripts load from credentials file (no hardcoded keys)
- [x] All documentation uses placeholders
- [x] Cron outputs redacted
- [x] Session dumps redacted
- [x] No grep hits for raw key pattern

## Rotation Schedule
- **Recommended**: Every 90 days, or immediately upon suspected exposure
- **Next due**: ~2026-10-19
- **Automation**: Monthly reminder cron `0528ad2c657b` (1st of month, 09:00)
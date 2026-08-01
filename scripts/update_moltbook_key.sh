#!/usr/bin/env bash
set -euo pipefail

CREDS_FILE="/opt/data/moltbook_ethos_tracker.json"
BACKUP_DIR="/opt/data/backups/cred-rotation"
NEW_KEY="$1"

if [[ -z "$NEW_KEY" ]]; then
  echo "Usage: $0 <NEW_MOLTBOOK_API_KEY>"
  exit 2
fi

mkdir -p "$BACKUP_DIR"
TS=$(date +%F_%H%M%S)
if [[ -f "$CREDS_FILE" ]]; then
  cp "$CREDS_FILE" "$BACKUP_DIR/moltbook_ethos_tracker.json.$TS"
  echo "Backup saved: $BACKUP_DIR/moltbook_ethos_tracker.json.$TS"
else
  echo "Warning: creds file not found. Creating new one at $CREDS_FILE"
  mkdir -p "$(dirname "$CREDS_FILE")"
  cat > "$CREDS_FILE" <<EOF
{
  "api_key": "<REDACTED_MOLTBOOK_API_KEY>",
  "agent_id": "952f2850-05ae-435f-aae3-974fe3616e79",
  "name": "jornalista_inclusivo_bot",
  "description": "Ethos.Tracker — crawler analítico de governança sintética",
  "claim_url": "<REDACTED_CLAIM_URL>",
  "verification_code": "<REDACTED_VERIFICATION_CODE>",
  "profile_url": "https://www.moltbook.com/u/jornalista_inclusivo_bot",
  "created_at": "2026-07-19T16:53:37.753Z",
  "status": "claimed"
}
EOF
fi

# Update api_key field in JSON (minimal, robust)
python3 - <<PY
import json
p='''$CREDS_FILE'''
new='$NEW_KEY'
with open(p,'r') as f:
    data=json.load(f)
data['api_key']=new
with open(p,'w') as f:
    json.dump(data,f,indent=2)
print('Updated',p)
PY

chmod 600 "$CREDS_FILE"

# Restart Hermes gateway so new key is picked up (best-effort)
if command -v /opt/hermes/bin/hermes >/dev/null 2>&1; then
  /opt/hermes/bin/hermes gateway restart || echo "hermes gateway restart failed; restart Hermes app manually"
fi

echo "Done. New key written and Hermes gateway restarted (if available)."

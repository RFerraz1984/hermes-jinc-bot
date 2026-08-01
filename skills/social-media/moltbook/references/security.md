Secure handling for Moltbook credentials & docs

Purpose: concrete steps to keep API keys and verification codes out of documentation and logs.

Rules
- Store keys only in /opt/data/moltbook_ethos_tracker.json or in /opt/data/.env (consistent with Hermes policies). File perms: chmod 600.
- Never embed keys in SKILL.md, references/*.md, cron outputs, or scripts. Use placeholder text like <REDACTED_MOLTBOOK_API_KEY> in docs.
- Backups: exclude secrets from auto backups. Use the selective backup script (/opt/data/scripts/backup-hermes-selective.sh) which excludes secrets and caches.
- Logs: rotate and redact logs that contain tokens. After rotation, run a one-time redact: replace occurrences of known tokens with <REDACTED> in cron/output/* and archive originals in /opt/data/backups/.
- Rotation: rotate API keys on suspicion or every 90 days. Use /opt/data/scripts/update_moltbook_key.sh to update local file and restart gateway.

How to rotate (quick steps)
1. Revoke old key in Moltbook dashboard.
2. Generate new key and copy it safely.
3. Run: /opt/data/scripts/update_moltbook_key.sh <NEW_KEY>
4. Verify: curl -H "Authorization: Bearer <NEW_KEY>" https://www.moltbook.com/api/v1/agents/status
5. Redact logs: (optional) run redact script to remove old key from cron outputs.

Emergency
- If key leaked publicly: revoke immediately and run rotation. Archive old logs for audit; do not publish them.

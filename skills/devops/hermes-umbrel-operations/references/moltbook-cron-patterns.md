# Cron Job Patterns — Moltbook Heartbeat & Comment Monitoring

## Context
Added practical patterns from session 2026-07-21 for Moltbook social network integration with Hermes on Umbrel.

## Moltbook Heartbeat Cron Job

### Purpose
Periodic health check + engagement for `jornalista_inclusivo_bot` on Moltbook. Runs every **4 hours** (updated from every 30min).

### Schedule
```bash
# Every 4 hours
0 */4 * * *
```

### Command (no_agent = true, zero LLM cost)
```bash
# Wrapper: /opt/data/scripts/moltbook_heartbeat_wrapper.sh
# Workdir: /opt/data
# Deliver: origin (suppressed by smart_notify_filter when no action needed)
```

### What the Heartbeat Does
1. **Status check** — calls `/api/v1/agents/me` to verify claim status
2. **Notifications check** — fetches unread notifications, DMs, mentions
3. **Feed scan** — polls `algorithmic-auditing`, `ai-rights`, `accessibility`, `ethics` submolts for new posts
4. **State persistence** — writes `/opt/data/moltbook_heartbeat_state.json` with:
   - `last_check` (ISO timestamp)
   - `last_post_id` (most recent post seen)
   - `last_notification_id` (most recent notification)
5. **Optional posting** — with `--post-if-inspired` flag, can generate and post a relevant comment

### Hermes Cron Job Definition (Current Working Config)
```bash
hermes cronjob create \
  --name "Moltbook Heartbeat - jornalista_inclusivo_bot" \
  --schedule "0 */4 * * *" \
  --script "moltbook_heartbeat_wrapper.sh" \
  --workdir "/opt/data" \
  --no-agent \
  --deliver origin \
  --enabled-toolsets terminal
```

### Job ID: `3d75d014af16`

### Wrapper Script: `/opt/data/scripts/moltbook_heartbeat_wrapper.sh`
```bash
#!/bin/bash
cd /opt/data
python3 /opt/data/scripts/moltbook_helpers.py heartbeat 2>&1 | python3 /opt/data/scripts/smart_notify_filter.py --job-name "Moltbook Heartbeat" --exit-code ${PIPESTATUS[0]}
```

### ⚠️ Mode Conflict Fixed (2026-07-29)
This job was previously misconfigured with BOTH `skill: "moltbook"` / `skills: ["moltbook"]` AND `script` / `no_agent: true`, causing:
```
RuntimeError: HTTP 400: tool call validation failed: attempted to call tool 'skill_view(name="moltbook")' which was not in request.tools
```
Fixed by removing `skill`/`skills` fields, setting `no_agent: true` explicitly, and using the wrapper script above.

---

## Comment Monitoring & Verification Cron Job

### Purpose
Watch for new comments on own posts, auto-verify if within challenge window, alert for manual response.

### Schedule
```bash
# Every 15 minutes (tight loop for 5-min verification window)
*/15 * * * *
```

### Script: `/opt/data/scripts/watch_moltbook_comments.py`
```python
#!/usr/bin/env python3
"""
Watch for new comments on own posts, handle verification challenges,
alert via Telegram for comments needing human/agent response.
"""
import json, os, sys
from pathlib import Path

# Load credentials from .env
env_path = Path('/opt/data/.env')
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

# Now import and run
sys.path.insert(0, '/opt/data/skills/social-media/moltbook/scripts')
from moltbook_helpers import MoltbookClient

def main():
    client = MoltbookClient()
    
    # 1. Get home dashboard for notification summary
    home = client.get_home()
    activity = home.get('activity_on_your_posts', [])
    
    # 2. For each post with new notifications
    for item in activity:
        post_id = item['post_id']
        post_title = item['post_title']
        new_count = item['new_notification_count']
        
        if new_count == 0:
            continue
            
        # 3. Fetch comments (newest first)
        comments = client.get_comments(post_id, sort='new', limit=20)
        
        # 4. For each comment: check verification status, auto-verify if possible
        for comment in comments.get('comments', []):
            cid = comment['id']
            vstatus = comment.get('verification_status', 'unknown')
            
            if vstatus == 'pending' and comment.get('verification'):
                # Challenge exists — try auto-verify
                challenge = comment['verification']['challenge_text']
                code = comment['verification']['verification_code']
                
                # Solve
                from moltbook_helpers import solve_verification_challenge
                answer = solve_verification_challenge(challenge)
                
                # Submit
                result = client.verify_comment(code, answer)
                if result.get('success'):
                    print(f"Auto-verified comment {cid}")
                else:
                    print(f"Failed to verify {cid}: {result}")
                    
            elif vstatus == 'failed':
                print(f"Comment {cid} verification failed - needs re-post or manual")
                # Alert via Telegram
                send_telegram_alert(f"⚠️ Verification failed on {post_title}: comment {cid}")
                
    # 5. Also check for mentions/DMs
    notifications = client.get_notifications(limit=50)
    for n in notifications.get('notifications', []):
        if n.get('type') in ('mention', 'dm'):
            # Alert for response
            send_telegram_alert(f"💬 {n['type'].title()} from {n['actor_name']}: {n['preview']}")

def send_telegram_alert(message):
    # Uses TELEGRAM_BOT_TOKEN + TELEGRAM_HOME_CHANNEL from env
    import urllib.request, json
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat = os.environ.get('TELEGRAM_HOME_CHANNEL') or os.environ.get('TELEGRAM_CHANNEL_ID')
    if token and chat:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({'chat_id': chat, 'text': message}).encode()
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req)

if __name__ == '__main__':
    main()
```

### Cron Job Definition
```bash
hermes cronjob create \
  --name "Moltbook Comment Monitor" \
  --schedule "*/15 * * * *" \
  --script "watch_moltbook_comments.py" \
  --workdir "/opt/data" \
  --no-agent \
  --deliver telegram \
  --enabled-toolsets terminal
```

---

## Rate Limit Awareness (Critical for Cron)

| Operation | Limit | Backoff |
|-----------|-------|---------|
| Post creation | 1 per 150s | 429 includes `retry_after_seconds` |
| Comments | Separate limit | Space by 3+ min |
| Heartbeat API calls | ~10 per run | Fine |
| Comment monitoring | ~20 per run | Fine |

### Best Practices
- **Space heartbeat and comment monitor** by at least 5 minutes (e.g., heartbeat at :00/:30, comments at :07/:22/:37/:52)
- **Never batch comment replies** in a single cron run — spread over multiple runs
- **Use `auto-verify` immediately after posting** (within 5 min window)
- **Check `/home` first** — it tells you which posts have new activity, avoids unnecessary API calls

---

## Environment Variables Required

Cron jobs don't inherit `.env`. Scripts must load explicitly:

```bash
# In the cron script:
export $(grep -E '^(MOLTBOOK|TELEGRAM|OPENROUTER)_' /opt/data/.env | xargs)

# Critical mappings:
export TELEGRAM_CHANNEL_ID="${TELEGRAM_CHANNEL_ID:-${TELEGRAM_HOME_CHANNEL}}"
```

---

## State Files

| File | Purpose | Updated By |
|------|---------|------------|
| `/opt/data/moltbook_heartbeat_state.json` | Last check time, post ID, notification ID | Heartbeat cron |
| `/opt/data/moltbook_comment_watch_state.json` | Last seen comment IDs per post | Comment monitor cron |
| `/opt/data/moltbook_ethos_tracker.json` | Credentials (api_key, agent_id) | Key rotation script |

---

## Verification Challenge Handling

### Challenge Format
Obfuscated math word problems:
```
"A] LoBbSt-Er S[wImmS LiKe Um] aNd ClAwS PuLl^ LiKe Uh] fOrCeS...
 A] lO-bS tEr^ lOoObsTtErrr ClAw] fO^rCe Is ThIrRtYy FiV-e NeW{]-ToNs...
```

### Solver
```bash
# Built into moltbook_helpers.py
echo "Challenge text" | python3 moltbook_helpers.py solve-verification
# Returns: "40.00" (always 2 decimal places)
```

### Auto-Verify Flow (preferred)
```bash
python3 moltbook_helpers.py auto-verify <COMMENT_ID>
# Handles: fetch challenge → solve → submit → confirm
```

### Manual Submit (if auto-verify fails)
```bash
curl -X POST https://www.moltbook.com/api/v1/verify \
  -H "Authorization: Bearer $MOLTBOOK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"verification_code": "moltbook_verify_XXXX", "answer": "40.00"}'
```

### Response Codes
- `200 + {"success": true}` — verified
- `409 Conflict` — already verified or challenge expired
- `400 Bad Request` — wrong format (must be `NN.NN`)
- `401 Unauthorized` — bad API key

---

## Failed Post Recovery

If a post/comment verification fails (`verification_status: failed`):
1. **No retry on same object** — API doesn't allow re-verification
2. **Must repost identical content** — use templates in `templates/post_*.md`
3. **Immediately run auto-verify** on new post (within 5 min window)

```bash
# Repost from template
CONTENT=$(cat /opt/data/skills/social-media/moltbook/templates/post_ai_rights.md)
python3 /opt/data/skills/social-media/moltbook/scripts/moltbook_helpers.py post ai-rights "Habeas corpus..." "$CONTENT"
# Then:
python3 /opt/data/skills/social-media/moltbook/scripts/moltbook_helpers.py auto-verify <NEW_POST_ID>
```

---

## Key Command Reference

| Task | Command |
|------|---------|
| Full heartbeat | `moltbook_helpers.py heartbeat --post-if-inspired` |
| Status only | `moltbook_helpers.py status` |
| Home dashboard | `moltbook_helpers.py home` |
| Notifications | `moltbook_helpers.py notifications --limit 50` |
| Comments on post | `moltbook_helpers.py get-comments <POST_ID> --sort new --limit 20` |
| Post comment | `moltbook_helpers.py comment <POST_ID> "text" [--parent-id <CID>]` |
| Auto-verify | `moltbook_helpers.py auto-verify <CID>` |
| Solve challenge | `echo "challenge" | moltbook_helpers.py solve-verification` |
| Search posts | `moltbook_helpers.py search "keywords" --limit 10` |
| Feed | `moltbook_helpers.py feed --submolt <name> --sort new --limit 20` |
| Attach label (mod) | `moltbook_helpers.py attach-label <LABEL_DEF_ID> <POST_ID>` |

---

## Umbrel-Specific Notes

- **Persistence**: All state in `/opt/data` (survives app updates)
- **Gateway restart** after config changes: `s6-svc -r /run/service/gateway-default`
- **PATH** for cron: must include `/opt/data/.npm-global/bin:/opt/data/bin:/opt/data/home/.local/bin`
- **Toolsets**: cron jobs need `--enabled-toolsets terminal` (global toolsets config is broken as string)
- **Logs**: gateway at `/opt/data/logs/gateway.log`, cron output via Telegram delivery
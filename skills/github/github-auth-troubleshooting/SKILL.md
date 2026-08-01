---
name: github-auth-troubleshooting
description: "Troubleshooting GitHub authentication issues — token types, scopes, 401 errors, credential helpers, and common pitfalls for Hermes Agent on Umbrel."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Authentication, Troubleshooting, Token, Umbrel, 401]
    related_skills: [github-auth, github-repo-management]
---

# GitHub Authentication Troubleshooting

This skill covers diagnosing and fixing GitHub authentication failures when working with Hermes Agent in containerized environments (Umbrel, Docker, etc.).

## Common Failure: 401 Bad Credentials with Fine-Grained PAT

### Symptom
```bash
curl -H "Authorization: token $TOKEN" https://api.github.com/user
# {"message": "Bad credentials", "documentation_url": "...", "status": "401"}
```

Token in `/opt/data/.github-token` starts with `github_pat_` (fine-grained) instead of `ghp_` (classic).

### Root Cause
Fine-grained Personal Access Tokens **cannot create repositories** on user accounts and often fail with 401 for API operations that classic tokens handle. GitHub's API returns generic "Bad credentials" rather than a clear scope error.

### Fix
1. Create a **Classic PAT** at https://github.com/settings/tokens
   - Click **"Generate new token (classic)"** — NOT "Fine-grained token"
   - Name: `hermes-agent`
   - Scopes: ✅ `repo` (required for repo create/push), ✅ `workflow` (optional, for Actions)
   - Expiration: 90 days recommended
2. Update token file in container:
   ```bash
   echo "ghp_YOUR_NEW_CLASSIC_TOKEN" > /opt/data/.github-token
   chmod 600 /opt/data/.github-token
   ```
3. Verify:
   ```bash
   TOKEN=$(cat /opt/data/.github-token) && curl -s -H "Authorization: token $TOKEN" https://api.github.com/user
   ```
4. Configure git credential helper (one-time in container):
   ```bash
   git config --global credential.helper store
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   git ls-remote https://github.com/youruser/any-repo.git
   # Username: your-github-username
   # Password: paste the ghp_ token
   ```

### Real-World Case (This Project — 2026-07-21)
- Created 3 fine-grained PATs (`github_pat_...`) — all failed with 401 on repo creation
- Classic PAT (`ghp_...`) worked immediately for both API (`/user`) and repo creation (`/user/repos`)
- Token stored at `/opt/data/.github-token` (chmod 600)
- Git credential helper `store` configured → credentials cached in `~/.git-credentials`
- Remote URL rewritten to embed token: `https://RFerraz1984:ghp_...@github.com/RFerraz1984/hermes-jinc-bot.git`

### Real-World Case 2 — Org Transfer & Token Verification (2026-07-25)
**Scenario**: Repo transferred from personal account `RFerraz1984` → organization `jornalistainclusivo` (note: **no hyphen** in org name). Token `hermes-agent` (classic PAT, created by `RFerraz1984`) needed to work on transferred repo.

**Key Learnings**:
1. **Org name matters**: `jornalistainclusivo` (no hyphen) ≠ `jornalista-inclusivo` (with hyphen). README clone URL was wrong (had hyphen), fixed to `git clone https://github.com/jornalistainclusivo/capacitismo-algoritmico.git`

2. **Classic PAT + Org transfer**: Token created by user `RFerraz1984` works on org repos **automatically** if:
   - User is Owner/Member with Write/Admin on the repo
   - Token has `repo` scope (classic PAT)
   - No "Authorize" button needed for classic tokens — it's based on user's org membership

3. **Token in `.env` was truncated**: `/opt/data/.env` showed `ghp_tw...dmlB` (truncated display). Actual token: `[REDACTED]` (40 chars, classic PAT `ghp_...`). **Always verify full token** with `grep GITHUB_TOKEN /opt/data/.env | cut -d'=' -f2- | wc -c` (should be 41 with newline) or `cat -A`.

4. **401 Bad credentials root cause**: Token was correct but shell variable `$GITHUB_TOKEN` was empty. The token in `.env` wasn't exported. Fix: `export GITHUB_TOKEN=$(grep GITHUB_TOKEN /opt/data/.env | cut -d'=' -f2-)` then test with `curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user`

5. **After transfer**: Remote URL must be updated: `git remote set-url origin https://github.com/jornalistainclusivo/capacitismo-algoritmico.git`

5. **README clone URL must match org name**: Corrected from `jornalista-inclusivo` → `jornalistainclusivo` (no hyphen)

### Token Format Quick Reference
| Prefix | Type | Length | Can Create Repos? | API Access |
|--------|------|--------|-------------------|------------|
| `ghp_` | Classic | **40 chars total** (`ghp_` + 36) | ✅ Yes | Full (scoped) |
| `github_pat_` | Fine-grained | ~93 chars | ❌ No (user account) | Limited |

> **Correction (2026-07-21)**: Classic PATs are SHORT (40 chars), not long. Do not assume a 40-char `ghp_` token is truncated/invalid just because it "looks short" — verify with a live API call (`curl -H "Authorization: token $TOKEN" https://api.github.com/user`) before concluding the token itself is the problem. A `401 Bad credentials` on a well-formed 40-char `ghp_` token usually means the token was **revoked/rotated**, not malformed — ask the user to confirm which token is current before hypothesizing about format.

## `gh` CLI vs raw REST API — Scope Mismatch Pitfall (2026-07-21)

### Symptom
```bash
$ gh auth login --with-token <<< "$TOKEN"
error validating token: missing required scope 'read:org'
```
But the same token works fine for direct REST calls:
```bash
curl -H "Authorization: token $TOKEN" https://api.github.com/user   # 200 OK
curl -X POST https://api.github.com/user/repos -H "Authorization: token $TOKEN" -d '{...}'  # 201 Created
```

### Root Cause
The `gh` CLI's `auth login --with-token` validates the token against a broader set of scopes than the REST endpoints it will actually be used for — it wants `read:org` even for pure user-repo operations. A Classic PAT scoped to just `repo` + `workflow` is enough for repo create/push/labels but fails `gh auth login`'s own validation gate.

### Fix — Skip `gh` entirely, use git + curl directly
When `gh auth login` rejects a token that clearly works via curl, don't chase more scopes — just bypass `gh` for that operation:

```bash
# Create repo via REST directly
curl -X POST https://api.github.com/user/repos \
  -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github.v3+json" \
  -d '{"name":"repo-name","description":"...","private":false}'

# Push via git with token embedded in remote URL (no credential helper needed)
git remote set-url origin https://$TOKEN@github.com/OWNER/REPO.git
git push -u origin master
```

This is the same pattern documented above for git credential pitfalls — reuse it rather than re-adding `read:org` to the token (adding org-read scope to a personal-repo-only token is an unnecessary permission expansion).

### When `gh` IS worth fixing scopes for
If you genuinely need `gh`-specific features (branch protection API sugar, `gh repo create --confirm` interactive flow, Actions permission toggling), then add `read:org` to the Classic PAT scopes. Otherwise, prefer the git+curl fallback — it's one less scope to rotate/audit later.

## Container/Credential Helper Pitfalls (Umbrel/Docker)

### Symptom
Token works in `curl` but `git push` fails, or credentials don't persist.

### Cause
- No git credential helper configured in container
- Token embedded in remote URL gets lost on repo re-clone
- `credential.helper store` saves to plaintext `~/.git-credentials` (works in container)

### Fix
```bash
# One-time setup in container
git config --global credential.helper store
git config --global user.name "Your Name"
git config --global user.email "you@example.com"

# Test - will prompt once, then cache
git ls-remote https://github.com/youruser/any-repo.git
# Username: your-github-username
# Password: paste the ghp_ token
```

### Alternative: Token in Remote URL (per-repo, no helper needed)
```bash
git remote set-url origin https://<username>:<ghp_token>@github.com/<owner>/<repo>.git
```

## Debugging Checklist

When GitHub API returns 401:
1. `cat /opt/data/.github-token` — verify it starts with `ghp_`
2. `curl -H "Authorization: token $(cat /opt/data/.github-token)" https://api.github.com/user` — test raw token
3. Check token scopes at https://github.com/settings/tokens — must include `repo`
4. Verify token not expired
5. If using `gh CLI`: `gh auth status` — but Hermes on Umbrel typically uses git+curl

## Related Skills
- `github-auth` — primary auth setup (bundled)
- `github-repo-management` — repo operations using auth
- `umbrel` — container environment specifics
---
name: github-classic-token-workflow
description: "Create GitHub Classic PAT and use it for repo creation via API (fine-grained tokens cannot create repos)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, PAT, Classic, Token, Repository, Creation, API]
    related_skills: [github-auth, github-repo-management]
---

# GitHub Classic Token Workflow for Repo Creation

## The Critical Distinction

**Fine-grained PATs (`github_pat_...`) CANNOT create repositories via the GitHub API.**

Only **Classic PATs (`ghp_...`)** with the `repo` scope can call `POST /user/repos`.

## Quick Setup (do once)

### 1. Create Classic Token

1. Go to: **https://github.com/settings/tokens**
2. Click **"Generate new token (classic)"** — NOT "Fine-grained tokens"
3. Name: `hermes-agent`
4. Scopes: ✅ `repo` (required), ✅ `workflow` (optional), ✅ `read:org` (optional)
5. Expiration: 90 days
6. **Copy the token** (starts with `ghp_`)

### 2. Store in Container (persistent)

```bash
echo "ghp_YOUR_TOKEN_HERE" > /opt/data/.github-token && chmod 600 /opt/data/.github-token
```

### 3. Verify

```bash
TOKEN=$(cat /opt/data/.github-token)
curl -H "Authorization: token $TOKEN" https://api.github.com/user
# Should return your user JSON
```

## Create Repository via API

```bash
TOKEN=$(cat /opt/data/.github-token)
curl -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user/repos \
  -d '{
    "name": "jinc-ethos",
    "description": "Jornalista Inclusivo — Ethos.Tracker: automação, pesquisa, acessibilidade e inclusão digital",
    "private": false,
    "has_issues": true,
    "has_projects": false,
    "has_wiki": false,
    "auto_init": true,
    "gitignore_template": "Python",
    "license_template": "mit"
  }'
```

## Clone to Persistent Path

```bash
TOKEN=$(cat /opt/data/.github-token)
git clone https://RFerraz1984:$TOKEN@github.com/RFerraz1984/jinc-ethos.git /opt/data/jinc-ethos
cd /opt/data/jinc-ethos
```

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `403 Resource not accessible by personal access token` | Using fine-grained PAT | Use Classic PAT with `repo` scope |
| `401 Bad credentials` | Token invalid/expired | Regenerate Classic token |
| `422 Validation Failed: name already exists` | Repo exists | Delete or rename |
| `git clone: could not read Username` | Token not in URL | Use `https://USER:TOKEN@github.com/...` |

## Persistent Files

| Path | Purpose |
|------|---------|
| `/opt/data/.github-token` | Classic PAT (chmod 600) |
| `/opt/data/jinc-ethos/` | Cloned repo (survives Umbrel updates) |
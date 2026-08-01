# notebooklm-py MCP Server — Umbrel Constraints & Alternatives

**Session context:** User asked about creating an MCP to access NotebookLM (logged into their Google account) to administer/create notebooks. We reviewed `notebooklm-py` (teng-lin/notebooklm-py, v0.8.0).

---

## What notebooklm-py Provides

| Component | Details |
|-----------|---------|
| **Python API** | `NotebookLMClient` — async, full coverage |
| **CLI** | `notebooklm` — create notebooks, add sources, chat, generate artifacts |
| **MCP Server** | `notebooklm-mcp` (stdio or HTTP) — 25 tools: notebooks, sources, chat, notes, artifacts, research |
| **Auth** | Browser cookie reuse (Playwright/Chromium) — **no official OAuth** |
| **Artifacts** | Audio, video, slide-deck, quiz, flashcards, infographic, data-table, mind-map, report |

---

## Why It's Problematic on Umbrel

| Blocker | Impact |
|---------|--------|
| **Playwright + Chromium (~170MB)** | Heavy download, needs system deps (`playwright install-deps` often fails on Alpine/Debian slim) |
| **Interactive Google login + 2FA** | Cannot run headless without manual intervention; cookies expire |
| **Container isolation** | `localhost` MCP server not reachable from host Windows; `host.docker.internal` unreliable on Umbrel |
| **No official API** | Google changes internal endpoints → library breaks without warning |
| **Maintenance burden** | Cookie refresh, Chromium updates, endpoint drift |

---

## Recommended Alternative: Google Drive API + Local RAG

**Architecture:**
1. **Google Drive API** (official, stable OAuth) → list/download PDFs, docs, sheets
2. **Local indexing** (LlamaIndex / LangChain) → chunk, embed, store in `/opt/data/rag/`
3. **Local LLM** (`llama-cpp` or `vLLM` on Umbrel) → grounded Q&A with citations
4. **Hermes tools** → `search_files`, `read_file`, `terminal` for ingestion; `delegate_task` for research pipelines

**Skills to leverage:**
- `google-workspace` — Drive API via `gws` CLI or Python
- `huggingface-hub` — embedding models (e.g., `BAAI/bge-small-en-v1.5`)
- `llama-cpp` / `serving-llms-vllm` — local inference
- `hermes-agent-skill-authoring` — wrap as reusable skill

---

## If You Still Want notebooklm-py on Umbrel (Not Recommended)

```bash
# In Hermes container terminal (PTY)
cd /opt/data
python3 -m venv .venv-nlm
source .venv-nlm/bin/activate
pip install "notebooklm-py[browser,mcp]"
playwright install chromium
# playwright install-deps chromium  # likely fails — missing libs

# Interactive login (needs PTY terminal)
notebooklm login  # opens headless Chromium → manual Google sign-in + 2FA

# Run MCP server (HTTP for network access)
notebooklm-mcp --transport http --port 8000 --profile default
```

**Then connect Hermes native MCP client:**
```yaml
# /opt/data/config.yaml
mcp_servers:
  notebooklm:
    url: "http://<UMBREL_HOST_IP>:8000/mcp"  # NOT localhost, NOT host.docker.internal
    timeout: 180
```

---

## Key Files for Reference

- GitHub: https://github.com/teng-lin/notebooklm-py
- MCP Guide: https://github.com/teng-lin/notebooklm-py/blob/main/docs/mcp-guide.md
- CLI Reference: https://github.com/teng-lin/notebooklm-py/blob/main/docs/cli-reference.md
- Auth/Cookie Lifecycle: https://github.com/teng-lin/notebooklm-py/blob/main/docs/auth-cookie-lifecycle.md
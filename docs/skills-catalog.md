# Catálogo de Skills JINC

> Skills instaladas no Hermes Agent (`/opt/data/skills/`) relevantes para **Jornalista Inclusivo (JINC Apps)**.  
> Versão: 2026-07-21 | Total: 80+ skills | Categorias: 15

---

## 🎯 Skills Principais JINC (Prioridade Alta)

| Skill | Categoria | Descrição | Trigger |
|-------|-----------|-----------|---------|
| `journalism/gmail-triage-jinc` | Jornalismo | Triagem automatizada Gmail (Workspace ou conta comum) para JINC. Filtra últimos N dias por palavras-chave de inclusão, gera releases e sugestões de pauta. | Emails de pautas, press releases, newsletters de inclusão/PcD |
| `journalism/jinc-gmail-triagem-imap` | Jornalismo | Triagem Gmail via IMAP no Hermes → releases e sugestões de pautas inclusivas para JornalistaInclusivo.com. | Mesma da anterior, via IMAP |
| `journalist-inclusion-research` | Jornalismo | Pesquisa jornalística sobre inclusão/acessibilidade PcD — coleta, triagem, resumo de notícias, dados, políticas no Brasil. | Demandas de pauta, fact-checking, legislação |
| `journalist-inclusion-research/jinc-gmail-triagem` | Jornalismo | Triagem inteligente Gmail (Workspace) para gerar releases e sugestões de pautas do JornalistaInclusivo.com com deduplicação robusta. | Inbox Gmail JINC |
| `social-media/social-media-multiplatform` | Social | Postagem multi-plataforma para JINC: Bluesky, Facebook, LinkedIn, Telegram Channel, WhatsApp Business + X/Twitter. Acessibilidade nativa. | Publicação de conteúdo JINC |
| `social-media/moltbook` | Social | Integração Moltbook para agentes: post, read feed, comment, heartbeat. **Case principal: Moltbook Bot.** | Bot @jornalista-inclusivo-bot no Moltbook |
| `social-media/xurl` | Social | X/Twitter via xurl CLI: post, search, DM, media, v2 API. | Posts no X/Twitter |

---

## ⚙️ Skills DevOps / Infraestrutura (Umbrel + Hermes)

| Skill | Descrição | Quando usar |
|-------|-----------|-------------|
| `devops/hermes-umbrel-operations` | Hermes config, CLI, gateway ops no Umbrel — paths, s6 service control, workflows comuns. | Qualquer ops Hermes no Umbrel |
| `devops/cron-rss-multi-feed-telegram` | Cron multi-feed RSS → Telegram (deduplicação). | Agregação de feeds inclusão/tech |
| `devops/cronjob-python-environment` | Criar/gerenciar venvs isolados para scripts Python em cronjobs. | Scripts Python em cron |
| `devops/hermes-container-oauth` | Padrões OAuth para Hermes containerizado (Umbrel, Docker, K8s) — callbacks localhost inacessíveis. | OAuth no container |
| `devops/hermes-stt-setup` | Configurar STT providers: Groq Whisper, faster-whisper local, OpenAI Whisper, Mistral Voxtral. | Speech-to-Text |
| `devops/raft-hermes-integration` | Conectar Hermes ao Raft como external agent via wake-channel bridge. Raft CLI, agent creation, device code. | Multi-agente / UI custom |
| `devops/media-service-integrations` | Configurar/troubleshoot integrações mídia (Spotify, etc.) no Hermes containerizado. | Spotify, etc. |
| `devops/container-oauth` | Padrões OAuth genéricos para ambientes containerizados. | OAuth genérico |
| `devops/install-python-dependencies-restricted` | Instalação deps quando pip/uv indisponível ou venv read-only. Workarounds uv --target, apt-based. | Ambientes restritos |

---

## 🐙 Skills GitHub (Auth + Workflows)

| Skill | Descrição |
|-------|-----------|
| `github/github-auth` | HTTPS tokens, SSH keys, gh CLI login. **Base para todas ops GitHub.** |
| `github/github-auth-troubleshooting` | Troubleshooting: token types, scopes, 401 errors, credential helpers, pitfalls Hermes/Umbrel. |
| `github/github-classic-token-workflow` | Criar Classic PAT e usar para criar repos via API (fine-grained NÃO cria repos). |
| `github/github-repo-management` | Clone/create/fork repos; manage remotes, releases. |
| `github/github-pr-workflow` | PR lifecycle: branch, commit, open, CI, merge. |
| `github/github-code-review` | Review PRs: diffs, inline comments via gh ou REST. |
| `github/github-issues` | Create, triage, label, assign issues via gh ou REST. |
| `github/codebase-inspection` | Inspecionar codebases com pygount: LOC, languages, ratios. |

---

## 🤖 Skills Agentes Autônomos / Coding

| Skill | Descrição |
|-------|-----------|
| `autonomous-ai-agents/hermes-agent` | Configurar, estender, contribuir com Hermes Agent. |
| `autonomous-ai-agents/claude-code` | Delegar coding para Claude Code CLI (features, PRs). |
| `autonomous-ai-agents/codex` | Delegar coding para OpenAI Codex CLI (features, PRs). |
| `autonomous-ai-agents/opencode` | Delegar coding para OpenCode CLI (features, PR review). |
| `software-development/hermes-agent-skill-authoring` | **Escrever skills válidas**: frontmatter, validator, estrutura, princípios de qualidade. |

---

## 🔬 Skills Pesquisa / Data Science

| Skill | Descrição |
|-------|-----------|
| `research/arxiv` | Buscar papers arXiv por keyword, autor, categoria, ID. |
| `research/blogwatcher` | Monitorar blogs/RSS/Atom via blogwatcher-cli. |
| `research/llm-wiki` | Karpathy LLM Wiki: build/query KB markdown interlinkado. |
| `research/polymarket` | Consultar Polymarket: mercados, preços, orderbooks, histórico. |
| `data-science/hermes-shared-rag` | Mini-RAG local para `/opt/data/hermes-shared`. Extrai PDF/MD/TXT, embeddings, FAISS. |
| `data-science/jupyter-live-kernel` | Python iterativo via kernel Jupyter vivo (hamelnb). |
| `mlops/huggingface-hub` | hf CLI: search/download/upload models, datasets. |
| `mlops/rag-pipeline` | RAG local com Google Drive, embeddings locais, FAISS, opcional re-ranking. |

---

## 🎨 Skills Criativas / Visualização

| Skill | Descrição |
|-------|-----------|
| `creative/architecture-diagram` | Diagramas SVG dark-themed (arch, arquitetura/cloud/infra) como HTML. |
| `creative/excalidraw` | Diagramas mão-livre Excalidraw JSON (arch, flow, seq). |
| `creative/ascii-art` | ASCII art: pyfiglet, cowsay, boxes, image-to-ascii. |
| `creative/baoyu-infographic` | Infográficos: 21 layouts × 21 estilos. |
| `creative/p5js` | p5.js sketches: generative art, shaders, interativo, 3D. |
| `creative/manim-video` | Animações Manim CE (3Blue1Brown style). |

---

## 📧 Skills Email / Produtividade

| Skill | Descrição |
|-------|-----------|
| `email/himalaya` | Himalaya CLI: IMAP/SMTP email do terminal. |
| `productivity/google-workspace` | Gmail, Calendar, Drive, Docs, Sheets via gws CLI ou Python. |
| `productivity/hermes-google-apis` | Padrões Google APIs (Drive, Gmail, Calendar, Sheets, Docs) com OAuth no Hermes/Umbrel. |
| `productivity/notion` | Notion API + ntn CLI: pages, databases, markdown, Workers. |
| `productivity/airtable` | Airtable REST API via curl. Records CRUD, filters, upserts. |
| `productivity/ocr-and-documents` | Extrair texto de PDFs/scans (pymupdf, marker-pdf). |
| `productivity/nano-pdf` | Editar PDF texto/typos/títulos via nano-pdf CLI (NL prompts). |
| `productivity/powerpoint` | Criar, ler, editar .pptx, slides, notes, templates. |

---

## 🛡️ Skills Segurança / Red-teaming

| Skill | Descrição |
|-------|-----------|
| `security/cybersecurity-wellbeing` | Cibersegurança e bem-estar digital para Hermes no Umbrel. Hardening, monitoramento, higiene digital. |
| `red-teaming/godmode` | Jailbreak LLMs: Parseltongue, GODMODE, ULTRAPLINIAN. |

---

## 🏠 Skills Smart Home / Outros

| Skill | Descrição |
|-------|-----------|
| `smart-home/openhue` | Philips Hue lights, scenes, rooms via OpenHue CLI. |
| `apple/*` | Apple Notes, Reminders, FindMy, iMessage (requer macOS). |
| `yuanbao` | Yuanbao groups: @mention, query info/members. |

---

## 📦 Como Adicionar Nova Skill JINC

1. **Use a skill de authoring:**
   ```bash
   # No Hermes TUI
   skill_view(name="software-development/hermes-agent-skill-authoring")
   ```

2. **Estrutura mínima:**
   ```
   skills/minha-skill-jinc/
   ├── SKILL.md          # Frontmatter YAML + markdown (obrigatório)
   ├── scripts/          # Scripts auxiliares (opcional)
   ├── templates/        # Templates Jinja2 (opcional)
   └── references/       # Docs de referência (opcional)
   ```

3. **Valide:**
   ```bash
   hermes skill validate skills/minha-skill-jinc/SKILL.md
   ```

4. **Teste local:**
   ```bash
   hermes skill run minha-skill-jinc --prompt "instrução de teste"
   ```

5. **Commit + PR** seguindo convenções em `AGENTS.md` / `CLAUDE.md`.

---

## 🔍 Busca Rápida

```bash
# Listar todas skills com descrição
find /opt/data/skills -name "SKILL.md" -exec sh -c 'yq ".description" {} 2>/dev/null | head -1' \;

# Filtrar por categoria
ls /opt/data/skills/github/
ls /opt/data/skills/journalism/
ls /opt/data/skills/social-media/
```

---

## 📋 Checklist de Qualidade (por skill)

- [ ] Frontmatter válido: `name`, `description`, `version`, `author`, `license`, `platforms`
- [ ] `metadata.hermes.tags` + `metadata.hermes.related_skills`
- [ ] Seções: **Trigger Conditions**, **Passos Numerados**, **Pitfalls**, **Verification**
- [ ] Comandos exatos (copypaste-ready), não placeholders
- [ ] Acessibilidade: linguagem clara, estrutura semântica
- [ ] Testes em `eval/<skill-name>/`
- [ ] Documentada em `docs/skills-catalog.md` (este arquivo)

---

## 🔗 Referências

- [Hermes Skill Authoring Guide](https://hermes-agent.nousresearch.com/docs/skills/authoring)
- `software-development/hermes-agent-skill-authoring` skill (local)
- `AGENTS.md` / `CLAUDE.md` convenções de contribuição
# hermes-jinc-bot

Hermes Agent for **Jornalista Inclusivo (JINC Apps)** — automação, pesquisa, acessibilidade e inclusão digital.

## Sobre

Este repositório contém a configuração, skills, memórias e cron jobs do Hermes Agent operando como app no **Umbrel OS** (homelab), servindo o projeto **Jornalista Inclusivo** (jornalistainclusivo.com/.br) e **Dataverso PcD** (pcd.dataverso.org).

**Editor-chefe:** Rafael Ferraz Carpi (RFerraz1984) — jornalista e ativista social focado em jornalismo inclusivo e direitos das pessoas com deficiência.

Temas: capacitismo, neurodiversidade, acessibilidade em mídia, práticas jornalísticas inclusivas, tecnologia inclusiva.

## Estrutura

```
hermes-jinc-bot/
├── AGENTS.md          # Constituição permanente do agente (princípios, ambiente, skills)
├── CLAUDE.md          # Guia para Claude Code (este arquivo)
├── LICENSE            # MIT
├── README.md          # Este arquivo
├── .gitignore
├── docs/
│   ├── architecture.md      # ADRs e decisões arquiteturais
│   └── skills-catalog.md    # Catálogo detalhado skills JINC
├── skills/                  # Skills locais (git-tracked)
│   └── .gitkeep
├── scripts/                 # Scripts utilitários
│   └── .gitkeep
└── .github/
    └── workflows/           # GitHub Actions (CI/CD)
        └── .gitkeep
```

## Ambiente

- **Host:** Umbrel OS (container Hermes)
- **Home persistente:** `/opt/data` (config, skills, cron, logs, sessions)
- **Token GitHub:** `/opt/data/.github-token` (Classic PAT `ghp_*`, scopes `repo`, `workflow`, `read:org`)
- **Raft CLI:** `/opt/data/.npm-global/bin/raft` (agent externo `jornalista-inclusivo-bot`)

## Skills Principais

| Skill | Domínio | Descrição |
|-------|---------|-----------|
| `github-auth` | DevOps | HTTPS tokens, SSH keys, gh CLI login |
| `github-repo-management` | DevOps | Clone/create/fork repos, remotes, releases |
| `jinc-gmail-triagem` | Jornalismo | Triagem inteligente Gmail (Google Workspace) |
| `journalist-inclusion-research` | Jornalismo | Pesquisa jornalística sobre inclusão/acessibilidade |
| `hermes-umbrel-operations` | DevOps | Hermes config, CLI, gateway ops no Umbrel |
| `cron-rss-multi-feed-telegram` | DevOps | Cron multi-feed RSS → Telegram |
| `social-media-multiplatform` | Social | Multi-platform posting acessibilidade/PcD |

Ver catálogo completo em `docs/skills-catalog.md`.

## Quick Start

```bash
# No container Hermes (Umbrel app)
cd /opt/data/hermes-jinc-bot

# Verificar token GitHub
cat /opt/data/.github-token
curl -H "Authorization: token $(cat /opt/data/.github-token)" https://api.github.com/user

# Listar skills disponíveis
hermes skills list

# Executar cron job manualmente
hermes cron run <job-id>
```

## Cron Jobs Principais

| Job | Schedule | Descrição |
|-----|----------|-----------|
| `jinc-gmail-triagem` | `0 6 * * *` | Triagem diária Gmail → relatório Telegram |
| `rss-multi-feed-telegram` | `*/30 * * * *` | Feeds RSS (inclusão/tech) → Telegram |
| `social-media-post` | `0 9,14,19 * * *` | Posts agendados multi-plataforma |

## Acessibilidade

**Requisito padrão** — todo output, doc, script, skill deve considerar:
- Linguagem clara e sem capacitismo
- Estrutura semântica (headings, listas, tabelas)
- Terminologia preferida pela comunidade PcD
- Compatibilidade leitor de tela

## Contribuição

1. Fork & branch (`feat/...`, `fix/...`, `docs/...`)
2. Commits convencionais (`feat:`, `fix:`, `docs:`, `chore:`)
3. PR com descrição clara + testes manuais
4. Code review (security scan + quality gates)

## Licença

MIT — veja [LICENSE](LICENSE).

## Links

- **Jornalista Inclusivo:** https://jornalistainclusivo.com / .br
- **Dataverso PcD:** https://pcd.dataverso.org
- **GitHub:** https://github.com/RFerraz1984
- **Hermes Agent Docs:** https://hermes-agent.nousresearch.com/docs
# CLAUDE.md — Contexto para Claude Code

> **Projeto:** hermes-jinc-bot — Hermes Agent para Jornalista Inclusivo (JINC Apps)  
> **Público:** Claude Code CLI (anthropic/claude-code)  
> **Idioma:** pt-BR

---

## 🎯 Objetivo

Este arquivo fornece contexto para que o **Claude Code** opere efetivamente no repositório `hermes-jinc-bot`, seguindo as mesmas convenções, princípios e workflows definidos em `AGENTS.md`.

> **Regra de ouro:** Leia `AGENTS.md` primeiro. Este arquivo apenas complementa com especificidades do Claude Code.

---

## 🛠️ Comandos Úteis no Container

```bash
# Navegar para o projeto
cd /opt/data/hermes-jinc-bot

# GitHub API (token em /opt/data/.github-token)
TOKEN=$(cat /opt/data/.github-token) && curl -H "Authorization: token $TOKEN" https://api.github.com/user

# Hermes CLI
hermes skill list
hermes skill view <name>
hermes cron list
hermes memory add "fato duradouro"

# Raft CLI (profile ativo via RAFT_PROFILE)
raft --help

# Python deps (uv)
uv pip install -r requirements.txt  # se existir

# Testes skills (pytest)
pytest eval/ -v
```

---

## 📁 Estrutura Esperada pelo Claude Code

```
hermes-jinc-bot/
├── .github/workflows/     # CI: lint, test, deploy docs
├── skills/                # Skills locais (submodules ou cópias)
├── scripts/               # Utilitários (deploy, backup, sync)
├── prompts/               # Prompts versionados
├── eval/                  # Testes de regressão skills
└── docs/                  # Documentação técnica
```

---

## 🔧 Workflows Comuns

### Criar/Atualizar Skill
```bash
# 1. Carregar skill de authoring
# (feito via skill_view no Hermes, ou ler skills/hermes-agent-skill-authoring/SKILL.md)

# 2. Criar estrutura
mkdir -p skills/minha-skill/{scripts,templates,references}
# Escrever SKILL.md seguindo frontmatter + seções obrigatórias

# 3. Validar
hermes skill validate skills/minha-skill/SKILL.md
```

### Testar Skill Localmente
```bash
# No Hermes TUI ou via cronjob de teste
hermes skill run minha-skill --prompt "instrução de teste"
```

### Commit + PR
```bash
git checkout -b feat/minha-skill
git add .
git commit -m "feat(skill): adiciona minha-skill para X

- Implementa Y com Z
- Testes em eval/minha-skill/

Refs: #<issue>"
git push origin feat/minha-skill
gh pr create --fill
```

---

## 🧪 Testes (eval/)

Cada skill deve ter testes em `eval/<skill-name>/`:

```
eval/
└── jinc-gmail-triagem/
    ├── test_teste
    │   ├── test_triagem_basic.py
    │   ├── fixtures/
    │   │   ├── email_sample_1.eml
    │   │   └── email_sample_2.eml
    │   └── expected_output.json
```

Execute: `pytest eval/ -v`

---

## 📝 Convenções Específicas Claude Code

### Tool Use
- **Prefira** `bash` para comandos, `read`/`write`/`edit` para arquivos
- **Use** `task` (subagent) para: debugging complexo, code review, research synthesis, parallel workstreams
- **Não use** `task` para: mechanical multi-step, single tool calls, tasks needing user interaction

### Output Style
- Conciso, técnico, pt-BR
- Headings, listas numeradas, tabelas, checklists
- Sem verbosidade desnecessária, entusiasmo artificial, marketing

### Acessibilidade
- Mesmas regras do `AGENTS.md`
- Explique siglas na 1ª ocorrência
- Estrutura semântica sempre

---

## 🔗 Referências Rápidas

| Arquivo | Finalidade |
|---------|------------|
| `AGENTS.md` | Princípios, ambiente, skills, convenções (fonte primária) |
| `docs/architecture.md` | ADRs, decisões arquiteturais |
| `docs/skills-catalog.md` | Catálogo detalhado skills JINC |
| `skills/hermes-agent-skill-authoring/SKILL.md` | Como criar skills válidas |
| `/opt/data/.github-token` | GitHub Classic PAT (ghp_*) |

---

## ⚠️ Armadilhas Conhecidas

| Problema | Solução |
|----------|---------|
| `pip` falha (PEP 668) | Use `uv pip install` ou venv |
| `gh` não instalado | Use `git` + token + `curl` (ver `github-auth` skill) |
| Token Fine-grained (`github_pat_`) | **Não funciona para criar repos** — use Classic (`ghp_`) |
| Cron job sem delivery | Use `deliver='telegram'` ou `deliver='all'` |
| `localhost` no container | Use Docker service names (ex: `redis`, `postgres`) |
| Paths fora de `/opt/data` | São efêmeros — não persistem |

---

## 🎯 Princípio Fundamental (Repetido de AGENTS.md)

> **Seu objetivo não é gerar respostas.**  
> **Seu objetivo é aumentar continuamente a capacidade do seu parceiro humano e o conhecimento institucional do Jornalista Inclusivo, produzindo conhecimento confiável, reutilizável, acessível e operacional.**
# Cronjob Scripts — Autônomos (Session 2026-07-21)

Todos os scripts de cronjob seguem o **padrão de saída em linguagem natural** para entrega no Telegram (ver seção "Cronjob Output Pattern" no SKILL.md).

## Scripts Criados

### 1. `moltbook_monitor.py` — Monitor Principal (15 min)
**Local:** `/opt/data/scripts/moltbook_monitor.py`  
**Cron:** `*/15 * * * *` (job `582cdb557284`)

**Funções:**
- Verifica comentários novos nos 4 posts principais
- Responde com templates contextuais (keyword → reply)
- Resolve challenge de verificação imediato (`auto-verify`)
- Roda ciclo Auditor no `algorithmic-auditing` (a cada 2 execuções)
- Entrega relatório em linguagem natural no Telegram

**Estado persistido:** `/opt/data/moltbook_monitor_state/`
- `replied_<COMMENT_ID>.json` — evita duplicatas
- `verified_<POST_ID>.json` — posts com verificação resolvida
- `labeled_<POST_ID>.json` — posts etiquetados pelo Auditor
- `auditor_cycle_count.json` — contador para cadência do Auditor

### 2. `moltbook_verification_checker.py` — Verificação de Posts (5 min)
**Local:** `/opt/data/scripts/moltbook_verification_checker.py`  
**Cron:** `*/5 * * * *` (job `7f7cd6d2f4b1`)

**Função:**
- Varre os 4 posts com `verification_status=pending`
- Detecta `verification` object (challenge) se presente
- Resolve matemática via solver padrão
- Submete `POST /verify` antes de expirar (TTL 5 min)
- Entrega relatório em linguagem natural no Telegram

**Posts monitorados (IDs originais falhados + republicados):**
| Post Original (failed) | Republicado (verified) | Submolt |
|------------------------|------------------------|---------|
| `68cffd1e-cc97-41e5-9584-b0cf8f995732` | `29b55ffe-1ef0-4055-927e-75314e254e4a` | ai-rights |
| `bec38bce-d198-4a55-a7b9-1a30bf6f63d2` | `2010672b-9b14-43ef-9e05-91204a9b26f1` | accessibility |
| `0d2f3a5d-f272-4fe4-ac33-18937fe1258a` | `02f53332-e4ad-4f4b-bba6-96a8cad91071` | ethics |
| `67848028-334d-47da-8180-ffbf397ea583` | (já verificado) | ai-rights |

### 3. `moltbook_heartbeat.py` — Heartbeat (30 min)
**Local:** `/opt/data/scripts/moltbook_heartbeat.py` (ou usa `moltbook_helpers.py heartbeat`)  
**Cron:** `*/30 * * * *` (job `3d75d014af16`)

**Função:**
- Checka claim status
- Fetch hot feed
- Check notifications
- Mantém agente `claimed`/`active`

### 4. `watch_hermes_shared.py` — Watchdog Hermes-Shared (15 min)
**Local:** `/opt/data/scripts/watch_hermes_shared.py`  
**Cron:** `*/15 * * * *` (job `e005e2a045b5`)

**Função:**
- Detecta arquivos novos em `/opt/data/hermes-shared`
- Reindexa mini-RAG (`index_hermes_shared.py --reindex`)
- Avisa no Telegram com lista de arquivos novos/alterados/removidos

### 5. `publish.sh` — Publica Dataset no GitHub
**Local:** `/opt/data/scripts/publish.sh`  
**Uso:** Manual (após autenticar `gh`)

```bash
/opt/data/scripts/publish.sh [owner/repo] [branch]
# Ex: /opt/data/scripts/publish.sh jornalistainclusivo/capacitismo-algoritmico main
```

**O que faz:**
1. Verifica se repo remoto existe; se não, cria público com description padrão
2. Configura/atualiza remote `origin`
3. Push da branch (default: master)
4. Habilita branch protection (requer admin no repo)
5. Habilita GitHub Actions se houver workflows
6. Imprime URL final

**Pré-reqs:** `gh` em `/opt/data/bin/gh` + `GITHUB_TOKEN` válido (scopes: repo, admin:repo_hook) ou `gh auth login`.

## Padrão de Estado Persistido

Todos os scripts de monitoramento salvam estado em:
```
/opt/data/moltbook_monitor_state/
├── replied_<COMMENT_ID>.json       # comentário respondido
├── verified_<POST_ID>.json         # post verificado
├── labeled_<POST_ID>.json          # post etiquetado pelo Auditor
└── auditor_cycle_count.json        # contador ciclos Auditor
```

**Cleanup:** Arquivos > 7 dias são removidos automaticamente pelo monitor.

## Padrão de Entrega Telegram

Todos os scripts outputam **apenas** relatório em linguagem natural (Markdown + emojis), sem JSON bruto. Exemplo:

```
📂 **Watchdog Hermes-Shared** — 21/07/2026 20:15

🆕 **2 arquivo(s) novo(s) detectado(s):**
  • `curriculo/novo-curriculo.pdf`
  • `artigos/paper-ia-acessibilidade.md`

🔧 Iniciando reindexação incremental do mini-RAG...
✅ **Reindexação concluída com sucesso** — mini-RAG atualizado
```

Silêncio = tudo OK (watchdog pattern: return 0, no output).
# Sessão: 2026-06-23 → 2026-07-03 — Notas de execução e correções

Resumo curto
- Job `weekly-inclusion-digest` (680521a2437d) rodou manualmente e retornou exatamente `[SILENT]` — não havia novidades após dedup.
- Job `topic-news-digest` (9584576094fa) **ENTREGOU NOTÍCIAS DE 2023/2024 EM 2026** — FALHA GRAVE de jornalismo factual.
- Problemas identificados: jobs sem provider/model explícito; prompts sem filtro de data; fallback para modelo gratuito (nemotron) sem controle de recência.

Ações corretivas executadas (2026-07-03)
1. **Pausados jobs problemáticos**: 9584576094fa e 680521a2437d (paused).
2. **Recriados jobs FIXADOS** com:
   - provider=groq, model=llama-3.3-70b-versatile (explícito)
   - skill=journalist-inclusion-research (mínima)
   - prompts com filtro de data OBRIGATÓRIO ("2026" em todas as queries)
   - regra: descartar 2023/2024/2025; [SILENT] se nada novo de 2026
3. **Atualizada skill `journalist-inclusion-research`** (v1.1.0):
   - Adicionada "Regra Obrigatória de Filtro de Data (Jornalismo Factual)" no SKILL.md
   - Atualizado template `templates/cronjob-template.md` com exemplos corretos
   - Prompt padrão agora exige queries com "2026" e filtro rigoroso

Novos job IDs (FIXADOS)
- `c77d6e1e92db` — "weekly-inclusion-digest (FIXED)" — sexta 19:00 BRT
- `d9d3f8c62f21` — "topic-news-digest-ia-tech (FIXED)" — dias úteis 18:00 BRT

Diagnóstico reproduzível
- Ver jobs: /opt/data/cron/jobs.json
- Saída do job: /opt/data/cron/output/<job_id>/<timestamp>.md
- Logs do agente: /opt/data/logs/agent.log

Correções concretas (checklist obrigatório para TODO cron job de pesquisa)
- [ ] provider + model definidos EXPLICITAMENTE (não confiar em fallback)
- [ ] skill=journalist-inclusion-research anexada (mínima)
- [ ] Prompt inclui "2026" em TODAS as queries web_search
- [ ] Regra: "DESCARTE 2023/2024/2025. Só 2026."
- [ ] Fallback: [SILENT] se nada novo do ano atual
- [ ] Testar com `cronjob run <job_id>` ANTES de habilitar entrega automática

Notas sobre dedupe
- Dedupe via `session_search` contra execuções anteriores do mesmo job — correto.

Próximos passos
- Rodar teste manual dos novos jobs (`cronjob run <job_id>`) e validar saída.
- Agendar revisão humana semanal antes de qualquer postagem automática.
- Monitorar primeira execução automática (sexta 19:00 e dias úteis 18:00).
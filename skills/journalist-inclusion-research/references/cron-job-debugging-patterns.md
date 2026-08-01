# Cron Job Debugging Patterns — Jornalista Inclusivo

Capturado da sessão 2026-07-03 (debug de jobs `weekly-inclusion-digest` e `topic-news-digest-ia-tech`).

## Problema: Context Length Exceeded

**Sintoma:** `RuntimeError: Context length exceeded (6,751 tokens). Cannot compress further.`

**Causa:** Anexar skill `journalist-inclusion-research` ao cron job injeta todo o SKILL.md + references (~6-7k tokens) no prompt. O system prompt já consome ~3.5k tokens. Total > limite do modelo.

**Solução aplicada:**
- Remover `skills: ["journalist-inclusion-research"]` do cron job
- Colocar instruções essenciais direto no prompt do job
- Ou usar `no_agent: true` com script standalone

## Problema: Modelo Gratuito Exaure (ResourceExhausted)

**Sintoma:** `ResourceExhausted: Worker local total request limit reached (32/32)` no modelo `nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter.

**Causa:** Modelo gratuito tem limite de 32 workers simultâneos. Cron jobs paralelos ou execuções frequentes batem o limite.

**Solução:** Usar provider pago/estável em cron jobs de produção:
- `provider=groq, model=llama-3.3-70b-versatile` (recomendado)
- `provider=anthropic, model=claude-sonnet-4`
- `provider=openrouter, model=anthropic/claude-sonnet-4`

## Problema: Filtro de Data Ausente → Notícias de 2023/2024 em 2026

**Sintoma:** Job entregou notícias de 2023/2024 rodando em 2026.

**Causa:** Prompt original não exigia filtro de ano explícito nas queries.

**Regra Obrigatória (agora no SKILL.md):**
- TODA query `web_search` deve incluir ano atual (`"2026"`)
- Descartar resultados de anos anteriores (2023, 2024, 2025)
- Se nada de 2026 → responder `[SILENT]`

## Template de Prompt de Cron Job Corrigido

```yaml
prompt: |
  Busque 5 notícias de 2026 sobre [TEMA] no Brasil.
  Queries obrigatórias com "2026":
  - "termo 2026 site:fonte.gov.br"
  - "termo 2026 site:jornalistainclusivo.com"
  Regras: descarte 2023/2024/2025. Só 2026. Se nada, [SILENT].
  Formato: título — fonte — link — 1 frase.

provider: groq
model: llama-3.3-70b-versatile
skills: []  # VAZIO — evita context length exceeded
schedule: "0 19 * * 5"  # sexta 19h BRT
```

## Checklist de Criação/Atualização de Cron Job

- [ ] `provider` + `model` explícitos (não confiar em fallback)
- [ ] `skills: []` vazio (instruções no prompt)
- [ ] Filtro `"2026"` em TODAS as queries web_search
- [ ] Regra: "descarte 2023/2024/2025. Só 2026"
- [ ] Fallback: `[SILENT]` se nada novo de 2026
- [ ] Testar com `cronjob run <job_id>` ANTES de habilitar
- [ ] Ver saída em `/opt/data/cron/output/<job_id>/`
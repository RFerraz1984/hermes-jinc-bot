# Pitfalls & Learnings — JINC Gmail Triagem IMAP

Documenta problemas encontrados e soluções aplicadas durante a implementação do pipeline de triagem de Gmail via IMAP para o JornalistaInclusivo.com.

---

## 1. Porta 465 ≠ IMAP (Erro clássico)

**Sintoma:** Usuário mencionou "conexão segura na porta 465 usando SSL" para leitura de e-mail.

**Causa:** Porta **465** é **SMTP submission (envio)** com SSL implícito. Para **leitura via IMAP**, a porta padrão é **993 (IMAP over SSL/TLS)**.

**Regra:** Sempre confirmar `host` e `porta IMAP` antes de configurar. Se o usuário citar 465/587, tratar como alerta e pedir IMAP host/porta.

---

## 2. Credenciais placeholder não rodam no cron

**Sintoma:** Cronjob criado mas falharia se executado com `SEU_EMAIL@gmail.com` / `SENHA_OU_APP_PASSWORD`.

**Solução:** Validar existência e conteúdo de `/opt/data/journali/imap-config.json` **antes** de despausar o cron. Checklist:
- [ ] Arquivo existe
- [ ] `host`, `port`, `username`, `password` não são placeholders
- [ ] Teste manual de conexão IMAP (ex.: `python -c "import imaplib; imaplib.IMAP4_SSL('imap.gmail.com', 993).login(user, pass)"`)

---

## 3. Deduplicação por hash de texto é frágil

**Problema:** Remetentes podem reenviar com pequenas variações (assinatura, rodapé, encoding) → hash de corpo/assunto muda.

**Solução adotada:** Deduplicar **exclusivamente por `messageId`** (header `Message-ID` do RFC 5322). Persistir em `/opt/data/journali/processed-message-ids.jsonl` (append-only, 1 por linha).

---

## 4. Backup do Umbrel inclui segredos

**Risco:** Backup automático do app Hermes no Umbrel (Settings → Backup) empacota **todo `/opt/data`** → `.env`, `auth.json`, `google_*.json`, `client_secret_*.json` vão para o arquivo de backup.

**Mitigação implementada:**
- Script `backup-hermes-selective.sh` cria tarball **sem segredos** (exclui `.env`, `auth.json`, `google_*.json`, `state.db*`, logs, caches).
- Cron diário às 03:00 (`fbb2f2b8405a`) roda esse script e entrega no Telegram.
- Lembrete mensal de rotação de credenciais (`0528ad2c657b`) alerta para verificar se backup do Umbrel **não** incluiu segredos.

---

## 5. Watchdog duplicado de rate-limit OpenRouter

**Ocorrência:** Dois crons idênticos criados (`434fc53f1769` e `e11c70a86885`) — um sem `workdir`, outro com.

**Correção:** Removido o duplicado (`434fc53f1769`). Mantido `e11c70a86885` com `workdir: /opt/data` para que o script encontre `.env`.

---

## 6. Script Python precisa ler `.env` do Hermes

**Problema:** Cron `no_agent=true` roda script isolado; variáveis de ambiente do processo Hermes **não** são herdadas.

**Solução:** Script `check_openrouter_rate.py` inclui função `load_env_file("/opt/data/.env")` que faz `os.environ[key] = value` antes de ler `OPENROUTER_API_KEY`.

---

## 7. App Password vs senha comum no Gmail/Workspace

**Observação:** Google Workspace e contas pessoais com 2FA **exigem App Password** para IMAP/SMTP. Senha comum falha com "Invalid credentials" mesmo se correta.

**Regra prática:** No `imap-config.json`, orientar `password` como "App Password". Se falhar, testar com senha comum apenas como fallback (raro funcionar).

---

## 8. Estrutura de arquivos JINC (padrão consolidado)

```
/opt/data/journali/
├── imap-config.json              # Credenciais IMAP (template em skill)
├── processed-message-ids.jsonl   # Deduplicação (1 messageId por linha)
├── triagem-YYYY-MM-DD.md         # Output diário (um por dia)
└── backups/                      # (opcional) backups locais
```

---

## 9. Cron jobs ativos relacionados (IDs para referência)

| Job ID | Nome | Schedule | Função |
|---|---|---|---|
| `12d59b921ae1` | JINC Gmail triagem-15d | `0 9 * * *` | **Pausado** — aguarda `imap-config.json` real |
| `fbb2f2b8405a` | Backup seletivo Hermes | `0 3 * * *` | Tarball sem segredos → Telegram |
| `0528ad2c657b` | Lembrete rotação credenciais | `0 9 1 * *` | Checklist mensal → Telegram |
| `e11c70a86885` | OpenRouter rate watchdog | `*/30 * * * *` | Consulta API key endpoint → Telegram |

---

## 10. Próximos passos quando usuário editar `imap-config.json`

1. Validar conexão: `python3 -c "import imaplib; m=imaplib.IMAP4_SSL('imap.gmail.com',993); m.login('user','pass'); print('OK'); m.logout()"`
2. Despausar cron: `hermes cron resume 12d59b921ae1`
3. Testar run manual: `hermes cron run 12d59b921ae1`
4. Verificar output no Telegram + `/opt/data/journali/triagem-YYYY-MM-DD.md`

---

## 11) Classificação LLM-enhanced via OpenRouter (2026-07-28)

**Implementação:** Script principal `jinc_gmail_triagem_15d.py` agora usa LLM (`nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter) para:
- Classificação semântica: `release` | `sugestao_de_pauta` | `irrelevante`
- Extração de palavras-chave relevantes
- Resumo em 1 linha (max 160 chars)
- Geração de 2-4 ângulos jornalísticos inclusivos específicos

**Fluxo:**
1. Busca IMAP otimizada → candidatos (Subject/From match)
2. Para cada candidato: extrai body → chama LLM para classificar
3. Se `irrelevante` → descarta (mas salva Message-ID no dedupe)
4. Se relevante → chama LLM para ângulos → monta item estruturado
5. Fallback heurístico se LLM falhar (timeout, 401, rate limit)

**Prompt templates** embutidos no script:
- `CLASSIFICATION_PROMPT`: categorização + confiança + keywords + resumo + motivo
- `ANGLE_EXTRACTION_PROMPT`: 2-4 ângulos específicos e acionáveis

**Resultado observado:** Classificação mais precisa que regex (ex.: filtra DMARC reports, newsletters genéricas). Confiança ~50-90%.

---

## 12) OpenRouter API Key — 401 Unauthorized & Fallback (2026-07-28)

**Problema:** `OPENROUTER_API_KEY` configurada no `.env` mas retorna HTTP 401 `{"error":{"message":"Missing Authentication header","code":401}}`.

**Causa provável:** Chave inválida/expirada ou modelo `nvidia/nemotron-3-ultra-550b-a55b:free` requer autenticação diferente.

**Padrão de fallback implementado no script:**
```python
try:
    response = call_llm(prompt)
    return parse_llm_json(response, fallback)
except Exception as e:
    print(f"⚠️ LLM failed: {e}", file=sys.stderr)
    fallback["motivo"] = f"Erro LLM: {e}"
    return fallback
```

**Ação necessária:** Verificar/gerar nova chave em https://openrouter.ai/keys e atualizar `.env`. Enquanto isso, heurística + fallback garante operação contínua.

---

## 13) IMAP Search Optimization — Headers First (2026-07-28)

**Estratégia validada em produção:**
1. `SEARCH CHARSET UTF-8 SINCE "13-Jul-2026"` → IDs
2. Limitar aos 100 mais recentes (`msg_ids[-100:]`)
3. `FETCH BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)]` para todos
4. Filtrar localmente: keywords no Subject + From conhecido (newsletters, alertas)
5. Só então `FETCH RFC822` dos candidatos (tipicamente 5-20 emails)

**Ganho:** De ~580 fetches completos (timeout 180s) → ~10-20 fetches (<30s).

**Código-chave em `fetch_matching_emails()`:** Fetch headers first → filter → fetch body only for candidates.

---

## 14) Cron Schedule Atualizado — 3x Diário (2026-07-28)

**Novo schedule:** `0 12,17,21 * * *` (12:00, 17:00, 21:00 UTC = 09:00, 14:00, 18:00 BRT)

**Job ID:** `12d59b921ae1`
**Estado:** ✅ enabled, scheduled
**Próxima execução:** `2026-07-28T17:00:00+00:00` (14:00 BRT hoje)

**Racional:** Cobertura matutina (releases overnight), tarde (eventos/convites), noite (fechamento dia).

---

## 15) Relatório Markdown Cumulativo + Delta com Timestamp (2026-07-28)

**Problema:** Output anterior sobrescrevia arquivo diário (`triagem-YYYY-MM-DD.md`) mostrando apenas itens novos da execução → usuário via "Total: 0" mesmo com cache cumulativo.

**Solução implementada no script `jinc_gmail_triagem_15d.py`:**

| Arquivo | Conteúdo | Formato |
|---------|----------|---------|
| `triagem-YYYY-MM-DD-HH-MM.md` | **Cumulativo 15 dias** + destaque dos novos desta execução | Markdown estruturado |
| `triagem-delta-YYYY-MM-DD-HH-MM.md` | **Apenas itens novos** desta execução | Markdown estruturado |
| `processed_items_cache.json` | Cache persistente de todos os itens válidos (15 dias) | JSON array |

**Estrutura do Markdown cumulativo:**
```markdown
# Triagem JINC — DD/MM/YYYY HH:MM (Cumulativo 15 dias)
**Total nos últimos 15 dias:** N itens (X releases, Y sugestões)
**Novos nesta execução:** M (A releases, B sugestões)

## 📋 Todos os itens relevantes (últimos 15 dias)
### 🚀 Releases
#### 1. Título do Release
- **Fonte:** Remetente <email@domain.com>
- **Data:** DD/MM/YYYY HH:MM
- **Link/ID:** `<Message-ID>`
- **Resumo:** ...
- **Confiança:** XX%
- **Palavras-chave:** kw1, kw2, ...
- **Ângulos inclusivos:**
  - Ângulo 1
  - Ângulo 2

### 💡 Sugestões de Pautas
...
```

**Funções-chave:**
- `generate_cumulative_markdown(all_items, new_items, date_str, time_str)` — gera cumulativo + destaque novos
- `load_all_processed_items()` — lê `processed_items_cache.json`
- Bloco final do `main()` salva cache atualizado + escreve ambos arquivos

---

## 16) LLM Classification Pipeline — Robustez em Produção (2026-07-28)

**Configuração final validada:**
- **Modelo:** `openrouter/auto` (roteamento inteligente para melhor modelo grátis)
- **Max tokens:** 2000 (evita truncamento JSON — antes 600 era insuficiente)
- **Temperature:** 0.1 (determinístico)
- **Timeout HTTP:** 120s
- **Retry:** 3x com backoff exponencial (2s, 4s, 8s)
- **Prompt:** Formato pipe-delimited simplificado `CATEGORIA|CONFIANCA|PALAVRAS_CHAVE|RESUMO|MOTIVO|ANGULOS`

**Parser JSON robusto (`parse_llm_json`):**
1. Tenta extrair JSON puro com regex `r'\{.*\}'` (DOTALL)
2. Limpa markdown code blocks (```json ... ```)
3. Fallback: split por `|` (formato pipe-delimited)
4. Fallback final: heurística por keywords no subject/body
5. Loga responses inválidos para debug

**Fallback keyword-based obrigatório:**
```python
# Se LLM retorna 'irrelevante' mas body/subject contém keywords monitoradas:
if categoria == "irrelevante" and any(kw in text_lower for kw in IMAP_KEYWORDS):
    categoria = "sugestao_de_pauta"  # forçar relevância
    confianca = 0.7
    motivo = "Fallback: contém keyword monitorada"
```

**Resultado observado:** 13 itens no cache cumulativo, classificação funcional, execução < 5 min (cron limit).

---

## 17) IMAP Search — Keywords sem Acentos (Server-Side UTF-8) (2026-07-28)

**Problema:** `SEARCH` IMAP server-side não suporta acentos em charset UTF-8 padrão do Gmail.

**Solução:** Remover acentos das keywords no script:
```python
IMAP_KEYWORDS = [
    "acessibilidade", "deficiencia", "inclusao", "autismo", "neurodiversidade",
    "pcd", "tea", "wcag", "e-mag", "capacitismo", "audiodescricao",
    "leitor de tela", "libras", "tecnologia assistiva", "design universal"
]
```
Busca funciona: `OR SUBJECT BODY "acessibilidade" "deficiencia" ...` → 93 mensagens confirmadas nos últimos 15 dias.

---

## 18) Script Execution — Timeout Resolvido (2026-07-28)

**Histórico:**
- v1: Fetch 580 headers → timeout 180s
- v2: `SEARCH SINCE` + fetch headers → timeout 300s no fetch body
- v3: `SEARCH SINCE` + fetch headers + **filter local** + fetch body **apenas candidatos** → **< 30s**
- v4 (atual): Adicionado `MAX_EMAILS_PER_RUN=100`, `MAX_PROCESSING_TIME=240s`, parser robusto, duplicações removidas → **exit 0 consistentemente**

**Métricas finais:**
- Emails escaneados (headers): até 100 mais recentes
- Candidatos para LLM: tipicamente 5-20
- Tempo total: ~60-120s (bem dentro do limite 300s do cron)
- Cache cumulativo: 13 itens válidos persistidos

---

## 19) Tavily MCP OAuth — Non-Interactive Container (2026-07-28)

**Erro observado:**
```
MCP OAuth for 'tavily': non-interactive environment and no cached tokens found.
Run `hermes mcp login tavily` interactively first to complete initial authorization.
```

**Causa:** `config.yaml` tem `mcp_servers.tavily.auth: oauth` mas container Hermes não tem browser/TTY para fluxo OAuth.

**Soluções (ordem de preferência):**
1. **API Key direta** — se tem `TAVILY_API_KEY`: mudar `auth: none` + header `Authorization: Bearer $TAVILY_API_KEY`
2. **Desabilitar** — `enabled: false` no config.yaml (para erro imediato)
3. **Login interativo** — `hermes mcp login tavily` em terminal anexado (token expira, não recomendado para cron)

**Config atual problemática:**
```yaml
tavily:
  auth: oauth
  enabled: true
  url: https://mcp.tavily.com/mcp/
  headers:
    Authorization: Bearer ***  # placeholder, não funciona com OAuth
```

**Ação recomendada:** Verificar se `TAVILY_API_KEY` existe em `/opt/data/.env` e migrar para auth none.
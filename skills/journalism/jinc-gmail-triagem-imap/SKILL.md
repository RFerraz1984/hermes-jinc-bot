---
name: jinc-gmail-triagem-imap
description: "Triagem de Gmail (Google Workspace) via IMAP no Hermes para gerar releases e sugestões de pautas inclusivas para o JornalistaInclusivo.com."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [gmail, imap, triagem, journalism, acessibilidade, inclusao, workflow]
---

# Triagem de Gmail (Google Workspace) via IMAP → JornalistaInclusivo.com

## Objetivo
Construir um pipeline **robusto e repetível** no Hermes para:
1) Ler mensagens do Gmail via **IMAP**
2) Filtrar por **janela de período** (ex.: últimos 15 dias) e **palavras‑chave** (inclusão/acessibilidade/deficiência)
3) Deduplicar por **`messageId`**
4) Classificar cada item como **release** ou **sugestão de pauta**
5) Extrair metadados e gerar **ângulo inclusivo** (2–4 bullets)
6) Entregar para o JornalistaInclusivo.com via **Telegram** e salvar um **markdown diário** em `/opt/data`

## Arquivos/paths (padrão JINC)
- ` /opt/data/journali/imap-config.json`
- ` /opt/data/journali/processed-message-ids.jsonl` (append-only)
- ` /opt/data/journali/triagem-YYYY-MM-DD.md` (um arquivo por dia)
- **Scripts de execução**: `/opt/data/scripts/jinc_gmail_triagem_15d.py` (principal) + `/opt/data/scripts/jinc_gmail_triagem_15d_filtered.py` (wrapper filtrado para cron)

## Estrutura de config IMAP
Crie/edite ` /opt/data/journali/imap-config.json` com:
```json
{
  "host": "imap.gmail.com",
  "port": 993,
  "username": "SEU_EMAIL@gmail.com",
  "password": "SENHA_OU_APP_PASSWORD",
  "search_folder": "INBOX"
}
```

## Regras de filtro
### Janela temporal
- Sempre usar **últimos 15 dias** (ou parametrizar, mas iniciar com 15).

### Palavras‑chave (assunto + corpo)
Usar OR/normalização simples (case-insensitive) para:
- "pessoas com deficiência"
- "pessoa com deficiência"
- "neurodiversidade"
- "autismo"; "TEA"; (inclui "autista" se aparecer)
- "inclusão"; "acessibilidade"; "equidade"; "diversidade"
- "deficiência intelectual"; "deficiência visual"; "deficiência auditiva"
- "direitos humanos"

## Classificação e extração (LLM + heurística)
### Tipo
- `release`: mensagem com natureza de comunicados / press release / “para divulgação”/“release”
- `sugestao_de_pauta`: convite a cobertura, tese/tema, evento, relatório com potencial de ângulo editorial
- `heurística + reforço`: primeiro detectar com regex/termos comuns; depois validar/ajustar com LLM.

### Campos mínimos por item
- `tipo`
- `fonte` (From)
- `assunto`
- `date` (Date do e-mail, se disponível)
- `identificador/link` (URL, Message-ID ou ambos)
- `resumo` (3–6 linhas)
- `ângulo inclusivo` (2–4 bullets alinhados com JornalistaInclusivo.com)
- `palavras_chave_encontradas` (lista)

## Deduplicação
- Deduplicar **por `messageId`**.
- Persistir em `/opt/data/journali/processed-message-ids.jsonl` (1 por linha).

## Entrega
- **Telegram**: 1 mensagem única contendo todos os itens do dia.
- **Arquivo diário**: salvar em `/opt/data/journali/triagem-YYYY-MM-DD.md`.

## Pitfalls / correções (aprendizado incorporado)
1) **Não confundir 465/SSL com IMAP.** Porta **465** é típica de **SMTP submission**. Para leitura de caixa via IMAP, use **IMAP SSL 993** (ou a porta IMAP equivalente no seu Workspace). Se alguém mencionar 465 como "leitura", trate como alerta e exija host/porta IMAP antes de rodar.
2) **Não rodar cron com credenciais placeholder.** Antes da primeira execução, validar que `imap-config.json` existe e tem `host`, `port`, `username`, `password` não‑placeholder.
3) **Deduplicar sempre por `messageId`.** Deduplicação por hash de texto pode falhar quando remetentes reenviam com pequenas variações.
4) **Validar conectividade IMAP antes de habilitar cron.** Um `telnet imap.gmail.com 993` ou `openssl s_client -connect imap.gmail.com:993` confirma que o host/porta respondem antes de confiar no agendamento.
5) **Tratar "App Password" como padrão para Google.** Contas Google (Workspace ou comum) com 2FA exigem App Password para IMAP. Senha normal costuma falhar com "Invalid credentials" mesmo se a senha estiver correta.
6) **Cron de triagem deve falhar explicitamente se config ausente/incompleta.** O prompt do cronjob deve checar existência e completude do `imap-config.json` e abortar com mensagem clara (ex.: "campo X faltando") em vez de tentar conectar e falhar silenciosamente.
7) **Separar backup seletivo (sem segredos) de backup completo.** O backup automático do Umbrel inclui `.env`, `auth.json`, tokens Google — o que vaza segredos se o arquivo de backup for acessado. Criar cron de backup seletivo que **exclui** segredos e caches.
8) **Rotação de credenciais precisa de lembrete recorrente + procedimento.** Adicionar cron mensal que lista cada credencial, URL do painel de rotação, e passo pós-rotação (`hermes gateway restart`).
9) **Gmail comum vs Workspace:** para conta Gmail comum (não Workspace), IMAP costuma exigir **App Password** (senha de app) em vez da senha normal, pois o Google bloqueia "less secure apps". O fluxo OAuth nativo do Hermes (`hermes auth add google`) não existe; use IMAP + App Password.
10) **Cron com prompt placeholder:** criar o cron job **pausado** com prompt genérico, depois atualizar o prompt com a lógica real e só então despausar. Evita execução acidental antes da config estar pronta.
11) **IMAP SEARCH com acentos falha** — usar `CHARSET UTF-8` no search criteria. Busca por keywords com acentos (ex.: "acessibilidade", "deficiência") exige charset explícito, senão `UnicodeEncodeError` / `BAD [b'Could not parse command']`.
12) **Otimização de busca IMAP (performance):** Para caixas com 500+ emails, buscar TODOS os corpos (RFC822) é lento (>180s timeout). Estratégia vencedora: 1) `SEARCH SINCE date` → limitar aos N mais recentes; 2) `FETCH BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)]` para todos; 3) Filtrar por keywords no Subject + From conhecidos; 4) Só então `FETCH RFC822` dos candidatos. Reduz de 580 fetches completos para ~10-20.
13) **Integração com `smart_notify_filter.py`:** Wrapper filtrado (`*_filtered.py`) deve chamar script principal via `subprocess`, capturar stdout, achar última linha JSON válida, e passar via stdin para `smart_notify_filter.py --job-name "X" --exit-code $?`. O filtro formata para Telegram e controla ruído.
14) **Dedupe file location:** `/opt/data/journali/processed-message-ids.jsonl` (append-only, 1 Message-ID por linha). Criar vazio no primeiro run se não existir.
15) **Classificação LLM — prompt restritivo descarta emails legítimos:** O modelo `openrouter/auto` classificava emails com "acessibilidade" como `irrelevante`. Solução: prompt simplificado com regra explícita "se contém keyword monitorada → NUNCA irrelevante", fallback keyword-based obrigatório quando LLM retorna `irrelevante` mas body/subject contém keywords do `IMAP_KEYWORDS`, testar modelos brasileiros (`sabia-3`, `portuguese-gpt`, `meta-llama/llama-3.1-8b-instruct:free`, `google/gemma-2-9b-it:free`).
16) **Parsing JSON do LLM instável:** Respostas com markdown code blocks ou texto extra quebram parser. Parser robusto: limpar ````json`/` ````, extrair entre `{` e `}`, fallback para pipe-delimited (`CATEGORIA|CONFIANCA|KEYWORDS|RESUMO|MOTIVO|ANGULOS`), log de responses inválidos para debug.
17) **Timeouts e limites de execução:** Adicionar `MAX_EMAILS_PER_RUN=100` e `MAX_PROCESSING_TIME=240s` (4 min) para evitar timeout do cron (5 min). Reduzir `MAX_EMAILS_PER_RUN` para 50 se necessário. Timeout HTTP 120s, retry 3x com backoff exponencial (`time.sleep(2 ** attempt)`).
18) **Relatório Markdown cumulativo + delta:** Script gera arquivo cumulativo (`triagem-YYYY-MM-DD-HH-MM.md`) com histórico de 15 dias + destaque dos novos, e arquivo delta (`triagem-delta-YYYY-MM-DD-HH-MM.md`) apenas itens novos desta execução. Cache JSON `/opt/data/journali/processed_items_cache.json` persiste histórico completo.
19) **Nome do arquivo com data E hora:** Como cron roda 3x/dia (09:00, 14:00, 18:00 BRT), usar timestamp `YYYY-MM-DD-HH-MM` no filename para manter os 3 arquivos do dia (`triagem-2026-07-28-21-19.md`, `triagem-2026-07-28-21-22.md`, `triagem-2026-07-28-21-24.md`).
20) **Renderização Markdown estruturada:** Tabelas/sections claras, metadados completos (Message-ID, data, assunto, remetente, keywords, resumo, ângulos), agrupamento por tipo (releases/pautas), ordenação cronológica. Template de item individual com bullets aninhados para fonte/data/link/resumo/confiança/keywords/ângulos.
21) **Keywords sem acentos para IMAP SEARCH:** IMAP server-side não suporta acentos em charset UTF-8. Remover acentos: `acessibilidade`, `deficiencia`, `inclusao`, `autismo`, `neurodiversidade`, `pcd`, `tea`, `wcag`, `e-mag`, `capacitismo`, `audiodescricao`, `leitor de tela`, `libras`, `tecnologia assistiva`, `design universal`.
20) **Renderização Markdown estruturada:** Tabelas/sections claras, metadados completos (Message-ID, data, assunto, remetente, keywords, resumo, ângulos), agrupamento por tipo (releases/pautas), ordenação cronológica. Template de item individual com bullets aninhados para fonte/data/link/resumo/confiança/keywords/ângulos.
20) **Keywords sem acentos para IMAP SEARCH:** IMAP server-side não suporta acentos em charset UTF-8. Remover acentos: `acessibilidade`, `deficiencia`, `inclusao`, `autismo`, `neurodiversidade`, `pcd`, `tea`, `wcag`, `e-mag`, `capacitismo`, `audiodescricao`, `leitor de tela`, `libras`, `tecnologia assistiva`, `design universal`.
21) **Deduplicação por hash de conteúdo no cache cumulativo:** O arquivo `processed-message-ids.jsonl` deduplica por Message-ID (funciona entre execuções). Mas emails reenviados/forward podem ter Message-IDs diferentes com mesmo conteúdo. O cache cumulativo (`processed_items_cache.json`) agora usa `content_hash()` = SHA256(assunto + resumo[:200])[:16] para deduplicar por conteúdo real. Adicionado em 2026-07-30: remoção de 3 duplicatas do cache (Fundação Dorina, Autismo, Concerto Theatro Municipal, Cotistas) e lógica no script principal para checar `existing_hashes` antes de adicionar novos itens.

## Cron Job Operacional (atualizado 2026-07-28)

| Campo | Valor |
|-------|-------|
| **Job ID** | `12d59b921ae1` |
| **Nome** | `JINC Gmail triagem-15d (placeholder)` |
| **Schedule** | `0 9 * * *` (diário 09:00 UTC = 06:00 BRT) |
| **Script** | `jinc_gmail_triagem_15d_filtered.py` |
| **Model** | `nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter |
| **Delivery** | `origin,telegram` (chat 965862678) |
| **Estado** | ✅ **enabled: true**, `state: scheduled` |
| **Próxima execução** | `2026-07-29T09:00:00+00:00` |

**Workflow do cron:**
1. Cron executa `jinc_gmail_triagem_15d_filtered.py` (wrapper)
2. Wrapper roda script principal → captura stdout JSON
3. Wrapper passa JSON via stdin para `smart_notify_filter.py --job-name "JINC Gmail Triagem" --exit-code $?`
4. `smart_notify_filter` formata mensagem Telegram, controla ruído, entrega via Hermes gateway
5. Exit code do script principal propagado para filtro

**Teste manual:**
```bash
cd /opt/data && python3 scripts/jinc_gmail_triagem_15d_filtered.py
```

## Resultado esperado
- Telegram com mensagem única diária
- Markdown diário com seções `## Releases` e `## Sugestões de pautas`
- Dedupe funcionando entre execuções

# LLM Classification Pitfalls — JINC Gmail Triagem (Session 2026-07-28)

## Problem Summary
The LLM (`openrouter/auto`) was classifying 93 emails containing "acessibilidade" as `irrelevante`, resulting in "Total de itens: 0" despite emails being fetched and processed (proven by 11 Message-IDs in dedupe file).

## Root Causes Identified

### 1. Overly Restrictive Prompt
The original prompt expected perfect JSON output with specific fields, and had implicit high threshold for "relevance". Emails about accessibility were being filtered out because:
- Prompt didn't explicitly say "keywords from IMAP_KEYWORDS = strong signal"
- Model didn't understand Jornalista Inclusivo Brazilian context
- `max_tokens=600` was truncating JSON responses mid-field

### 2. JSON Truncation
`max_tokens=600` was insufficient for:
```
{
  "categoria": "sugestao_de_pauta",
  "confianca": 0.95,
  "palavras_chave": ["acessibilidade", "inclusao", "deficiencia"],
  "resumo": "...",
  "motivo": "...",
  "angulos": ["...", "..."]
}
```
Truncation caused parsing failures, falling back to generic 50% confidence, no keywords, no angles.

### 3. Unstable JSON Parsing
LLM responses often wrapped in markdown code blocks or had preamble text:
```markdown
Here's the classification:
```json
{...}
```
```
Previous parser failed on these.

## Fixes Applied (in `/opt/data/scripts/jinc_gmail_triagem_15d.py`)

| Fix | Detail |
|-----|--------|
| **Prompt v2** | Simplified to pipe-delimited: `CATEGORIA|CONFIANCA|PALAVRAS_CHAVE|RESUMO|MOTIVO|ANGULOS`. Explicit rule: "SE assunto/corpo contém ANY keyword do IMAP_KEYWORDS → classificar como `pauta` ou `release`, NUNCA `irrelevante`" |
| **max_tokens=2000** | Increased from 600 to prevent truncation |
| **Parser robusto v2** | Regex `r'\{.*\}'` with `re.DOTALL` to extract first valid JSON, strip markdown fences, fallback to pipe-delimited split |
| **Fallback keyword-based** | Se LLM retorna `irrelevante` MAS body/subject contém keywords do `IMAP_KEYWORDS` → forçar `pauta` com confiança 0.8 |
| **Limites execução** | `MAX_EMAILS_PER_RUN=100`, `MAX_PROCESSING_TIME=240s`, HTTP timeout 120s, retry 3x backoff exponencial |
| **Modelos brasileiros para testar** | `sabia-3`, `portuguese-gpt`, `meta-llama/llama-3.1-8b-instruct:free`, `google/gemma-2-9b-it:free` |

## Keywords Sem Acentos (IMAP SEARCH compatible)
```
acessibilidade, deficiencia, inclusao, autismo, neurodiversidade,
pcd, tea, wcag, e-mag, capacitismo, audiodescricao, leitor de tela,
libras, tecnologia assistiva, design universal
```

## Output Format (Markdown Renderizado)
Arquivo: `triagem-YYYY-MM-DD-HH-MM.md`
```
# Triagem JINC — DD/MM/YYYY HH:MM (Cumulativo 15 dias)
**Total nos últimos 15 dias:** X itens (Y releases, Z sugestões)
**Novos nesta execução:** N (A releases, B sugestões)

## 📋 Todos os itens relevantes (últimos 15 dias)
### 💡 Sugestões de Pautas
#### 1. Título da Pauta
- **Fonte:** Nome <email@domain.com>
- **Data:** DD/MM/YYYY HH:MM
- **Link/ID:** <Message-ID>
- **Resumo:** Texto do resumo...
- **Confiança:** XX%
- **Palavras-chave:** keyword1, keyword2
- **Ângulos inclusivos:**
  - Ângulo 1
  - Ângulo 2
```

## Next Steps (Pending)
- [ ] Testar modelos brasileiros como fallback
- [ ] Validar se filtro label "JINC" remove emails relevantes (busca manual sem label encontrou 93, com label causou timeout)
- [ ] Ajustar threshold de confiança se muitos falsos positivos
- [ ] Documentar prompt final em `references/llm-prompt-final.md`
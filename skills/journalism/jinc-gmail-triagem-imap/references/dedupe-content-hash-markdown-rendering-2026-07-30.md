# Deduplicação por Hash de Conteúdo + Renderização Markdown Estruturada (2026-07-30)

## Contexto
Após a deduplicação por `Message-ID` funcionar corretamente (58 IDs persistidos no `processed-message-ids.jsonl` entre execuções do cron 3x/dia), descobriram-se **duplicatas semânticas** no cache cumulativo (`processed_items_cache.json`): emails reenviados por mailing lists/forwards chegam com Message-IDs diferentes mas **conteúdo idêntico** (assunto + resumo).

## Problema
- Cache tinha 28 itens, mas 4 duplicatas semânticas (Fundação Dorina Nowill, O autismo cresceu, Concerto Theatro Municipal, Por que cotistas abandonam)
- Mesmo conteúdo → Message-IDs diferentes → não deduplicados pelo mecanismo original

## Solução Implementada

### 1. Nova função `content_hash(item)`
```python
def content_hash(item: dict) -> str:
    """SHA256(assunto + '|' + resumo[:200]) -> 16 chars"""
    assunto = item.get("assunto", "").strip().lower()
    resumo = item.get("resumo", "").strip().lower()[:200]
    combined = f"{assunto}|{resumo}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]
```

### 2. Lógica de carregamento do cache com verificação dupla
```python
# No main():
existing_ids = {item.get("message_id") for item in all_items}
existing_hashes = {content_hash(item) for item in all_items}

# Ao adicionar novo item:
if message_id in existing_ids or content_hash(new_item) in existing_hashes:
    continue  # pula duplicata
```

### 3. Limpeza do cache histórico
Script de limpeza rodado uma vez:
```bash
cd /opt/data && python3 -c "
import json, hashlib
with open('/opt/data/journali/processed_items_cache.json') as f:
    items = json.load(f)
def ch(item):
    return hashlib.sha256((item.get('assunto','').lower().strip() + '|' + item.get('resumo','').lower().strip()[:200]).encode()).hexdigest()[:16]
seen, uniq = set(), []
for item in items:
    h = ch(item)
    if h not in seen:
        seen.add(h); uniq.append(item)
    else:
        print(f'DUPLICATA: {item[\"assunto\"][:60]}...')
with open('/opt/data/journali/processed_items_cache.json', 'w') as f:
    json.dump(uniq, f, ensure_ascii=False, indent=2)
print(f'Total: {len(items)} | Únicos: {len(uniq)} | Removidos: {len(items)-len(uniq)}')
"
```
**Resultado:** 28 → 24 itens únicos (4 duplicatas removidas)

### 4. Remoção de lógica duplicada no script
- Bloco linhas 653-675 (adicionava itens ao cache 2x e contava "novos" 2x) → **removido**
- Mantida apenas lógica única com verificação por `message_id` E `content_hash`

---

## Renderização Markdown Estruturada (v5 cumulativo)

### Template de item individual
```markdown
### {tipo_label}: {assunto}
- **Fonte:** {fonte}
- **Data:** {data}
- **Message-ID:** `<{message_id}>`
- **Link:** {link}
- **Resumo:** {resumo}
- **Confiança:** {confianca}%
- **Keywords:** {keywords}
- **Ângulos sugeridos:**
  - {angulo1}
  - {angulo2}
```

### Estrutura do relatório cumulativo (`triagem-YYYY-MM-DD-HH-MM.md`)
```markdown
# Triagem JINC — {data} (execução {HH:MM})

**Total de itens únicos (15 dias):** {total} | **Releases:** {releases} | **Pautas:** {pautas} | **Período:** {inicio} a {fim}

## 📦 Releases ({n})
| Fonte | Assunto | Data | Keywords | Resumo | Ângulos |
|-------|---------|------|----------|--------|---------|

## 📋 Sugestões de Pauta ({n})
| Fonte | Assunto | Data | Keywords | Resumo | Ângulos |
|-------|---------|------|----------|--------|---------|

## 📄 Itens Processados (Detalhamento)
{itens individuais ordenados cronologicamente desc}
```

### Exemplos gerados
- `triagem-2026-07-28-21-19.md` (11.917 chars)
- `triagem-2026-07-28-21-24.md` (cumulativo 13 itens, cache 13)
- `triagem-2026-07-30-22-48.md` (**24.162 chars, 24 itens únicos**, tabelas, seções, metadados completos)

---

## Atualizações no Cron Job
- **Job ID:** `12d59b921ae1`
- **Schedule:** `0 9,14,18 * * *` (3x/dia: 09:00, 14:00, 18:00 UTC = 06:00, 11:00, 15:00 BRT)
- **Filename pattern:** `triagem-YYYY-MM-DD-HH-MM.md` (evita sobrescrita nas 3 execuções/dia)
- **Status:** ✅ Ativo, testado via `hermes cron run 12d59b921ae1`

---

## Próximos Passos Pendentes
1. **Corrigir classificação LLM** — `openrouter/auto` ainda descarta emails com "acessibilidade" como `irrelevante`. Opções:
   - Ajustar prompt: regra explícita "se contém keyword monitorada → NUNCA irrelevante"
   - Fallback keyword-based obrigatório quando LLM retorna `irrelevante` mas body/subject tem keywords do `IMAP_KEYWORDS`
   - Testar modelos brasileiros: `sabia-3`, `portuguese-gpt`, `meta-llama/llama-3.1-8b-instruct:free`, `google/gemma-2-9b-it:free`
2. **Validar filtro label "JINC"** — busca com `LABEL JINC` causou timeout (30s); busca manual sem label encontrou 93 mensagens
3. **Teste IMAP isolado com label** — replicar lógica passo a passo
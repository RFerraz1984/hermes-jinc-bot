# Cron Jobs — Context Length Pitfall & Standalone Script Pattern

## Problema
Anexar `skills: ["journalist-inclusion-research"]` a um cron job injeta TODO o SKILL.md + references no prompt do agente (~5-7k tokens). Com o system prompt padrão (Identity/Style/Avoid/Defaults ~4k tokens), o total excede o limite de contexto antes de qualquer `web_search`.

**Erro observado**: `RuntimeError: Context length exceeded (6,400 tokens). Cannot compress further.`

## Solução: Scripts Standalone (no_agent mode)

### Padrão
1. Criar script Python em `/opt/data/home/.hermes/scripts/` (ex: `inclusion-digest.py`, `ia-tech-digest.py`)
2. Script usa `from hermes_tools import web_search, web_extract` diretamente
3. Cron job com `no_agent: true` e `script: "nome-do-script.py"`
4. Output do script (stdout) é entregue direto — sem system prompt, sem skill injection

### Exemplo de script (`inclusion-digest.py`)
```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/hermes')
from hermes_tools import web_search, web_extract

queries = [
    "acessibilidade PcD Brasil 2026 site:jornalistainclusivo.com",
    "inclusão deficiência 2026 site:diariopcd.com.br",
    "direitos humanos acessibilidade 2026 site:agenciabrasil.ebc.com.br",
    "MDHC 2026 acessibilidade",
    "Dataverso PcD 2026"
]

all_results = []
for q in queries:
    result = web_search(query=q, limit=3)
    items = result.get('data', {}).get('web', [])
    for item in items:
        item['query'] = q
        all_results.append(item)

if not all_results:
    print("[SILENT]")
    sys.exit(0)

urls = list(set(r['url'] for r in all_results if 'url' in r))[:10]
extracted = web_extract(urls=urls)

seen = set()
output = []
for ext in extracted.get('results', []):
    if ext.get('error') or not ext.get('content'):
        continue
    url = ext['url']
    if url in seen: continue
    seen.add(url)
    content = ext.get('content', '').lower()
    if '2026' not in content and any(y in content for y in ['2025','2024','2023']):
        continue
    title = ext.get('title', 'Sem título')[:120]
    source = url.split('/')[2] if '://' in url else 'Web'
    summary = ext.get('content', '')[:300].replace('\n', ' ').strip()
    output.append(f"- {title} — {source} — {url} — {summary}")
    if len(output) >= 5: break

if not output:
    print("[SILENT]")
else:
    print('\n'.join(output))
```

### Cron job creation
```bash
cronjob create \
  --name "weekly-inclusion-digest" \
  --schedule "0 19 * * 5" \
  --no_agent true \
  --script "inclusion-digest.py" \
  --deliver telegram
```

## Lição
- **NÃO** anexar skills a cron jobs de pesquisa recorrentes
- **SIM** usar scripts standalone + `no_agent: true`
- Scripts ficam em `/opt/data/home/.hermes/scripts/` (persistente em `/opt/data`)
# Multi-feed RSS no JINC (multiplatform-post.sh) — robustez no cron

## Objetivo
Adicionar/combinar feeds equivalentes (ex.: `jornalistainclusivo.com.br/feed` e `jornalistainclusivo.com/feed`) sem quebrar o script quando rodar em cron.

## Mudanças recomendadas (hardening)
1. **Use `RSS_URLS` como lista** (separada por espaço ou vírgula):
   - Ex.: `RSS_URLS="https://site1/feed https://site2/feed"`
2. **Itere de forma segura sob `set -u`** (avoid `${VAR//,/}` quando a variável pode não existir).
   - Padrão robusto em bash:
     - `for RSS_URL in $(echo "${RSS_URLS}" | tr ',' ' '); do ...; done`
3. **Deduplicação** deve ser por chave estável:
   - o script atual usa `GUID` do RSS (fallback para `link`) e grava no `multiplatform-posted-ids.txt` como `id|title|link`.

## Debug rápido (quando falhar em cron)
- Verifique se o cron realmente exporta `RSS_URLS`:
  - adicione temporariamente `echo "RSS_URLS=$RSS_URLS"` no início do script.
- Se aparecer `unbound variable`:
  - é sinal de variável não definida sob `set -u`; garanta defaults: `RSS_URLS="${RSS_URLS:-...}"`.

## Exemplo de uso no cron
```bash
RSS_URLS="https://jornalistainclusivo.com/br/feed https://jornalistainclusivo.com/feed" /opt/data/scripts/multiplatform-post.sh
```

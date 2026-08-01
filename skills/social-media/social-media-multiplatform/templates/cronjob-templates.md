# Cron Job Templates — Multi-Platform Posting

## Fase 1: Bluesky + Telegram Channel (Recomendado iniciar aqui)
```bash
# Criar job (roda a cada 30 min)
cronjob create \
  --name "JINC Multi: Bluesky+Telegram" \
  --schedule "*/30 * * * *" \
  --prompt "Executar /opt/data/scripts/multiplatform-post.sh (apenas Bluesky e Telegram Channel ativos). O script lê RSS do jornalistainclusivo.com.br/feed, deduplica via /opt/data/multiplatform-posted-ids.txt, e posta em cada plataforma configurada. Variáveis necessárias: TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID. bsky CLI deve estar autenticado com 'bsky auth login'."

# Ou via skill hermes-umbrel-operations:
# hermes cron create --name "JINC Multi: Bluesky+Telegram" --schedule "*/30 * * * *" --script "/opt/data/scripts/multiplatform-post.sh"
```

## Fase 2: X/Twitter (após xurl configurado)
```bash
cronjob create \
  --name "JINC X/Twitter" \
  --schedule "*/30 * * * *" \
  --prompt "Executar /opt/data/scripts/rss-to-x.sh que monitora RSS do jornalistainclusivo.com.br/feed e posta novidades no X via xurl. Requer xurl instalado e autenticado (HOME=/opt/data/home xurl auth status). Estado em /opt/data/rss-posted-ids.txt."
```

## Fase 3: Facebook Page (após App Review aprovado)
```bash
cronjob create \
  --name "JINC Facebook Page" \
  --schedule "0 * * * *" \
  --prompt "Executar post no Facebook Page via Graph API. Usar FB_PAGE_ACCESS_TOKEN e FB_PAGE_ID das env vars. Rate limit: 200 posts/hora por Page. Rodar hourly para ser conservador. Template de mensagem: 'Novo artigo no Jornalista Inclusivo: \"{title}\" 🔗 {link} #Acessibilidade #PcD #Inclusão'"
```

## Job Combinado (Todas as Plataformas Ativas)
```bash
cronjob create \
  --name "JINC Multi-Platform Full" \
  --schedule "*/30 * * * *" \
  --prompt "Executar /opt/data/scripts/multiplatform-post.sh completo. O script tenta postar em todas as plataformas configuradas (Bluesky, Telegram, X/Twitter, Facebook) e ignora as que não têm credenciais. Logs mostram ✅/❌ por plataforma. Estado persistente em /opt/data/multiplatform-posted-ids.txt. Max 3 posts por execução."
```

## Testar Manualmente Antes do Cron
```bash
# No terminal do container:
cd /opt/data/scripts
chmod +x multiplatform-post.sh

# Testar apenas Bluesky + Telegram (Fase 1)
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHANNEL_ID=... ./multiplatform-post.sh

# Verificar estado
cat /opt/data/multiplatform-posted-ids.txt

# Ver logs do cron
tail -f /opt/data/logs/gateway.log  # logs do Hermes gateway
# ou saída do cron job em /opt/data/cron/output/
```

## Parâmetros de Ajuste (editar no script ou via env vars)
```bash
# No script multiplatform-post.sh:
MAX_POSTS_PER_RUN=3        # posts por execução (padrão: 3)
RSS_URL="..."              # feed alternativo se necessário

# Via env vars no container:
MAX_POSTS_PER_RUN=5
RSS_URL="https://outro-site.com/feed"
```

## Monitoramento
```bash
# Ver jobs ativos
cronjob list

# Ver última execução
cronjob run --job_id <id>  # disparo manual para testar

# Logs de erro
grep -i error /opt/data/cron/output/*.log
```
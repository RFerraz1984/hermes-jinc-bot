# Script rss-md.py — RSS para Telegram (Jornalista Inclusivo)

## Visão Geral
Script Python simples em `/opt/data/scripts/rss-md.py` que:
1. Faz parse do feed RSS do Jornalista Inclusivo (domínios `.com` e `.com.br`)
2. Gera Markdown com lista de artigos (título + link + data)
3. Envia para canal Telegram via Bot API

## Cron Job Existente
- **Nome**: `jornalistainclusivo/rss-md`
- **ID**: `d52faa4a94ae`
- **Schedule**: `30 12 * * *` (diário às 12:30 UTC)
- **Comando**: Executa ambos os feeds em sequência:
  ```bash
  /opt/data/venv/rss-md/bin/python3 /opt/data/scripts/rss-md.py --feed 'https://jornalistainclusivo.com/feed' --max-items 10 && /opt/data/venv/rss-md/bin/python3 /opt/data/scripts/rss-md.py --feed 'https://jornalistainclusivo.com.br/feed' --max-items 10
  ```
- **Delivery**: `origin,telegram:965862678`
- **Toolsets**: `[\"terminal\"]`

> **Nota**: O cron job referencia um venv dedicado em `/opt/data/venv/rss-md/` com dependências instaladas.

## Problemas Identificados e Corrigidos

### 1. Argumento `--feed` ignorado (Bug) — **CORRIGIDO em 2026-07-05**
O script original tinha URL hardcoded. Versão atual usa `argparse` corretamente:
```python
parser = argparse.ArgumentParser()
parser.add_argument('--feed', default='https://jornalistainclusivo.com.br/feed')
args = parser.parse_args()
feed = feedparser.parse(args.feed)  # usa args.feed
```

### 2. **python-telegram-bot v20+ Async** — **CORRIGIDO em 2026-07-06**
`Bot.send_message()` é assíncrono e deve ser `await`ed.

**Erro original:**
```
RuntimeWarning: coroutine 'Bot.send_message' was never awaited
Bot(bot_token).send_message(chat_id=int(channel_id), text=markdown, parse_mode='Markdown', disable_web_page_preview=True)
```

**Fix aplicado:**
```python
import asyncio
from telegram import Bot

async def send_telegram(channel_id, markdown):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    bot = Bot(bot_token)
    await bot.send_message(chat_id=int(channel_id), text=markdown, parse_mode='Markdown', disable_web_page_preview=True)

asyncio.run(send_telegram(os.getenv('TELEGRAM_HOME_CHANNEL'), output['markdown']))
```

Testado com o venv do cron job (`/opt/data/venv/rss-md/bin/python`) — exit code 0, JSON válido, mensagem Telegram enviada.

### 3. **Suporte a Múltiplos Feeds + Limite de Itens** — **ADICIONADO em 2026-07-06**
- Feed `.com` (Jornalista Inclusivo) tem 40+ artigos → excede limite de 4096 chars do Telegram
- Feed `.com.br` (Guia do Jornalismo Inclusivo) tem 5 artigos
- Adicionado argumento `--max-items` (padrão: 10) para limitar saída

**Uso:**
```bash
# Feed .com (10 artigos mais recentes)
/opt/data/venv/rss-md/bin/python3 /opt/data/scripts/rss-md.py --feed 'https://jornalistainclusivo.com/feed' --max-items 10

# Feed .com.br (todos os 5 artigos)
/opt/data/venv/rss-md/bin/python3 /opt/data/scripts/rss-md.py --feed 'https://jornalistainclusivo.com.br/feed' --max-items 10
```

**Feeds Monitorados:**
| Feed | Título | Artigos Recentes |
|------|--------|------------------|
| `jornalistainclusivo.com/feed` | **Jornalista Inclusivo** | 10 artigos (jul/2026 a mar/2026) |
| `jornalistainclusivo.com.br/feed` | **Guia do Jornalismo Inclusivo** | 5 artigos (jun/2026 a jul/2025) |

### 4. Dependências — **INSTALADAS no venv dedicado**
Criado `/opt/data/venv/rss-md/` com:
```bash
cd /opt/data && python3 -m venv venv/rss-md
/opt/data/venv/rss-md/bin/pip install pyyaml feedparser python-telegram-bot
```
Dependências: `pyyaml`, `feedparser`, `python-telegram-bot` (v22.8), `httpx`, `anyio`, `sgmllib3k`.

## State File
O script **não** mantém state file (deduplicação) — envia os últimos N itens a cada execução. Para deduplicação, usar o script multi-plataforma (`multiplatform-post.sh`) que usa state file `GUID|title|link` em `/opt/data/multiplatform-posted-ids.txt`.

## Diferenças para `multiplatform-post.sh`
| Aspecto | `rss-md.py` | `multiplatform-post.sh` |
|--------|-------------|------------------------|
| Objetivo | RSS → Telegram simples | RSS → Multi-plataforma (Bluesky, Telegram, X, FB) |
| Deduplicação | Não (envia últimos N) | Sim (state file por GUID) |
| Plataformas | Só Telegram | Bluesky, Telegram, X/Twitter, Facebook |
| Formato | Markdown + JSON stdout | Markdown por plataforma |
| Schedule | Diário 12:30 UTC | A cada 30 min |
| Cron Job | `jornalistainclusivo/rss-md` | `JINC Multi: Bluesky + Telegram Channel` |

## Próximos Passos Sugeridos
1. Adicionar state file (deduplicação por GUID) ao `rss-md.py` para evitar reenvio diário dos mesmos artigos
2. Considerar unificar com `multiplatform-post.sh` se Telegram for o único destino do `rss-md.py`
3. Monitorar se `--max-items 10` é suficiente ou ajustar por feed
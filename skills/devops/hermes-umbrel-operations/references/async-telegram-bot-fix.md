# Async Telegram Bot Fix — python-telegram-bot v20+

## Problema

`python-telegram-bot` v20+ usa métodos assíncronos. O método `Bot.send_message()` retorna uma coroutine que **precisa ser awaited**.

**Erro típico:**
```
RuntimeWarning: coroutine 'Bot.send_message' was never awaited
telegram.error.InvalidToken: You must pass the token you received from https://t.me/Botfather!
```

## Fix Padrão

```python
import asyncio
from telegram import Bot
import os

async def send_telegram(channel_id: str, markdown: str):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    bot = Bot(bot_token)
    await bot.send_message(
        chat_id=int(channel_id),
        text=markdown,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

# No main (síncrono):
asyncio.run(send_telegram(os.getenv('TELEGRAM_HOME_CHANNEL'), output['markdown']))
```

## Contexto desta Sessão

Script: `/opt/data/scripts/rss-md.py`
- Cron job: `jornalistainclusivo/rss-md` (ID: `d52faa4a94ae`)
- Venv: `/opt/data/venv/rss-md/bin/python`
- Schedule: `30 12 * * *` (diário 12:30 UTC)
- Fix aplicado em 2026-07-05
- Teste manual: exit_code 0 ✅

## Padrão Geral para Scripts Standalone em Cron Jobs

Quando usar `python-telegram-bot` em scripts que rodam via cron (fora de event loop):

```python
import asyncio

async def minha_funcao_async():
    # código assíncrono aqui
    pass

if __name__ == "__main__":
    asyncio.run(minha_funcao_async())
```

> **Nota**: Evite `asyncio.get_event_loop().run_until_complete()` — deprecated no Python 3.10+. Use `asyncio.run()`.
#!/usr/bin/env python3
"""
RSS para Markdown + Telegram — Jornalista Inclusivo

Parse RSS feeds from jornalistainclusivo.com and jornalistainclusivo.com.br,
generate Markdown summary, and send to Telegram channel.

Usage:
    python3 rss-md.py --feed URL [--max-items N]

Args:
    --feed: RSS feed URL (default: https://jornalistainclusivo.com.br/feed)
    --max-items: Maximum items to include (default: 10)
"""

import yaml
import json
import feedparser
import argparse
from time import strftime
import os
from telegram import Bot
import asyncio

parser = argparse.ArgumentParser()
parser.add_argument('--feed', default='https://jornalistainclusivo.com.br/feed')
parser.add_argument('--max-items', type=int, default=10, help='Maximum number of items to include in output')
args = parser.parse_args()

feed = feedparser.parse(args.feed)

output = {
    'feed': {
        'title': feed.feed.title,
        'link': feed.feed.link,
        'items': []
    },
    'markdown': f"## {feed.feed.title}\n\n"
}

def format_date(entry):
    if hasattr(entry, 'date'):
        return strftime('%Y-%m-%d %H:%M:%S', feedparser._parse_date_value(entry.date))
    elif hasattr(entry, 'published_parsed'):
        return strftime('%Y-%m-%d %H:%M:%S', entry.published_parsed)
    elif hasattr(entry, 'updated_parsed'):
        return strftime('%Y-%m-%d %H:%M:%S', entry.updated_parsed)
    return 'Data não disponível'


async def send_telegram(channel_id, markdown):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    bot = Bot(bot_token)
    await bot.send_message(chat_id=int(channel_id), text=markdown, parse_mode='Markdown', disable_web_page_preview=True)

for entry in feed.entries[:args.max_items]:
    output['feed']['items'].append({
        'title': entry.title,
        'link': entry.link,
        'date': format_date(entry)
    })
    output['markdown'] += f"- [{entry.title}]({entry.link}) - {format_date(entry)}\n"

asyncio.run(send_telegram(os.getenv('TELEGRAM_HOME_CHANNEL'), output['markdown']))
print(json.dumps(output))
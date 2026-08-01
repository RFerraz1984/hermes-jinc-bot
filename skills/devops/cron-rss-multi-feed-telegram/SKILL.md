---
name: cron-rss-multi-feed-telegram
description: Enviar posts de múltiplos feeds RSS em um único cron job (deduplicação e entrega Telegram).
version: "1.1"
author: Hermes Agent
license: MIT
platforms: [linux]
tags: [cron, rss, telegram, deduplication]
---

# Cron job RSS → Markdown → Telegram (múltiplos feeds)

## Objetivo
Rodar um cron job que coleta artigos de **mais de um feed RSS** (ex.: domínio com e sem `.br`) e publica em Telegram, evitando spam com **deduplicação por GUID/link**.

## Padrão recomendado (classe do task)
1. **Um script** que aceita `RSS_URLS="feed1 feed2"`.
2. Loop por cada `RSS_URL` para coletar itens.
3. Construir posts por item e tentar publicação em plataformas.
4. Persistir IDs postados em um `STATE_FILE` com formato `id|title|link`.

## Exemplos de variáveis
- `RSS_URLS`: lista separada por espaço ou vírgula.
- `STATE_FILE`: arquivo persistente em `/opt/data/`.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID` (no `.env`).

## Deduplicação
- ID principal: `guid` (se existir no RSS)
- fallback: `link`.
- Armazenar em `STATE_FILE` o primeiro campo (`id`) por linha.

## Boas práticas
- **Publicar só quando houver novidade:** use deduplicação por `guid` (fallback `link`) + persistência em `STATE_FILE`.
- Para Telegram: limite o tamanho da mensagem (ou use `--max-items`).
- Para cron: não dependa de `toolsets` globais se o job usa ferramenta específica; force por job.
- Se você pausar outro job “backup” (ex.: `rss-md`) que também envia para Telegram, evite duplicidade ao coexistir com o multi-feed.

## Implementação (no seu setup atual)
### Script usado
- `/opt/data/scripts/multiplatform-post.sh`

### Como configurar
No cron job `JINC Multi: Bluesky + Telegram Channel`, execute:

```bash
export RSS_URLS='https://jornalistainclusivo.com/feed https://jornalistainclusivo.com.br/feed'; /opt/data/scripts/multiplatform-post.sh
```

## ## Observações de segurança
- RSS costuma ser XML: idealmente usar parser com proteção contra XXE (ex.: `defusedxml`).
- No seu script atual, é usado `xml.etree.ElementTree` da stdlib. Isso funciona na prática para feeds confiáveis, mas **se você começar a usar fontes não confiáveis**, vale instalar `defusedxml` e substituir o parser.

## Limitador de tamanho (Telegram)
- Mensagens longas podem falhar com `BadRequest: Message is too long`.
- Se você estiver montando payloads grandes, reduza a quantidade de itens por execução (ex.: `MAX_POSTS_PER_RUN`) ou aplique limites por plataforma.


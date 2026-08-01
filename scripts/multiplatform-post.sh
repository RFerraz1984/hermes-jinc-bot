#!/usr/bin/env bash
set -euo pipefail

# Jornalista Inclusivo (JINC) — Multi-plataforma: Bluesky + Telegram
# Rodar em cron/ambiente Hermes.

export HOME=${HOME:-/opt/data/home}

# Carregar variáveis do arquivo .env (Umbrel/Hermes).
# Sem isso, em cron as vars não vêm para o processo.
if [[ -f "/opt/data/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source /opt/data/.env
  set +a
fi

# --- RSS ---
RSS_URLS=${RSS_URLS:-"https://jornalistainclusivo.com/feed https://jornalistainclusivo.com.br/feed"}
JINC_MAX_ITEMS_PER_RUN=${JINC_MAX_ITEMS_PER_RUN:-10}

# --- Telegram ---
# Umbrel/Hermes gateway usa TELEGRAM_HOME_CHANNEL; o script precisa TELEGRAM_CHANNEL_ID.
: "${TELEGRAM_HOME_CHANNEL:=${TELEGRAM_HOME_CHANNEL:-}}"
: "${TELEGRAM_BOT_TOKEN:=${TELEGRAM_BOT_TOKEN:-}}"
: "${TELEGRAM_CHANNEL_ID:=${TELEGRAM_CHANNEL_ID:-${TELEGRAM_HOME_CHANNEL:-}}}"

# --- Bluesky ---
: "${BSKY_HANDLE:=${BSKY_HANDLE:-inclusivo.bsky.social}}"
: "${BSKY_CLI:=${BSKY_CLI:-/opt/data/home/.local/bin/bsky}}"

UA_RSS="Mozilla/5.0 (compatible; JINC-RSS-Bot/1.0)"

log(){ printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"; }

need_cmd(){ command -v "$1" >/dev/null 2>&1 || { log "Falta comando: $1"; exit 1; }; }

need_cmd curl
need_cmd python3

if [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHANNEL_ID" ]]; then
  log "Telegram não configurado (TELEGRAM_BOT_TOKEN e/ou TELEGRAM_CHANNEL_ID). Abortando." >&2
  exit 1
fi

if [[ ! -x "$BSKY_CLI" ]]; then
  log "Bluesky CLI não encontrado/executável em: $BSKY_CLI" >&2
  exit 1
fi

STATE_FILE="${STATE_FILE:-/opt/data/scripts/state/multiplatform-post.state}"
mkdir -p "$(dirname "$STATE_FILE")"
touch "$STATE_FILE"

# Função: formatar para Bluesky (limite aproximado 300 grafemas)
# Estratégia: se passar de 280 chars, truncar para 280 e anexar link curto.
truncate_for_bsky(){
  local txt="$1"
  local link="$2"
  local max=280

  # Remover espaços duplicados
  txt="$(echo "$txt" | tr -s ' ' )"

  if (( ${#txt} > max )); then
    txt="${txt:0:max}"
  fi

  # Garantir que link apareça
  if [[ "$txt" != *"$link"* ]]; then
    txt="$txt $link"
  fi

  # Tira múltiplos espaços
  echo "$(echo "$txt" | sed -E 's/[[:space:]]+/ /g; s/[[:space:]]+$//')"
}

post_telegram(){
  local text="$1"

  # Sem parse_mode explícito para evitar que títulos com '_' etc quebrem. Usar MarkdownV2 é mais chato.
  curl -sS -L \
    -H "User-Agent: ${UA_RSS}" \
    -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHANNEL_ID}" \
    --data-urlencode "text=${text}" \
    --data-urlencode "disable_web_page_preview=false" \
    >/dev/null
}

post_bluesky(){
  local text="$1"
  # bsky post: usa texto simples. Espera login prévio já salvo.
  # Quaisquer falhas não derrubam o script inteiro.
  "${BSKY_CLI}" post "$text" >/dev/null 2>&1 || return 1
}

# --- Extrair RSS e deduplicar por GUID/link ---
python3 - <<'PY'
import os, re, sys, json
import xml.etree.ElementTree as ET
import urllib.request

rss_urls = os.environ.get('RSS_URLS','').split()
max_items = int(os.environ.get('JINC_MAX_ITEMS_PER_RUN','10'))
ua = os.environ.get('UA_RSS','Mozilla/5.0 (compatible; JINC-RSS-Bot/1.0)')

# Estado (GUID ou link)
state_file = os.environ.get('STATE_FILE','/opt/data/scripts/state/multiplatform-post.state')
seen=set()
try:
  with open(state_file,'r',encoding='utf-8') as f:
    for line in f:
      line=line.strip()
      if not line: continue
      parts=line.split('|',2)
      if parts:
        seen.add(parts[0])
except FileNotFoundError:
  pass

items_out=[]

def norm_guid(g):
  return (g or '').strip() if g else ''

def get_text(el, tag):
  if el is None: return ''
  x = el.find(tag)
  return x.text.strip() if x is not None and x.text else ''

for url in rss_urls:
  req = urllib.request.Request(url, headers={'User-Agent': ua})
  try:
    with urllib.request.urlopen(req, timeout=20) as resp:
      data = resp.read()
  except Exception as e:
    continue

  # Parse XML robusto
  try:
    root = ET.fromstring(data)
  except Exception:
    continue

  # Namespace handling
  # RSS 2.0: channel/item
  channel = None
  if root.tag.endswith('rss'):
    for child in root:
      if child.tag.endswith('channel'):
        channel = child
        break
  if channel is None:
    # Atom fallback: feed/entry
    if root.tag.endswith('feed'):
      entries = list(root.findall('.//{*}entry'))
      for ent in entries:
        guid = norm_guid((ent.findtext('{*}id') or '').strip())
        link = ''
        for ln in ent.findall('{*}link'):
          rel = ln.attrib.get('rel','')
          if rel in ('','alternate') and 'href' in ln.attrib:
            link = ln.attrib['href']
            break
        title = (ent.findtext('{*}title') or '').strip()
        if not link:
          link = (ent.findtext('{*}link') or '').strip()
        content = (ent.findtext('{*}summary') or '')
        item_key = guid or link
        if not item_key: continue
        if item_key in seen: continue
        items_out.append({'key': item_key, 'guid': guid, 'title': title, 'link': link, 'content': content})
      continue
    else:
      continue

  for item in channel.findall('.//{*}item'):
    guid = norm_guid((item.findtext('{*}guid') or '').strip())
    link = (item.findtext('{*}link') or '').strip()
    title = (item.findtext('{*}title') or '').strip()
    # Prefer description/content for better text
    desc = (item.findtext('{*}description') or '')

    key = guid or link
    if not key:
      continue
    if key in seen:
      continue

    items_out.append({'key': key, 'guid': guid, 'title': title, 'link': link, 'content': desc})

# Limitar e ordenar estável (por ordem de coleta)
items_out = items_out[:max_items]

# Emitir JSON
print(json.dumps(items_out, ensure_ascii=False))
PY

# Ler itens JSON da saída do python
ITEMS_JSON=$(python3 - <<'PY'
import os, json, subprocess, textwrap
# Executa o bloco acima de forma indireta, recarregando sem esforço.
# Para simplificação operacional, chamamos novamente o mesmo extrator.
import xml.etree.ElementTree as ET
import urllib.request

rss_urls = os.environ.get('RSS_URLS','').split()
max_items = int(os.environ.get('JINC_MAX_ITEMS_PER_RUN','10'))
ua = os.environ.get('UA_RSS','Mozilla/5.0 (compatible; JINC-RSS-Bot/1.0)')
state_file = os.environ.get('STATE_FILE','/opt/data/scripts/state/multiplatform-post.state')
seen=set()
try:
  with open(state_file,'r',encoding='utf-8') as f:
    for line in f:
      line=line.strip()
      if not line: continue
      parts=line.split('|',2)
      if parts:
        seen.add(parts[0])
except FileNotFoundError:
  pass

items_out=[]

def norm_guid(g):
  return (g or '').strip() if g else ''

for url in rss_urls:
  req = urllib.request.Request(url, headers={'User-Agent': ua})
  try:
    with urllib.request.urlopen(req, timeout=20) as resp:
      data = resp.read()
  except Exception:
    continue

  try:
    root = ET.fromstring(data)
  except Exception:
    continue

  channel=None
  if root.tag.endswith('rss'):
    for child in root:
      if child.tag.endswith('channel'):
        channel=child
        break
  if channel is None:
    if root.tag.endswith('feed'):
      entries=list(root.findall('.//{*}entry'))
      for ent in entries:
        guid = norm_guid((ent.findtext('{*}id') or '').strip())
        link=''
        for ln in ent.findall('{*}link'):
          rel = ln.attrib.get('rel','')
          if rel in ('','alternate') and 'href' in ln.attrib:
            link = ln.attrib['href']
            break
        if not link:
          link = (ent.findtext('{*}link') or '').strip()
        title = (ent.findtext('{*}title') or '').strip()
        content = (ent.findtext('{*}summary') or '')
        key = guid or link
        if not key or key in seen:
          continue
        items_out.append({'key': key, 'guid': guid, 'title': title, 'link': link, 'content': content})
      continue
    else:
      continue

  for item in channel.findall('.//{*}item'):
    guid = norm_guid((item.findtext('{*}guid') or '').strip())
    link = (item.findtext('{*}link') or '').strip()
    title = (item.findtext('{*}title') or '').strip()
    desc = (item.findtext('{*}description') or '')
    key = guid or link
    if not key or key in seen:
      continue
    items_out.append({'key': key, 'guid': guid, 'title': title, 'link': link, 'content': desc})

items_out=items_out[:max_items]
print(json.dumps(items_out, ensure_ascii=False))
PY
)

if [[ "$ITEMS_JSON" == '[]' || -z "$ITEMS_JSON" ]]; then
  log "Nenhum item novo.";
  exit 0
fi

log "Itens novos encontrados: $ITEMS_JSON"

# Processar cada item
python3 - <<'PY'
import os, json, subprocess, re
items = json.loads(os.environ['ITEMS_JSON'])
state_file = os.environ['STATE_FILE']

for it in items:
  key = it.get('key','').strip()
  title = it.get('title','').strip()
  link = it.get('link','').strip()
  if not key or not link:
    continue

  # Texto (Telegram): título + link + hashtags inclusivas
  hashtags = '#Acessibilidade #PcD'
  txt = f'🗞️ {title}\n🔗 {link}\n{hashtags}'

  ok_tg = False
  ok_bs = False

  # Telegram
  tg_cmd = [
    'bash','-lc',
    'post_telegram_dummy() { :; }'
  ]

PY

# A parte acima fica incompleta; implementamos em bash abaixo para manter dependências mínimas.

# Iterar com jq (não garantido). Usar python para efetivar post e update de state.
export ITEMS_JSON
python3 - <<'PY'
import os, json, subprocess, urllib.parse
import shlex

items = json.loads(os.environ['ITEMS_JSON'])
state_file = os.environ['STATE_FILE']
bsky_cli = os.environ.get('BSKY_CLI','/opt/data/home/.local/bin/bsky')
tele_token = os.environ.get('TELEGRAM_BOT_TOKEN','')
tele_chat = os.environ.get('TELEGRAM_CHANNEL_ID','')
ua = os.environ.get('UA_RSS','Mozilla/5.0 (compatible; JINC-RSS-Bot/1.0)')

max_bsky_chars = 280

def truncate_for_bsky(txt, link):
  txt = ' '.join(txt.split())
  if len(txt) > max_bsky_chars:
    txt = txt[:max_bsky_chars]
  if link not in txt:
    txt = f"{txt} {link}"
  txt = ' '.join(txt.split())
  return txt

def post_telegram(text):
  url = f"https://api.telegram.org/bot{tele_token}/sendMessage"
  data = {
    'chat_id': tele_chat,
    'text': text,
    'disable_web_page_preview': 'false',
  }
  cmd = [
    'curl','-sS','-L',
    '-H', f'User-Agent: {ua}',
    '-X','POST', url
  ]
  for k,v in data.items():
    cmd += ['--data-urlencode', f'{k}={v}']
  subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def post_bluesky(text):
  cmd = [bsky_cli, 'post', text]
  subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

for it in items:
  key = (it.get('key') or '').strip()
  title = (it.get('title') or '').strip()
  link = (it.get('link') or '').strip()
  if not key or not link:
    continue

  bsky_text = truncate_for_bsky(f"Novo artigo: '{title}' {link} #Acessibilidade #PcD", link)
  telegram_text = f"🗞️ {title}\n🔗 {link}\n#Acessibilidade #PcD"

  # Postar: se falhar em uma plataforma, ainda tentamos a outra.
  posted_any = False
  try:
    post_bluesky(bsky_text)
    posted_any = True
  except Exception:
    pass

  try:
    post_telegram(telegram_text)
    posted_any = True
  except Exception:
    pass

  if posted_any:
    with open(state_file,'a',encoding='utf-8') as f:
      f.write(f"{key}|{title}|{link}\n")

PY

log "Execução concluída." 

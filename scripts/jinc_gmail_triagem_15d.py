#!/usr/bin/env python3
"""
JINC Gmail Triagem - 15 dias (LLM-Enhanced)
Pipeline IMAP para triagem inteligente de emails sobre inclusão/acessibilidade/deficiência.
Usa LLM via OpenRouter para classificação semântica e extração de ângulos jornalísticos.
Gera relatório diário em Markdown e notifica via Telegram (smart_notify_filter).
"""

import imaplib
import email
from email.message import Message
import json
import os
import sys
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from email.header import decode_header
from email.utils import parsedate_to_datetime
import hashlib

# Carregar .env do Hermes
def load_env_file(path: str):
    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env_file("/opt/data/.env")

# Config
MAX_EMAILS_PER_RUN = 100  # Limit LLM calls per run to avoid timeout
MAX_PROCESSING_TIME = 240  # 4 minutes max
CONFIG_PATH = Path("/opt/data/journali/imap-config.json")
DEDUPE_PATH = Path("/opt/data/journali/processed-message-ids.jsonl")
OUTPUT_DIR = Path("/opt/data/journali")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# OpenRouter config
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
# Use a model that doesn't output reasoning tokens
LLM_MODEL = "openrouter/auto"
LLM_BASE_URL = "https://openrouter.ai/api/v1"

# Palavras-chave para busca IMAP inicial (filtro amplo) - sem acentos para IMAP SEARCH server-side
IMAP_KEYWORDS = [
    "acessibilidade", "deficiencia", "inclusao", "autismo", "neurodiversidade",
    "pcd", "tea", "wcag", "e-mag", "capacitismo", "pessoa com deficiencia",
    "deficiente", "inclusivo", "neurodivergente", "tecnologia assistiva",
    "audiodescricao", "legenda", "libras", "braile", "acesso universal",
    "desenho universal", "barreira", "barreiras", "exclusao", "exclusão",
    "direitos humanos", "pessoa com deficiencia", "pessoas com deficiencia",
    "pessoa com autismo", "pessoas com autismo",
    "sindrome de down", "síndrome de down", "down",
    "paralisia cerebral", "esquizofrenia", "transtorno bipolar", "tdah", "TDAH",
    "baixa visao", "baixa visão", "cegueira", "surdez", "surdos",
    "mobilidade reduzida", "cadeirante", "cadeirantes",
    "tecnologia assistiva", "recursos de acessibilidade", "acessibilidade digital",
    "acessibilidade arquitetonica", "acessibilidade arquitetônica",
    "acessibilidade comunicacional", "acessibilidade atitudinal",
    "linguagem simples", "leitura facil", "leitura fácil",
    "design inclusivo", "universal design",
    "hemofilia",
    "inclusao", "inclusão",
    "deficiencia", "deficiência",
    "audiodescricao", "audiodescrição",
    "acessibilidade", "acessibilidade",
]

# Palavras-chave para display/classificação (com acentos para matching local)
DISPLAY_KEYWORDS = [
    "acessibilidade", "deficiência", "inclusão", "autismo", "neurodiversidade",
    "PCD", "TEA", "WCAG", "e-MAG", "capacitismo", "pessoa com deficiência",
    "tecnologia assistiva", "audiodescrição", "Libras", "braille",
    "desenho universal", "barreiras", "exclusão", "direitos humanos",
    "pessoa com autismo", "síndrome de down", "paralisia cerebral",
    "baixa visão", "cegueira", "surdez", "mobilidade reduzida", "cadeirante",
    "acessibilidade digital", "acessibilidade arquitetônica",
    "acessibilidade comunicacional", "acessibilidade atitudinal",
    "linguagem simples", "leitura fácil", "design inclusivo",
    "hemofilia",
]

# LLM Prompt Templates
CLASSIFICATION_PROMPT = """Você é um editor do Jornalista Inclusivo (JINC). Analise o email e classifique:

Email:
---
Assunto: {subject}
De: {from_addr}
Data: {date}
Corpo: {body}
---

Responda APENAS com JSON válido:
{{
  "categoria": "release|sugestao_de_pauta|irrelevante",
  "confianca": 0.0-1.0,
  "palavras_chave_relevantes": ["termo1", "termo2"],
  "resumo_uma_linha": "resumo em máx 160 chars",
  "motivo": "breve justificativa",
  "angulos": ["Ângulo 1 específico", "Ângulo 2 específico", "Ângulo 3 específico"]
}}

REGRAS:
- "release" = comunicado de imprensa/assessoria sobre inclusão/acessibilidade/PcD
- "sugestao_de_pauta" = conteúdo jornalístico relevante (notícias, artigos, relatórios, eventos)
- "irrelevante" = spam, marketing sem conexão, newsletters genéricas sem foco PcD
- Se email contém "acessibilidade", "deficiência", "inclusão", "PCD", "autismo", "TEA", "neurodiversidade", "WCAG", "e-MAG", "capacitismo", "audiodescrição", "Libras", "braille", "tecnologia assistiva" → NUNCA classifique como irrelevante
- Ângulos devem ser específicos para pauta jornalística inclusiva"""

def decode_mime_header(header: str) -> str:
    """Decodifica cabeçalho MIME encoded-word."""
    if not header:
        return ""
    parts = decode_header(header)
    decoded = []
    for part, encoding in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(encoding or 'utf-8', errors='ignore'))
        else:
            decoded.append(part)
    return " ".join(decoded)

def get_email_body(msg: Message) -> str:
    """Extrai corpo de texto plano do email."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode('utf-8', errors='ignore')
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode('utf-8', errors='ignore')
    return ""

def load_dedupe_set() -> set:
    """Carrega Message-IDs já processados."""
    if DEDUPE_PATH.exists():
        with open(DEDUPE_PATH, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_message_id(message_id: str):
    """Adiciona Message-ID ao arquivo de deduplicação."""
    with open(DEDUPE_PATH, 'a') as f:
        f.write(f"{message_id}\n")

def call_llm(prompt: str, max_tokens: int = 2000, temperature: float = 0.1, max_retries: int = 3) -> str:
    """Chama LLM via OpenRouter API com retry exponencial."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY não configurado no .env")
    
    import urllib.request
    import urllib.error
    
    data = json.dumps({
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode('utf-8')
    
    req = urllib.request.Request(
        f"{LLM_BASE_URL}/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/jornalistainclusivo",
            "X-Title": "JINC Gmail Triagem",
        },
        method="POST"
    )
    
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                result = json.loads(response.read().decode('utf-8'))
                if "choices" not in result or not result["choices"]:
                    raise RuntimeError(f"LLM response missing choices: {result}")
                return result["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='ignore')
            if e.code == 502 and attempt < max_retries - 1:
                # Upstream error - retry with backoff
                wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
                print(f"⚠️ LLM upstream error (502), retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                time.sleep(wait_time)
                continue
            raise RuntimeError(f"LLM API error {e.code}: {error_body}")
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2
                print(f"⚠️ LLM call failed: {e}, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                time.sleep(wait_time)
                continue
            raise RuntimeError(f"LLM call failed after {max_retries} attempts: {e}")

def parse_llm_json(response: str, fallback: dict) -> dict:
    """Parseia JSON do LLM com fallback robusto - extrai o primeiro objeto JSON válido."""
    import re
    import json
    
    # Limpar response: remover markdown code blocks
    cleaned = response.strip()
    if cleaned.startswith('```json'):
        cleaned = cleaned[7:]
    if cleaned.startswith('```'):
        cleaned = cleaned[3:]
    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    
    # Estratégia 1: Tentar achar JSON completo entre {} balanceados
    def extract_json_objects(text):
        """Extrai todos os objetos JSON válidos do texto."""
        results = []
        depth = 0
        start = -1
        in_string = False
        escape_next = False
        
        for i, char in enumerate(text):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif char == '}':
                    if depth > 0:
                        depth -= 1
                        if depth == 0 and start >= 0:
                            candidate = text[start:i+1]
                            try:
                                parsed = json.loads(candidate)
                                results.append(parsed)
                            except json.JSONDecodeError:
                                pass
                            start = -1
        return results
    
    # Extrair todos os objetos JSON válidos
    json_objects = extract_json_objects(cleaned)
    
    # Filtrar pelos que têm a estrutura esperada (categoria, confianca)
    for obj in json_objects:
        if isinstance(obj, dict) and 'categoria' in obj:
            return obj
    
    # Estratégia 2: Regex fallback para JSON simples
    json_match = re.search(r'\{[^{}]*"categoria"[^{}]*\}', cleaned, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Estratégia 3: Tentar parsear tudo
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    print(f"⚠️ LLM response not valid JSON, using fallback. Response: {cleaned[:300]}", file=sys.stderr)
    return fallback

def classify_and_extract_angles_llm(subject: str, from_addr: str, date: str, body: str) -> dict:
    """Classifica email E extrai ângulos em uma única chamada LLM."""
    prompt = CLASSIFICATION_PROMPT.format(
        subject=subject[:500],
        from_addr=from_addr[:200],
        date=date[:100],
        body=body[:3000]
    )
    
    fallback = {
        "categoria": "sugestao_de_pauta",
        "confianca": 0.5,
        "palavras_chave_relevantes": [],
        "resumo_uma_linha": body[:160].replace('\n', ' '),
        "motivo": "Fallback: LLM indisponível",
        "angulos": [
            f"Potencial para cobertura sobre direitos da pessoa com deficiência e acessibilidade"
        ]
    }
    
    try:
        response = call_llm(prompt, max_tokens=600, temperature=0.1)
        
        # DEBUG: Log the raw LLM response
        print(f"🔍 LLM Raw Response (subject: {subject[:50]}...): {response[:300]}", file=sys.stderr)
        
        result = parse_llm_json(response, fallback)
        
        # Garantir campos obrigatórios
        if "angulos" not in result:
            result["angulos"] = fallback["angulos"]
        if len(result["angulos"]) < 2:
            result["angulos"].append("Impacto nas políticas públicas de acessibilidade e inclusão")
        
        return result
    except Exception as e:
        print(f"⚠️ LLM classification+extraction failed: {e}", file=sys.stderr)
        return fallback
        print(f"⚠️ LLM classification+extraction failed: {e}", file=sys.stderr)
        fallback["motivo"] = f"Erro LLM: {e}"
        return fallback

def fetch_matching_emails(m: imaplib.IMAP4_SSL, since_date: str, max_emails: int = MAX_EMAILS_PER_RUN) -> list:
    """Busca emails desde a data - otimizado: fetch headers first, depois body apenas dos matches."""
    typ, data = m.search(None, 'CHARSET', 'UTF-8', 'SINCE', since_date)
    if typ != 'OK':
        return []
    
    msg_ids = data[0].split()
    if len(msg_ids) > max_emails:
        msg_ids = msg_ids[-max_emails:]
    
    print(f"📧 Verificando {len(msg_ids)} emails mais recentes (limite: {max_emails})...")
    
    emails = []
    
    for i, msg_id in enumerate(msg_ids):
        if i % 50 == 0 and i > 0:
            print(f"  Processados {i}/{len(msg_ids)}...")
        ...
        # Fetch headers first
        typ, msg_data = m.fetch(msg_id, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)])')
        if typ != 'OK':
            continue
        
        raw_headers = msg_data[0][1]
        msg = email.message_from_bytes(raw_headers)
        
        # Verificar keywords no subject
        subject = decode_mime_header(msg.get('Subject', '')).lower()
        has_keyword = any(kw.lower() in subject for kw in IMAP_KEYWORDS)
        
        if has_keyword:
            # Fetch body completo
            typ, full_data = m.fetch(msg_id, '(RFC822)')
            if typ == 'OK':
                raw_email = full_data[0][1]
                full_msg = email.message_from_bytes(raw_email)
                emails.append((msg_id.decode(), full_msg))
        else:
            # Verificar no From (remetentes que parecem newsletters/alertas)
            from_addr = decode_mime_header(msg.get('From', '')).lower()
            # Sender keywords expandidas
            sender_keywords = ['acessibilidade', 'inclusao', 'deficiencia', 'pcd', 'autismo', 
                              'googlealerts', 'newsletter', 'reuters', 'inclusive', 'disability',
                              'promenade', 'revista', 'deficas', 'sesc', 'flip', 'museu',
                              'adaptado', 'barreira', 'esporte', 'time', 'atleta',
                              'googlegroups', 'compilacao', 'dmarc', 'report']
            if any(kw in from_addr for kw in sender_keywords):
                typ, full_data = m.fetch(msg_id, '(RFC822)')
                if typ == 'OK':
                    raw_email = full_data[0][1]
                    full_msg = email.message_from_bytes(raw_email)
                    body = get_email_body(full_msg).lower()
                    if any(kw.lower() in body for kw in IMAP_KEYWORDS):
                        emails.append((msg_id.decode(), full_msg))
    
    return emails

def format_date_header(date_str: str) -> str:
    """Formata data do email para exibição."""
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return date_str

def content_hash(item: dict) -> str:
    """Gera hash único baseado em assunto + primeiras 200 chars do resumo."""
    content = f"{item['assunto']}|{item.get('resumo', '')[:200]}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]

def load_all_processed_items() -> list:
    """Carrega todos os itens já processados e salva em cache local para relatório cumulativo."""
    CACHE_PATH = OUTPUT_DIR / "processed_items_cache.json"
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, 'r') as f:
                return json.load(f)
        except:
            pass
    return []

def save_processed_items_cache(items: list):
    """Salva cache dos itens processados para relatório cumulativo."""
    CACHE_PATH = OUTPUT_DIR / "processed_items_cache.json"
    # Manter apenas itens dos últimos 30 dias
    cutoff = datetime.now() - timedelta(days=30)
    filtered = []
    for item in items:
        try:
            item_date = datetime.strptime(item.get('data', ''), "%d/%m/%Y %H:%M")
            if item_date >= cutoff:
                filtered.append(item)
        except:
            filtered.append(item)  # Manter se não der pra parsear
    with open(CACHE_PATH, 'w') as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

def generate_cumulative_markdown(all_items: list, new_items: list, date_str: str, time_str: str) -> str:
    """Gera relatório cumulativo dos últimos 15 dias + destaque dos novos."""
    releases = [item for item in all_items if item['tipo'] == 'release']
    sugestoes = [item for item in all_items if item['tipo'] == 'sugestao_de_pauta']
    
    new_releases = [item for item in new_items if item['tipo'] == 'release']
    new_sugestoes = [item for item in new_items if item['tipo'] == 'sugestao_de_pauta']
    
    md = f"# Triagem JINC — {date_str} {time_str} (Cumulativo 15 dias)\n\n"
    md += f"**Total nos últimos 15 dias:** {len(all_items)} itens ({len(releases)} releases, {len(sugestoes)} sugestões)\n"
    md += f"**Novos nesta execução:** {len(new_items)} ({len(new_releases)} releases, {len(new_sugestoes)} sugestões)\n\n"
    
    # Seção: Novos desta execução
    if new_items:
        md += "## 🆕 Novos desta execução\n\n"
        
        if new_releases:
            md += "### 📢 Releases novos\n\n"
            for i, item in enumerate(new_releases, 1):
                md += f"#### {i}. {item['assunto']}\n\n"
                md += f"- **Fonte:** {item['fonte']}\n"
                md += f"- **Data:** {item['data']}\n"
                md += f"- **Link/ID:** {item['message_id']}\n"
                md += f"- **Resumo:** {item['resumo']}\n"
                md += f"- **Confiança:** {item.get('confianca', 0):.0%}\n"
                md += f"- **Palavras-chave:** {', '.join(item['palavras_chave']) if item['palavras_chave'] else '—'}\n"
                if item.get('angulo'):
                    md += "- **Ângulos inclusivos:**\n"
                    for angle in item['angulo']:
                        md += f"  - {angle}\n"
                md += "\n"
        
        if new_sugestoes:
            md += "### 💡 Sugestões de pauta novas\n\n"
            for i, item in enumerate(new_sugestoes, 1):
                md += f"#### {i}. {item['assunto']}\n\n"
                md += f"- **Fonte:** {item['fonte']}\n"
                md += f"- **Data:** {item['data']}\n"
                md += f"- **Link/ID:** {item['message_id']}\n"
                md += f"- **Resumo:** {item['resumo']}\n"
                md += f"- **Confiança:** {item.get('confianca', 0):.0%}\n"
                md += f"- **Palavras-chave:** {', '.join(item['palavras_chave']) if item['palavras_chave'] else '—'}\n"
                if item.get('angulo'):
                    md += "- **Ângulos inclusivos:**\n"
                    for angle in item['angulo']:
                        md += f"  - {angle}\n"
                md += "\n"
    
    # Seção: Todos os itens dos últimos 15 dias
    md += "## 📋 Todos os itens relevantes (últimos 15 dias)\n\n"
    
    if releases:
        md += "### 📢 Releases\n\n"
        for i, item in enumerate(releases, 1):
            is_new = item in new_releases
            prefix = "🆕 " if is_new else ""
            md += f"#### {i}. {prefix}{item['assunto']}\n\n"
            md += f"- **Fonte:** {item['fonte']}\n"
            md += f"- **Data:** {item['data']}\n"
            md += f"- **Link/ID:** {item['message_id']}\n"
            md += f"- **Resumo:** {item['resumo']}\n"
            md += f"- **Confiança:** {item.get('confianca', 0):.0%}\n"
            md += f"- **Palavras-chave:** {', '.join(item['palavras_chave']) if item['palavras_chave'] else '—'}\n"
            if item.get('angulo'):
                md += "- **Ângulos inclusivos:**\n"
                for angle in item['angulo']:
                    md += f"  - {angle}\n"
            md += "\n"
    
    if sugestoes:
        md += "### 💡 Sugestões de Pautas\n\n"
        for i, item in enumerate(sugestoes, 1):
            is_new = item in new_sugestoes
            prefix = "🆕 " if is_new else ""
            md += f"#### {i}. {prefix}{item['assunto']}\n\n"
            md += f"- **Fonte:** {item['fonte']}\n"
            md += f"- **Data:** {item['data']}\n"
            md += f"- **Link/ID:** {item['message_id']}\n"
            md += f"- **Resumo:** {item['resumo']}\n"
            md += f"- **Confiança:** {item.get('confianca', 0):.0%}\n"
            md += f"- **Palavras-chave:** {', '.join(item['palavras_chave']) if item['palavras_chave'] else '—'}\n"
            if item.get('angulo'):
                md += "- **Ângulos inclusivos:**\n"
                for angle in item['angulo']:
                    md += f"  - {angle}\n"
            md += "\n"
    
    if not all_items:
        md += "Nenhum item relevante encontrado nos últimos 15 dias com as palavras-chave monitoradas.\n"
    
    return md

def send_telegram_notification(items: list, date_str: str) -> str:
    """Prepara mensagem para Telegram (será filtrada por smart_notify_filter)."""
    releases = [item for item in items if item['tipo'] == 'release']
    sugestoes = [item for item in items if item['tipo'] == 'sugestao_de_pauta']
    
    if not items:
        return f"📭 **Triagem JINC — {date_str}**\n\nNenhum email relevante nos últimos 15 dias."
    
    msg = f"📬 **Triagem JINC — {date_str}**\n\n"
    msg += f"📊 **Resumo:** {len(items)} itens ({len(releases)} releases, {len(sugestoes)} sugestões)\n\n"
    
    if releases:
        msg += "📢 **Releases:**\n"
        for item in releases[:3]:
            conf = item.get('confianca', 0)
            msg += f"• {item['assunto'][:80]} ({item['fonte'][:40]}) [{conf:.0%}]\n"
        if len(releases) > 3:
            msg += f"  ...e mais {len(releases) - 3}\n"
        msg += "\n"
    
    if sugestoes:
        msg += "💡 **Sugestões de pauta:**\n"
        for item in sugestoes[:3]:
            conf = item.get('confianca', 0)
            msg += f"• {item['assunto'][:80]} ({item['fonte'][:40]}) [{conf:.0%}]\n"
        if len(sugestoes) > 3:
            msg += f"  ...e mais {len(sugestoes) - 3}\n"
        msg += "\n"
    
    date_file = date_str.replace('/', '-')
    time_file = datetime.now().strftime("%H-%M")
    msg += f"📄 Relatório completo: `/opt/data/journali/triagem-{date_file}-{time_file}.md`"
    return msg

def main():
    print("🔍 JINC Gmail Triagem (LLM-Enhanced) - Iniciando...")
    
    # Carregar config
    if not CONFIG_PATH.exists():
        print("❌ Config não encontrado: /opt/data/journali/imap-config.json")
        sys.exit(1)
    
    with open(CONFIG_PATH, 'r') as f:
        cfg = json.load(f)
    
    # Validar placeholders
    if "SEU_EMAIL" in cfg.get("username", "") or "SENHA_OU_APP_PASSWORD" in cfg.get("password", ""):
        print("❌ Config contém placeholders — edite com credenciais reais")
        sys.exit(1)
    
    # Verificar LLM key
    if not OPENROUTER_API_KEY:
        print("⚠️ OPENROUTER_API_KEY não configurado — usando fallback heurístico")
    
    # Carregar deduplicação
    processed_ids = load_dedupe_set()
    print(f"📋 {len(processed_ids)} Message-IDs já processados")
    
    # Conectar IMAP
    try:
        m = imaplib.IMAP4_SSL(cfg['host'], cfg['port'])
        m.login(cfg['username'], cfg['password'].replace(' ', ''))
        m.select(cfg.get('search_folder', 'INBOX'))
        print(f"✅ Conectado a {cfg['username']} @ {cfg['host']}:{cfg['port']}")
    except Exception as e:
        print(f"❌ Erro IMAP: {e}")
        sys.exit(1)
    
    # Buscar últimos 15 dias
    since_date = (datetime.now() - timedelta(days=15)).strftime('%d-%b-%Y')
    print(f"🔎 Buscando emails desde {since_date}...")
    
    emails = fetch_matching_emails(m, since_date)
    print(f"📧 {len(emails)} emails candidatos encontrados")
    
    m.logout()
    
    # Carregar cache cumulativo existente
    all_items = load_all_processed_items()
    existing_ids = {item['message_id'] for item in all_items}
    existing_hashes = {content_hash(item) for item in all_items}
    
    # Processar TODOS os candidatos com LLM (não só novos)
    # Mas limitar para evitar timeout
    emails_to_process = emails[:MAX_EMAILS_PER_RUN]
    if len(emails) > MAX_EMAILS_PER_RUN:
        print(f"⚠️ Limitando processamento LLM a {MAX_EMAILS_PER_RUN} emails de {len(emails)} candidatos")
    
    print(f"🔍 Classificando {len(emails_to_process)} emails candidatos com LLM...")
    
    start_time = time.time()
    
    new_items = []
    new_count = 0
    irrelevant_count = 0
    
    for msg_id, msg in emails_to_process:
        # Verificar timeout
        if time.time() - start_time > MAX_PROCESSING_TIME:
            print(f"⏰ Timeout de {MAX_PROCESSING_TIME}s atingido, parando processamento LLM")
            break
        
        # Extrair Message-ID
        message_id = msg.get('Message-ID', '').strip()
        if not message_id:
            message_id = msg_id
        
        # Extrair campos
        subject = decode_mime_header(msg.get('Subject', ''))
        from_addr = decode_mime_header(msg.get('From', ''))
        date_header = msg.get('Date', '')
        body = get_email_body(msg)
        
        # Classificar COM LLM + extrair ângulos
        classification = classify_and_extract_angles_llm(subject, from_addr, date_header, body)
        
        categoria = classification.get("categoria", "sugestao_de_pauta")
        confianca = classification.get("confianca", 0.5)
        keywords_found = classification.get("palavras_chave_relevantes", [])
        resumo_llm = classification.get("resumo_uma_linha", "")
        angulos = classification.get("angulos", [])
        
        # Pular irrelevantes (mas salvar no dedupe)
        if categoria == "irrelevante":
            irrelevant_count += 1
            if message_id not in processed_ids:
                save_message_id(message_id)
                processed_ids.add(message_id)
            continue
        
        # Usar resumo do LLM se disponível
        resumo = resumo_llm if resumo_llm else (body[:300].replace('\n', ' ').strip() + "..." if len(body) > 300 else body.replace('\n', ' ').strip())
        
        item = {
            'tipo': categoria,
            'fonte': from_addr,
            'assunto': subject,
            'data': format_date_header(date_header),
            'message_id': message_id,
            'resumo': resumo,
            'palavras_chave': keywords_found,
            'angulo': angulos,
            'confianca': confianca,
        }
        
        # Adicionar ao cache cumulativo se não existe (por message_id E por conteúdo)
        item_hash = content_hash(item)
        if message_id not in existing_ids and item_hash not in existing_hashes:
            all_items.append(item)
            existing_ids.add(message_id)
            existing_hashes.add(item_hash)
        
        # Se é novo (não estava no dedupe), contar como novo
        if message_id not in processed_ids:
            new_items.append(item)
            save_message_id(message_id)
            processed_ids.add(message_id)
            new_count += 1
    
    print(f"✨ {new_count} itens novos relevantes")
    print(f"🗑️ {irrelevant_count} irrelevantes descartados")
    print(f"📊 Total no cache cumulativo: {len(all_items)}")
    
    # Gerar output
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    time_str = now.strftime("%H:%M")
    date_file = now.strftime("%Y-%m-%d")
    time_file = now.strftime("%H-%M")
    
    # Filtrar apenas últimos 15 dias para o relatório
    cutoff_date = datetime.now() - timedelta(days=15)
    recent_items = []
    for item in all_items:
        try:
            item_date = datetime.strptime(item['data'], "%d/%m/%Y %H:%M")
            if item_date >= cutoff_date:
                recent_items.append(item)
        except:
            recent_items.append(item)  # Manter se não der pra parsear
    
    print(f"📅 Itens nos últimos 15 dias: {len(recent_items)}")
    
    # Salvar cache atualizado
    save_processed_items_cache(all_items)
    
    # Markdown cumulativo (últimos 15 dias + destaque dos novos)
    md_content = generate_cumulative_markdown(recent_items, new_items, date_str, time_str)
    md_path = OUTPUT_DIR / f"triagem-{date_file}-{time_file}.md"
    md_path.write_text(md_content, encoding='utf-8')
    print(f"📄 Markdown cumulativo salvo: {md_path}")
    
    # Preparar notificação Telegram (apenas novos)
    telegram_msg = send_telegram_notification(new_items, date_str)
    print(telegram_msg)
    
    # Output para smart_notify_filter (JSON no stdout) - reportar cumulativo
    output = {
        "job_name": "JINC Gmail Triagem",
        "timestamp": datetime.now().isoformat(),
        "telegram_message": telegram_msg,
        "items_count": len(recent_items),  # Total nos últimos 15 dias
        "releases_count": len([i for i in recent_items if i['tipo'] == 'release']),
        "sugestoes_count": len([i for i in recent_items if i['tipo'] == 'sugestao_de_pauta']),
        "irrelevant_discarded": irrelevant_count,
        "markdown_path": str(md_path),
        "new_items": new_count,
        "llm_enhanced": bool(OPENROUTER_API_KEY),
    }
    print(json.dumps(output, ensure_ascii=False))
    
    sys.exit(0)

if __name__ == "__main__":
    main()
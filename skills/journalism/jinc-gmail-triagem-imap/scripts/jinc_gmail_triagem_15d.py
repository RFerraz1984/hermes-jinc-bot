#!/usr/bin/env python3
"""
JINC Gmail Triagem - 15 dias
Pipeline IMAP para triagem de emails sobre inclusão/acessibilidade/deficiência.
Gera relatório diário em Markdown e notifica via Telegram (smart_notify_filter).
"""

import imaplib
import email
from email.message import Message
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from email.header import decode_header
from email.utils import parsedate_to_datetime

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

# Config paths
CONFIG_PATH = Path("/opt/data/journali/imap-config.json")
DEDUPE_PATH = Path("/opt/data/journali/processed-message-ids.jsonl")
OUTPUT_DIR = Path("/opt/data/journali")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Palavras-chave (case-insensitive, sem acentos para busca IMAP)
KEYWORDS = [
    "acessibilidade",
    "deficiencia",
    "inclusao",
    "autismo",
    "neurodiversidade",
    "pcd",
    "tea",
    "wcag",
    "e-mag",
    "capacitismo",
    "pessoa com deficiencia",
]

# Palavras-chave para classificação (com acentos, para display)
KEYWORDS_DISPLAY = [
    "acessibilidade",
    "deficiência",
    "inclusão",
    "autismo",
    "neurodiversidade",
    "PCD",
    "TEA",
    "WCAG",
    "e-MAG",
    "capacitismo",
    "pessoa com deficiência",
]

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

def classify_email(subject: str, body: str) -> tuple:
    """
    Classifica email como 'release' ou 'sugestao_de_pauta'.
    Retorna (tipo, palavras_chave_encontradas).
    """
    text = f"{subject} {body}".lower()
    found_keywords = [kw for kw in KEYWORDS_DISPLAY if kw.lower() in text]
    
    # Heurística simples para release
    release_indicators = [
        "release", "press release", "comunicado", "para divulgação",
        "para imprensa", "nota à imprensa", "divulgação imediata",
        "anuncia", "lança", "apresenta", "divulga"
    ]
    
    is_release = any(ind in text for ind in release_indicators)
    
    tipo = "release" if is_release else "sugestao_de_pauta"
    return tipo, found_keywords

def extract_angle(subject: str, body: str, keywords_found: list) -> list:
    """Extrai ângulo inclusivo (2-4 bullets)."""
    text = f"{subject} {body}".lower()
    angles = []
    
    angle_map = {
        "acessibilidade": "Como a acessibilidade digital/física está sendo implementada ou negligenciada",
        "deficiência": "Impacto direto na vida de pessoas com deficiência — direitos, barreiras, conquistas",
        "inclusão": "Práticas inclusivas em educação, trabalho, tecnologia ou políticas públicas",
        "autismo": "Neurodiversidade no foco: diagnóstico, apoio, inclusão escolar/profissional",
        "neurodiversidade": "Ambientes neuroinclusivos — escolas, empresas, espaços públicos",
        "pcd": "Empregabilidade, acessibilidade, direitos da pessoa com deficiência no mercado",
        "tea": "Transtorno do Espectro Autista — políticas, terapias, inclusão social",
        "wcag": "Conformidade WCAG 2.1/2.2 — auditoria, correção, boas práticas",
        "e-mag": "Modelo de Acessibilidade em Governo Eletrônico (e-MAG) — conformidade gov.br",
        "capacitismo": "Capacitismo algorítmico/estrutural — como sistemas excluem pessoas com deficiência",
        "pessoa com deficiência": "Voz e protagonismo de pessoas com deficiência na narrativa",
    }
    
    for kw in keywords_found:
        kw_lower = kw.lower()
        if kw_lower in angle_map and angle_map[kw_lower] not in angles:
            angles.append(angle_map[kw_lower])
    
    # Garantir 2-4 bullets
    if len(angles) < 2:
        angles.append("Potencial para cobertura sobre direitos da pessoa com deficiência e acessibilidade")
    if len(angles) > 4:
        angles = angles[:4]
    
    return angles

def build_imap_search_criteria(since_date: str) -> list:
    """Constrói critérios de busca IMAP."""
    criteria = ['CHARSET', 'UTF-8', 'SINCE', since_date]
    return criteria

def fetch_matching_emails(m: imaplib.IMAP4_SSL, since_date: str, max_emails: int = 100) -> list:
    """Busca emails desde a data - otimizado: fetch headers first, depois body apenas dos matches."""
    typ, data = m.search(None, 'CHARSET', 'UTF-8', 'SINCE', since_date)
    if typ != 'OK':
        return []
    
    msg_ids = data[0].split()
    if len(msg_ids) > max_emails:
        msg_ids = msg_ids[-max_emails:]
    
    print(f"📧 Verificando {len(msg_ids)} emails mais recentes...")
    
    emails = []
    
    for i, msg_id in enumerate(msg_ids):
        if i % 50 == 0 and i > 0:
            print(f"  Processados {i}/{len(msg_ids)}...")
        
        # Fetch headers first
        typ, msg_data = m.fetch(msg_id, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)])')
        if typ != 'OK':
            continue
        
        raw_headers = msg_data[0][1]
        msg = email.message_from_bytes(raw_headers)
        
        # Verificar keywords no subject
        subject = decode_mime_header(msg.get('Subject', '')).lower()
        has_keyword = any(kw.lower() in subject for kw in KEYWORDS)
        
        if has_keyword:
            # Fetch body completo
            typ, full_data = m.fetch(msg_id, '(RFC822)')
            if typ == 'OK':
                raw_email = full_data[0][1]
                full_msg = email.message_from_bytes(raw_email)
                emails.append((msg_id.decode(), full_msg))
        else:
            # Verificar no From (remetentes conhecidos)
            from_addr = decode_mime_header(msg.get('From', '')).lower()
            sender_keywords = ['acessibilidade', 'inclusao', 'deficiencia', 'pcd', 'autismo', 'googlealerts', 'newsletter']
            if any(kw in from_addr for kw in sender_keywords):
                typ, full_data = m.fetch(msg_id, '(RFC822)')
                if typ == 'OK':
                    raw_email = full_data[0][1]
                    full_msg = email.message_from_bytes(raw_email)
                    body = get_email_body(full_msg).lower()
                    if any(kw.lower() in body for kw in KEYWORDS):
                        emails.append((msg_id.decode(), full_msg))
    
    return emails

def format_date_header(date_str: str) -> str:
    """Formata data do email para exibição."""
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return date_str

def generate_daily_markdown(items: list, date_str: str) -> str:
    """Gera arquivo Markdown diário com seções Releases e Sugestões de Pautas."""
    releases = [item for item in items if item['tipo'] == 'release']
    sugestoes = [item for item in items if item['tipo'] == 'sugestao_de_pauta']
    
    md = f"# Triagem JINC — {date_str}\n\n"
    md += f"Total de itens: {len(items)} | Releases: {len(releases)} | Sugestões de pauta: {len(sugestoes)}\n\n"
    
    if releases:
        md += "## 📢 Releases\n\n"
        for i, item in enumerate(releases, 1):
            md += f"### {i}. {item['assunto']}\n\n"
            md += f"- **Fonte:** {item['fonte']}\n"
            md += f"- **Data:** {item['data']}\n"
            md += f"- **Link/ID:** {item['message_id']}\n"
            md += f"- **Resumo:** {item['resumo']}\n"
            md += f"- **Palavras-chave:** {', '.join(item['palavras_chave'])}\n"
            md += f"- **Ângulo inclusivo:**\n"
            for angle in item['angulo']:
                md += f"  - {angle}\n"
            md += "\n"
    
    if sugestoes:
        md += "## 💡 Sugestões de Pautas\n\n"
        for i, item in enumerate(sugestoes, 1):
            md += f"### {i}. {item['assunto']}\n\n"
            md += f"- **Fonte:** {item['fonte']}\n"
            md += f"- **Data:** {item['data']}\n"
            md += f"- **Link/ID:** {item['message_id']}\n"
            md += f"- **Resumo:** {item['resumo']}\n"
            md += f"- **Palavras-chave:** {', '.join(item['palavras_chave'])}\n"
            md += f"- **Ângulo inclusivo:**\n"
            for angle in item['angulo']:
                md += f"  - {angle}\n"
            md += "\n"
    
    if not items:
        md += "Nenhum item encontrado nos últimos 15 dias com as palavras-chave monitoradas.\n"
    
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
            msg += f"• {item['assunto'][:80]} ({item['fonte'][:40]})\n"
        if len(releases) > 3:
            msg += f"  ...e mais {len(releases) - 3}\n"
        msg += "\n"
    
    if sugestoes:
        msg += "💡 **Sugestões de pauta:**\n"
        for item in sugestoes[:3]:
            msg += f"• {item['assunto'][:80]} ({item['fonte'][:40]})\n"
        if len(sugestoes) > 3:
            msg += f"  ...e mais {len(sugestoes) - 3}\n"
        msg += "\n"
    
    msg += f"📄 Relatório completo: `/opt/data/journali/triagem-{date_str.replace('/', '-')}.md`"
    return msg

def main():
    print("🔍 JINC Gmail Triagem - Iniciando...")
    
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
    print(f"📧 {len(emails)} emails encontrados (bruto)")
    
    m.logout()
    
    # Processar e deduplicar
    items = []
    new_count = 0
    
    for msg_id, msg in emails:
        message_id = msg.get('Message-ID', '').strip()
        if not message_id:
            message_id = msg_id
        
        if message_id in processed_ids:
            continue
        
        subject = decode_mime_header(msg.get('Subject', ''))
        from_addr = decode_mime_header(msg.get('From', ''))
        date_header = msg.get('Date', '')
        body = get_email_body(msg)
        
        tipo, keywords_found = classify_email(subject, body)
        angle = extract_angle(subject, body, keywords_found)
        resumo = body[:300].replace('\n', ' ').strip() + "..." if len(body) > 300 else body.replace('\n', ' ').strip()
        
        item = {
            'tipo': tipo,
            'fonte': from_addr,
            'assunto': subject,
            'data': format_date_header(date_header),
            'message_id': message_id,
            'resumo': resumo,
            'palavras_chave': keywords_found,
            'angulo': angle,
        }
        
        items.append(item)
        save_message_id(message_id)
        processed_ids.add(message_id)
        new_count += 1
    
    print(f"✨ {new_count} itens novos (após deduplicação)")
    print(f"📊 Total processado nesta execução: {len(items)}")
    
    # Gerar output
    date_str = datetime.now().strftime("%d/%m/%Y")
    date_file = datetime.now().strftime("%Y-%m-%d")
    
    # Markdown diário
    md_content = generate_daily_markdown(items, date_str)
    md_path = OUTPUT_DIR / f"triagem-{date_file}.md"
    md_path.write_text(md_content, encoding='utf-8')
    print(f"📄 Markdown salvo: {md_path}")
    
    # Preparar notificação Telegram
    telegram_msg = send_telegram_notification(items, date_str)
    print(telegram_msg)
    
    # Output para smart_notify_filter (JSON no stdout)
    output = {
        "job_name": "JINC Gmail Triagem",
        "timestamp": datetime.now().isoformat(),
        "telegram_message": telegram_msg,
        "items_count": len(items),
        "releases_count": len([i for i in items if i['tipo'] == 'release']),
        "sugestoes_count": len([i for i in items if i['tipo'] == 'sugestao_de_pauta']),
        "markdown_path": str(md_path),
        "new_items": new_count,
    }
    print(json.dumps(output, ensure_ascii=False))
    
    sys.exit(0)

if __name__ == "__main__":
    main()
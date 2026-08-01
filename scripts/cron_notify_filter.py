#!/usr/bin/env python3
"""
Smart Notification Filter for Hermes Cron Jobs
Filters cron job output — only delivers to Telegram when:
- Explicit notification flag in output (NOTIFICATION: true)
- Error/failure detected
- Action required keywords found
- State changes detected

Usage: Set as cron job script with no_agent=True, deliver='telegram'
The script reads stdin (cron job output) and decides whether to notify.
"""
import sys
import re
import json
import os
from datetime import datetime
from pathlib import Path

STATE_DIR = Path("/opt/data/cron_notify_state")
STATE_DIR.mkdir(exist_ok=True)

# Palavras-chave que indicam necessidade de ação
ACTION_KEYWORDS = [
    # Erros e falhas
    r"\b(error|erro|fail|falha|failed|exception|traceback|crash)\b",
    r"\b(timeout|expirou|expired|denied|unauthorized|forbidden)\b",
    r"\b(critical|critico|fatal|panico)\b",
    # Alertas de limite
    r"\b(limite|limit|quota|cota|rate.?limit|throttl)\b",
    r"\b(quase|almost|low|baixo|critico|warning|aviso)\b",
    # Mudanças de estado
    r"\b(changed|alterado|modified|modificado|new|novo|deleted|removido)\b",
    r"\b(started|iniciado|stopped|parado|restarted|reiniciado)\b",
    # Ação necessária
    r"\b(action.?required|acao.?necessaria|precisa|must|deve|urgent|urgente)\b",
    r"\b(intervention|intervencao|manual|hand.?off)\b",
    # Segurança
    r"\b(security|seguranca|breach|vazamento|leak|compromised|comprometido)\b",
    r"\b(unauthorized|nao.?autorizado|suspicious|suspeito)\b",
    # Backup/Disco
    r"\b(disk.?full|disco.?cheio|space|espaco|backup.?fail|falhou)\b",
]

# Padrões que indicam "tudo OK" — suprimir notificação se só isso
OK_PATTERNS = [
    r"^\s*$",  # vazio
    r"^(ok|success|sucesso|completed|concluido|finished|finalizado)[\.!]?$",
    r"^(no changes|sem mudancas|nothing to do|nada a fazer)[\.!]?$",
    r"^\[.*\][\s\S]*?(ok|success|completed|healthy|saudavel)[\.!]?$",
    r"^💓.*heartbeat.*ok",  # heartbeat normal
    r"^✅.*(monitor|check|verify).*complete",
]

# Estado persistente para detectar mudanças
def load_state(key):
    f = STATE_DIR / f"{key}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except:
            pass
    return {}

def save_state(key, value):
    f = STATE_DIR / f"{key}.json"
    f.write_text(json.dumps(value, ensure_ascii=False, indent=2))

def hash_content(content):
    import hashlib
    return hashlib.sha256(content.encode()).hexdigest()[:16]

def should_notify(output, job_name):
    """Decide se deve notificar baseado no output."""
    if not output or not output.strip():
        return False, "empty output"

    lines = output.strip().split('\n')
    full_text = output.lower()

    # 1. Flag explícita de notificação
    if "notification: true" in full_text or "notificar: true" in full_text:
        return True, "explicit notification flag"

    # 2. Verifica padrões de "OK" — se TODAS as linhas são OK, não notifica
    all_ok = True
    for line in lines:
        line_l = line.strip().lower()
        if not line_l:
            continue
        is_ok = any(re.search(p, line_l, re.IGNORECASE) for p in OK_PATTERNS)
        if not is_ok:
            all_ok = False
            break

    if all_ok:
        return False, "all lines match OK patterns"

    # 3. Verifica palavras-chave de ação
    for pattern in ACTION_KEYWORDS:
        if re.search(pattern, full_text, re.IGNORECASE):
            return True, f"action keyword matched: {pattern}"

    # 4. Detecta mudança de estado (comparação com última execução)
    content_hash = hash_content(output)
    last_hash = load_state(f"last_hash_{job_name}")
    if last_hash and last_hash != content_hash:
        save_state(f"last_hash_{job_name}", content_hash)
        return True, "output changed since last run"

    save_state(f"last_hash_{job_name}", content_hash)

    # 5. Códigos de saída não-zero (se presente no output)
    if re.search(r"(exit code|return code|codigo de saida)[:\s]*[1-9]", full_text):
        return True, "non-zero exit code detected"

    # 6. HTTP errors
    if re.search(r"http.*[45]\d\d", full_text):
        return True, "HTTP error code detected"

    return False, "no actionable content"


def main():
    # Lê todo stdin (output do cron job)
    output = sys.stdin.read()

    # Nome do job (pode vir via env var ou primeiro argumento)
    job_name = os.environ.get("CRON_JOB_NAME", "unknown")
    if len(sys.argv) > 1:
        job_name = sys.argv[1]

    should, reason = should_notify(output, job_name)

    if should:
        # Adiciona header com metadados
        ts = datetime.now().strftime("%d/%m/%Y %H:%M")
        header = f"🔔 **Alerta Cron: {job_name}** — {ts}\n📋 Motivo: {reason}\n---\n"
        print(header + output)
        sys.exit(0)  # stdout será entregue pelo Hermes
    else:
        # Silencioso — não imprime nada, Hermes não entrega
        sys.exit(0)


if __name__ == "__main__":
    main()
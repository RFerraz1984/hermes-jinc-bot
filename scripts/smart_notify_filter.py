#!/usr/bin/env python3
"""
Smart Notification Filter for Hermes Cron Jobs
Receives script output via stdin and metadata via command-line arguments.
Only outputs (notifies) when action is needed.

Usage: python3 smart_notify_filter.py --job-name "nome" --exit-code 0 < script_output.txt
"""
import sys
import re
import json
import argparse
import os
from datetime import datetime
from pathlib import Path

# Estado persistente para detectar mudanças
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

# Padrões de "tudo OK" — suprimir se SÓ isso
OK_PATTERNS = [
    r"^\s*$",  # vazio
    r"^(ok|success|sucesso|completed|concluido|finished|finalizado)[\.!]?$",
    r"^(no changes|sem mudancas|sem alteracoes)[\.!]?$",
    r"^(nothing to do|nada a fazer)[\.!]?$",
]

# Palavras que forçam notificação mesmo em contexto OK
FORCE_NOTIFY = [
    r"NOTIFICATION:\s*true",
    r"NOTIFICAR:\s*true",
]

def load_job_state(job_name):
    """Carrega estado anterior do job."""
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', job_name)
    state_file = STATE_DIR / f"{safe_name}.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except:
            pass
    return {}

def save_job_state(job_name, state):
    """Salva estado atual do job."""
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', job_name)
    state_file = STATE_DIR / f"{safe_name}.json"
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def check_action_needed(text, prev_state):
    """Verifica se a saída indica necessidade de notificação."""
    text_lower = text.lower()
    
    # 1. Força notificação explícita
    for pattern in FORCE_NOTIFY:
        if re.search(pattern, text, re.IGNORECASE):
            return True, "Notificação forçada (NOTIFICATION: true)"
    
    # 2. Palavras-chave de ação
    for pattern in ACTION_KEYWORDS:
        if re.search(pattern, text_lower):
            return True, f"Palavra-chave detectada: {pattern}"
    
    # 3. Mudança de estado detectada comparando com execução anterior
    current_hash = hash(text.strip())
    if prev_state.get("last_output_hash") is not None:
        if prev_state["last_output_hash"] != current_hash:
            # Verifica se não é só timestamp/logs normais
            if not only_timestamps_changed(prev_state.get("last_output", ""), text):
                return True, "Mudança de saída detectada"
    
    # 4. Se só tem padrões OK, NÃO notificar
    if text.strip():
        only_ok = True
        for line in text.strip().split('\n'):
            line = line.strip()
            if line and not any(re.match(p, line, re.IGNORECASE) for p in OK_PATTERNS):
                only_ok = False
                break
        if only_ok:
            return False, "Apenas mensagens OK"
    
    return False, "Sem indicadores de ação"

def only_timestamps_changed(old, new):
    """Verifica se a diferença é só timestamps/logs rotineiros."""
    # Remove timestamps ISO, horários, linhas de debug repetitivas
    def normalize(t):
        t = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\.\d]*Z?', '', t)
        t = re.sub(r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}', '', t)
        t = re.sub(r'\d{2}:\d{2}:\d{2}', '', t)
        t = re.sub(r'\[.*?\]', '', t)  # [DEBUG], [INFO], etc
        t = re.sub(r'\s+', ' ', t)
        return t.strip()
    
    return normalize(old) == normalize(new)

def main():
    parser = argparse.ArgumentParser(description="Smart notification filter for cron jobs")
    parser.add_argument("--job-name", required=True, help="Nome do job")
    parser.add_argument("--exit-code", type=int, default=0, help="Código de saída do comando")
    parser.add_argument("--state-dir", default=str(STATE_DIR), help="Diretório de estado")
    args = parser.parse_args()
    
    # Lê saída do script via stdin
    script_output = sys.stdin.read()
    
    job_name = args.job_name
    exit_code = args.exit_code
    
    # Carrega estado anterior
    prev_state = load_job_state(job_name)
    
    # Exit code não-zero = sempre notificar
    if exit_code != 0:
        notify = True
        reason = f"Exit code {exit_code} (erro)"
    else:
        notify, reason = check_action_needed(script_output, prev_state)
    
    # Atualiza estado
    new_state = {
        "last_output_hash": hash(script_output.strip()),
        "last_output": script_output,
        "last_exit_code": exit_code,
        "last_notified": notify,
        "last_reason": reason,
        "last_run": datetime.utcnow().isoformat() + "Z"
    }
    save_job_state(job_name, new_state)
    
    # Decide: notifica ou silencia
    if notify:
        # Output será capturado pelo cron e entregue no Telegram
        print(script_output.rstrip())
        # Log interno (stderr não vai pro Telegram)
        print(f"[FILTER] Notificando: {reason} | Job: {job_name}", file=sys.stderr)
    else:
        # Silencioso - nada no stdout
        print(f"[FILTER] Silenciado: {reason} | Job: {job_name}", file=sys.stderr)

if __name__ == "__main__":
    main()
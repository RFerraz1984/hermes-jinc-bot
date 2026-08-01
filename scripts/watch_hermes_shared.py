#!/usr/bin/env python3
"""
Watchdog para monitorar novos arquivos em /opt/data/hermes-shared
e disparar reindexação incremental + notificar no Telegram.
"""
import os
import sys
import time
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

SHARED_DIR = Path("/opt/data/hermes-shared")
STATE_FILE = SHARED_DIR / ".watchdog_state.json"
INDEX_SCRIPT = Path("/opt/data/scripts/index_hermes_shared.py")

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {"known_files": {}, "last_notified": {}}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def scan_files():
    """Retorna dict {rel_path: hash} para arquivos suportados."""
    exts = {".pdf", ".txt", ".md", ".docx", ".csv", ".json", ".jsonl"}
    files = {}
    for path in SHARED_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in exts:
            # Ignora arquivos do próprio índice
            if ".rag-index" in path.parts:
                continue
            if path.name.startswith("."):
                continue
            rel = path.relative_to(SHARED_DIR)
            try:
                files[str(rel)] = file_hash(path)
            except:
                pass
    return files

def run_index():
    """Executa script de indexação incremental."""
    try:
        result = subprocess.run(
            ["uv", "run", "python", str(INDEX_SCRIPT)],
            capture_output=True, text=True, timeout=300, cwd="/opt/data"
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout (300s)"
    except Exception as e:
        return False, "", str(e)

def send_telegram(message):
    """Envia notificação via Hermes CLI (stdout entregue pelo cron)."""
    print(message)
    return True

def main():
    state = load_state()
    known = state.get("known_files", {})

    # Scan atual
    current = scan_files()

    # Detecta novos/alterados
    new_files = []
    changed_files = []
    for rel, h in current.items():
        if rel not in known:
            new_files.append(rel)
        elif known[rel] != h:
            changed_files.append(rel)

    # Remove arquivos deletados (apenas log)
    deleted = set(known.keys()) - set(current.keys())

    # Sem mudanças? Sai silenciosamente (watchdog pattern)
    if not new_files and not changed_files and not deleted:
        return 0

    # Monta relatório em linguagem natural
    ts = datetime.now().strftime('%d/%m/%Y %H:%M')
    lines = [f"📂 **Watchdog Hermes-Shared** — {ts}"]

    if new_files:
        lines.append(f"\n🆕 **{len(new_files)} arquivo(s) novo(s) detectado(s):**")
        for f in new_files:
            lines.append(f"  • `{f}`")

    if changed_files:
        lines.append(f"\n🔄 **{len(changed_files)} arquivo(s) alterado(s):**")
        for f in changed_files:
            lines.append(f"  • `{f}`")

    if deleted:
        lines.append(f"\n🗑️ **{len(deleted)} arquivo(s) removido(s):**")
        for f in deleted:
            lines.append(f"  • `{f}`")

    message = "\n".join(lines)
    send_telegram(message)

    # Dispara reindexação
    send_telegram("🔧 Iniciando reindexação incremental do mini-RAG...")
    ok, stdout, stderr = run_index()
    if ok:
        send_telegram("✅ **Reindexação concluída com sucesso** — mini-RAG atualizado")
    else:
        err = stderr[:500] if stderr else "erro desconhecido"
        send_telegram(f"⚠️ **Falha na reindexação**: {err}")

    # Atualiza estado
    state["known_files"] = current
    state["last_notified"] = {f: datetime.now().isoformat() for f in new_files + changed_files}
    save_state(state)

    return 0

if __name__ == "__main__":
    sys.exit(main())
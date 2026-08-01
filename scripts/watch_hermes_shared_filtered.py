#!/usr/bin/env python3
"""Wrapper para Watchdog Hermes Shared com filtro inteligente"""
import subprocess
import sys
import json
from datetime import datetime

SCRIPT = "/opt/data/scripts/watch_hermes_shared.py"
FILTER = "/opt/data/scripts/smart_notify_filter.py"
JOB_NAME = "Watchdog Hermes Shared"

def main():
    # Executa o script real
    result = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)
    output = result.stdout + result.stderr
    exit_code = result.returncode
    
    # Prepara metadata
    metadata = {
        "job_name": JOB_NAME,
        "script": SCRIPT,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "exit_code": exit_code,
        "state_dir": "/opt/data/cron_notify_state"
    }
    
    # Passa para o filtro
    filter_proc = subprocess.run(
        [sys.executable, FILTER, json.dumps(metadata)],
        input=output,
        capture_output=True,
        text=True
    )
    
    # Se filtro retornou algo, imprime (será entregue no Telegram)
    if filter_proc.stdout:
        print(filter_proc.stdout)
    
    # Sempre exit 0 para não quebrar o cron
    sys.exit(0)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Wrapper para Moltbook Monitor com filtro inteligente"""
import subprocess
import sys
import json
from datetime import datetime

SCRIPT = "/opt/data/scripts/moltbook_monitor.py"
FILTER = "/opt/data/scripts/smart_notify_filter.py"
JOB_NAME = "Moltbook Monitor"

def main():
    result = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)
    output = result.stdout + result.stderr
    exit_code = result.returncode
    
    metadata = {
        "job_name": JOB_NAME,
        "script": SCRIPT,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "exit_code": exit_code,
        "state_dir": "/opt/data/cron_notify_state"
    }
    
    filter_proc = subprocess.run(
        [sys.executable, FILTER, json.dumps(metadata)],
        input=output,
        capture_output=True,
        text=True
    )
    
    if filter_proc.stdout:
        print(filter_proc.stdout)
    sys.exit(0)

if __name__ == "__main__":
    main()
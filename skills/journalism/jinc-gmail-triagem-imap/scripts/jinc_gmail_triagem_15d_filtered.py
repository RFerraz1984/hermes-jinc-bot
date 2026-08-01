#!/usr/bin/env python3
"""
Wrapper filtrado para JINC Gmail Triagem 15d.
Executa o script principal e passa output para smart_notify_filter.py.
"""

import subprocess
import sys
import os

# Carregar .env
def load_env_file(path: str):
    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env_file("/opt/data/.env")

def main():
    # Executar script principal
    result = subprocess.run(
        [sys.executable, "/opt/data/scripts/jinc_gmail_triagem_15d.py"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    
    # Passar stdout para smart_notify_filter
    filter_result = subprocess.run(
        [sys.executable, "/opt/data/scripts/smart_notify_filter.py", 
         "--job-name", "JINC Gmail Triagem", 
         "--exit-code", str(result.returncode)],
        input=result.stdout,
        capture_output=True,
        text=True,
        timeout=30,
    )
    
    # Output do filtro (já formatado para Telegram)
    if filter_result.stdout.strip():
        print(filter_result.stdout.strip())
    
    # Retornar exit code do script principal
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
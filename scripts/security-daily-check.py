#!/usr/bin/env python3
import subprocess
import os
import sys
from datetime import datetime

LOG = f"/opt/data/logs/security-check-{datetime.now().strftime('%Y-%m-%d')}.log"

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def main():
    today = datetime.now().strftime('%Y-%m-%d')
    output_lines = []
    
    def log(line):
        output_lines.append(line)
        print(line)
    
    log(f"=== Security Check {datetime.now()} ===")
    log("1. Allowlists:")
    code, out, _ = run_cmd("grep -E 'TELEGRAM_ALLOWED_USERS|GATEWAY_ALLOW_ALL_USERS' /opt/data/config.yaml /opt/data/.env 2>/dev/null || echo '  Nao configurado'")
    for line in out.split('\n'):
        log(line)
    
    log("2. Cosign:")
    if os.path.isfile("/opt/data/bin/cosign") and os.access("/opt/data/bin/cosign", os.X_OK):
        code, out, _ = run_cmd("/opt/data/bin/cosign version | head -1")
        log(f"  OK Instalado ({out})")
    else:
        log("  FALTANDO")
    
    log("3. Dashboard binding (0.0.0.0 --insecure):")
    log("  (ignorado - normal no container Umbrel)")
    
    log("4. Conexoes pty insecure:")
    log("  (ignorado - normal para TUI/CLI)")
    
    log("5. Telegram token status (InvalidToken/Unauthorized hoje):")
    code, out, _ = run_cmd(f'grep -c "{today}.*InvalidToken|{today}.*Unauthorized" /opt/data/logs/gateway.log 2>/dev/null || echo 0')
    token_errors = int(out.strip()) if out.strip().isdigit() else 0
    if token_errors > 0:
        log(f"  {token_errors} erros de token hoje ALERTA")
    else:
        log("  0 erros de token hoje OK")
    
    log("6. Auxiliar Nous auth:")
    log("  (ignorado - esperado sem portal.nousresearch.com)")
    
    log("7. Credenciais antigas (>90 dias):")
    code, out, _ = run_cmd("find /opt/data -maxdepth 1 \\( -name '.env' -o -name 'auth.json' \\) -mtime +90 -exec ls -la {} \\; 2>/dev/null || echo '  Nenhuma'")
    for line in out.split('\n'):
        log(line)
    
    log("8. Espaco em disco:")
    code, out, _ = run_cmd("df -h /opt/data | tail -1")
    parts = out.split()
    if len(parts) >= 5:
        log(f"  Usado: {parts[2]} / {parts[1]} ({parts[4]})")
    
    # Write log
    with open(LOG, 'w') as f:
        f.write('\n'.join(output_lines) + '\n')
    
    # Check REAL alerts
    REAL_ALERTS = 0
    if not (os.path.isfile("/opt/data/bin/cosign") and os.access("/opt/data/bin/cosign", os.X_OK)):
        REAL_ALERTS = 1
    if token_errors > 0:
        REAL_ALERTS = 1
    code, out, _ = run_cmd("find /opt/data -maxdepth 1 \\( -name '.env' -o -name 'auth.json' \\) -mtime +90 2>/dev/null | grep -q .")
    if code == 0:
        REAL_ALERTS = 1
    code, out, _ = run_cmd("df /opt/data | tail -1 | awk '{print $5}' | sed 's/%//'")
    try:
        disk_usage = int(out.strip())
        if disk_usage > 85:
            REAL_ALERTS = 1
    except:
        pass
    
    return REAL_ALERTS

if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
import subprocess
import os
import tarfile
from datetime import datetime

BACKUP_DIR = "/opt/data/backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

INCLUDE = [
    "/opt/data/.env*",
    "/opt/data/auth.json*",
    "/opt/data/config.yaml*",
    "/opt/data/SOUL.md",
    "/opt/data/scripts/",
    "/opt/data/skills/",
    "/opt/data/plugins/",
    "/opt/data/mcp/",
    "/opt/data/hooks/",
    "/opt/data/memories/",
    "/opt/data/state/",
    "/opt/data/plans/",
    "/opt/data/kanban/",
    "/opt/data/pairing/",
    "/opt/data/platforms/",
    "/opt/data/cron/",
    "/opt/data/bin/",
    "/opt/data/rag/",
]

EXCLUDE = [
    "/opt/data/cache/",
    "/opt/data/logs/*.log",
    "/opt/data/node_modules/",
    "/opt/data/.cache/",
    "/opt/data/.npm/",
    "/opt/data/*_cache.json",
    "/opt/data/state.db*",
    "/opt/data/audio_cache/",
    "/opt/data/image_cache/",
    "/opt/data/kanban.db*",
    "/opt/data/sessions/",
    "/opt/data/backups/",
]

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d")
    backup_file = f"{BACKUP_DIR}/hermes-backup-{timestamp}.tar.gz"
    
    # Build tar command with includes and excludes
    include_args = " ".join(INCLUDE)
    exclude_args = " ".join([f"--exclude={e}" for e in EXCLUDE])
    
    cmd = f"tar -czf {backup_file} {exclude_args} {include_args} 2>/dev/null"
    
    code, out, err = run_cmd(cmd)
    
    if code != 0:
        print(f"ERRO no backup: {err}")
        return 1
    
    # Get backup size
    size = os.path.getsize(backup_file)
    size_mb = size / (1024 * 1024)
    
    # Keep only last 3 backups
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("hermes-backup-") and f.endswith(".tar.gz")])
    for old_backup in backups[:-3]:
        os.remove(os.path.join(BACKUP_DIR, old_backup))
    
    print(f"Backup criado: {backup_file} ({size_mb:.1f} MB)")
    print(f"Backups mantidos: {len(backups[:-3]) + min(3, len(backups))}")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
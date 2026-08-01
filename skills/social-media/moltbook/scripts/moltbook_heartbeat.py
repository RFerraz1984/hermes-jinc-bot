#!/usr/bin/env python3
# Moltbook Heartbeat Script for Cronjob
# Runs the moltbook heartbeat and notifies via messenger if online

import json
import subprocess
import sys
from pathlib import Path

def main():
    # Run heartbeat with post-if-inspired enabled
    result = subprocess.run(
        [sys.executable, "/opt/data/skills/social-media/moltbook/scripts/moltbook_helpers.py", "heartbeat", "--post-if-inspired", "--submolt", "governance"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    # Try to notify via Hermes if available
    try:
        subprocess.run(
            ["hermes", "send", "💓 Ethos.Tracker Moltbook heartbeat completed.", "--deliver", "origin"],
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass  # Hermes CLI might not be available in cron context

    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
Moltbook Cron Runner
Runs heartbeat + monitor in sequence for cronjob.
"""

import sys
import subprocess

def run_heartbeat():
    """Run heartbeat with args."""
    try:
        result = subprocess.run(
            [sys.executable, "/opt/data/skills/social-media/moltbook/scripts/moltbook_helpers.py", "heartbeat", "--post-if-inspired", "--submolt", "governance"],
            capture_output=True,
            text=True,
            timeout=120
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ heartbeat timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ heartbeat failed: {e}", file=sys.stderr)
        return False

def run_monitor():
    """Run monitor script."""
    try:
        result = subprocess.run(
            [sys.executable, "/opt/data/skills/social-media/moltbook/scripts/moltbook_monitor.py"],
            capture_output=True,
            text=True,
            timeout=300
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ monitor timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ monitor failed: {e}", file=sys.stderr)
        return False

def main():
    print("=" * 60)
    print("🕐 Moltbook Cron Runner - " + __import__('datetime').datetime.now().isoformat())
    print("=" * 60)
    
    # 1. Run heartbeat
    print("\n💓 Running heartbeat...")
    hb_ok = run_heartbeat()
    
    # 2. Run monitor
    print("\n🔍 Running monitor...")
    mon_ok = run_monitor()
    
    print("\n" + "=" * 60)
    print(f"Heartbeat: {'✅' if hb_ok else '❌'} | Monitor: {'✅' if mon_ok else '❌'}")
    print("=" * 60)
    
    sys.exit(0 if (hb_ok and mon_ok) else 1)


if __name__ == "__main__":
    main()
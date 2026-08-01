#!/bin/bash
# Wrapper para cron job legislativo - configura ambiente e roda script Python

export PATH="/opt/data/.npm-global/bin:$PATH"
export PLAYWRIGHT_BROWSERS_PATH="/opt/data/.playwright"

cd /opt/data/skills/journalism/accessibility-audit-toolkit
/opt/data/.venv/bin/python scripts/audit_cron_legislative.py
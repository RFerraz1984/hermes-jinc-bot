#!/bin/bash
# Wrapper isolado para audit_cron.py - executa em subshell limpo

# Limpa variáveis de ambiente que possam interferir
unset PYTHONPATH
unset PYTHONHOME

# Configura ambiente
export PATH="/opt/data/.npm-global/bin:/opt/data/.venv/bin:$PATH"
export PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright

# Executa em subshell isolado
exec /opt/data/.venv/bin/python -c "
import sys
sys.path.insert(0, '/opt/data/skills/journalism/accessibility-audit-toolkit')
from scripts.audit_cron import main
import asyncio
asyncio.run(main())
"
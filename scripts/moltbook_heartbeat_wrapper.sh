#!/bin/bash
cd /opt/data
python3 /opt/data/scripts/moltbook_helpers.py heartbeat 2>&1 | python3 /opt/data/scripts/smart_notify_filter.py --job-name "Moltbook Heartbeat" --exit-code ${PIPESTATUS[0]}

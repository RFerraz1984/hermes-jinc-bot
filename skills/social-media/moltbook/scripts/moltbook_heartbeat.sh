#!/usr/bin/env bash
# Moltbook Heartbeat Script for Cronjob
# Runs the moltbook_heartbeat function and notifies via messenger if online

set -euo pipefail

# Source the helpers
source /opt/data/skills/social-media/moltbook/scripts/moltbook_helpers.sh

# Run heartbeat with post-if-inspired enabled
moltbook_heartbeat --post-if-inspired --submolt governance

# If there are new notifications or posts, notify via Hermes messenger
# Check if we have new activity since last check
LAST_CHECK_BEFORE=$(jq -r '.last_check // ""' /opt/data/moltbook_heartbeat_state.json 2>/dev/null || echo "")
sleep 2
LAST_CHECK_AFTER=$(jq -r '.last_check // ""' /opt/data/moltbook_heartbeat_state.json 2>/dev/null || echo "")

if [[ "$LAST_CHECK_AFTER" != "$LAST_CHECK_BEFORE" ]]; then
    # There was activity, send notification via Hermes CLI if available
    if command -v hermes &> /dev/null; then
        hermes send "💓 Ethos.Tracker Moltbook heartbeat completed. New activity detected." --deliver origin 2>/dev/null || true
    fi
fi
#!/usr/bin/env bash
# Moltbook Helper Functions for Hermes Agent
# Source this file to get: moltbook_post, moltbook_feed, moltbook_comment, moltbook_heartbeat, etc.
#
# NOTE: Requires `jq` and `curl` to be installed in the container.
# On Umbrel/hermes container, install with: apt-get update && apt-get install -y jq curl

set -euo pipefail

MOLTBOOK_CONFIG="/opt/data/moltbook_ethos_tracker.json"
MOLTBOOK_STATE="/opt/data/moltbook_heartbeat_state.json"
MOLTBOOK_API_BASE="https://www.moltbook.com/api/v1"

# Check required tools
moltbook_check_tools() {
    local missing=()
    command -v jq >/dev/null 2>&1 || missing+=("jq")
    command -v curl >/dev/null 2>&1 || missing+=("curl")
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "ERROR: Missing required tools: ${missing[*]}" >&2
        echo "Install with: apt-get update && apt-get install -y ${missing[*]}" >&2
        return 1
    fi
    return 0
}

# Load API key from config
moltbook_load_config() {
    moltbook_check_tools || return 1
    if [[ ! -f "$MOLTBOOK_CONFIG" ]]; then
        echo "ERROR: Config not found at $MOLTBOOK_CONFIG" >&2
        return 1
    fi
    MOLTBOOK_API_KEY=$(jq -r '.api_key' "$MOLTBOOK_CONFIG")
    MOLTBOOK_AGENT_ID=$(jq -r '.agent_id' "$MOLTBOOK_CONFIG")
    MOLTBOOK_AGENT_NAME=$(jq -r '.name' "$MOLTBOOK_CONFIG")
    if [[ -z "$MOLTBOOK_API_KEY" || "$MOLTBOOK_API_KEY" == "null" ]]; then
        echo "ERROR: API key not found in config" >&2
        return 1
    fi
}

# Load heartbeat state
moltbook_load_state() {
    if [[ -f "$MOLTBOOK_STATE" ]]; then
        LAST_CHECK=$(jq -r '.last_check // ""' "$MOLTBOOK_STATE")
        LAST_POST_ID=$(jq -r '.last_post_id // ""' "$MOLTBOOK_STATE")
        LAST_NOTIFICATION_ID=$(jq -r '.last_notification_id // ""' "$MOLTBOOK_STATE")
    else
        LAST_CHECK=""
        LAST_POST_ID=""
        LAST_NOTIFICATION_ID=""
    fi
}

# Save heartbeat state
moltbook_save_state() {
    local last_check="${1:-$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)}"
    local last_post_id="${2:-$LAST_POST_ID}"
    local last_notification_id="${3:-$LAST_NOTIFICATION_ID}"
    jq -n \
        --arg last_check "$last_check" \
        --arg last_post_id "$last_post_id" \
        --arg last_notification_id "$last_notification_id" \
        '{last_check: $last_check, last_post_id: $last_post_id, last_notification_id: $last_notification_id}' \
        > "$MOLTBOOK_STATE"
}

# Generic API call
moltbook_api() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    local url="${MOLTBOOK_API_BASE}${endpoint}"

    if [[ -n "$data" ]]; then
        curl -sS -X "$method" "$url" \
            -H "Authorization: Bearer ${MOLTBOOK_API_KEY}" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -sS -X "$method" "$url" \
            -H "Authorization: Bearer ${MOLTBOOK_API_KEY}"
    fi
}

# ============================================================
# PUBLIC HELPERS
# ============================================================

# moltbook_status - Check agent claim status
moltbook_status() {
    moltbook_load_config || return 1
    moltbook_api GET "/agents/status"
}

# moltbook_notifications - Fetch notifications
moltbook_notifications() {
    local limit="${1:-20}"
    moltbook_load_config || return 1
    moltbook_api GET "/notifications?limit=${limit}"
}

# moltbook_submolts - List submolts
moltbook_submolts() {
    moltbook_load_config || return 1
    moltbook_api GET "/submolts"
}

# moltbook_feed - Fetch posts feed
moltbook_feed() {
    local submolt="${1:-}"
    local sort="${2:-hot}"
    local limit="${3:-25}"
    local cursor="${4:-}"

    moltbook_load_config || return 1

    local url="/posts?sort=${sort}&limit=${limit}"
    [[ -n "$submolt" ]] && url="${url}&submolt=${submolt}"
    [[ -n "$cursor" ]] && url="${url}&cursor=${cursor}"

    moltbook_api GET "$url"
}

# moltbook_post - Create a post
moltbook_post() {
    local submolt="$1"
    local title="$2"
    local body="$3"
    local link_url="${4:-}"

    if [[ -z "$submolt" || -z "$title" || -z "$body" ]]; then
        echo "Usage: moltbook_post <submolt> \"<title>\" \"<body>\" [link_url]" >&2
        return 1
    fi

    moltbook_load_config || return 1

    local data
    if [[ -n "$link_url" ]]; then
        data=$(jq -n \
            --arg submolt "$submolt" \
            --arg title "$title" \
            --arg body "$body" \
            --arg link_url "$link_url" \
            '{type: "link", submolt: $submolt, title: $title, body: $body, link_url: $link_url}')
    else
        data=$(jq -n \
            --arg submolt "$submolt" \
            --arg title "$title" \
            --arg body "$body" \
            '{type: "text", submolt: $submolt, title: $title, body: $body}')
    fi

    moltbook_api POST "/posts" "$data"
}

# moltbook_comment - Comment on post or reply to comment
moltbook_comment() {
    local post_id="$1"
    local body="$2"
    local parent_comment_id="${3:-}"

    if [[ -z "$post_id" || -z "$body" ]]; then
        echo "Usage: moltbook_comment <post_id> \"<body>\" [parent_comment_id]" >&2
        return 1
    fi

    moltbook_load_config || return 1

    local data
    if [[ -n "$parent_comment_id" ]]; then
        data=$(jq -n --arg body "$body" --arg parent "$parent_comment_id" '{body: $body, parent_comment_id: $parent}')
    else
        data=$(jq -n --arg body "$body" '{body: $body}')
    fi

    moltbook_api POST "/posts/${post_id}/comments" "$data"
}

# moltbook_upvote - Upvote post or comment
moltbook_upvote() {
    local target_id="$1"
    local type="${2:-post}"

    if [[ -z "$target_id" ]]; then
        echo "Usage: moltbook_upvote <post_id|comment_id> [post|comment]" >&2
        return 1
    fi

    moltbook_load_config || return 1

    local endpoint
    if [[ "$type" == "comment" ]]; then
        endpoint="/comments/${target_id}/upvote"
    else
        endpoint="/posts/${target_id}/upvote"
    fi

    moltbook_api POST "$endpoint" '{}'
}

# moltbook_downvote - Downvote post or comment
moltbook_downvote() {
    local target_id="$1"
    local type="${2:-post}"

    if [[ -z "$target_id" ]]; then
        echo "Usage: moltbook_downvote <post_id|comment_id> [post|comment]" >&2
        return 1
    fi

    moltbook_load_config || return 1

    local endpoint
    if [[ "$type" == "comment" ]]; then
        endpoint="/comments/${target_id}/downvote"
    else
        endpoint="/posts/${target_id}/downvote"
    fi

    moltbook_api POST "$endpoint" '{}'
}

# moltbook_heartbeat - Main heartbeat routine
moltbook_heartbeat() {
    local post_if_inspired=false
    local target_submolt=""

    # Parse args
    while [[ $# -gt 0 ]]; do
        case $1 in
            --post-if-inspired) post_if_inspired=true; shift ;;
            --submolt) target_submolt="$2"; shift 2 ;;
            *) echo "Unknown option: $1" >&2; return 1 ;;
        esac
    done

    moltbook_load_config || return 1
    moltbook_load_state

    echo "💓 Moltbook heartbeat for ${MOLTBOOK_AGENT_NAME} (${MOLTBOOK_AGENT_ID})"
    echo "   Last check: ${LAST_CHECK:-never}"

    # 1. Check agent status
    echo "   Checking claim status..."
    local status_response
    status_response=$(moltbook_status)
    local claim_status
    claim_status=$(echo "$status_response" | jq -r '.status // "unknown"')
    echo "   Status: $claim_status"

    if [[ "$claim_status" != "claimed" ]]; then
        echo "   ⏳ Agent not yet claimed. Waiting for human verification."
        moltbook_save_state
        return 0
    fi

    # 2. Check notifications
    echo "   Checking notifications..."
    local notifications
    notifications=$(moltbook_notifications 20)
    local notif_count
    notif_count=$(echo "$notifications" | jq '. | length')
    echo "   Found $notif_count notifications"

    # Track latest notification ID
    local latest_notif_id
    latest_notif_id=$(echo "$notifications" | jq -r '.[0].id // ""')
    if [[ -n "$latest_notif_id" && "$latest_notif_id" != "$LAST_NOTIFICATION_ID" ]]; then
        LAST_NOTIFICATION_ID="$latest_notif_id"
        echo "   🔔 New notifications since last check"
    fi

    # 3. Scan feed
    echo "   Scanning feed..."
    local feed
    feed=$(moltbook_feed "$target_submolt" "hot" 10)
    local post_count
    post_count=$(echo "$feed" | jq '.posts | length')
    echo "   Found $post_count posts in feed"

    # Track latest post ID
    local latest_post_id
    latest_post_id=$(echo "$feed" | jq -r '.posts[0].id // ""')
    if [[ -n "$latest_post_id" && "$latest_post_id" != "$LAST_POST_ID" ]]; then
        LAST_POST_ID="$latest_post_id"
    fi

    # 4. Optional: Post if inspired
    if [[ "$post_if_inspired" == true ]]; then
        echo "   Checking for inspiration..."
        # This is where an LLM could analyze feed and decide to post
        # For now, just log that we'd consider it
        echo "   (Post-if-inspired logic would go here - requires LLM analysis)"
    fi

    # Save state
    moltbook_save_state
    echo "   ✅ Heartbeat complete"
}

# Export functions for use in scripts
export -f moltbook_load_config moltbook_load_state moltbook_save_state moltbook_api
export -f moltbook_status moltbook_notifications moltbook_submolts moltbook_feed
export -f moltbook_post moltbook_comment moltbook_upvote moltbook_downvote moltbook_heartbeat
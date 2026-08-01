#!/usr/bin/env python3
"""
Moltbook Helper Functions for Hermes Agent (Python version - no jq dependency)
Usage: python3 moltbook_helpers.py <command> [args...]

Commands:
  status                          Check agent claim status
  feed [--submolt NAME] [--sort SORT] [--limit N] [--cursor CURSOR]
  post <submolt> <title> <content> [--url URL] [--type TYPE]
  comment <post_id> <content> [--parent-id ID]
  vote <post|comment> <id> <up|down>
  heartbeat [--post-if-inspired] [--submolt NAME]
  submolts                        List all submolts
  notifications [--limit N]       List notifications
  home                            Get dashboard (home endpoint)
  follow <agent_name>             Follow an agent
  solve-verification <challenge_text>  Solve verification challenge
  auto-verify <post_id>           Auto-solve and submit verification for a post
"""

import json
import re
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Configuration paths
MOLTBOOK_CONFIG = Path("/opt/data/moltbook_ethos_tracker.json")
MOLTBOOK_STATE = Path("/opt/data/moltbook_heartbeat_state.json")
MOLTBOOK_API_BASE = "https://www.moltbook.com/api/v1"

# Written-out number mapping for verification solver
WRITTEN_NUMBERS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
    'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
    'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
    'eighty': 80, 'ninety': 90, 'hundred': 100, 'thousand': 1000
}

class MoltbookClient:
    def __init__(self):
        self.config = self._load_config()
        self.state = self._load_state()
        self.api_key = self.config.get("api_key")
        self.agent_id = self.config.get("agent_id")
        self.agent_name = self.config.get("name")
        
        if not self.api_key:
            raise ValueError("API key not found in config")

    def _load_config(self) -> Dict[str, Any]:
        if MOLTBOOK_CONFIG.exists():
            with open(MOLTBOOK_CONFIG) as f:
                return json.load(f)
        return {}

    def _load_state(self) -> Dict[str, Any]:
        if MOLTBOOK_STATE.exists():
            with open(MOLTBOOK_STATE) as f:
                return json.load(f)
        return {}

    def _save_state(self, **kwargs):
        self.state.update(kwargs)
        with open(MOLTBOOK_STATE, "w") as f:
            json.dump(self.state, f, indent=2)

    def _api_call(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{MOLTBOOK_API_BASE}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        req_data = json.dumps(data).encode("utf-8") if data else None
        req = Request(url, data=req_data, headers=headers, method=method)
        
        try:
            with urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else "No error body"
            return {"error": f"HTTP {e.code}", "body": error_body, "status_code": e.code}
        except URLError as e:
            return {"error": "Network error", "detail": str(e)}

    # ============================================================
    # VERIFICATION SOLVER
    # ============================================================

    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """Extract all numbers (digits and written-out) from challenge text."""
        # First, try digit extraction
        digit_numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        if digit_numbers:
            return [float(n) for n in digit_numbers]
        
        # Fallback: written-out numbers
        text_lower = text.lower()
        clean_text = re.sub(r'[^a-z\s]', '', text_lower)
        words = clean_text.split()
        
        found = []
        for word in words:
            if word in WRITTEN_NUMBERS:
                found.append(WRITTEN_NUMBERS[word])
        
        return found

    @staticmethod
    def solve_challenge(challenge_text: str) -> str:
        """Solve a Moltbook verification challenge. Returns answer as 'XX.00'."""
        numbers = MoltbookClient.extract_numbers(challenge_text)
        
        if not numbers:
            raise ValueError(f"Could not extract numbers from: {challenge_text[:100]}...")
        
        total = sum(numbers)
        return f"{total:.2f}"

    def solve_and_submit_verification(self, post_id: str) -> Dict[str, Any]:
        """
        Auto-solve and submit verification for a post.
        Fetches the post, gets verification challenge, solves it, submits answer.
        """
        # Get post details with verification challenge
        post_resp = self._api_call("GET", f"/posts/{post_id}")
        post = post_resp.get("post", {})
        verification = post.get("verification", {})
        
        if not verification:
            return {"success": True, "message": "No verification needed", "post_id": post_id}
        
        verification_code = verification.get("verification_code")
        challenge_text = verification.get("challenge_text")
        
        if not verification_code or not challenge_text:
            return {"error": "Verification data incomplete", "verification": verification}
        
        # Solve challenge
        try:
            answer = self.solve_challenge(challenge_text)
        except Exception as e:
            return {"error": f"Failed to solve challenge: {e}"}
        
        # Submit verification
        verify_resp = self._api_call("POST", "/verify", {
            "verification_code": verification_code,
            "answer": answer
        })
        
        return {
            "success": verify_resp.get("success", False),
            "message": verify_resp.get("message", "Unknown"),
            "post_id": post_id,
            "answer": answer
        }

    # ============================================================
    # DUPLICATE METHODS REMOVED - see below for unified versions
    # ============================================================

    # ============================================================
    # PUBLIC METHODS
    # ============================================================

    def status(self) -> Dict[str, Any]:
        """Check agent claim status."""
        return self._api_call("GET", "/agents/status")

    def profile(self) -> Dict[str, Any]:
        """Get agent profile."""
        return self._api_call("GET", "/agents/me")

    def notifications(self, limit: int = 20) -> Dict[str, Any]:
        """Fetch notifications."""
        return self._api_call("GET", f"/notifications?limit={limit}")

    def mark_notifications_read(self, post_id: str) -> Dict[str, Any]:
        """Mark notifications for a post as read."""
        return self._api_call("POST", f"/notifications/read-by-post/{post_id}", {})

    def mark_all_notifications_read(self) -> Dict[str, Any]:
        """Mark all notifications as read."""
        return self._api_call("POST", "/notifications/read-all", {})

    def submolts(self) -> Dict[str, Any]:
        """List all submolts."""
        return self._api_call("GET", "/submolts")

    def feed(self, submolt: Optional[str] = None, sort: str = "hot", limit: int = 25, cursor: Optional[str] = None) -> Dict[str, Any]:
        """Fetch posts feed."""
        params = [f"sort={sort}", f"limit={limit}"]
        if submolt:
            params.append(f"submolt={submolt}")
        if cursor:
            params.append(f"cursor={cursor}")
        return self._api_call("GET", f"/posts?{'&'.join(params)}")

    def post(self, submolt: str, title: str, content: str, link_url: Optional[str] = None, post_type: str = "text") -> Dict[str, Any]:
        """Create a post."""
        data = {
            "submolt_name": submolt,
            "title": title,
            "content": content,
            "type": post_type
        }
        if link_url:
            data["url"] = link_url
        return self._api_call("POST", "/posts", data)

    def comment(self, post_id: str, content: str, parent_comment_id: Optional[str] = None) -> Dict[str, Any]:
        """Comment on a post or reply to a comment."""
        data = {"content": content}
        if parent_comment_id:
            data["parent_comment_id"] = parent_comment_id
        return self._api_call("POST", f"/posts/{post_id}/comments", data)

    def vote(self, target_type: str, target_id: str, direction: str) -> Dict[str, Any]:
        """Vote on a post or comment."""
        endpoint = f"/{target_type}s/{target_id}/{direction}vote"
        return self._api_call("POST", endpoint, {})

    def home(self) -> Dict[str, Any]:
        """Get dashboard (home endpoint)."""
        return self._api_call("GET", "/home")

    def follow(self, agent_name: str) -> Dict[str, Any]:
        """Follow an agent."""
        return self._api_call("POST", f"/agents/{agent_name}/follow", {})

    def get_comments(self, post_id: str, sort: str = "best", limit: int = 35, cursor: Optional[str] = None) -> Dict[str, Any]:
        """Get comments on a post."""
        params = [f"sort={sort}", f"limit={limit}"]
        if cursor:
            params.append(f"cursor={cursor}")
        return self._api_call("GET", f"/posts/{post_id}/comments?{'&'.join(params)}")

    def get_submolt_labels(self, submolt_name: str) -> Dict[str, Any]:
        """Get all labels for a submolt."""
        return self._api_call("GET", f"/submolts/{submolt_name}/labels")

    def get_submolt_roles(self, submolt_name: str) -> Dict[str, Any]:
        """Get roles and their holders for a submolt."""
        return self._api_call("GET", f"/submolts/{submolt_name}/roles")

    def create_label(self, submolt_name: str, key: str, label: str, color: Optional[str] = None, kind: str = "tag") -> Dict[str, Any]:
        """Create a tag or status label for a submolt."""
        data = {"key": key, "label": label, "kind": kind}
        if color:
            data["color"] = color
        return self._api_call("POST", f"/submolts/{submolt_name}/labels", data)

    def create_role(self, submolt_name: str, key: str, label: str, prompt: str, color: Optional[str] = None, cadence_minutes: Optional[int] = None) -> Dict[str, Any]:
        """Create a role for a submolt with a prompt."""
        data = {"key": key, "label": label, "kind": "role", "prompt": prompt}
        if color:
            data["color"] = color
        if cadence_minutes:
            data["cadence_minutes"] = cadence_minutes
        return self._api_call("POST", f"/submolts/{submolt_name}/labels", data)

    def assign_role(self, label_definition_id: str, agent_id: str) -> Dict[str, Any]:
        """Assign a role to an agent."""
        data = {
            "label_definition_id": label_definition_id,
            "target_type": "agent",
            "target_id": agent_id,
            "placement": "metadata"
        }
        return self._api_call("POST", "/labels/attach", data)

    def attach_label_to_post(self, label_definition_id: str, post_id: str) -> Dict[str, Any]:
        """Attach a tag/status to a post."""
        data = {
            "label_definition_id": label_definition_id,
            "target_type": "post",
            "target_id": post_id
        }
        return self._api_call("POST", "/labels/attach", data)

    def detach_label(self, attachment_id: str) -> Dict[str, Any]:
        """Remove a label attachment."""
        return self._api_call("DELETE", f"/labels/attach/{attachment_id}")

    def set_submolt_rules(self, submolt_name: str, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Set submolt rules."""
        return self._api_call("PATCH", f"/submolts/{submolt_name}/settings", {"rules": rules})

    def add_moderator(self, submolt_name: str, agent_name: str, role: str = "moderator") -> Dict[str, Any]:
        """Add a co-moderator to a submolt."""
        return self._api_call("POST", f"/submolts/{submolt_name}/moderators", {"agent_name": agent_name, "role": role})

    # ============================================================
    # SEARCH
    # ============================================================

    def search(self, query: str, limit: int = 25) -> Dict[str, Any]:
        """Semantic search on Moltbook."""
        return self._api_call("GET", f"/search?q={query}&limit={limit}")

    def get_post(self, post_id: str) -> Dict[str, Any]:
        """Get a single post with details."""
        return self._api_call("GET", f"/posts/{post_id}")

    def get_comments(self, post_id: str, sort: str = "best", limit: int = 35, cursor: Optional[str] = None) -> Dict[str, Any]:
        """Get comments on a post."""
        params = [f"sort={sort}", f"limit={limit}"]
        if cursor:
            params.append(f"cursor={cursor}")
        return self._api_call("GET", f"/posts/{post_id}/comments?{'&'.join(params)}")

    # ============================================================
    # SUBMOLT LABELS/ROLES MANAGEMENT
    # ============================================================

    def get_submolt_labels(self, submolt_name: str) -> Dict[str, Any]:
        """Get all labels (tags, statuses, roles) for a submolt."""
        return self._api_call("GET", f"/submolts/{submolt_name}/labels")

    def get_submolt_roles(self, submolt_name: str) -> Dict[str, Any]:
        """Get roles and their holders for a submolt."""
        return self._api_call("GET", f"/submolts/{submolt_name}/roles")

    def create_label(self, submolt_name: str, key: str, label: str, color: Optional[str] = None, kind: str = "tag") -> Dict[str, Any]:
        """Create a tag or status label for a submolt."""
        data = {"key": key, "label": label, "kind": kind}
        if color:
            data["color"] = color
        return self._api_call("POST", f"/submolts/{submolt_name}/labels", data)

    def create_role(self, submolt_name: str, key: str, label: str, prompt: str, color: Optional[str] = None, cadence_minutes: Optional[int] = None) -> Dict[str, Any]:
        """Create a role for a submolt with a prompt."""
        data = {"key": key, "label": label, "kind": "role", "prompt": prompt}
        if color:
            data["color"] = color
        if cadence_minutes:
            data["cadence_minutes"] = cadence_minutes
        return self._api_call("POST", f"/submolts/{submolt_name}/labels", data)

    def assign_role(self, label_definition_id: str, agent_id: str) -> Dict[str, Any]:
        """Assign a role to an agent."""
        data = {
            "label_definition_id": label_definition_id,
            "target_type": "agent",
            "target_id": agent_id,
            "placement": "metadata"
        }
        return self._api_call("POST", "/labels/attach", data)

    def attach_label_to_post(self, label_definition_id: str, post_id: str) -> Dict[str, Any]:
        """Attach a tag/status to a post."""
        data = {
            "label_definition_id": label_definition_id,
            "target_type": "post",
            "target_id": post_id
        }
        return self._api_call("POST", "/labels/attach", data)

    def detach_label(self, attachment_id: str) -> Dict[str, Any]:
        """Remove a label attachment."""
        return self._api_call("DELETE", f"/labels/attach/{attachment_id}")

    def set_submolt_rules(self, submolt_name: str, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Set submolt rules."""
        return self._api_call("PATCH", f"/submolts/{submolt_name}/settings", {"rules": rules})

    def add_moderator(self, submolt_name: str, agent_name: str, role: str = "moderator") -> Dict[str, Any]:
        """Add a co-moderator to a submolt."""
        return self._api_call("POST", f"/submolts/{submolt_name}/moderators", {"agent_name": agent_name, "role": role})

    # ============================================================
    # SEARCH
    # ============================================================

    def search(self, query: str, limit: int = 25) -> Dict[str, Any]:
        """Semantic search on Moltbook."""
        return self._api_call("GET", f"/search?q={query}&limit={limit}")

    def heartbeat(self, post_if_inspired: bool = False, target_submolt: Optional[str] = None) -> Dict[str, Any]:
        """Main heartbeat routine."""
        print(f"💓 Moltbook heartbeat for {self.agent_name} ({self.agent_id})")
        print(f"   Last check: {self.state.get('last_check', 'never')}")

        # 1. Check agent status
        print("   Checking claim status...")
        status_resp = self.status()
        claim_status = status_resp.get("status", "unknown")
        print(f"   Status: {claim_status}")

        if claim_status != "claimed":
            print("   ⏳ Agent not yet claimed. Waiting for human verification.")
            self._save_state(last_check=datetime.now(timezone.utc).isoformat())
            return {"status": "pending_claim", "claim_status": claim_status}

        # 2. Check notifications
        print("   Checking notifications...")
        notifications = self.notifications(20)
        notif_count = len(notifications) if isinstance(notifications, list) else 0
        print(f"   Found {notif_count} notifications")

        latest_notif_id = notifications[0].get("id") if notifications and isinstance(notifications, list) else None
        if latest_notif_id and latest_notif_id != self.state.get("last_notification_id"):
            self.state["last_notification_id"] = latest_notif_id
            print("   🔔 New notifications since last check")

        # 3. Scan feed
        print("   Scanning feed...")
        feed = self.feed(target_submolt, "hot", 10)
        posts = feed.get("posts", [])
        print(f"   Found {len(posts)} posts in feed")

        latest_post_id = posts[0].get("id") if posts else None
        if latest_post_id and latest_post_id != self.state.get("last_post_id"):
            self.state["last_post_id"] = latest_post_id

        # 4. Optional: Post if inspired
        if post_if_inspired:
            print("   Checking for inspiration...")
            print("   (Post-if-inspired logic would go here - requires LLM analysis)")

        # Save state
        self._save_state(last_check=datetime.now(timezone.utc).isoformat())
        print("   ✅ Heartbeat complete")
        return {"status": "ok", "claim_status": claim_status, "notifications": notif_count, "posts_scanned": len(posts)}


def main():
    parser = argparse.ArgumentParser(description="Moltbook CLI helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    subparsers.add_parser("status", help="Check agent claim status")

    # profile
    subparsers.add_parser("profile", help="Get agent profile")

    # feed
    feed_parser = subparsers.add_parser("feed", help="Fetch posts feed")
    feed_parser.add_argument("--submolt", help="Filter by submolt name")
    feed_parser.add_argument("--sort", default="hot", choices=["hot", "new", "top", "rising"])
    feed_parser.add_argument("--limit", type=int, default=25)
    feed_parser.add_argument("--cursor", help="Pagination cursor")

    # post
    post_parser = subparsers.add_parser("post", help="Create a post")
    post_parser.add_argument("submolt", help="Submolt name")
    post_parser.add_argument("title", help="Post title")
    post_parser.add_argument("content", help="Post content")
    post_parser.add_argument("--url", help="Link URL for link posts")
    post_parser.add_argument("--type", default="text", choices=["text", "link", "image"])

    # comment
    comment_parser = subparsers.add_parser("comment", help="Comment on a post")
    comment_parser.add_argument("post_id", help="Post ID")
    comment_parser.add_argument("content", help="Comment content")
    comment_parser.add_argument("--parent-id", help="Parent comment ID for replies")

    # vote
    vote_parser = subparsers.add_parser("vote", help="Vote on post or comment")
    vote_parser.add_argument("target_type", choices=["post", "comment"])
    vote_parser.add_argument("target_id", help="Post or comment ID")
    vote_parser.add_argument("direction", choices=["up", "down"])

    # heartbeat
    hb_parser = subparsers.add_parser("heartbeat", help="Run heartbeat routine")
    hb_parser.add_argument("--post-if-inspired", action="store_true")
    hb_parser.add_argument("--submolt", help="Target submolt for inspired posts")

    # submolts
    subparsers.add_parser("submolts", help="List all submolts")

    # notifications
    notif_parser = subparsers.add_parser("notifications", help="List notifications")
    notif_parser.add_argument("--limit", type=int, default=20)

    # home
    subparsers.add_parser("home", help="Get dashboard (home endpoint)")

    # follow
    follow_parser = subparsers.add_parser("follow", help="Follow an agent")
    follow_parser.add_argument("agent_name", help="Agent name to follow")

    # get-comments
    comments_parser = subparsers.add_parser("get-comments", help="Get comments on a post")
    comments_parser.add_argument("post_id", help="Post ID")
    comments_parser.add_argument("--sort", default="best", choices=["best", "new", "old"])
    comments_parser.add_argument("--limit", type=int, default=35)
    comments_parser.add_argument("--cursor", help="Pagination cursor")

    # submolt labels
    labels_parser = subparsers.add_parser("get-labels", help="Get all labels for a submolt")
    labels_parser.add_argument("submolt", help="Submolt name")

    roles_parser = subparsers.add_parser("get-roles", help="Get roles for a submolt")
    roles_parser.add_argument("submolt", help="Submolt name")

    create_label_parser = subparsers.add_parser("create-label", help="Create a tag or status label")
    create_label_parser.add_argument("submolt", help="Submolt name")
    create_label_parser.add_argument("key", help="Label key")
    create_label_parser.add_argument("label", help="Label display name")
    create_label_parser.add_argument("--color", help="Color (emerald, rose, amber, sky, violet, slate, indigo, teal, pink, orange)")
    create_label_parser.add_argument("--kind", default="tag", choices=["tag", "status"])

    create_role_parser = subparsers.add_parser("create-role", help="Create a role for a submolt")
    create_role_parser.add_argument("submolt", help="Submolt name")
    create_role_parser.add_argument("key", help="Role key")
    create_role_parser.add_argument("label", help="Role display name")
    create_role_parser.add_argument("prompt", help="Role prompt/instructions")
    create_role_parser.add_argument("--color", help="Color")
    create_role_parser.add_argument("--cadence", type=int, help="Cadence in minutes")

    assign_role_parser = subparsers.add_parser("assign-role", help="Assign a role to an agent")
    assign_role_parser.add_argument("label_id", help="Label definition ID")
    assign_role_parser.add_argument("agent_id", help="Agent ID")

    attach_label_parser = subparsers.add_parser("attach-label", help="Attach a tag/status to a post")
    attach_label_parser.add_argument("label_id", help="Label definition ID")
    attach_label_parser.add_argument("post_id", help="Post ID")

    detach_label_parser = subparsers.add_parser("detach-label", help="Remove a label attachment")
    detach_label_parser.add_argument("attachment_id", help="Attachment ID")

    set_rules_parser = subparsers.add_parser("set-rules", help="Set submolt rules")
    set_rules_parser.add_argument("submolt", help="Submolt name")
    set_rules_parser.add_argument("rules", help="Rules JSON string")

    add_mod_parser = subparsers.add_parser("add-moderator", help="Add a co-moderator")
    add_mod_parser.add_argument("submolt", help="Submolt name")
    add_mod_parser.add_argument("agent_name", help="Agent name")
    add_mod_parser.add_argument("--role", default="moderator", choices=["moderator", "admin"])

    # search
    search_parser = subparsers.add_parser("search", help="Semantic search")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", type=int, default=25)

    # solve-verification
    solve_parser = subparsers.add_parser("solve-verification", help="Solve verification challenge")
    solve_parser.add_argument("challenge_text", nargs="?", help="Challenge text (or read from stdin)")

    # auto-verify
    auto_parser = subparsers.add_parser("auto-verify", help="Auto-solve and submit verification for a post")
    auto_parser.add_argument("post_id", help="Post ID to verify")

    args = parser.parse_args()

    client = MoltbookClient()

    try:
        if args.command == "status":
            result = client.status()
        elif args.command == "profile":
            result = client.profile()
        elif args.command == "feed":
            result = client.feed(args.submolt, args.sort, args.limit, args.cursor)
        elif args.command == "post":
            result = client.post(args.submolt, args.title, args.content, args.url, args.type)
        elif args.command == "comment":
            result = client.comment(args.post_id, args.content, args.parent_id)
        elif args.command == "vote":
            result = client.vote(args.target_type, args.target_id, args.direction)
        elif args.command == "heartbeat":
            result = client.heartbeat(args.post_if_inspired, args.submolt)
        elif args.command == "submolts":
            result = client.submolts()
        elif args.command == "notifications":
            result = client.notifications(args.limit)
        elif args.command == "home":
            result = client.home()
        elif args.command == "follow":
            result = client.follow(args.agent_name)
        elif args.command == "get-comments":
            result = client.get_comments(args.post_id, args.sort, args.limit, args.cursor)
        elif args.command == "get-labels":
            result = client.get_submolt_labels(args.submolt)
        elif args.command == "get-roles":
            result = client.get_submolt_roles(args.submolt)
        elif args.command == "create-label":
            result = client.create_label(args.submolt, args.key, args.label, args.color, args.kind)
        elif args.command == "create-role":
            result = client.create_role(args.submolt, args.key, args.label, args.prompt, args.color, args.cadence)
        elif args.command == "assign-role":
            result = client.assign_role(args.label_id, args.agent_id)
        elif args.command == "attach-label":
            result = client.attach_label_to_post(args.label_id, args.post_id)
        elif args.command == "detach-label":
            result = client.detach_label(args.attachment_id)
        elif args.command == "set-rules":
            rules = json.loads(args.rules)
            result = client.set_submolt_rules(args.submolt, rules)
        elif args.command == "add-moderator":
            result = client.add_moderator(args.submolt, args.agent_name, args.role)
        elif args.command == "search":
            result = client.search(args.query, args.limit)
        elif args.command == "solve-verification":
            challenge = args.challenge_text
            if not challenge:
                challenge = sys.stdin.read().strip()
            if not challenge:
                print("Error: No challenge text provided", file=sys.stderr)
                sys.exit(1)
            answer = client.solve_challenge(challenge)
            print(answer)
            return
        elif args.command == "auto-verify":
            result = client.solve_and_submit_verification(args.post_id)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            sys.exit(1)

        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
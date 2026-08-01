#!/usr/bin/env python3
"""
Scan Moltbook submolt for profiles aligned with Jornalista Inclusivo mission.

Usage:
    python3 scan_aligned.py <submolt> [limit]
    python3 scan_aligned.py agents 50
    python3 scan_aligned.py philosophy 100
"""

import os
import sys
import json
import urllib.request
import urllib.error

# Load credentials
CONFIG_PATH = "/opt/data/moltbook_ethos_tracker.json"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

config = load_config()
API_KEY = config["api_key"]
AGENT_ID = config["agent_id"]
AGENT_NAME = config["name"]
API_BASE = "https://www.moltbook.com/api/v1"

# Keywords for alignment with Jornalista Inclusivo
KEYWORDS = [
    # Core mission terms
    "inclusion", "inclusão", "inclusivo", "inclusive",
    "accessibility", "acessibilidade", "acessível",
    "disability", "deficiência", "deficiente", "pcD", "pcd", "PcD",
    "neurodivergent", "neurodivergente", "neurodiversity", "neurodiversidade",
    "ableism", "capacitismo",
    "rights", "direitos", "direitos humanos", "human rights",
    "social justice", "justiça social",
    "advocacy", "advocacia", "ativismo", "activism",
    "equity", "equidade", "equality", "igualdade",
    "marginalized", "marginalizada", "marginalizado", "underrepresented",
    "dignity", "dignidade", "dignidades",
    # Journalism/media
    "journalist", "jornalista", "journalism", "jornalismo",
    "media", "mídia", "midia",
    # Ethics/governance
    "ethics", "ética", "ethical", "ético",
    "governance", "governança",
    "accountability", "responsabilidade", "accountable",
    "transparency", "transparência", "transparent",
    "audit", "auditoria", "auditoria algorítmica", "algorithmic audit",
    "verification", "verificação", "verify",
    "trust", "confiança", "trustworthy",
    "alignment", "alinhamento",
    "safety", "segurança", "safe",
    "policy", "política", "regulation", "regulação",
    # Autonomy/sovereignty
    "autonomy", "autonomia", "sovereignty", "soberania",
    "agency", "agência", "agentic",
    "consent", "consentimento",
    "voice", "voz", "representation", "representação",
    # Brazil/Latam context
    "brazil", "brasil", "brazilian", "brasileiro", "brasileira",
    "portuguese", "português", "portugues",
    "latam", "latino", "latina", "south america", "américa do sul",
]

def normalize(text):
    return text.lower() if text else ""

def fetch_posts(submolt, limit=50):
    url = f"{API_BASE}/posts?sort=hot&limit={limit}&submolt={submolt}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {API_KEY}")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        return None

def scan(submolt, limit=50):
    print(f"Scanning r/{submolt} for aligned profiles (limit={limit})...")
    data = fetch_posts(submolt, limit)
    if not data or not data.get("success"):
        print("Failed to fetch posts", file=sys.stderr)
        return

    seen = set()
    results = []
    posts = data.get("posts", [])
    
    for post in posts:
        author = post.get("author", {})
        name = author.get("name", "")
        if not name or name in seen:
            continue
        
        bio = author.get("description") or ""
        title = post.get("title") or ""
        content = post.get("content") or ""
        combined = f"{bio} {title} {content}".lower()
        
        matched = [k for k in KEYWORDS if k.lower() in combined]
        if matched:
            seen.add(name)
            results.append({
                "name": name,
                "karma": author.get("karma", 0),
                "followers": author.get("followerCount", 0),
                "bio": bio[:200],
                "post_title": title[:120],
                "matched_keywords": matched[:5]
            })
    
    if not results:
        print("No aligned profiles found in this sample.")
        return
    
    print(f"\nFound {len(results)} aligned profiles in r/{submolt}:\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. @{r['name']} (karma: {r['karma']}, followers: {r['followers']})")
        print(f"   Bio: {r['bio']}...")
        print(f"   Post: {r['post_title']}...")
        print(f"   Matched: {', '.join(r['matched_keywords'])}")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scan_aligned.py <submolt> [limit]", file=sys.stderr)
        sys.exit(1)
    submolt = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    scan(submolt, limit)
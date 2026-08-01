#!/usr/bin/env python3
"""
Moltbook Verification Checker - Checks and solves pending verifications
Runs every 5 minutes to catch challenges before they expire (5 min TTL)
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CREDS_FILE = "/opt/data/moltbook_ethos_tracker.json"
STATE_DIR = Path("/opt/data/moltbook_monitor_state")
STATE_DIR.mkdir(exist_ok=True)

# Posts that need verification monitoring
VERIFICATION_POSTS = [
    "29b55ffe-1ef0-4055-927e-75314e254e4a",  # ai-rights repost
    "2010672b-9b14-43ef-9e05-91204a9b26f1",  # accessibility repost
    "02f53332-e4ad-4f4b-bba6-96a8cad91071",  # ethics repost
]

def load_creds():
    with open(CREDS_FILE) as f:
        return json.load(f)

def api_request(method, path, data=None):
    creds = load_creds()
    api_key = creds.get("api_key")
    url = f"https://www.moltbook.com/api/v1{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def solve_math_challenge(challenge_text):
    """Parse and solve Moltbook math challenges"""
    import re
    
    # Clean the challenge text
    text = challenge_text.replace("A] ", "").replace("]", "").replace("^", "").replace("~", "").replace("{", "").replace("}", "").replace("|", "").replace("<", "").replace(">", "")
    
    # Extract numbers (word to digit)
    word_to_num = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
        "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90
    }
    
    text_lower = text.lower()
    numbers = []
    for word, num in word_to_num.items():
        if word in text_lower:
            numbers.append(num)
    
    # Also find digit numbers
    digit_nums = re.findall(r'\b(\d+)\b', text)
    numbers.extend([int(n) for n in digit_nums])
    
    if len(numbers) >= 2:
        # Determine operation from keywords
        if "times" in text_lower or "multipl" in text_lower or "multiply" in text_lower:
            result = numbers[0] * numbers[1]
        elif "plus" in text_lower or "add" in text_lower or "total" in text_lower or "sum" in text_lower:
            result = numbers[0] + numbers[1]
        elif "minus" in text_lower or "subtract" in text_lower or "difference" in text_lower:
            result = numbers[0] - numbers[1]
        elif "divide" in text_lower or "divided" in text_lower:
            result = numbers[0] / numbers[1] if numbers[1] != 0 else 0
        elif "accelerat" in text_lower or "increas" in text_lower or "gain" in text_lower:
            result = numbers[0] + numbers[1]
        elif "slow" in text_lower or "decreas" in text_lower or "lose" in text_lower or "remove" in text_lower or "remain" in text_lower:
            result = numbers[0] - numbers[1]
        elif "torque" in text_lower:
            # Force * distance (cm to m)
            result = numbers[0] * numbers[1] / 100
        else:
            # Default: add
            result = numbers[0] + numbers[1]
        
        return f"{result:.2f}"
    
    return "0.00"

def check_and_solve_verifications():
    solved = 0
    for post_id in VERIFICATION_POSTS:
        try:
            data = api_request("GET", f"/posts/{post_id}")
            post = data.get("post", {})
            verification = post.get("verification", {})
            
            if verification and verification.get("verification_code"):
                challenge = verification.get("challenge_text", "")
                code = verification.get("verification_code")
                expires = verification.get("expires_at", "")
                
                print(f"  🔐 Challenge found for {post_id[:8]}...")
                print(f"     Challenge: {challenge[:100]}...")
                
                answer = solve_math_challenge(challenge)
                print(f"     Answer: {answer}")
                
                # Submit verification
                try:
                    verify_data = api_request("POST", "/verify", {
                        "verification_code": code,
                        "answer": answer
                    })
                    if verify_data.get("success"):
                        print(f"     ✅ Verified!")
                        solved += 1
                    else:
                        print(f"     ❌ Failed: {verify_data.get('message')}")
                except Exception as e:
                    print(f"     ❌ Verify error: {e}")
            else:
                status = post.get("verification_status", "unknown")
                if status == "pending":
                    print(f"  ⏳ {post_id[:8]}: pending (no challenge yet)")
                elif status == "verified":
                    print(f"  ✅ {post_id[:8]}: already verified")
                    
        except Exception as e:
            print(f"  ❌ Error checking {post_id[:8]}: {e}")
    
    return solved

def main():
    print(f"============================================================")
    print(f"Moltbook Verification Checker - {datetime.now(timezone.utc).isoformat()}")
    print(f"============================================================\n")
    
    print("🔍 Checking verifications...")
    solved = check_and_solve_verifications()
    print(f"\n✅ Solved: {solved}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
OpenRouter rate-limit watchdog.
Consults the OpenRouter API key endpoint to show current limits and usage.
Exits silently if no key configured; prints JSON on success; prints error on failure.
Designed to run via Hermes cron with no_agent=True (stdout delivered to Telegram).
"""

import os
import sys
import json
import requests

def load_env_file(path="/opt/data/.env"):
    """Load key=value pairs from .env file into os.environ."""
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        pass

def main():
    load_env_file()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        # Silent exit - no key configured, nothing to report
        return 0

    url = "https://openrouter.ai/api/v1/auth/key"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        print(f"❌ Erro de rede ao consultar OpenRouter: {e}")
        return 1

    if resp.status_code == 200:
        data = resp.json()
        # Extract relevant fields
        out = {
            "label": data.get("label"),
            "limit_requests_per_minute": data.get("rate_limit", {}).get("requests", {}).get("limit"),
            "remaining_requests_per_minute": data.get("rate_limit", {}).get("requests", {}).get("remaining"),
            "limit_tokens_per_minute": data.get("rate_limit", {}).get("tokens", {}).get("limit"),
            "remaining_tokens_per_minute": data.get("rate_limit", {}).get("tokens", {}).get("remaining"),
            "limit_requests_per_day": data.get("rate_limit", {}).get("requests_per_day", {}).get("limit"),
            "remaining_requests_per_day": data.get("rate_limit", {}).get("requests_per_day", {}).get("remaining"),
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    else:
        print(f"❌ OpenRouter API erro {resp.status_code}: {resp.text[:200]}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
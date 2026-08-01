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
        rate = data.get("rate_limit", {})
        req = rate.get("requests", {})
        tok = rate.get("tokens", {})
        day = rate.get("requests_per_day", {})

        # Build natural language report
        label = data.get("label") or "Chave sem label"
        
        # Requests per minute
        req_limit = req.get("limit")
        req_remain = req.get("remaining")
        if req_limit is not None and req_remain is not None:
            req_pct = (req_remain / req_limit * 100) if req_limit > 0 else 0
            req_line = f"  • Requisições/min: {req_remain:,}/{req_limit:,} restantes ({req_pct:.1f}% livre)"
        else:
            req_line = "  • Requisições/min: informações não disponíveis"

        # Tokens per minute
        tok_limit = tok.get("limit")
        tok_remain = tok.get("remaining")
        if tok_limit is not None and tok_remain is not None:
            tok_pct = (tok_remain / tok_limit * 100) if tok_limit > 0 else 0
            tok_line = f"  • Tokens/min: {tok_remain:,}/{tok_limit:,} restantes ({tok_pct:.1f}% livre)"
        else:
            tok_line = "  • Tokens/min: informações não disponíveis"

        # Requests per day
        day_limit = day.get("limit")
        day_remain = day.get("remaining")
        if day_limit is not None and day_remain is not None:
            day_pct = (day_remain / day_limit * 100) if day_limit > 0 else 0
            day_line = f"  • Requisições/dia: {day_remain:,}/{day_limit:,} restantes ({day_pct:.1f}% livre)"
        else:
            day_line = "  • Requisições/dia: informações não disponíveis"

        # Overall status
        if req_limit is not None and req_remain is not None:
            if req_pct < 10:
                status = "⚠️ **ATENÇÃO**: Limite de requisições/min crítica (<10% livre)"
            elif req_pct < 30:
                status = "⚡ **CUIDADO**: Limite de requisições/min baixo (<30% livre)"
            else:
                status = "✅ **OK**: Limites dentro da normalidade"
        else:
            status = "ℹ️ **INFO**: OpenRouter não expôs limites detalhados para esta chave"

        report = f"""📊 **Relatório de Limites OpenRouter**
🔑 Chave: `{label}`

**Limites atuais:**
{req_line}
{tok_line}
{day_line}

**Status:** {status}

---
*Verificação automática a cada 30 min via Hermes cron*"""
        print(report)
        return 0
    else:
        print(f"❌ OpenRouter API erro {resp.status_code}: {resp.text[:200]}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
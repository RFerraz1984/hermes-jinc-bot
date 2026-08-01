#!/usr/bin/env python3
"""
OpenRouter Credit & Rate Limit Watchdog.
Checks both rate limits (requests/min, tokens/min) AND credit balance/spending.
Exits silently if no key configured; prints natural language report on success;
prints error on failure. Designed for Hermes cron with no_agent=True.
"""
import os
import sys
import json
import requests
from datetime import datetime

def load_env_file(path="/opt/data/.env"):
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        pass

def fmt_brl(val):
    """Format number as BRL currency string."""
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def main():
    load_env_file()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return 0

    headers = {"Authorization": f"Bearer {api_key}"}
    base = "https://openrouter.ai/api/v1"

    # 1. Rate limits + key metadata (usage, limit, limit_remaining)
    try:
        r_key = requests.get(f"{base}/auth/key", headers=headers, timeout=10)
    except Exception as e:
        print(f"❌ Erro de rede ao consultar OpenRouter (auth/key): {e}")
        return 1

    if r_key.status_code != 200:
        print(f"❌ OpenRouter API erro {r_key.status_code}: {r_key.text[:200]}")
        return 1

    key_data = r_key.json()
    data = key_data.get("data", {})
    label = data.get("label") or "Chave sem label"
    rate = data.get("rate_limit", {})
    req = rate.get("requests", {})
    tok = rate.get("tokens", {})
    day = rate.get("requests_per_day", {})

    # Credit limit fields (per OpenRouter API docs)
    credit_limit = data.get("limit")           # total credit limit for key (or null = unlimited)
    credit_remaining = data.get("limit_remaining")  # remaining credits
    credit_used_total = data.get("usage")      # all-time usage
    credit_used_daily = data.get("usage_daily") # current UTC day usage
    credit_used_weekly = data.get("usage_weekly")
    credit_used_monthly = data.get("usage_monthly")

    # 2. Credits endpoint (account-wide balance)
    try:
        r_cred = requests.get(f"{base}/credits", headers=headers, timeout=10)
        cred_data = r_cred.json() if r_cred.status_code == 200 else {}
    except Exception:
        cred_data = {}

    total_credits = cred_data.get("total_credits") or cred_data.get("data", {}).get("total_credits")
    used_credits = cred_data.get("used_credits") or cred_data.get("data", {}).get("used_credits")
    remaining_credits = cred_data.get("remaining_credits") or cred_data.get("data", {}).get("remaining_credits")

    # Build report
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [f"📊 **Relatório OpenRouter** — {ts}", f"🔑 Chave: `{label}`", ""]

    # --- Rate Limits ---
    lines.append("**⏱️ Rate Limits (requisições/tokens por minuto):**")
    for name, bucket in [("Requisições/min", req), ("Tokens/min", tok)]:
        lim = bucket.get("limit")
        rem = bucket.get("remaining")
        if lim is not None and rem is not None:
            pct = (rem / lim * 100) if lim > 0 else 0
            if pct < 10:
                flag = " 🔴"
            elif pct < 30:
                flag = " 🟡"
            else:
                flag = " 🟢"
            lines.append(f"  • {name}: {rem:,}/{lim:,} livres ({pct:.1f}%){flag}")
        else:
            lines.append(f"  • {name}: informações não disponíveis")

    # --- Credit Limits (per-key) ---
    lines.append("")
    lines.append("**💰 Limite de Créditos (por chave):**")
    if credit_limit is not None:
        limit_str = f"${credit_limit:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        rem_str = f"${credit_remaining:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        used_str = f"${credit_used_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        daily_str = f"${credit_used_daily:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        pct = (credit_remaining / credit_limit * 100) if credit_limit > 0 else 0
        if pct < 10:
            flag = " 🔴 **CRÍTICO**"
        elif pct < 30:
            flag = " 🟡 **ATENÇÃO**"
        else:
            flag = " 🟢"
        lines.append(f"  • Limite total: {limit_str}")
        lines.append(f"  • Restante: {rem_str} ({pct:.1f}%){flag}")
        lines.append(f"  • Gasto total (histórico): {used_str}")
        lines.append(f"  • Gasto hoje (UTC): {daily_str}")
        if credit_used_weekly is not None:
            wk_str = f"${credit_used_weekly:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            lines.append(f"  • Gasto semana: {wk_str}")
        if credit_used_monthly is not None:
            mo_str = f"${credit_used_monthly:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            lines.append(f"  • Gasto mês: {mo_str}")
    else:
        lines.append("  • Sem limite configurado (ilimitado ou não exposto)")

    # --- Account Credits (global) ---
    if total_credits is not None:
        lines.append("")
        lines.append("**🏦 Saldo da Conta (global):**")
        tot = f"${total_credits:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        rem = f"${remaining_credits:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        used = f"${used_credits:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        lines.append(f"  • Créditos totais: {tot}")
        lines.append(f"  • Restante: {rem}")
        lines.append(f"  • Usado: {used}")

    # --- Alertas ---
    alerts = []
    if credit_limit is not None and credit_remaining is not None:
        if credit_remaining <= 0:
            alerts.append("🚨 **CRÉDITOS ESGOTADOS** — a chave não fará mais requisições pagas")
        elif credit_limit > 0 and (credit_remaining / credit_limit) < 0.1:
            alerts.append("⚠️ Menos de 10% do limite restante — considere recarregar ou trocar modelo")

    if total_credits is not None and remaining_credits is not None:
        if remaining_credits <= 0:
            alerts.append("🚨 **SALDO DA CONTA ZERADO** — recarregue em openrouter.ai/credits")
        elif total_credits > 0 and (remaining_credits / total_credits) < 0.15:
            alerts.append("⚠️ Saldo da conta abaixo de 15% — recarga recomendada")

    if alerts:
        lines.append("")
        lines.append("**🚨 ALERTAS:**")
        for a in alerts:
            lines.append(f"  {a}")

    lines.append("")
    lines.append("---")
    lines.append("*Verificação automática a cada 30 min via Hermes cron*")

    print("\n".join(lines))
    return 0

if __name__ == "__main__":
    sys.exit(main())
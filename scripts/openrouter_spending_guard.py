#!/usr/bin/env python3
"""
OpenRouter Spending Guard — verifica créditos e ENFORÇA limite de gasto.
- Consulta /api/v1/credits (saldo total) e /api/v1/auth/key (limite por chave + gasto diário)
- Se gasto diário > LIMITE_DIARIO_USD ou saldo < LIMITE_SALDO_MINIMO: BLOQUEIA modelos caros
- Bloqueio = altera config.yaml para forçar modelo free/barato (nemotron-3-ultra, etc.)
- Reverte automaticamente quando gasto volta ao normal (histerese)
"""
import os
import sys
import json
import requests
import subprocess
from pathlib import Path

# ============ CONFIGURAÇÃO (ajuste conforme sua realidade) ============
LIMITE_DIARIO_USD = 5.00      # Alerta/bloqueio se gasto diário > $5
LIMITE_SALDO_MINIMO = 10.00   # Alerta se saldo total < $10
LIMITE_CRITICO_USD = 20.00    # Bloqueio duro se gasto diário > $20

# Modelos por tier de custo (ordem de preferência quando bloqueado)
MODELOS_BLOQUEIO = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",  # Free tier
    "google/gemma-2-9b-it:free",                # Free
    "meta-llama/llama-3.1-8b-instruct:free",    # Free
]

MODELOS_NORMAL = "openrouter/auto"  # Seu modelo preferido normal (ex: anthropic/claude-sonnet-4)

CONFIG_YAML = Path("/opt/data/config.yaml")
ENV_FILE = Path("/opt/data/.env")
STATE_FILE = Path("/opt/data/openrouter_spending_state.json")

# ===================================================================

def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

def get_credits(api_key):
    """GET /api/v1/credits — saldo total da conta"""
    r = requests.get("https://openrouter.ai/api/v1/credits",
                     headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
    r.raise_for_status()
    return r.json().get("data", {})

def get_key_info(api_key):
    """GET /api/v1/auth/key — limites + gasto diário/semanal/mensal da chave"""
    r = requests.get("https://openrouter.ai/api/v1/auth/key",
                     headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
    r.raise_for_status()
    return r.json().get("data", {})

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {"blocked": False, "last_action": None}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def get_current_model():
    """Lê model.default do config.yaml"""
    try:
        import yaml
        cfg = yaml.safe_load(CONFIG_YAML.read_text())
        return cfg.get("model", {}).get("default", "")
    except:
        return ""

def set_model(new_model):
    """Altera model.default no config.yaml via hermes config set"""
    try:
        result = subprocess.run(["/opt/hermes/bin/hermes", "config", "set", "model.default", new_model],
                                capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception as e:
        print(f"Erro ao alterar modelo: {e}", file=sys.stderr)
        return False

def main():
    load_env()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY não configurado", file=sys.stderr)
        return 0  # silent exit

    state = load_state()
    now = __import__("datetime").datetime.utcnow().isoformat() + "Z"

    try:
        # 1. Saldo total da conta
        credits = get_credits(api_key)
        total_credits = credits.get("total_credits", 0)
        used_credits = credits.get("used_credits", 0)
        remaining = total_credits - used_credits

        # 2. Info da chave (limites + gasto diário)
        key_info = get_key_info(api_key)
        daily_usage = key_info.get("usage_daily", 0)
        # daily_usage vem em créditos OpenRouter (1 crédito = $1 USD aprox)
        # Confirmar: OpenRouter usa 1 crédito = $1

        print(f"📊 **OpenRouter Spending Guard** — {now[:19]}")
        print(f"💰 Saldo: ${remaining:.2f} / ${total_credits:.2f} (usado: ${used_credits:.2f})")
        print(f"📅 Gasto hoje: ${daily_usage:.2f}")

        # 3. Decisão de bloqueio/desbloqueio
        current_model = get_current_model()
        should_block = False
        reason = ""

        if daily_usage >= LIMITE_CRITICO_USD:
            should_block = True
            reason = f"Gasto diário ${daily_usage:.2f} > LIMITE CRÍTICO ${LIMITE_CRITICO_USD:.2f}"
        elif daily_usage >= LIMITE_DIARIO_USD:
            should_block = True
            reason = f"Gasto diário ${daily_usage:.2f} > LIMITE DIÁRIO ${LIMITE_DIARIO_USD:.2f}"
        elif remaining < LIMITE_SALDO_MINIMO:
            should_block = True
            reason = f"Saldo ${remaining:.2f} < MÍNIMO ${LIMITE_SALDO_MINIMO:.2f}"

        # Histerese: só desbloqueia se gasto caiu bem abaixo do limite
        if state.get("blocked") and daily_usage < LIMITE_DIARIO_USD * 0.5 and remaining > LIMITE_SALDO_MINIMO * 1.5:
            should_block = False
            reason = "Recuperação: gasto caiu para 50% do limite + saldo OK"

        # 4. Aplicar ação
        action_taken = None
        if should_block and not state.get("blocked"):
            # BLOQUEAR — forçar modelo free
            for m in MODELOS_BLOQUEIO:
                if set_model(m):
                    action_taken = f"🔒 **BLOQUEADO** — Modelo forçado para: `{m}`"
                    state["blocked"] = True
                    state["previous_model"] = current_model
                    break
            if not action_taken:
                action_taken = "❌ Falha ao forçar modelo free"
        elif not should_block and state.get("blocked"):
            # DESBLOQUEAR — restaurar modelo anterior ou normal
            restore_model = state.get("previous_model") or MODELOS_NORMAL
            if set_model(restore_model):
                action_taken = f"🔓 **DESBLOQUEADO** — Modelo restaurado: `{restore_model}`"
                state["blocked"] = False
                state["previous_model"] = None
            else:
                action_taken = "❌ Falha ao restaurar modelo"

        state["last_check"] = now
        state["last_daily_usage"] = daily_usage
        state["last_remaining"] = remaining
        if action_taken:
            state["last_action"] = action_taken
        save_state(state)

        # 5. Output para Telegram (apenas se houver ação ou alerta)
        if action_taken or daily_usage >= LIMITE_DIARIO_USD * 0.8 or remaining < LIMITE_SALDO_MINIMO * 1.5:
            lines = [
                f"🛡️ **OpenRouter Spending Guard** — {now[:19]}",
                f"💰 Saldo: **${remaining:.2f}** / ${total_credits:.2f}",
                f"📅 Gasto hoje: **${daily_usage:.2f}**",
                f"🤖 Modelo atual: `{current_model}`",
                f"⚙️ Limites: diário ≤${LIMITE_DIARIO_USD:.0f} | crítico ${LIMITE_CRITICO_USD:.0f} | saldo mín ${LIMITE_SALDO_MINIMO:.0f}",
            ]
            if action_taken:
                lines.append(f"\n{action_taken}")
            elif daily_usage >= LIMITE_DIARIO_USD * 0.8:
                lines.append(f"\n⚡ **CUIDADO**: Gasto diário a {daily_usage/LIMITE_DIARIO_USD*100:.0f}% do limite")
            elif remaining < LIMITE_SALDO_MINIMO * 1.5:
                lines.append(f"\n⚡ **CUIDADO**: Saldo a ${remaining:.2f} (mínimo ${LIMITE_SALDO_MINIMO:.0f})")
            else:
                lines.append("\n✅ **OK**: Dentro dos parâmetros")

            lines.append("\n---\n*Verificação automática a cada 30 min via Hermes cron*")
            print("\n".join(lines))

        return 0

    except requests.RequestException as e:
        print(f"❌ Erro de rede OpenRouter: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Erro inesperado: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
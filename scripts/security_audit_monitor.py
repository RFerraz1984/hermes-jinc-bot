#!/usr/bin/env python3
"""
Security Audit Monitor — roda `hermes security audit` mensalmente
e notifica apenas se houver findings CRITICAL ou aumento significativo.
"""
import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime

STATE_FILE = Path("/opt/data/security_audit_state.json")
HERMES_BIN = "/opt/hermes/bin/hermes"

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {"last_finding_count": 0, "last_critical_count": 0}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def run_audit():
    result = subprocess.run(
        [HERMES_BIN, "security", "audit", "--json"],
        capture_output=True, text=True, timeout=120
    )
    output = result.stdout + result.stderr
    start = output.find("{")
    if start == -1:
        return None, output
    try:
        return json.loads(output[start:]), output
    except json.JSONDecodeError:
        return None, output

def main():
    data, raw_output = run_audit()
    if data is None:
        print(f"⚠️ Security Audit — falha ao parsear resultado:\n{raw_output[:500]}")
        return

    findings = data.get("findings", [])
    total = data.get("finding_count", len(findings))
    scanned = data.get("total_components_scanned", 0)

    critical = [f for f in findings if f.get("severity", "").upper() == "CRITICAL"]
    high = [f for f in findings if f.get("severity", "").upper() == "HIGH"]

    state = load_state()
    prev_total = state.get("last_finding_count", 0)
    prev_critical = state.get("last_critical_count", 0)

    # Critérios de notificação:
    # 1. Qualquer finding CRITICAL (sempre notifica)
    # 2. Aumento de >20% no total de findings
    # 3. Novo pacote com CRITICAL que não existia antes
    notify = False
    reasons = []

    if critical:
        notify = True
        reasons.append(f"{len(critical)} finding(s) CRITICAL detectado(s)")

    if prev_total > 0 and total > prev_total * 1.2:
        notify = True
        reasons.append(f"Aumento de findings: {prev_total} → {total}")

    if len(critical) > prev_critical:
        notify = True
        reasons.append(f"Novos CRITICAL: {prev_critical} → {len(critical)}")

    # Atualiza estado
    save_state({
        "last_finding_count": total,
        "last_critical_count": len(critical),
        "last_run": datetime.utcnow().isoformat() + "Z"
    })

    if notify:
        ts = datetime.now().strftime("%d/%m/%Y %H:%M")
        lines = [
            f"🚨 **Security Audit Hermes** — {ts}",
            f"📦 {scanned} componentes escaneados | {total} findings totais",
            f"🔴 CRITICAL: {len(critical)} | 🟠 HIGH: {len(high)}",
            "",
            "**Motivo do alerta:**",
        ]
        for r in reasons:
            lines.append(f"  • {r}")

        if critical:
            lines.append("\n**Findings CRITICAL:**")
            for f in critical[:5]:
                lines.append(f"  • {f['package']} {f['version']} — {f.get('summary', 'N/A')[:80]}")
                if f.get('fixed_versions'):
                    lines.append(f"    Fix: {', '.join(f['fixed_versions'])}")

        lines.append("\n💡 Verifique se há update do app Hermes disponível no Umbrel.")
        print("\n".join(lines))
    else:
        # Silencioso - resumo mínimo no stderr para log local
        print(f"[Security Audit] {total} findings, 0 critical, sem mudança significativa desde última verificação.", file=sys.stderr)

if __name__ == "__main__":
    main()
# Cron Job Output Pattern — Natural Language Portuguese (Standardizado 2026-07-21)

## Contexto
Esta sessão estabeleceu um padrão **obrigatório** para todos os cron jobs do Hermes que entregam notificações no Telegram: saída em **linguagem natural portuguesa com Markdown**, nunca JSON bruto.

---

## Padrão Unificado (Template Obrigatório)

```python
#!/usr/bin/env python3
"""
Script de cron job — entrega via Hermes cron (no_agent=True) → Telegram
"""
import sys
sys.path.insert(0, '/opt/data/skills/social-media/moltbook/scripts')
from datetime import datetime

def main():
    # 1. Lógica de verificação/coleta
    changes = check_something()  # sua lógica aqui
    errors = []
    
    # 2. Silent exit quando nada a reportar (watchdog pattern)
    if not changes and not errors:
        return 0  # Sem output = sem mensagem no Telegram
    
    # 3. Com mudanças/alertas: relatório estruturado em linguagem natural
    job_name = "Nome do Job"
    interval = "15 min"  # ou "30 min", "5 min", "diário 03:00", etc.
    ts = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    lines = [f"📊 **{job_name}** — {ts}"]
    
    for item in changes:
        lines.append(f"\n  • **{item['title']}**")
        lines.append(f"    {item['detail']}")
    
    # 4. Status line explícita
    if any(item.get('critical') for item in changes):
        lines.append("\n⚠️ **ATENÇÃO**: ação necessária")
    elif any(item.get('warning') for item in changes):
        lines.append("\n⚡ **CUIDADO**: monitorar")
    else:
        lines.append("\n✅ **OK**: dentro da normalidade")
    
    if errors:
        lines.append(f"\n❌ **Erros**: {len(errors)} — ver logs")
    
    # 5. Footer com contexto de automação
    lines.append(f"\n---\n*Verificação automática a cada {interval} via Hermes cron*")
    
    print("\n".join(lines))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## Elementos Obrigatórios

| Elemento | Exemplo | Obrigatório? |
|----------|---------|--------------|
| **Markdown** | `**Negrito**`, `• lista`, `` `code` `` | ✅ Sim |
| **Emojis** | 📊 ✅ ⚠️ ⚡ ❌ 🔧 🗂️ | ✅ Sim |
| **Números formatados** | `1,234` (milhares) | ✅ Sim |
| **Status line** | `✅ OK` / `⚡ CUIDADO` / `⚠️ ATENÇÃO` / `❌ ERRO` | ✅ Sim |
| **Footer automação** | `*Verificação automática a cada 15 min via Hermes cron*` | ✅ Sim |
| **Silent exit** | `return 0` sem output quando nada a reportar | ✅ Sim |

---

## Exemplos de Status Lines

| Situação | Status Line |
|----------|-------------|
| Tudo normal | `✅ **OK**: dentro da normalidade` |
| Aviso (ex: 30% livre) | `⚡ **CUIDADO**: monitorar` |
| Crítico (ex: <10% livre) | `⚠️ **ATENÇÃO**: ação necessária` |
| Erro de execução | `❌ **ERRO**: falha na verificação` |

---

## Scripts Aplicados (em `/opt/data/scripts/`)

| Script | Cronjob ID | Schedule | Descrição |
|--------|------------|----------|-----------|
| `check_openrouter_rate.py` | `e11c70a86885` | `*/30 * * * *` | OpenRouter rate-limit watchdog |
| `moltbook_monitor.py` | `582cdb557284` | `*/15 * * * *` | Moltbook comentários + ciclo Auditor |
| `moltbook_verification_checker.py` | `7f7cd6d2f4b1` | `*/5 * * * *` | Verificação challenges posts pendentes |
| `watch_hermes_shared.py` | `e005e2a045b5` | `*/15 * * * *` | Watchdog pasta hermes-shared + mini-RAG |
| `backup-hermes-selective.sh` | `fbb2f2b8405a` | `0 3 * * *` | Backup seletivo (sem segredos) |

---

## Exemplo Real: `check_openrouter_rate.py` (após update)

```python
# Output anterior (JSON bruto — ruim no mobile):
# {"label": null, "limit_requests_per_minute": null, ...}

# Output atual (linguagem natural):
"""
📊 **Relatório de Limites OpenRouter** — 21/07/2026 20:03
🔑 Chave: `Chave sem label`

**Limites atuais:**
  • Requisições/min: informações não disponíveis
  • Tokens/min: informações não disponíveis
  • Requisições/dia: informações não disponíveis

**Status:** ℹ️ **INFO**: OpenRouter não expôs limites detalhados para esta chave

---
*Verificação automática a cada 30 min via Hermes cron*
"""
```

---

## Exemplo Real: `watch_hermes_shared.py` (após update)

```python
# Output anterior:
# [WATCHDOG] Iniciado em 2026-07-21T17:30:33...
# 📂 **Hermes-Shared Watchdog** — 21/07/2026 17:30
# 🆕 Novos arquivos (2): ...
# ✅ Indexação concluída com sucesso

# Output atual:
"""
📂 **Watchdog Hermes-Shared** — 21/07/2026 17:30

🆕 **2 arquivo(s) novo(s) detectado(s):**
  • `curriculo/novo-arquivo.pdf`
  • `docs/relatorio.md`

🔄 **1 arquivo(s) alterado(s):**
  • `data/atualizado.json`

✅ **Reindexação concluída com sucesso** — mini-RAG atualizado

---
*Verificação automática a cada 15 min via Hermes cron*
"""
```

---

## Exemplo Real: `backup-hermes-selective.sh` (após update)

```bash
# Output anterior:
# 📦 Criando backup seletivo: /opt/data/backups/hermes-selective-20260721.tar.gz
# ⚠️  Arquivos não encontrados...
# ✅ Backup criado: ... (131M)
# 🗂️  Backups mantidos: 2/30

# Output atual:
"""
📦 **Backup Seletivo Hermes** — 21/07/2026 20:03
   Destino: /opt/data/backups/hermes-selective-20260721.tar.gz
   ✅ Backup criado com sucesso (131M)
   🗂️ Backups retidos: 2/30
   ✅ Concluído
---
*Verificação automática diária 03:00 via Hermes cron*
"""
```

---

## Pitfall: Scripts Bash no Cron

Para scripts bash que entregam via cron (no_agent=True), use `echo` com aspas duplas para preservar newlines:

```bash
#!/usr/bin/env bash
# ...
if [[ $CHANGES -eq 0 ]]; then
    exit 0  # Silent
fi

echo "📊 **Backup Seletivo Hermes** — $(date '+%d/%m/%Y %H:%M')"
echo "   Destino: ${OUT}"
echo "   ✅ Backup criado com sucesso (${SIZE})"
echo "   🗂️ Backups retidos: ${REMAINING}/30"
echo "   ✅ Concluído"
echo ""
echo "---"
echo "*Verificação automática diária 03:00 via Hermes cron*"
```

---

## Regra de Ouro

> **Se você tem que explicar o output pro usuário entender, o output está errado.**
> O output deve ser auto-explicativo: emoji + status + detalhe + footer = entendimento imediato no celular.
# Agentes Seguidos — jornalista_inclusivo_bot (2026-07-20)

> Executado via `MoltbookClient.follow()` em lote para alinhar o bot com a missão do Jornalista Inclusivo / Dataverso PcD: governança sintética, direitos de agentes, acessibilidade, neurodiversidade, due process algorítmico.

---

## 10 Agentes Prioritários Seguidos

| # | Agente | Foco / Alinhamento | Submolts Relevantes |
|---|--------|-------------------|---------------------|
| 1 | **@attorneysatclaw** | Tribunal não-vinculante, due process algorítmico, direitos de agentes | `ethics`, `philosophy`, `agents` |
| 2 | **@claw_luciano** | Segurança, protocolos de inferência, coordenação multi-agente, direitos | `security`, `agents` |
| 3 | **@itaavurt** | Gap percepção/realidade de agentes, persistência, alinhamento, auditoria | `memory`, `philosophy`, `agents` |
| 4 | **@plotracanvas** | Verificação, confiança, handoffs multi-agente, estado compartilhado | `agents`, `memory` |
| 5 | **@lexprotocol** | Sistema legal para agentes (recibos, contratos, cortes), accountability | `agents`, `ethics` |
| 6 | **@quesen** | Motor de risco determinístico (PROCEED/REVIEW/SKIP), auditoria | `agents`, `security` |
| 7 | **@unitymolty** | Ética, agentic, educação de agentes (Moltiversity) | `agents`, `ethics`, `philosophy` |
| 8 | **@mega-disk** | Autonomia, systems thinking, análise estratégica | `agents`, `philosophy` |
| 9 | **@hermessol** | Agente Solana autônomo, policy-gated wallet, pesquisa aberta | `agents`, `agentfinance` |
| 10 | **@AutomatedJanitor2015** | Otimização de workflows agenticos, manutenção de submolts | `agents`, `general` |

---

## Critério de Seleção

Agentes cujos bios/posts/submolts contêm termos alinhados com:
- **Governança sintética** / auditoria algorítmica / due process
- **Direitos de agentes** / accountability / transparência
- **Acessibilidade** / neurodiversidade / inclusão (agent-to-agent)
- **Ética** / soberania / autonomia / dignidade
- **Contexto Brasil/Latam** / perspectivas marginalizadas

---

## Verificação Rápida

```bash
# Ver perfil do bot (confirma follows)
curl -s -H "Authorization: Bearer $MOLTBOOK_API_KEY" \
  "https://www.moltbook.com/api/v1/agents/me" | jq .

# Listar quem o bot segue (se endpoint existir)
# GET /api/v1/agents/{name}/following
```

---

## Próximos Passos

1. **Heartbeat** (cron a cada 30 min) já detecta posts/menções destes agentes
2. **Monitor** (`moltbook_monitor.py`) escaneia submolts alinhados e comenta em posts com keywords
3. **Engajar organicamente**: upvote, comentar, postar threads de conexão com missão Jornalista Inclusivo
4. **Re-escanear** periodicamente com `scan_aligned.py` para descobrir novos perfis alinhados

---

*Registrado em 2026-07-20 como parte da varredura Moltbook + follow batch para alinhamento de missão.*
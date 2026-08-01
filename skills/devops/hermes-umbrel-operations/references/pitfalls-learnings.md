### ⚠️ Critical: Telegram Bot Token Troubleshooting (Added 2026-07-05)

**Sintoma:** `telegram.error.InvalidToken: The token \`876079...WpOY\` was rejected by the server`

**Causas possíveis:**
1. Token revogado no @BotFather
2. Bot deletado/recriado
3. Token copiado incorretamente (truncado nos logs)

**Diagnóstico:**
```bash
# Testar token direto
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"

# Ver erros recentes no gateway
grep -c "$(date +%Y-%m-%d).*InvalidToken" /opt/data/logs/gateway.log
```

**Fix:**
1. Gerar novo token no @BotFather (`/mybots` → Bot → API Token → Revoke & Get new)
2. Atualizar no Umbrel: Settings → Hermes → Env vars → `TELEGRAM_BOT_TOKEN`
3. Reiniciar app Hermes no Umbrel (não só gateway)
4. Verificar logs: `✓ telegram connected`

---

### ⚠️ Tavily MCP OAuth Fails in Containerized Hermes (Added 2026-07-28)

**Sintoma:**
```
MCP OAuth for 'tavily': non-interactive environment and no cached tokens found.
Run `hermes mcp login tavily` interactively first to complete initial authorization.
```

**Causa:** `config.yaml` tem `mcp_servers.tavily.auth: oauth` mas container Hermes não tem browser/TTY para fluxo OAuth interativo.

**Config problemática:**
```yaml
tavily:
  auth: oauth
  enabled: true
  url: https://mcp.tavily.com/mcp/
  headers:
    Authorization: Bearer ***  # placeholder, não funciona com OAuth
```

**Soluções (ordem de preferência):**
1. **API Key direta** — se tem `TAVILY_API_KEY`: mudar `auth: none` + header `Authorization: Bearer $TAVILY_API_KEY`
2. **Desabilitar** — `enabled: false` no config.yaml (para erro imediato)
3. **Login interativo** — `hermes mcp login tavily` em terminal anexado (token expira, não recomendado para cron)

**Ação recomendada:** Verificar se `TAVILY_API_KEY` existe em `/opt/data/.env` e migrar para auth none.

**Padrão geral:** Qualquer MCP server configurado com `auth: oauth` falhará em ambiente headless/containerizado sem browser. Prefira `auth: none` + API key via header, ou desabilite se não crítico.
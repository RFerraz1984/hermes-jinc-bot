# Cron Jobs JINC — Referência rápida

## Jobs ativos (criados nesta sessão)

| Job ID | Nome | Schedule | Entrega | Tipo |
|--------|------|----------|---------|------|
| `12d59b921ae1` | JINC Gmail triagem-15d | `0 9 * * *` (diário 09:00) | `origin,telegram` | **PAUSADO** — aguarda `imap-config.json` com credenciais reais |
| `e11c70a86885` | OpenRouter rate-limit watchdog | `*/30 * * * *` (a cada 30 min) | `telegram` | `no_agent` — script `check_openrouter_rate.py` |
| `fbb2f2b8405a` | Backup seletivo Hermes | `0 3 * * *` (diário 03:00) | `telegram` | `no_agent` — script `backup-hermes-selective.sh` |
| `0528ad2c657b` | Lembrete rotação credenciais | `0 9 1 * *` (dia 1, 09:00) | `telegram` | `no_agent` — script `cred-rotation-reminder.sh` |

## Comandos úteis

```bash
# Listar todos
/opt/hermes/bin/hermes cron list --all

# Rodar job agora (teste)
/opt/hermes/bin/hermes cron run <JOB_ID>

# Pausar / retomar
/opt/hermes/bin/hermes cron pause <JOB_ID>
/opt/hermes/bin/hermes cron resume <JOB_ID>

# Ver detalhes
/opt/hermes/bin/hermes cron status
```

## Job de triagem Gmail (12d59b921ae1) — Como ativar

1. Editar `/opt/data/journali/imap-config.json` com credenciais reais:
   ```json
   {
     "host": "imap.gmail.com",
     "port": 993,
     "username": "seu_email@gmail.com",
     "password": "APP_PASSWORD_AQUI",
     "search_folder": "INBOX"
   }
   ```
2. Testar conectividade:
   ```bash
   openssl s_client -connect imap.gmail.com:993 -quiet
   ```
3. Despausar:
   ```bash
   /opt/hermes/bin/hermes cron resume 12d59b921ae1
   ```
4. Testar run imediato:
   ```bash
   /opt/hermes/bin/hermes cron run 12d59b921ae1
   ```

## Jobs de manutenção (already existing)

- `8cb9105b3256` — monthly-backup-pattern-b (script `monthly-backup.py`, 02:00 dia 1)
- `283c46f524cf` — daily-security-check-pattern-b (script `security-daily-check.py`, 11:30 diário)
- `3d75d014af16` / `d236bd0ed731` — moltbook heartbeats (a cada 30 min)
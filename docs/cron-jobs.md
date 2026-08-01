# Cron Jobs - Hermes JINC Bot

> Exportado em: 2026-08-01
> Total: 14 jobs (14 ativos, 0 pausados)

---

## Jobs Ativos

| Job ID | Nome | Schedule | Script | Deliver | Workdir | Status |
|--------|------|----------|--------|---------|---------|--------|
| `8cb9105b3256` | monthly-backup-pattern-b | `0 2 1 * * *` | `monthly-backup.py` | telegram | `/opt/data` | active |
| `283c46f524cf` | daily-security-check-pattern-b | `30 11 * * *` | `security-daily-check.py` | telegram | `/opt/data` | active |
| `12d59b921ae1` | **JINC Gmail triagem-15d** | `0 12,17,21 * * *` | `jinc_gmail_triagem_15d_filtered.py` | origin,telegram | `/opt/data` | active |
| `3d75d014af16` | Moltbook Heartbeat | `0 */4 * * *` | `moltbook_heartbeat_wrapper.sh` | origin | `/opt/data` | active |
| `e11c70a86885` | OpenRouter rate-limit watchdog | `*/30 * * * *` | `check_openrouter_rate_filtered.sh` | telegram | `/opt/data` | active |
| `fbb2f2b8405a` | Backup seletivo Hermes | `0 3 * * *` | `backup-hermes-daily.sh` | telegram | `/opt/data` | active |
| `0528ad2c657b` | Lembrete rotação credenciais | `0 9 1 * *` | `cred-rotation-reminder.sh` | telegram | `/opt/data` | active |
| `e005e2a045b5` | Watchdog hermes-shared | `*/15 * * * *` | `watch_hermes_shared_filtered.py` | telegram | `/opt/data` | active |
| `582cdb557284` | Moltbook Monitor | `0 */2 * * *` | `moltbook_monitor_filtered.py` | telegram | `/opt/data` | active |
| `7f7cd6d2f4b1` | Moltbook Verification Checker | `*/15 * * * *` | `moltbook_verification_checker_filtered.py` | telegram | `/opt/data` | active |
| `3fd1a5f9fd27` | Security Audit Monitor | `0 8 * * 1` | `security_audit_monitor.py` | telegram | `/opt/data` | active |
| `70eb5f1891e5` | Ollama Warmup | `*/5 * * * *` | `warmup-ollama.sh` | local | `/opt/data` | active |
| `dc3e5a9edccf` | audit-weekly-deep | `0 2 * * 1` | `audit_cron_wrapper.sh` | telegram:965862678 | `/opt/data` | active |
| `0ae4f4b5fe35` | audit-legislative | `0 6 * * 2,4` | `audit_cron_legislative_wrapper.sh` | telegram:965862678 | `/opt/data` | active |

---

## Legenda

- **origin** = chat de origem (Telegram DM)
- **telegram** = canal Home (chat_id 965862678)
- **local** = apenas arquivo local, sem notificação
- Scripts com sufixo `_filtered` usam `smart_notify_filter.py` para deduplicação de notificações


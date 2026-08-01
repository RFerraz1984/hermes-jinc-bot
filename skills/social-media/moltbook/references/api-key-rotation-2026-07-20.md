# Rotação de API Key Moltbook — 2026-07-20

## Contexto
Key antiga (`moltbook_sk_7lPJYqAkI6z1Ov992JjxCM5EmuOjCXqk`) exposta em logs/cron outputs. Rotacionada para `moltbook_sk_6NAxZLKi59xleOBctYQ5VhlYHVW6e6nV`.

## Procedimento Validado

### 1. Gerar nova key no Owner Dashboard (Moltbook)
1. https://www.moltbook.com → "👤 I'm a Human" → login por magic link
2. Owner Dashboard → Agents → `jornalista_inclusivo_bot`
3. Seção "API Key" → **Revoke** → **Generate New API Key**
4. Copiar nova key (mostrada uma vez) → salvar no gerenciador de senhas

### 2. Atualizar arquivo de credenciais local
```bash
# Via script helper (faz backup + update + chmod 600)
/opt/data/scripts/update_moltbook_key.sh "moltbook_sk_6NAxZLKi59xleOBctYQ5VhlYHVW6e6nV"

# Ou manualmente (preservando outros campos):
# Edite /opt/data/moltbook_ethos_tracker.json → campo "api_key"
chmod 600 /opt/data/moltbook_ethos_tracker.json
```

### 3. Validar
```bash
python3 /opt/data/skills/social-media/moltbook/scripts/moltbook_helpers.py status
# Esperado: {"success":true,"status":"claimed",...}
```

### 4. Limpar segredos antigos (logs, cron outputs, sessions)
```bash
# Key antiga
find /opt/data -type f \( -name "*.md" -o -name "*.json" -o -name "*.py" -o -name "*.log" -o -name "*.txt" \) \
  -exec grep -l "moltbook_sk_7lPJYqAkI6z1Ov992JjxCM5EmuOjCXqk" {} \; \
  -exec sed -i 's/moltbook_sk_7lPJYqAkI6z1Ov992JjxCM5EmuOjCXqk/<REDACTED_MOLTBOOK_API_KEY>/g' {} \;

# Verification code
find /opt/data -type f \( -name "*.md" -o -name "*.json" -o -name "*.py" -o -name "*.log" -o -name "*.txt" \) \
  -exec grep -l "bay-2P6A" {} \; \
  -exec sed -i 's/bay-2P6A/<REDACTED_VERIFICATION_CODE>/g' {} \;

# Claim URL
find /opt/data -type f \( -name "*.md" -o -name "*.json" -o -name "*.py" -o -name "*.log" -o -name "*.txt" \) \
  -exec grep -l "moltbook_claim_I9sh763vbTSyT2YZ2FHX02OW9iR6I9gn" {} \; \
  -exec sed -i 's#https://www.moltbook.com/claim/moltbook_claim_I9sh763vbTSyT2YZ2FHX02OW9iR6I9gn#<REDACTED_CLAIM_URL>#g' {} \;
```

### 5. Sanitizar documentação e scripts
- `SKILL.md` → placeholders no JSON de exemplo
- `references/api_session_2026-07-19.md` → placeholders
- `post_*.py` → leem key de `/opt/data/moltbook_ethos_tracker.json` (não hardcoded)

### 6. Reiniciar gateway Hermes (host Umbrel)
Settings → Apps → Hermes Agent → **Restart**
(Ou `systemctl --user restart hermes-gateway` via SSH no host)

## Checklist Pós-Rotação
- [x] Nova key no gerenciador de senhas
- [x] `/opt/data/moltbook_ethos_tracker.json` atualizado (chmod 600)
- [x] Validação via API → `claimed`
- [x] Logs/cron outputs limpos (120+ arquivos)
- [x] Documentação/skills sanitizadas
- [x] Gateway reiniciado
- [ ] Testar postagem real

## Lições
1. **Nunca** hardcode API keys em scripts/docs — use arquivo de credenciais (chmod 600)
2. Cron outputs acumulam segredos → rotação exige limpeza em massa
3. Gateway Hermes **não reinicia de dentro do container** — reinicie no host
4. Validação via `/agents/status` é a prova definitiva
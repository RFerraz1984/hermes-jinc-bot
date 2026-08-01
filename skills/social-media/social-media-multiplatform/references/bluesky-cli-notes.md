# Bluesky CLI Notes

## Installation & Auth Notes

Refer to main SKILL.md for full installation and auth instructions.

## Session Learnings (2025-07-03)

### CLI Login Syntax Correction
The `bsky` CLI (v0.0.81) uses **positional arguments**, not flags:
```bash
# CORRECT
HOME=/opt/data/home /opt/data/home/.local/bin/bsky login jornalistainclusivo.bsky.social i2p2-eyof-77bd-zwqh

# WRONG (flags -a/-p not defined for login subcommand)
bsky login -a handle -p password
```

### Config Location in Umbrel Container
With `HOME=/opt/data/home`, config saves to:
```
/opt/data/home/.config/bsky/config.json
```
Contents:
```json
{
  "bgs": "https://bsky.network",
  "host": "https://bsky.social",
  "handle": "inclusivo.bsky.social",
  "password": "i2p2-eyof-77bd-zwqh"
}
```

### App Password Requirement (Critical)
The password **must be an App Password** created at:
**Bluesky Settings → Privacy → App Passwords → Create**
- Name: "JINC Bot" (or similar)
- Copy the generated password (format: `xxxx-xxxx-xxxx-xxxx`)
- Regular account password **will not work**

### Session Verification
```bash
# Test login worked
HOME=/opt/data/home /opt/data/home/.local/bin/bsky show-profile jornalistainclusivo.bsky.social

# Test post
HOME=/opt/data/home /opt/data/home/.local/bin/bsky post "Teste JINC 🧵 #Acessibilidade"
```

### Bridged Account Warning (Resolved ✅)
**The native account EXISTS and works.** The handle is `inclusivo.bsky.social` (not `jornalistainclusivo.bsky.social`).
- Handle: `inclusivo.bsky.social`
- DID: `did:plc:qmruty76nvydyjcljgbha4sz`
- Display Name: "Jornalista Inclusivo"
- Description: "Protagonismo e Representatividade PCD ⤵️ 🗞Notícias: JornalistaInclusivo.com/linkdabio ✍️Docs: JornalistaInclusivo.com.br 👥️Dados: pcd.Dataverso.org"

**App Password authentication works** — this is a native Bluesky account, not a bridged account. The bridged account `jornalistainclusivo.com.web.brid.gy` (`did:plc:m7w5l7wb73dods7wdmyvr3qn`) is a separate read-only mirror.
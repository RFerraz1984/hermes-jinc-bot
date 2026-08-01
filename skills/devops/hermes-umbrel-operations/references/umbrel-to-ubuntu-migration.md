# Migração Umbrel → Ubuntu: Hermes Agent

Kit completo para mover seu Hermes Agent do Umbrel (Docker) para Ubuntu nativo ou Docker no Ubuntu.

---

## Estrutura de Arquivos Migrada

```
data/
├── config.yaml           # Config principal (ajustado)
├── .env                  # Env limpo (sem vars Umbrel)
├── auth.json             # Auth Nous Portal
├── state.db              # SQLite: sessões, kanban, jobs
├── skills/               # Skills customizadas
├── memories/             # Memórias persistentes
├── scripts/              # Scripts de cron
├── logs/                 # Logs (gui.log, gateway.log, etc.)
├── plugins/              # Plugins locais
├── cache/                # Cache (RAG, etc.)
└── cron/                 # Definições de cron jobs
```

---

## O que o Script de Migração Faz

| Ação | Detalhes |
|------|----------|
| Copia `config.yaml` | Ajusta `max_concurrent_sessions=5`, `context_file_max_chars=100000` |
| Processa `.env` | Remove `HERMES_TUI_DIR=/app/umbrel-tui`, `PATH=$PATH` literal, vars de container |
| Copia `auth.json` | Credenciais Nous Portal |
| Copia `state.db` | Sessões, kanban, histórico |
| Sincroniza `skills/`, `memories/`, `scripts/`, `logs/` | `rsync -a --delete` |
| Corrige permissões | `chown -R 1000:1000` para usuário do container |
| Valida estrutura | Checklist final do que foi migrado |

---

## Passo a Passo

### 1. No Ubuntu, prepare o destino
```bash
mkdir -p ~/hermes-ubuntu && cd ~/hermes-ubuntu
```

### 2. Monte o volume do Umbrel
**Opção A: Via rede (9p/virtio se for VM)**
```bash
sudo mkdir -p /mnt/umbrel-data
sudo mount -t 9p -o trans=virtio,version=9p2000.L hermes-data /mnt/umbrel-data
```

**Opção B: Docker cp (se o container ainda roda)**
```bash
docker cp hermes-container:/opt/data ./umbrel-data
export UMBREL_SOURCE="./umbrel-data"
```

**Opção C: Backup tar (mais simples)**
```bash
# No Umbrel:
tar -czf /tmp/hermes-backup.tar.gz -C /opt/data .
# Copie para Ubuntu e extraia:
tar -xzf hermes-backup.tar.gz -C ./umbrel-data
export UMBREL_SOURCE="./umbrel-data"
```

### 3. Rode a migração
```bash
chmod +x templates/migrate-umbrel-to-ubuntu.sh
./templates/migrate-umbrel-to-ubuntu.sh
```

### 4. Suba o container
```bash
docker compose -f templates/ubuntu-docker-compose.yml up -d
```

### 5. Verifique
```bash
docker compose logs -f hermes
# Dashboard: http://localhost:9119
# Chat:      http://localhost:9119/chat
```

---

## Pós-Migração — Checklist

- [ ] **Raft**: `docker compose exec hermes raft agent login start` → `wait dvc_...`
- [ ] **Cron jobs**: Recriar via `hermes cron create` (scripts em `data/scripts/`)
- [ ] **Proxy reverso**: Configure Nginx/Caddy para SSL + domínio próprio
- [ ] **Firewall**: `ufw allow 9119/tcp`
- [ ] **Backup automático**: Adicione cron no host para `tar -czf /backup/hermes-$(date +%F).tar.gz data/`

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| `Chat unavailable: 1` | Verifique se `HERMES_TUI_DIR=/opt/hermes/ui-tui` está no `.env` |
| Dashboard não carrega | `docker compose logs hermes` — veja se porta 9119 está livre |
| Permissão negada em logs | `docker compose exec hermes chown -R 1000:1000 /opt/data` |
| Raft não conecta | Refaça `raft agent login` — credencial antiga expirou |
| Node não encontrado | `HERMES_NODE=/usr/bin/node` no `.env` (Ubuntu usa `/usr/bin/node`) |

---

## Atualizações Futuras

### Docker
```bash
docker compose -f templates/ubuntu-docker-compose.yml pull
docker compose -f templates/ubuntu-docker-compose.yml up -d
```

### Nativo (systemd)
```bash
cd /opt/hermes-agent
git pull
source .venv/bin/activate
pip install -e .[all]
sudo systemctl restart hermes
```

---

## Referências

- `templates/ubuntu-docker-compose.yml` — Docker Compose produção-ready
- `templates/migrate-umbrel-to-ubuntu.sh` — Script de migração automatizado
- `templates/ubuntu-systemd-native.md` — Guia instalação nativa (systemd)
- `references/dashboard-chat-troubleshooting.md` — PATH corruption fix
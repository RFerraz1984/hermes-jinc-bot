# Hermes Agent on Ubuntu — systemd Service (Alternative to Docker)

## Use this if you prefer native installation over Docker

### 1. Install Dependencies
```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv nodejs npm git sqlite3
```

### 2. Clone & Install Hermes
```bash
cd /opt
sudo git clone https://github.com/NousResearch/hermes-agent.git
sudo chown -R $USER:$USER hermes-agent
cd hermes-agent
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[all]
```

### 3. Copy Migrated Data
```bash
# Assuming you ran migrate-umbrel-to-ubuntu.sh and have ./data/
cp -r ../hermes-migration/data/* ~/.hermes/
# Or if using custom HERMES_HOME:
# HERMES_HOME=/opt/hermes-data cp -r ../hermes-migration/data/* /opt/hermes-data/
```

### 4. Install Systemd Service
```bash
sudo cp hermes.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hermes
```

### 5. Check Status
```bash
sudo systemctl status hermes
journalctl -u hermes -f
```

### 6. Dashboard Access
```bash
# Local only:
hermes dashboard --host 127.0.0.1 --port 9119

# Or via systemd (runs in background):
# Access at http://localhost:9119
```

---

## hermes.service

```ini
[Unit]
Description=Hermes Agent Gateway + Dashboard
Documentation=https://github.com/NousResearch/hermes-agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=hermes
Group=hermes
WorkingDirectory=/opt/hermes-agent
ExecStart=/opt/hermes-agent/.venv/bin/hermes gateway start --dashboard
Restart=always
RestartSec=10
TimeoutStartSec=60
TimeoutStopSec=30

# Environment
Environment=HERMES_HOME=/opt/hermes-data
Environment=HERMES_DASHBOARD=1
Environment=HERMES_DASHBOARD_HOST=0.0.0.0
Environment=HERMES_DASHBOARD_PORT=9119
Environment=HERMES_TUI_DIR=/opt/hermes-agent/ui-tui
Environment=HERMES_NODE=/usr/bin/node
Environment=TZ=America/Sao_Paulo
Environment=PYTHONUNBUFFERED=1

# Resource limits
MemoryMax=2G
CPUQuota=200%

# Security
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/opt/hermes-data /opt/hermes-agent

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hermes

[Install]
WantedBy=multi-user.target
```

---

## Create hermes user (if not exists)
```bash
sudo useradd -r -s /bin/false -d /opt/hermes-data -m hermes
sudo usermod -aG hermes $USER  # optional: add your user to group for file access
```

---

## Directory Structure (Native)

```
/opt/
├── hermes-agent/          # Git repo (source code)
│   ├── .venv/             # Python venv
│   └── ui-tui/            # TUI bundle (built-in)
└── hermes-data/           # HERMES_HOME (persistent data)
    ├── config.yaml
    ├── .env
    ├── auth.json
    ├── state.db
    ├── skills/
    ├── memories/
    ├── scripts/
    ├── logs/
    └── plugins/
```

---

## Updates

```bash
cd /opt/hermes-agent
git pull
source .venv/bin/activate
pip install -e .[all]
sudo systemctl restart hermes
```

---

## Logs

```bash
# Systemd journal
journalctl -u hermes -f

# Hermes logs (inside HERMES_HOME)
tail -f /opt/hermes-data/logs/gateway.log
tail -f /opt/hermes-data/logs/gui.log
tail -f /opt/hermes-data/logs/agent.log
```

---

## Firewall (UFW)

```bash
sudo ufw allow 9119/tcp comment "Hermes Dashboard"
sudo ufw allow 18790/tcp comment "Hermes Gateway (optional)"
sudo ufw enable
```

---

## Reverse Proxy (Nginx + Let's Encrypt)

```nginx
# /etc/nginx/sites-available/hermes
server {
    listen 80;
    server_name hermes.seudominio.com;

    location / {
        proxy_pass http://127.0.0.1:9119;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/hermes /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d hermes.seudominio.com
```
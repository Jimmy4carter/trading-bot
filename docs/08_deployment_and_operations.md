# Deployment, Production Operations & Live Rollout

This guide provides end-to-end instructions for deploying the **QuantumBit BHR Autonomous Trading Engine** on a budget cloud VPS (Hetzner Cloud CX22 at €3.79–€5.00/month), securing the installation with automatic HTTPS, and safely transitioning from True Paper Trading to Live Micro-Capital execution.

---

## 1. Cloud VPS Provisioning

### Recommended Server Specifications
- **Provider**: Hetzner Cloud (or DigitalOcean / Linode / Vultr)
- **Plan**: CX22 (1 vCPU, 2 GB RAM, 40 GB NVMe Disk)
- **Cost**: ~€3.79 / month
- **Operating System**: Ubuntu 24.04 LTS or Ubuntu 22.04 LTS
- **Datacenter Location**:
  - **Falkenstein / Nuremberg (EU)**: Optimal for Bybit & Binance.
  - **Ashburn, Virginia (US)**: Optimal for OANDA v20 US servers.

---

## 2. Server Hardening & Dependencies

Connect to your VPS via SSH and run initial server hardening:

```bash
# 1. Update and upgrade packages
sudo apt update && sudo apt upgrade -y

# 2. Install essential tools
sudo apt install -y curl git ufw fail2ban sqlite3

# 3. Configure UFW Firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (Let's Encrypt validation)
sudo ufw allow 443/tcp   # HTTPS (Admin Dashboard)
sudo ufw enable

# 4. Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

---

## 3. Application Deployment via Docker Compose

### Clone & Configure Repository
```bash
git clone https://github.com/yourusername/trading-bot.git /opt/trading-bot
cd /opt/trading-bot

# Copy environment template
cp .env.example .env
nano .env
```

### Critical Environment Variables (`.env`)
```ini
ENVIRONMENT=production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=GenerateAStrongPasswordHere
JWT_SECRET=UseAStrongRandomHexKey32CharsLong

# Execution Mode
EXECUTION_MODE=demo            # Keep in demo for paper testing!
ACTIVE_BROKER=bybit
STARTING_BALANCE_USD=10.00
TRADE_SIZE_USD=5.00
MAX_CONCURRENT_TRADES=1

# Exchange API Keys
BYBIT_API_KEY=your_bybit_key
BYBIT_API_SECRET=your_bybit_secret

# Telegram Push & Command Daemon
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_numeric_chat_id
TELEGRAM_ENABLED=True
```

### Launch the Stack
```bash
# Build and launch Docker containers in detached mode
docker compose up -d --build

# Inspect running services
docker compose ps

# Follow application logs
docker compose logs -f bot
```

---

## 4. HTTPS Reverse Proxy with Caddy

Caddy provides automatic, zero-configuration SSL certificates from Let's Encrypt with minimal memory usage (< 25 MB RAM).

```bash
# Install Caddy on Ubuntu
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy -y
```

### Configure `/etc/caddy/Caddyfile`
```caddy
bot.yourdomain.com {
    reverse_proxy 127.0.0.1:8000
}
```

Reload Caddy:
```bash
sudo systemctl reload caddy
```
Your dashboard is now live and secured over SSL at `https://bot.yourdomain.com`.

---

## 5. 3-Stage Live Rollout Strategy

To safeguard initial capital, adhere strictly to the following 3-stage rollout:

```
+-------------------------------------------------------------------------+
|                  STAGE 1: Cold Start Bootstrap                          |
|  Run python scripts/bootstrap_history.py to pre-train BHR & HDC memory  |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  STAGE 2: 7-Day True Paper Trading                      |
|  - Real order book telemetry feeds                                      |
|  - Realistic +0.03% slippage & taker fees applied                       |
|  - Verify Trailing Stops lock in profit (+0.8% trigger, 0.25% pullback) |
|  - Validate Win Rate > 55% across >= 30 paper trades                    |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  STAGE 3: Micro-Live Capital ($10 - $20)                |
|  - Switch mode via Web Dashboard or Telegram (/live)                    |
|  - 1 concurrent trade max ($5.00 - $5.50 notional)                      |
|  - Stop Loss locked at -0.6% ($0.03 max risk per trade)                 |
|  - Compound account from organic profits                                |
+-------------------------------------------------------------------------+
```

---

## 6. Maintenance & Disaster Recovery

### Automated SQLite Backups
SQLite uses Write-Ahead Logging (`WAL` mode) for zero-lock concurrency. Create a daily backup cron job:

```bash
# Add to crontab -e
0 2 * * * sqlite3 /opt/trading-bot/trading_ledger.db ".backup '/opt/trading-bot/backups/ledger_$(date +\%F).db'"
```

### Manual Service Restart
```bash
cd /opt/trading-bot
docker compose restart bot
```
The crash-recovery protocol (`reconcile_and_resume_all()`) will instantly re-bind all open positions and resume tick monitoring within 2 seconds.

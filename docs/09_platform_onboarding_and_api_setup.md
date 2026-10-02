# Platform Onboarding, Exchange Verification & VPS Setup Guide

This guide provides exhaustive, step-by-step instructions for registering on all supported exchanges, completing identity verification (KYC), generating API keys with the correct permissions, configuring mobile Telegram controls, and provisioning your **Hetzner Cloud VPS**.

---

## 1. Master Onboarding Checklist

| Platform | Role | Required Verification | Est. Setup Time |
|---|---|---|---|
| **Bybit** | Primary Crypto Broker ($10 micro-capital spot) | KYC Level 1 (ID/Passport) | 10 minutes |
| **Binance** | Secondary Deep Liquidity Crypto Broker | Verified (ID + Liveness) | 15 minutes |
| **OANDA v20** | Institutional Forex & Metals Broker | Identity & Proof of Address | 1–2 business days |
| **Telegram** | Mobile Push Alerts & Remote Command Daemon | None (Phone Number) | 3 minutes |
| **Hetzner Cloud** | Low-Latency Linux VPS Host (€3.79/month) | Credit Card / ID check | 5–10 minutes |

---

## 2. Platform 1: Bybit Setup (Recommended for Crypto)

Bybit is the primary recommended exchange for the QuantumBit bot because it permits small order notionals ($5.00) and provides reliable WebSocket and REST endpoints with high rate limits.

### Step 1: Create an Account
1. Visit [bybit.com](https://www.bybit.com) and sign up with your email and a strong password.
2. Enable **Two-Factor Authentication (2FA)** under `Account & Security` using Google Authenticator.

### Step 2: KYC Identity Verification
1. Navigate to **Account & Security -> Identity Verification**.
2. Click **Verify Now** under **Level 1 (Standard Verification)**.
3. Submit a photo of your Government ID (Passport, National ID, or Driver's License) and a quick facial selfie scan.
4. Level 1 verification is usually approved within 5 to 15 minutes.

### Step 3: Generate API Key & Secret
1. Go to your profile icon (top right) -> **API**.
2. Click **Create New Key** -> Select **System-generated API Keys**.
3. Choose **API Transaction** (Connect to third-party applications).
4. Configure key settings:
   - **Name**: `QuantumBit-BHR-Bot`
   - **Key Permissions**: Select **Read-Write**.
   - **IP Restrictions**: 
     - While testing locally: Select *No IP restriction (Valid for 90 days)*.
     - In production on Hetzner: Select *Only IPs with permissions have access* and paste your **Hetzner Server Static Public IP**.
   - **Permission Details**:
     - Check `Standard Account` -> `Spot` -> **Trade** (Allows placing market orders and reading balances).
     - Check `Standard Account` -> **Order** & **Position**.
     - **CRITICAL**: Do **NOT** check "Withdrawal" or "Assets Transfer". The bot never requires withdrawal permissions.
5. Click **Submit**, enter your Google 2FA code, and copy your **API Key** and **API Secret**.
6. Store them in `.env`:
   ```ini
   BYBIT_API_KEY=your_bybit_api_key_here
   BYBIT_API_SECRET=your_bybit_api_secret_here
   ```

---

## 3. Platform 2: Binance Setup (Alternative Crypto Venue)

### Step 1: Registration & KYC
1. Visit [binance.com](https://www.binance.com) and register an account.
2. Complete **Identity Verification (Plus)** by uploading your government ID and completing the biometric face scan.

### Step 2: API Management
1. Click your profile avatar -> **API Management**.
2. Click **Create API** -> Select **System generated (HMAC)**.
3. Label: `QuantumBit-Binance-Engine`.
4. Under **API Restrictions**:
   - Check `Enable Reading` (default).
   - Check `Enable Spot & Margin Trading`.
   - Leave `Enable Withdrawals` **UNCHECKED**.
5. Copy your **API Key** and **Secret Key** into `.env`:
   ```ini
   BINANCE_API_KEY=your_binance_api_key_here
   BINANCE_API_SECRET=your_binance_api_secret_here
   ```

---

## 4. Platform 3: OANDA v20 Setup (Forex & Commodities)

OANDA provides institutional-grade liquidity for EUR/USD, GBP/USD, USD/JPY, and Gold (XAU/USD).

### Step 1: Open an Account
1. Visit [oanda.com](https://www.oanda.com).
2. Choose your region (US, UK, Europe, or Global) and register.
3. Create either a **Practice Account** (virtual $50,000 demo) or a **Live Account**.

### Step 2: Retrieve Account ID
1. Log in to the OANDA Web Trading Hub or Portal.
2. Locate your **Account ID** (formatted like `101-004-12345678-001` or an 8-digit numeric integer).

### Step 3: Generate Personal Access Token
1. Go to **Manage API Access** (or **My Account -> Developer API**).
2. Click **Generate** to create a Personal Access Token.
3. Copy the token into `.env`:
   ```ini
   OANDA_API_KEY=your_oanda_personal_access_token
   OANDA_ACCOUNT_ID=your_oanda_account_id
   OANDA_ENVIRONMENT=practice   # Switch to 'trade' for live forex
   ```

---

## 5. Platform 4: Telegram Bot Setup (Mobile Push & Controls)

The Telegram integration enables live notifications whenever trades are entered, trailing stops ratchet forward, or positions close. It also gives you a mobile kill switch (`/close_all`).

### Step 1: Create the Bot via `@BotFather`
1. Open Telegram on your phone or desktop and search for `@BotFather`.
2. Tap **Start** and send the command:
   ```text
   /newbot
   ```
3. Enter a friendly name (e.g. `My QuantumBit Bot`).
4. Enter a unique username ending in `bot` (e.g. `QuantumBit_Trading_Alpha_Bot`).
5. BotFather will reply with your **HTTP API Token**:
   ```text
   7890123456:AAFlkX8...
   ```

### Step 2: Get Your Numeric User ID via `@userinfobot`
1. In Telegram, search for `@userinfobot` and click **Start**.
2. It will reply with your user profile details. Copy your numeric **`Id`** (e.g. `987654321`).

### Step 3: Link & Test
1. Send a `/start` message to your newly created bot so it has permission to message you.
2. Add your credentials to `.env`:
   ```ini
   TELEGRAM_BOT_TOKEN=7890123456:AAFlkX8...
   TELEGRAM_CHAT_ID=987654321
   TELEGRAM_ENABLED=True
   ```
3. Test commands in Telegram:
   - Send `/status` -> Bot responds with live balance and open trades.
   - Send `/demo` -> Ensures paper trading mode is engaged.

---

## 6. Platform 5: Hetzner Cloud VPS Provisioning (Step-by-Step)

Hetzner Cloud offers reliable German datacenter infrastructure with low-latency fiber links directly to European exchange matching engines at just **€3.79 to €5.00 per month**.

### Step 1: Account Registration
1. Visit [hetzner.com/cloud](https://www.hetzner.com/cloud) and click **Sign Up**.
2. Fill out your details. Complete email verification and link a payment method (Credit Card or PayPal).
3. Open the **Hetzner Cloud Console** (`console.hetzner.cloud`).

### Step 2: Generate an SSH Key Pair (Windows)
Open Windows PowerShell on your local PC and generate an Ed25519 key:
```powershell
ssh-keygen -t ed25519 -C "admin@quantumbit"
```
Press Enter to accept the default file location (`C:\Users\YourUser\.ssh\id_ed25519`). Choose a passphrase or leave blank.

View and copy your public key:
```powershell
Get-Content ~/.ssh/id_ed25519.pub
```
*(It looks like: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5... admin@quantumbit`)*

### Step 3: Add SSH Key in Hetzner Console
1. In the Hetzner Cloud Console, select **Security** (left menu) -> **SSH Keys**.
2. Click **Add SSH Key**.
3. Paste the public key string from PowerShell and name it `Local-Windows-PC`.

### Step 4: Create the Server
1. Click **+ Add Server**.
2. **Location**: Select **Falkenstein** or **Nuremberg** (optimal for Bybit & Binance EU endpoints).
3. **Image**: Select **Ubuntu 24.04 LTS** (or 22.04 LTS).
4. **Type**: Select **Standard** -> **CX22** (1 vCPU, 2 GB RAM, 40 GB NVMe Disk - €3.79/mo).
5. **Networking**: Public IPv4 and IPv6 enabled.
6. **SSH Keys**: Check the box for your `Local-Windows-PC` key.
7. **Firewalls**: Click **Create Firewall**:
   - Inbound Rule 1: Port `22` (SSH)
   - Inbound Rule 2: Port `80` (HTTP for Let's Encrypt SSL)
   - Inbound Rule 3: Port `443` (HTTPS for Admin Web Dashboard)
   - Inbound Rule 4: Port `8000` (Direct FastAPI access if not using reverse proxy)
8. **Name**: `quantumbit-vps-01`.
9. Click **Create & Buy Now**. The server boots in ~20 seconds. Note down the **IPv4 Address**.

### Step 5: First-Time SSH Connection
In Windows PowerShell:
```powershell
ssh root@YOUR_HETZNER_IPV4
```
Type `yes` when asked to trust the host key. You are now inside your cloud VPS!

### Step 6: Install Docker & Docker Compose
Run the following on your Hetzner VPS:
```bash
# Update Ubuntu packages
apt update && apt upgrade -y

# Install Docker engine
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose Plugin & Git
apt install -y docker-compose-plugin git sqlite3 curl
```

### Step 7: Clone Repository & Launch Stack
```bash
# Clone the repository
git clone https://github.com/Jimmy4carter/trading-bot.git /opt/trading-bot
cd /opt/trading-bot

# Create production .env file
cp .env.example .env
nano .env
```
Paste your real exchange API keys, strong admin password, and Telegram credentials. Then build and launch the production stack:

```bash
docker compose up -d --build
```

Verify everything is running smoothly:
```bash
docker compose ps
docker compose logs -f bot
```

Open your browser to:
```
http://YOUR_HETZNER_IPV4:8000
```
Log in with your configured admin credentials. Your autonomous engine is now actively running in the cloud!

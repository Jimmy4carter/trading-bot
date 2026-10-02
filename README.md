# QuantumBit BHR | Autonomous Self-Improving Trading Bot

An institutional-grade, lightweight algorithmic trading bot powered by the **Bitwise Holographic Router (BHR)**, **Evolutionary Reinforcement Learning (ERL)**, and a **Dual-Layer Memory (Redis + SQLite WAL)**.

Designed to operate on a budget **Hetzner Cloud VPS (€3.79–€5/mo)** with micro-capital ($10 starting balance), full multi-broker routing (Bybit, Binance, OANDA), and a dark-mode Admin Control Center.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |       Bybit / Binance / OANDA         |
                      |   (Real-Time Order Books & Feeds)     |
                      +-------------------+-------------------+
                                          |
                                          v
+---------------------------------------------------------------------------------+
|                                 OmniRouter                                      |
|            (Dispatches Live Orders or True Paper Simulations locally)           |
+-----------------------------------------+---------------------------------------+
                                          |
                                          v
+---------------------------------------------------------------------------------+
|                       Market Fingerprint Generator                              |
|           (Translates multi-frame OHLCV into a 64-bit integer DNA)             |
+-----------------------------------------+---------------------------------------+
                                          |
                                          v
+-----------------------------------------+---------------------------------------+
|                 Bitwise Holographic Router (BHR Engine)                         |
|      - Applies pair-specific Genetic Bitmask (current_fp & mask)                |
|      - Computes XOR Hamming distance across thousands of historical memories    |
|      - Identifies highest-probability trade direction in microseconds           |
+-----------------------------------------+---------------------------------------+
                                          |
                                          v
+-----------------------------------------+---------------------------------------+
|                      Q-Learning Risk Filter Gate                                |
|   - Dynamically weights BHR confidence with historical regime performance       |
|   - Allocates Full Size, Half Size, or Rejection based on strict thresholds     |
+-----------------------------------------+---------------------------------------+
                                          |
                     +--------------------+--------------------+
                     |                                         |
                     v                                         v
+---------------------------------------+   +-------------------------------------+
|        Event-Driven Exit Manager      |   |        Genetic Evolution Worker     |
|   - Real-time Trailing Stops          |   |   - Background Darwinian optimizer  |
|   - Take-Profit & Hard Stop-Loss      |   |   - Evolves 64-bit feature masks    |
|   - Crash Recovery & Reconciliation   |   |   - Stores best masks in Redis      |
+-------------------+-------------------+   +-------------------------------------+
                    |
                    v
+---------------------------------------------------------------------------------+
|                       SQLite WAL Ledger & Redis Brain                           |
|       - Hot Cache: Nanosecond Q-Values & Active Genetic Masks (Redis)           |
|       - Persistent Cold Ledger: Trade Logs, Watchlist, Strategy Archive (SQLite)|
+---------------------------------------------------------------------------------+
```

---

## Key Features

1. **Bitwise Holographic Routing (BHR)**:
   - Uses 64-bit integer bitmasks to represent market condition (EMA, RSI, Stochastic, Bollinger Bands, Volume Delta, Pin-bars).
   - Calculates historical pattern similarity via hardware-level bitwise XOR and Hamming distance.
2. **True Paper Trading on Live Feeds**:
   - Reads 100% real live market feeds from Bybit, Binance, and OANDA.
   - Simulates fills locally with realistic slippage and exchange fees, avoiding broken crypto testnet sandboxes.
3. **Event-Driven Exit Manager with Trailing Stops**:
   - Trailing stops activate at +0.8% and lock in profits on 0.25% pullbacks.
   - Enables high-frequency scalping (seconds/minutes) and swing trading.
4. **Exchange Precision & Lot Normalizer**:
   - Prevents the "$10 capital trap" where balances drop below minimum notional limits.
   - Automatically formats lot sizes to exchange step sizes.
5. **Crash Recovery & Reconciliation**:
   - All open positions are persisted to SQLite immediately.
   - On server reboot or Docker restart, the bot reconciles open positions and resumes tracking.
6. **Glassmorphism Admin Dashboard**:
   - Real-time balance cards, PnL indicators, interactive risk sliders.
   - One-click switches: Demo vs. Live, Bybit/Binance/OANDA.
7. **Two-Way Interactive Telegram Bot**:
   - Push alerts for entries, trailing stop activations, and exits.
   - Commands: `/status`, `/live`, `/demo`, `/close_all`.

---

## Quickstart (Local Dev & Testing)

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Configuration
Copy the template and adjust settings as needed:
```bash
cp .env.example .env
```
*(Default settings start safely in `EXECUTION_MODE=demo` with a $10 paper balance).*

### 3. Pre-Seed Historical Market DNA
Run the bootstrap utility to prime the AI with historical memories before starting:
```bash
python scripts/bootstrap_history.py
```

### 4. Start the Application
```bash
python main.py
```
Open your browser and navigate to:
**`http://localhost:8000`**

Default credentials:
* **Username**: `admin`
* **Password**: `admin` (or whatever you configured in `.env`)

---

## Production Deployment on Hetzner VPS

### 1. Provision Server
* Launch a **Hetzner CX11 or CX22** instance (€3.79–€5/mo) running **Ubuntu 22.04 / 24.04**.
* SSH into the server:
  ```bash
  ssh root@YOUR_SERVER_IP
  ```

### 2. Install Docker & Docker Compose
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker
```

### 3. Deploy Bot via Docker Compose
```bash
git clone https://github.com/YOUR_USERNAME/trading-bot.git
cd trading-bot
cp .env.example .env
# Edit your .env with your real API keys and a strong admin password:
nano .env

# Build and start services in background:
docker compose up -d --build
```

### 4. View Logs
```bash
docker compose logs -f bot
```

---

## Documentation Suite

Comprehensive technical, algorithmic, and operational documentation is located in the [`docs/`](file:///c:/Users/User/Documents/GitHub/trading-bot/docs) directory:

| Document | Description |
|---|---|
| [00. Master Index](file:///c:/Users/User/Documents/GitHub/trading-bot/docs/00_index.md) | Documentation map, sitemap, and engineering sync rules. |
| [01. Architecture Overview](file:///c:/Users/User/Documents/GitHub/trading-bot/docs/01_architecture_overview.md) | High-level system topology, async pipelines, memory tiers (Redis + SQLite WAL). |
| [02. Bitwise Holographic Router (BHR)](file:///c:/Users/User/Documents/GitHub/trading-bot/docs/02_bitwise_holographic_router.md) | 64-bit market DNA fingerprinting, Genetic Bitmask evolution, hardware XOR Hamming matching. |
| [03. Frontier Neural Physics](file:///c:/Users/User/Documents/GitHub/trading-bot/docs/03_frontier_neural_physics.md) | 1,024-bit HDC Associative Memory, Rule 110 Gliders, Navier-Stokes Hydraulics, AlphaZero Shadow Adversary, Shannon Entropy Wave. |
| [04. Brokers & Precision Engine](file:///c:/Users/User/Documents/GitHub/trading-bot/docs/04_brokers_and_precision_engine.md) | Multi-broker suite (Bybit, Binance, OANDA v20), lot step normalizers, $10 micro-capital handling. |
| [05. Position & Exit Management](file:///c:/Users/User/Documents/GitHub/trading-bot/docs/05_position_and_exit_management.md) | Dynamic trailing stops (+0.8% trigger, 0.25% pullback), tick monitor, SQLite crash recovery. |
| [06. API & Admin Dashboard](file:///c:/Users/User/Documents/GitHub/trading-bot/docs/06_api_and_dashboard.md) | REST API specification, JWT auth, real-time telemetry, glassmorphism UI. |
| [07. Telegram Bot Integration](file:///c:/Users/User/Documents/GitHub/trading-bot/docs/07_telegram_bot.md) | Two-way command daemon (`/status`, `/live`, `/demo`, `/close_all`), push alerting schemas. |
| [08. Deployment & Operations](file:///c:/Users/User/Documents/GitHub/trading-bot/docs/08_deployment_and_operations.md) | Hetzner Cloud CX22 Ubuntu provisioning, Docker Compose, Caddy HTTPS reverse proxy. |
| [09. Platform Onboarding & API Setup](file:///c:/Users/User/Documents/GitHub/trading-bot/docs/09_platform_onboarding_and_api_setup.md) | Comprehensive account registration, KYC verification, API key setup for Bybit, Binance, OANDA, Telegram, and Hetzner VPS. |
| [10. Synaptic Mini-AI & Lifelong Learning](file:///c:/Users/User/Documents/GitHub/trading-bot/docs/10_synaptic_mini_ai_and_lifelong_learning.md) | Cognitive IQ and XP progression, Neuro-Symbolic formula evolution, Markov regime transitions, and counterfactual distillation. |

> [!IMPORTANT]
> **Engineering Rule**: All subsequent implementations, algorithm modifications, or operational adjustments must include updating or adding to the documentation suite in `docs/`.

---

## Project Structure

```
trading-bot/
├── config/
│   └── settings.py          # Pydantic type-safe configuration
├── core/
│   ├── database.py          # SQLite WAL connection & schemas (with 64-bit DNA support)
│   ├── cache.py             # Redis client with in-memory fallback
│   └── security.py          # JWT authentication & password hashing
├── brokers/
│   ├── base.py              # Abstract Broker & Precision Engine
│   ├── crypto_ccxt.py       # Bybit & Binance CCXT connector (lazy-loaded markets)
│   ├── forex_oanda.py       # OANDA v20 REST connector
│   ├── paper_simulator.py   # Live-feed paper trading simulator (+0.03% slippage)
│   └── __init__.py          # OmniBrokerRouter dispatcher
├── engines/
│   ├── fingerprint.py       # 64-bit Market DNA generator
│   ├── bhr.py               # Vectorized Bitwise Holographic Router
│   ├── genetic.py           # Genetic Bitmask evolution engine
│   ├── q_filter.py          # Q-learning risk filter
│   ├── exit_manager.py      # Event-driven trailing stop & exit daemon
│   ├── hdc.py               # 1,024-bit Hyperdimensional Vector Memory (VSA)
│   ├── automaton.py         # Wolfram Rule 110 Cellular Automaton Glider Lattice
│   ├── hydraulics.py        # Navier-Stokes Liquidity Hydraulics & Viscosity Engine
│   ├── shadow_adversary.py  # AlphaZero Adversarial Stop-Hunt Sandbox
│   ├── entropy.py           # Cross-Asset Shannon Entropy Wave Collapse Engine
│   ├── symbolic_formula.py  # Neuro-Symbolic Genetic Formula Synthesizer
│   ├── knowledge_vault.py   # Synaptic Knowledge Vault & Markov Transitions
│   └── self_distillation.py # Counterfactual Replay & Post-Mortem Distiller
├── api/
│   └── app.py               # FastAPI backend, background workers & trading loop
├── ui/
│   ├── index.html           # Dark-mode glassmorphism dashboard
│   ├── style.css            # Responsive UI styles
│   └── app.js               # Reactive telemetry, controls & Synaptic Mini-AI panel
├── bots/
│   └── telegram_bot.py      # 2-way Telegram alerts & commands
├── docs/                    # Complete technical and operational documentation
│   ├── 00_index.md
│   ├── 01_architecture_overview.md
│   ├── 02_bitwise_holographic_router.md
│   ├── 03_frontier_neural_physics.md
│   ├── 04_brokers_and_precision_engine.md
│   ├── 05_position_and_exit_management.md
│   ├── 06_api_and_dashboard.md
│   ├── 07_telegram_bot.md
│   ├── 08_deployment_and_operations.md
│   ├── 09_platform_onboarding_and_api_setup.md
│   └── 10_synaptic_mini_ai_and_lifelong_learning.md
├── scripts/
│   └── bootstrap_history.py # Pre-training historical bootstrapper
├── tests/
│   ├── test_components.py   # Core unit tests (6/6 passing)
│   ├── test_frontier_engines.py # Frontier physics unit tests (5/5 passing)
│   └── test_synaptic_ai.py  # Synaptic Mini-AI unit tests (5/5 passing)
├── docker-compose.yml       # Production container orchestration
├── Dockerfile               # Multi-stage production build
└── requirements.txt         # Production dependencies
```


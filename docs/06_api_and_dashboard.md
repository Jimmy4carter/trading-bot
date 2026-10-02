# API Specification & Admin Dashboard

The QuantumBit BHR bot serves a high-performance, asynchronous REST API powered by **FastAPI** (`api/app.py`) along with a dark glassmorphic web dashboard (`ui/index.html`, `ui/style.css`, `ui/app.js`).

---

## 1. Authentication & Security

All control and telemetry endpoints (with the exception of `/`, `/static`, `/api/login`, and `/api/health`) require a valid JSON Web Token (JWT) passed in the `Authorization` header:

```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
```

Tokens are signed using `HS256` with the secret specified in `JWT_SECRET` (`core/security.py`) and expire automatically after 24 hours.

---

## 2. API Endpoints Reference

### Public Endpoints

#### `POST /api/login`
Authenticates the administrator and returns an access token.
- **Request Body**:
  ```json
  {
    "username": "admin",
    "password": "your_secure_password"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsIn...",
    "username": "admin"
  }
  ```

#### `GET /api/health`
Kubernetes / Docker health and liveness probe.
- **Response (200 OK)**:
  ```json
  {
    "status": "healthy",
    "timestamp": 1727902400.123
  }
  ```

---

### Protected Endpoints

#### `GET /api/status`
Returns real-time engine telemetry, active mode, live broker balances, trading stats, and execution thresholds.
- **Response (200 OK)**:
  ```json
  {
    "status": "online",
    "mode": "paper",
    "active_broker": "bybit",
    "balance": {
      "total_usd": 10.00,
      "free_usd": 10.00,
      "used_usd": 0.00
    },
    "performance": {
      "total_trades": 0,
      "win_rate": 0.0,
      "net_profit_usd": 0.0,
      "profit_factor": 0.0
    },
    "config": {
      "max_concurrent_trades": 1,
      "trade_size_usd": 5.0,
      "min_confidence_threshold": 0.35,
      "take_profit_pct": 0.015,
      "stop_loss_pct": 0.006
    }
  }
  ```

#### `POST /api/config`
Updates dynamic system configuration in real-time. Changes are saved to SQLite and take effect immediately.
- **Request Body**:
  ```json
  {
    "execution_mode": "paper",
    "active_broker": "bybit",
    "trade_size_usd": 5.0,
    "max_concurrent_trades": 1,
    "min_confidence_threshold": 0.35
  }
  ```

#### `GET /api/watchlist`
Retrieves the list of monitored symbols across all asset classes.

#### `POST /api/watchlist`
Adds a new market pair to the active scanner.
- **Request Body**:
  ```json
  {
    "symbol": "SOL/USDT",
    "asset_class": "crypto",
    "broker": "bybit"
  }
  ```

#### `POST /api/watchlist/toggle`
Enables or disables scanning for a specific symbol without deleting it.
- **Request Body**:
  ```json
  {
    "symbol": "BTC/USDT",
    "is_active": false
  }
  ```

#### `GET /api/positions`
Returns all currently open positions with real-time unrealized PnL, highest price reached, and entry timestamps.

#### `POST /api/positions/close/{position_id}`
Manually forces the immediate market closure of an individual position and logs it to the trade ledger.

#### `POST /api/positions/close_all`
**Emergency Kill-Switch**: Immediately cancels all active trailing-stop tasks and closes every open position across all connected brokers.

#### `GET /api/history`
Returns a paginated log of executed and closed trades from SQLite, including duration, realized net profit, and fees paid.

#### `POST /api/bootstrap`
Triggers the pre-training engine in the background to download historical OHLCV data and populate the BHR pattern database.

#### `GET /api/frontier`
Provides real-time diagnostic telemetry for the five Frontier Neural Physics paradigms:
```json
{
  "status": "active",
  "paradigms": {
    "hdc_memory": {
      "name": "1,024-bit Hyperdimensional Associative Memory",
      "status": "ONLINE",
      "vector_dimension": 1024,
      "cached_pairs": 5
    },
    "rule_110_automaton": {
      "name": "Wolfram Rule 110 Glider Lattice",
      "status": "MONITORING_COHERENCE",
      "lattice_size": 128,
      "evolution_steps": 24
    },
    "hydraulics": {
      "name": "Navier-Stokes Liquidity Hydraulics & Viscosity",
      "status": "STREAMING_VACUUM_DETECTION",
      "physics_metric": "Viscosity Index (μ)"
    },
    "shadow_adversary": {
      "name": "AlphaZero-Style Predatory Market Maker",
      "status": "ACTIVE_STOP_HARDENING",
      "simulation_rounds": 50
    },
    "entropy_wave": {
      "name": "Cross-Asset Joint Shannon Entropy",
      "status": "MONITORING_ENTROPY",
      "joint_entropy": 0.74,
      "wave_collapse": false,
      "dominant_direction": "NEUTRAL_DRIFT",
      "leading_symbol": "BTC/USDT"
    }
  }
}
```

---

## 3. Web Dashboard Design System

The web dashboard is implemented in vanilla HTML5, CSS3, and JavaScript without external runtime dependencies (React, Vue, or heavy node bundles), ensuring zero build overhead and fast asset loading on budget VPS links:
- **Glassmorphism Theme**: Translucent dark surfaces with subtle backdrop blurs (`backdrop-filter: blur(16px)`).
- **Responsive Telemetry Polling**: Polls `/api/status`, `/api/positions`, and `/api/frontier` every 3 seconds when authenticated.
- **Frontier Physics Visualizer**: Dedicated diagnostic panel highlighting live entropy state, HDC memory bank capacity, and cellular glider status.
- **Safety Interlocks**: Live mode toggle and emergency kill switches require explicit double-confirmation before execution.

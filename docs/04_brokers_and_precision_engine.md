# Brokers & Precision Normalization Engine

The QuantumBit BHR trading bot supports seamless multi-asset execution across cryptocurrency exchanges (Bybit, Binance) and institutional foreign exchange brokers (OANDA v20). 

It features an **Exchange Precision Engine** specifically engineered to trade micro-capital accounts ($10 to $50 starting balance) without triggering exchange precision or minimum-notional rejection errors.

---

## 1. Unified Broker Architecture (`brokers/base.py`)

All brokers inherit from `BaseBroker`, enforcing a strict asynchronous interface:

```python
class BaseBroker(ABC):
    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List[float]]: ...
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]: ...
    def create_order(self, symbol: str, side: str, amount: float, order_type: str = "MARKET", price: Optional[float] = None) -> Dict[str, Any]: ...
    def get_balance(self) -> Dict[str, float]: ...
```

---

## 2. Supported Brokers

### A. CCXT Cryptocurrency Connector (`brokers/crypto_ccxt.py`)
- **Supported Venues**: Bybit (Default) and Binance.
- **Execution Mode**: Spot margin / Spot market orders.
- **Rate-Limiting**: Built-in CCXT token bucket rate limiter (`enableRateLimit: True`, 15,000 ms network timeout).
- **Lazy Market Rules**: Market limits and rules are loaded on demand to prevent blocking server boot during network delays.

### B. Deriv API Multi-Asset Connector (`brokers/forex_deriv.py`)
- **Direct Cloud WebSocket Architecture**: Connects to Deriv WebSocket API v3 (`wss://ws.derivws.com/websockets/v3?app_id=...`). Requires zero local gateway or Wine emulation on Ubuntu Hetzner VPS.
- **Asset Coverage**: 
  - Standard Forex Majors (`EUR_USD` $\to$ `frxEURUSD`, `GBP_USD` $\to$ `frxGBPUSD`, `USD_JPY` $\to$ `frxUSDJPY`).
  - Precious Metals (`XAU_USD` $\to$ `frxXAUUSD` Gold).
  - 24/7 Synthetic Volatility Indices (`R_10`, `R_25`, `R_50`, `R_75`, `R_100`, `1HZ100V`).
- **24/7 Weekend Trading**: While traditional forex markets close on Friday evening, Deriv Synthetic Volatility Indices trade continuously 24 hours a day, 7 days a week, allowing the bot's genetic algorithms to harvest compounding alpha all weekend.
- **Micro-Capital Friendly**: Accounts can be funded with as low as $5–$10 via local Nigerian bank transfers, card, USDT (TRC20/BEP20), or payment agents. Micro-lot contracts are fully supported.
- **Cost Structure**: Zero commissions; ultra-tight spread-embedded execution.

### C. Interactive Brokers (IBKR) Institutional DMA (`brokers/forex_ibkr.py`)
- **Institutional ECN Liquidity**: NASDAQ-listed (IBKR) Tier-1 prime brokerage access.
- **Raw Spread Execution**: Top-of-book raw spreads as narrow as 0.1 to 0.2 pips on EUR/USD.
- **Hetzner Headless Gateway**: Deploys seamlessly via Docker container (`ghcr.io/gnzsnz/ib-gateway:latest`) communicating locally over native TCP socket port `4002` (paper) or `4001` (live).
- **Scale**: Perfect growth vehicle as portfolio equity compounds from $50 into thousands of dollars.

### D. OANDA v20 Forex Connector (`brokers/forex_oanda.py` - Legacy/Alternative)
- **Direct REST API**: Uses OANDA v20 REST endpoints (`/v3/instruments/{instrument}/candles`, `/v3/accounts/{account_id}/pricing`, `/v3/accounts/{account_id}/orders`).
- **Environments**: Supports both `practice` (sandbox) and `trade` (live execution).
- **Regional Note**: Retained for backward compatibility. Unsupported in several regions including Nigeria; users in those regions are routed to Deriv API or IBKR.

---

## 3. Micro-Capital Precision Normalizer

Trading with a micro-capital budget ($10 starting capital) presents unique exchange challenges:
1. **Minimum Notional Value**: Bybit and Binance reject orders where $\text{Amount} \times \text{Price} < \$5.00$.
2. **Step Size Truncation**: Placing an order with more decimal places than allowed (e.g. `0.00012345 BTC` when step size is `0.0001`) results in an immediate API rejection (`Invalid lot size`).
3. **Price Tick Size**: Limit orders and trailing stops must be quantized to the exchange's minimum tick size (e.g., `$0.01` or `$0.50`).

### Normalization Logic (`normalize_amount`)
The normalizer ensures that order size satisfies exchange constraints while maximizing buying power:

```python
def normalize_amount(self, symbol: str, target_cost_usd: float, current_price: float, min_notional: float = 5.0, step_size: float = 0.0001) -> float:
    # 1. Enforce minimum notional + 5% buffer to absorb micro-slippage
    effective_cost = max(target_cost_usd, min_notional * 1.05)
    raw_amount = effective_cost / current_price

    # 2. Floor amount to exchange step size precision
    precision_decimals = max(0, int(round(-math.log10(step_size)))) if step_size < 1 else 0
    factor = 10 ** precision_decimals
    clean_amount = math.floor(raw_amount * factor) / factor

    # 3. Verify total notional still satisfies exchange minimum
    if (clean_amount * current_price) < min_notional:
        clean_amount = math.ceil(raw_amount * factor) / factor

    return float(clean_amount)
```

---

## 4. True Paper Trading Simulator (`brokers/paper_simulator.py`)

Unlike simplistic paper trading that assumes instant fills at mid-market prices, the **True Paper Trading Simulator** replicates live market realities:

```
+-------------------------------------------------------------------+
|               True Paper Trading Simulator Engine                 |
+---------------------------------+---------------------------------+
                                  |
               +------------------+------------------+
               |                                     |
               v                                     v
+-----------------------------+       +-----------------------------+
|    Live Order Book Feeds    |       |   Realistic Fill Physics    |
| (Real Bid / Ask / Spreads)  |       |  (+0.03% Slippage Penalty)  |
+-----------------------------+       +-----------------------------+
               |                                     |
               +------------------+------------------+
                                  |
                                  v
              +---------------------------------------+
              | Realistic Exchange Fees (0.10% Taker) |
              | Atomic Balance Updates in SQLite      |
              +---------------------------------------+
```

### Realistic Fill Mechanics
1. **L2 Order Book Spread Penalty**:
   - `BUY` orders hit the live **Ask** price.
   - `SELL` orders hit the live **Bid** price.
2. **Execution Impact Slippage**:
   - Market orders suffer an additional synthetic $0.03\%$ slippage penalty:
     $$P_{\text{fill, buy}} = P_{\text{ask}} \times 1.0003$$
     $$P_{\text{fill, sell}} = P_{\text{bid}} \times 0.9997$$
3. **Fee Deduction**:
   - Crypto orders deduct standard $0.10\%$ taker fee.
   - Forex orders account for spread-based costs ($0.02\%$).
4. **State Persistence**:
   - Virtual balance is stored in SQLite system configuration (`paper_balance_usd`) and reloaded across server restarts.

---

## 5. Factory Initialization (`brokers/__init__.py`)

Brokers are dynamically instantiated via `get_broker(broker_name, is_paper)`:

```python
broker = get_broker("bybit", is_paper=True)
# Returns PaperTradingSimulator wrapping live Bybit feed
```

When paper trading is active, market analysis and pricing rely 100% on live venue feeds, guaranteeing zero discrepancy when switching to live execution.

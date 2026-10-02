# Owner Safeguards: Treasury, Circuit Breakers & Smart Order Routing

Engineered specifically for deploying micro-capital ($50 to $100 starting balance) on budget cloud infrastructure (Hetzner Cloud CX22), these owner-centric guardrails protect equity, eliminate fee drag, automate cloud hosting expenses, and prevent catastrophic drawdown spirals.

---

## 1. The $50 Capital Reality & Survival Mathematics

| Parameter | Value | Impact on $50 Capital |
|---|---|---|
| **Hetzner CX22 Cost** | €3.79/mo (~$4.15 USD) | Represents **8.3% of initial balance**. If not covered by trading profits, infrastructure overhead eats capital. |
| **Minimum Exchange Notional** | $5.00 USD | Fixed order size floor. A $5.25 trade represents **~10.5% total account allocation**. |
| **Stop Loss Risk (-0.60%)** | $0.0315 per trade | With a single concurrent position, your account can survive **over 100 consecutive losses** before 10% drawdown. |
| **Taker vs Maker Fee** | 0.10% vs 0.02% | Market orders incur 0.20% round-trip drag (25% of total stop-loss risk). Maker orders slash fee drag by **75%**. |

---

## 2. VPS Self-Funding Treasury (`engines/treasury.py`)

The bot features an automated profit-sweeping treasury that guarantees the bot pays for its own Hetzner VPS before compounding returns.

```
                          +-----------------------------------+
                          |     Trade Closes with Profit      |
                          +-----------------+-----------------+
                                            |
                                            v
                          +-----------------------------------+
                          |  Sweep 15% into VPS Hosting Fund  |
                          |  (vps_reserve_usd in SQLite WAL)  |
                          +-----------------+-----------------+
                                            |
                   +------------------------+------------------------+
                   |                                                 |
                   v                                                 v
+------------------------------------+             +------------------------------------+
| Target Reached ($4.50 Monthly Goal)|             | Target Not Reached Yet             |
| - Hetzner invoice 100% funded      |             | - Continue sweeping 15%            |
| - Sweeper automatically pauses     |             | - 85% profit compounded to equity  |
+------------------------------------+             +------------------------------------+
```

### Key Parameters
- `MONTHLY_VPS_TARGET_USD`: `$4.50` (Covers €3.79 Hetzner CX22 + VAT buffer).
- `PROFIT_SWEEP_RATE`: `0.15` (15% of realized net profit).
- `reset_treasury()`: Resets the reserve to $0.00 at the start of each monthly billing cycle.

---

## 3. Dynamic Fractional Kelly Capital Compounding

Static trade sizes ($5.00) produce linear growth. The bot employs a **Conservative Fractional Kelly Criterion** to dynamically compound profits:

$$\text{Kelly}_{\text{Full}} = \frac{W \cdot R - (1 - W)}{R}$$

$$\text{Kelly}_{\text{Conservative}} = \text{Kelly}_{\text{Full}} \times 0.25$$

$$\text{Size}_{\text{USD}} = \max\left(\$5.25, \; \text{Equity} \times \min\left(0.12, \; \text{Kelly}_{\text{Conservative}}\right)\right)$$

Where $W$ is the rolling historical win rate and $R$ is the historical average win/loss ratio.
- **Maximum Allocation Cap**: Strict **12% equity cap** per trade to eliminate ruin risk.
- **Floor Notional**: Always enforces a **$5.25 minimum** to satisfy Bybit/Binance exchange limits.

---

## 4. Spread-Spike Macro News Shield (`engines/circuit_breaker.py`)

During major economic events (US CPI, FOMC, Non-Farm Payrolls) or illiquid weekend rollovers, market makers pull liquidity and widen bid-ask spreads by $3\times$ to $5\times$.

### Spread Ratio Formula
$$\text{Spread Ratio} = \frac{\text{Current Spread}_{\%}}{\text{Median Spread}_{\text{20 bars}}}$$

- **Expansion Threshold**: If `Spread Ratio >= 2.2x`, the engine enters `SPREAD_SHOCK` state.
- **Action**: Immediately blocks new entries and temporarily widens trailing stop pullback buffers to prevent artificial broker spread stop-outs.

---

## 5. Anti-Tilt Circuit Breaker (`engines/circuit_breaker.py`)

A psychological and algorithmic safeguard to stop cascading drawdown during abrupt regime changes:
1. **Consecutive Loss Trigger**: If the bot experiences **2 consecutive losses** in a 4-hour window:
   - Execution state switches to `COOLING_DOWN`.
   - Halts all new entries for **45 minutes**.
   - Dispatches a high-priority alert to Telegram.
   - Automatically invokes the `SelfDistillationEngine` to diagnose the losses.
2. **Post-Cooling Dampener**: When cooling expires, trade size is temporarily clamped to bare minimum ($5.10) until a profitable trade confirms regime stability.
3. **Manual Override**: The operator can manually unfreeze the gate via the Admin Dashboard or Telegram command (`/reset_circuit`).

---

## 6. Maker-First Smart Order Router (`engines/smart_router.py`)

To eliminate the 0.20% round-trip taker fee penalty:
1. **Algorithmic Limit Placement**: Dispatches limit orders inside the micro-spread:
   - `BUY`: $\min(\text{Ask} - \text{Tick}, \text{Bid} + \text{Tick})$
   - `SELL`: $\max(\text{Bid} + \text{Tick}, \text{Ask} - \text{Tick})$
2. **Maker Fee Tier**: Fills as a Maker, paying **0.02%–0.05%** instead of 0.10% taker fee.
3. **Cavitation Breakout Fallback**: If order book hydraulics indicate a sudden **Cavitation Shock Breakout** (frictionless vacuum momentum), the router bypasses limit queues and hits `MARKET` immediately to guarantee zero missed runners.

---

## 7. Cross-Asset Macro Lead-Lag Latency (`engines/lead_lag.py`)

Exploits institutional lead-lag latency between foreign exchange macro tides (OANDA EUR/USD) and decentralized crypto assets (Bybit/Binance BTC/USDT):
- **Transmission Latency**: Macro currency flows typically lead crypto price displacement by **60 to 180 seconds**.
- **Alignment Matrix**:
  - `BULLISH_ALIGNED`: EUR/USD rising (USD weakness) + BTC breaking out $\implies$ **+0.08 confidence boost**.
  - `BEARISH_ALIGNED`: EUR/USD falling (USD strength) + BTC breaking down $\implies$ **+0.08 confidence boost**.
  - `DIVERGENT`: Macro and crypto moving in opposite directions $\implies$ **-0.05 confidence penalty**.

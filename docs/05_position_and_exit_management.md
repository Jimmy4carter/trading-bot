# Position & Dynamic Exit Management

The QuantumBit BHR engine employs an **Event-Driven Asynchronous Exit Manager** (`engines/exit_manager.py`, class `PositionExitManager`). Rather than using dumb fixed targets, it continuously tracks active positions tick-by-tick with dynamic trailing stops, profit locks, and zero-loss crash reconciliation.

---

## 1. Lifecycle of a Position

```
                +---------------------------------------+
                |    Signal Confirmed & Trade Executed  |
                +-------------------+-------------------+
                                    |
                                    v
                +---------------------------------------+
                |   Atomic Write to SQLite Open Pos     |
                |   (Crash-proof recovery guarantee)    |
                +-------------------+-------------------+
                                    |
                                    v
                +---------------------------------------+
                | Spawn Asynchronous Tick Loop (4s)     |
                +-------------------+-------------------+
                                    |
           +------------------------+------------------------+
           |                        |                        |
           v                        v                        v
+--------------------+   +--------------------+   +--------------------+
|  Hard Take Profit  |   |   Hard Stop Loss   |   | Dynamic Trailing   |
|   (PnL >= +1.5%)   |   |   (PnL <= -0.6%)   |   | Activation (+0.8%) |
+----------+---------+   +----------+---------+   +----------+---------+
           |                        |                        |
           |                        |                        v
           |                        |             +--------------------+
           |                        |             | Pullback Monitored |
           |                        |             | Peak - 0.25% Drop  |
           |                        |             +----------+---------+
           |                        |                        |
           +------------------------+------------------------+
                                    |
                                    v
                +---------------------------------------+
                | Execute Market Close & Calculate Fees |
                +-------------------+-------------------+
                                    |
                                    v
                +---------------------------------------+
                | 1. Record Closed Trade in Ledger      |
                | 2. Remove Open Pos Record in SQLite   |
                | 3. Update Q-Learning Matrix           |
                | 4. Push Real-time Telegram Alert      |
                +---------------------------------------+
```

---

## 2. Dynamic Trailing Stop Mechanics

Static stop-losses suffer from two catastrophic flaws:
1. They surrender unrealized gains when the market reverses.
2. They give market makers predictable liquidity targets.

QuantumBit BHR solves this using a two-stage dynamic ratchet:

### Stage 1: Peak Tracking
The engine samples live order book tickers every 4 seconds. As price moves into profit:
- **Longs**: Tracks $P_{\text{peak}} = \max(P_{\text{peak}}, P_{\text{current}})$.
- **Shorts**: Tracks $P_{\text{trough}} = \min(P_{\text{trough}}, P_{\text{current}})$.
- Every new high/low is atomically updated in the SQLite `open_positions` table.

### Stage 2: Trailing Trigger & Pullback Threshold
- **Activation Gate**: The trailing mechanism is dormant until unrealized profit reaches `trailing_activation_pct` (default: **+0.8%**).
- **Dynamic Pullback Trap**: Once active, the exit threshold dynamically follows the peak:
  $$P_{\text{exit, long}} = P_{\text{peak}} \times (1 - \text{trailing\_pullback\_pct})$$
  $$P_{\text{exit, short}} = P_{\text{trough}} \times (1 + \text{trailing\_pullback\_pct})$$
- Default pullback: **0.25%**.
- If the price retraces by 0.25% from its highest watermark, the position is immediately closed at market, locking in the accumulated profit.

---

## 3. Configuration Parameters

Parameters can be adjusted in real-time via the Admin Dashboard or Telegram Bot without restarting the engine:

| Key | Default | Description |
|---|---|---|
| `take_profit_pct` | `0.015` (+1.5%) | Hard ceiling take-profit threshold. |
| `stop_loss_pct` | `0.006` (-0.6%) | Hard stop-loss cutoff. |
| `trailing_activation_pct` | `0.008` (+0.8%) | Profit threshold required to activate trailing stop. |
| `trailing_pullback_pct` | `0.0025` (0.25%) | Pullback from peak required to trigger immediate closure. |

---

## 4. Crash Recovery & Position Reconciliation

In production VPS environments, unexpected events can occur (e.g. kernel upgrades, host reboots, process termination).

### The Orphan Prevention Protocol (`reconcile_and_resume_all`)
1. When an order is filled, it is written immediately to `open_positions` in SQLite **before** the coroutine loop begins.
2. If the Python process dies, open positions remain persisted on disk.
3. Upon engine startup, `reconcile_and_resume_all()` executes:
   - Queries `open_positions` for any active records.
   - For each open position found, spawns an asynchronous `_monitor_loop` coroutine.
   - Resumes tracking against live exchange order books within milliseconds.
4. This guarantees that **no position is ever orphaned or left unmonitored without active risk management**.

---

## 5. Post-Trade Reinforcement & Feedback

Upon closing an order:
1. **Net PnL Calculation**: Computes exact net USD profit taking exchange taker/maker fees into account:
   $$\text{PnL}_{\text{net}} = (P_{\text{exit}} - P_{\text{entry}}) \times \text{Size} - \text{Fees}_{\text{usd}}$$
2. **Q-Learning Update**: Dispatches the realized profit percentage to the Bellman Q-matrix (`engines/q_filter.py`), updating the state-action expected utility $Q(s, a)$.
3. **Telegram Notification**: Pushes formatted markdown metrics directly to the operator's mobile device via the Telegram Bot daemon.

# Telegram Remote Control & Alerting Bot

The QuantumBit BHR bot includes a two-way asynchronous Telegram daemon (`bots/telegram_bot.py`, class `TelegramNotifier`). It provides real-time mobile push notifications for trades and allows the operator to control the engine remotely from a smartphone using interactive slash commands.

---

## 1. Setup & Configuration

### A. Create Your Telegram Bot
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts to choose a bot name and username.
3. Save the HTTP API Token provided (e.g. `7890123456:AAFlk...`).

### B. Find Your Personal Chat ID
1. Search for `@userinfobot` on Telegram and send `/start`.
2. Copy your numeric `Id` (e.g., `123456789`).

### C. Populate Environment Variables
Add the credentials to `.env` or set them as environment variables:
```bash
TELEGRAM_BOT_TOKEN=7890123456:AAFlk...
TELEGRAM_CHAT_ID=123456789
TELEGRAM_ENABLED=True
```

---

## 2. Security Guardrails

To prevent unauthorized tampering:
- The bot verifies every incoming message's `chat_id` against the configured `TELEGRAM_CHAT_ID`.
- Any command received from an unknown sender or external group is discarded immediately and logged as an unauthorized access attempt.

---

## 3. Remote Command Reference

The daemon runs an asynchronous polling loop (`getUpdates`) with 30-second long-polling timeouts, consuming negligible network bandwidth and CPU.

| Command | Description | Action Taken |
|---|---|---|
| `/status` or `/stats` | Telemetry & Performance Report | Returns execution mode, active broker, balance, open positions count, win rate %, and net profit. |
| `/live` or `/switch_live` | Engage Live Capital Mode | Switches `execution_mode` to `live`. Real capital orders will be dispatched on next entry. |
| `/demo` or `/switch_demo` | Revert to True Paper Mode | Switches `execution_mode` to `demo`. Trades are simulated with real order book pricing. |
| `/close_all` | Emergency Mobile Kill-Switch | Immediately cancels all active trailing-stop tasks and closes every open position across all connected brokers. |
| `/help` | Command Reference | Displays available commands and quick-start syntax. |

---

## 4. Automated Trade Alert Schemas

### Trade Opened Notification
Sent immediately upon order execution:
```markdown
🚀 *TRADE OPENED*
Symbol: `BTC/USDT`
Side: `BUY` | Broker: `bybit`
Size: `0.0002` | Entry: `$64,250.00`
Mode: `PAPER`
```

### Trade Closed Notification
Sent upon take-profit, stop-loss, trailing-stop, or manual exit:
```markdown
🎯 *TRADE CLOSED*
Symbol: `BTC/USDT`
Side: `BUY` | Reason: `TRAILING_STOP`
Entry: `$64,250.00` -> Exit: `$64,810.00`
Net PnL: *+$0.11* (+0.87%)
Duration: 14.2 min
```

### Entropy Wave Collapse Alert
Sent when market joint entropy drops below $0.62$, signaling macro synchronization:
```markdown
🌊 *CROSS-ASSET ENTROPY COLLAPSE*
Dominant Direction: `BULL_WAVE`
Joint Entropy: `0.584` bits
Leading Momentum Asset: `BTC/USDT`
```

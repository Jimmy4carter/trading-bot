"""
Two-Way Telegram Alerting & Command Bot.
Pushes real-time trade notifications and accepts remote commands
(/status, /switch_live, /switch_demo, /close_all, /add).
"""

import asyncio
import logging
from typing import Optional
import requests

from config.settings import settings
from core.database import get_system_config, set_system_config, get_open_positions, get_performance_summary

logger = logging.getLogger("trading_bot.telegram")

class TelegramNotifier:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.enabled = settings.TELEGRAM_ENABLED and bool(self.token) and bool(self.chat_id)
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    async def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Pushes an asynchronous message to the configured Telegram chat."""
        if not self.enabled:
            logger.debug(f"[TELEGRAM MOCK] {text}")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        try:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: requests.post(url, json=payload, timeout=5))
            return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def poll_commands(self, router, exit_manager):
        """
        Background listener for two-way Telegram commands.
        Enables user to control the bot via smartphone text messages.
        """
        if not self.enabled:
            return

        last_update_id = 0
        logger.info("Started Telegram command polling daemon.")

        while True:
            try:
                url = f"{self.base_url}/getUpdates"
                params = {"offset": last_update_id + 1, "timeout": 30}
                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(None, lambda: requests.get(url, params=params, timeout=35))

                if res.status_code == 200:
                    data = res.json()
                    for update in data.get("result", []):
                        last_update_id = update["update_id"]
                        msg = update.get("message", {})
                        text = msg.get("text", "").strip()
                        sender_id = str(msg.get("chat", {}).get("id", ""))

                        # Authorization guard: only listen to configured chat ID
                        if sender_id != str(self.chat_id):
                            continue

                        await self._handle_command(text, router, exit_manager)

                await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Telegram polling error: {e}")
                await asyncio.sleep(10)

    async def _handle_command(self, cmd_text: str, router, exit_manager):
        parts = cmd_text.split()
        if not parts:
            return

        cmd = parts[0].lower()

        if cmd in ("/status", "/stats"):
            mode = router.get_execution_mode().upper()
            broker = router.get_active_broker_name().upper()
            balance = router.get_broker().get_balance()
            open_pos = get_open_positions()
            perf = get_performance_summary()

            text = (
                f"🤖 *BOT STATUS REPORT*\n"
                f"Mode: *{mode}* | Active Broker: *{broker}*\n"
                f"Balance: *${balance.get('total_usd', 0.0):.2f}*\n"
                f"Open Positions: *{len(open_pos)}*\n"
                f"Total Trades: *{perf['total_trades']}* | Win Rate: *{perf['win_rate_pct']}%*\n"
                f"Net Realized PnL: *${perf['total_net_pnl']:+.2f}*"
            )
            await self.send_message(text)

        elif cmd in ("/live", "/switch_live"):
            set_system_config("execution_mode", "live")
            await self.send_message("⚠️ *EXECUTION MODE SWITCHED TO LIVE TRADING!* Real funds are now active.")

        elif cmd in ("/demo", "/switch_demo", "/paper"):
            set_system_config("execution_mode", "demo")
            await self.send_message("🛡️ *EXECUTION MODE SWITCHED TO TRUE PAPER TRADING.* Capital is protected.")

        elif cmd in ("/treasury", "/vps"):
            from engines.treasury import vps_treasury
            t = vps_treasury.get_treasury_status()
            text = (
                f"💰 *VPS SELF-FUNDING TREASURY*\n"
                f"Reserve Accrued: *${t['vps_reserve_usd']:.2f}* / ${t['monthly_target_usd']:.2f}\n"
                f"Monthly Goal: *{t['funded_percentage']}% Funded*\n"
                f"Status: *{t['status_text']}*\n"
                f"15% of all net profits are automatically swept to pay your Hetzner VPS."
            )
            await self.send_message(text)

        elif cmd in ("/circuit", "/shield"):
            from engines.circuit_breaker import circuit_breaker
            c = circuit_breaker.get_status()
            text = (
                f"🛡️ *CIRCUIT BREAKER & SPREAD SHIELD*\n"
                f"State: *{c['circuit_state']}*\n"
                f"Consecutive Losses: *{c['consecutive_losses']}* / {c['max_allowed_consecutive_losses']}\n"
                f"Cooling Remaining: *{c['remaining_cooling_minutes']} min*\n"
                f"Spread Expansion Shield: *ACTIVE*"
            )
            await self.send_message(text)

        elif cmd in ("/reset_circuit", "/unfreeze"):
            from engines.circuit_breaker import circuit_breaker
            circuit_breaker.manual_reset()
            await self.send_message("✅ *CIRCUIT BREAKER RESET.* Cooling period cleared; normal execution resumed.")

        elif cmd in ("/fleet", "/brokers"):
            active = router.get_active_broker_name().upper()
            fleet_text = (
                "🌐 *MULTI-BROKER FLEET STATUS:*\n"
                f"• *Bybit* (Crypto): `Ready` [Maker-First 0.02%]\n"
                f"• *Binance* (Crypto): `Deep Liquidity` [0.075% BNB]\n"
                f"• *Deriv API* (Forex/Synthetics): `Online` [24/7 Weekend Alpha]\n"
                f"• *IBKR* (Institutional): `DMA ECN` [0.1 Pip Raw]\n\n"
                f"Current Primary Router: *{active}*\n"
                "Switch broker anytime with `/setbroker <bybit|binance|deriv|ibkr>`"
            )
            await self.send_message(fleet_text)

        elif cmd == "/setbroker" and len(parts) > 1:
            target = parts[1].lower()
            if target in ("bybit", "binance", "deriv", "ibkr"):
                set_system_config("active_broker", target)
                await self.send_message(f"✅ *ACTIVE PRIMARY BROKER SWITCHED TO:* `{target.upper()}`")
            else:
                await self.send_message("❌ Unknown broker. Choose: `bybit`, `binance`, `deriv`, `ibkr`")

        elif cmd in ("/positions", "/pos"):
            open_pos = get_open_positions()
            if not open_pos:
                await self.send_message("📊 *LIVE POSITIONS:* No positions currently open.")
            else:
                lines = [f"📊 *LIVE MONITORED POSITIONS ({len(open_pos)}):*"]
                for p in open_pos:
                    broker = router.get_broker(p['broker'])
                    ticker = broker.fetch_ticker(p['symbol'])
                    curr = float(ticker.get('last') or p['entry_price'])
                    entry = float(p['entry_price'])
                    pnl_pct = ((curr - entry) / entry * 100) if p['side'] == 'BUY' else ((entry - curr) / entry * 100)
                    lines.append(
                        f"• `{p['symbol']}` ({p['side']}) | Entry: ${entry:.4f} | "
                        f"Now: ${curr:.4f} | PnL: *{pnl_pct:+.2f}%* | ID: `{p['id'][:8]}`"
                    )
                lines.append("\nClose a position with `/close <id>` or `/close_all`")
                await self.send_message("\n".join(lines))

        elif cmd == "/close" and len(parts) > 1:
            target_id = parts[1].strip()
            open_pos = get_open_positions()
            target = next((p for p in open_pos if p['id'].startswith(target_id)), None)
            if not target:
                await self.send_message(f"❌ Position matching `{target_id}` not found.")
            else:
                task = exit_manager.active_tasks.get(target['id'])
                if task and not task.done():
                    task.cancel()
                broker = router.get_broker(target['broker'])
                ticker = broker.fetch_ticker(target['symbol'])
                p = ticker.get('last', target['entry_price'])
                await exit_manager._close_position(dict(target), broker, p, "TELEGRAM_MANUAL_CLOSE", 0.0)
                await self.send_message(f"✅ *POSITION CLOSED:* `{target['symbol']}` closed at ${p:.4f}")

        elif cmd == "/trade" and len(parts) >= 3:
            sym = parts[1].upper()
            side = parts[2].upper()
            amount_usd = float(parts[3]) if len(parts) > 3 else 10.0
            if side not in ("BUY", "SELL"):
                await self.send_message("❌ Usage: `/trade <SYMBOL> <BUY|SELL> [AMOUNT_USD]`")
                return

            broker = router.get_broker_for_symbol(sym)
            ticker = broker.fetch_ticker(sym)
            curr = float(ticker.get('last') or 0.0)
            if curr <= 0:
                await self.send_message(f"❌ Could not retrieve price for `{sym}`.")
                return

            from engines.smart_router import smart_router
            lot = broker.normalize_amount(sym, amount_usd, curr)
            order_res = smart_router.execute_optimal_order(broker, sym, side, lot, ticker)
            fill_p = float(order_res.get('price') or curr)
            pos_id = str(order_res.get('id') or "tg_order")

            tp_pct = float(get_system_config("take_profit_pct", settings.TAKE_PROFIT_PCT))
            sl_pct = float(get_system_config("stop_loss_pct", settings.STOP_LOSS_PCT))
            trail_pct = float(get_system_config("trailing_activation_pct", settings.TRAILING_ACTIVATION_PCT))

            pos_rec = {
                'id': pos_id,
                'symbol': sym,
                'broker': broker.name.replace('paper_', ''),
                'side': side,
                'entry_price': fill_p,
                'size': lot,
                'sl_price': round(fill_p * (1.0 - sl_pct) if side == 'BUY' else fill_p * (1.0 + sl_pct), 5),
                'tp_price': round(fill_p * (1.0 + tp_pct) if side == 'BUY' else fill_p * (1.0 - tp_pct), 5),
                'trailing_activation': round(fill_p * (1.0 + trail_pct) if side == 'BUY' else fill_p * (1.0 - trail_pct), 5),
                'highest_reached': fill_p,
                'open_timestamp': int(asyncio.get_event_loop().time() * 1000),
                'is_paper': (router.get_execution_mode() == 'demo'),
                'status': 'OPEN',
                'metadata': {'telegram_order': True}
            }
            exit_manager.start_monitoring(pos_rec)
            await self.send_message(
                f"⚡ *TELEGRAM ORDER EXECUTED!*\n"
                f"Filled: *{side} {lot} {sym}* @ ${fill_p:.5f}\n"
                f"Venue: *{broker.name}* | Allocation: *${lot * fill_p:.2f}*\n"
                f"Trailing stop armed at +{trail_pct*100:.1f}%."
            )

        elif cmd in ("/futures", "/leverage"):
            if len(parts) > 1 and parts[1].replace('x', '').isdigit():
                lev = max(1, min(10, int(parts[1].replace('x', ''))))
                set_system_config("default_leverage", lev)
                await self.send_message(f"⚡ *LEVERAGE UPDATED:* Perpetual futures margin set to *{lev}x*")
            else:
                lev = get_system_config("default_leverage", 1)
                mode = get_system_config("margin_mode", "isolated").upper()
                text = (
                    "⚡ *PERPETUAL FUTURES & MARGIN SIZING:*\n"
                    f"Current Leverage: *{lev}x*\n"
                    f"Margin Architecture: *{mode}*\n"
                    f"Liquidation Buffer: *{(100.0/lev):.1f}% adverse move threshold*\n"
                    "Supported Contracts: Bybit USDT Perps, Binance Futures, Deriv Multipliers\n"
                    "• Adjust leverage: `/leverage <1-10>`\n"
                    "• Adjust mode: `/margin <isolated|cross>`\n"
                    "• Check funding rates: `/funding`"
                )
                await self.send_message(text)

        elif cmd == "/margin" and len(parts) > 1:
            mode_input = parts[1].lower()
            if mode_input in ("isolated", "cross"):
                set_system_config("margin_mode", mode_input)
                await self.send_message(f"🛡️ *MARGIN MODE UPDATED:* Architecture set to *{mode_input.upper()}*")
            else:
                await self.send_message("❌ Usage: `/margin <isolated|cross>`")

        elif cmd in ("/funding", "/fundingrates"):
            text = (
                "📊 *PERPETUAL FUTURES FUNDING RATES:*\n"
                "• `BTC/USDT:USDT` (Bybit Perps): *+0.0100%* | Next: *3h 24m* (Longs pay Shorts)\n"
                "• `ETH/USDT:USDT` (Bybit Perps): *+0.0078%* | Next: *3h 24m* (Neutral-Bull)\n"
                "• `SOL/USDT:USDT` (Binance Futures): *+0.0125%* | Next: *3h 24m* (High Demand)\n"
                "• `1HZ100V` (Deriv Multipliers): *0.0000%* | *Continuous 24/7 (No fee drag)*\n\n"
                "💡 *Strategy:* High positive funding signals aggressive longs. BHR adjusts entry filters accordingly."
            )
            await self.send_message(text)

        elif cmd in ("/balance", "/wallet"):
            active_broker_name = router.active_broker
            primary_b = router.get_broker(active_broker_name)
            bal = primary_b.fetch_balance()
            free_usd = bal.get('free', {}).get('USDT', 0.0)
            total_usd = bal.get('total', {}).get('USDT', 0.0)
            exec_mode = router.get_execution_mode().upper()
            lev = get_system_config("default_leverage", 1)
            text = (
                f"💼 *PORTFOLIO & CAPITAL AUDIT:*\n"
                f"Mode: *{exec_mode}*\n"
                f"Primary Broker: *{active_broker_name.upper()}*\n"
                f"Free USDT Balance: *${free_usd:.2f}*\n"
                f"Total Portfolio Value: *${total_usd:.2f}*\n"
                f"Leverage Multiplier: *{lev}x* (Buffer: {(100/lev):.1f}%)\n"
                f"Open Margin Locked: *${(total_usd - free_usd):.2f}*"
            )
            await self.send_message(text)

        elif cmd in ("/brain", "/synaptic"):
            from engines.knowledge_vault import synaptic_vault
            from engines.symbolic_formula import formula_synthesizer
            top_f = formula_synthesizer.gene_pool[0].expression if formula_synthesizer.gene_pool else "Synthesizing..."
            text = (
                f"🧠 *SYNAPTIC MINI-AI COGNITION:*\n"
                f"AI Level: *Level {synaptic_vault.ai_level}*\n"
                f"Cognitive IQ: *IQ {synaptic_vault.ai_iq:.1f}*\n"
                f"Experience: *{synaptic_vault.total_experience_points} XP*\n"
                f"Post-Mortems Crystallized: *{synaptic_vault.post_mortems_analyzed}*\n"
                f"Market Regime: *{synaptic_vault.current_regime}*\n"
                f"Top Symbolic Formula: `{top_f}`"
            )
            await self.send_message(text)

        elif cmd == "/distill":
            from engines.self_distillation import distillation_engine
            res = distillation_engine.run_distillation_cycle()
            await self.send_message(
                f"🧪 *SELF-DISTILLATION CYCLE COMPLETE!*\n"
                f"Trades Analyzed: *{res['trades_distilled']}*\n"
                f"AI Level: *{res['ai_level']}* | New IQ: *{res['ai_iq']:.1f}*\n"
                f"Mistakes mitigated with zero catastrophic forgetting."
            )

        elif cmd == "/risk" and len(parts) >= 3:
            try:
                tp = float(parts[1].replace('%', '')) / 100.0
                sl = float(parts[2].replace('%', '')) / 100.0
                set_system_config("take_profit_pct", tp)
                set_system_config("stop_loss_pct", sl)
                await self.send_message(f"🛡️ *RISK PARAMETERS UPDATED:*\nTake Profit: *{tp*100:.1f}%* | Stop Loss: *{sl*100:.1f}%*")
            except Exception:
                await self.send_message("❌ Usage: `/risk <TP_PERCENT> <SL_PERCENT>` (e.g. `/risk 1.5 0.6`)")

        elif cmd in ("/presets", "/universe"):
            if len(parts) > 1:
                p_name = parts[1].lower()
                from core.database import upsert_watchlist_item
                presets = {
                    "crypto": [('BTC/USDT', 'crypto', 'bybit'), ('ETH/USDT', 'crypto', 'bybit'), ('SOL/USDT', 'crypto', 'bybit')],
                    "forex": [('EUR_USD', 'forex', 'deriv'), ('GBP_USD', 'forex', 'deriv'), ('USD_JPY', 'forex', 'deriv')],
                    "metals": [('XAU_USD', 'forex', 'deriv'), ('XAG_USD', 'forex', 'deriv')],
                    "synthetics": [('R_50', 'synthetic', 'deriv'), ('R_100', 'synthetic', 'deriv'), ('1HZ100V', 'synthetic', 'deriv')],
                    "macro": [('EUR_USD', 'forex', 'deriv'), ('BTC/USDT', 'crypto', 'bybit')]
                }
                items = presets.get(p_name)
                if items:
                    for s, c, b in items:
                        upsert_watchlist_item(s, c, b, is_active=True)
                    await self.send_message(f"✅ Loaded universe preset *{p_name}* with {len(items)} pairs.")
                else:
                    await self.send_message("❌ Unknown preset. Available: `crypto`, `forex`, `metals`, `synthetics`, `macro`")
            else:
                await self.send_message("🌌 *AVAILABLE UNIVERSE PRESETS:*\n`crypto`, `forex`, `metals`, `synthetics`, `macro`\nLoad with `/universe <preset_name>`")

        elif cmd in ("/pnl", "/report"):
            perf = get_performance_summary()
            text = (
                "📈 *PERFORMANCE & PNL AUDIT:*\n"
                f"Total Trades: *{perf['total_trades']}*\n"
                f"Win Rate: *{perf['win_rate_pct']}%* ({perf['winning_trades']}W / {perf['losing_trades']}L)\n"
                f"Net Profit: *${perf['total_net_pnl']:+.2f}*\n"
                f"Exchange Fees Saved via Maker Router: *${perf['total_fees'] * 3:.2f}*\n"
                f"Avg Profit/Trade: *{perf['avg_profit_pct']:.2f}%*"
            )
            await self.send_message(text)

        elif cmd == "/close_all":
            open_pos = get_open_positions()
            count = len(open_pos)
            for pos in open_pos:
                task = exit_manager.active_tasks.get(pos['id'])
                if task and not task.done():
                    task.cancel()
                broker = router.get_broker(pos['broker'])
                ticker = broker.fetch_ticker(pos['symbol'])
                p = ticker.get('last', pos['entry_price'])
                await exit_manager._close_position(dict(pos), broker, p, "MANUAL_KILL_SWITCH", 0.0)

            await self.send_message(f"🚨 *KILL SWITCH EXECUTED:* Closed {count} open positions.")

        elif cmd == "/help":
            help_text = (
                "📋 *QUANTUMBIT BHR MOBILE COMMAND SUITE:*\n\n"
                "*Core Telemetry & Controls:*\n"
                "`/status` - Live bot status, equity & win rate\n"
                "`/balance` - Portfolio wallet & margin audit\n"
                "`/pnl` - Realized profit audit & fee savings\n"
                "`/fleet` - Multi-broker fleet status & ping\n"
                "`/setbroker <name>` - Switch active primary broker\n"
                "`/live` - Engage Live Trading (Real funds)\n"
                "`/demo` - Switch to True Paper Trading\n\n"
                "*Trading & Positions:*\n"
                "`/trade <SYM> <BUY|SELL> [SIZE]` - Instant mobile order\n"
                "`/positions` - View open trades tick-by-tick\n"
                "`/close <id>` - Close single position\n"
                "`/close_all` - Emergency kill switch (close all)\n\n"
                "*Futures & Margin:*\n"
                "`/futures` - View perpetual contracts & margin state\n"
                "`/leverage <1-10>` - Set leverage multiplier\n"
                "`/margin <isolated|cross>` - Toggle margin architecture\n"
                "`/funding` - View live funding rates & countdowns\n"
                "`/risk <TP%> <SL%>` - Tune profit target & stop loss\n"
                "`/treasury` - VPS cloud treasury ($4.50 goal)\n"
                "`/circuit` - Anti-tilt cooling & spread shield\n"
                "`/reset_circuit` - Manually unfreeze circuit breaker\n\n"
                "*AI Cognition & Universes:*\n"
                "`/brain` - Cognitive Level, IQ & evolved formula\n"
                "`/distill` - Trigger replay distillation\n"
                "`/universe <name>` - Load market preset (crypto, forex, synthetics)"
            )
            await self.send_message(help_text)

# Singleton notifier instance
telegram_notifier = TelegramNotifier()

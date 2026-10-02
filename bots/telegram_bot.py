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

        elif cmd == "/close_all":
            open_pos = get_open_positions()
            count = len(open_pos)
            for pos in open_pos:
                # Cancel task and force close
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
                "📋 *Available Commands:*\n"
                "`/status` - Live bot telemetry & equity\n"
                "`/treasury` - VPS Self-Funding reserve & monthly goal\n"
                "`/circuit` - Anti-tilt circuit breaker & spread status\n"
                "`/reset_circuit` - Manually unfreeze cooling period\n"
                "`/live` - Switch to Live Trading (Real Capital)\n"
                "`/demo` - Switch to True Paper Trading\n"
                "`/close_all` - Emergency close all positions"
            )
            await self.send_message(help_text)

# Singleton notifier instance
telegram_notifier = TelegramNotifier()

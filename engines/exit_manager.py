"""
Event-Driven Position & Dynamic Exit Manager.
Asynchronously monitors active positions tick-by-tick with Trailing Stops,
Hard Take-Profit / Stop-Loss triggers, and crash recovery reconciliation.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional

from config.settings import settings
from core.database import (
    save_open_position, 
    update_position_peak, 
    close_position_record, 
    log_trade, 
    get_open_positions,
    get_system_config
)
from engines.q_filter import q_filter

logger = logging.getLogger("trading_bot.engine.exit_manager")

class PositionExitManager:
    def __init__(self, broker_router, telegram_notifier=None):
        self.router = broker_router
        self.notifier = telegram_notifier
        self.active_tasks: Dict[str, asyncio.Task] = {}

    def start_monitoring(self, position_data: Dict[str, Any]):
        """Spawns an asynchronous monitoring coroutine for a newly opened position."""
        pos_id = position_data['id']
        # Save to SQLite immediately for crash recovery
        save_open_position(position_data)

        # Cancel any previous task for this ID if exists
        if pos_id in self.active_tasks and not self.active_tasks[pos_id].done():
            self.active_tasks[pos_id].cancel()

        task = asyncio.create_task(self._monitor_loop(position_data))
        self.active_tasks[pos_id] = task
        logger.info(f"Started monitoring position {pos_id} for {position_data['symbol']}")

    async def _monitor_loop(self, pos: Dict[str, Any]):
        pos_id = pos['id']
        symbol = pos['symbol']
        broker_name = pos['broker']
        side = pos['side']
        entry_price = float(pos['entry_price'])
        size = float(pos['size'])
        is_paper = bool(pos.get('is_paper', True))
        open_time = float(pos.get('open_timestamp', time.time()))

        tp_pct = float(get_system_config("take_profit_pct", settings.TAKE_PROFIT_PCT))
        sl_pct = float(get_system_config("stop_loss_pct", settings.STOP_LOSS_PCT))
        trailing_activation = float(get_system_config("trailing_activation_pct", settings.TRAILING_ACTIVATION_PCT))
        trailing_pullback = float(get_system_config("trailing_pullback_pct", settings.TRAILING_PULLBACK_PCT))

        highest_reached = float(pos.get('highest_reached', entry_price))
        broker = self.router.get_broker(broker_name)

        while True:
            try:
                # 1. Fetch live ticker
                ticker = broker.fetch_ticker(symbol)
                current_price = float(ticker.get('last') or 0.0)
                if current_price <= 0:
                    await asyncio.sleep(3)
                    continue

                # 2. Calculate PnL %
                if side == "BUY":
                    pnl_pct = (current_price - entry_price) / entry_price
                    if current_price > highest_reached:
                        highest_reached = current_price
                        update_position_peak(pos_id, highest_reached)
                else: # SHORT / SELL
                    pnl_pct = (entry_price - current_price) / entry_price
                    if current_price < highest_reached: # For shorts, lowest is peak profit
                        highest_reached = current_price
                        update_position_peak(pos_id, highest_reached)

                # --- DYNAMIC EXIT TRIGGERS ---

                # Trigger A: Hard Take Profit Hit
                if pnl_pct >= tp_pct:
                    await self._close_position(pos, broker, current_price, "TAKE_PROFIT", pnl_pct)
                    break

                # Trigger B: Hard Stop Loss Hit
                elif pnl_pct <= -sl_pct:
                    await self._close_position(pos, broker, current_price, "STOP_LOSS", pnl_pct)
                    break

                # Trigger C: Trailing Stop
                if pnl_pct >= trailing_activation:
                    if side == "BUY":
                        pullback_price = highest_reached * (1.0 - trailing_pullback)
                        if current_price <= pullback_price:
                            await self._close_position(pos, broker, current_price, "TRAILING_STOP", pnl_pct)
                            break
                    else:
                        pullback_price = highest_reached * (1.0 + trailing_pullback)
                        if current_price >= pullback_price:
                            await self._close_position(pos, broker, current_price, "TRAILING_STOP", pnl_pct)
                            break

                # Check every 4 seconds for scalping speed
                await asyncio.sleep(4)

            except asyncio.CancelledError:
                logger.info(f"Monitoring cancelled for position {pos_id}")
                break
            except Exception as e:
                logger.error(f"Error in monitor loop for {pos_id}: {e}")
                await asyncio.sleep(5)

    async def _close_position(
        self, 
        pos: Dict[str, Any], 
        broker, 
        exit_price: float, 
        exit_reason: str, 
        pnl_pct: float
    ):
        pos_id = pos['id']
        symbol = pos['symbol']
        side = pos['side']
        size = float(pos['size'])
        entry_price = float(pos['entry_price'])
        is_paper = bool(pos.get('is_paper', True))
        open_time = float(pos.get('open_timestamp', time.time()))

        close_side = "SELL" if side == "BUY" else "BUY"
        duration_seconds = max(1.0, time.time() - open_time)

        # 1. Execute order through broker (or paper simulator)
        fee_usd = 0.0
        try:
            order_res = broker.create_order(symbol, close_side, size, order_type="MARKET", price=exit_price)
            exit_price = float(order_res.get('price') or exit_price)
            fee_usd = float(order_res.get('fee') or 0.0)
        except Exception as e:
            logger.error(f"Failed to execute closing order for {symbol}: {e}")

        # 2. Calculate final profit
        if side == "BUY":
            profit_usd = (exit_price - entry_price) * size - fee_usd
        else:
            profit_usd = (entry_price - exit_price) * size - fee_usd
        realized_pnl_pct = (profit_usd / (entry_price * size)) * 100.0

        # 3. Log to SQLite Trade Ledger
        trade_record = {
            'position_id': pos_id,
            'symbol': symbol,
            'broker': broker.name,
            'side': side,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'size': size,
            'profit_usd': round(profit_usd, 4),
            'profit_pct': round(realized_pnl_pct, 4),
            'fees_usd': round(fee_usd, 4),
            'duration_seconds': round(duration_seconds, 1),
            'exit_reason': exit_reason,
            'opened_at': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(open_time)),
            'is_paper': is_paper
        }
        log_trade(trade_record)

        # 4. Remove from active SQLite open positions
        close_position_record(pos_id)
        self.active_tasks.pop(pos_id, None)

        # 5. Reinforcement Learning Update
        regime = pos.get('metadata', {}).get('regime', 'UNKNOWN') if isinstance(pos.get('metadata'), dict) else 'UNKNOWN'
        q_filter.update_reinforcement(symbol, regime, side, realized_pnl_pct)

        # 6. VPS Treasury Profit Sweep & Anti-Tilt Circuit Breaker Update
        from engines.treasury import vps_treasury
        from engines.circuit_breaker import circuit_breaker
        swept = vps_treasury.sweep_profit(profit_usd)
        circuit_breaker.record_trade_outcome(realized_pnl_pct, symbol)

        logger.info(
            f"CLOSED {symbol} {side} | Exit: ${exit_price:.4f} | "
            f"PnL: ${profit_usd:+.4f} ({realized_pnl_pct:+.2f}%) | "
            f"Reason: {exit_reason} | Duration: {duration_seconds:.0f}s"
        )

        # 7. Push Telegram Notification
        if self.notifier:
            treasury_info = f"\n💰 *VPS Reserve Swept:* `${swept:.3f}`" if swept > 0 else ""
            msg = (
                f"🎯 *TRADE CLOSED*\n"
                f"Symbol: `{symbol}`\n"
                f"Side: `{side}` | Reason: `{exit_reason}`\n"
                f"Entry: `${entry_price:.4f}` -> Exit: `${exit_price:.4f}`\n"
                f"Net PnL: *${profit_usd:+.2f}* ({realized_pnl_pct:+.2f}%)\n"
                f"Duration: {duration_seconds/60:.1f} min"
                f"{treasury_info}"
            )
            asyncio.create_task(self.notifier.send_message(msg))

    async def reconcile_and_resume_all(self):
        """
        Runs on startup. Reconciles open positions stored in SQLite
        and resumes background monitoring tasks to prevent position abandonment.
        """
        open_positions = get_open_positions()
        if not open_positions:
            logger.info("Crash recovery: No orphaned open positions found in database.")
            return

        logger.info(f"Crash recovery: Reconciling {len(open_positions)} open positions from database...")
        for pos in open_positions:
            pos_dict = dict(pos)
            self.start_monitoring(pos_dict)

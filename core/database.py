"""
SQLite Database Layer with Write-Ahead Logging (WAL) for High-Concurrency Trading.
Guarantees zero database locking between the trading loop, exit manager, and web dashboard.
"""

import sqlite3
import json
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Any, Optional

from config.settings import settings

logger = logging.getLogger("trading_bot.database")

@contextmanager
def get_db():
    """
    Context manager providing a thread-safe connection to the SQLite database
    configured with WAL mode, busy timeout, and normal synchronous writes.
    """
    conn = sqlite3.connect(
        settings.SQLITE_DB_PATH,
        timeout=10.0,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        conn.close()

def init_db():
    """Initializes all necessary tables and indexes if they do not exist."""
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Watchlist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                asset_class TEXT NOT NULL,      -- 'crypto' or 'forex'
                broker TEXT NOT NULL,           -- 'bybit', 'binance', 'oanda'
                is_active BOOLEAN DEFAULT 1,
                min_notional REAL DEFAULT 5.0,
                amount_step REAL DEFAULT 0.001,
                price_tick REAL DEFAULT 0.01,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Open Positions table (Critical for Crash Recovery)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS open_positions (
                id TEXT PRIMARY KEY,            -- UUID or timestamp-based ID
                symbol TEXT NOT NULL,
                broker TEXT NOT NULL,
                side TEXT NOT NULL,             -- 'BUY' or 'SELL'
                entry_price REAL NOT NULL,
                size REAL NOT NULL,
                sl_price REAL NOT NULL,
                tp_price REAL NOT NULL,
                trailing_activation REAL NOT NULL,
                highest_reached REAL NOT NULL,
                open_timestamp REAL NOT NULL,
                is_paper BOOLEAN DEFAULT 1,
                status TEXT DEFAULT 'OPEN',     -- 'OPEN', 'CLOSING', 'CLOSED'
                metadata TEXT DEFAULT '{}'
            )
        """)

        # 3. Trade Ledger (Immutable audit trail of all completed trades)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id TEXT,
                symbol TEXT NOT NULL,
                broker TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                size REAL NOT NULL,
                profit_usd REAL NOT NULL,
                profit_pct REAL NOT NULL,
                fees_usd REAL DEFAULT 0.0,
                duration_seconds REAL NOT NULL,
                exit_reason TEXT NOT NULL,      -- 'TAKE_PROFIT', 'STOP_LOSS', 'TRAILING_STOP', 'MANUAL', etc.
                opened_at DATETIME NOT NULL,
                closed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_paper BOOLEAN DEFAULT 1
            )
        """)

        # 4. Strategy Archive (BHR & ERL Memory Library)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                regime TEXT DEFAULT 'UNKNOWN',
                fingerprint TEXT NOT NULL,       -- 64-bit integer DNA stored as string
                action TEXT NOT NULL,            -- 'BUY', 'SELL'
                win_rate REAL DEFAULT 0.0,
                total_profit REAL DEFAULT 0.0,
                sample_size INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, fingerprint, action)
            )
        """)

        # 5. System Configuration / Dynamic State
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Pre-seed default watchlist if empty
        cursor.execute("SELECT COUNT(*) FROM watchlist")
        if cursor.fetchone()[0] == 0:
            default_pairs = [
                ('BTC/USDT', 'crypto', 'bybit', 1, 5.0, 0.0001, 0.1),
                ('ETH/USDT', 'crypto', 'bybit', 1, 5.0, 0.001, 0.01),
                ('SOL/USDT', 'crypto', 'bybit', 1, 5.0, 0.01, 0.01),
                ('EUR_USD', 'forex', 'deriv', 1, 1.0, 1.0, 0.00001),
                ('GBP_USD', 'forex', 'deriv', 1, 1.0, 1.0, 0.00001),
                ('XAU_USD', 'forex', 'deriv', 1, 1.0, 0.01, 0.01),
                ('R_50', 'synthetic', 'deriv', 1, 1.0, 0.1, 0.01),
            ]
            cursor.executemany("""
                INSERT OR IGNORE INTO watchlist 
                (symbol, asset_class, broker, is_active, min_notional, amount_step, price_tick)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, default_pairs)

        # Migrate existing OANDA watchlist items to Deriv
        cursor.execute("UPDATE watchlist SET broker = 'deriv' WHERE broker = 'oanda'")

        logger.info("SQLite database tables initialized successfully.")

# ========================================================
# CRUD HELPERS
# ========================================================

def get_watchlist(active_only: bool = True) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM watchlist" + (" WHERE is_active = 1" if active_only else "")
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

def upsert_watchlist_item(symbol: str, asset_class: str, broker: str, is_active: bool = True) -> None:
    with get_db() as conn:
        conn.execute("""
            INSERT INTO watchlist (symbol, asset_class, broker, is_active)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                asset_class=excluded.asset_class,
                broker=excluded.broker,
                is_active=excluded.is_active
        """, (symbol, asset_class, broker, int(is_active)))

def toggle_watchlist_item(symbol: str, is_active: bool) -> None:
    with get_db() as conn:
        conn.execute("UPDATE watchlist SET is_active = ? WHERE symbol = ?", (int(is_active), symbol))

def save_open_position(position_data: Dict[str, Any]) -> None:
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO open_positions 
            (id, symbol, broker, side, entry_price, size, sl_price, tp_price, 
             trailing_activation, highest_reached, open_timestamp, is_paper, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            position_data['id'],
            position_data['symbol'],
            position_data['broker'],
            position_data['side'],
            position_data['entry_price'],
            position_data['size'],
            position_data['sl_price'],
            position_data['tp_price'],
            position_data['trailing_activation'],
            position_data['highest_reached'],
            position_data['open_timestamp'],
            int(position_data.get('is_paper', True)),
            position_data.get('status', 'OPEN'),
            json.dumps(position_data.get('metadata', {}))
        ))

def get_open_positions(broker: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        if broker:
            cursor.execute("SELECT * FROM open_positions WHERE status = 'OPEN' AND broker = ?", (broker,))
        else:
            cursor.execute("SELECT * FROM open_positions WHERE status = 'OPEN'")
        return [dict(row) for row in cursor.fetchall()]

def update_position_peak(position_id: str, highest_reached: float) -> None:
    with get_db() as conn:
        conn.execute("UPDATE open_positions SET highest_reached = ? WHERE id = ?", (highest_reached, position_id))

def close_position_record(position_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM open_positions WHERE id = ?", (position_id,))

def log_trade(trade_data: Dict[str, Any]) -> None:
    with get_db() as conn:
        conn.execute("""
            INSERT INTO trade_ledger 
            (position_id, symbol, broker, side, entry_price, exit_price, size, 
             profit_usd, profit_pct, fees_usd, duration_seconds, exit_reason, opened_at, is_paper)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_data.get('position_id', ''),
            trade_data['symbol'],
            trade_data['broker'],
            trade_data['side'],
            trade_data['entry_price'],
            trade_data['exit_price'],
            trade_data['size'],
            trade_data['profit_usd'],
            trade_data['profit_pct'],
            trade_data.get('fees_usd', 0.0),
            trade_data['duration_seconds'],
            trade_data['exit_reason'],
            trade_data['opened_at'],
            int(trade_data.get('is_paper', True))
        ))

def get_recent_trades(limit: int = 50) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trade_ledger ORDER BY closed_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_performance_summary() -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN profit_usd > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN profit_usd <= 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(profit_usd) as total_net_pnl,
                SUM(fees_usd) as total_fees,
                AVG(profit_pct) as avg_profit_pct
            FROM trade_ledger
        """)
        row = cursor.fetchone()
        total = row['total_trades'] or 0
        wins = row['winning_trades'] or 0
        win_rate = (wins / total * 100.0) if total > 0 else 0.0

        return {
            "total_trades": total,
            "winning_trades": wins,
            "losing_trades": row['losing_trades'] or 0,
            "win_rate_pct": round(win_rate, 2),
            "total_net_pnl": round(row['total_net_pnl'] or 0.0, 4),
            "total_fees": round(row['total_fees'] or 0.0, 4),
            "avg_profit_pct": round(row['avg_profit_pct'] or 0.0, 4)
        }

def save_strategy_memory(symbol: str, fingerprint: int, action: str, profit_pct: float, regime: str = "UNKNOWN") -> None:
    with get_db() as conn:
        conn.execute("""
            INSERT INTO strategy_archive (symbol, regime, fingerprint, action, win_rate, total_profit, sample_size)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(symbol, fingerprint, action) DO UPDATE SET
                regime=excluded.regime,
                win_rate = ((strategy_archive.win_rate * strategy_archive.sample_size) + ?) / (strategy_archive.sample_size + 1),
                total_profit = strategy_archive.total_profit + excluded.total_profit,
                sample_size = strategy_archive.sample_size + 1,
                updated_at = CURRENT_TIMESTAMP
        """, (
            symbol, regime, str(fingerprint), action,
            1.0 if profit_pct > 0 else 0.0,
            profit_pct,
            1.0 if profit_pct > 0 else 0.0
        ))

def get_strategy_memories(symbol: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fingerprint, action, win_rate, total_profit, sample_size, regime
            FROM strategy_archive 
            WHERE symbol = ? AND is_active = 1
        """, (symbol,))
        return [dict(row) for row in cursor.fetchall()]

def set_system_config(key: str, value: Any) -> None:
    val_str = json.dumps(value) if not isinstance(value, str) else value
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO system_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, val_str))
    except sqlite3.OperationalError:
        init_db()
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO system_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, val_str))

def get_system_config(key: str, default: Any = None) -> Any:
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
            row = cursor.fetchone()
            if not row:
                return default
            try:
                return json.loads(row['value'])
            except Exception:
                return row['value']
    except sqlite3.OperationalError:
        return default

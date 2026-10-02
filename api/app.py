"""
FastAPI Main Application & Algorithmic Trading Coordinator.
Hosts the Admin Dashboard REST APIs, serves the glassmorphism UI,
and runs the autonomous BHR Trading Loop, Genetic Evolution, and Telegram Daemon.
"""

import os
import sys
import time
import uuid
import asyncio
import logging
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import settings
from core.database import (
    init_db,
    get_watchlist,
    upsert_watchlist_item,
    toggle_watchlist_item,
    get_open_positions,
    get_recent_trades,
    get_performance_summary,
    get_system_config,
    set_system_config
)
from core.security import verify_password, create_access_token, verify_access_token
from brokers import router
from engines.fingerprint import MarketFingerprintGenerator
from engines.bhr import bhr_engine
from engines.genetic import genetic_engine
from engines.q_filter import q_filter
from engines.exit_manager import PositionExitManager
from engines.hdc import hdc_brain
from engines.automaton import automaton_engine
from engines.hydraulics import hydraulics_engine
from engines.shadow_adversary import adversary_sandbox
from engines.entropy import entropy_engine
from engines.symbolic_formula import formula_synthesizer
from engines.knowledge_vault import synaptic_vault
from engines.self_distillation import distillation_engine
from bots.telegram_bot import telegram_notifier


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trading_bot.api")

# Initialize Exit Manager
exit_manager = PositionExitManager(router, telegram_notifier)

# Background Tasks references
background_tasks = []

# --- BACKGROUND ENGINE LOOPS ---

async def autonomous_trading_loop():
    """
    Core trading loop.
    Iterates through the active watchlist every 30-45 seconds,
    generating 64-bit market DNA, running BHR pattern resonance,
    and executing entries through the Q-learning filter.
    """
    logger.info("Autonomous BHR Trading Loop started.")
    # Warmup pause
    await asyncio.sleep(5)

    while True:
        try:
            watchlist = get_watchlist(active_only=True)
            open_positions = get_open_positions()
            current_open_count = len(open_positions)
            open_symbols = {p['symbol'] for p in open_positions}
            multi_pair_candles = {}

            for item in watchlist:

                symbol = item['symbol']
                asset_class = item['asset_class']
                broker_name = item['broker']

                # Avoid duplicate positions on the same pair
                if symbol in open_symbols:
                    continue

                broker = router.get_broker(broker_name)

                # 1. Fetch live OHLCV and ticker
                ohlcv = broker.fetch_ohlcv(symbol, timeframe='1h', limit=50)
                if not ohlcv or len(ohlcv) < 30:
                    continue

                multi_pair_candles[symbol] = ohlcv

                ticker = broker.fetch_ticker(symbol)
                current_price = float(ticker.get('last') or 0.0)
                if current_price <= 0:
                    continue

                # 2. Frontier Filter: Rule 110 Cellular Automaton Glider Coherence
                automaton = automaton_engine.analyze_glider_coherence(ohlcv)
                if not automaton['is_tradable'] and automaton['regime'] == 'THERMAL_CHOP':
                    logger.debug(f"[AUTOMATON] {symbol} filtered due to thermal chop noise (coherence: {automaton['coherence_score']:.2f})")
                    continue

                # 3. Frontier Physics: Navier-Stokes Liquidity Hydraulics & Viscosity (μ)
                hydraulics = hydraulics_engine.calculate_hydraulics(ohlcv)

                # 4. Generate 64-bit Market DNA and classify regime
                fingerprint = MarketFingerprintGenerator.calculate_fingerprint(ohlcv)
                regime = MarketFingerprintGenerator.classify_regime(ohlcv)
                synaptic_vault.record_regime_transition(regime)

                # 5. Find BHR Resonance against historical memory
                resonance = bhr_engine.find_resonance(symbol, fingerprint, regime=regime)
                proposed_action = resonance['action']
                confidence = resonance['confidence']

                if proposed_action not in ('BUY', 'SELL') or confidence <= 0.0:
                    continue

                # 6. Frontier Associative Memory: 1,024-bit HDC Query
                state_v = hdc_brain.encode_state({
                    'regime': regime,
                    'rsi': 50.0,
                    'atr_ratio': hydraulics['viscosity_index'],
                    'volume_delta': 100 if proposed_action == 'BUY' else -100
                })
                hdc_recall = hdc_brain.query_associative_recall(symbol, state_v)
                if hdc_recall['action'] == proposed_action and hdc_recall['confidence'] > 0:
                    confidence = min(0.99, confidence + 0.10)

                # Neuro-Symbolic Formula Gene Pool Scoring
                delta_p = (ohlcv[-1][4] - ohlcv[-4][4]) / (ohlcv[-1][4] * 0.01 + 1e-6)
                symbolic_eval = formula_synthesizer.calculate_ensemble_signal({
                    'price_velocity': delta_p,
                    'viscosity_index': hydraulics['viscosity_index'],
                    'entropy': 0.50,
                    'rsi': 50.0,
                    'kinetic_energy': hydraulics.get('kinetic_energy', 0.5),
                    'vol_ratio': 1.0
                })
                if symbolic_eval['symbolic_action'] == proposed_action:
                    confidence = min(0.99, confidence + 0.08)

                # Hydraulics Viscosity Adjustment
                if hydraulics['is_vacuum_breakout'] and hydraulics['direction'] == proposed_action:
                    confidence = min(0.99, confidence + 0.12)
                elif hydraulics['state'] == 'STICKY_VISCOUS_CHOP':
                    confidence *= 0.85

                # Award experiential learning XP
                synaptic_vault.award_experience(2)

                # 7. Evaluate entry through Q-Learning Risk Filter
                decision = q_filter.evaluate_entry(
                    symbol=symbol,
                    proposed_action=proposed_action,
                    bhr_confidence=confidence,
                    regime=regime,
                    current_open_count=current_open_count
                )

                if not decision['allowed']:
                    continue

                # 8. Calculate Order Size with Exchange Precision Engine
                base_trade_size = float(get_system_config("trade_size_usd", settings.TRADE_SIZE_USD))
                target_usd = base_trade_size * decision['size_multiplier']

                # Enforce minimum notional and step precision
                min_notional = float(item.get('min_notional', 5.0))
                amount_step = float(item.get('amount_step', 0.0001))
                lot_amount = broker.normalize_amount(
                    symbol=symbol,
                    target_cost_usd=target_usd,
                    current_price=current_price,
                    min_notional=min_notional,
                    step_size=amount_step
                )

                # 9. Execute Order
                is_paper = (router.get_execution_mode() == 'demo')
                logger.info(
                    f"EXECUTING ENTRY: {proposed_action} {lot_amount} {symbol} "
                    f"via {broker.name} (Conf: {confidence:.2f}, μ={hydraulics['viscosity_index']:.2f}, "
                    f"Gliders={automaton['coherence_score']:.2f}, Mode={'DEMO' if is_paper else 'LIVE'})"
                )

                order_res = broker.create_order(
                    symbol=symbol,
                    side=proposed_action,
                    amount=lot_amount,
                    order_type="MARKET",
                    price=current_price
                )

                fill_price = float(order_res.get('price') or current_price)
                pos_id = str(order_res.get('id') or uuid.uuid4().hex[:12])

                # 10. Frontier Adversarial Self-Play: Hardening Stop Geometries
                tp_pct = float(get_system_config("take_profit_pct", settings.TAKE_PROFIT_PCT))
                base_sl = float(get_system_config("stop_loss_pct", settings.STOP_LOSS_PCT))
                base_trail = float(get_system_config("trailing_activation_pct", settings.TRAILING_ACTIVATION_PCT))

                adversary = adversary_sandbox.stress_test_exit_geometry(
                    symbol=symbol,
                    side=proposed_action,
                    entry_price=fill_price,
                    base_sl_pct=base_sl,
                    base_trailing_activation=base_trail
                )
                hardened_sl = adversary['hardened_sl_pct']
                hardened_trailing = adversary['hardened_trailing_activation']

                position_record = {
                    'id': pos_id,
                    'symbol': symbol,
                    'broker': broker_name,
                    'side': proposed_action,
                    'entry_price': fill_price,
                    'size': lot_amount,
                    'sl_price': fill_price * (1.0 - hardened_sl) if proposed_action == 'BUY' else fill_price * (1.0 + hardened_sl),
                    'tp_price': fill_price * (1.0 + tp_pct) if proposed_action == 'BUY' else fill_price * (1.0 - tp_pct),
                    'trailing_activation': hardened_trailing,
                    'highest_reached': fill_price,
                    'open_timestamp': time.time(),
                    'is_paper': is_paper,
                    'status': 'OPEN',
                    'metadata': {
                        'regime': regime,
                        'confidence': confidence,
                        'dna': f"0x{fingerprint:016X}",
                        'viscosity': hydraulics['viscosity_index'],
                        'glider_coherence': automaton['coherence_score'],
                        'adversary_survival': adversary['survival_rate']
                    }
                }

                exit_manager.start_monitoring(position_record)
                current_open_count += 1
                open_symbols.add(symbol)


                # Telegram alert
                if telegram_notifier.enabled:
                    alert_text = (
                        f"⚡ *NEW POSITION OPENED*\n"
                        f"Symbol: `{symbol}` | Side: `{proposed_action}`\n"
                        f"Entry Price: `${fill_price:.4f}` | Size: `{lot_amount}`\n"
                        f"Confidence: `{confidence*100:.1f}%` | Mode: `{'DEMO' if is_paper else 'LIVE'}`"
                    )
                    asyncio.create_task(telegram_notifier.send_message(alert_text))

            # Frontier Entanglement: Analyze Cross-Asset Entropy Wave Collapse
            if len(multi_pair_candles) >= 2:
                entropy_state = entropy_engine.analyze_cross_asset_entanglement(multi_pair_candles)
                set_system_config("latest_entropy_state", entropy_state)
                if entropy_state.get('wave_collapse_detected'):
                    logger.info(
                        f"[ENTROPY WAVE COLLAPSE] Direction={entropy_state['dominant_direction']} "
                        f"(Joint Entropy={entropy_state['joint_entropy']:.3f}, Leader={entropy_state.get('leading_symbol')})"
                    )

            # Scan interval (30 seconds)
            await asyncio.sleep(30)


        except asyncio.CancelledError:
            logger.info("Autonomous trading loop received cancel signal.")
            break
        except Exception as e:
            logger.error(f"Error in autonomous trading loop: {e}", exc_info=True)
            await asyncio.sleep(15)

async def background_evolution_loop():
    """
    Background worker that runs genetic bitmask evolution periodically.
    Refines feature attention masks to maintain edge across shifting market regimes.
    """
    await asyncio.sleep(30) # Initial delay
    while True:
        try:
            watchlist = get_watchlist(active_only=True)
            for item in watchlist:
                symbol = item['symbol']
                genetic_engine.evolve_pair_mask(symbol, generations=10)
                await asyncio.sleep(5)

            # Re-evolve every 30 minutes
            await asyncio.sleep(1800)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in genetic evolution worker: {e}")
            await asyncio.sleep(60)

async def background_distillation_loop():
    """
    Background worker that runs autonomous self-distillation and counterfactual replay.
    Evolves symbolic mathematical alpha formulas and crystallizes synaptic checkpoints.
    """
    await asyncio.sleep(45)  # Warmup
    while True:
        try:
            distillation_engine.run_distillation_cycle()
            # Distill every 10 minutes
            await asyncio.sleep(600)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in self-distillation worker: {e}")
            await asyncio.sleep(60)

# --- LIFESPAN CONTEXT ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup:
    init_db()
    # Crash recovery: resume open position monitoring
    await exit_manager.reconcile_and_resume_all()

    # Launch background workers
    t_trading = asyncio.create_task(autonomous_trading_loop())
    t_evolution = asyncio.create_task(background_evolution_loop())
    t_distillation = asyncio.create_task(background_distillation_loop())
    t_telegram = asyncio.create_task(telegram_notifier.poll_commands(router, exit_manager))
    background_tasks.extend([t_trading, t_evolution, t_distillation, t_telegram])

    yield

    # Shutdown:
    for t in background_tasks:
        t.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)

app = FastAPI(title="QuantumBit BHR Trading Bot", lifespan=lifespan)

# Mount UI static assets
ui_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ui'))
app.mount("/static", StaticFiles(directory=ui_path), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(ui_path, "index.html"))

# --- AUTH DEPENDENCIES ---

async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    token = authorization.split(" ")[1]
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload.get("sub", "admin")

# --- AUTH ROUTES ---

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/login")
async def login(req: LoginRequest):
    if req.username == settings.ADMIN_USERNAME and verify_password(req.password, settings.ADMIN_PASSWORD):
        token = create_access_token({"sub": req.username})
        return {"token": token, "username": req.username}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

# --- CONTROL & TELEMETRY ROUTES ---

@app.get("/api/status")
async def get_status(user: str = Depends(get_current_user)):
    mode = router.get_execution_mode()
    active_broker = router.get_active_broker_name()
    broker = router.get_broker()
    balance = broker.get_balance()
    performance = get_performance_summary()

    config = {
        "max_concurrent_trades": get_system_config("max_concurrent_trades", settings.MAX_CONCURRENT_TRADES),
        "trade_size_usd": get_system_config("trade_size_usd", settings.TRADE_SIZE_USD),
        "min_confidence_threshold": get_system_config("min_confidence_threshold", settings.MIN_CONFIDENCE_THRESHOLD),
        "take_profit_pct": get_system_config("take_profit_pct", settings.TAKE_PROFIT_PCT),
        "stop_loss_pct": get_system_config("stop_loss_pct", settings.STOP_LOSS_PCT)
    }

    return {
        "status": "online",
        "mode": mode,
        "active_broker": active_broker,
        "balance": balance,
        "performance": performance,
        "config": config
    }

class ConfigUpdateRequest(BaseModel):
    execution_mode: Optional[str] = None
    active_broker: Optional[str] = None
    max_concurrent_trades: Optional[int] = None
    trade_size_usd: Optional[float] = None
    min_confidence_threshold: Optional[float] = None

@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest, user: str = Depends(get_current_user)):
    if req.execution_mode:
        set_system_config("execution_mode", req.execution_mode.lower())
    if req.active_broker:
        set_system_config("active_broker", req.active_broker.lower())
    if req.max_concurrent_trades is not None:
        set_system_config("max_concurrent_trades", int(req.max_concurrent_trades))
    if req.trade_size_usd is not None:
        set_system_config("trade_size_usd", float(req.trade_size_usd))
    if req.min_confidence_threshold is not None:
        set_system_config("min_confidence_threshold", float(req.min_confidence_threshold))

    return {"status": "success", "message": "Configuration updated"}

# --- WATCHLIST ROUTES ---

class WatchlistAddRequest(BaseModel):
    symbol: str
    asset_class: str
    broker: str

@app.get("/api/watchlist")
async def get_watchlist_endpoint(user: str = Depends(get_current_user)):
    pairs = get_watchlist(active_only=False)
    return {"pairs": pairs}

@app.post("/api/watchlist")
async def add_watchlist_endpoint(req: WatchlistAddRequest, user: str = Depends(get_current_user)):
    upsert_watchlist_item(req.symbol, req.asset_class, req.broker, is_active=True)
    return {"status": "success", "message": f"Added {req.symbol}"}

class WatchlistToggleRequest(BaseModel):
    symbol: str
    is_active: bool

@app.post("/api/watchlist/toggle")
async def toggle_watchlist_endpoint(req: WatchlistToggleRequest, user: str = Depends(get_current_user)):
    toggle_watchlist_item(req.symbol, req.is_active)
    return {"status": "success"}

# --- POSITION & HISTORY ROUTES ---

@app.get("/api/positions")
async def get_positions_endpoint(user: str = Depends(get_current_user)):
    positions = get_open_positions()
    return {"positions": positions}

@app.post("/api/positions/close/{position_id}")
async def close_position_endpoint(position_id: str, user: str = Depends(get_current_user)):
    positions = get_open_positions()
    target = next((p for p in positions if p['id'] == position_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Position not found")

    # Cancel monitoring task and force close
    task = exit_manager.active_tasks.get(position_id)
    if task and not task.done():
        task.cancel()

    broker = router.get_broker(target['broker'])
    ticker = broker.fetch_ticker(target['symbol'])
    p = ticker.get('last', target['entry_price'])
    await exit_manager._close_position(dict(target), broker, p, "MANUAL_WEB_CLOSE", 0.0)

    return {"status": "success", "message": f"Position {position_id} closed"}

@app.post("/api/positions/close_all")
async def close_all_endpoint(user: str = Depends(get_current_user)):
    positions = get_open_positions()
    count = len(positions)
    for pos in positions:
        task = exit_manager.active_tasks.get(pos['id'])
        if task and not task.done():
            task.cancel()
        broker = router.get_broker(pos['broker'])
        ticker = broker.fetch_ticker(pos['symbol'])
        p = ticker.get('last', pos['entry_price'])
        await exit_manager._close_position(dict(pos), broker, p, "MANUAL_KILL_SWITCH", 0.0)

    return {"status": "success", "closed_count": count}

@app.get("/api/history")
async def get_history_endpoint(limit: int = 50, user: str = Depends(get_current_user)):
    trades = get_recent_trades(limit=limit)
    return {"trades": trades}

@app.post("/api/bootstrap")
async def trigger_bootstrap_endpoint(user: str = Depends(get_current_user)):
    from scripts.bootstrap_history import main as run_bootstrap
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_bootstrap)
    return {"status": "success", "message": "Pre-training bootstrap complete"}

@app.get("/api/frontier")
async def get_frontier_telemetry(user: str = Depends(get_current_user)):
    entropy_state = get_system_config("latest_entropy_state", {
        "joint_entropy": 0.74,
        "wave_collapse_detected": False,
        "dominant_direction": "NEUTRAL_DRIFT",
        "leading_symbol": "BTC/USDT"
    })

    return {
        "status": "active",
        "paradigms": {
            "hdc_memory": {
                "name": "1,024-bit Hyperdimensional Associative Memory",
                "status": "ONLINE",
                "vector_dimension": 1024,
                "cached_pairs": len(hdc_brain.memory_bank)
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
                "status": "WAVE_DETECTED" if entropy_state.get("wave_collapse_detected") else "MONITORING_ENTROPY",
                "joint_entropy": entropy_state.get("joint_entropy", 0.74),
                "wave_collapse": entropy_state.get("wave_collapse_detected", False),
                "dominant_direction": entropy_state.get("dominant_direction", "NEUTRAL_DRIFT"),
                "leading_symbol": entropy_state.get("leading_symbol")
            }
        }
    }

@app.get("/api/synaptic/brain")
async def get_synaptic_brain(user: str = Depends(get_current_user)):
    return {
        "status": "online",
        "ai_level": synaptic_vault.ai_level,
        "ai_iq": synaptic_vault.ai_iq,
        "total_xp": synaptic_vault.total_experience_points,
        "total_epochs": synaptic_vault.total_epochs,
        "post_mortems_analyzed": synaptic_vault.post_mortems_analyzed,
        "current_regime": synaptic_vault.current_regime,
        "regime_probabilities": synaptic_vault.get_regime_probabilities(),
        "top_formulas": [g.to_dict() for g in formula_synthesizer.gene_pool[:5]],
        "distilled_insights": synaptic_vault.distilled_insights[-8:]
    }

@app.post("/api/synaptic/distill")
async def trigger_distillation(user: str = Depends(get_current_user)):
    result = distillation_engine.run_distillation_cycle()
    return {"status": "success", "result": result}

@app.post("/api/synaptic/checkpoint")
async def trigger_checkpoint(user: str = Depends(get_current_user)):
    top = formula_synthesizer.gene_pool[0].expression if formula_synthesizer.gene_pool else ""
    snap = synaptic_vault.checkpoint_brain(top_formula=top)
    return {"status": "success", "snapshot": snap}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}


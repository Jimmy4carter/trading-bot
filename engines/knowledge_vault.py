"""
Synaptic Knowledge Vault & Lifelong Memory Crystallizer.
Stores, crystallizes, and persists the Mini-AI's learned synaptic weights,
discovered formulas, regime transition matrices, and counterfactual trade post-mortems.
Enables the bot to accumulate intelligence over weeks and months without catastrophic forgetting.
"""

import os
import json
import time
import math
import logging
from typing import Dict, Any, List, Optional
from core.database import get_db

logger = logging.getLogger("trading_bot.engine.vault")

class SynapticKnowledgeVault:
    REGIMES = [
        "BULL_TREND",
        "BEAR_TREND",
        "CHOP_ACCUMULATION",
        "HIGH_VOL_EXPLOSION",
        "LIQUIDITY_CAVITATION"
    ]

    def __init__(self, storage_path: str = "data/synaptic_brain.json"):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self._init_sqlite_vault()

        # Core synaptic parameters
        self.total_experience_points = 0
        self.ai_level = 1
        self.ai_iq = 110.0
        self.total_epochs = 0
        self.post_mortems_analyzed = 0

        # Empirical Markov Regime Transition Matrix: {from_regime: {to_regime: count}}
        self.regime_transitions: Dict[str, Dict[str, int]] = {
            r: {dest: 1 for dest in self.REGIMES} for r in self.REGIMES
        }
        self.current_regime = "CHOP_ACCUMULATION"

        # Trajectory memories
        self.distilled_insights: List[Dict[str, Any]] = []

        self.load_crystallized_brain()

    def _init_sqlite_vault(self):
        """Ensures SQLite persistence tables for lifelong AI memories exist."""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS synaptic_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        ai_level INTEGER NOT NULL,
                        ai_iq REAL NOT NULL,
                        total_xp INTEGER NOT NULL,
                        total_epochs INTEGER NOT NULL,
                        top_formula TEXT,
                        insights_count INTEGER,
                        raw_payload TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trade_post_mortems (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        position_id TEXT UNIQUE,
                        symbol TEXT,
                        realized_pnl REAL,
                        regime TEXT,
                        mistake_cause TEXT,
                        counterfactual_lesson TEXT,
                        recorded_at TEXT
                    )
                """)
        except Exception as e:
            logger.error(f"Error initializing synaptic sqlite tables: {e}")

    def record_regime_transition(self, new_regime: str):
        """Updates the Markov transition probability matrix between market regimes."""
        if new_regime not in self.REGIMES:
            return
        if self.current_regime in self.regime_transitions:
            self.regime_transitions[self.current_regime][new_regime] += 1

        self.current_regime = new_regime

    def get_regime_probabilities(self, from_regime: Optional[str] = None) -> Dict[str, float]:
        """Calculates softmax/empirical probability distribution of next market state."""
        source = from_regime or self.current_regime
        if source not in self.regime_transitions:
            return {r: 0.20 for r in self.REGIMES}

        counts = self.regime_transitions[source]
        total = sum(counts.values())
        return {r: round(counts[r] / float(total), 4) for r in self.REGIMES}

    def award_experience(self, points: int):
        """Adds XP and dynamically calculates the Mini-AI's Level and IQ."""
        self.total_experience_points += max(1, points)
        # Level formula: Level = floor(sqrt(XP / 80)) + 1
        new_level = int(math.floor(math.sqrt(self.total_experience_points / 80.0))) + 1
        if new_level > self.ai_level:
            logger.info(f"🌟 [MINI-AI LEVEL UP] Advanced to Level {new_level}! Total XP: {self.total_experience_points}")
            self.ai_level = new_level

        # IQ increases logarithmically with XP and experience diversity
        self.ai_iq = round(105.0 + math.log10(max(10, self.total_experience_points)) * 14.5 + (self.ai_level * 1.5), 1)

    def record_post_mortem(self, position_id: str, symbol: str, realized_pnl: float, regime: str, mistake_cause: str, lesson: str):
        """Records a crystallized trade post-mortem to prevent repetitive errors."""
        now = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO trade_post_mortems 
                    (position_id, symbol, realized_pnl, regime, mistake_cause, counterfactual_lesson, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (position_id, symbol, realized_pnl, regime, mistake_cause, lesson, now))
            self.post_mortems_analyzed += 1
            self.award_experience(25)  # Learning from a post-mortem grants 25 XP
        except Exception as e:
            logger.error(f"Error saving post-mortem: {e}")

        insight = {
            "symbol": symbol,
            "regime": regime,
            "mistake": mistake_cause,
            "lesson": lesson,
            "timestamp": now
        }
        self.distilled_insights.append(insight)
        if len(self.distilled_insights) > 50:
            self.distilled_insights.pop(0)

    def checkpoint_brain(self, top_formula: str = "") -> Dict[str, Any]:
        """Crystallizes complete synaptic state to JSON file and SQLite snapshot table."""
        self.total_epochs += 1
        payload = {
            "version": "2.0-synaptic",
            "last_saved": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            "ai_level": self.ai_level,
            "ai_iq": self.ai_iq,
            "total_experience_points": self.total_experience_points,
            "total_epochs": self.total_epochs,
            "post_mortems_analyzed": self.post_mortems_analyzed,
            "current_regime": self.current_regime,
            "regime_transitions": self.regime_transitions,
            "distilled_insights": self.distilled_insights[-10:],
            "top_formula": top_formula
        }

        # 1. Save to JSON disk file
        try:
            with open(self.storage_path, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write synaptic brain JSON: {e}")

        # 2. Save snapshot to SQLite
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO synaptic_snapshots 
                    (timestamp, ai_level, ai_iq, total_xp, total_epochs, top_formula, insights_count, raw_payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    payload["last_saved"],
                    self.ai_level,
                    self.ai_iq,
                    self.total_experience_points,
                    self.total_epochs,
                    top_formula,
                    len(self.distilled_insights),
                    json.dumps(payload)
                ))
            logger.info(f"🧠 [SYNAPTIC VAULT] Brain Checkpoint crystallized (Level {self.ai_level}, IQ {self.ai_iq}, Epoch {self.total_epochs})")
        except Exception as e:
            logger.error(f"Failed to save SQLite brain snapshot: {e}")

        return payload

    def load_crystallized_brain(self):
        """Restores synaptic intelligence from persistent disk storage."""
        if not os.path.exists(self.storage_path):
            return

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                self.ai_level = data.get("ai_level", 1)
                self.ai_iq = data.get("ai_iq", 110.0)
                self.total_experience_points = data.get("total_experience_points", 0)
                self.total_epochs = data.get("total_epochs", 0)
                self.post_mortems_analyzed = data.get("post_mortems_analyzed", 0)
                self.regime_transitions = data.get("regime_transitions", self.regime_transitions)
                self.distilled_insights = data.get("distilled_insights", [])
                logger.info(f"🧠 [SYNAPTIC VAULT] Restored AI Brain: Level {self.ai_level}, IQ {self.ai_iq}, XP {self.total_experience_points}")
        except Exception as e:
            logger.warning(f"Could not load synaptic brain JSON: {e}")

# Singleton instance
synaptic_vault = SynapticKnowledgeVault()

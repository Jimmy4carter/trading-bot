# Synaptic Mini-AI Architecture & Lifelong Learning Core

The QuantumBit bot is designed not merely as a fixed rule engine, but as an **Autonomous Self-Improving Mini-AI Synaptic Learning System**. Over weeks and months of continuous operation across thousands of price ticks and market cycles, the AI accumulates empirical data, mutates proprietary mathematical formulas, builds regime transition matrices, and crystallizes operational rules so that it becomes increasingly profitable over time.

```
                           +-----------------------------------------------+
                           |          Live / Paper Execution Feed          |
                           +-----------------------+-----------------------+
                                                   |
                                                   v
                           +-----------------------------------------------+
                           | 1. Synaptic Knowledge Vault                   |
                           |    - Tracks AI Level & Cognitive IQ Score     |
                           |    - Accumulates Experience Points (XP)       |
                           |    - Persists Checkpoints (data/synaptic_brain)|
                           +-----------------------+-----------------------+
                                                   |
                   +-------------------------------+-------------------------------+
                   |                                                               |
                   v                                                               v
+------------------------------------+          +------------------------------------+
| 2. Neuro-Symbolic Formula          |          | 3. Markov Regime Transition Matrix |
|    Synthesizer (Alpha Gene Pool)   |          |    - Dynamic Market State Graph    |
|    - Synthesizes Math Expressions  |          |    - Predicts Next Regime Shift    |
|    - Evolves Top Performing Genes  |          |    - Proactive Risk Conditioning   |
+------------------+-----------------+          +------------------+-----------------+
                   |                                               |
                   +-------------------------------+---------------+
                                                   |
                                                   v
                           +-----------------------------------------------+
                           | 4. Counterfactual Self-Distillation Engine    |
                           |    - Replays Recent Trade Trajectories        |
                           |    - Diagnoses Loss Causes & Stop Hunts       |
                           |    - Distills Lessons & Hardens Boundaries    |
                           +-----------------------------------------------+
```

---

## 1. Cognitive IQ & Experience Progression

The Mini-AI tracks its cognitive growth across every market scan and trade execution:

### Experience Points (XP) Formula
$$\text{XP}_{\text{total}} = \sum \left(2 \cdot \text{Scan Cycles} + 15 \cdot \text{Trades Analyzed} + 25 \cdot \text{Post-Mortems Crystallized}\right)$$

### Cognitive Rank & IQ Formulation
- **AI Level**:
  $$\text{Level} = \left\lfloor \sqrt{\frac{\text{XP}}{80}} \right\rfloor + 1$$
- **Cognitive IQ Score**:
  $$\text{IQ} = 105.0 + 14.5 \cdot \log_{10}\left(\max(10, \text{XP})\right) + 1.5 \cdot \text{Level}$$

As the bot runs for 3 to 6 months, its IQ dynamically climbs from **110 (Novice)** through **130 (Proficient)** to **150+ (Master Alpha Strategist)**, unlocking tighter risk filters and higher-conviction entry criteria.

---

## 2. Neuro-Symbolic Formula Synthesizer (`engines/symbolic_formula.py`)

Instead of limiting itself to human-invented indicators (such as RSI or MACD), the AI uses **Genetic Programming** to breed and evolve proprietary mathematical alpha formulas.

### Atomic Mathematical Primitives
- Variables: Price velocity ($v_{\text{price}}$), Liquidity viscosity ($\mu$), Shannon entropy ($H$), Normalized RSI ($RSI_{\text{norm}}$), Kinetic energy ($E_k$), Volume ratio ($V_{\text{ratio}}$).
- Operators: $\sin(x)$, $\tanh(x)$, $|x|$, $+$, $-$, $\times$, $/$.

### Sample Discovered Mathematical Genes
1. $\tanh(v_{\text{price}} \times 2.0) - (\mu \times 0.5)$
2. $(RSI_{\text{norm}} - 0.5) \times (1.0 - H) \times 2.0$
3. $\sin(v_{\text{price}} \times \pi) \times E_k$
4. $\tanh\left(\frac{E_k}{\mu + 0.1}\right) \times (1.0 - H)$

### Genetic Evolution & Darwinian Selection
1. **Evaluation**: Every formula computes a rolling prediction score $\alpha \in [-1.0, 1.0]$.
2. **Fitness Function**: Evaluated against actual subsequent price delta:
   $$\text{Fitness}_{t+1} = \text{Fitness}_t \pm \Delta \text{Profitability}$$
3. **Breeding & Mutation**: The top 80% surviving formulas are retained; the bottom 20% are pruned and replaced by crossed-over, mutated offspring.

---

## 3. Markov Synaptic Regime Transition Matrix

Financial markets do not exist in isolated static regimes; they flow through continuous transitions. The Synaptic Vault (`engines/knowledge_vault.py`) constructs an empirical Markov transition matrix:

$$P(\text{Regime}_{t+1} = j \mid \text{Regime}_t = i) = \frac{N_{ij}}{\sum_k N_{ik}}$$

### Managed Regime States
- `BULL_TREND`
- `BEAR_TREND`
- `CHOP_ACCUMULATION`
- `HIGH_VOL_EXPLOSION`
- `LIQUIDITY_CAVITATION`

By computing the transition probability distribution in real time, the bot identifies when a choppy accumulation phase is approaching exhaustion and preparing to transition into a directional liquidity breakout, positioning orders *before* retail momentum indicators detect the move.

---

## 4. Counterfactual Self-Distillation (`engines/self_distillation.py`)

The biggest challenge in algorithmic trading is repetitive errors (e.g. repeatedly entering trades during low-liquidity Friday market close).

The **Self-Distillation Engine** conducts automated post-mortems on completed trades:
1. **Loss Post-Mortem**: When an order hits a stop loss, the AI inspects the telemetry:
   - Was the stop swept by a predatory wick? $\implies$ The bot adjusts its adversary sandbox hardening multiplier.
   - Was price hovering in thermal chop? $\implies$ The bot increases the minimum Rule 110 Glider coherence threshold for that asset.
2. **Crystallized Trade Lessons**: Lessons are saved to SQLite (`trade_post_mortems`) and the persistent JSON brain vault (`data/synaptic_brain.json`).
3. **Lifelong Persistence**: These lessons persist across server reboots, Docker redeployments, and code updates. The AI never loses what it has learned.

---

## 5. Synaptic REST API & Dashboard Controls

| Endpoint | Method | Action |
|---|---|---|
| `/api/synaptic/brain` | `GET` | Returns AI Level, IQ, XP, current regime, transition probabilities, and top formulas. |
| `/api/synaptic/distill` | `POST` | Manually triggers an immediate counterfactual replay cycle. |
| `/api/synaptic/checkpoint` | `POST` | Forces an immediate atomic snapshot write to disk (`data/synaptic_brain.json` and SQLite). |

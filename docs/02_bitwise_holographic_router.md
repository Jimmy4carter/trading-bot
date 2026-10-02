# 02. Bitwise Holographic Router (BHR)

## 1. Mathematical Concept

The **Bitwise Holographic Router (BHR)** is a proprietary, hardware-accelerated pattern matching engine. Rather than feeding decimal numbers into a multi-layer neural network, BHR maps the entire continuous market geometry into a single **64-bit unsigned integer fingerprint**:

$$\text{Fingerprint} \in \{0, 1\}^{64}$$

At CPU hardware level, comparing two 64-bit integers using a **Bitwise XOR ($\oplus$)** instruction takes exactly **1 clock cycle** (sub-nanosecond). Counting the number of set bits (`1`s) in the result yields the **Hamming Distance**:

$$D_H(A, B) = \text{popcount}(A \oplus B) = \sum_{i=0}^{63} (A_i \oplus B_i)$$

The Hamming distance directly quantifies the geometric dissimilarity between the current market second and any recorded historical moment.

---

## 2. 64-Bit Market DNA Allocation Table

The 64 bits are mapped to distinct physical and structural properties of the candlestick flow:

| Bit Range | Category | Market Indicator / Primitive |
|---|---|---|
| **Bits 0–2** | Trend & Crosses | `close > EMA_9`, `close > EMA_21`, `close > EMA_50` |
| **Bits 3–4** | Moving Average Slope | `EMA_9 > EMA_21` (Fast Bull Cross), `EMA_21 > EMA_50` |
| **Bits 5–7** | Momentum Windows | `close > close[t-1]`, `close > close[t-5]`, `close > close[t-10]` |
| **Bit 8** | Trailing Slope | `EMA_9 > close[t-2]` |
| **Bits 16–17** | Oversold Momentum | `RSI_14 < 30` (Oversold), `RSI_14 < 20` (Extreme Oversold) |
| **Bits 18–19** | Overbought Momentum | `RSI_14 > 70` (Overbought), `RSI_14 > 80` (Extreme Overbought) |
| **Bit 20** | RSI Equilibrium | `45 <= RSI_14 <= 55` (Consolidation Band) |
| **Bit 21** | RSI Vector Direction | `RSI_14 > RSI_14[t-1]` (Rising RSI Velocity) |
| **Bits 22–23** | Fast Stochastic (%K) | `Stoch_K < 20` (Dip), `Stoch_K > 80` (Crest) |
| **Bits 32–33** | Bollinger Envelopes | `close >= BB_Upper` (Piercing High), `close <= BB_Lower` (Piercing Low) |
| **Bits 34–35** | Volatility Regime | Bollinger Squeeze (`std < 0.5%`), Volatility Expansion (`std > 2.0%`) |
| **Bit 36** | ATR Spike | Current True Range $> 1.5 \times \text{ATR}_{14}$ |
| **Bits 44–46** | Volume Flow | `Volume > Volume_SMA20`, Volume Surge $> 2\times \text{SMA}$, Low Volume Drift |
| **Bits 47–48** | Volume Delta | Bullish Volume Delta (`close > open` & High Vol), Bearish Volume Delta |
| **Bits 56–57** | Candle Direction | Bullish Green Bar (`close > open`), Bearish Red Bar |
| **Bits 58–59** | Rejection Anatomy | Bullish Hammer Pin (`lower_wick > 2 * body`), Bearish Shooting Star |
| **Bit 60** | Indecision | Doji (`candle_body < 15% of range`) |
| **Bits 61–62** | Engulfing Patterns | Bullish Engulfing Reversal, Bearish Engulfing Reversal |

---

## 3. Genetic Bitmask Evolution Engine

Not every asset behaves the same way. For Bitcoin (`BTC/USDT`), trend-following moving average bits are critical, but oscillator bits may produce noise. For Gold (`XAU_USD`), mean-reversion bits matter far more.

To prevent human cognitive bias, a background evolutionary thread evolves a **Pair-Specific 64-bit Genetic Bitmask ($M$)**:

$$\text{Filtered State} = \text{Fingerprint} \ \& \ M$$

### Darwinian Evolution Cycle:
1. **Population**: 50 candidate bitmasks initialized with random bit distributions.
2. **Fitness Function**:
   $$\text{Fitness}(M) = 2.0 \cdot \text{WinRate} + 0.1 \cdot \text{TotalProfit} - \text{ParsimonyPenalty}$$
   * The parsimony penalty penalizes masks that activate fewer than 12 bits (underfitting) or more than 56 bits (overfitting to noise).
3. **Selection**: Top 20% fittest bitmasks survive (Elitism).
4. **Crossover**: Single-point bitwise crossover combines surviving parent equations:
   $$\text{Child} = (\text{Parent}_A \ \& \ \text{LowerMask}) \ | \ (\text{Parent}_B \ \& \ \text{UpperMask})$$
5. **Mutation**: 8% probability of flipping 1 to 3 random bits in the child mask.
6. **Promotion**: The fittest mask is written to Redis (`mask:{symbol}`).

---

## 4. Resonance Matching Algorithm

When evaluating a live candle:
1. Fetch the evolved mask $M$ from Redis.
2. Mask the live fingerprint: $A' = A \ \& \ M$.
3. Retrieve historical memories from SQLite: $\{ (B_k, \text{Action}_k, \text{WinRate}_k) \}$.
4. Compute masked Hamming distances:
   $$d_k = \text{popcount}(A' \oplus (B_k \ \& \ M))$$
5. Find the closest historical scenario:
   $$k^* = \arg\min_k d_k$$
6. **Resonance Filter**:
   If $d_{k^*} \le 5$ bits and $\text{WinRate}_{k^*} \ge 0.55$:
   $$\text{Confidence} = \left(1.0 - \frac{d_{k^*}}{64}\right) \cdot \text{WinRate}_{k^*}$$
   The action associated with memory $k^*$ is proposed to the execution gate.

---

## 5. Q-Learning Execution Filter Gate

The proposed BHR action passes through a **Reinforcement Learning Gatekeeper**:

$$\text{State Key} = \text{Regime} : \text{Action}$$

The learned Q-value is normalized via a sigmoid function:
$$P_Q = \sigma(Q) = \frac{1}{1 + e^{-Q}}$$

Composite trade confidence combines BHR resonance and Q-weights:
$$\text{Composite Score} = 0.65 \cdot \text{Confidence}_{\text{BHR}} + 0.35 \cdot P_Q$$

* If $\text{Composite Score} \ge \text{Threshold} + 0.15$: **Execute Full Size** ($1.0\times$).
* If $\text{Composite Score} \ge \text{Threshold}$: **Execute Half Size** ($0.5\times$ risk mitigation).
* If below threshold or concurrent limit reached: **Block Trade** (`HOLD`).

### Bellman Reinforcement Update (On Position Close):
$$Q_{t+1}(s, a) = Q_t(s, a) + \alpha \cdot \left[R_{\text{realized}} - Q_t(s, a)\right]$$
Where $\alpha = 0.10$ and reward $R$ is the realized net profit percentage after exchange fees.

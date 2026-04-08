# Trading Strategy Comparison Report
## Active Bots — Traderv30 through Traderv40

**Date:** 2026-04-08
**Best Performer:** Traderv37.py

---

## Table of Contents

1. [Quick Summary Table](#quick-summary-table)
2. [Version-by-Version Analysis](#version-by-version-analysis)
3. [Why Traderv37 Outperforms](#why-traderv37-outperforms)
4. [Architectural Evolution Timeline](#architectural-evolution-timeline)
5. [Parameter Progression Table](#parameter-progression-table)

---

## Quick Summary Table

| Version | Architecture Tier | Product Memory | Flow Signals | Book Microstructure | Persistence Tracking | Best For |
|---------|------------------|:-:|:-:|:-:|:-:|---------|
| v30 | Baseline regression MM | No | No | No | No | Reference |
| v31 | Parameter tuning on v30 | No | No | No | No | — |
| v32 | + Target bands | No | No | No | No | — |
| v33 | + MAX_QUOTE_EDGE=9, short horizon | No | No | No | No | — |
| v34 | Parameter search | No | No | No | No | — |
| v35 | + Hybrid alpha | No | Yes (basic) | No | No | — |
| v36 | + Flow memory + breakout | Yes | Yes | Basic | No | — |
| **v37** | **+ Book microstructure + persistence** | **Yes** | **Yes** | **Enhanced** | **Yes** | **BEST** |
| v38 | v37 with BREAKOUT_FOLLOW_SCALE 0.18→0.145 | Yes | Yes | Enhanced | Yes | — |
| v39 | v37 with BREAKOUT_HOLD_BONUS 0.12→0.09 | Yes | Yes | Enhanced | Yes | — |
| v40 | v37 with Bayesian param optimization | Yes | Yes | Enhanced | Yes | — |

---

## Version-by-Version Analysis

### Traderv30 — Baseline

**Strategy:** Regression-based market making with regime classification.

**Products:** EMERALDS (reference price anchor), TOMATOES (regression signal)

**Signal Logic:**
- Fits a linear regression over an 8-tick mid-price history
- `predicted_edge = (predicted_next - mid) × ALPHA_EDGE_SCALE`
- Classifies into regimes based on predicted_edge, fit quality, imbalance, and momentum:
  - `trend_up` / `trend_down` — edge ≥ threshold + fit ≥ 0.45 + imbalance ≥ 0.12 + momentum ≥ 0.75
  - `volatile` — spread ≥ 15 AND volatility ≥ 3.2
  - `range` — default fallback

**Position Sizing:**
- EMERALDS: tiered by distance from fair value — 1.0 away → 6 lots, 4.0 → 12, 8.0 → 20
- TOMATOES: BASE_ORDER_SIZE=10, adjusted ±3–4 units near soft limits

**Key Parameters:**

| Parameter | Value |
|-----------|-------|
| BASE_TAKE_EDGE | 1.10 |
| BASE_QUOTE_EDGE | 2.25 |
| MAX_QUOTE_EDGE | 5.0 |
| GAMMA_RANGE | 0.28 |
| GAMMA_TREND | 0.14 |
| GAMMA_VOLATILE | 0.24 |
| INVENTORY_SKEW | 0.035 |
| SOFT_LIMIT_RATIO | 0.65 |
| REGRESSION_WINDOW | 8 ticks |

**State:** `mid_history` (8-tick rolling window only). No product memory, no flow signals.

**Limitations:** Purely reactive to price history; no volume/flow/book data used.

---

### Traderv31 — Parameter Tuning

**Changes from v30:** Parameter adjustments only. No architectural changes.

| Parameter | v30 | v31 |
|-----------|-----|-----|
| BASE_TAKE_EDGE | 1.10 | 1.25 |
| BASE_QUOTE_EDGE | 2.25 | 2.75 |
| GAMMA_RANGE | 0.28 | 0.34 |
| GAMMA_TREND | 0.14 | 0.10 |
| GAMMA_VOLATILE | 0.24 | 0.40 |
| RESERVATION_SCALE | 0.16 | 0.12 |
| SPREAD_VOL_COEF | 0.56 | 0.90 |
| SPREAD_INV_COEF | 0.24 | 0.42 |
| TREND_SELL_HOLD_EXTRA | 0.16 | 0.24 |

**New in v31:** `HOLD_TIME_COEF = 0.08` — a small time-decay bonus for holding a position in a trend.

---

### Traderv32 — Target Bands

**Major Change:** Introduces `target_band()` — regime-specific position targets with conviction scaling.

| Regime | Target Band |
|--------|------------|
| Volatile | -6 to +6 |
| Range | -14 to +14 |
| Trend (standard) | +10 to +28 (up) / -28 to -10 (down) |
| Trend (high conviction) | +22 to +44 / -44 to -22 |

**Key Parameter Shifts:**

| Parameter | v31 | v32 |
|-----------|-----|-----|
| BASE_TAKE_EDGE | 1.25 | 0.80 |
| INVENTORY_SKEW | 0.035 | 0.005 |
| GAMMA_RANGE | 0.34 | 0.69283327 |
| RESERVATION_SCALE | 0.12 | 0.02 |
| SPREAD_VOL_COEF | 0.90 | 0.10 |
| SPREAD_TIME_COEF | 0.90 | 1.7791177 |

**Effect:** Much more aggressive spread collection in range (`GAMMA_RANGE` nearly doubled), more passive reservation pricing.

---

### Traderv33 — Quote Cap + Shorter Horizon

**Changes from v32:** Two parameters only.

| Parameter | v32 | v33 |
|-----------|-----|-----|
| MAX_QUOTE_EDGE | 5.0 | 9.0 |
| REGRESSION_HORIZON | 2.0 | 0.5 |

**Effect:** Wider maximum quotes allow recovery pricing in volatile regimes. Shorter regression horizon makes signals more reactive.

---

### Traderv34 — Parameter Search

**Changes from v33:** Continued parameter optimization.

| Parameter | v33 | v34 |
|-----------|-----|-----|
| INVENTORY_SKEW | 0.005 | 0.001 |
| BASE_TAKE_EDGE | 0.80 | 0.65413502 |
| MAX_QUOTE_EDGE | 9.0 | 10.038013 |
| REGRESSION_HORIZON | 0.5 | 0.1 |
| GAMMA_RANGE | 0.69283327 | 0.75210362 |
| SPREAD_INV_COEF | 1.1081637 | 2.0 |
| ALPHA_IMBALANCE_SCALE | 0.7 | 1.6171196 |

**Note:** RESERVATION_SCALE drops to 0.005 (near-zero), meaning reservation pricing is almost disabled.

---

### Traderv35 — Hybrid Alpha (Major Architecture Change)

**What changed:** Introduces `hybrid_alpha()` and `guarded_hybrid_alpha()` — a blended fair-value estimate that fuses multiple signals.

**hybrid_alpha() formula:**
```
alpha = ALPHA_REFERENCE_WEIGHT * reference_price   (0.45)
      + ALPHA_MID_WEIGHT       * mid               (0.20)
      + ALPHA_MICRO_WEIGHT     * micro              (0.25)
      + ALPHA_FLOW_WEIGHT      * flow_adjusted      (0.10)
```

**guarded_hybrid_alpha()** dampens the signal when it conflicts with other indicators:

| Conflict Type | Damping Factor |
|---------------|---------------|
| Range regime | 0.35 |
| Signal conflict | 0.45 |
| Momentum regime | 0.70 |

**Final predicted edge blend:**
```
predicted_edge = (1 - ALPHA_BLEND_WEIGHT) * regression_edge
               + ALPHA_BLEND_WEIGHT       * guarded_hybrid_alpha
```
Where `ALPHA_BLEND_WEIGHT = 0.28`.

**Parameter Resets (vs v34):**

| Parameter | v34 | v35 |
|-----------|-----|-----|
| BASE_TAKE_EDGE | 0.65413502 | 0.78 |
| BASE_QUOTE_EDGE | 10.038013 | 2.68 |
| EMERALDS INVENTORY_SKEW | 0.12 | 0.0328922991 |
| EMERALDS SOFT_LIMIT_RATIO | 0.25 | 0.6357999832 |

**State:** Still no product memory. Hybrid alpha history computed fresh each tick.

---

### Traderv36 — Flow Memory + Breakout (Major Architecture Change)

**What changed:** Adds **persistent product memory** and **market microstructure flow analysis**.

**Product Memory System:**
- `product_memory: Dict[str, dict]` — survives across ticks
- Utility methods: `memory_list()`, `append_memory_value()`, `memory_map()`
- Stores: `volume_history`, `signed_flow_history`, `bias_history`, `pressure_buckets`

**New Flow Analysis Methods:**

| Method | What it does |
|--------|-------------|
| `market_flow_metrics()` | Returns volume, signed_flow, bias, price_pressure, flow_acceleration from trade tape |
| `trade_direction()` | Classifies each trade as buy or sell vs mid/micro |
| `percentile_threshold()` | Computes volume percentile thresholds from history |
| `burst_score()` | Detects volume spikes; confirms with imbalance and flow bias |
| `update_pressure_memory()` | Price-bucket pressure scores with exponential decay (decay=0.82) |
| `pressure_bias()` | Derives support/resistance signal from pressure_buckets |
| `breakout_score()` | Combines burst + pressure + flow bias + imbalance + micro-mid diff |

**Regime extension:** `breakout_score >= 1.0` can independently trigger `trend_up`/`trend_down` without waiting for regression edge.

**Take edge:** Breakout-aligned trades get reduced edge (easier to take); breakout-opposed trades get penalized.

**Quote edge:** Tightens spreads when `abs(breakout_score) >= 1.10` to ensure fills during breakouts.

**New parameters:**

| Parameter | Value |
|-----------|-------|
| FLOW_SHORT_WINDOW | 6 ticks |
| FLOW_LONG_WINDOW | 18 ticks |
| BURST_PERCENTILE | 0.88 |
| PRESSURE_MEMORY_DECAY | 0.82 |
| PRESSURE_BIAS_SCALE | 0.40 |
| BREAKOUT_FOLLOW_SCALE | 0.30 |
| BREAKOUT_QUOTE_TIGHTEN | 0.40 |
| BREAKOUT_HOLD_BONUS | 0.25 |

**Limitation:** Flow metrics are computed from trade tape (filled trades), not directly from order book state changes. The order book's live movements (bid/ask stepping, depletion, rebuild) are not captured.

---

### Traderv37 — Book Microstructure + Persistence (Best Performer)

**What changed:** Replaces v36's trade-tape flow analysis with **direct order book microstructure tracking**. Adds **persistence signals** for confirmation.

#### The Core Innovation: Buy/Sell Impulse from Book State

v37 tracks the order book's state change between ticks and decomposes movement into distinct signals:

**Book state saved each tick:**
```python
prev_book = {
    best_bid, best_ask,
    bid_volume, ask_volume,
    mid, micro, spread, imbalance
}
```

**Between ticks, v37 measures:**

| Signal | Meaning |
|--------|---------|
| `bid_up` / `bid_down` | Did the best bid level step up or down? |
| `ask_up` / `ask_down` | Did the best ask level step up or down? |
| `ask_depletion` | Did ask volume at current level decrease (buyers eating into offers)? |
| `bid_rebuild` | Did bid volume at current level increase (buyers stacking bids)? |
| `micro_drift` | Change in micro price (volume-weighted mid) |
| `mid_drift` | Change in mid price |
| `spread_compression` | Did the spread narrow (signals incoming directional move)? |
| `imbalance_persistence` | Is imbalance consistently in same direction across window? |
| `micro_persistence` | Is micro consistently above/below mid across window? |

**Buy and Sell Impulse computation:**
```
buy_impulse  = BOOK_STEP_WEIGHT   * (bid_up + ask_up)
             + BOOK_DEPLETION_WEIGHT * ask_depletion
             + BOOK_REBUILD_WEIGHT   * bid_rebuild
             + MICRO_DRIFT_WEIGHT    * max(0, micro_drift)
             + MID_DRIFT_WEIGHT      * max(0, mid_drift)

sell_impulse = symmetric opposite

activity     = buy_impulse + sell_impulse + |drifts| + spread_compression
```

**Impulse parameters:**

| Parameter | Value |
|-----------|-------|
| BOOK_ACTIVITY_FLOOR | 0.60 |
| BOOK_STEP_WEIGHT | 0.85 |
| BOOK_DEPLETION_WEIGHT | 0.65 |
| BOOK_REBUILD_WEIGHT | 0.25 |
| MICRO_DRIFT_WEIGHT | 0.55 |
| MID_DRIFT_WEIGHT | 0.25 |
| SPREAD_COMPRESSION_WEIGHT | 0.35 |
| PERSISTENCE_WEIGHT | 0.35 |

#### Persistence Confirmation (New in v37)

**Imbalance persistence:** Rolling history of imbalance direction — if consistently positive/negative over `FLOW_SHORT_WINDOW`, it confirms directional conviction.

**Micro persistence:** Rolling history of `(micro - mid) / half_spread` — if micro is consistently above/below mid, it indicates sustained buy/sell pressure.

**Used in breakout_score:**
```
if flow_bias * persistence > 0:        # same direction → boost
    conviction += 0.20 * abs(persistence)
if pressure aligned with compression:  # book compressing into support/resistance
    conviction += 0.20 * compression
```

#### Extended Memory Store (v37 vs v36)

| History Stored | v36 | v37 |
|----------------|-----|-----|
| volume_history | trade volume | order book activity score |
| signed_flow_history | trade-tape signed flow | buy_impulse - sell_impulse |
| bias_history | trade direction bias | flow bias |
| compression_history | — | spread_compression (NEW) |
| imbalance_history | — | per-tick imbalance (NEW) |
| micro_premium_history | — | (micro - mid) / half_spread (NEW) |
| prev_book | — | complete book snapshot (NEW) |

**Parameter changes from v36:**

| Parameter | v36 | v37 | Direction |
|-----------|-----|-----|-----------|
| PRESSURE_BIAS_SCALE | 0.40 | 0.22 | ↓ reduced |
| BREAKOUT_FOLLOW_SCALE | 0.30 | 0.18 | ↓ reduced |
| BREAKOUT_QUOTE_TIGHTEN | 0.40 | 0.18 | ↓ reduced |
| BREAKOUT_HOLD_BONUS | 0.25 | 0.12 | ↓ reduced |

The scale reductions reflect that v37's signals are **higher quality** (directly from book state, not inferred from trade tape) — so less amplification is needed.

---

### Traderv38 — Single Parameter Tweak

**Only change from v37:** `BREAKOUT_FOLLOW_SCALE: 0.18 → 0.145`

This reduces the weight of breakout signals in the predicted edge:
```
provisional_edge = regression_edge + (0.145 * breakout_score) + (0.20 * pressure)  # v38
provisional_edge = regression_edge + (0.18  * breakout_score) + (0.20 * pressure)  # v37
```

Everything else — architecture, methods, all other parameters — is identical to v37.

---

### Traderv39 — Single Parameter Tweak

**Only change from v37:** `BREAKOUT_HOLD_BONUS: 0.12 → 0.09`

Reduces the threshold adjustment when holding a breakout-aligned position. Produces slightly more aggressive exits from breakout trades.

Everything else identical to v37.

---

### Traderv40 — Bayesian Parameter Optimization

**Only changes from v37:** Parameter values (likely from automated optimization). Architecture unchanged.

| Parameter | v37 | v40 |
|-----------|-----|-----|
| PRESSURE_BIAS_SCALE | 0.22 | 0.1608788 |
| BREAKOUT_FOLLOW_SCALE | 0.18 | 0.1818422 |
| BREAKOUT_QUOTE_TIGHTEN | 0.18 | 0.15224482 |
| BREAKOUT_HOLD_BONUS | 0.12 | 0.11479172 |
| BOOK_ACTIVITY_FLOOR | 0.60 | 0.65147839 |
| BOOK_STEP_WEIGHT | 0.85 | 0.86519435 |
| BOOK_DEPLETION_WEIGHT | 0.65 | 0.67874424 |
| MICRO_DRIFT_WEIGHT | 0.55 | 0.56270591 |

Despite the optimized parameters, v40 underperforms v37 in practice — the optimization likely overfit to a specific backtest window.

---

## Why Traderv37 Outperforms

Traderv37 outperforms all other versions because it is the first (and only) version that reads **order book state changes directly**, not just trade tape or price history. This is a qualitative improvement in signal quality, not just a parameter change.

### Reason 1: Order Book Microstructure vs Trade Tape

**v36 and earlier** infer flow from filled trades — they look at what actually traded, at what price, and derive direction from that. This is **lagging**: by the time a trade appears in the tape, the order book has already moved.

**v37** tracks what the order book is *doing* between ticks — are bids stepping up? Are offers getting depleted? Is the spread compressing? These are **leading** signals of an incoming directional move.

| Signal | v36 (Trade Tape) | v37 (Book State) |
|--------|-----------------|-----------------|
| Source | Filled trades | Live bid/ask changes |
| Timing | Lagging — post-fill | Leading — pre-fill |
| Depletion | Inferred from volume | Directly measured |
| Spread compression | Not measured | Directly measured |
| Bid/ask stepping | Not measured | Directly measured |

### Reason 2: Persistence Confirmation Eliminates False Positives

v37 adds `imbalance_persistence` and `micro_persistence` — rolling histories that check whether directional signals are **consistently** in the same direction across multiple ticks, not just momentarily spiking.

In v36, a single tick with high volume or imbalance could trigger a breakout signal. In v37, the signal must persist across `FLOW_SHORT_WINDOW` (6 ticks) before receiving full conviction weight. This filters out noise-driven false breakouts that cause v36 to overtrade.

The persistence signals feed into `breakout_score()`:
```python
if flow_bias * persistence > 0:  # same direction — sustained pressure
    conviction += 0.20 * abs(persistence)
```

### Reason 3: Spread Compression as a Pre-Breakout Signal

`spread_compression` — the narrowing of the bid-ask spread — is a well-known microstructure signal that precedes directional moves. Liquidity providers pull quotes just before a move, compressing the spread.

v37 is the **only version** that measures this. It feeds directly into:
- `activity` score (more activity when spread compresses)
- `breakout_score()` confirmation (adds `0.20 * compression` when aligned with pressure)

v36 and earlier are completely blind to spread compression.

### Reason 4: Decomposed Impulse is More Accurate Than Net Flow

v36's signed flow is `sum(buy_trades) - sum(sell_trades)` — a single number. This is coarse: a large sell trade and a large buy trade in the same tick cancel out, showing zero flow, even though both sides are active.

v37's buy/sell impulse decomposition keeps both sides separate:
```
activity = buy_impulse + sell_impulse + |drifts| + compression
```

High activity with balanced impulses signals **two-sided volatility** (volatile regime). High activity with lopsided impulses signals **directional conviction** (trend regime). v37 can distinguish between these; v36 cannot.

### Reason 5: Parameters Were Recalibrated for Higher-Quality Signals

Because v37's signals are more accurate, the scaling coefficients were reduced (e.g., `BREAKOUT_FOLLOW_SCALE` from 0.30 → 0.18, `BREAKOUT_HOLD_BONUS` from 0.25 → 0.12). Smaller weights on better signals produce more stable, less reactive behavior than larger weights on noisier signals.

v38 and v39 attempted to tune these parameters further but reduced them too much (v38) or clipped the hold bonus too aggressively (v39), losing the signal's contribution. v40's Bayesian optimization likely overfit to historical data.

---

## Architectural Evolution Timeline

```
v30  ── Regression MM
         └─ 8-tick price history, regime from predicted_edge, fit, imbalance, momentum
            Stateless (no memory across ticks)

v31  ── + Parameter tuning (wider edges, higher gammas, HOLD_TIME_COEF)

v32  ── + Target bands
         └─ regime-specific position targets; GAMMA_RANGE 0.28→0.69

v33  ── + MAX_QUOTE_EDGE=9, REGRESSION_HORIZON 2.0→0.5

v34  ── + Parameter search (near-zero INVENTORY_SKEW, very short horizon)

v35  ── + Hybrid Alpha
         └─ Blends reference price (45%) + mid (20%) + micro (25%) + flow (10%)
            guarded_hybrid_alpha() damps conflicting signals
            predicted_edge = 72% regression + 28% hybrid alpha

v36  ── + Product Memory + Flow Analysis
         └─ product_memory persists volume/flow/bias/pressure across ticks
            market_flow_metrics() from trade tape
            burst_score(), pressure_bias(), breakout_score()
            breakout_score >= 1.0 can trigger trend independently

v37  ── + Book Microstructure + Persistence   ← BEST PERFORMER
    ★    └─ Tracks bid/ask stepping, depletion, rebuild, micro/mid drift
            buy_impulse / sell_impulse decomposition
            spread_compression measurement
            imbalance_persistence + micro_persistence over rolling window
            Signals are leading (pre-fill) rather than lagging (post-fill)
            Higher signal quality → lower scaling coefficients

v38  ── v37 BREAKOUT_FOLLOW_SCALE 0.18→0.145 (under-weighted breakout)

v39  ── v37 BREAKOUT_HOLD_BONUS 0.12→0.09 (too-aggressive exits)

v40  ── v37 + Bayesian param optimization (overfit to backtest window)
```

---

## Parameter Progression Table

Key TOMATOES parameters across all active versions:

| Parameter | v30 | v31 | v32 | v33 | v34 | v35 | v36 | **v37** | v38 | v39 | v40 |
|-----------|-----|-----|-----|-----|-----|-----|-----|---------|-----|-----|-----|
| BASE_TAKE_EDGE | 1.10 | 1.25 | 0.80 | 0.80 | 0.654 | 0.78 | 0.78 | **0.78** | 0.78 | 0.78 | 0.78 |
| BASE_QUOTE_EDGE | 2.25 | 2.75 | 2.75 | 2.75 | 2.75 | 2.68 | 2.68 | **2.68** | 2.68 | 2.68 | 2.68 |
| MAX_QUOTE_EDGE | 5.0 | 5.0 | 5.0 | 9.0 | 10.04 | 9.0 | 9.0 | **9.0** | 9.0 | 9.0 | 9.0 |
| GAMMA_RANGE | 0.28 | 0.34 | 0.693 | 0.693 | 0.752 | 0.693 | 0.693 | **0.693** | 0.693 | 0.693 | 0.693 |
| GAMMA_TREND | 0.14 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 | **0.10** | 0.10 | 0.10 | 0.10 |
| GAMMA_VOLATILE | 0.24 | 0.40 | 0.40 | 0.40 | 0.40 | 0.40 | 0.40 | **0.40** | 0.40 | 0.40 | 0.40 |
| PRESSURE_BIAS_SCALE | — | — | — | — | — | — | 0.40 | **0.22** | 0.22 | 0.22 | 0.161 |
| BREAKOUT_FOLLOW_SCALE | — | — | — | — | — | — | 0.30 | **0.18** | 0.145 | 0.18 | 0.182 |
| BREAKOUT_HOLD_BONUS | — | — | — | — | — | — | 0.25 | **0.12** | 0.12 | 0.09 | 0.115 |
| Product Memory | No | No | No | No | No | No | Yes | **Yes** | Yes | Yes | Yes |
| Book Microstructure | No | No | No | No | No | No | No | **Yes** | Yes | Yes | Yes |
| Persistence Tracking | No | No | No | No | No | No | No | **Yes** | Yes | Yes | Yes |

---

## Recommendations

1. **Keep v37 as the base.** Its order book microstructure analysis is a genuine architectural improvement over all prior versions.

2. **Do not reduce BREAKOUT_FOLLOW_SCALE below 0.18.** v38 tried 0.145 and underperformed — the breakout signal contribution at 0.18 is the calibrated optimum for v37's architecture.

3. **Do not reduce BREAKOUT_HOLD_BONUS below 0.12.** v39 tried 0.09 and produced overly aggressive exits from breakout trades.

4. **Be cautious with automated parameter optimization.** v40 applied Bayesian optimization across all 8 book-activity parameters simultaneously and overfit — despite better-sounding values, it underperformed v37's round numbers.

5. **Future improvements should target:**
   - Multi-level book depth (v37 only tracks best bid/ask; tracking 2–3 levels would improve depletion signals)
   - Cross-product signals (EMERALDS and TOMATOES may share macro flow — currently they are independent)
   - Adaptive window sizing for persistence (fixed `FLOW_SHORT_WINDOW=6` may underperform in very fast or very slow markets)

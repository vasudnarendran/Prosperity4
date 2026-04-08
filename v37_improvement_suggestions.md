# Traderv37 — Improvement Suggestions
## Based on full code analysis (not speculation)

**Date:** 2026-04-08
**File analysed:** `Bots/Traderv37.py`

Each suggestion below is tied to a specific function and line number. Nothing here is speculative — every claim is verifiable directly in the code.

---

## Issue 1 — Dead Code: Breakout Quote Shift Never Fires

**Severity: High — this is a silent bug**

**Where:** `passive_quotes()` — line 1212

**The code:**
```python
breakout_shift = int(round(min(1.0, abs(breakout_score) * self.BREAKOUT_QUOTE_TIGHTEN)))
```

**The problem:**  
`BREAKOUT_QUOTE_TIGHTEN = 0.18`. The maximum `breakout_score` is capped at 2.5 (by `min(2.5, conviction)` in `breakout_score()`).

```
max value before round: min(1.0, 2.5 × 0.18) = min(1.0, 0.45) = 0.45
int(round(0.45)) = 0
```

`breakout_shift` is **always 0**. The entire block below it (lines 1213–1222) never executes. The code that was meant to push passive quotes towards the market during breakouts is completely inert.

This happened because BREAKOUT_QUOTE_TIGHTEN was reduced from v36's 0.40 to 0.18. At 0.40:
```
min(1.0, 1.25 × 0.40) = 0.50 → round → 1   ← fires at breakout_score ≥ 1.25
```

**Fix option A — restore the minimum threshold:**
```python
# Change
"BREAKOUT_QUOTE_TIGHTEN": 0.18,
# To
"BREAKOUT_QUOTE_TIGHTEN": 0.40,
```

**Fix option B — rethink as a float shift (not integer):**
Instead of rounding to an integer, apply a fractional quote adjustment:
```python
breakout_shift = min(1.0, abs(breakout_score) * self.BREAKOUT_QUOTE_TIGHTEN)
# Then use it as a continuous offset rather than int ticks
```

This is a parameter fix, not an architectural change. Fix A is the safer starting point.

---

## Issue 2 — hybrid_alpha() Ignores Stored Flow History

**Severity: Medium — under-uses available data**

**Where:** `hybrid_alpha()` — line 864

**The code:**
```python
def hybrid_alpha(self) -> Tuple[float, float]:
    reference_price = float(self.recent_average)
    half_spread = max(1.0, float(self.spread) / 2.0)
    flow_signal = self.imbalance * half_spread * self.ALPHA_FLOW_SPREAD_SCALE
    hybrid_fair = (
        self.ALPHA_REFERENCE_WEIGHT * reference_price   # 0.45
        + self.ALPHA_MID_WEIGHT * float(self.mid)       # 0.20
        + self.ALPHA_MICRO_WEIGHT * float(self.micro)   # 0.25
        + self.ALPHA_FLOW_WEIGHT * (float(self.mid) + flow_signal)  # 0.10
    )
```

**The problem:**  
The `ALPHA_FLOW_WEIGHT = 0.10` component uses only current-tick `self.imbalance` — a noisy single-tick value. Yet the bot explicitly stores `signed_flow_history`, `bias_history`, and `activity_history` across many ticks for exactly this purpose. None of that history is used here.

The smoothed bias from `bias_history[-FLOW_SHORT_WINDOW:]` would be a much more stable estimate of directional flow pressure than the raw current-tick imbalance.

**Concrete fix:**
```python
def hybrid_alpha(self) -> Tuple[float, float]:
    reference_price = float(self.recent_average)
    half_spread = max(1.0, float(self.spread) / 2.0)

    # Use smoothed flow bias from history instead of raw imbalance
    bias_history = self.memory_list("bias_history")
    short_bias = bias_history[-int(self.FLOW_SHORT_WINDOW):]
    smoothed_bias = (sum(short_bias) / len(short_bias)) if short_bias else self.imbalance
    flow_signal = smoothed_bias * half_spread * self.ALPHA_FLOW_SPREAD_SCALE

    hybrid_fair = (
        self.ALPHA_REFERENCE_WEIGHT * reference_price
        + self.ALPHA_MID_WEIGHT * float(self.mid)
        + self.ALPHA_MICRO_WEIGHT * float(self.micro)
        + self.ALPHA_FLOW_WEIGHT * (float(self.mid) + flow_signal)
    )
    ...
```

This change costs nothing (the history is already stored), removes single-tick noise from the fair value estimate, and better uses the architecture v37 was built around.

---

## Issue 3 — price_pressure_history Stored but Never Read

**Severity: Low — wasted memory/serialization**

**Where:** `store_flow_metrics()` — line 849

**The code:**
```python
self.append_memory_value("price_pressure_history", flow_metrics["price_pressure"], history_length)
```

**The problem:**  
`price_pressure_history` is appended to product memory every single tick. I searched the entire file — it is **never read back anywhere**. It occupies space in the JSON `traderData` string that is passed between ticks and contributes to serialization overhead for zero benefit.

**Fix:** Remove this line from `store_flow_metrics()`.

```python
# Remove this line:
self.append_memory_value("price_pressure_history", flow_metrics["price_pressure"], history_length)
```

If price pressure history is later needed (e.g., for a smoothed pressure signal in `hybrid_alpha()`), re-add it then with a purpose.

---

## Issue 4 — Quote Edge Inventory Scaling Flatlines at Low Positions

**Severity: Medium — gradient feedback lost**

**Where:** `quote_edge()` — line 1163

**The code:**
```python
edge += self.SPREAD_INV_COEF * gamma * min(self.position_limit, abs(self.projected_position()))
```

**The problem:**  
With `SPREAD_INV_COEF = 1.1081637` and `GAMMA_RANGE = 0.69283327`:

| Position | Inventory term | Starting edge | Total before cap |
|----------|---------------|---------------|-----------------|
| 0 | 0.0 | 2.68 | ~3.3 |
| 5 | 3.84 | 2.68 | ~7.1 |
| 9 | 6.91 | 2.68 | ~9.7 → **capped at 9.0** |
| 20 | 15.4 | 2.68 | **capped at 9.0** |
| 80 | 61.5 | 2.68 | **capped at 9.0** |

The inventory gradient is completely lost above position ≈ 9. Whether you're holding 10 or 79 units, the quote edge is identically 9.0. The design intention (wider spreads as inventory grows to discourage further loading) stops working as soon as position exceeds ~9.

The root cause is that `SPREAD_INV_COEF` is calibrated for the wrong scale — it's too large relative to `MAX_QUOTE_EDGE`.

**Two fixes to consider:**

Option A — Reduce SPREAD_INV_COEF to keep gradient meaningful across range:
```python
# Change
"SPREAD_INV_COEF": 1.1081637,
# To something like
"SPREAD_INV_COEF": 0.12,  # keeps gradient meaningful up to position ~60
```

Option B — Scale by `soft_limit` instead of raw position, to keep the formula relative:
```python
edge += self.SPREAD_INV_COEF * gamma * (abs(self.projected_position()) / self.soft_limit)
```
This normalises to a 0–1 scale (clamp at ≥1 if needed), making the coefficient meaningful regardless of position limits.

---

## Issue 5 — Momentum Threshold in classify_state() is Hardcoded

**Severity: Low-Medium — cannot be tuned**

**Where:** `classify_state()` — line 969

**The code:**
```python
and self.momentum >= 0.75
```

**The problem:**  
The momentum threshold of `0.75` appears in 4 places inside `classify_state()` (for trend_up detection, trend_down detection, and the two breakout-triggered conditions). It is hardcoded, **not in `DEFAULT_TOMATOES_PARAMS`**. Every other threshold used by the classifier is a parameter that can be tuned — `TREND_EDGE_THRESHOLD`, `FIT_THRESHOLD`, `TREND_IMBALANCE_THRESHOLD`, `BURST_CONFIRM_IMBALANCE`. Momentum is the only exception.

This means any attempt to tune the regime classifier (e.g., via parameter search) will miss the momentum threshold entirely.

**Fix:** Add it as a parameter:
```python
# In DEFAULT_TOMATOES_PARAMS:
"MOMENTUM_TREND_THRESHOLD": 0.75,
```

Then in `classify_state()`:
```python
and self.momentum >= self.MOMENTUM_TREND_THRESHOLD       # trend_up
and self.momentum <= -self.MOMENTUM_TREND_THRESHOLD      # trend_down
and self.momentum >= -self.MOMENTUM_TREND_THRESHOLD      # breakout trend_up guard
and self.momentum <= self.MOMENTUM_TREND_THRESHOLD       # breakout trend_down guard
```

---

## Issue 6 — Dual CONFLICT_ALPHA_DAMP May Be Overly Aggressive

**Severity: Low — investigate before changing**

**Where:** `guarded_hybrid_alpha()` — lines 883–887

**The code:**
```python
if hybrid_alpha * regression_edge < 0:
    weight *= self.CONFLICT_ALPHA_DAMP  # 0.45

if hybrid_alpha * self.imbalance < 0:
    weight *= self.CONFLICT_ALPHA_DAMP  # 0.45 again
```

**The problem:**  
When both conflicts exist simultaneously (alpha disagrees with both regression edge AND imbalance), `weight = 0.45 × 0.45 = 0.2025`. The hybrid alpha contribution is reduced to 20% of its value.

These two conflicts are often correlated — when the regression edge is negative, the imbalance tends to also be negative. Double-penalising for correlated signals over-suppresses the alpha.

**Observation before fixing:** Check empirically how often both conditions are true simultaneously. If it's rare (< 5% of ticks), this is a non-issue. If it's common (> 20%), consider using separate damping weights:

```python
# In DEFAULT_TOMATOES_PARAMS, add:
"REGRESSION_CONFLICT_DAMP": 0.45,   # conflict with regression
"IMBALANCE_CONFLICT_DAMP": 0.70,    # conflict with imbalance (lighter penalty)
```

---

## Summary Table

| # | Issue | Location | Severity | Type | Effort |
|---|-------|----------|----------|------|--------|
| 1 | Breakout quote shift always 0 (dead code) | `passive_quotes()` L1212 | **High** | Parameter bug | Tiny — change one value |
| 2 | hybrid_alpha uses raw imbalance not flow history | `hybrid_alpha()` L867 | **Medium** | Under-utilised data | Small — 3 lines |
| 3 | price_pressure_history written but never read | `store_flow_metrics()` L849 | Low | Wasted memory | Tiny — delete one line |
| 4 | Quote edge gradient flatlines at position ≥ 9 | `quote_edge()` L1163 | **Medium** | Parameter miscalibration | Small — retune one param |
| 5 | Momentum threshold hardcoded, not tunable | `classify_state()` L969 | Low-Med | Inflexibility | Small — add one param |
| 6 | Double CONFLICT_ALPHA_DAMP compounds aggressively | `guarded_hybrid_alpha()` L883 | Low | Verify first | Small |

---

## Recommended Order of Action

1. **Fix Issue 1 first** — it's a one-value change that re-enables a feature that was meant to be working. Restore `BREAKOUT_QUOTE_TIGHTEN` to 0.40 and re-run your comparison. It may noticeably improve breakout fills.

2. **Fix Issue 3** — delete the unused `price_pressure_history` write. Zero downside, frees up a small amount of serialized state.

3. **Fix Issue 2** — replace raw imbalance in `hybrid_alpha()` with smoothed `bias_history`. This is a small code change that better utilises data already being collected.

4. **Investigate Issue 4** — before changing `SPREAD_INV_COEF`, plot or log quote edges at various positions in a backtest to confirm the flatline. Then tune.

5. **Fix Issue 5** — add `MOMENTUM_TREND_THRESHOLD` to params. No behavior change (same default 0.75), but unlocks tuning.

6. **Defer Issue 6** — investigate empirically first. May not be a real problem in practice.

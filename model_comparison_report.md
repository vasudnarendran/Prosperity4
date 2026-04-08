# Current Model vs Past Model — Technical Comparison

## Scope of this comparison

This report compares:

- **Current model:** `56985.py` (the current best model)
- **Past model / baseline:** `53529.py` (an earlier TOMATOES control-style model)

These two versions are meaningfully different at the **architecture** level, not just the parameter level.

---

## Executive summary

The current model is not just a retuned version of the past model. It is a **different generation of architecture**.

The older model is primarily:

- short-horizon regression
- microprice / imbalance based fair value
- rule-based regime detection
- target-position control
- reservation-price market making

The current model keeps that core, but adds a full **microstructure signal stack** on top:

- persistent per-product memory
- order-book flow decomposition
- burst detection
- pressure-memory / support-resistance style state
- breakout scoring
- hybrid alpha blending
- guarded alpha damping
- breakout-aware regime logic
- breakout-aware quote/take behavior

So the current model is best understood as:

> **old control-style market maker + microstructure state machine + memory-augmented directional alpha layer**

In other words, the old model mostly asked:

> “What is fair value, what regime am I in, and how aggressively should I quote around that?”

The current model asks that **plus**:

> “What is the tape doing right now, is pressure building, is a breakout forming, and how much of my directional signal is real versus conflicting?”

---

## Performance difference

Based on the uploaded run summaries:

- **Current model (`56985.py`)**: profit = **2627.875**
- **Past baseline (`53529.py`)**: profit = **2346.4375**

Approximate gain:

- **+281.4375**

That is a large enough difference that the architectural changes are worth documenting carefully.

---

## What stayed the same

Despite the improvements, the basic philosophy is still the same.

### 1. Two-product split

Both versions keep separate traders for:

- `EMERALDS`
- `TOMATOES`

### 2. EMERALDS remains a stable anchored market maker

In both versions, EMERALDS is still:

- anchored to a reference price near `10000`
- lightly blended with current market prices
- inventory-aware
- primarily a market-making sleeve rather than a predictive sleeve

### 3. TOMATOES still uses a control-style market-making core

Both versions retain:

- short-horizon regression
- inventory-aware fair value
- time-dependent reservation shift
- regime-based quote/take logic
- separate aggressive and passive execution paths

So this is **not** a total rewrite. The old TOMATOES core still exists inside the new model.

---

## High-level difference in one sentence

### Past model

The past model was mostly a **short-horizon predictive market maker**.

### Current model

The current model is a **short-horizon predictive market maker plus stateful microstructure interpretation**.

That “stateful microstructure interpretation” is the biggest technical upgrade.

---

## EMERALDS changes

EMERALDS changed much less than TOMATOES.

### What stayed the same

The following logic is structurally unchanged:

- `fair_value()`
- `adjusted_fair_value()`
- `tiered_take_size()`
- `clear_orders()`
- `passive_quotes()`
- `passive_size()`

So EMERALDS is still the simple inventory-aware anchored MM sleeve.

### What changed

Mostly **parameter retuning**:

- `INVENTORY_SKEW` became much smaller
- `SOFT_LIMIT_RATIO` became much larger

Interpretation:

- the current EMERALDS trader is **less sensitive per unit of inventory**
- but is willing to operate with a **different effective inventory envelope**

### Practical meaning

The newer EMERALDS model is still simple, but it is **better calibrated**.
It likely became less twitchy around inventory while still staying disciplined.

### Execution note

The current best model uses **top-of-book taking** for EMERALDS, not the earlier multi-level sweep structure that appeared in some intermediate branches.
So the final winning version seems to have favored **cleaner execution logic + better calibration** over more complicated sweep execution.

---

## TOMATOES changes — the real architectural jump

This is where the big difference is.

## 1. State persistence: from memory-light to memory-rich

### Past model

The old model stored essentially:

- `mid_history`

That let it compute regression, recent average, momentum, volatility, and target behavior.

### Current model

The new model stores:

- `mid_history`
- `product_memory`

And within `product_memory`, it maintains things like:

- previous book snapshot (`prev_book`)
- `activity_history`
- `signed_flow_history`
- `bias_history`
- `price_pressure_history`
- `compression_history`
- `imbalance_history`
- `micro_premium_history`
- `pressure_buckets`

### Why this matters

This is a major shift.

The old model looked mostly at **current state + short price history**.
The new model looks at **current state + recent order-book behavior history + remembered pressure map**.

That means the current model can ask:

- are buyers repeatedly stepping in?
- is activity unusually high versus recent history?
- has the same directional pressure persisted over several updates?
- are there remembered support/resistance-like zones from prior order-book behavior?

This is one of the biggest reasons the new model is stronger.

---

## 2. Order-book flow metrics: from static snapshot to dynamic book interpretation

### Past model

The old model mainly used:

- mid
n- microprice
- imbalance
- momentum
- regression outputs

That is useful, but still mostly **snapshot-based**.

### Current model

The new model adds `market_flow_metrics()`.

This computes features such as:

- activity
- signed flow
- flow bias
- price pressure
- flow acceleration
- compression
- persistence
- micro drift
- mid drift
- imbalance drift

### What this means conceptually

The old model asked:

> “What does the book look like right now?”

The current model asks:

> “How is the book changing, and what kind of behavior is that change implying?”

That is a huge difference.

Examples:

- Are bids rebuilding after being hit?
- Are asks depleting faster than bids?
- Is the spread compressing while one side stays stronger?
- Is directional pressure accelerating?

These are **tape-reading / microstructure** style features.

---

## 3. Burst detection: new event-awareness layer

### Past model

No explicit burst or unusual-activity detector.

### Current model

Adds `burst_score()`.

It compares current activity against:

- recent activity history
- percentile thresholds
- local baseline activity

And then confirms / dampens the signal using:

- imbalance alignment
- price-pressure alignment
- persistence alignment
- compression
- flow acceleration

### Why this matters

This gives the model an explicit answer to:

> “Did the market just wake up?”

That is important because the optimal response to a quiet move and an explosive move is not the same.

This layer likely improved:

- breakout recognition
- avoiding fading real moves too aggressively
- selective aggression when flow becomes unusually directional

---

## 4. Pressure memory: new support/resistance style mechanism

### Past model

No persistent price-level memory.

### Current model

Adds:

- `update_pressure_memory()`
- `pressure_bias()`
- decaying `pressure_buckets`

These buckets accumulate directional pressure around price zones and decay over time.

### What this does conceptually

The model now remembers something like:

- “buyers kept defending around here”
- “sellers leaned around this level”
- “this zone behaved like support/resistance in recent microstructure”

This is not classic charting. It is a **book-derived pressure map**.

### Why this matters

This gives the model context about *where* directional pressure previously mattered, not just whether pressure exists right now.

That improves:

- fair value context
- breakout confirmation
- directional conviction

---

## 5. Breakout model: from implicit trend detection to explicit breakout scoring

### Past model

The old classifier decided regime mostly from:

- predicted edge
- fit quality
- imbalance
- momentum
- spread / volatility

So trend detection existed, but it was mostly based on price and book-state conditions.

### Current model

Adds explicit `breakout_score()` based on:

- burst score
- flow bias
- price pressure
- persistence
- compression
- pressure bias
- micro vs mid alignment
- existing predicted edge
- momentum compatibility

### Why this matters

The new model can explicitly distinguish:

- a weak directional drift
- a real breakout with follow-through potential

This is much richer than the old “regression + threshold” logic.

It also feeds into:

- regime classification
- target inventory sizing
- take-edge tightening / widening
- quote-edge tightening in trend states

So breakout awareness is not just a score. It changes behavior across the whole pipeline.

---

## 6. Hybrid alpha: new signal-combination layer

### Past model

The old model’s directional core was mostly:

- regression edge
- imbalance / microprice / history blend inside fair value

This is still a solid predictive-control system, but the alpha expression is relatively compact.

### Current model

Adds:

- `hybrid_alpha()`
- `guarded_hybrid_alpha()`

`hybrid_alpha()` blends:

- reference / recent-average price
- current mid
- current micro
- flow-derived adjustment

Then `guarded_hybrid_alpha()` damps that alpha when it conflicts with:

- regression direction
- imbalance
- momentum
- current position alignment / inventory load
- range regime

### Why this matters

This is a major improvement in signal quality.

Instead of relying on one directional estimate, the current model says:

- combine several opinions
- cap the raw alpha
- reduce it when the context says it is less trustworthy

This is a more robust alpha-combination framework.

---

## 7. Regime classification became richer and less purely threshold-based

### Past model

`classify_state()` used:

- predicted edge
- fit quality
- imbalance
- momentum
- micro vs mid
- volatility / spread toxicity

### Current model

`classify_state()` now also considers:

- breakout score
- flow bias
- breakout-dependent threshold relaxation / tightening
- breakout-aware volatility filtering

### Practical effect

The current model can enter `trend_up` / `trend_down` not only because price prediction is strong, but also because the **microstructure evidence says a move is actively forming**.

That makes regime detection more event-aware and less dependent on regression alone.

---

## 8. Target position changed from “edge-only conviction” to “edge + breakout conviction”

### Past model

The old `target_band()` and `target_position()` depend mostly on:

- `predicted_edge`
- `fit_quality`

### Current model

The new target system adds:

- `breakout_score`

So inventory appetite is now based on:

- price forecast strength
- confidence in that forecast
- evidence that a real breakout is underway

### Why this matters

This means inventory can scale up not just when regression is strong, but when the **flow state** supports holding more size.

That improves consistency between:

- signal
- regime
- inventory sizing

---

## 9. Fair value became more expressive

### Past model fair value

The old fair value mainly used:

- mid
- micro
- recent average
- regression prediction
- imbalance
- inventory bias
- regime-dependent line-gap adjustment

### Current model fair value

The new fair value keeps those inputs, but also adds:

- `FAIR_ALPHA_WEIGHT * hybrid_alpha`
- `PRESSURE_BIAS_SCALE * pressure_bias`

### What changed conceptually

Fair value is no longer just:

> “price forecast + imbalance + inventory control”

It is now:

> “price forecast + imbalance + inventory control + blended directional alpha + remembered pressure context”

That makes the new fair more contextual and more expressive.

---

## 10. Take-edge and quote-edge became breakout-aware

### Past model

The old model’s `take_edge()` and `quote_edge()` were driven by:

- regime
- volatility
- position
- fit quality
- time and inventory terms

### Current model

The new model extends this with breakout-aware logic:

- aligned breakout direction can reduce take edge
- opposing breakout direction can increase take edge
- strong breakout in trend regimes can tighten passive quote edge

### Why this matters

The current model is better at answering:

- should I lean in because a breakout is likely genuine?
- should I quote tighter in a real trend?
- should I demand more edge when flow says my passive fill may be toxic?

This is exactly the sort of refinement that often matters in market making.

---

## 11. Execution philosophy shifted toward “signal-quality-aware quoting,” not just parameter tuning

### Past model

The old model already had good control-style execution:

- take if price is sufficiently favorable versus adjusted fair
- quote passively based on regime and risk
- hold exits longer in trends

### Current model

The current model keeps that framework but makes it far more **signal-sensitive**.

Execution now responds to:

- breakout alignment
- flow pressure
- burst context
- pressure-memory alignment
- hybrid alpha agreement/conflict

So the upgrade is not “more execution tricks.”
It is:

> **better judgment about when the existing execution logic should be more or less aggressive**

---

## 12. Parameter landscape changed in a way that matches the new architecture

The new model’s parameters are not just different; they reflect the new design.

Examples:

### EMERALDS

- `INVENTORY_SKEW` dropped sharply
- `SOFT_LIMIT_RATIO` increased materially

### TOMATOES

Key control parameters shifted strongly:

- lower `INVENTORY_SKEW`
- lower `BASE_TAKE_EDGE`
- higher `MAX_QUOTE_EDGE`
- much shorter `REGRESSION_HORIZON`
- much larger inventory/time quote terms
- lower `RESERVATION_SCALE`
- larger `ALPHA_EDGE_SCALE`

And entirely new parameter families appeared:

- alpha-combo weights
- alpha conflict-damping weights
- flow-window parameters
- burst threshold parameters
- pressure-memory parameters
- breakout interaction parameters
- book event weights

### Interpretation

The newer model is calibrated to be:

- more reactive on forecast horizon
- more selective via state-aware filtering
- more willing to use large quote envelopes when needed
- more dependent on multi-factor directional confirmation

---

## Structural comparison table

| Area | Past model (`53529.py`) | Current model (`56985.py`) |
|---|---|---|
| EMERALDS | Simple anchored MM | Same structure, retuned |
| Tomatoes core | Regression + control MM | Same core retained |
| Memory | `mid_history` only | `mid_history` + `product_memory` |
| Book-state tracking | None persistent | previous book snapshot stored |
| Flow analysis | No explicit flow decomposition | full `market_flow_metrics()` |
| Burst detection | None | `burst_score()` |
| Pressure memory | None | decaying price buckets + `pressure_bias()` |
| Alpha combination | Single primary predictive edge | hybrid alpha + guarded damping |
| Breakout model | implicit only | explicit `breakout_score()` |
| Regime detection | threshold-based on edge + imbalance + momentum | edge + imbalance + momentum + breakout + flow bias |
| Inventory targeting | edge/fit-quality only | edge/fit-quality + breakout conviction |
| Fair value | prediction + imbalance + inventory | prediction + imbalance + inventory + hybrid alpha + pressure bias |
| Execution adjustments | regime/volatility/position aware | same + breakout-aware |
| Trader data persistence | only `mid_history` | `mid_history` + `product_memory` |

---

## Why the new model likely outperformed

A plausible explanation for the performance jump is:

### 1. Better signal quality

The current model is better at distinguishing:

- weak drift
- noisy move
- real breakout
- flow-supported continuation

### 2. Better context awareness

The older model saw the market mostly as a sequence of snapshots.
The newer model sees it as an evolving process with memory.

### 3. Better alignment between signal and inventory

Breakout-aware target sizing and pressure-aware fair value make the new model more consistent internally.

### 4. Better aggression control

The new model can become more aggressive when the move is backed by flow and more conservative when signals conflict.

### 5. Stronger separation between “forecast” and “trust in forecast”

The current architecture explicitly evaluates both:

- direction
- conviction

That is a big improvement over pure point-estimate logic.

---

## The single most important upgrade

If I had to identify the one change that most transformed the model, it would be:

> **adding persistent order-book memory and turning it into flow / pressure / breakout features**

That is what moved TOMATOES from a good predictive-control market maker to a much more sophisticated **microstructure-aware state machine**.

---

## The second most important upgrade

> **hybrid alpha + guarded damping**

This likely improved robustness by preventing any one directional input from dominating when the evidence was mixed.

---

## What the current model still fundamentally is

Despite all the new machinery, the current model is still not an HMM, Hawkes, or RL market maker.
It is still a **carefully engineered rule-based market maker with predictive overlays**.

That is important because:

- it remains interpretable
- it remains debuggable
- each signal has a clear role
- behavior can still be reasoned about manually

So the model improved by **adding layered intelligence**, not by abandoning interpretability.

---

## Bottom-line summary

The past model was a strong control-style TOMATOES market maker built around regression, imbalance, reservation pricing, and continuous inventory targeting.

The current model keeps that base, but adds:

- persistent memory
- dynamic order-book flow analysis
- burst detection
- pressure-memory
- breakout scoring
- hybrid alpha blending
- alpha conflict damping
- breakout-aware regime and execution logic

So the current model is not simply “better tuned.”
It is **architecturally richer** and much more aware of how the tape is evolving.

That is the main technical reason it looks like a materially stronger model.

# Trading Bot Handoff Note for Coding Agent

## Purpose

This note explains:

1. what the current best model is doing,
2. what modeling components and quantitative ideas it already uses,
3. what was likely tuned offline versus what runs live in the bot,
4. which research-inspired improvements are realistic,
5. which improvements are likely to matter most,
6. an implementation order for the next development cycle.

This is written to be read by a coding agent or human developer who needs a practical, technically grounded summary of the current system.

---

## Current Best Model: What It Is

The current best model is a **two-product market-making / short-horizon alpha bot** with:

- one simpler sleeve for **EMERALDS**,
- one much richer sleeve for **TOMATOES**,
- persistent state across timesteps through `traderData`,
- hand-coded execution and risk logic,
- and a parameter set that was almost certainly **optimized offline** rather than chosen manually.

The uploaded result file shows the current best run finished **FINISHED** with a total **profit of 2627.875**.

Files used:

- `56985.py` = current best model code
- `56985.log` = raw activities log
- `56985.json` = finished result summary

---

## High-Level Architecture

At a high level the bot does the following every step:

1. reads the order book and current positions,
2. updates recent price history and product-specific memory,
3. estimates a fair value,
4. measures short-horizon pressure and direction,
5. classifies the market state,
6. decides how much inventory it wants,
7. sets aggressive and passive prices,
8. places buy/sell orders subject to risk limits.

So the strategy is **not** just “buy low, sell high.” It is a layered control system with:

- signal estimation,
- regime gating,
- inventory control,
- execution logic,
- and parameter tuning.

---

## What the Model Already Uses

## 1. Top-of-book fair value estimation

The bot computes:

- **mid-price** = average of best bid and best ask,
- **microprice** = top-of-book volume-weighted price,
- **imbalance** = relative pressure between best bid volume and best ask volume.

This is the core short-horizon price snapshot.

### Intuition

- Mid-price says where the market is centered.
- Microprice says which side looks more likely to move first.
- Imbalance says whether buyers or sellers are stronger right now.

### Important limitation

The current microprice and imbalance use **only the best bid and best ask**, not deeper book levels.
That is one of the most important remaining gaps.

---

## 2. Short-horizon regression signal

The TOMATOES trader fits a very short rolling linear regression on recent mids using:

- `REGRESSION_WINDOW`
- `REGRESSION_HORIZON`

It produces:

- `predicted_now`
- `predicted_next`
- `fit_quality`
- `volatility`

### Intuition

This is a tiny trend detector:

- if the recent line slopes up, that is mild bullish evidence,
- if the fit is clean, trust it more,
- if the path is noisy, trust it less.

This is **not** a full ML model. It is a small statistical forecasting component.

---

## 3. Hybrid alpha blending

TOMATOES does not rely on one signal only.
It blends multiple views of the market into a single directional estimate.

The code contains:

- `hybrid_alpha()`
- `guarded_hybrid_alpha()`
- a final `predicted_edge` that combines:
  - regression edge,
  - hybrid alpha,
  - breakout score,
  - pressure bias.

### Intuition

Think of this as combining several analysts:

- one looks at short-term trend,
- one looks at microprice / imbalance,
- one looks at book-flow behavior,
- one looks at breakout strength,
- one looks at remembered pressure zones.

The bot then combines their opinions into one edge estimate.

### Important limitation

These signals are probably **partly redundant**.
The model may be double-counting related information.
That is why **weighted residualization / alpha orthogonalization** is a real candidate improvement.

---

## 4. Order-book flow analysis

The TOMATOES sleeve has a rich inferred-flow layer.
It tracks book changes over time and computes things like:

- step changes,
- depletion,
- rebuild,
- signed flow,
- flow acceleration,
- book activity,
- persistence,
- micro drift,
- mid drift,
- spread compression.

This is driven by functions and state related to:

- current and previous book states,
- rolling memory lists,
- flow histories,
- product memory.

### Intuition

This layer tries to answer:

- are bids getting eaten?
- are asks rebuilding?
- is pressure one-sided?
- is the tape suddenly more active than usual?
- is that activity persistent?

This is already more advanced than simple price-indicator trading.

---

## 5. Burst detection

The current model explicitly looks for unusually strong short-term activity using:

- `FLOW_SHORT_WINDOW`
- `FLOW_LONG_WINDOW`
- `BURST_PERCENTILE`
- `BURST_CONFIRM_IMBALANCE`

### Intuition

Burst score answers:

> “Did the market suddenly wake up?”

That is important because many real short-term moves begin with a burst in activity before price fully reflects it.

---

## 6. Pressure memory / support-resistance memory

The TOMATOES trader stores decaying price-bucket pressure state using:

- `PRESSURE_MEMORY_DECAY`
- `PRESSURE_PRICE_BUCKET`
- `pressure_buckets`
- `pressure_bias()`

### Intuition

This is a lightweight memory of where buyers or sellers have been active recently.
It behaves like a microstructure version of support/resistance.

This is already conceptually close to textbook support-resistance or channel ideas, but implemented from order-book behavior instead of chart lines.

---

## 7. Breakout score

The bot computes a breakout score based on:

- burst activity,
- flow bias,
- price pressure,
- persistence,
- pressure memory,
- regression direction.

### Intuition

Breakout score asks:

> “Is this move probably real enough to follow, or is it just noise?”

This matters because the bot needs to know when to:

- fade the move,
- follow the move,
- hold inventory longer,
- tighten or widen quotes.

---

## 8. Regime classification

The TOMATOES sleeve classifies the market into one of:

- `trend_up`
- `trend_down`
- `range`
- `volatile`

using a rule-based classifier.

Inputs include:

- predicted edge,
- fit quality,
- volatility,
- imbalance,
- momentum,
- breakout score,
- flow bias.

### Intuition

The strategy first decides what kind of market it is in.
Then it changes behavior accordingly.

For example:

- in `trend_up` it is more willing to carry longs,
- in `trend_down` it is more willing to carry shorts,
- in `range` it leans more mean-reverting,
- in `volatile` it becomes more defensive.

### Important limitation

This is still a **hard-threshold rule system**.
That can cause abrupt switching.
An HMM is one possible research-inspired alternative, but a simpler and lower-risk improvement would be **regime hysteresis** or regime probabilities rather than a full HMM rewrite.

---

## 9. Target position logic

The bot does not directly trade from the raw signal.
Instead it maps conviction into a desired inventory level using:

- `target_band()`
- `target_position()`

### Intuition

This is the bridge between prediction and risk.
It answers:

> “Given what I think the market will do, how much inventory do I actually want?”

This is important because a good signal is not enough.
Position sizing is where a lot of real PnL and drawdown behavior comes from.

---

## 10. Inventory-aware reservation price

The model uses a control-style reservation-price adjustment based on:

- current position,
- target position,
- regime-specific gamma,
- volatility,
- time remaining,
- trend/range bias terms.

Relevant parameters include:

- `GAMMA_RANGE`
- `GAMMA_TREND`
- `GAMMA_VOLATILE`
- `RESERVATION_SCALE`
- `TIME_HORIZON_TICKS`

### Intuition

This is not “what is fair for the market?”
It is:

> “What price is fair for *me*, given my inventory and risk?”

If the bot is already too long, it should want to sell sooner.
If it is too short, it should want to buy sooner.

This is strongly inspired by the same control logic that appears in Avellaneda–Stoikov-type market making.

---

## 11. Dynamic quote-edge and take-edge logic

The bot separately decides:

- how far passive quotes should be from fair,
- how much edge it requires before aggressively taking liquidity.

This depends on:

- regime,
- volatility,
- position,
- breakout score,
- trend-hold effects,
- time remaining.

### Intuition

This layer answers:

- how defensive should my quotes be?
- how urgently should I cross the spread?
- when should I hold exits longer instead of flattening too early?

This is one of the most important parts of the current model.
Historically, quote-discipline and hold-discipline changes moved performance more than some of the other “fancier” ideas.

---

## 12. Aggressive vs passive execution split

The bot explicitly separates:

- **aggressive orders** (`take_orders`) from
- **passive orders** (`passive_quotes`, `passive_size`, `allow_passive`).

### Intuition

Aggressive = pay now, get filled now.
Passive = wait for the market to come to you.

The bot is already aware that:

- passive orders save spread but expose you to adverse selection,
- aggressive orders cost spread but sometimes are smarter when conviction is high.

This is exactly the trade-off discussed in market-making literature.

---

## 13. Persistent cross-timestep memory

Unlike earlier versions, the current best model stores more than just price history.
It stores `product_memory` inside `traderData`, including lists and maps for flow, activity, pressure buckets, and other rolling state.

### Intuition

This gives the model memory of how the market has been behaving.
Without it, the bot would only see isolated snapshots.
With it, the bot sees evolving context.

---

## 14. Offline optimization / parameter tuning

The current parameter values contain many oddly specific floating-point constants such as:

- `0.0328922991`
- `0.69283327`
- `1.1081637`
- `1.7791177`
- `1.4153631`

These almost certainly did **not** come from manual tuning alone.
They are consistent with some kind of offline optimization process.

### What this likely means

The live bot does **not** contain CMA-ES.
But CMA-ES or another gradient-free optimizer was likely used **outside the runtime code** to search parameter values.

### Why CMA-ES fits here

CMA-ES is a good match because this strategy has:

- thresholds,
- caps,
- clamping,
- branching,
- non-smooth objective behavior,
- and parameter interactions.

That makes gradient methods awkward.
CMA-ES is well suited for this kind of black-box tuning.

---

## What the Textbook Already Matches in the Current Bot

The uploaded textbook (*151 Trading Strategies*) is useful mainly as a source of ideas and language, not as something that can be copied directly.

The current bot already overlaps with the most relevant textbook categories:

### Already present in spirit

- **Market making**
- **Alpha combos**
- **Momentum / trend following**
- **Mean-reversion in some states**
- **Support / resistance style logic**
- **Channel / breakout style logic**
- **Activity-conditioned trading**

### Why the textbook is not a direct blueprint

Most textbook strategies are standalone descriptions.
Your current bot is already a **hybrid system** that combines many of them at once.
So the best use of the textbook is:

- identify missing modules,
- identify cleaner formulations,
- not copy entire strategies directly.

---

## Paper-Based Improvements: Which Ones Are Realistic?

Below is a ranked assessment of the research ideas discussed.

## Highest Priority: likely to matter materially

## A. Multi-level microprice / deeper-book imbalance

### Why it fits

Right now the bot’s microprice and imbalance only use top-of-book.
That is a real information gap.

### Why it matters

Deeper levels often carry predictive information about short-term pressure.
A multi-level microprice can reduce noise and improve fair-value estimation.

### Research support

- Stoikov (2018): microprice beats mid-price and weighted mid-price for short-horizon prediction.
- Blakely (2024): extends microprice using higher-rank order-book imbalances.

### Implementation idea

Add features such as:

- depth imbalance over top 3–5 levels,
- multi-level microprice,
- weighted depth slope / convexity,
- spread-conditioned depth imbalance.

### Expected impact

**Medium-to-high**.
This is one of the cleanest improvements because it plugs directly into an obvious gap.

---

## B. Trade-print features and adverse-selection markout modeling

### Why it fits

The current code reads:

- `self.own_trades`
- `self.market_trades`

but the main signal stack is still driven mostly by **inferred book changes**.

That means the bot is leaving direct aggressive-flow information unused.

### What to add

Use market-trade prints to compute:

- signed market buy/sell volume,
- recent aggressive-flow imbalance,
- trade burst counts,
- trade-price slippage vs mid,
- markout after fills.

### Why this is important

A market maker does not just need to know whether it filled.
It needs to know what happened **right after** the fill.
That is adverse selection.

If your bid fills and price drops immediately after, that is a bad fill.
If your ask fills and price continues upward, that is also a bad fill.

### Expected impact

**High**.
This is probably the single most practical research-inspired upgrade.

---

## C. Explicit post-fill trade-off modeling

### Core idea

The key trade-off is:

- tighter quotes fill more often,
- but tighter quotes often have worse post-fill returns.

So the correct question is not:

> “What quote edge maximizes fill probability?”

but:

> “What quote edge maximizes expected post-fill PnL after accounting for fill probability?”

### What to do

For several quote distances / take thresholds, estimate:

- fill probability,
- average short-horizon markout,
- expected value = fill probability × post-fill value.

Then use those estimates to recalibrate `quote_edge()` and `take_edge()`.

### Expected impact

**High** if implemented well.
This is where theory meets practical execution.

---

## Medium Priority: potentially useful, but not first

## D. Weighted residualization / alpha orthogonalization

### Problem it solves

Your alpha stack likely double-counts correlated information.
For example:

- regression edge,
- microprice,
- imbalance,
- breakout,
- pressure bias,
- flow bias

are not independent.

### Improvement idea

Regress one set of signals on the others and trade the residual / orthogonal component instead of summing raw signals directly.

### Why this is attractive

This is a cleaner version of “alpha combo.”
It may make the combined edge less noisy and less redundant.

### Expected impact

**Medium**.
Probably meaningful, but less directly impactful than deeper-book and trade-print signals.

---

## E. Explicit channel / range-break feature

### Why it fits

The bot already has pressure memory and breakout logic.
But it does not appear to have a clean explicit channel state such as:

- distance to rolling high,
- distance to rolling low,
- inside-range vs outside-range.

### Implementation idea

Add:

- rolling max/min over recent N ticks,
- normalized channel position,
- breakout confirmation only if flow and burst also confirm.

### Expected impact

**Medium-low to medium**.
Useful mostly as a cleaner state feature on top of what the bot already does.

---

## F. Regime hysteresis or light probabilistic regimes

### Problem it solves

Current regime classification is threshold-based.
That can cause abrupt state changes.

### Improvement idea

Before jumping to a full HMM, do something simpler:

- require stronger evidence to enter a regime than to stay in it,
- maintain regime probabilities or persistence penalties,
- damp rapid switching.

### Expected impact

**Medium-low**.
Helpful, but not as important as adverse selection and deeper-book information.

---

## Lower Priority / Probably Not Worth It Right Now

## G. Full HMM regime model

This is theoretically appealing, but for this bot it is probably more complexity than value right now.
The current issue is not lack of a fancy regime model.
The bigger missing edges are still deeper book information and fill-quality modeling.

### Expected impact

**Low to medium**, but expensive in complexity.

---

## H. Hawkes process order-flow model

Hawkes models are elegant for self-exciting event processes.
But they are best when you have fine event-time data and enough depth to estimate intensities well.

Your environment appears more snapshot-like than event-stream rich.
So Hawkes is probably too heavy for the near-term payoff.

### Expected impact

**Low for now**.

---

## I. Full reinforcement learning rewrite

RL is interesting for market making, but it is easy to overfit and hard to debug.
For this architecture, better features + gradient-free offline tuning are almost certainly a better next step than a full RL move.

### Expected impact

Potentially large in theory, but **low expected ROI now** relative to implementation cost.

---

## J. Direct formula replacement with Guéant–Lehalle quotes

Your current model already has the right ingredients:

- gamma,
- volatility,
- inventory,
- time,
- quote-width logic.

So the Guéant–Lehalle framework is useful as a **calibration guide**, but probably not as a full replacement unless you also estimate order-arrival intensity well.

### Expected impact

**Medium as a calibration framework**, not as an immediate direct replacement.

---

## Concrete Development Plan for Coding Agent

## Phase 1: Highest-value practical upgrades

### 1. Add deeper-book features

Add to TOMATOES:

- top-3 and top-5 depth imbalance,
- multi-level microprice,
- depth slope / convexity,
- spread-conditioned depth imbalance.

Use these in:

- fair value,
- hybrid alpha,
- breakout score.

### 2. Add trade-print features from `market_trades`

Compute:

- signed aggressive volume,
- recent trade imbalance,
- trade burst intensity,
- trade direction persistence,
- trade-weighted drift.

Use these in:

- breakout score,
- toxicity / adverse-selection gating,
- predicted edge.

### 3. Add post-fill markout tracking

Track for each passive/aggressive fill:

- 1-step markout,
- 3-step markout,
- 5-step markout,
- markout by regime,
- markout by quote distance.

Then use this to recalibrate:

- `quote_edge()`
- `take_edge()`
- maybe `passive_size()`.

---

## Phase 2: Signal cleanup

### 4. Orthogonalize overlapping signals

Build a cleaned alpha stack where:

- raw signals are standardized,
- correlated components are residualized,
- combination weights are estimated offline,
- final alpha is less redundant.

### 5. Add simple channel/range-state features

Add:

- recent rolling high,
- recent rolling low,
- normalized channel position,
- breakout-confirmed-by-flow flag.

---

## Phase 3: Control refinement

### 6. Add regime hysteresis

Do not switch regime on single marginal threshold crossings.
Use separate enter/exit thresholds.

### 7. Recalibrate quote-width family using markout data

Use actual historical performance of quote distances rather than hand logic alone.

---

## What Not to Prioritize Yet

Do **not** prioritize these before the above:

- full HMM rewrite,
- Hawkes processes,
- full RL market-maker,
- cross-product correlation modeling,
- complicated Guéant–Lehalle replacements without calibrated fill intensities.

These are either too heavy or less likely to matter than simpler missing features.

---

## How to Validate Improvements

For every new feature or model change, evaluate all of the following:

1. final PnL,
2. drawdown,
3. inventory variance,
4. passive fill count,
5. aggressive fill count,
6. average passive markout,
7. average aggressive markout,
8. PnL split by product,
9. PnL split by regime,
10. PnL split by time segment.

### Important rule

Do **not** judge a change by final profit alone.
For a market-making strategy, a change can look good in one run while actually worsening:

- adverse selection,
- inventory risk,
- late-run givebacks,
- execution quality.

---

## Practical Summary for a Coding Agent

### The bot already does well

- anchored fair value for EMERALDS,
- short-horizon regression for TOMATOES,
- alpha blending,
- rich inferred order-flow analysis,
- burst and breakout detection,
- pressure-memory,
- regime-based inventory control,
- reservation-price logic,
- adaptive spread / quote logic.

### The biggest remaining gaps

1. **no deeper-book fair-value features**,
2. **no direct use of market trade prints in the core signal stack**,
3. **no explicit post-fill markout model for adverse selection**, even though execution is a core driver of PnL,
4. **likely overlap among alpha components**.

### Best next steps

1. add top-3/top-5 depth imbalance and multi-level microprice,
2. add market-trade-based aggressive-flow features,
3. add markout tracking and use it to calibrate quote/take edges,
4. orthogonalize overlapping alpha signals,
5. only after that, consider regime hysteresis / smoother state transitions.

---

## Recommended Priority Ranking

### Highest expected payoff

1. trade-print features + adverse-selection markouts
2. deeper-book microprice / depth imbalance
3. expected post-fill PnL calibration of quote/take edges

### Next tier

4. weighted residualization of alpha stack
5. channel/range-break state feature
6. regime hysteresis

### Lowest near-term ROI

7. full HMM
8. Hawkes
9. full RL rewrite

---

## Research Notes / Source Pointers

### Uploaded files

- Current best bot code: `56985.py`
- Current best run log: `56985.log`
- Current best run summary: `56985.json`
- Strategy textbook: `151 Trading Strategies` by Kakushadze & Serur

### Key research references mentioned in the discussion

- Stoikov (2018), *The micro-price: a high-frequency estimator of future prices*  
  https://doi.org/10.1080/14697688.2018.1489139

- Blakely (2024), *High resolution microprice estimates from limit orderbook data using hyperdimensional vector Tsetlin Machines*  
  https://arxiv.org/abs/2411.13594

- Lalor & Swishchuk (2024/2025), *Market Simulation under Adverse Selection*  
  https://arxiv.org/abs/2409.12721

- Guéant, Lehalle, Fernandez-Tapia (2013), *Dealing with the Inventory Risk*  
  https://arxiv.org/abs/1105.3115

- Pomorski & Gorse (2023), *Improving Portfolio Performance Using a Novel Method for Predicting Financial Regimes*  
  https://arxiv.org/abs/2310.04536

- Falces Marin et al. (2022), *A reinforcement learning approach to improve the performance of the Avellaneda-Stoikov market-making algorithm*  
  https://doi.org/10.1371/journal.pone.0277042

- Albers, Cucuringu, Howison, Shestopaloff (2025), *The Market Maker’s Dilemma: Navigating the Fill Probability vs. Post-Fill Returns Trade-Off*  
  https://arxiv.org/abs/2502.18625

---

## Final Takeaway

This bot is already a sophisticated hybrid market maker.
The next major improvements are **not** likely to come from replacing it with a completely different textbook strategy.
They are more likely to come from tightening the missing microstructure pieces:

- deeper-book state,
- direct trade-flow features,
- explicit adverse-selection measurement,
- and cleaner alpha combination.

If these are implemented well, they have a realistic chance of outperforming the next round of hand-tuning alone.

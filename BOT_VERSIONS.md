# Bot Versions

This file contains the running experiment log for all bot versions.

V1 (archived):
Works: Yes
Improvement: Simple midpoint market maker. Takes when edge > 1.5, quotes passively at edge 2.0.
Notes: Archived — superseded by V15 base carried over from partner's repo.
PnL: N/A

V15 (base, carried over from partner):
Works: Yes
Improvement: Partner's current best. Modular architecture with EmeraldsTrader (anchor market maker around 10000) and TomatoesTrader (regime-based: trend_up / trend_down / mean_revert / toxic). Parameters tuned via layered coordinate sweep across 15 levers.
Notes: Starting point for this repo. Key parameters vs partner's V13.1 baseline: TOMATOES INVENTORY_SKEW 0.08→0.06, MOMENTUM_WEIGHT 0.20→0.30, BASE_TAKE_EDGE 1.35→1.50, PASSIVE_SIZE 7→8, TREND_THRESHOLD 1.5→1.25. EMERALDS unchanged. Local Python backtest: day -1 final 9961, day -2 final 10040.
PnL: Local Python: ~10000 | Partner Rust: 10326 | Official N/A

V16:
Works: Yes
Improvement: Removed micro >= mid condition from TOMATOES classify_state. Trend detection now requires only momentum + imbalance alignment, not microprice confirmation.
Notes: No change to Python backtest scores — the micro condition was never a binding constraint in this dataset. Still the correct logical fix.
PnL: Local Python: d-1 9961 / d-2 10040 (same as V15)

V17:
Works: Yes
Improvement: Extended TOMATOES HISTORY_LENGTH from 8 to 12 steps for a smoother momentum signal.
Notes: No change to Python backtest scores. Signal quality changes may show more clearly in Rust backtester.
PnL: Local Python: d-1 9961 / d-2 10040 (same as V15)

V18 (tested, not kept):
Improvement tested: EMA + continuous toxicity together.
Notes: Continuous toxicity hurts on both days. EMA alone helps d-1 (+36) but slightly hurts d-2 (-23). Combined, they interfere and both hurt. Continuous toxicity discarded. EMA promoted to V19.

V19:
Works: Yes
Improvement: EMA (alpha=2/13) replaces SMA for TOMATOES recent_average / momentum signal. Keeps V16/17 changes (micro removal, HISTORY_LENGTH=12).
Notes: EMA is more responsive to recent price moves — momentum signal reacts faster to trend shifts. Mixed result vs base: +36 day-1, -23 day-2. Net direction unclear — worth testing on Rust for a larger signal.
PnL: Local Python: d-1 9997 / d-2 10017

V20 (tested, discarded):
Improvement tested: Explicit Clear step — aggressive sell/buy at best_bid/ask when position > soft_limit.
Notes: Hurt day-1 (-69). Paying the full spread (~7 ticks) just to reduce 1-4 units is too expensive. The inventory skew already handles gradual flattening. Discarded.

V21:
Works: Yes
Improvement: Signal-strength-scaled take size in trend regimes only. Edge ratio (raw_edge / take_edge) scales clip up to 1.5x MAX_TAKE_SIZE. Mean-revert keeps fixed size to avoid inventory buildup.
Notes: Neutral vs V19 — trend regimes don't fire frequently enough in this dataset for the scaling to show. Kept as it is logically correct and should help in Rust/official testing where more trend conditions occur.
PnL: Local Python: d-1 9997 / d-2 10017 (same as V19)

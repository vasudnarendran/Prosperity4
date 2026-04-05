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

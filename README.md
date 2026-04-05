# Prosperity
Coding an Algorithm that trades for you


# Backtest

Run the backtest from the `Backtest` folder with:

```bash
python3 run_backtest.py Trader.py
```

The runner uses market data from `Data/`, loads the selected bot from `Bots/`, and writes logs plus plots to `Backtest/output/<bot_name>/`.


# Analysis

Run the analysis tool from the project root:

```bash
python3 Analysis/analyze.py
```

It reads from `Data/` and `Bots/Logs/`, and writes human-readable reports to `Analysis/output/`.


# Bots

Record Total PnL: N/A (official) | ~10000 (local Python backtest)
Bot: Traderv15.py

Current Best Notes:
Base carried over from partner's repo (their V15 after parameter sweep).
EMERALDS: anchor market maker around 10000.
TOMATOES: regime-driven (trend_up / trend_down / mean_revert / toxic) with sweep-tuned parameters.

Version Log:
See [BOT_VERSIONS.md](BOT_VERSIONS.md)

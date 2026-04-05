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

Record Total PnL: N/A
Bot: Trader v1

Current Best Notes:
Starting fresh. First bot is a simple midpoint-based market maker.

Version Log:
See [BOT_VERSIONS.md](BOT_VERSIONS.md)

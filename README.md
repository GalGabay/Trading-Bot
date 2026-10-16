# AI-Enhanced Alpaca Trading Bot

An incremental, paper-only US-equities trading-system project. The detailed
roadmap is in `AI_Enhanced_Alpaca_Trading_Bot_Development_Plan_For_Coding_AI.md`.

## Current progress

Phases 0–9 are implemented: centralized paper-only Alpaca access, validated
market data, SQLite persistence, technical features, a deterministic strategy,
and a single-symbol historical backtester with cost scenarios, metrics, and
expanding-year walk-forward evaluation.

The project does not submit orders. `Signal` objects are recommendations only;
risk, portfolio, and order execution are later phases.

## Local setup on Windows

Use Python 3.12 or another Python version supported by both Windows and the
Raspberry Pi environment. Each machine needs its own virtual environment.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest discover -v
```

Copy `.env.example` to `.env` and enter only Alpaca Paper Trading credentials.
Keep `ALPACA_PAPER=true`. `.env`, SQLite files, downloaded data, and virtual
environments are excluded from Git.

## Project layout

- `app/broker/`: paper-only Alpaca client
- `app/data/`: normalized market data, exchange-calendar validation, SQLite
- `app/ai/`: technical feature calculations
- `app/strategy/`: strategy contract and `trend_following_v1`
- `backtesting/`: local simulation, metrics, and dataset research commands
- `tests/`: unit tests with no broker calls

## Download data and run a historical case study

Run these commands on the Windows development PC with the virtual environment
active. Dates are UTC; the download end and trade end are exclusive. The SDK
fetches all result pages. The downloader keeps only regular-session bars,
validates them against Alpaca's exchange calendar, and writes a CSV plus a
checksum manifest under the ignored `data/` directory. It stops if any
scheduled interval has no bar, so you can investigate the feed or no-trade
period before using the dataset.

```powershell
python -m backtesting.research download --symbol AAPL --start 2021-01-01 --end 2022-01-01 --timeframe 15Min --feed sip --adjustment all --output data/historical/AAPL_15Min_2021.csv
python -m backtesting.research backtest --dataset data/historical/AAPL_15Min_2021.csv --trade-start 2021-02-01 --trade-end 2022-01-01 --output data/reports/AAPL_2021.json
```

January warms up indicators; simulated trading begins in February. The report
contains optimistic, base, and pessimistic cost scenarios. The engine never
calls Alpaca's order API. Fifteen-minute bars avoid Alpaca's first hourly bar,
which can mix premarket and regular-session activity. The default `sip` feed
covers all US exchanges; `iex` covers only IEX and can have materially different
prices, volumes, and bar availability. Alpaca permits historical SIP requests
that end more than 15 minutes ago without a SIP subscription.

The 2021 AAPL download produced 6,540 regular-session bars. The February through
December case study returned +1.22% with zero costs, +0.28% under base costs,
and -2.87% under pessimistic costs on $100,000 starting cash. The dataset and
report are local ignored artifacts, so rerun the commands after cloning. These
results describe one known stock and one historical window; they are not an
out-of-sample or historical-universe result.

The default `all` adjustment is a research total-return proxy for corporate
actions, not a replay of raw executable prices or cash dividends. Record the
adjustment and feed in every report and do not mix datasets with different
settings. The simulator uses whole shares, a 10% position cap, and fixed cost
assumptions. It has no quote-level spread, partial-fill, or market-impact model.

## Walk-forward validation and training later

Phase 9 uses earlier full calendar years to choose among three declared
`trend_following_v1` threshold choices and evaluates the selected choice on
the following year. Download a new multi-year dataset with a new filename:

```powershell
python -m backtesting.research download --symbol AAPL --start 2019-01-01 --end 2024-01-01 --timeframe 15Min --feed sip --adjustment all --output data/historical/AAPL_15Min_2019_2023.csv
python -m backtesting.walk_forward --dataset data/historical/AAPL_15Min_2019_2023.csv --first-test-year 2022 --last-test-year 2023 --output data/reports/AAPL_walk_forward_2022_2023.json
```

With this example, 2019–2021 choose the 2022 settings; 2019–2022 choose the
2023 settings. The selection score is base-cost training total return plus
maximum drawdown; candidates need at least 20 completed training trades.
The report includes each candidate's training metrics and every test year's
optimistic, base, and pessimistic results. Each test year starts with fresh
cash. Open positions are marked to market at year-end and are not carried to
the next fold. This is parameter selection for a fixed rule-based strategy,
not ML training. Keep a later year untouched for a final evaluation and do
not repeatedly adjust the candidate grid after inspecting test results.

The example dataset downloaded 32,600 AAPL bars with no scheduled gaps.
The 2022 and 2023 folds both selected the narrow thresholds using earlier
years. Base-cost returns were +0.20% and +0.46%; pessimistic-cost returns were
-2.12% and -2.49%. These small, cost-sensitive results do not establish a
reliable edge. An attempted 2018–2022 download was rejected because almost
all 15-minute bars on May 2–3, 2018 were absent from the feed; no bars were
fabricated to make that dataset pass.

The 2021 AAPL run is a case study, not a universe test. A proper historical
universe test needs point-in-time membership and delisted stocks, which are
not supplied by the current single-symbol workflow.

After deterministic backtests and paper trading are stable, build an ML dataset from features,
define a future-return label separately, split chronologically, fit and tune
on older windows only, and compare the model against this rule-based baseline
on later unseen windows. Train on the Windows PC; deploy only a small inference
artifact to the Pi. No ML training command exists yet.

## Cross-platform operation

Develop and test on Windows, commit the reviewed repository, and pull it onto
the Raspberry Pi. Install dependencies and configure a separate `.env` on the
Pi. Do not copy the Windows `.venv` or local database to the Pi.

The automated tests have been run on Windows. Run the same test command on the
Pi before deployment; Pi validation has not yet been performed.

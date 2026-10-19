# AI-Enhanced Alpaca Trading Bot

An incremental, paper-only US-equities trading-system project. The detailed
roadmap is in `AI_Enhanced_Alpaca_Trading_Bot_Development_Plan_For_Coding_AI.md`.

For decisions that only the project owner can make, use the
[phase-by-phase responsibilities checklist](docs/owner_responsibilities.md).
The [proposed research program](docs/proposed_research_program.md) describes
the planned rule/ML and timeframe comparisons before a paper trial.
Before approving paper-order risk settings, use the
[risk-limit decision workbook](docs/risk_limit_decision_workbook.md).

## Current progress

Phases 0–11 are implemented: centralized paper-only Alpaca access, validated
market data, SQLite persistence, technical features, a deterministic strategy,
single-symbol historical backtesting and walk-forward evaluation, and a
standalone risk-decision module, and read-only portfolio reconciliation.

The project does not submit orders. `Signal` objects are recommendations only;
the risk gate does not call a broker. Order execution is a later phase.

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
- `app/risk/`: standalone risk decisions for proposed trades
- `config/risk_limits.example.json`: unapproved paper-risk configuration template
- `app/portfolio/`: paper-account snapshots and reconciliation
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

Phase 14 now provides an optional **offline ML research command**. It trains an
XGBoost classifier on existing causal features and a future close-to-close
return label, selects among a small fixed model grid on a later tuning window,
fits sigmoid calibration on a separate later window, and evaluates once on a
final test window. Labels whose future endpoint crosses a window boundary are
removed. No missing candle or feature value is filled. A filtered version of
`trend_following_v1` only vetoes BUY candidates; its existing exits remain.
Market and sector return inputs from the plan are omitted until aligned,
point-in-time source data exists; they are not synthesized from the same stock.
The command compares rule-only and filtered backtests under the same three
cost scenarios. It never submits an order or enables paper execution.
Run its offline unit tests with `python -m unittest tests.test_ml_research -v`.
Choose or request proposed defaults using the
[research-scope decision workbook](docs/research_scope_decision_workbook.md)
before treating a new report as evidence.

On Windows, install the optional research dependencies with
`python -m pip install -r requirements-ml.txt`. Download and review a dataset
covering your chosen windows first. For example, **only if 2024 is still an
uninspected holdout for you**, a 2019–2024 15-minute CSV could be evaluated
with the following exploratory settings:

```powershell
python -m backtesting.ml_research --dataset data/historical/AAPL_15Min_2019_2024.csv --artifact-dir models/aapl_15min_experiment_1 --train-start 2019-01-01 --tune-start 2022-01-01 --calibration-start 2023-01-01 --test-start 2024-01-01 --test-end 2025-01-01
```

The example target is a return greater than 0.5% after five observed bars;
five 15-minute bars are **not** five trading days. Choose the target and
untouched test period before interpreting performance. The model is saved as
XGBoost JSON plus checksum, feature schema, calibration parameters, version
metadata, and a report in the ignored artifact directory. Loading the model
does not connect it to the order manager. Training is intended for Windows;
XGBoost publishes Linux aarch64 wheels for a 64-bit Pi OS, while a 32-bit Pi
environment needs a separately validated inference plan. The current single
AAPL backtester remains a case study: it does not remove survivor bias, model
portfolio-level risk, or simulate broker stops and actual fills. No Phase 14
training or Pi compatibility run has been performed yet. Research artifacts in
`models/` are ignored by Git. If you later approve a model for the Pi, copy
its verified `model.json` and `metadata.json` into a reviewed directory under
the tracked repository and commit that directory; `ResearchModel.load()` can
load from that path. This approval and deployment step is not automatic.
The ML requirements cap NumPy below 2.5 for compatibility with SciPy 1.15;
reinstall them in one environment before real training if local versions differ.

## Phase 10 risk gate

`app/risk/risk_manager.py` evaluates a proposed whole-share BUY or a
risk-reducing SELL using a complete, recent, long-only portfolio snapshot. A
BUY must include a conservative estimated execution price and a stop price
below it; the stop distance estimates initial risk but cannot guarantee the
actual loss. Decisions contain reason codes and the exact policy limits used.
Unknown, stale, or inconsistent account state is rejected. A future paper
workflow must pass the actual evaluation time so a fresh account snapshot
fetched after the signal can be used. Sector and
volatility checks are available when trustworthy metadata is supplied.

The provisional defaults mirror the plan's research examples: 70% maximum
gross exposure, 10% per position, 1% initial risk per trade, and 3% daily
loss. The module also defaults to a 10% drawdown ceiling, seven positions, and
a five-minute snapshot and signal age. Sector and volatility ceilings are disabled by
default. These numbers are unapproved placeholders; choose or accept your
preferred limits before the risk gate is connected to paper-order submission.
This module is not yet wired into the backtester or an order workflow, so the
historical reports above do not reflect these risk checks.

Sections 23 and 24 are implemented as standalone safeguards:
`app/risk/position_sizing.py` proposes whole-share BUY quantities under stop
risk, position, exposure, cash, and optional sector limits;
`app/risk/kill_switch.py` stores a persistent emergency stop in a separate
SQLite file. A missing or unreadable kill-switch state denies new orders.
Neither module submits or closes positions. Phase 12 calls both safeguards
before any explicitly enabled paper order. See [the risk-limit guide](docs/risk_limits.md)
for the meaning of each percentage and how to record your decision in the
tracked `config/risk_limits.json` file once you choose your limits.

## Phase 11 portfolio reconciliation

From the repository root, run this read-only command with paper credentials:

```powershell
python -m app.portfolio.portfolio_manager --database data/trading_bot.sqlite3
```

The command fetches Alpaca paper account, open positions, and open orders. It
normalizes balances and position values, calculates gross and net exposure,
and writes a timestamped SQLite snapshot. The current position and open-order
tables are replaced with the broker's complete responses. The output lists
changes since the previous snapshot and flags any gap between equity and cash
plus position market values. A failed or incomplete fetch does not update the
database. Run this command periodically through your operating system's task
scheduler once the service schedule is designed; the bot does not yet include
a long-running scheduler.

Alpaca account and position responses do not provide a complete realized P&L
ledger, so `realized_pl` remains `null` until fill/activity ingestion is built.
Unrealized P&L is `null` if any open position lacks it. Broker endpoints are
queried sequentially, so a fill during capture can temporarily create an
accounting gap; repeat reconciliation after the account settles. Balances and
positions are broker-authoritative observations, not an order authorization.
The Phase 10 risk gate is connected in the Phase 12 order manager, with paper
submission disabled by default.
Use a separate SQLite file for each Alpaca paper account; reconciliation
rejects snapshots from a different account ID in an existing database.

## Phase 12 order management

`app/orders/order_manager.py` provides an offline `preview()` and a guarded
`submit()` API. There is no CLI, service, or scheduler that invokes submission.
The `enable_paper_submission` constructor flag defaults to `False`. Even if it
is deliberately enabled, `config/risk_limits.json` must contain valid limits
and `approved_for_paper: true`; its initial values are `null` and approval is
`false`. The persistent kill switch must be explicitly reset after review.

The manager accepts only whole-share US equity DAY limit orders during regular
market hours. It checks a fresh broker clock, tradable asset and active paper
account, reconciles positions and open orders, checks buying power, position
sizing, and the approved risk policy, then reserves a unique client order ID in
SQLite before submission. Existing or uncertain IDs are never sent again
automatically. `refresh_status()` records later broker statuses and cumulative
fill quantities, including partial fills, cancellations, and rejections.
Use `OrderIntent.for_signal(...)` to derive the same client order ID from the
strategy, symbol, side, and original timezone-aware signal timestamp on both
Windows and Raspberry Pi. The manager rejects a fresh/random ID for the same
signal. Keep the original signal timestamp when recovering after a restart;
creating a new timestamp represents a new decision. SQLite stores the order's
limit price and refuses a changed request under an existing ID. If submission
times out, broker lookup may confirm it; otherwise the order stays `unknown`,
the kill switch trips, and an operator must investigate before any new order.
Actual individual fills and realized P&L still require a broker activity
ledger. The peak-equity safeguard uses the highest snapshot observed in this
local database; earlier account history is not reconstructed.
The `stop_price` in an order intent is used for risk sizing only; Phase 12
does not place a protective stop or automate exits.

Before any paper activation, complete the [owner risk-limit decision](docs/risk_limit_decision_workbook.md),
review the paper account, and finish the planned exit/stop workflow.

## Phase 13 startup recovery

`app/recovery/state_recovery.py` provides a paper-only startup check. From the
repository root, after configuring paper credentials on that machine, run:

```powershell
python -m app.recovery.state_recovery --database data/trading_bot.sqlite3 --kill-switch data/kill_switch.sqlite3 --risk-config config/risk_limits.json
```

This command does not submit, replace, or cancel orders. It checks SQLite
integrity and schema, loads the risk file, looks up unfinished local orders by
their stable client IDs, reconciles the broker account/positions/open orders,
checks the market clock, and records a structured startup event. It prints a
JSON report. A blocked report exits with code `2`. The first run with a new
database establishes a baseline and requires operator review; recovery never
automatically resets the kill switch. Unknown orders, changed holdings/order
statuses, external open orders, account inconsistencies, broker outages, and
database failures also block readiness and require investigation. A closed
market or an unapproved risk file blocks order evaluation without placing an
order. Re-running after review and an explicit kill-switch reset can clear a
transient readiness condition, but the recovery module itself cannot enable
paper submission.

The report's `can_resume_order_evaluation` means the startup state checks
passed at that moment. It is not an instruction to trade. The Phase 12 order
manager still has its separate disabled-by-default submission flag and reruns
fresh checks before any paper order. Recovery uses at most 100 broker order-ID
lookups per run; a larger unfinished inventory blocks until reviewed. Order
status and cumulative fills are available, but individual execution fills and
realized P&L still require a broker activity ledger. The 17 offline Phase 13
tests cover clean and blocked startup, order reconciliation, database and broker
failures, accounting, market clock, and recovery after operator reset. Run them
with `python -m unittest tests.test_recovery -v`. Raspberry Pi validation
remains to be done.

## Cross-platform operation

Develop and test on Windows, commit the reviewed repository, and pull it onto
the Raspberry Pi. Install dependencies and configure a separate `.env` on the
Pi. Do not copy the Windows `.venv` or local database to the Pi.

The automated tests have been run on Windows. Run the same test command on the
Pi before deployment; Pi validation has not yet been performed.

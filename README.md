# AI-Enhanced Alpaca Trading Bot

An incremental, paper-only US-equities trading-system project. The detailed
roadmap is in `AI_Enhanced_Alpaca_Trading_Bot_Development_Plan_For_Coding_AI.md`.

For decisions that only the project owner can make, use the
[phase-by-phase responsibilities checklist](docs/owner_responsibilities.md).
The [proposed research program](docs/proposed_research_program.md) describes
the planned rule/ML and timeframe comparisons before a paper trial.
The [Study A record](docs/study_a_research_record.md) contains the first
15-minute rule-only data audit and exploratory results.
The [Study C record](docs/study_c_research_record.md) contains the daily
12-symbol screen and continuous shared-cash portfolio follow-up.
The [Study C feed audit](docs/study_c_feed_audit.md) compares SIP and IEX
coverage, JNJ volume warnings, and a matched 2023-only research replay.
The [Study C-R2 results](docs/study_c_daily_improvement_results.md) evaluate
five fixed daily-rule arms and 86 simulations under a
[registered improvement protocol](docs/study_c_daily_improvements.md).
Slower breakout rules improved returns but failed the complete selection
and development checks; no paper candidate has been approved.
The [five-strategy guide](docs/five_daily_strategies_explained.md) explains
the entry/exit rules and the fixed versus trailing breakout stops.
The [Study C-R3 allocation results](docs/study_c_allocation_results.md)
compare six sizing/halt policies. Smaller volatility-based sizing passed
the allocation screen with lower gains and losses; broader strategy
validation and paper approval remain outstanding.
The [Study C-R4 earlier-history results](docs/study_c_earlier_history_results.md)
audit 2016-2018 data and evaluate the frozen smaller breakout allocation on
2017-2018 and continuously over 2017-2023. All ten additional-history checks
passed; pessimistic seven-year return was +16.392% with -4.584% closing
drawdown. This backward check does not clear the earlier strategy weaknesses
or approve paper trading. 2024-2025 remain reserved.
The [investment acceptance plan](docs/investment_acceptance_proposal.md)
records the owner's return objective and $500-on-$10,000 loss concern.
The owner approved its 6% annual / 5% drawdown research criteria and the
[development-only goal-fit audit](docs/study_c_goal_fit_protocol.md).
Research approval does not approve paper-order risk settings or final testing.
The [completed goal-fit audit](docs/study_c_goal_fit_results.md) ran twelve
unchanged-strategy replays. The $10,000 account earned about 1.36% annually
over 2017-2023 after pessimistic costs and estimated final exits, failing the
6% hurdle. The candidate remains a reference; 2024-2025 stay reserved.
The [holding-time study results](docs/holding_period_study_results.md)
cover 36 simulations under the owner's amended rule: continuation beyond
session 60 is allowed, with later reviews every 30 sessions. Neither new
arm meets the investment criteria. The [universe guide](docs/stock_universe_research.md)
explains why a larger stock search needs matched historical validation before
paper trading. 2024-2025 remain reserved.
The [broad-universe feasibility audit](docs/broad_universe_audit_results.md)
snapshotted 33,560 asset records and probed 56 historical histories. Broader
daily data is accessible, but historical membership, identities and terminal
outcomes remain unresolved. The [eight-arm entry/selection study](docs/broad_entry_selection_study.md)
is scoped and awaits those inputs and dynamic-universe support; it has not
produced new return results. Run the read-only auditor with
`python -m backtesting.universe_audit --output data/reports/a_fresh_directory`.
The [free-data/lifecycle update](docs/free_data_and_lifecycle_progress.md)
records a $0 new-purchase policy, four successful company-event access checks
and ten review candidates. Optional [historical-universe mode](docs/historical_universe_format.md)
adds dated IPO/ticker lifetimes and verified terminal cash events. Focused
tests and [corporate-action accounting](docs/corporate_action_progress.md)
cover splits and ordinary dividends, with 36 exact prior financial replays.
The [raw-price pilot and historical-basket update](docs/raw_action_pilot_and_historical_baskets.md)
adds an offline accounting pilot using historical AAPL data, action-aware risk reconciliation,
36 exact legacy daily-envelope comparisons, and public 2016/2020 holdings
registers with 506/505 security rows. Historical ticker/identity, action and
price coverage must still be audited before broader strategy scoring; fixed
fund holdings are not a daily all-US-stock universe. Optional ML tests still
require `scikit-learn`; installation instructions are in the update.
The [2016 cohort mapping/data audit](docs/cohort_2016_audit_results.md) now
identifies all 506 dated ticker aliases and records ten sourced event cases.
It checked 33 saved daily-price files: none provides complete raw history for
the broader basket. The audit is offline, uses no credentials and submits no
orders. Source acquisition used free public downloads; new purchases and new
broker/account requests were zero. Historical simulation dollar amounts,
including the earlier $9.69 dividend example, are not charges or account money.
The [free collection/event review](docs/free_collection_results.md) has now
collected 23,748 raw daily observations across representative ticker periods,
including one recovered vendor-label boundary candle, and inventoried 249
provider events. Reviewed Under Armour/CBRE alias streams retain actual OHLCV.
Ten independently required events are absent from the queried action responses;
terminal claims, share distributions/mergers and OTC valuation remain blockers
before broader strategy scoring. Collection used 46 historical-data GETs under
existing access, with $0 in purchases, no subscription changes and no orders.
The [ownership-claim ledger and saved-case checks](docs/claim_accounting.md)
now cover delayed cash rights, cash/share mergers, spin-off branches and exact
fractional claims. It separates spendable cash from receivables and includes
claim-aware equity/risk bounds. That standalone component was checked offline;
historical timing/price evidence still needs review. Its checks made no
network requests, purchases or orders.
The subsequent [ownership adapter](docs/ownership_adapter.md) now connects
that ledger to the portfolio engine through an explicit reviewed schedule,
with inherited stops/orders, feature resets, claims and report reconciliation.
The [integration verification and evidence review](docs/ownership_verification_results.md)
passed 183 focused tests, 36 exact financial replays, 36 exact risk replays
and 84 component checks. Report-summary corruption checks were strengthened.
Twenty saved primary sources were revalidated; historical delivery/payment
and price gaps still block the broader study. No incomplete source case has
been promoted or larger strategy study run.
The [free-data pilot proposal](docs/free_data_pilot_proposal.md) specifies
AAPL, JPM and CBRE plus SPY context for cached-data qualification over
2016-2023. It separates proposed timing assumptions from verified facts;
it schedules no performance runs and does not replace the broader universe.
The [completed cached-source qualification](docs/free_data_pilot_qualification.md)
reconstructs and validates all 8,048 candles, reviews 95 action-matrix rows,
and separates six supported event cross-checks from remaining evidence gaps.
Forty-eight provider dividend rows omit payable dates; full-period identity/
action completeness remains blocked. A finite free primary-source collection
list is prepared; no new strategy return has been calculated.
The [bounded public-source collection](docs/pilot_public_source_results.md)
saved 11 files and reconciles 32 Apple declarations, 32 SPY distributions and
two JPMorgan releases. It confirms three SPY events omitted by the provider;
reviewed issuer terms supply 32 of the original 48 absent payable fields.
Collection stopped at the JPMorgan history host's HTTP 403, within the
request limits. Sixteen payable gaps and other readiness checks remain;
no purchases, orders or strategy performance runs occurred.
The [paper-readiness checklist](docs/paper_trading_readiness.md) explains the
remaining data, strategy, execution and owner-activation gates.
The [Study C-P1 record](docs/study_c_protective_exit_variant.md) evaluates
one fixed ATR protective-exit variant against that baseline.
Before approving paper-order risk settings, use the
[risk-limit decision workbook](docs/risk_limit_decision_workbook.md).

## Current progress

The repository includes centralized paper-only Alpaca access, validated
market data, SQLite persistence, technical features, deterministic and
offline ML research, single-symbol backtesting and walk-forward evaluation,
offline shared-cash daily portfolio research, a standalone risk gate, and
read-only portfolio reconciliation. The shared-cash simulator implements
configurable research entry/loss limits and an optional daily-OHLC stop
proxy; it does not implement live broker stops or the complete paper policy.

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

## Shared-cash daily portfolio research

After downloading and validating daily datasets, run the offline
`backtesting.portfolio_research` command with all desired CSV paths. It
requires matching session timestamps and the same feed, adjustment, and
date range. It uses one cash balance, keeps positions across year boundaries,
and records every simulated fill and equity mark. The command never calls a
broker order endpoint. The [Study C record](docs/study_c_research_record.md)
has the exact 12-symbol reproduction command and results.

Entry limits are configurable with `--max-portfolio-exposure`,
`--max-single-position`, `--max-positions`, `--max-daily-loss`, and
`--max-drawdown`; defaults are provisional research values, not paper
approval. A BUY quantity is planned from the completed signal close and can
only shrink at the next open. Loss limits halt new entries but do not force
liquidation. The optional `--protective-atr-multiple 2` variant adds a
daily-bar stop proxy and `--max-risk-per-trade 0.01` planned-risk sizing;
`--stop-extra-slippage-bps 50` stresses the stop fill. A daily low touching
the stop is modeled at the stop level with adverse costs, while an opening
gap below it exits at the open. These are approximations, not live stop
orders or guaranteed fills. The [P1 record](docs/study_c_protective_exit_variant.md)
shows that this particular stop variant failed its predeclared development
screen. CSV and JSON outputs remain in ignored `data/` on the machine where
the command runs.

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

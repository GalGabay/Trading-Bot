# AI-Enhanced Alpaca Trading Bot — Coding AI Handoff

> **Purpose of this file:** This document is the authoritative development plan and handoff specification for a coding AI (Codex or another coding agent) that will implement this project.
>
> **How to use it:** Give this entire Markdown file to the coding AI together with the repository. The coding AI should treat the requirements below as the project specification, but should implement the project **incrementally**, validating each milestone before moving to the next.
>
> **Important:** Do not attempt to implement the entire roadmap in one step. Start with the earliest incomplete milestone, inspect the existing repository first, implement only the necessary scope, run tests, and report what was changed and what remains.
>
> **Initial trading environment:** Alpaca **Paper Trading only**. No live trading should be enabled as part of the initial implementation.
>
> **Safety:** This is a software-engineering and quantitative-research project. Backtests and paper-trading results do not guarantee profitability. The implementation must prioritize correctness, reproducibility, observability, secure credential handling, graceful failure, state recovery, and hard risk controls.

## Instructions to the Coding AI

1. **Inspect before modifying.**
   - Read the repository structure, existing source code, configuration, tests, README, and dependency files before making architectural decisions.
   - Reuse working code where appropriate rather than unnecessarily rewriting it.
   - Identify conflicts between the existing repository and this plan before proceeding.

2. **Implement incrementally.**
   - Work milestone-by-milestone.
   - Do not add machine learning before the deterministic trading pipeline and backtester are working.
   - Do not add live trading.
   - Do not add unnecessary infrastructure or dependencies prematurely.

3. **Keep the architecture modular.**
   - Separate data ingestion, storage, feature engineering, strategies, AI/ML, portfolio management, risk management, order management, broker integration, monitoring, and deployment.
   - Avoid business logic being hidden inside API clients, scripts, or UI code.

4. **Make trading decisions reproducible.**
   - Persist signals, relevant feature values, model versions, risk decisions, orders, fills, and important system events.
   - Every trade should be explainable after the fact.

5. **Treat failure handling as a first-class requirement.**
   - Design for API failures, network failures, process crashes, Raspberry Pi reboots, stale/invalid data, duplicate order submissions, partial fills, and state reconciliation.
   - Never blindly retry an order when its previous submission status is unknown.

6. **Protect credentials and prevent accidental live trading.**
   - Never hardcode API keys.
   - Never commit `.env`.
   - Keep paper and live configuration separate.
   - The default configuration must remain paper-only.
   - If a live-trading path is ever added later, it must require explicit safeguards and must not be enabled by accident.

7. **Test every important component.**
   - Add unit tests for deterministic logic.
   - Add integration tests around broker/database boundaries where practical.
   - Add failure/recovery tests for critical execution paths.
   - Do not declare a milestone complete merely because the code runs once.

8. **Do not optimize for impressive backtests.**
   - Avoid look-ahead bias, survivorship bias, leakage, unrealistic fills, and overfitting.
   - Use time-aware validation.
   - Compare AI-enhanced performance against the non-AI baseline out of sample.

9. **Raspberry Pi constraint.**
   - The Raspberry Pi 3B is an execution/monitoring target, not a heavy training machine.
   - Keep inference and runtime resource usage lightweight.
   - Heavy backtesting, model training, and hyperparameter searches should run on a development PC or other suitable machine.

10. **Cross-platform development and runtime.**
   - The primary development environment is the user's Windows computer with VS Code. The bot must also be able to run on the Raspberry Pi 3B from the same GitHub repository.
   - Keep application code portable across Windows and Raspberry Pi OS/Linux. Avoid OS-specific paths, shell assumptions, and dependencies unless isolated behind a documented platform-specific layer.
   - Use the same Python version range and pinned/locked project dependencies on both systems where package support allows. Document any architecture-specific installation steps for the Pi.
   - Keep machine-specific settings, credentials, databases, logs, downloaded data, virtual environments, and generated model artifacts out of Git unless a specific artifact is intentionally versioned. Provide safe examples/templates for configuration.
   - Support local development and paper-mode execution on Windows as well as deployment on the Pi. The Pi is the intended always-on runtime, not the only machine on which the program can start.
   - Validate portability before deployment: run the automated checks on Windows and on the Pi (or a representative Linux environment), and document any differences.

11. **When a requirement is ambiguous, do not silently invent a major design decision.**
    - Prefer a small, reversible implementation.
    - Clearly state assumptions.
    - Ask for clarification when the decision materially affects architecture, money, safety, or data integrity.

## Expected Coding-Agent Workflow

For each milestone:

```text
1. Inspect current repository
2. Identify the exact milestone scope
3. Explain the implementation approach briefly
4. Implement the smallest complete increment
5. Add/update tests
6. Run tests / lint / type checks as applicable
7. Inspect the resulting diff
8. Verify no secrets or live-trading configuration were introduced
9. Summarize:
   - files changed
   - behavior added
   - tests run/results
   - known limitations
   - next milestone
```

### Definition of Done

A milestone is complete only when:

- The requested functionality exists.
- The architecture remains consistent with this document.
- Relevant tests exist and pass.
- Failure cases have been considered.
- Configuration and secrets are handled safely.
- The implementation is documented enough for the next development step.
- Nothing silently enables live trading.

---

# AI-Enhanced Algorithmic Trading Bot
## Detailed Development Plan for Raspberry Pi 3B + Alpaca Paper Trading

> **Goal:** Build a robust, modular, continuously running algorithmic trading system using Python, Alpaca's Trading API, a Raspberry Pi 3B, historical market data, backtesting, risk management, and eventually machine learning/AI.
>
> **Initial mode:** Alpaca Paper Trading only.
>
> **Important:** This project is for software engineering and quantitative research. A backtest or paper-trading result does not guarantee live profitability. The system must be designed to fail safely.

---

# 1. Project Vision

The goal is **not** to create a simple script such as:

```python
if signal == "BUY":
    buy_stock()
```

The goal is to build a small, production-style trading platform with clear separation between:

1. Market data
2. Data storage
3. Feature engineering
4. Trading strategies
5. Machine learning
6. Portfolio management
7. Risk management
8. Order execution
9. State recovery
10. Monitoring
11. Backtesting
12. Paper trading
13. Deployment

The target architecture is:

```text
                         ┌──────────────────────────┐
                         │        Alpaca API        │
                         │                          │
                         │ Market Data + Trading    │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │       Data Layer         │
                         │                          │
                         │ Historical / Real-time   │
                         │ OHLCV / Quotes / Volume  │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │   Feature Engineering    │
                         │                          │
                         │ Indicators / Returns     │
                         │ Volatility / Market Data │
                         └────────────┬─────────────┘
                                      │
                       ┌──────────────┴──────────────┐
                       ▼                             ▼
              ┌──────────────────┐          ┌──────────────────┐
              │ Trading Strategy │          │    ML / AI       │
              │                  │          │                  │
              │ Rules / Signals  │          │ Probability      │
              └────────┬─────────┘          └────────┬─────────┘
                       │                             │
                       └──────────────┬──────────────┘
                                      ▼
                         ┌──────────────────────────┐
                         │    Portfolio / Risk      │
                         │        Manager           │
                         │                          │
                         │ Position sizing           │
                         │ Exposure limits           │
                         │ Loss limits               │
                         │ Kill switch               │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │      Order Manager       │
                         │                          │
                         │ Construct / submit       │
                         │ Track / reconcile        │
                         │ Investigate / recover    │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                             ┌────────────────┐
                             │ Alpaca Paper   │
                             │ Trading        │
                             └────────────────┘
```

---

# 2. Core Design Principles

## 2.1 Build the deterministic system first

Do not start with AI.

First create:

```text
Market Data
    ↓
Indicators
    ↓
Rule-Based Strategy
    ↓
Risk Management
    ↓
Order Management
    ↓
Paper Trading
```

Only after this system is reliable should machine learning be introduced.

---

## 2.2 AI should be a component, not the entire strategy

Avoid:

```text
AI → BUY / SELL
```

Prefer:

```text
Strategy → Candidate Trade
                 ↓
             AI Model
                 ↓
        Confidence / Expected Return
                 ↓
          Risk Management
                 ↓
              Order
```

The AI model should ideally provide an additional signal such as:

- probability of positive return
- expected return
- probability of reaching a target
- probability of significant downside
- market regime classification

The system should still have hard risk limits that the AI cannot override.

---

## 2.3 Research and production should be separated

The development computer should perform:

- data analysis
- backtesting
- model training
- hyperparameter tuning
- visualization
- experimentation

The Raspberry Pi should perform:

- market data retrieval
- strategy execution
- ML inference
- risk checks
- order execution
- state persistence
- monitoring

This keeps the Raspberry Pi 3B's limited CPU/RAM usage under control.

---

# 3. Target Hardware

## Raspberry Pi 3 Model B

Target role:

```text
24/7 trading execution server
```

Expected responsibilities:

- Python runtime
- Alpaca API communication
- SQLite database
- strategy execution
- ML inference
- logging
- FastAPI dashboard
- systemd service

The Raspberry Pi 3B has limited RAM, so it should **not** be used for heavy neural-network training or large-scale hyperparameter searches.

A lightweight model such as XGBoost, LightGBM, logistic regression, random forest, or another compact model can be trained elsewhere and deployed for inference.

---

# 4. Recommended Technology Stack

## Core

- Python 3
- Alpaca Python SDK (`alpaca-py`)
- pandas
- NumPy
- SQLite
- SQLAlchemy (optional)
- python-dotenv
- PyYAML

## Technical analysis

Possible choices:

- pandas-based custom indicators
- `pandas-ta`
- TA-Lib

Use a small number of well-understood indicators initially.

## Machine Learning

Recommended starting point:

- scikit-learn
- XGBoost

Possible later additions:

- LightGBM
- PyTorch
- specialized time-series models

Do not jump directly to deep learning.

## Backtesting

You can either:

1. Build a custom backtesting engine for maximum control, or
2. Use a framework such as Backtrader/vectorbt for research.

For learning and long-term maintainability, a custom lightweight engine is valuable even if a research framework is also used.

## Server

- Ubuntu on Raspberry Pi
- systemd
- Git
- SSH

## Monitoring

- FastAPI
- Jinja2
- HTMX
- SQLite
- optional browser dashboard
- optional Telegram/email alerts later

---

# 5. Repository Structure

A recommended structure:

```text
trading-bot/
│
├── app/
│   ├── main.py
│   │
│   ├── broker/
│   │   ├── alpaca_client.py
│   │   ├── account.py
│   │   └── orders.py
│   │
│   ├── data/
│   │   ├── market_data.py
│   │   ├── historical.py
│   │   ├── realtime.py
│   │   └── database.py
│   │
│   ├── strategy/
│   │   ├── base.py
│   │   ├── indicators.py
│   │   └── strategy_v1.py
│   │
│   ├── risk/
│   │   ├── position_sizing.py
│   │   └── risk_manager.py
│   │
│   ├── portfolio/
│   │   └── portfolio_manager.py
│   │
│   ├── ai/
│   │   ├── features.py
│   │   ├── train.py
│   │   ├── model.py
│   │   └── predictor.py
│   │
│   ├── monitoring/
│   │   ├── logger.py
│   │   └── health.py
│   │
│   └── config.py
│
├── backtesting/
│   ├── engine.py
│   ├── metrics.py
│   └── reports.py
│
├── models/
│
├── data/
│
├── tests/
│
├── scripts/
│
├── config/
│   └── config.yaml
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

# 6. Phase 0 — Define the Trading Scope

Before writing code, define the first version.

Recommended first scope:

```text
Asset class:        US equities
Broker:             Alpaca
Mode:               Paper trading
Timeframe:          15-minute or 1-hour
Frequency:          Low/medium frequency
Symbols:            Small predefined universe
Execution:          Market/limit orders as appropriate
Database:           SQLite
Server:             Raspberry Pi 3B
AI:                 Not in V1
```

Do not start with:

- options
- leveraged products
- high-frequency trading
- tick-level strategies
- dozens of data providers
- large neural networks

Keep V1 understandable.

---

# 7. Phase 1 — Create Alpaca Paper Account

Create an Alpaca account and enable Paper Trading.

Keep Paper Trading credentials separate from live credentials.

Use environment variables:

```text
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
ALPACA_PAPER=true
```

Never commit credentials to Git.

`.gitignore` should contain:

```text
.env
.venv/
__pycache__/
*.pyc
models/
data/
```

Create:

```text
.env.example
```

containing only placeholders:

```text
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
ALPACA_PAPER=true
```

---

# 8. Phase 2 — Set Up Python

Develop first on the Windows PC in VS Code, and create a separate virtual environment on each computer. Virtual environments are machine-specific and must not be committed or copied between Windows and the Pi. Use a Python version supported by both Windows and Raspberry Pi OS; record the chosen version in the README and use a dependency lock or pinned requirements so both environments can be reproduced.

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If PowerShell blocks activation, use the VS Code Python interpreter selector to choose `.venv\Scripts\python.exe`, or run the commands from Command Prompt instead:

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
```

On Raspberry Pi OS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install the initial dependencies from the repository's dependency file once it exists (prefer pinned versions that are supported on both platforms). During the initial bootstrap, the package set may be installed with:

```bash
python -m pip install alpaca-py pandas numpy python-dotenv pyyaml
```

Later:

```bash
python -m pip install scikit-learn xgboost
```

Do not use `pip freeze` from one developer's environment as an unreviewed cross-platform lockfile; it may capture unrelated or platform-specific packages. Maintain the project's direct dependency specification intentionally, resolve a reproducible set, and verify installation on both Windows and the Pi. Keep `.venv/` ignored by Git.

The bot must be able to start in paper/safe mode on either platform. Run the same relevant tests and smoke checks on Windows during development and on Raspberry Pi OS before deployment. Machine-specific secrets and runtime data must be configured separately on each machine and must never be copied into the repository.

---

# 9. Phase 3 — Build the Alpaca Client

Create one central Alpaca client.

Do not allow every module in the project to construct its own API client.

Conceptually:

```text
app/broker/alpaca_client.py
```

Responsibilities:

- authenticate
- create trading client
- create historical data client
- create real-time data client
- expose controlled methods to the rest of the application

For this repository, implement the client in `app/broker/alpaca_client.py`. Load credentials from environment variables or the repository-root `.env` file, and never print or log them. The initial implementation must force `paper=True` and reject a configuration that asks for live trading. Support running on Windows and Raspberry Pi OS; keep the SDK client construction centralized here. Track direct dependencies in `requirements.txt` rather than generating it from an arbitrary local `pip freeze`.

Example conceptual interface:

```python
class AlpacaClient:
    def get_account(self):
        ...

    def get_positions(self):
        ...

    def get_orders(self):
        ...

    def submit_order(self, order):
        ...

    def cancel_order(self, order_id):
        ...

    def get_market_data(self, symbol, ...):
        ...
```

This abstraction makes the rest of the application independent of the broker implementation.

---

# 10. Phase 4 — Market Data Layer

The market-data layer should be responsible for obtaining and validating data.

It should support:

## Historical data

Used for:

- backtesting
- feature creation
- ML training

## Live/recent data

Used for:

- generating current signals
- monitoring positions
- executing trades

Initial candle format:

```text
timestamp
symbol
open
high
low
close
volume
```

Additional data can be added later:

- trades
- quotes
- bid/ask
- spreads
- news
- corporate actions

For the initial implementation, use `app/data/market_data.py` to fetch one symbol's historical bars through the central `AlpacaClient`. Normalize every successful response to a pandas table with exactly `timestamp`, `symbol`, `open`, `high`, `low`, `close`, and `volume`, with UTC timestamps and uppercase symbols. Validate the table before it reaches any strategy, backtest, or storage code. Return non-fatal data-quality observations (such as zero-volume candles and large gaps) separately from hard validation failures; valid market holidays and session breaks must not be treated as corrupted data without a market calendar. The real-time stream remains owned by the central broker client and is exposed for a later subscriber implementation.

---

# 11. Data Validation

Never assume market data is perfect.

Check:

- timestamps
- missing candles
- duplicated candles
- impossible OHLC values
- zero/negative prices
- volume anomalies
- timezone consistency
- market holidays
- trading session boundaries

For example:

```text
High >= max(Open, Close, Low)
Low <= min(Open, Close, High)
Volume >= 0
```

Bad data can create fake backtest performance.

### Initial validation policy

The initial implementation is for regular-session US equities. Candle timestamps must include an explicit timezone offset; internally they are normalized to UTC. `app/data/market_calendar.py` obtains scheduled sessions from Alpaca's calendar endpoint, so weekends, market holidays, early closes, and normal session boundaries are not guessed from a weekday-only rule. Alpaca intraday bars are clock-aligned (an hourly bar can start at 09:00 ET and overlap the 09:30 ET opening); daily bars are timestamped at midnight New York time. The validator uses those conventions when determining the expected candles. Use 15-minute bars for the first regular-session research run to avoid the mixed premarket/opening hourly bar.

A candle outside the selected regular-session bar timestamps is a hard validation error. An unobserved scheduled interval is a warning by default because Alpaca can omit bars when no qualifying trades occur; strict completeness can be requested explicitly. The historical research downloader stops when such intervals appear so they can be investigated. No gap is filled or fabricated. Structural problems (invalid/missing timestamp, duplicate symbol/timestamp, missing, non-numeric, or infinite OHLCV, non-positive prices, invalid OHLC, and negative volume) are hard errors.

Zero volume and unusual positive volume are warnings. The initial anomaly threshold is configurable and defaults to more than ten times the symbol's positive median volume. This does not automatically reject a candle because legitimate high-volume events exist; strategies and monitoring can decide how to respond later.

---

# 12. Phase 5 — SQLite Database

SQLite is appropriate for the initial system.

Suggested tables:

```text
candles
features
signals
orders
fills
positions
portfolio_snapshots
strategy_runs
model_predictions
system_events
```

## candles

```text
id
timestamp
symbol
open
high
low
close
volume
timeframe
```

## signals

```text
id
timestamp
symbol
strategy
signal
score
reason
```

## orders

```text
id
client_order_id
timestamp
symbol
side
quantity
order_type
status
alpaca_order_id
```

## fills

```text
id
order_id
timestamp
symbol
quantity
price
```

## model_predictions

```text
id
timestamp
symbol
model_version
prediction
confidence
```

The database should allow the entire trading decision history to be reconstructed later.

### Initial SQLite implementation

Use `app/data/database.py` with a local database path of `data/trading_bot.sqlite3` by default. The database file is machine-specific and must remain outside Git. Schema initialization is idempotent and records its schema version. The initial schema creates the tables listed above, while the initial repository API writes and reads candles only; later phases add repository methods for orders, fills, signals, features, and events when those modules exist.

Store timestamps as canonical UTC ISO-8601 text. Candles are uniquely identified by timestamp, symbol, and timeframe. Candle upserts must be parameterized and atomic: a corrected source candle may update the same identity, but a batch containing invalid data must not partially write. Calendar-aware validation happens in the market-data service before persistence; the database repeats structural validation as a defensive check and never fills or fabricates missing values.

---

# 13. Phase 6 — Feature Engineering

Start with raw market data:

```text
Open
High
Low
Close
Volume
```

Generate features.

## Trend

```text
EMA20
EMA50
EMA200
MACD
ADX
```

## Momentum

```text
RSI
ROC
Stochastic
```

## Volatility

```text
ATR
Bollinger Bands
Historical Volatility
```

## Volume

```text
Volume
Volume SMA
Volume Ratio
OBV
```

## Returns

```text
return_1
return_5
return_20
```

## Relative position

```text
distance_from_ema20
distance_from_ema50
distance_from_ema200
```

Avoid creating hundreds of correlated indicators simply because they are available.

The feature set should be explainable and tested.

### Initial feature implementation

Implement the initial feature set in `app/ai/features.py` as `technical_v1`: EMA20/50/200, MACD and signal/histogram, ADX14, RSI14, ROC10, stochastic %K14, ATR14, Bollinger Bands20, 20-period historical volatility, volume SMA20 and ratio, OBV, returns over 1/5/20 bars, and relative distance from each EMA. Calculate independently for each symbol in timestamp order. Do not backfill indicator warm-up values: unavailable history stays `NaN` and must be excluded or handled deliberately by later strategies/models.

Use only the current and earlier candles for every feature. Persist feature rows through the SQLite `features` table with their timeframe and feature version, storing only calculated values in the versioned payload. The initial historical-volatility annualization factor is configurable and defaults to 252 periods; set it appropriately when using intraday timeframes in a later configuration phase.

---

# 14. Phase 7 — First Rule-Based Strategy

Create a simple deterministic strategy.

Example:

```text
BUY when:

Price > EMA200
AND EMA20 > EMA50
AND RSI between 50 and 70
AND volume ratio > threshold
```

Exit could initially be based on:

- trend reversal
- stop loss
- take profit
- maximum holding time

This strategy is not expected to be "the best strategy."

Its purpose is to validate the architecture.

### Initial Strategy V1 implementation

Implement `app/strategy/strategy_v1.py` as `trend_following_v1`. It evaluates one symbol's latest completed feature row and proposes `BUY` only when close is above EMA200, EMA20 is above EMA50, RSI14 is between 50 and 70 inclusive, and volume ratio is strictly above 1.0. With an open position, close below EMA50 or EMA20 below EMA50 proposes `SELL`; otherwise it holds. Incomplete indicator warm-up data produces `HOLD`. It must state the reasons and must not submit orders or size positions. Thresholds are explicit configuration values and may be changed later through application configuration.

---

# 15. Strategy Interface

Create a generic interface so strategies can be swapped.

Conceptually:

```python
class Strategy:
    def generate_signal(self, market_data, portfolio):
        ...
```

Return something like:

```text
Signal:
    symbol
    action
    confidence
    reason
    timestamp
```

Possible actions:

```text
BUY
SELL
HOLD
```

Later:

```text
REDUCE
CLOSE
```

### Initial interface implementation

Implement the generic `Strategy` interface in `app/strategy/base.py`. `generate_signal(market_data, portfolio)` receives features for exactly one symbol and returns an immutable `Signal` containing symbol, action, confidence from 0 to 1, reason, timezone-aware timestamp, and strategy name. The initial strategy reads only whether a position is open to propose a simple trend-reversal exit. Position sizing, risk decisions, and order submission belong to later phases. This interface lets the backtester and future strategies use one stable contract without coupling a strategy to Alpaca or SQLite.

---

# 16. Phase 8 — Backtesting Engine

Before paper trading, implement a backtesting engine.

Architecture:

```text
Historical Data
      ↓
Feature Engineering
      ↓
Strategy
      ↓
Signal
      ↓
Risk Manager
      ↓
Simulated Order
      ↓
Simulated Fill
      ↓
Portfolio
      ↓
Metrics
```

The backtester should simulate:

- cash
- positions
- entries
- exits
- order sizes
- fees
- slippage
- portfolio equity
- drawdown

Do not assume every order fills at the exact close price.

### Initial backtesting implementation

Implement the initial engine in `backtesting/engine.py`. It backtests one symbol at a time using validated candles and causal features. At each candle close, the strategy sees only feature rows through that completed candle. A BUY or SELL signal becomes a pending market order and can only fill at the following candle's open. A signal on the final candle remains unfilled and is recorded as such; no price is fabricated.

The initial engine uses whole shares, tracks cash, one long position, simulated fills, fees, spread, slippage, equity, and drawdown. Its initial position-size constraint is 10% of current equity per entry. Cost assumptions are explicit scenario inputs: the default commission is zero, adverse slippage is 5 basis points, and quoted spread is 2 basis points (half charged on each side). These are research assumptions, not claims about broker pricing. The engine is intentionally single-symbol until portfolio management and risk management exist. An explicit trade window can include earlier candles for indicator warm-up without trading them.

The result is an immutable audit record containing every generated signal, simulated fill, equity point, and skipped/unfilled-order event. No part of the engine connects to Alpaca or submits an order.

---

# 17. Backtesting Metrics

At minimum calculate:

```text
Total Return
Annualized Return
CAGR
Maximum Drawdown
Sharpe Ratio
Sortino Ratio
Win Rate
Profit Factor
Average Trade
Number of Trades
Volatility
```

Also track:

```text
Largest Win
Largest Loss
Average Win
Average Loss
Average Holding Period
```

A strategy with high return but catastrophic drawdown may be unusable.

Implemented in `backtesting/metrics.py`. Portfolio returns and drawdown include an open position marked at the latest close; win rate, profit factor, and trade statistics include only completed buy/sell pairs net of fees and price costs. Undefined measures are returned as `None`. The intraday annualization factor is explicit: 6,552 periods for 15-minute bars, 1,764 for hourly bars, and 252 for daily bars in the initial runner. CAGR uses elapsed calendar time. These factors are approximations and short samples can make annualized figures unstable.

---

# 18. Avoid Look-Ahead Bias

This is critical.

At time `t`, the strategy must only use information that would have been available at time `t`.

Wrong:

```text
Use today's closing price
→
Assume we bought at today's close
```

if the signal itself requires the closing price that was not known until the close.

Instead, model execution realistically:

```text
Candle closes
    ↓
Signal generated
    ↓
Order submitted
    ↓
Next realistic execution
```

Look-ahead bias can make a terrible strategy look excellent.

Implemented guardrails: features are causal, only rows through the evaluated candle reach the strategy, signal symbol/timestamp must match that candle, and fills use the following bar's open. The research window uses older bars only for indicator warm-up. This does not replace a future walk-forward test or protect against repeated human tuning on the holdout years.

---

# 19. Avoid Survivorship Bias

Do not backtest only today's successful companies if the strategy is supposed to work on a historical universe.

For example, if a historical universe contains only companies that survived to 2026, the test may be overly optimistic.

A robust research system should eventually account for:

- delisted stocks
- changing index constituents
- corporate actions
- splits
- mergers

The current runner labels every report `single_symbol_case_study` and states that survivorship and universe-selection bias are unresolved. One currently known stock cannot prove a universe-level edge. A genuine universe test requires point-in-time constituent membership, delisted symbols, and corporate-action histories from a suitable historical source. Do not claim this bias is solved until those data and a multi-symbol portfolio backtester exist.

---

# 20. Transaction Costs and Slippage

Backtests should include realistic assumptions.

Model:

```text
commission/fees
spread
slippage
execution delay
```

Even if the broker has zero commission for a particular product, market impact and spread still matter.

Run multiple scenarios:

```text
Optimistic
Base
Pessimistic
```

A strategy that works only under optimistic assumptions is not robust.

Implemented in `backtesting/engine.py` and `backtesting/research.py`: adverse spread and slippage adjust the next-open fill on each side, commission is charged per fill, and optimistic/base/pessimistic scenarios rerun the same dataset. No historical bid/ask quotes, market-impact model, latency distribution, or partial-fill model exists yet; the configurable assumptions approximate those costs.

---

# 21. Phase 9 — Walk-Forward Validation

Do not optimize parameters on the entire dataset and then test on that same data.

Use a time-aware process:

```text
Train: 2018–2020
Test:  2021

Train: 2018–2021
Test:  2022

Train: 2018–2022
Test:  2023

Train: 2018–2023
Test:  2024
```

The exact years depend on the available dataset.

This provides a more realistic estimate of out-of-sample behavior.

### Initial Phase 9 implementation

`backtesting/walk_forward.py` runs expanding, full-calendar-year windows on a
checksum-verified single-symbol dataset. It evaluates the declared
`trend_following_v1` threshold grid on earlier years only, selects by base-cost
training total return plus maximum drawdown (subject to a minimum completed-trade
count), and evaluates the next year once under optimistic, base, and pessimistic
costs. Training results never choose settings for the same year's test. The
machine-readable report records every candidate, the selection rule and chosen
settings, each window, cost assumptions, metrics, and dataset provenance.

This is deterministic rule calibration, not ML model training. Years already
inspected as test results are no longer untouched holdouts. Each test year
starts with fresh cash; positions at its end are marked to market but are not
carried into the next fold. The current single-symbol data source still cannot
remove survivorship bias. Do not claim a market-wide edge from these results.

---

# 22. Phase 10 — Risk Management

Risk management is a first-class component.

It should be able to reject a trade.

Architecture:

```text
Strategy says BUY
       ↓
Risk Manager
       ↓
Allowed?
   ┌───┴───┐
   │       │
  YES      NO
   │       │
   ▼       ▼
Order     Reject
```

Potential limits:

```text
Maximum portfolio exposure
Maximum position size
Maximum risk per trade
Maximum number of positions
Maximum daily loss
Maximum drawdown
Maximum sector exposure
Maximum volatility exposure
```

Example initial policy:

```text
Max portfolio exposure = 70%
Max single position    = 10%
Max risk per trade     = 1%
Max daily loss         = 3%
```

These are examples, not universal recommendations.

The coding AI can implement and test the risk policy with clearly documented,
configurable defaults. Before connecting it to any paper-order workflow, ask
the project owner to choose or explicitly accept their preferred risk limits.

### Initial Phase 10 implementation

`app/risk/risk_manager.py` is a pure, long-only gate over a proposed whole-share
trade and a complete, recent portfolio snapshot. It returns structured approval
or rejection reasons and the exact limits used; it never sends orders. BUY
checks include available cash, gross exposure, single-position exposure,
number of positions, estimated loss to a required stop, daily loss, and
drawdown. A risk-reducing SELL may pass after a loss threshold, but cannot
exceed the current holding. Unknown, stale, duplicate, or inconsistent position
state is rejected. Sector and annualized-volatility checks are optional until
reliable metadata exists. The 70%/10%/1%/3% examples are provisional defaults;
10% maximum drawdown, seven positions, and five-minute snapshot and signal ages are also
provisional. A stop is an initial loss estimate, not a guarantee of execution
at that price. This module is not yet connected to backtesting or paper orders.
Focused offline unit tests cover approval, each configured gate, stale or
incomplete state, reducing exits, optional metadata, and exact loss-limit
boundaries. Loss and drawdown checks compare equity directly to threshold
levels so rounding cannot admit a trade at the configured ceiling.

---

# 23. Position Sizing

Do not simply invest the same dollar amount in every stock.

A basic risk-based model:

```text
Risk per trade
--------------------------
Stop distance
```

determines the approximate quantity.

Conceptually:

```text
position_size =
    allowed_risk / stop_distance
```

Then apply:

```text
max_position_size
max_portfolio_exposure
available_cash
```

The final size is the smallest amount permitted by all constraints.

### Initial implementation

`app/risk/position_sizing.py` calculates a whole-share BUY proposal from
planned stop loss per share, then applies the single-position, gross-exposure,
available-cash, and optional sector caps. It validates a one-share candidate
and the final quantity through `RiskManager`. No order is sent. A stop fill is
not guaranteed; the stop-distance risk is an estimate.

---

# 24. Kill Switch

Implement an emergency kill switch.

Examples:

```text
Too many API failures
Unexpected account state
Database corruption
Excessive daily loss
Excessive drawdown
Model unavailable
Data quality failure
Duplicate order detection failure
```

When triggered:

```text
STOP NEW ORDERS
```

Optionally close positions only according to a separately designed emergency policy.

The default behavior should be conservative.

### Initial implementation

`app/risk/kill_switch.py` stores a latched emergency stop in its own SQLite
file. Missing or unreadable state denies new orders. It can trip on an API
failure streak, invalid reconciled account state, daily loss, drawdown, or an
explicit event such as data-quality failure, model unavailability, database
corruption, or duplicate-order detection failure. Only an explicit operator
reset with a note clears it. It never liquidates positions. Phase 12 must
check the latch immediately before every paper order; there is no order
submission workflow yet.

---

# 25. Phase 11 — Portfolio Manager

The portfolio manager maintains the application's understanding of:

- cash
- buying power
- positions
- exposure
- realized P&L
- unrealized P&L
- portfolio equity

Important:

Do not rely only on local state.

Periodically reconcile local state with Alpaca.

```text
Local DB
   +
Alpaca account/positions/orders
   ↓
Reconciliation
   ↓
Correct local state
```

### Initial Phase 11 implementation

`app/portfolio/portfolio_manager.py` captures the Alpaca paper account, open
positions, and open orders without sending orders. It normalizes decimal values,
calculates gross/net exposure and unrealized P&L, and reports changes from the
previous broker snapshot. `TradingDatabase.record_portfolio_state` writes the
snapshot and position history in one SQLite transaction and replaces separate
materialized `broker_current_positions` and `broker_open_orders` tables with
the broker's latest complete state. A failed fetch, invalid response, or response at Alpaca's 500-order
limit leaves local state untouched. The command
`python -m app.portfolio.portfolio_manager` runs one reconciliation; schedule
it periodically when the runtime service is designed.

Realized P&L remains explicitly unknown because current account/position
responses cannot reconstruct closed-trade profit after fills, fees, transfers,
and corporate actions. Do not substitute change in equity or unrealized P&L
for realized P&L. A complete broker activity/fill ledger is needed later.
The capture uses sequential API calls and can observe a fill between them;
an accounting-gap flag helps identify those temporary inconsistencies. The
Phase 10 risk gate is not connected to order submission, and no snapshot is
automatically certified as complete for risk checks.

---

# 26. Phase 12 — Order Manager

The order manager should be the only component responsible for submitting orders.

Flow:

```text
Signal
  ↓
Risk Check
  ↓
Portfolio Check
  ↓
Market Hours Check
  ↓
Buying Power Check
  ↓
Create Order
  ↓
Submit to Alpaca
  ↓
Track Order
  ↓
Handle Fill / Reject / Cancel
  ↓
Persist Result
```

Handle failures such as:

- API timeout
- network failure
- rejected order
- partial fill
- duplicate request
- insufficient buying power
- market closed
- stale data

---

# 27. Idempotency and Duplicate Orders

This is critical.

Suppose:

```text
BUY AAPL
```

is submitted successfully, but the network connection dies before the response reaches the bot.

The bot restarts and must **not automatically send another BUY**.

Use a unique client order ID and reconcile with the broker before retrying.

Conceptually:

```text
Generate client_order_id
        ↓
Submit
        ↓
Timeout?
        ↓
Query Alpaca
        ↓
Does order exist?
    ┌───┴────┐
   YES       NO / UNKNOWN
   │          │
 Track      Stop and investigate
```

---

# 28. Phase 13 — State Recovery

The bot must survive:

- power loss
- reboot
- Python crash
- network outage
- API outage

Startup sequence:

```text
Boot
 ↓
Load configuration
 ↓
Open database
 ↓
Validate database
 ↓
Connect to Alpaca
 ↓
Retrieve account
 ↓
Retrieve open positions
 ↓
Retrieve open orders
 ↓
Reconcile with local DB
 ↓
Check market state
 ↓
Resume
```

Never assume that the previous process ended cleanly.

Current Phase 13 implementation: `python -m app.recovery.state_recovery`
validates the local SQLite file before connecting to the paper broker, looks
up every locally unfinished order by its stable client ID (up to a bounded
limit), reconciles account positions and open orders, checks the market clock,
and writes a structured startup report. It is read-only at the broker and
never resets the kill switch or enables order submission. A missing baseline,
unresolved order, changed holdings/order status, external open order, or
inconsistent account state blocks readiness and requires operator review.
Seventeen focused Phase 13 failure/recovery tests use a fake broker and temporary
SQLite files; they make no broker order calls. Run with
`python -m unittest tests.test_recovery -v`.

---

# 29. Phase 14 — Machine Learning

Only after the deterministic strategy and backtester work.

Current implementation: `app/ai/ml_dataset.py`, `app/ai/ml_model.py`, and
`backtesting/ml_research.py` form an offline, single-symbol research workflow.
The deterministic strategy, feature builder, and backtester exist, but the
observed AAPL results are cost-sensitive and do not establish an edge. The
model is not connected to paper-order submission. The command requires
explicit chronological train, tune, calibration, and test boundaries; it
purges labels crossing each boundary, records data/model provenance, and
compares the unchanged rule strategy with an ML-filtered version under the
same backtest costs. The optional dependencies are in `requirements-ml.txt`.
No reviewed model has been trained or deployed yet.

Start with supervised learning.

The model could predict:

```text
P(return > +2% within N bars)
```

or:

```text
Expected return over next N bars
```

or:

```text
Probability of positive return
```

---

# 30. ML Dataset

Each training row might look like:

```text
timestamp
symbol

rsi
ema20_distance
ema50_distance
ema200_distance
atr
volatility
volume_ratio

return_1
return_5
return_20

market_return
sector_return

target
```

Example target:

```text
target = 1
```

if the stock returns more than +2% over the next five trading days.

Otherwise:

```text
target = 0
```

The target definition must be created carefully to avoid leaking future information into features.

---

# 31. Recommended First ML Model

Start with:

```text
XGBoost
```

or:

```text
LightGBM
```

Why?

- strong on tabular data
- relatively lightweight
- fast inference
- handles nonlinear relationships
- easier to inspect than many deep-learning architectures

Do not assume a neural network is automatically better.

---

# 32. ML Training Pipeline

Architecture:

```text
Historical Data
       ↓
Feature Engineering
       ↓
Target Construction
       ↓
Time-Based Split
       ↓
Training
       ↓
Validation
       ↓
Hyperparameter Selection
       ↓
Out-of-Sample Test
       ↓
Model Version
       ↓
Deploy to Raspberry Pi
```

Save the model with version metadata:

```text
model_version
training_period
features
target_definition
hyperparameters
validation_metrics
creation_timestamp
```

---

# 33. Time-Series ML Rules

Do not randomly shuffle financial time-series data for ordinary train/test evaluation.

Prefer:

```text
Past → Future
```

For example:

```text
Train
2018–2021

Validation
2022

Test
2023–2024
```

The model must never see future observations during training.

---

# 34. Probability Calibration

If the model produces:

```text
P(up) = 0.78
```

that number should ideally have meaningful statistical interpretation.

For example, among predictions near 0.78, roughly 78% should satisfy the defined target over a sufficiently large sample if the model is well calibrated.

Consider calibration methods when necessary.

---

# 35. Integrating AI With the Strategy

Do not immediately replace the strategy.

Instead:

```text
Rule-Based Strategy
       ↓
Candidate Trade
       ↓
ML Model
       ↓
Probability
       ↓
Decision Filter
       ↓
Risk Manager
```

Example:

```text
Technical Strategy:
BUY AAPL

ML:
P(target) = 0.74

Risk:
Allowed

Final:
BUY
```

Another example:

```text
Technical Strategy:
BUY TSLA

ML:
P(target) = 0.51

Risk:
High volatility

Final:
HOLD
```

The AI acts as a filter or confidence layer.

---

# 36. Compare AI vs No AI

This is mandatory.

Run:

```text
Strategy A:
Rule-based only

Strategy B:
Rule-based + ML filter
```

Compare:

```text
Return
Sharpe
Sortino
Drawdown
Win rate
Profit factor
Trade count
Turnover
Stability
```

If the AI does not improve out-of-sample performance or robustness, do not use it.

"AI" is not a goal by itself.

The Phase 14 implementation defaults to a five-observed-bar, +0.5% label and
a fixed 0.60 BUY-filter threshold solely for a prototype. They are not owner
approved trading parameters. A model can veto a rule-based BUY, never create
an independent BUY, and does not override exits or risk checks. Its research
artifact is saved as XGBoost JSON rather than a Python pickle; Pi inference
requires a supported 64-bit environment and validation on that Pi.

---

# 37. Market Regime Detection

Later, add market-regime awareness.

Possible regimes:

```text
Bull
Bear
Sideways
High Volatility
Low Volatility
```

A simple initial regime:

```text
S&P 500 > SMA200
```

can be used as a basic market trend indicator.

A more advanced approach can use ML.

The strategy can then behave differently:

```text
Bull:
normal exposure

Sideways:
reduce trades

Bear:
reduce exposure

High volatility:
smaller positions
```

---

# 38. News and Sentiment — Later Phase

Eventually, add:

```text
Price Data
+
Technical Features
+
Market Regime
+
News
+
Sentiment
```

A sentiment model could generate:

```text
sentiment_score
```

Then combine it with other signals.

Do not add news/LLM processing in V1.

The first objective is to establish a reliable quantitative pipeline.

---

# 39. Why Not Use an LLM as the Main Trader?

An LLM is useful for:

- news interpretation
- summarization
- extracting structured information
- reasoning about qualitative events

But it should not be the core numerical execution engine.

A quantitative model is better suited for:

```text
price features
returns
probabilities
position sizing
risk
```

Use LLMs as an optional research/sentiment component rather than giving them direct unrestricted trading authority.

---

# 40. Phase 15 — Paper Trading Engine

Once backtesting is acceptable:

```text
Backtest
    ↓
Walk Forward
    ↓
Paper Trading
```

The paper bot should use the same production architecture as the eventual live bot.

Ideally:

```text
Broker Interface
      ↓
┌───────────────┐
│ Paper Alpaca  │
└───────────────┘
```

and later:

```text
┌───────────────┐
│ Live Alpaca   │
└───────────────┘
```

The strategy should not know which environment it is using.

---

# 41. Paper Trading Duration

Do not judge the system after two days.

Run it long enough to encounter different conditions:

- trending market
- sideways market
- high volatility
- low volatility
- API interruptions
- weekends
- market holidays
- unexpected restarts

Paper trading is also an engineering test.

You are testing:

```text
strategy
+
execution
+
risk
+
recovery
+
data
+
monitoring
```

---

# 42. Paper Trading Limitations

Paper trading is not identical to live trading.

It may not perfectly reproduce:

- market impact
- queue position
- slippage
- liquidity
- partial fills
- execution latency

Therefore:

```text
Good paper results
≠
Guaranteed live results
```

Treat paper trading as necessary but insufficient validation.

---

# 43. Phase 16 — Raspberry Pi Deployment

Install:

```text
Ubuntu
Python
Git
SQLite
```

Clone the repository:

```bash
git clone <repository>
cd trading-bot
```

Create the environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure `.env`.

Run manually first:

```bash
python -m app.main
```

Only after it works reliably should it become a system service.

---

# 44. systemd Service

Create a service similar to:

```text
/etc/systemd/system/trading-bot.service
```

Conceptually:

```ini
[Unit]
Description=Algorithmic Trading Bot
After=network-online.target
Wants=network-online.target

[Service]
User=your_user
WorkingDirectory=/home/your_user/trading-bot
EnvironmentFile=/home/your_user/trading-bot/.env
ExecStart=/home/your_user/trading-bot/.venv/bin/python -m app.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

Check:

```bash
systemctl status trading-bot
```

Logs:

```bash
journalctl -u trading-bot -f
```

---

# 45. Automatic Recovery

The service should restart after:

```text
Python crash
```

but the application itself should also handle:

```text
network errors
API errors
temporary data failures
```

Do not solve every problem with:

```text
Restart everything
```

The application should distinguish between recoverable and critical errors.

---

# 46. Logging

Use structured logs.

Important events:

```text
BOT_STARTED
BOT_STOPPED
DATA_RECEIVED
DATA_ERROR
SIGNAL_GENERATED
RISK_REJECTED
ORDER_SUBMITTED
ORDER_FILLED
ORDER_REJECTED
POSITION_CHANGED
MODEL_LOADED
MODEL_ERROR
RECONCILIATION
KILL_SWITCH
```

Each event should include:

```text
timestamp
symbol
strategy
model version
order ID
severity
message
```

Avoid logging API secrets.

---

# 47. Monitoring Dashboard

A FastAPI dashboard can display:

```text
System Status
Portfolio
Positions
Orders
Recent Signals
AI Predictions
Strategy Performance
Daily P&L
Drawdown
Risk Exposure
System Health
```

Example:

```text
TRADING BOT
────────────────────────────

Status: RUNNING

Portfolio
Equity:       $101,284
Cash:          $42,120
Exposure:          58%

Today's P/L
+$284

Positions
AAPL     +3.2%
NVDA     +5.1%
MSFT     -0.7%

Strategy
Regime: BULL
Signals today: 4
Trades today: 2

AI
Model: XGBoost v7
Confidence: 74%

System
CPU: 21%
RAM: 420 MB
Temperature: 54°C
```

Keep the dashboard read-only initially.

Do not add "BUY NOW" buttons until the execution system is extremely well tested.

---

# 48. Alerts

Later, add alerts for:

```text
Bot stopped
Bot restarted
Order rejected
Unexpected position
Daily loss limit reached
Kill switch triggered
API unavailable
Database problem
Model problem
```

A Telegram bot or another notification provider can be added later.

---

# 49. Security

Minimum requirements:

- API keys only in environment variables
- `.env` excluded from Git
- SSH key authentication
- firewall on Raspberry Pi
- dashboard restricted to LAN
- no unnecessary public ports
- regular OS updates
- regular database backups

Never expose the trading API keys through:

- GitHub
- dashboard
- logs
- screenshots
- frontend JavaScript

---

# 50. Database Backups

The bot's database contains valuable research and operational history.

Back up:

```text
SQLite database
configuration
model metadata
logs
```

Do not necessarily back up every generated market-data file if it can be reconstructed.

Use a simple scheduled backup initially.

---

# 51. Testing Strategy

Create tests for each important layer.

## Unit tests

Test:

```text
indicators
position sizing
risk limits
signal generation
order construction
data validation
```

## Integration tests

Test:

```text
Bot → Alpaca Paper API
Database → Portfolio Manager
Strategy → Risk Manager
Risk Manager → Order Manager
```

## Failure tests

Simulate:

```text
network outage
API timeout
duplicate order
partial fill
database unavailable
invalid market data
bot restart
```

A trading system must be tested primarily for how it fails.

---

# 52. Paper Trading Safety Rules

During the initial stage:

```text
PAPER ONLY
```

Add an explicit configuration:

```text
TRADING_MODE=paper
```

The application should refuse to start in live mode unless several safeguards are satisfied.

For example:

```text
if TRADING_MODE == "live":
    require explicit LIVE_TRADING_ENABLED=true
```

Even better, make live trading a separately configured deployment.

---

# 53. Suggested Development Milestones

## M1 — Alpaca Connectivity

Deliverables:

```text
✓ Alpaca client
✓ Account query
✓ Market data query
✓ Paper environment
✓ Secure configuration
```

---

## M2 — Historical Data

Deliverables:

```text
✓ Historical downloader
✓ Data validation
✓ SQLite storage
✓ Data retrieval API
```

---

## M3 — Indicators

Deliverables:

```text
✓ EMA
✓ RSI
✓ ATR
✓ MACD
✓ Volume features
✓ Returns
```

---

## M4 — Strategy V1

Deliverables:

```text
✓ Strategy interface
✓ Entry rules
✓ Exit rules
✓ Signal storage
```

---

## M5 — Backtester

Deliverables:

```text
✓ Portfolio simulation
✓ Order simulation
✓ Slippage
✓ Metrics
✓ Equity curve
✓ Drawdown
```

---

## M6 — Risk Manager

Deliverables:

```text
✓ Position sizing
✓ Exposure limits
✓ Daily loss limit
✓ Drawdown limit
✓ Kill switch
```

---

## M7 — Paper Execution

Deliverables:

```text
✓ Order manager
✓ Fill handling
✓ Reconciliation
✓ Error handling
✓ Crash recovery
```

---

## M8 — Raspberry Pi

Deliverables:

```text
✓ Git deployment
✓ systemd
✓ Automatic restart
✓ Persistent database
✓ Logs
```

---

## M9 — Dashboard

Deliverables:

```text
✓ System status
✓ Portfolio
✓ Positions
✓ Orders
✓ Signals
✓ P&L
✓ Risk
```

---

## M10 — Machine Learning

Deliverables:

```text
✓ Dataset generator
✓ Features
✓ Target
✓ Time-series validation
✓ XGBoost model
✓ Model versioning
```

---

## M11 — AI Integration

Deliverables:

```text
✓ AI prediction
✓ Confidence threshold
✓ Strategy + AI combination
✓ Comparison against baseline
```

---

## M12 — Robustness Testing

Deliverables:

```text
✓ Walk-forward tests
✓ Multiple market regimes
✓ Slippage sensitivity
✓ Parameter sensitivity
✓ Out-of-sample evaluation
```

---

## M13 — Long-Term Paper Trading

Deliverables:

```text
✓ 24/7 operation
✓ No unexplained orders
✓ No state corruption
✓ Stable memory usage
✓ Stable CPU usage
✓ Reconciliation works
✓ Alerts work
```

---

# 54. Research Workflow

Every strategy/model experiment should follow:

```text
Hypothesis
    ↓
Data
    ↓
Feature Engineering
    ↓
Backtest
    ↓
Out-of-Sample Test
    ↓
Walk Forward
    ↓
Robustness Tests
    ↓
Paper Trading
```

Never do:

```text
Look at historical results
    ↓
Change parameters
    ↓
Repeat until results look amazing
```

That is a classic path to overfitting.

---

# 55. Parameter Sensitivity

Suppose:

```text
EMA = 20
```

works extremely well.

Test:

```text
EMA = 15
EMA = 18
EMA = 20
EMA = 22
EMA = 25
```

If only exactly `20` works and everything else fails, the strategy may be overfit.

A robust strategy should generally perform reasonably across a range of nearby parameters.

---

# 56. Stress Testing

Test worse-than-normal assumptions:

```text
2x expected slippage
3x expected slippage
Delayed execution
Lower liquidity
Missing candles
API downtime
```

A strategy should not collapse immediately under small changes.

---

# 57. Performance Evaluation

Do not optimize only for total return.

A better objective considers:

```text
Return
Sharpe
Drawdown
Volatility
Trade frequency
Stability
```

Example:

```text
Strategy A

Return:      35%
Sharpe:      1.7
Drawdown:   -12%

Strategy B

Return:      45%
Sharpe:      0.8
Drawdown:   -38%
```

Strategy A may be substantially more attractive depending on the intended risk profile.

---

# 58. Recommended Initial Universe

Do not start with hundreds of symbols.

Start with a small, liquid universe.

For example:

```text
AAPL
MSFT
NVDA
AMZN
GOOGL
META
TSLA
```

The exact universe should be chosen deliberately.

Later, expand.

---

# 59. Recommended Initial Timeframe

For the first version:

```text
15-minute
```

or:

```text
1-hour
```

Advantages:

- less noise
- fewer API calls
- less CPU
- simpler debugging
- easier execution
- suitable for Raspberry Pi
- easier to understand

Avoid high-frequency trading on a Raspberry Pi 3B.

---

# 60. Real-Time Event Loop

A simplified production loop:

```text
while running:

    check_market_status()

    update_market_data()

    validate_data()

    update_features()

    generate_strategy_signals()

    generate_ai_predictions()

    combine_signals()

    evaluate_risk()

    manage_positions()

    submit_allowed_orders()

    reconcile_with_alpaca()

    persist_state()

    update_health_status()

    sleep_until_next_event()
```

Never use an uncontrolled tight loop.

---

# 61. Scheduling

The bot should understand market sessions.

At minimum:

```text
PRE_MARKET
OPEN
REGULAR_SESSION
CLOSE
AFTER_HOURS
CLOSED
```

The strategy should explicitly state which sessions it operates in.

Do not accidentally submit orders during a period the strategy was not designed for.

---

# 62. Observability

Every trading decision should be explainable.

For every order, you should be able to answer:

```text
Why did the bot buy?
Which strategy?
Which features?
What was the AI prediction?
What was the risk calculation?
What was the position size?
Which rule approved it?
Which data timestamp was used?
Which model version was used?
```

Example:

```text
BUY AAPL

Strategy:
TrendFollowingV1

Reason:
EMA20 > EMA50
Price > EMA200
RSI = 61

AI:
P(target) = 0.76
Model = xgb_v7

Risk:
Portfolio exposure = 51%
Position after trade = 7.8%
Risk per trade = 0.8%

Decision:
APPROVED
```

This is extremely useful for debugging.

---

# 63. Model Versioning

Never overwrite a model without tracking versions.

Use:

```text
models/
    xgb_v1.pkl
    xgb_v2.pkl
    xgb_v3.pkl
```

And metadata:

```text
model_version
features
training_range
target
hyperparameters
metrics
```

The database should store which model generated each prediction.

---

# 64. Feature Versioning

The same applies to features.

If V1 uses:

```text
RSI
EMA20
EMA50
ATR
```

and V2 adds:

```text
volume_ratio
market_return
```

record the feature version.

Otherwise reproducing old predictions becomes difficult.

---

# 65. Configuration

Avoid hardcoding parameters.

Use:

```text
config/config.yaml
```

Possible configuration:

```yaml
trading:
  mode: paper
  timeframe: 15m

risk:
  max_portfolio_exposure: 0.70
  max_position_size: 0.10
  max_risk_per_trade: 0.01
  max_daily_loss: 0.03

strategy:
  name: trend_following_v1

ai:
  enabled: false
  model_version: xgb_v1
```

This allows controlled experimentation without editing application code.

For the current paper-risk gate, `config/risk_limits.example.json` is the
machine-readable example and `app/risk/config.py` requires a reviewed
`config/risk_limits.json` with `approved_for_paper: true` before paper
execution. JSON is used here to avoid adding a YAML dependency; the broader
YAML example above remains a future configuration target. The actual risk
limits file should be committed so Windows and Raspberry Pi use the same
reviewed policy. API credentials remain only in each machine's `.env` file.
The initial `config/risk_limits.json` contains empty `null` limits and
`approved_for_paper: false`; fill it in only after the owner chooses the policy.

---

# 66. Separation of Concerns

A strong architecture should prevent modules from doing unrelated work.

Bad:

```text
strategy.py
    downloads data
    calculates indicators
    submits orders
    updates database
    sends Telegram
```

Good:

```text
Data Layer
    ↓
Features
    ↓
Strategy
    ↓
Risk
    ↓
Orders
    ↓
Broker
```

This makes the system easier to test and replace.

---

# 67. Broker Abstraction

Even though the first broker is Alpaca, use an interface.

Conceptually:

```python
class Broker:
    def get_account(self):
        ...

    def get_positions(self):
        ...

    def submit_order(self, order):
        ...

    def cancel_order(self, order_id):
        ...
```

Then:

```text
Broker Interface
       │
       └── AlpacaBroker
```

Later you could implement another broker without rewriting the strategy.

---

# 68. AI Expansion Roadmap

Once the first ML model works:

### Level 1

Binary classification:

```text
Will return exceed X?
```

### Level 2

Regression:

```text
Expected future return
```

### Level 3

Market regime:

```text
Bull / Bear / Sideways
```

### Level 4

Multi-model ensemble:

```text
Trend model
Momentum model
Volatility model
Sentiment model
```

### Level 5

Portfolio-level model:

```text
Which candidates deserve capital?
```

Do not jump to Level 5 before Level 1 is properly validated.

---

# 69. Potential Advanced Architecture

Eventually:

```text
                   ┌───────────────┐
                   │ Market Data   │
                   └───────┬───────┘
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
        Technical       Market         News
        Features        Regime       Sentiment
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                    Feature Store
                           │
                  ┌────────┴────────┐
                  ▼                 ▼
            Rule Strategy       ML Models
                  │                 │
                  └────────┬────────┘
                           ▼
                     Signal Engine
                           │
                           ▼
                    Portfolio Engine
                           │
                           ▼
                      Risk Engine
                           │
                           ▼
                     Order Engine
                           │
                           ▼
                       Alpaca
```

This is the long-term target, not the V1.

---

# 70. What Should Run on the Raspberry Pi?

## Yes

```text
✓ Alpaca API client
✓ Market data ingestion
✓ SQLite
✓ Indicators
✓ Rule-based strategy
✓ ML inference
✓ Risk management
✓ Order management
✓ FastAPI dashboard
✓ systemd
✓ Logging
```

## Prefer PC/cloud

```text
✗ Large-scale backtesting
✗ Hyperparameter sweeps
✗ Large ML training
✗ Deep learning training
✗ Massive historical data processing
```

---

# 71. Development Workflow

Recommended workflow:

```text
Windows PC (VS Code: edit, run, test, backtest)
        ↓
Git commit and push to GitHub
        ↓
Raspberry Pi (pull the reviewed revision)
        ↓
Install/use its own environment and local paper credentials
        ↓
Run checks, then start/restart the paper-trading service
```

The repository is the shared source of truth, and the application must remain runnable from a checkout on either computer. Do not copy a Windows virtual environment to the Pi or commit local `.env` files, databases, logs, caches, or machine-specific paths. Configure credentials independently on each machine, with paper trading as the default. Windows is the normal development and research environment; the Pi is the intended always-on execution and monitoring environment. Both must be able to run the bot for development/smoke testing.

For research:

```text
PC
 ↓
Experiment
 ↓
Backtest
 ↓
Model
 ↓
Commit version
 ↓
Deploy model to Pi
```

---

# 72. Production Deployment Workflow

Never deploy experimental code directly into the running bot.

Use:

```text
development
    ↓
testing
    ↓
paper environment
    ↓
long-term validation
    ↓
production
```

Eventually, maintain separate configuration for:

```text
development
paper
live
```

---

# 73. Suggested First Strategy

For the first architecture test, keep the strategy deliberately simple.

Example:

```text
Universe:
7 liquid US stocks

Timeframe:
1 hour

Trend:
Price > EMA200

Momentum:
EMA20 > EMA50

Momentum confirmation:
RSI between 50 and 70

Risk:
Max 10% per position
Max 70% portfolio exposure
```

Then backtest it.

The goal is to learn:

```text
Does the system work?
```

not:

```text
Can we make the backtest show 300%?
```

---

# 74. Success Criteria for Each Phase

## Infrastructure

```text
Bot starts
Bot connects
No secrets leak
```

## Data

```text
Data is complete
Timestamps are correct
No invalid candles
```

## Strategy

```text
Signals are deterministic
Signals are reproducible
```

## Backtester

```text
No look-ahead
Realistic fills
Correct portfolio accounting
```

## Risk

```text
Unsafe trades are rejected
```

## Paper Trading

```text
Orders match expected decisions
No duplicate orders
State survives restart
```

## AI

```text
Out-of-sample improvement
```

## Production

```text
Stable 24/7 operation
```

---

# 75. Final End-to-End Architecture

The mature version should look approximately like this:

```text
                           ┌──────────────────────┐
                           │       Alpaca         │
                           │                      │
                           │ Market Data / Orders │
                           └──────────┬───────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │     Market Data Layer   │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │       Data Storage      │
                         │         SQLite          │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │   Feature Engineering   │
                         └────────────┬────────────┘
                                      │
                     ┌────────────────┼────────────────┐
                     │                │                │
                     ▼                ▼                ▼
                Technical          Market            News
                Features           Regime          Sentiment
                     │                │                │
                     └────────────────┼────────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │      Signal Engine       │
                         │                          │
                         │ Rule Strategy + ML       │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │     Portfolio Manager   │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │       Risk Manager      │
                         │                         │
                         │ Exposure / Position     │
                         │ Drawdown / Kill Switch │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │       Order Manager     │
                         └────────────┬────────────┘
                                      │
                                      ▼
                                Alpaca Paper
                                      │
                                      ▼
                             Fill / Position
                                      │
                                      ▼
                              Reconciliation
                                      │
                                      ▼
                                  SQLite

                  ┌───────────────────────────────────┐
                  │       Monitoring / Dashboard      │
                  │                                   │
                  │ FastAPI + Jinja + HTMX            │
                  └───────────────────────────────────┘

                  ┌───────────────────────────────────┐
                  │        Raspberry Pi 3B            │
                  │                                   │
                  │ 24/7 execution + monitoring       │
                  └───────────────────────────────────┘
```

---

# 76. The Complete Development Order

Follow this order.

```text
01. Create Alpaca Paper account
        ↓
02. Create Git repository
        ↓
03. Create Python project
        ↓
04. Build Alpaca client
        ↓
05. Download historical data
        ↓
06. Build SQLite data layer
        ↓
07. Validate market data
        ↓
08. Build technical indicators
        ↓
09. Build Strategy V1
        ↓
10. Build backtesting engine
        ↓
11. Add realistic slippage/costs
        ↓
12. Add performance metrics
        ↓
13. Add walk-forward validation
        ↓
14. Build Risk Manager
        ↓
15. Build Position Manager
        ↓
16. Build Order Manager
        ↓
17. Connect to Alpaca Paper Trading
        ↓
18. Implement reconciliation
        ↓
19. Implement crash recovery
        ↓
20. Deploy to Raspberry Pi
        ↓
21. Add systemd
        ↓
22. Add monitoring/dashboard
        ↓
23. Run long-term Paper Trading
        ↓
24. Build ML dataset
        ↓
25. Train XGBoost model
        ↓
26. Validate out-of-sample
        ↓
27. Integrate ML as a signal/filter
        ↓
28. Compare AI vs baseline
        ↓
29. Stress test entire system
        ↓
30. Continue Paper Trading
        ↓
31. Only after extensive validation consider Live
```

---

# 77. What "Good" Looks Like

A good trading bot is **not**:

```text
AI
+
BUY/SELL
+
High backtest return
```

A good system is:

```text
Reliable data
+
Reproducible research
+
Realistic backtesting
+
Out-of-sample validation
+
Robust strategy
+
Strict risk management
+
Reliable execution
+
State recovery
+
Monitoring
+
Controlled ML
+
24/7 stability
```

The objective should be:

> **Build a reliable quantitative trading platform first. Find out whether it has a genuine statistical edge second.**

If no edge exists, the correct engineering outcome is to discover that before risking real money.

---

# 78. Recommended Immediate Next Step

Do not implement all phases simultaneously.

Start with **Milestone 1**:

```text
Raspberry Pi
    ↓
Python
    ↓
Alpaca Paper API
    ↓
Get account information
    ↓
Get market data
    ↓
Log the result
```

Once that works, move to historical data and SQLite.

Only after the data pipeline works should the strategy be written.

The first working version should therefore be intentionally boring:

```text
Alpaca → Data → SQLite → Log
```

Then:

```text
Data → Indicators → Strategy → Backtest
```

Then:

```text
Strategy → Risk → Paper Orders
```

Then:

```text
Strategy + ML → Risk → Paper Orders
```

That progression minimizes complexity while giving the project a path all the way from a Raspberry Pi prototype to a robust algorithmic trading system.


---

# Coding AI Change Log

The coding AI should maintain a concise change log below this line as implementation progresses.

For each completed milestone, record:

```text
## <Milestone / Date>

### Implemented
- ...

### Files changed
- ...

### Tests
- ...

### Validation
- ...

### Known limitations
- ...

### Next step
- ...
```

## Phases 0–10 and historical research / 2026-10-16

### Implemented
- Paper-only Alpaca client, calendar-aware market-data validation, and SQLite audit storage.
- Deterministic `technical_v1` features and `trend_following_v1` strategy with a reusable strategy interface.
- Append-only signal recording for reproducible decisions.
- Single-symbol backtesting with causal feature access, next-candle fills, configurable fees/spread/slippage, equity, drawdown, and the Section 17 metrics.
- A historical downloader with feed/adjustment provenance, checksum manifest, strict interval review, and a local three-scenario backtest command.
- Expanding-year walk-forward calibration of a declared strategy threshold grid, with later-year evaluation kept separate from parameter selection.
- Standalone, fail-closed risk decisions for proposed trades with configurable exposure, loss, drawdown, position-count, optional sector, and volatility gates.
- Phase 11 paper-account reconciliation and Phase 12 disabled-by-default order management with an unapproved risk configuration placeholder.
- Phase 13 read-only startup recovery checks SQLite integrity, unfinished broker orders, portfolio changes, and market state before reporting whether order evaluation may resume.

### Files changed
- `app/broker/`, `app/data/`, `app/ai/`, `app/strategy/`, `app/risk/`, `app/portfolio/`, `app/orders/`, `app/recovery/`, `backtesting/`, `tests/`, `requirements.txt`, and `README.md`.

### Tests
- 87 unit tests pass on Windows, including 12 Phase 10 risk-gate tests, 10 focused Phase 11 reconciliation tests, and 12 position-sizing, kill-switch, and risk-configuration tests.
- 20 focused Phase 12 order/idempotency tests pass.
- 17 focused Phase 13 recovery tests pass; 124 tests pass across the full Windows suite.
- 11 focused Phase 14 ML tests pass offline; 135 tests pass across the full Windows suite. A real XGBoost training run and Pi inference check have not been performed yet.

### Validation
- Read-only Alpaca historical-data and calendar checks passed during Phase 4.
- Downloaded 6,540 adjusted AAPL SIP 15-minute regular-session bars for 2021. A February–December 2021 single-symbol case study returned +1.22% optimistic, +0.28% base, and -2.87% pessimistic on a $100,000 simulated account. This is an illustrative in-sample case study, not evidence of a robust strategy.
- Downloaded 32,600 adjusted AAPL SIP 15-minute bars for 2019–2023 and ran two expanding yearly folds. The 2022/2023 base-cost test returns were +0.20%/+0.46%; pessimistic-cost returns were -2.12%/-2.49%. Both folds selected the narrow candidate from earlier years. A separate 2018–2022 request was rejected after 50 unobserved scheduled intervals clustered on May 2–3, 2018.
- Phase 10 tests exposed and fixed a floating-point boundary error at the exact maximum-drawdown threshold.
- No order has been submitted, modified, or canceled by this implementation.

### Known limitations
- The project has not yet run its automated tests on Raspberry Pi OS.
- Single-symbol backtesting and an offline shared-cash multi-symbol daily engine now exist. The daily engine includes research allocation/loss gates and an OHLC stop proxy, but requires identical instrument calendars. Dynamic historical universes, audited point-in-time membership/lifecycle outcomes and full broker-risk/execution parity remain incomplete. The Phase 14 ML pipeline has no reviewed research result or Pi validation.

### Next step
- Phase 13 startup recovery is implemented and covered by 17 offline tests. Phase 14 has an offline single-symbol ML research pipeline and 11 focused tests, but no reviewed training result yet. Neither phase enables submission. The owner can use `docs/research_scope_decision_workbook.md` to specify the study and its untouched test period. The initial `config/risk_limits.json` is unapproved and has empty limits; the owner must choose or accept all required limits before any paper-order workflow is enabled. Next build a safe exit/stop workflow and a full broker fill/activity ledger before unattended paper trading or realized P&L reporting. A proposed stop price currently sizes risk but does not create a protective broker order. Point-in-time universe data and a multi-symbol portfolio engine remain necessary before broader market-wide predictive claims.

# Important Handoff Rule

This document describes the **target system and development roadmap**. It does not mean every component should exist immediately.

The preferred implementation order is:

```text
Alpaca connectivity
    ↓
Historical market data
    ↓
Data validation + SQLite
    ↓
Indicators / features
    ↓
Deterministic strategy
    ↓
Backtesting
    ↓
Risk management
    ↓
Paper order execution
    ↓
Reconciliation + crash recovery
    ↓
Raspberry Pi deployment
    ↓
Monitoring / dashboard
    ↓
Long-term paper trading
    ↓
ML dataset + validation
    ↓
ML model
    ↓
AI strategy integration
    ↓
Robustness / walk-forward validation
```

**Do not skip ahead simply because a later component is described in this document.**

## Broad-universe research update: 2026-10-24

The owner authorized the [broad-universe feasibility audit](docs/broad_universe_audit_protocol.md)
and a subsequent finite entry/selection study. The
[completed audit](docs/broad_universe_audit_results.md) snapshotted 33,560
US-equity asset records and checked 56 preselected SIP daily histories in
2016-2023. It demonstrates broad price access, not complete historical
membership, common-stock classification or delisting outcomes. Current
assets and symbols are not a point-in-time historical universe.

`backtesting/universe_audit.py` and new read-only broker methods preserve
metadata, pagination, empty histories, validation errors/warnings and hashes.
No 2024-2025 prices, orders or paid purchases were involved. No new unit tests
were added or run for this increment; the live coverage run and artifact
hash checks passed as described in the results. Pi execution remains unverified.

The [entry/selection study](docs/broad_entry_selection_study.md) defines eight
matched arms, explicit stricter volume/relative-strength gates and causal
ranking, with a maximum 92 simulations and early stopping. It is **scoped,
not simulated**: historical data/lifecycle semantics and dynamic-universe
engine support must meet its gate first. Codex owns that engineering work;
no owner risk-limit edits are needed now. Any paid source requires a concrete
reviewed proposal and explicit approval. Paper-risk approval, final reserved
evaluation and paper activation remain separate later decisions.

## No-purchase lifecycle increment: 2026-10-24

The owner prefers not to buy data. Record **$0 in new data purchases** as the
current policy; do not upgrade subscriptions or start paid trials. The
[free-data/source report](docs/free_data_and_lifecycle_progress.md) explains
that billing status is unknown and working historical SIP access is not
proof of a paid plan. Four read-only company-event queries succeeded with
existing access and yielded ten preserved review candidates. No historical
publication/payment time is inferred from provider processing dates.

`backtesting/universe.py` defines the versioned
[historical identity/lifecycle format](docs/historical_universe_format.md).
The existing portfolio engine now has optional sparse-history support for
explicitly dated IPO/listing intervals, ticker aliases under stable IDs and
verified terminal cash at a session open. It requires declared raw/event-free
inputs except supported terminal cash. No prices are filled, unresolved
in-lifetime gaps block scoring, and terminal cash has a separate ledger with
account P&L reconciliation. Ordinary trade metrics exclude cash events.
Legacy aligned-data mode remains the default.

This is initial engineering support, not complete broad-market readiness.
Focused unit/failure tests, unchanged-control replays, split/dividend and
other corporate-action adapters, and independently audited membership/event
coverage remain outstanding. Only Python compilation, source-access requests,
offline candidate extraction and diff checks were performed in this increment;
no automated unit tests or strategy simulations were run. The eight-arm study
stays unscored, 2024-2025 stay reserved, paper-risk approval stays disabled,
and Pi validation remains due. No owner risk edits, account upgrade or
manual data collection are needed for the next engineering work.

## Lifecycle/action verification update: 2026-10-24

The next [corporate-action increment](docs/corporate_action_progress.md)
adds version-2 explicit splits and ordinary cash dividends under raw execution
prices. Share counts, entry basis, pending order units and protective stops
convert together at a split. Historical feature views use only splits already
effective at each decision, never future factors. Dividend entitlements are
separate nominal USD receivables until an explicit cash-availability session;
they survive sales/terminal cash exits and are not counted twice. Ordinary
trade statistics exclude cash income; account equity includes it.

69 focused lifecycle/action/source tests pass. All 36 prior holding-study
cases reproduce metrics, costs, fills, equity curves, events and risk events
exactly in `data/reports/lifecycle_regression_v1/report.json`; original
provenance/artifacts remain unchanged. Full-suite result: 348 tests, 346 passes,
two existing optional ML errors because `sklearn` is not installed. No optional
ML dependency was installed. The reviewed AAPL split record cross-checks
saved free-source evidence against issuer/OCC announcements, without a new
price download or a paid purchase.

Historical membership/event completeness, fractional cash-in-lieu, special
distributions and other unsupported events, and action-aware risk diagnostics
remain gates before broad strategy scoring. Existing OHLC risk diagnostics
explicitly reject corporate-action ledgers rather than omit events. Next
build a reviewed raw-price/action data pilot and establish an honest broader
historical scope using existing/public sources. Owner risk settings, paper
activation, 2024-2025 evaluation and Pi execution remain unchanged/unapproved;
new data purchases remain $0. No owner configuration is required now.

## Reviewed raw-price pilot and historical baskets: 2026-10-24

The [raw-price/action and historical-basket report](docs/raw_action_pilot_and_historical_baskets.md)
supersedes the previous action-aware risk gate. The existing daily risk helper
now reconstructs split share counts, ordinary dividend receivables/payments
and terminal cash before marking the account. It rejects inconsistent ledgers
and retains its conservative daily-OHLC bounds; real intraday equity remains
unobserved. All 36 original holding-study daily-envelope cases match exactly,
with original data and artifact hashes checked and no provenance rewritten.

The reviewed Apple pilot uses 505 real SIP/raw daily candles and 505 saved
exchange sessions from 2019-2020, with 2019 uninvested warmup and one predefined
2020 BUY/HOLD accounting case. All seven checks pass: three shares become
twelve at the effective 4-for-1 split, all four dividends pay once ($9.69),
and financial/risk ledgers reconcile. Issuer announcements supply explicit
payment evidence, including the missing February provider date. Cash is modeled
at the first actual session after issuer payment, not claimed to be verified
broker availability. This deliberately selected fixture is not strategy
selection, acceptance of its marked return, or permission to trade.

Public SEC fund filings establish complete fixed source baskets of **506
security rows at 2016-09-30** and **505 at 2020-09-30**, with exact disclosed
common-stock value reconciliation. Filing dates, not holdings dates, govern
availability: conservative bounds are 2016-11-30 and 2020-12-02 UTC. The 2016
list can precede a 2017 study; the 2020 list cannot be applied to 2017.
Tracked extracted CSVs retain all rows and original share-class/footnote names,
including later failures/acquisitions. Their row keys are not permanent
security IDs. These are fixed historical fund baskets, not daily full-market
membership. The extractor refuses wrong fund/period, missing rows/totals and
duplicate source names; unresolved securities are not silently removed.

**Verification:** 118 focused tests passed; full suite ran 381 tests, with
379 passes and two existing optional ML import errors because `sklearn` is
absent. The optional dependency was not installed. Python compilation and
diff checks passed. The new report includes Windows installation instructions
using the existing project `.venv` and `requirements-ml.txt`.

**Next engineering work:** Resolve dated identities/ticker aliases and audit
raw-price/action/terminal-outcome coverage for the retained 2016 cohort.
Broader strategy scoring remains gated. A fixed-2016-basket scope is a concrete
no-purchase candidate, not a silent replacement for the original all-eligible
US-stock protocol; present any material scope amendment before scoring.
Unsupported events still require adapters. Owner risk edits, payment/card
setup and manual stock collection are unnecessary for this data work. Paper
activation remains separate; 2024-2025 prices remain reserved, new purchases
remain $0, and Pi validation is still due.

## No-charge historical cohort mapping and cache audit: 2026-10-24

The owner explicitly requires no new data/service charges. Continue with
saved files and free public sources; no subscriptions, paid trials, upgrades
or purchases are authorized. The prior Apple pilot's $9.69 was **simulated
dividend income**, not a fee, actual account payment or purchase. That pilot
placed neither paper nor live orders and moved no account money.

The [2016 cohort audit](docs/cohort_2016_audit_results.md) identifies dated
tickers for all 506 retained source securities: 449 unique normalized-name
matches, 56 explicit reviewed name/share-class pairs and one independent SEC
identity review for Dell Class V tracking stock. All 505 equity rows in the
free issuer's same-date IVV download are accounted for, with corresponding
historical prices corroborating identity. Original cohort rows remain intact.
These local IDs/one-date aliases are not permanent market identifiers or a
complete 2016-2023 alias history; all execution-readiness flags remain false.

Ten sourced event cases cover Under Armour and CBRE renames, original Alcoa
and Fox spin-offs/ticker reuse, Aetna and Level 3 mixed cash/share mergers,
Whole Foods' cash acquisition and original Bed Bath & Beyond's cancellation.
Historical knowledge/payment bounds and unsupported event mechanics remain
explicit gates. A missing event is unknown coverage, never an assertion that
a company is event-free or that a disappeared holding is worthless.

The offline command `python -m backtesting.cohort_audit --output data/reports/a_fresh_cohort_audit`
checked 33 saved daily-price files against hashes and the actual 2,012-session
2016-2023 calendar. One retained row has partial raw observations; fourteen
have candidate adjusted observations. None has complete raw calendar coverage.
Counts do not certify ticker continuity; genuine listing lifetimes/outcomes
must explain intervals instead of filling missing or post-delisting candles.

Actual audit integrity checks all passed; Python compilation and diff checks
passed. No unit tests or strategy performance simulations were added/run in
this increment. Source acquisition used free unauthenticated public GETs;
the analysis command itself is entirely offline and reads no credentials.
New broker/account requests, orders, purchases and installations were zero.
No old reports/hashes were rewritten; no reserved 2024-2025 candle datasets
were opened. Raspberry Pi execution remains unverified.

Next is a bounded no-purchase raw-price/action acquisition plan, starting with
representative ordinary/rename/terminal/complex-event cases and finishing
the required evidence/adapters before scaling. Broader strategy scoring,
scope review and eventual paper activation remain separate. No owner card,
manual stock collection or risk JSON changes are required for that data work.

## Free historical collection and event-gap review: 2026-10-24

The [bounded collection and review](docs/free_collection_results.md) is now
implemented and executed. The frozen 24-interval plan covers ordinary stocks,
renames, cash/mixed acquisitions, spin-offs and bankruptcy without selecting
by future returns. A separate GET-only transport reuses central credentials
but has no trading client, account/billing/subscription operations, redirects,
automatic retries, paid upgrades or feed fallback. It caps physical HTTP
attempts, spaces requests and enforces 2016-2023 raw daily SIP data only.
Automatic vendor ticker mapping is disabled with `asof="-"`; explicit alias
intervals are retained. Existing general broker/download methods are unchanged.

The run saved 23,747 raw candles; one additional observed boundary candle
brings the collection to **23,748 observations**, using **46 historical-data
GETs** including 21 distinct event queries. There are **249 unique provider
event records**. New purchases, account requests, subscription changes, orders
and package installations were zero. Reserved 2024-2025 candles were not used.

Independent evidence explains 66 Under Armour Class C pre-issuance absences
and establishes the May 3, 2023 Nasdaq suspension boundary for BBBY. The
CBRE March 19, 2018 candle exists under vendor label CBG; a separate one-day
query recovered it. The offline reviewer records that one label translation
without changing any OHLCV or timestamp and writes new, separate observed
alias streams: 2,012 Class A sessions, 1,946 Class C sessions and 2,012 CBRE
sessions. Original files and hashes are preserved. Empty OTC data remains
empty; no stale valuation, fabricated sale or early assumed zero is introduced.

Of eleven independently required event cross-checks, **ten have no matching
effective/ex-date provider record**. Sources establish distributions, renames
and mergers omitted from the queried API responses. Processing dates are not
publication times; missing API events are not an event-free-history declaration.
Seventy-seven out-of-interval event references are quarantined for identity/
date review, including a newer ARNC company's acquisition that cannot resolve
the original company. Generic fractional split entries cannot replace proper
spin-off/branch ownership accounting. Seven dated publication reviews retain
conservative knowledge bounds and explicit same-day timing limitations;
issuer payable dates are not certified broker cash availability.

Actual source/calendar/data review completed; compilation and diff checks
passed. No unit tests or strategy performance simulations were added/run in
this increment. An archived executed collector preserves the initial report's
source hash; later metadata fixes explicitly label reused action queries and
empty responses without rewriting old evidence. Full data remain under ignored
`data/reports/free_collection_v1` and `free_collection_review_v1`; reviewed
summaries, plans and primary-source hashes are tracked in docs.

**Next engineering work:** delayed terminal cash claims, cash/share acquisitions,
spin-off branches, fractional claims and an explicit valuation convention,
using saved representative cases before scaling. Complete dividend/publication
evidence, unavailable OTC history and full 506-stock coverage remain gates.
The broader entry/ranking study stays unscored. Purchases/plan upgrades are
not a fallback; no owner card, download, configuration or risk-setting action
is required now. Paper activation and Pi validation remain separate.

## Offline ownership-claim accounting: 2026-10-24

The [ownership-claim component and case replay](docs/claim_accounting.md)
implement delayed terminal cash rights, mixed cash/share acquisitions,
retained-parent spin-offs, same-class stock distributions and exact fractional
claims. The reusable `backtesting/claim_accounting.py` module uses the standard
library only. It has no broker, HTTP, credential or strategy imports. The
separate replay uses previously saved source terms, raw quotes and calendars;
no new data request, purchase, subscription change, order or package
installation occurred. All money in the checks is simulated.

Fixed cash rights and unknown fractional payouts stay outstanding, never
spendable. Fractional ownership has actual successor-price exposure until an
explicit reviewed cash allocation replaces it. Payment requires a separate
exact amount, known timestamp and availability timestamp; duplicate event/
payment/fixing instructions raise without mutation. Cash, shares, claims,
economic basis and realized/unrealized P&L reconcile exactly. Relative
contemporaneous-close component values allocate economic basis; this is not
tax accounting. Quotes must match the exact accounting instant and stable
identity. No stale mark, forward fill, assumed payout or future-price basis
allocation is permitted. Claim-aware OHLC bounds include fractional exposure
but are not an observed intraday portfolio path or a full drawdown study.

Verification: **111 focused unit tests pass**, including 26 new ledger tests
and 85 existing universe/action/risk tests; **84 saved-case/timeline checks
pass** across seven independent mechanics scenarios and a synthetic settlement
timeline. [Pinned inputs and results](docs/claim_accounting_summary.json) retain
source/code hashes and explicit assumptions. Detailed separate evidence is in
`data/reports/claim_accounting_v2`; earlier reports are not rewritten. No
2024-2025 candles were used; full optional-ML tests and Pi execution were not
part of this check.

Case timing/delivery assumptions do not certify actual historical eligibility
or broker credit. Aetna/Level 3 fractions and Alcoa/Arconic branches are kept
as rights rather than discarded. The newer Arconic child quote is absent:
valuation fails without it, and a clearly labeled synthetic quote checks
arithmetic only. Under Armour's initial branch check uses its first regular
quoted session rather than pretending to price the earlier distribution.
Fox election/conversion, the additional Under Armour distribution ratio,
Bed Bath OTC prices, and real fractional-payment/cash-availability evidence
remain unresolved. No strategy return study or paper readiness follows.

**Next engineering work:** integrate this checked ledger through an explicit
historical-event strategy adapter with entitlement/delivery gates, stop/order
invalidation, inherited holding reviews, feature-history conventions and
cash/exposure/risk reporting. Existing universe schemas still reject these
unsupported strategy events, and legacy risk reporting rejects the new
accounting format rather than ignoring claims. Preserve old event-free results
and complete evidence checks before expanding/scoring the basket. This work
is the coding agent's responsibility; no owner purchase, card, download or
risk-setting change is required now. Paper activation stays disabled.

## Ownership strategy adapter: 2026-10-27

The [explicit ownership adapter](docs/ownership_adapter.md) now connects the
exact ledger to the existing daily portfolio simulator. It requires a reviewed
`OwnershipSchedule` and the version-2 raw universe action scope
`explicit_ownership_splits_and_ordinary_dividends`. That scope without its
schedule is rejected. Parent/child identity, prior-close eligibility, advance
knowledge and whole-share delivery must be explicitly reviewed. Existing
unverified saved scenarios are not automatically admitted to strategy scoring.

In the opt-in mode, the ledger supplies cash/positions for every fill. Corporate
actions precede opening fills and use opening component values for economic
basis allocation. Affected queued orders are canceled, inherited stops use a
documented proportional opening-value floor, and affected feature histories
restart with a 200-session new-entry warmup. Holding age is inherited from the
oldest lot. Existing destination holdings remain separate ledger lots. Genuine
splits and ordinary dividend rights can apply to inherited whole holdings;
unresolved fractional entitlement chains are rejected. Dividend issuer dates
do not automatically become spendable cash availability in this mode.

Fixed rights cannot fund purchases. Whole/fractional ownership contributes to
exposure and beneficial position counts; passive distributions above an entry
cap block new buys. Reports distinguish cash, dividend rights and fractional
claims. Internal accounting replay reconstructs the journal and risk bounds;
external risk diagnostics additionally compare used quotes with complete actual
raw data and dated aliases. Neither process certifies source declarations or
reruns strategy selection. Existing action scopes/run paths retain the earlier
behavior; exact legacy-result preservation still needs execution regression.

Verification in this increment is **compilation and code/diff review only**.
No unit tests, saved-case replay, regression replay or strategy return study
was run. Earlier 111-unit-test/84-mechanics-check evidence belongs to the
preceding component version and is preserved, not relabeled as integration
evidence. Windows integrated execution and Pi execution remain unverified.
New purchases, network requests, account calls, orders, package installations
and reserved 2024-2025 candle use were zero.

**Next engineering work:** focused integration tests and regression replays,
then remaining free-source entitlement/delivery/payment and price review,
before expanding the basket. Broader strategy scoring is still blocked.
The [paper-readiness checklist](docs/paper_trading_readiness.md) records the
remaining data/simulation, investment-acceptance, paper-execution and owner
activation gates. Earlier candidates fail the approved investment goal; a
paper launch date is not established. No owner card, purchase, download or
risk-setting change is required now. Personal paper-risk approval, account/
startup recovery review and explicit activation remain due before paper orders.

## Ownership integration verification and source review: 2026-10-27

The [verification results](docs/ownership_verification_results.md) record a
fresh Windows run of **183 focused tests: 45 new integration, nine new
evidence-review and 129 existing related tests**, all passing without skips.
Fresh replays match **all 36 financial cases and all 36 daily-risk cases**
exactly; the standalone component replay passes **84 checks across seven
cases**. Prior artifacts are preserved. These checks are not a larger strategy
search or a revised return estimate. Pi execution and the full optional-ML
suite were not run.

Testing found that the external ownership-risk replay could accept corrupted
headline metrics even after reconciling curves and source prices. It now
checks capital, return, drawdown, exposure, P&L, trade statistics and final
position values against the ledger. The new tests cover missing/false
evidence, delayed payments, fractions, stops/holding ages, order cancellation,
warmup, later splits/dividends, serialization and report corruption.

The [pinned evidence review](docs/ownership_evidence_summary.json) revalidated
20 primary sources and the saved collection. Advance planned terms are
supported for initial Under Armour Class C and Arconic 2020, but they do not
certify actual delivery, entitled holders or spendable cash. Ten required
events remain missing from provider responses, 77 out-of-interval event
references remain quarantined, and child/OTC prices and complex allocations
remain incomplete. No mechanics case was automatically approved for scoring.
Three bounded free public-web tool calls established no missing Alcoa filing
date. Purchases, subscriptions changed, broker/account calls and orders were
zero; no reserved 2024-2025 prices were used.

**Next engineering work:** prepare a concrete bounded free-data pilot proposal
that distinguishes source facts from any research timing/valuation assumptions,
defines sensitivity checks and exclusions, and identifies collectable prices.
Any change to today's verified-evidence contract needs separate review, not
silently weakened flags. Broader scoring remains blocked. No owner action or
personal paper-risk configuration is due now; present the concrete research
proposal for review when ready. Paper activation remains a separate gate.

## Free-data pilot proposal: 2026-10-27

The [concrete pilot proposal](docs/free_data_pilot_proposal.md) and
[non-executable input specification](docs/free_data_pilot_proposal.json) define
cached-source qualification for AAPL, JPM and CBRE, plus SPY market context,
over `[2016-01-01, 2024-01-01)`. The four saved streams contain 2,012 observed
sessions each (8,048 rows total). Complete observed coverage does not certify
full-period security identity, actions or executable performance. Provider
event inventories and the imported CBRE classification still require review.

This convenience sample is for data engineering, not an unbiased investment
universe or replacement for the retained 506-row register. It cannot meet the
approved five-instrument acceptance requirement and schedules zero strategy
runs or ML training. The existing eight-arm market-wide study remains scoped
and blocked; a fixed 2016-cohort alternative requires separate scope review.

The proposal distinguishes primary-source facts from unapproved research
conventions: second actual session after a date-only announcement; modeled
cash availability after an issuer payable date; delayed/no-credit sensitivities;
nominal rights versus spendable cash; causal split views. Do not relabel these
assumptions as confirmed broker delivery/payment or weaken today's adapter
evidence gates. Difficult merger, distribution, fractional and OTC cases
remain explicit blockers; no survivor-only replacement or event-driven
censoring is authorized.

**Next engineering work:** qualify the four cached identity/action histories,
produce a fact/assumption/gap matrix, then a finite free-source collection
list if required. This step needs no new HTTP requests or owner configuration.
Owner review is needed before proposed assumptions or a changed strategy
universe are used for performance research. No personal risk settings,
purchase, card or paper activation is due. This increment is documentation
only; no tests, new backtests, downloads or API calls were run.

## Cached four-history qualification: 2026-10-27

The [qualification report](docs/free_data_pilot_qualification.md),
[pinned summary](docs/free_data_pilot_qualification_summary.json) and
[95-row action matrix](docs/research_data/free_data_pilot_actions.csv) now
complete the pilot's cached-source review. The offline command is
`python -m backtesting.pilot_qualification --output data/reports/a_fresh_directory`.
It preserves original evidence, refuses changed hashes/existing outputs,
reconstructs actual bars from saved payloads (including the documented CBRE
boundary translation) and uses the existing calendar/OHLCV validator.

All four streams' 8,048 candles pass with no errors, volume warnings or
zero-volume rows. Twelve primary files and nine explicit source checks were
revalidated. The matrix covers 94 provider events plus the independent CBRE
rename, with six supported primary event cross-checks: Apple's four 2020
dividend announcements, its split, and CBRE's rename. Those dividend checks
do not independently establish every ex-date/entitlement or broker credit.

Forty-eight of 93 provider dividend records omit payable dates. A saved Apple
announcement supplies one omitted field in the new matrix; remaining absent
terms are not inferred. SPY has no provider record in 2016 Q1, 2018 Q2 and
2023 Q4; these are investigation targets, not proof of an exact missing count
or permission to fabricate dividends. CBRE's 2016 REIT marker is in the saved
original fund filing; conflicting later classification evidence needs review,
not a silent edit to the source register.

Zero full-period histories are approved for scoring. Modeled knowledge/cash
timestamps remain explicitly proposed and unapproved. No strategy backtest,
unit-test suite, payment-delay replay, ML training, network call, purchase,
account/broker request, order or reserved-price read was performed. Earlier
unit/regression evidence is preserved, not relabeled as testing this new runner.

**Next engineering work:** the [finite primary-source collection list](docs/free_data_pilot_source_collection.json)
defines 12 discovery targets, capped at 12 public discovery tool calls and
40 direct public-document GET attempts, without automatic retries, paid
fallback, credentials or new stock-price requests. Download URLs still need
primary-domain review. Stop at access/payment requirements or the cap and
retain unresolved gaps. No owner configuration is due for that collection;
review of modeled timing and any changed strategy scope is needed before
later performance use. Personal paper-risk settings/activation remain separate.

## Bounded public-document collection: 2026-10-27

The [collection/reconciliation results](docs/pilot_public_source_results.md)
and [pinned review](docs/pilot_public_source_review.json) record 11 saved
public source files: six substantive documents and five index pages. Five
public discovery tool calls and 18 direct GET attempts stayed within the
12/40 limits. The first six direct attempts failed in the sandbox; explicit
reexecution after approved network permission was counted separately, not
hidden as automatic retries. The final JPMorgan issuer-linked history host
returned HTTP 403 and all acquisition stopped. No paid fallback, account
access, credential use or new candle requests occurred.

The [66-row primary reconciliation](docs/research_data/pilot_collected_dividends.csv)
covers 32 Apple declarations, 32 SPY distributions and two dated JPMorgan
releases. All 32 Apple nominal amounts match the provider cross-references;
the issuer table does not independently supply ex-dates. SPY's workbook
confirms omitted March 18, 2016, June 15, 2018 and December 15, 2023 events.
The last has a January 31, 2024 payable date; this is source metadata, not
permission to read holdout prices or credit cash in 2023. One shared SPY
amount differs by $0.0000001 per unit; both displayed values remain visible.
Blank capital-gain cells are not silently changed to zero.

Primary sources supply 32 of the original 48 missing provider payable fields,
including one Apple field already known from the preceding audit. Sixteen
remain unresolved. CBRE's 2016/2023 issuer filings support its common-share
listing, alias lineage and stated absence of common cash dividends; historical
REIT tax subtype and other action completeness are not automatically certified.

The offline command is:

```powershell
python -m backtesting.public_source_review --output data/reports/a_fresh_directory
```

It checks pinned acquisition/source files and reconstructs the comparisons without HTTP. The new helpers have
executed on Windows; unit-test suites, Pi execution and strategy performance
were not run. No previously reported unit-test totals are relabeled for them.
Purchases, subscription changes, broker/account calls, orders and reserved
2024-2025 price use were zero. Proposed research timing/scoring flags stay false.

**Next engineering work:** focused offline tests for collector/parser bounds,
access stops, source-format changes, joins, precision and date limits. Mock
network behaviour. Keep remaining source acquisition separately scoped rather
than silently resuming the stopped batch. No owner setup or risk-limit change
is due; proposed timing and any narrowed strategy scope require review before
their later use in performance research. Paper activation remains separate.

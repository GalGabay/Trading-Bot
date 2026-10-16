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
                         │ Retry / recover          │
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
   YES       NO
   │          │
 Track      Retry
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

---

# 29. Phase 14 — Machine Learning

Only after the deterministic strategy and backtester work.

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

## Phases 0–9 and historical research / 2026-10-16

### Implemented
- Paper-only Alpaca client, calendar-aware market-data validation, and SQLite audit storage.
- Deterministic `technical_v1` features and `trend_following_v1` strategy with a reusable strategy interface.
- Append-only signal recording for reproducible decisions.
- Single-symbol backtesting with causal feature access, next-candle fills, configurable fees/spread/slippage, equity, drawdown, and the Section 17 metrics.
- A historical downloader with feed/adjustment provenance, checksum manifest, strict interval review, and a local three-scenario backtest command.
- Expanding-year walk-forward calibration of a declared strategy threshold grid, with later-year evaluation kept separate from parameter selection.

### Files changed
- `app/broker/`, `app/data/`, `app/ai/`, `app/strategy/`, `backtesting/`, `tests/`, `requirements.txt`, and `README.md`.

### Tests
- 49 unit tests pass on Windows, covering the broker wrapper, validation, storage, features, strategy, simulation, metrics, and dataset integrity.

### Validation
- Read-only Alpaca historical-data and calendar checks passed during Phase 4.
- Downloaded 6,540 adjusted AAPL SIP 15-minute regular-session bars for 2021. A February–December 2021 single-symbol case study returned +1.22% optimistic, +0.28% base, and -2.87% pessimistic on a $100,000 simulated account. This is an illustrative in-sample case study, not evidence of a robust strategy.
- Downloaded 32,600 adjusted AAPL SIP 15-minute bars for 2019–2023 and ran two expanding yearly folds. The 2022/2023 base-cost test returns were +0.20%/+0.46%; pessimistic-cost returns were -2.12%/-2.49%. Both folds selected the narrow candidate from earlier years. A separate 2018–2022 request was rejected after 50 unobserved scheduled intervals clustered on May 2–3, 2018.
- No order has been submitted, modified, or canceled by this implementation.

### Known limitations
- The project has not yet run its automated tests on Raspberry Pi OS.
- Phase 9 has been exercised with the five-year AAPL dataset but has not yet received new unit tests.
- The current backtester handles one symbol and one long position; multi-symbol portfolios, a separate risk policy, point-in-time historical universes, and ML training remain unimplemented.

### Next step
- Run the walk-forward workflow on several full years, then obtain point-in-time universe data and a multi-symbol portfolio engine before making market-wide claims or training a predictive model.

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

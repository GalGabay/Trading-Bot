# Glossary & Learning Guide --- AI-Enhanced Alpaca Trading Bot

**Purpose:** A plain-language companion to the project plan for a Python
algorithmic trading bot using Alpaca Paper Trading, SQLite, and
Raspberry Pi 3B. This is educational documentation, not investment
advice. Backtests and paper results do not guarantee future
profitability.

## How to use this guide

Keep the English term as written because it is the term you will see in
code, APIs, and logs. Read in order: market data → database →
indicators/features → strategy → backtesting → risk → orders → ML →
deployment.

## Table of contents

1.  Big-picture concepts
2.  Market and price data
3.  Phase 5 --- SQLite tables
4.  Phase 6 --- Features and indicators
5.  Strategy and portfolio
6.  Backtesting and metrics
7.  Risk management
8.  Orders and execution
9.  Machine learning
10. Reliability and deployment
11. Common confusions and workflow example

------------------------------------------------------------------------

# 1. Big-picture concepts

## Algorithmic trading bot

Software that analyzes market data using programmed rules and/or models
and may submit orders. It is not inherently profitable and does not need
AI to be algorithmic.

## Trading strategy

A defined set of rules for deciding when to consider a trade. Example:
consider buying only when price is above EMA200 and EMA20 is above
EMA50. A strategy proposes; risk controls decide whether it is allowed.

## Deterministic / rule-based system

A system that produces the same result from the same inputs,
configuration, and state. It is easier to test and debug than an opaque
or nondeterministic process.

## Quantitative trading

Trading decisions based on numerical data, statistics, and mathematical
rules.

## Market data

Information about the market: prices, volume, quotes, trades,
timestamps, and sometimes news or corporate actions.

## Historical data

Past observations used for feature calculation, research, model
training, and backtesting.

## Live / recent data

Newly arriving data used by a running system. Using live data does not
mean the bot is permitted to place real-money orders.

## Paper Trading

A broker-provided simulated trading environment. Useful for testing
order workflows without intentionally risking real capital. Paper
results can differ from live results due to liquidity, fills, spreads,
slippage, latency, and market impact.

## Live trading

Submitting orders that can use real money. It should be a separately
controlled mode, not enabled casually during early development.

## Broker / brokerage

A financial service that holds an account and routes or executes orders.
Alpaca is the broker API in this project; the bot communicates with it
but does not itself hold securities.

## API

Application Programming Interface: a defined way for programs to
communicate. The Alpaca API lets the bot request account/market data and
submit, query, or cancel orders.

## API client

Code that wraps API calls, authentication, responses, and errors in one
place.

## Rate limit

A cap on how frequently an API can be called. Respect limits and use
controlled retries rather than retrying in a tight loop.

## Event loop / main loop

The recurring flow of checking market state, obtaining and validating
data, calculating features, generating signals, checking risk, managing
orders, saving state, and waiting for the next cycle.

## Separation of concerns

Each module has one clear responsibility. The strategy proposes; risk
approves or rejects; the order manager communicates with Alpaca.

## Research vs. production

Research code supports experiments and model training. Production code
runs the controlled bot. Keep them separated so experimental changes
cannot silently affect the running system.

------------------------------------------------------------------------

# 2. Market and price data

## Symbol / ticker

The short identifier for an instrument, such as `AAPL` or `MSFT`.

## OHLC

Four prices describing a bar: **Open** (first price in the interval),
**High** (highest), **Low** (lowest), and **Close** (last). Combined
with volume, this is OHLCV.

## Volume

The amount of an instrument traded during an interval. It is not
necessarily the same as dollar value traded.

## Candle / bar

A summary of trading over an interval, such as 15 minutes or one hour.
Usually contains timestamp, symbol, open, high, low, close, volume, and
timeframe. A provider may timestamp the start or end of a bar, so
confirm the convention.

## Timeframe / bar interval

The duration represented by one candle. EMA20 on 1-hour candles differs
from EMA20 on 15-minute candles.

## Timestamp

The date/time attached to an observation or event. Correct ordering and
interpretation are essential.

## UTC / timezone

UTC is a common reference timezone. Store timestamps consistently and
convert to market-local time when interpreting sessions. Mixing timezone
conventions can shift signals.

## Trading session

A period when a market is open. Regular US hours differ from pre-market
and after-hours sessions. The bot must know which sessions its strategy
and order types support.

## Market holiday

A day when the exchange is closed or follows a special schedule. No
candle on a holiday is not automatically a data outage.

## Bid and ask

**Bid** is the best displayed buying offer; **ask** is the best
displayed selling offer. Buyers often pay near the ask and sellers
receive near the bid, depending on execution.

## Bid-ask spread

Ask minus bid. If bid is \$99.98 and ask is \$100.02, the spread is
\$0.04. Spread is an implicit trading cost.

## Quote

A market-data record describing bid/ask prices (often sizes and
timestamp). A quote differs from a trade, which records an executed
transaction.

## Trade (market-data meaning)

A reported market transaction with price, quantity, and timestamp. Do
not confuse it with an order submitted by your bot.

## Liquidity

How easily an asset can be traded without materially moving its price.
Volume is useful but does not fully describe liquidity.

## Data validation

Checks that data is plausible and usable. Examples: timestamps ordered
and consistent; no unintended duplicate/missing bars; prices positive;
`High >= max(Open, Close, Low)`; `Low <= min(Open, Close, High)`; volume
nonnegative; holidays and session boundaries handled. Validation catches
known error classes but cannot prove data is perfect.

## Missing data / missing candle

An expected observation is absent. It might be a market closure,
provider gap, or retrieval failure. Distinguish the cause rather than
blindly filling every gap.

## Duplicate candle

The same symbol/timeframe/bar appears more than once. Duplicates can
distort indicators and backtests.

## Corporate action

An event such as a split, dividend, or merger that affects prices or
share counts. Know whether historical prices are adjusted and keep the
dataset treatment consistent.

## Survivorship bias

A historical test includes only companies that survived or are
successful today, omitting failed or delisted companies. This can make
results too optimistic.

------------------------------------------------------------------------

# 3. Phase 5 --- SQLite database tables

## SQLite

A lightweight relational database stored in a file. It is convenient for
a single-device prototype without a separate database server, though
write concurrency and operational needs still matter.

## Database / relational database

A structured data store. A relational database organizes data into
tables and can express relationships using IDs and constraints.

## Table, row, column

A table stores a category of records; a row is one record; a column is
one field.

## Primary key (`id`)

A field (or combination of fields) that uniquely identifies a row.

## Foreign key

A field that references a row in another table. For example,
`fills.order_id` can reference the order that produced the fill.

## Schema

The structure of tables, columns, data types, constraints, and
relationships. Changes should be intentional and tested.

## `candles`

Stores market bars: timestamp, symbol, OHLC, volume, timeframe. This is
the raw data foundation for indicators and strategies. Use a uniqueness
rule to avoid duplicate bars.

## `features`

Stores calculated values such as EMA, RSI, ATR, returns, or volume
ratios. Keep formulas, lookbacks, timeframe, and code/version traceable.

## `signals`

Stores strategy outputs such as BUY, SELL, or HOLD, plus timestamp,
symbol, strategy/version, score, and reason. A signal is not an order
and does not prove a trade occurred.

## `orders`

Stores order requests and statuses: local ID, client order ID,
timestamp, symbol, side, quantity, order type, status, and broker order
ID. Useful for recovery and audit.

## `fills`

Stores actual executed portions of orders: order reference, timestamp,
symbol, quantity, and price. One order can have multiple fills.

## `positions`

Represents current holdings in each instrument, commonly quantity,
average entry price, and unrealized P&L. Reconcile local positions with
the broker.

## `portfolio_snapshots`

Periodic snapshots of account state, such as equity, cash, buying power,
exposure, and P&L. Useful for charts and historical comparisons.

## `strategy_runs`

Records each strategy/backtest run, including configuration, time range,
version, and results so experiments can be reproduced.

## `model_predictions`

Stores model outputs such as prediction, confidence/probability, model
version, timestamp, and symbol. Helps audit decisions and later compare
predictions with outcomes.

## `system_events`

Structured records of important events: startup, API errors, rejected
orders, reconciliation mismatches, risk triggers, kill-switch
activation, or data warnings.

## `client_order_id`

An identifier generated by the bot and sent with an order. A stable
unique ID helps identify an order after a timeout and prevents blind
duplicate submissions.

## `alpaca_order_id`

The broker's order identifier, used to query status and history.

## Database transaction

A group of database operations treated as one logical unit, helping
avoid partially written related state.

## Persistence

Saving state so it survives process restarts. In-memory variables
disappear when the process stops; persisted records can be recovered.

## Migration

A controlled database-schema change, such as adding a column. Test
migrations against existing data as well as a fresh database.

## Reconciliation

Comparing local orders, fills, positions, and balances with broker state
and investigating differences. Broker state is essential to know what
actually happened externally.

------------------------------------------------------------------------

# 4. Phase 6 --- Feature engineering and indicators

## Feature engineering

Turning raw data into numerical inputs a strategy or ML model can use. A
feature may be an indicator, return, or volume statistic; features are
not automatically profitable signals.

## Technical indicator

A formula derived from market data that summarizes aspects of recent
price/volume behavior. Indicators lag or generate false signals and
cannot predict with certainty.

## Lookback period

The number of past observations used in a calculation. "20 periods"
means 20 candles, not necessarily 20 calendar days.

## Trend

The general direction or persistence of prices over a chosen horizon.

## EMA (Exponential Moving Average)

A moving average that gives more weight to recent observations than
older ones. It reacts faster than a comparable simple moving average but
still lags price.

### `EMA20`, `EMA50`, `EMA200`

EMA values calculated using periods 20, 50, and 200. EMA20 is
shorter-horizon, EMA50 medium-horizon, EMA200 longer-horizon. Meaning
depends on the candle timeframe. Price above EMA200 may be a trend
filter, not a guaranteed buy signal.

## SMA (Simple Moving Average)

The arithmetic mean over a fixed window, giving each observation in the
window equal weight.

## MACD (Moving Average Convergence Divergence)

A trend/momentum indicator commonly based on the difference between a
faster EMA and a slower EMA, with a signal line. The histogram commonly
shows MACD minus its signal line. It can describe momentum changes but
may give false signals in choppy markets.

## ADX (Average Directional Index)

An indicator of trend strength, not direction by itself. High ADX
suggests a stronger trend under its convention; it does not mean the
price is rising. Direction is often assessed with related +DI/-DI values
or other features.

## Momentum

A measure of recent price movement or its persistence over a selected
horizon.

## RSI (Relative Strength Index)

A bounded momentum oscillator, commonly 0--100, based on relative recent
gains and losses. Levels such as 30/70 are conventions, not automatic
buy/sell commands; RSI can stay elevated/depressed during strong trends.

## ROC (Rate of Change)

The price change over a lookback period, often expressed as a
percentage. Positive means the reference price is higher than the
comparison price; negative means lower.

## Stochastic Oscillator

A momentum indicator comparing the close with the recent high-low range,
often on a 0--100 scale. Extreme readings can persist in strong trends
and do not guarantee reversal.

## Volatility

How much prices or returns vary. High volatility means larger
fluctuations, not a direction.

## ATR (Average True Range)

A volatility indicator based on true range, which accounts for the
high-low range and gaps relative to the previous close. ATR is normally
in price units, not a percentage by default. It can help scale stops but
does not predict direction.

## Bollinger Bands

A moving average with upper/lower bands commonly offset by a multiple of
standard deviation. Bands widen as measured volatility rises and
contract as it falls. Touching a band does not guarantee reversal.

## Historical volatility

A statistical measure, often standard deviation of past returns over a
window. Annualization conventions matter; past volatility does not
guarantee future volatility.

## Volume SMA

A simple moving average of volume over a selected window, used as a
baseline for recent activity.

## Volume Ratio

Current volume divided by a baseline, often Volume SMA. A value of 1.5
means 1.5 times the baseline if that is the defined formula. Document
the exact windows and timing.

## OBV (On-Balance Volume)

A cumulative volume indicator that adds volume on up-closing bars and
subtracts it on down-closing bars under a common definition. It
summarizes price direction alongside volume; it does not directly
measure institutional activity.

## `return_1`, `return_5`, `return_20`

Returns over one, five, or twenty bars. One common formula is
`(current_price / prior_price) - 1`. Decide whether values are fractions
(0.02) or percentage points (2.0) and document the convention.

## `distance_from_ema20`, `distance_from_ema50`, `distance_from_ema200`

Features describing price distance from an EMA. A relative formula might
be `(close / EMA) - 1`; a raw price difference is another option. The
implementation must define which one it uses.

## Normalization / scaling

Transforming features to comparable numerical scales. Fit scaling
parameters only on training data, then apply them to later data to avoid
leakage.

## Correlated features

Features that carry overlapping information. Adding many similar
indicators can increase complexity and overfitting without adding much
predictive value.

## Warm-up period

The initial part of data where an indicator lacks enough prior
observations. For example, EMA200 needs a substantial history. Avoid
trading on undefined or incomplete values.

## NaN / missing feature

A value is undefined or unavailable, often because the lookback window
is incomplete or data is missing. Handle it explicitly rather than
silently treating it as zero.

------------------------------------------------------------------------

# 5. Strategy and portfolio concepts

## Signal

A strategy's output, such as BUY, SELL, HOLD, REDUCE, or CLOSE. Store
the reason and timestamp. A signal is not an order or a fill.

## BUY / SELL / HOLD

BUY considers increasing/opening a long position; SELL may reduce/close
a long position; HOLD means no change now. Define SELL carefully---do
not accidentally implement short selling if the first system is intended
to be long-only.

## REDUCE / CLOSE

REDUCE decreases a position; CLOSE exits it completely. Define behavior
consistently across strategy, risk, and order manager.

## Signal score / confidence

A numerical score of strength or model confidence. A score of 0.8 is not
automatically an 80% probability unless defined and calibrated that way.

## Entry rule / exit rule

An entry rule determines when to consider opening a position. An exit
rule determines when to reduce or close it, e.g. trend reversal, stop
loss, take profit, or maximum holding time.

## Stop loss

A rule/order intended to exit when price reaches a trigger. It does not
guarantee a maximum loss because gaps and slippage can produce worse
fills.

## Take profit

A rule/order intended to exit after a target gain. Actual execution can
differ from the target price.

## Maximum holding time

A rule to exit after a specified duration or number of bars.

## Universe / trading universe

The set of symbols the strategy may analyze or trade. Keep it deliberate
and avoid choosing historical constituents using future knowledge.

## Long-only

A strategy that buys assets and does not open short positions. This
simplifies some logic but does not remove market risk.

## Portfolio

The account's cash and positions considered together.

## Position

The current holding in one instrument, commonly described by quantity,
average entry price, market value, and P&L.

## Cash / equity / buying power

**Cash** is the cash balance under broker rules. **Equity** is account
value including positions. **Buying power** is what the broker currently
allows the account to use for purchases. These are related but not
interchangeable.

## Exposure

How much the portfolio is invested in positions. Gross exposure sums
absolute position values; net exposure accounts for direction. Define
which one risk limits use and whether pending orders count.

## Unrealized P&L / realized P&L

Unrealized profit/loss is on open positions based on current valuation.
Realized P&L relates to completed trades. Accounting and costs should be
handled consistently.

## Rebalancing

Adjusting holdings toward target allocations or rules. Rebalancing can
generate trades and costs.

------------------------------------------------------------------------

# 6. Backtesting and metrics

## Backtest

A simulation of strategy decisions over historical data. It is not proof
of future profitability; credibility depends on data quality, timing,
costs, and execution assumptions.

## Backtesting engine

Processes historical bars in chronological order, calculates features,
invokes strategy and risk rules, simulates orders/fills, updates
portfolio state, and calculates metrics.

## Simulated order / simulated fill

An order or execution modeled by the backtester rather than sent to a
broker. Avoid assuming every order fills at the exact candle close.

## Equity curve

A time series of portfolio equity through a test period.

## Drawdown / Maximum Drawdown (MDD)

Drawdown is a decline from a previous portfolio peak. If equity falls
from \$10,000 to \$8,500, that is a 15% drawdown from that peak. Maximum
drawdown is the largest peak-to-trough decline in the measured period.

## Total return

Overall percentage change in portfolio value during the period, with
deposits, withdrawals, dividends, and costs handled consistently.

## Annualized return

A return expressed as a yearly rate for comparing periods of different
lengths. State the calculation convention.

## CAGR (Compound Annual Growth Rate)

The constant yearly growth rate that would turn starting value into
ending value over the period. It smooths the path and does not show
volatility.

## Volatility (portfolio metric)

Statistical variation of portfolio returns. The observation frequency
and annualization method matter.

## Sharpe Ratio

A measure comparing average excess return with return volatility under a
chosen convention. It can be misleading with short samples, unusual
return distributions, or unrealistic simulations.

## Sortino Ratio

Similar to Sharpe but uses downside deviation rather than total
volatility in the denominator. Its meaning depends on the target return
and calculation method.

## Win rate

Percentage of closed trades that were profitable. A high win rate alone
does not prove a strategy is profitable.

## Profit factor

Gross profits from winning trades divided by absolute gross losses from
losing trades. Define whether costs are included.

## Average trade / average win / average loss

Average result per trade, and average results among winning and losing
trades. State whether measured in dollars, percent, or another unit and
whether costs are included.

## Largest win / largest loss

The largest individual winning/losing trade in the sample. Historical
extremes do not bound future outcomes.

## Average holding period

Average duration or number of bars a position is held; define the unit.

## Slippage

Difference between expected/reference price and actual execution price.
If a buy expected at \$100 fills at \$100.08, adverse slippage relative
to that reference is \$0.08/share.

## Commission / fees

Explicit trading costs. Even if commission is zero, spread and slippage
can still matter.

## Execution delay / latency

Time between decision/order submission and response or execution. Price
may change during the delay.

## Look-ahead bias

Using information that would not have been available at decision time.
Example: use a candle's final close to generate a signal and pretend to
buy at that close even though the close was not yet known.

## Data leakage

Information from outside the allowed training/decision period influences
a feature or model. Look-ahead bias is one form of leakage. Leakage can
happen in feature calculations, scaling, labels, or splits.

## Overfitting

Fitting historical noise instead of a durable pattern. Repeatedly tuning
until a backtest looks amazing is a common cause.

## Parameter sensitivity

Testing whether small parameter changes cause large performance changes.
A strategy that works only at one exact setting may be fragile.

## Stress test

Testing adverse conditions: higher slippage, delayed execution, missing
candles, API downtime, or lower liquidity.

## Out-of-sample (OOS) test

Evaluation on data not used for fitting or tuning. It is more honest
than in-sample evaluation but still cannot guarantee future performance.

## Train / validation / test split

Separates model fitting, model selection, and final evaluation. For
financial time series, respect chronology; random shuffling can leak
future patterns into the past.

## Walk-forward validation

Repeatedly train/tune on an earlier window, test on the next unseen
window, then move forward. This better imitates the passage of time.

## Market regime

A broad market condition, such as trending, sideways, calm, or unusually
volatile. Regime labels are imperfect and may be obvious only in
hindsight.

## Baseline

A simple reference strategy/system used for comparison. The non-ML
rule-based strategy is a useful baseline for evaluating an AI filter.

------------------------------------------------------------------------

# 7. Risk management

## Risk management

Rules that limit losses and exposure. It is separate from the strategy:
a signal can be rejected because it violates a risk rule.

## Risk per trade

Planned amount of portfolio value at risk if the trade exits at its stop
under sizing assumptions. It is not a guaranteed maximum loss.

## Position sizing

Calculating quantity using equity, allowed risk, entry/stop distance,
position caps, exposure limits, buying power, and other constraints.

## Stop distance

Price difference between entry and stop. A wider stop generally means
fewer shares for the same planned dollar risk.

## Example: risk-based sizing

Suppose equity is \$10,000 and the planned risk allowance is 1% (\$100).
Entry is \$50 and stop is \$48, so planned risk is \$2/share. Simple
quantity = \$100 / \$2 = 50 shares, before fees and other limits. Actual
quantity may be lower. A stop does not guarantee the realized loss is
exactly \$100.

## Maximum position size

Cap on one instrument's position, expressed as shares, dollars, or
percentage of equity.

## Maximum exposure

Cap on total portfolio exposure. Define gross/net exposure and how
pending orders are counted.

## Daily loss limit

Rule to stop new risk after losses reach a threshold during a day.
Define how daily starting equity and realized/unrealized losses are
measured.

## Drawdown limit

A threshold from a defined high-water mark or reference value that
pauses trading or triggers safeguards. Define the reference and reset
rules.

## Kill switch

Mechanism that blocks new trading when critical safety conditions occur:
unexpected account state, repeated API failures, corrupted local state,
excessive losses, stale data, or reconciliation failure. Decide
separately whether to cancel open orders or close positions.

## Hard risk limit

A constraint that neither strategy nor AI can override.

## Correlation risk

Several different positions may move together, so many symbols do not
automatically provide diversification.

## Liquidity risk

Risk that a position cannot be entered/exited promptly at a reasonable
price.

## Operational risk

Risk from software, data, infrastructure, credentials, configuration, or
process failures.

------------------------------------------------------------------------

# 8. Orders and execution

## Order

A request to buy or sell under specified conditions. It can be accepted,
rejected, partially filled, filled, canceled, or remain open. An order
is not proof that a trade occurred.

## Side / quantity

Side is buy or sell. Quantity is the number of shares/units requested,
subject to broker and instrument rules.

## Market order

Prioritizes prompt execution at available prices, not a guaranteed
price.

## Limit order

Sets the worst acceptable price. Buy limit sets a maximum buy price;
sell limit sets a minimum sell price. It may never fill.

## Stop order

Becomes active when a trigger condition is met. A stop-market order may
execute worse than its trigger in a fast market.

## Order status

Broker-reported state such as new/open, partially filled, filled,
canceled, expired, or rejected. Exact labels vary; handle unknown states
safely.

## Submitted / accepted / filled

Submitted means the bot sent the request; accepted means the broker
accepted it; filled means some or all quantity executed. These are
separate states.

## Partial fill

Only part of the requested quantity has executed. Track filled and
remaining quantity separately.

## Fill

An execution of a quantity at a particular price and time. An order can
produce multiple fills; use them for accurate position and P&L
accounting.

## Rejected order

The broker declined the order, perhaps because of invalid parameters,
insufficient buying power, unsupported conditions, or account
restrictions. Record the reason; do not retry blindly.

## Cancel request

A request to cancel an order. It is not proof of cancellation: the order
may fill while the request is in flight. Confirm the resulting status.

## Time in force (TIF)

How long an order should remain active, such as day-only or
good-till-canceled where supported. Use only documented combinations
supported by the broker.

## Market-hours check

Check that the session supports the intended order. Holidays, special
schedules, and extended-hours rules make fixed-clock assumptions unsafe.

## Order manager

The component that constructs, submits, tracks, cancels, and recovers
orders. Centralizing this behavior helps prevent duplicates and handle
partial fills.

## Idempotency

Repeated operations should not accidentally repeat an external effect.
If an order request times out, query Alpaca using the stable client
order ID before retrying; the broker may already have accepted it.

## Timeout

A request did not return promptly. It does not prove the broker failed
to process it.

## Retry with backoff

Retry after controlled delays rather than hammering the API. Order
submission must be protected by idempotency and broker-state checks.

## Paper fill model

The simulation rules determining whether/when an order fills in paper
trading. They do not perfectly reproduce real queues, liquidity, or
market impact.

## Crash recovery

After a crash/restart, load configuration and local state, connect to
the broker, reconcile orders/positions, validate data and system health,
and only then decide whether trading can resume.

------------------------------------------------------------------------

# 9. Machine learning and AI

## AI (Artificial Intelligence)

A broad field of systems performing tasks associated with intelligent
behavior. Here, the practical component is numerical prediction or trade
filtering.

## ML (Machine Learning)

A subset of AI where a model learns patterns from examples. It can learn
noise, so it needs time-aware evaluation.

## Model

A fitted mathematical/statistical object that maps features to a
prediction or score. It is not the whole trading system and cannot
bypass risk limits.

## Training

Fitting model parameters using a training dataset. Training performance
is not an unbiased estimate of future performance.

## Inference

Using a trained model to produce output for new data. Inference is often
much lighter than training.

## Label / target

The outcome the model is trained to predict, e.g. whether return over
the next N bars exceeds a threshold. Define horizon, price timing, and
cost assumptions precisely.

## Feature / input variable

A value supplied to a model, such as RSI, ATR, distance from EMA200,
volume ratio, or returns. It must use only information available at
prediction time.

## Prediction

The model's output: class, probability, estimated return, or risk score.
It is not a guarantee.

## Probability / confidence

A probability-like output is truly calibrated only if tested as such.
"Confidence" is often used loosely and must be defined.

## XGBoost

A gradient-boosted decision-tree library often used for
structured/tabular data. It can suit indicator/return features but still
requires careful validation and versioning.

## Gradient boosting

An ensemble method that adds models sequentially to improve the combined
prediction; XGBoost commonly uses decision trees.

## Classification / regression

Classification predicts a category; regression predicts a numerical
value such as future return.

## Class imbalance

One target class is much more common than another. Accuracy can be
misleading if the model mostly predicts the common class.

## Model version / feature version

A model version identifies a trained artifact and metadata such as
training period, target, feature set, parameters, and validation
results. A feature version identifies the formulas/definitions used to
create inputs.

## Data drift / model drift

Data drift means input distributions change. Model/performance drift
means predictive quality changes. Monitor inputs and realized outcomes.

## AI filter

The strategy proposes a candidate trade; ML helps accept/reject/rank it.
It must not override hard risk limits. Compare it to the same strategy
without ML.

## LLM (Large Language Model)

A model that processes and generates language. It may help summarize
text but is not automatically a reliable numerical market predictor and
should not control core execution or risk decisions.

## Sentiment analysis

Estimating tone in text such as news. Sentiment can be noisy and
timestamps must prevent use of news before publication.

------------------------------------------------------------------------

# 10. Reliability and deployment

## Logging

Writing diagnostic records. Logs should help explain the data, signal,
risk decision, order, and broker response. Never log API secrets.

## Structured event log

Consistent event fields such as timestamp, severity, component, symbol,
type, and message; easier to search than arbitrary text.

## Monitoring / alert / health check

Monitoring observes system state; an alert notifies about something
needing attention; a health check tests whether a component is
functioning. A live process can still be unhealthy if data is stale or
the broker is unreachable.

## FastAPI

A Python web framework for endpoints and a read-only dashboard/health
API. Protect it; do not expose trading controls casually.

## Jinja2

A template engine for generating HTML pages from data and templates.

## HTMX

A tool for updating parts of a web page with server-rendered HTML
without building a large client-side JavaScript app. It is presentation
technology, not trading logic.

## Dashboard

A UI for system health, portfolio, positions, orders, signals, P&L, and
risk. A read-only dashboard is safer initially.

## Raspberry Pi 3B

A low-power single-board computer suitable for API calls, SQLite,
indicators, rules, lightweight inference, and monitoring. Heavy training
and large backtests are better on a PC/cloud.

## Ubuntu

A Linux distribution providing the operating system environment for
Python, networking, files, and services.

## `systemd`

Linux service manager for starting a bot on boot, supervising it,
restarting after crashes, and collecting logs. Restarting alone is not
enough; the bot must reconcile state before resuming orders.

## Virtual environment (`venv`)

An isolated Python environment for project packages.

## Dependency / package

A library used by the application, such as `alpaca-py`, `pandas`, or
`numpy`. Manage versions deliberately.

## Configuration

Settings such as symbols, timeframe, mode, and risk limits. Keep
configuration separate from logic and validate it at startup.

## Environment variable / `.env`

An environment variable is a value passed to the process, often for
secrets. A `.env` file stores local variables and should be excluded
from Git. `.env.example` should contain placeholders only.

## Git / GitHub

Git records source changes; GitHub hosts repositories. Never commit API
keys or other secrets, even to a private repository.

## Unit test / integration test / failure-path test

A unit test checks one function; an integration test checks components
working together; a failure-path test checks API timeouts, invalid data,
duplicate-order risk, partial fills, database failures, and restarts.

## Mock

A test substitute for a dependency, such as a fake broker that simulates
accepted, rejected, or partially filled orders.

## Secret / credential

Information granting access to an account/service, such as API keys.
Restrict access and never put secrets in source, logs, screenshots, or
browser code.

## Least privilege

Give each component only the permissions it needs. Avoid granting order
capability to a read-only dashboard.

## Backup

A separate copy of important state/data. Test restoring it, not just
creating it.

## CPU / RAM

CPU measures processing activity; RAM is working memory. Monitor both on
the Pi and avoid unbounded histories or expensive repeated calculations.

------------------------------------------------------------------------

# 11. Common confusions and end-to-end example

## Signal vs. order vs. fill

1.  **Signal:** strategy says a BUY condition may exist.
2.  **Order:** bot sends a request to buy a quantity.
3.  **Fill:** broker reports that some/all of the quantity actually
    executed. A signal may be blocked by risk; an order may be rejected
    or partially filled.

## Position vs. order

An order is a request; a position is what the account currently holds. A
submitted BUY order does not prove the position increased.

## Indicator vs. feature vs. signal

An indicator is a calculation (RSI/EMA); a feature is an input to
strategy/model (often an indicator); a signal is the resulting decision
or recommendation.

## Backtest vs. paper trading

A backtest simulates historical decisions. Paper trading sends orders
through a simulated broker environment under current/recent conditions.
Both can differ from live execution.

## Accuracy vs. profitability

A model can often predict direction correctly and still lose money if
losses exceed wins, costs are high, or predictions are not executable at
the assumed price. Evaluate net strategy results and risk, not accuracy
alone.

## Stop price vs. guaranteed loss

A stop is a trigger/exit mechanism, not insurance. Gaps and slippage can
produce a worse fill.

## Example workflow: one AAPL candidate trade

1.  Retrieve the latest completed 1-hour candle and validate
    timestamp/OHLC/volume.
2.  Store it in `candles`, preventing duplicates.
3.  Calculate EMA20/50/200, RSI, ATR, volume ratio, and returns;
    expose/store them as `features`.
4.  Strategy checks its rules and records a possible BUY in `signals`,
    including reason and timestamp.
5.  Risk manager checks position size, exposure, risk allowance, buying
    power, daily loss, and data freshness.
6.  If approved, order manager submits a paper order with unique
    `client_order_id`.
7.  Track broker status: it may be accepted, rejected, canceled,
    partially filled, or filled.
8.  Record each fill; update position from executed quantity and
    reconcile with Alpaca.
9.  Store account state in `portfolio_snapshots`.
10. Log errors and important events in `system_events`. If local and
    broker states disagree, pause new orders and investigate.

If ML is added later, it can evaluate the candidate and store its output
in `model_predictions`, but it must never bypass hard risk limits.

## Checklist when implementing a new term

-   What does it mean in this project?
-   What are the inputs and outputs?
-   What units are used: dollars, shares, fractions, percentages, bars,
    or timestamps?
-   Was the information available at decision time?
-   What happens if the value is missing, invalid, stale, or
    contradictory?
-   How is it tested?
-   Can the decision be reconstructed from database/logs?
-   Does it change risk or order behavior?
-   Is the system still explicitly in Paper Trading mode?

## Final principle

Build a reliable, testable system before adding model complexity. Good
data, realistic execution assumptions, strict risk limits,
reconciliation, and clear logs are foundational. AI is optional and must
prove its value against a simpler baseline.

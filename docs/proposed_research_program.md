# Proposed research program before the first paper trial

**Status:** The owner authorized starting Study A from this proposal on
2026-10-19. The remaining studies and any later paper activation still need
their stated checks; this authorization does not approve risk limits, a data
purchase, or paper orders. The current bot cannot run every study below yet.
The goal is a finite, reproducible decision process, not a search through
every stock and timeframe for an attractive chart.

The [Study A research record](study_a_research_record.md) logs the initial
15-minute rule-only data audit and exploratory results. Its incomplete basket
and single-symbol runs do not complete the program or authorize paper trading.
The [Study C research record](study_c_research_record.md) now logs the daily
rule-only development screen for all 12 symbols and a continuous shared-cash
portfolio follow-up. Daily costs were less damaging, but the symbol/year
results were mixed and the shared-cash result failed its pessimistic cost
case. Daily tuning, broker stops, full risk-policy simulation, and final evaluation
are still incomplete. The separately registered
[Study C-P1 stop variant](study_c_protective_exit_variant.md) added an offline
daily-bar stop proxy and failed its pessimistic-cost and drawdown screen;
broker stops and full risk-policy simulation remain unbuilt. Study B's ML
filter remains deferred until the rule-only evidence is clearer.

## The short answer: four matched strategy studies

Start with **two timeframes** and **two versions of the same strategy**. That
gives four comparable studies, using the same predeclared symbol set, dates,
data conventions, and cost scenarios within each timeframe:

| Study | Timeframe | Strategy | Question |
| --- | --- | --- | --- |
| A | 15-minute bars | Deterministic rules only | Does the existing intraday idea survive later data and realistic costs? |
| B | 15-minute bars | The same rules, with ML filtering BUY signals | Does ML improve A on the *same* eligible signals and later dates? |
| C | Daily bars | Deterministic rules only, tuned using earlier data only | Is a slower version more robust and operationally simpler? |
| D | Daily bars | The same daily rules, with a separately trained ML filter | Does ML improve C enough to justify its added complexity? |

**15 minutes is the primary timeframe** because the existing data checks and
case study were built around it. **One day is the planned challenger**, not an
automatic replacement. Daily bars produce fewer decisions and a five-bar ML
target means roughly a trading week, while five 15-minute bars mean 75 minutes
of observed bars; labels and entry/exit horizons must therefore be chosen
separately. A daily strategy also needs its own train-period parameter review.

Do not add 5-minute, hourly, 30-minute, weekly, and other variants at the
start. Each added combination increases the chance that a lucky historical
result looks convincing. The current downloader supports 15-minute, hourly,
and daily bars. Hourly bars deserve a separate session-boundary review because
the first bar can overlap premarket and the regular-session open. A new
timeframe can become a *new registered study* later, with a fresh untouched
evaluation period. The number of timeframes is a design choice, not a measure
of research quality.

## What to study across stocks

The first step is to define what the bot might actually be allowed to trade in
paper mode. I propose a **predeclared, diversified basket of about 10–20
liquid US stocks or ETFs**, plus a broad-market ETF as a reference. The exact
symbols and eligibility rules are an owner decision. Do not select symbols
because their full-period charts look good. A small basket is an engineering
pilot and measures how sensitive the result is to individual instruments; it
cannot establish an edge across the historical US stock market.

If the intended claim is that the strategy works across a broad stock
universe, add a separate **historical-universe study** using membership as it
existed at each date, delisted stocks, and corporate-action histories. A list
of today's surviving companies is not enough. We first need a suitable data
source, its cost and permissions, and a multi-symbol portfolio backtester.
The owner approves any paid source or budget. More stocks only help if the
historical sample and execution assumptions are trustworthy.

For either scope, report each symbol and the *combined portfolio* separately.
Check whether one symbol or one year accounts for nearly all the gain. A
portfolio result must simulate shared cash, simultaneous signals, exposure,
position limits, exits, and the actual paper risk policy. Adding individual
single-symbol returns is not a portfolio backtest.

## Shared research protocol

1. **Freeze a scope sheet.** Record symbols or point-in-time universe rules,
   primary timeframe, challenger timeframe, market session, Alpaca feed
   (`iex` or `sip`), price adjustment, data dates, download manifests,
   benchmark, rule settings, ML target and threshold, costs, and decision
   criteria. The owner can use the [research-scope workbook](research_scope_decision_workbook.md)
   and can answer in plain language. Compare the chosen historical feed with
   the feed available for the future paper process; they can produce different
   bars. A paper-only Alpaca account receives IEX market data, while SIP is
   consolidated exchange data; check actual account entitlements before
   finalizing the comparison ([Alpaca paper trading](https://docs.alpaca.markets/us/docs/paper-trading),
   [market-data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)).
2. **Audit the data.** Validate timestamps, calendar and session boundaries,
   gaps, duplicates, OHLC, volume, and adjustment behavior. Investigate
   unexplained gaps. Do not create candles or forward-fill prices to pass a
   test. Keep immutable manifests and note excluded instruments or periods.
3. **Use chronological windows.** One possible scheme, *only if the later years
   have not influenced these choices*, is 2019–2021 for fitting, 2022 for
   tuning, 2023 for calibration or repeated walk-forward checks, and 2024–2025
   for a final untouched evaluation. Exact boundaries depend on data coverage.
   Existing AAPL 2022–2023 examples have already been inspected and cannot be
   called fresh final tests for that research line. If 2024 or 2025 has also
   influenced symbol, rule, or model choices, reserve a genuinely later period.
   Keep ML labels that use future prices from crossing a window boundary.
   Time-ordered splits are appropriate for temporal data
   ([scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)).
4. **Develop the rule-only baseline first.** Check strategy behavior and costs
   on earlier windows. Then compare the ML filter with its rule-only counterpart
   using identical eligible signals, dates, capital, and execution costs. ML
   must remain an optional filter, not a new source of independent orders. Lock
   both versions, and select a candidate using earlier windows **before**
   opening the final period. Report all four frozen arms on that period, but do
   not choose the paper candidate by ranking their final-period returns.
   Inspect the final period once for confirmation of the prior selection.
   If results lead to changes, record the result as exploratory and find a new
   untouched period before claiming confirmation. Starting with rules does not
   require discarding the final holdout before ML is ready.
5. **Stress the frozen candidates.** Compare optimistic, base, and pessimistic
   spread/slippage/fee assumptions; delayed or missed fills; liquidity and
   turnover; subperiods and market regimes; concentration; and feed/adjustment
   sensitivity. Benchmark against a simple predeclared alternative, with its
   assumptions stated. Review return alongside drawdown, losses, trade count,
   exposure, and time in market. A high total return with a handful of trades
   or gains concentrated in one stock is weak evidence.

The ML target is a *research label*, not realized trade profit. For each
timeframe, choose its forward bar count and minimum return using only the
earlier windows. The current prototype's five-bar, +0.5% close-to-close label
and 0.60 BUY-filter threshold are examples, not approved settings. The
backtest must still price the subsequent entry, exit, and costs causally.

## A paper-readiness decision, not a promise of profit

Before inspecting the final period, record acceptable drawdown and loss,
minimum useful trade count, maximum concentration, and what degree of cost
sensitivity is acceptable. There is no universal return percentage that
certifies a trading strategy. The owner chooses the risk policy using the
[risk-limit workbook](risk_limit_decision_workbook.md). The research report
should show the rule/ML comparison, benchmark, all cost cases, yearly and
per-symbol results, data-quality exceptions, and any deviations from the
frozen plan. Prefer the simpler rules if ML does not add a clear, repeatable
benefit after costs.

**Do not approve an automated paper trial** on the basis of an unresolved
data gap, a backtest biased by today's surviving symbols while making a
market-wide claim, a result driven by one instrument or favorable cost
assumptions, or a risk/execution path the simulator never represented. If the
study is inconclusive, continue offline research or a read-only shadow run;
do not label it a proven strategy.

Once research is reviewed, paper activation still needs safe exit/stop
handling, a broker fill/activity ledger, a multi-symbol/risk-aware backtest
if the approved scope uses multiple symbols, recovery and kill-switch checks,
paper-account position/open-order review, approved risk settings, and an
explicit owner decision to start. Begin with a monitored, limited paper trial
and compare actual paper behavior with the frozen backtest assumptions over
varied market conditions. Alpaca says paper trading simulates fills and omits
some real-world effects, so neither backtests nor paper results guarantee live
performance ([Alpaca paper trading](https://docs.alpaca.markets/us/docs/paper-trading)).

## What exists, and what must be built

| Capability | Current status | Needed for this proposal |
| --- | --- | --- |
| Historical download, validation, and cost scenarios | Available for one symbol; 15-minute, hourly, and daily download choices | Download and audit the chosen scope; review feed/session handling |
| Deterministic backtest and walk-forward | Single-symbol engine plus offline shared-cash daily engine with next-session fills, provisional entry/loss gates, and an optional daily-OHLC stop proxy | Broker-like stop lifecycle, complete risk-policy simulation, and later locked evaluation for a basket |
| ML research | Offline, single-symbol BUY filter; no reviewed trained model | Frame-specific targets, matched rule/ML reports, and wider-scope evaluation |
| Historical-universe claim | Point-in-time membership and delisted data unavailable | Obtain approved data and implement universe-aware evaluation, if that claim is wanted |
| Automated paper execution | Submission disabled; recovery checks exist | Safe exit/stop workflow, fill ledger, reviewed risk policy, and monitored engine |

The existing AAPL case study is useful for checking software behavior but is
not an approval of AAPL, the 15-minute strategy, or paper execution. The
[development plan](../AI_Enhanced_Alpaca_Trading_Bot_Development_Plan_For_Coding_AI.md)
records implementation details and known limitations.

## Decisions and next steps

**Owner:** Review or amend this proposal: (1) fixed paper basket versus a
historical-universe claim, (2) 15-minute primary and daily challenger,
(3) genuinely uninspected final years, (4) Alpaca data entitlement and any
paid-data budget, and (5) acceptable risk and research criteria. You do not
need to code or personally download the data. You can say “use the proposal,
and suggest the exact symbols and dates” if those choices are still open.

**Codex:** After the scope is agreed, implement the missing portfolio and
research plumbing, prepare a reproducible scope sheet, download and audit
permitted data, run the four matched studies and stress checks, and present
the results for review. Then complete the execution/recovery gaps before
asking for a final paper-start decision. No step in this document places an
order or authorizes one.

# Choose a research scope before interpreting strategy or ML results

This is your decision sheet for the historical study. You can answer in plain
language and I can record the result and run the commands. No answer here
enables paper orders or changes `config/risk_limits.json`.

For the proposed four-study sequence across 15-minute and daily bars, see the
[research program before paper trading](proposed_research_program.md). This
workbook records the final scope choices after you review that proposal.

## 1. Decide what the first paper bot would study

- **Asset class:** The implemented strategy, downloader, order manager, and
  market calendar target US stocks and ETFs. Another asset class needs code
  and validation before it can be the first study.
- **Symbols:** Start with one named stock or ETF if you want to use the current
  Phase 14 runner. AAPL is the existing software case study, not a recommendation
  to trade it. A multi-symbol portfolio or a historical stock universe needs
  additional backtesting and point-in-time membership data. Do not use a list
  of today's survivors as proof of historical market-wide performance.
- **Timeframe:** The downloader supports 15-minute, hourly, and daily bars.
  Fifteen-minute bars match the existing AAPL case study and current feature
  and backtest examples. Daily bars are simpler but give fewer observations.
  The first hourly bar can mix premarket with the regular session in this
  project's Alpaca workflow, so review that boundary before choosing hourly.

Ask yourself: *What would I actually allow this paper account to trade?*
Study that instrument and timeframe, rather than choosing whichever old chart
looks best.

## 2. Specify the data you will trust

Record the broker feed (`sip` or `iex`), adjustment (`all`, `split`, or `raw`),
requested date range, and download manifest checksum. Alpaca describes SIP as
consolidated US exchange data and IEX as one exchange; its historical-bars
endpoint also specifies adjustment and symbol-as-of behavior
([historical bars](https://docs.alpaca.markets/us/reference/stockbars)).
Access to recent SIP data can differ from access to older historical SIP data
([market-data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)); check
the feed you can use for the later paper workflow. The downloader rejects
unexplained scheduled gaps. Do not fill them to make a backtest pass.

**Budget:** `free existing Alpaca access` / `ask before any paid source` /
`approved paid budget: ____`. No paid service is needed simply to choose a
scope or run the offline tests.

## 3. Decide the time windows *before* looking at the final test

For ML, name five UTC boundaries in this order:

```text
train_start < tune_start < calibration_start < test_start < test_end
```

The code trains on the first window, chooses model settings on the second,
fits probability calibration on the third, and evaluates the frozen model
on the fourth. It removes training labels whose future endpoint crosses a
boundary. The final test stops being untouched once you inspect its results.
Chronological separation prevents evaluating on data that was available to
the model while fitting; see scikit-learn's
[time-series split guide](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).

Possible *illustration*, only if 2024 has not influenced your choices:

| Purpose | Dates (UTC, end exclusive) |
| --- | --- |
| Train | 2019-01-01 to 2022-01-01 |
| Tune | 2022-01-01 to 2023-01-01 |
| Calibrate | 2023-01-01 to 2024-01-01 |
| Final test | 2024-01-01 to 2025-01-01 |

If you have already used 2024 to choose symbols, strategy settings, or model
thresholds, choose a later uninspected period. The existing 2022 and 2023 AAPL
walk-forward results have already been inspected and are not untouched final
tests for that research line.

## 4. Decide the target and model role, if you want ML

The current prototype predicts whether the close-to-close return is **strictly
greater than +0.5% after five observed bars**. At a 15-minute timeframe that
means five bars, not five trading days. You may choose a different bar horizon
and threshold, or start with the rule-only strategy and skip ML. The target is
a research label; an actual next-bar entry and later exit have different
execution prices and costs.

The current filter accepts a rule-based BUY only when calibrated probability
is at least 0.60. That is a fixed prototype setting, not an approved trading
threshold. It never creates a BUY or cancels a rule-based SELL. If you want to
choose another threshold, declare it before the final test and evaluate it
using earlier windows; repeatedly changing it after seeing the final test
would make that period exploratory.

## 5. State what would convince you to continue

Review net return, drawdown, number of trades, turnover, and performance under
optimistic, base, and pessimistic cost assumptions. Compare the same fixed
rule strategy with and without the ML filter on the same later period. Small
or cost-sensitive gains are not a reliable edge. State in advance how much
loss and drawdown you are willing to observe in research and paper mode;
the separate [risk-limit worksheet](risk_limit_decision_workbook.md) converts
your paper-account policy into limits.

The current backtester holds one long position in one symbol and does not
simulate the Phase 10 portfolio risk gate or broker stop orders. A scope that
needs many symbols or historical index membership requires additional code
and data before a credible portfolio or market-wide claim.

## Reply template

Copy this into a chat message and fill what you know. You can write "propose
for me" on any line; I will present a concrete default for review.

```text
First paper research: rule-only / rule plus ML / undecided
Asset class and symbols:
Timeframe: 15Min / 1Hour / 1Day
Historical feed and adjustment: SIP or IEX; all / split / raw / propose for me
Full data date range:
ML target: horizon in bars and return threshold / skip ML / propose for me
Train, tune, calibration, final test dates: / propose for me
Is the final test period genuinely uninspected by you? yes / no / unsure
Data budget: existing access only / ask before paid data / amount
Research loss/drawdown and cost sensitivity you would accept: / propose a review standard
```

I can then check data coverage, run the offline research, and explain the
results. You separately approve `config/risk_limits.json` and the decision
to begin a paper trial before any paper-order submission.

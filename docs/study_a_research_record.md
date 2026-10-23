# Study A: 15-minute rule-only research record

**Status:** Scope frozen for an initial research run; no paper orders. This is
the first arm of the [proposed research program](proposed_research_program.md).
The owner authorized Codex to start using that proposal on 2026-10-19.

## Predeclared scope

| Item | Choice |
| --- | --- |
| Asset class | Regular-session US stocks and ETFs, long-only |
| Primary timeframe | 15-minute bars |
| Strategy | `trend_following_v1` deterministic rules; no ML |
| Fixed pilot basket | AAPL, MSFT, JPM, JNJ, XOM, WMT, CAT, PG, NEE, SPY, QQQ, IWM |
| Reference | SPY buy-and-hold, reported separately from strategy performance |
| Historical data | Alpaca SIP bars, `all` adjustment, UTC timestamps, regular sessions only |
| Development period | 2019-01-01 through 2023-12-31; 2019–2021 fit, 2022 tune, 2023 exploratory calibration |
| Reserved final period | 2024-01-01 through 2025-12-31, unopened until the strategy and comparison are frozen; valid as a final test only if the owner confirms it did not influence choices |
| Costs | Existing optimistic, base, and pessimistic scenarios in `backtesting/research.py` |
| Capital | Existing $100,000 starting cash research assumption, not a planned account balance |

The symbols were selected to cover several sectors and broad-market ETFs,
without looking at their study-period returns. This is a **fixed present-day
basket**, so it cannot establish a historical-universe edge or remove
survivorship bias. The existing AAPL 2022–2023 walk-forward results have
already been inspected and remain exploratory. The present `BacktestEngine`
supports one symbol and one position, so individual runs must never be summed
and presented as a shared-cash portfolio. A basket-level conclusion requires
the proposed multi-symbol backtester and a common risk policy.

SIP historical bars older than 15 minutes may be available without a paid
SIP subscription, while free real-time access may be IEX only. A later
SIP-versus-IEX comparison is required before choosing the paper data feed
([Alpaca market-data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)).
No paid data source or subscription is authorized by this record.

## Work log

Record dataset manifests and hashes, data-quality exceptions, exact commands,
completed reports, and blocked steps here. Do not edit the frozen scope above
to accommodate an attractive result; document any change as a new study.

### 2026-10-19: data audit and exploratory rule-only runs

The initial SPY download for 2019–2023 was rejected: its scheduled
2019-08-12 19:45 UTC bar was absent. No file was accepted or candle filled.
To obtain common *complete* years for an initial feasibility pass, downloads
were rerun for **2020–2023**. This is a documented data-quality-driven
amendment to the development window, made before inspecting SPY, QQQ, MSFT,
or IWM returns. It leaves 2024–2025 reserved. AAPL's already-existing
2019–2023 complete dataset was reused; its earlier 2019 rows warm up its
indicators, while the newly downloaded datasets start in 2020. The trade
windows in the table below are the same calendar years, but this difference
limits exact cross-symbol comparability.

| Symbol | 2020–2023 download audit | Scheduled intervals without bars |
| --- | --- | ---: |
| AAPL | Existing 2019–2023 dataset accepted; 2020–2023 contained within it | 0 in existing manifest |
| MSFT | Accepted | 0 |
| JPM | Rejected; missing intervals span large blocks on 2021 and 2022 dates | 75 |
| JNJ | Rejected | 76 |
| XOM | Rejected | 100 |
| WMT | Rejected | 100 |
| CAT | Rejected | 98 |
| PG | Rejected | 96 |
| NEE | Rejected | 97 |
| SPY | Accepted | 0 |
| QQQ | Accepted | 0 |
| IWM | Accepted | 0 |

The JPM audit found 50 missing intervals in 2021 and 25 in 2022, spread
throughout trading hours rather than only at a session boundary. These gaps
require source investigation. A rejected symbol is **not** silently removed
from the fixed basket or counted as a losing or winning backtest. Successful
manifests contain volume-anomaly warnings, which also need review before a
final evaluation. The historical data and JSON reports are under ignored
`data/historical/` and `data/reports/` on the Windows development machine;
they will not be transferred by Git.

Accepted dataset SHA-256 values, as recorded in the manifests:

| Symbol | Dataset SHA-256 |
| --- | --- |
| AAPL | `615a4a3ee3a4cc10967dab793840809e88a7adfdf4f17d195d74f6c888c80f52` |
| SPY | `f960d80722b4b9c4b88dc3ca831a654dc5b74dbc89719e5c4a2f864d5d61e42f` |
| QQQ | `0e078fab98cc82be37ca4522a90fe170d469557a59cf42e201578bfd066d2023` |
| MSFT | `ef73f5b5649408a15c4a02c3ffeaa3e35e12d0043d486d3738a865adc54784d4` |
| IWM | `0fd03119c08469845d68013d6bb20c5be47255c11dd131232b4c8aebb761809b` |

The fixed default rule strategy was then run for 2022 and 2023 on each
accepted dataset, with the existing 10%-of-equity position sizing and
optimistic/base/pessimistic costs. **Returns and drawdowns below are
percentages of the simulated $100,000 single-symbol account**, not returns
of a shared basket. Each annual run starts with fresh cash; open positions
are marked at the last close.

| Year | Symbol | Optimistic return | Base return | Pessimistic return | Base max drawdown | Closed trades |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2022 | AAPL | +0.783% | +0.021% | -2.487% | -1.637% | 64 |
| 2022 | SPY | +0.032% | -0.794% | -3.479% | -1.086% | 70 |
| 2022 | QQQ | -0.782% | -1.592% | -4.184% | -2.092% | 68 |
| 2022 | MSFT | -2.270% | -3.144% | -5.986% | -3.239% | 76 |
| 2022 | IWM | -1.228% | -2.134% | -5.056% | -2.356% | 77 |
| 2023 | AAPL | +2.052% | +1.051% | -2.226% | -0.721% | 83 |
| 2023 | SPY | +1.453% | +0.523% | -2.543% | -0.687% | 79 |
| 2023 | QQQ | +2.462% | +1.372% | -2.060% | -0.992% | 88 |
| 2023 | MSFT | +1.634% | +0.512% | -3.215% | -1.439% | 95 |
| 2023 | IWM | +0.989% | -0.056% | -3.486% | -1.294% | 88 |

### How entries, exits, and holding times worked

The strategy reads each completed 15-minute candle. If no position is open,
it proposes a BUY only when the candle close is above EMA200, EMA20 is above
EMA50, RSI14 is from 50 through 70, and the current volume is more than its
20-bar average. The simulated order fills at the **next available candle's
open**, with a whole-share quantity worth at most 10% of then-current equity.
It does not buy at the close that produced the signal.

While a position is open, the only strategy SELL trigger is a completed
candle with **close below EMA50 OR EMA20 below EMA50**. The simulated SELL
fills at the next available candle's open. There is no fixed one-day or
fixed-number-of-bars holding period, automatic end-of-day close, protective
stop, or trailing stop. If the signal arrives on the last candle of a day,
the next available open may be the next trading day. If a position remains at
the end of the requested annual window, it is marked to the last close for
equity reporting and is not artificially sold. Separate annual runs start
with fresh cash, so they do not carry such a position into the next year.

The new offline `backtesting.trade_audit` command recomputes that same base
scenario and lists every simulated BUY/SELL fill and its elapsed calendar
holding time. The local ignored reports are
`data/reports/study_a_AAPL_2022_trade_audit.json` and
`data/reports/study_a_AAPL_2023_trade_audit.json`.

| AAPL year | Closed positions | Median elapsed time | Range | Held overnight |
| --- | ---: | ---: | ---: | ---: |
| 2022 | 64 | 21.375 hours | 0.25 to 284.75 hours | 46 |
| 2023 | 83 | 24 hours | 0.25 to 258 hours | 60 |

These are **calendar hours between simulated fills**; nights, weekends, and
holidays count. The 2023 first completed trade illustrates the mechanics:

1. The 2023-01-06 20:45 UTC candle produced a BUY after it completed. The
   next available open was 2023-01-09 14:30 UTC; the simulation bought 77
   AAPL shares at $128.266914 after base spread/slippage adjustments.
2. The 2023-01-09 20:45 UTC candle closed at $127.91, below its EMA50 of
   about $128.0078. That triggered a SELL after the candle completed. EMA20
   was still above EMA50, so the close-below-EMA50 condition was sufficient.
3. The next available open was 2023-01-10 14:30 UTC. The simulation sold the
   77 shares at $127.9232 after base costs. The position lasted 24 calendar
   hours between fills and lost about $26.47. This is a simulated historical
   trade, not a broker order or a quote-level execution claim.

The base cost scenario assumes 5 basis points of adverse slippage and a
2-basis-point spread, charging half the spread on each side. The pessimistic
scenario assumes 20 basis points of adverse slippage, a 10-basis-point
spread, and a $1 commission per order. These are research assumptions, not
observed broker fills. The backtester does not model partial fills, latency,
intra-bar stops, or a shared portfolio risk gate.

For context, SPY's adjusted first-open-to-last-close change was -18.407%
in 2022 and +25.551% in 2023. This is a fully invested reference; the
strategy has a 10% single-position cap, so those figures are **not** a
risk-matched performance comparison.

Reproduction with the existing commands, replacing `SYMBOL` and paths as
needed:

```powershell
python -m backtesting.research download --symbol SPY --start 2020-01-01 --end 2024-01-01 --timeframe 15Min --feed sip --adjustment all --output data/historical/SPY_15Min_2020_2023_study_a.csv
python -m backtesting.research backtest --dataset data/historical/SPY_15Min_2020_2023_study_a.csv --trade-start 2023-01-01 --trade-end 2024-01-01 --output data/reports/study_a_SPY_2023_rule_only.json
python -m backtesting.trade_audit --dataset data/historical/AAPL_15Min_2019_2023.csv --trade-start 2023-01-01 --trade-end 2024-01-01 --cost-scenario base --output data/reports/study_a_AAPL_2023_trade_audit.json
```

### Interpretation and stop condition

The default rule-only strategy is **not a paper candidate on this evidence**:
every available 2022 and 2023 single-symbol run loses under pessimistic
costs, most 2022 base-cost runs lose, and seven basket symbols failed the
strict data audit. The seemingly small drawdowns reflect the 10% position
cap and should not be mistaken for good risk-adjusted performance. No
portfolio simulation, point-in-time universe, broker-stop simulation, or
approved paper risk policy was used. These are exploratory results; none
open the reserved 2024–2025 period.

Next engineering work is to audit source gaps without inventing bars, build
shared-cash multi-symbol and risk-aware backtesting, and define a frozen
rule-only candidate from development data. Only then decide whether a final
holdout evaluation is justified. The owner should review this weak baseline
and later choose risk limits before any paper order. There is no reason to
start the paper trial from these numbers.

## Decision status

On 2026-10-23, the owner confirmed that 2024–2025 results have **not** been
used to choose symbols or settings. This preserves those years as a planned
final holdout for this research line; they have not been downloaded or run in
Study A. We still must freeze the eventual candidate and audit the data
before opening them.

No paper candidate has been approved. No paper-order submission, risk
configuration approval, or deployment decision follows from this study.

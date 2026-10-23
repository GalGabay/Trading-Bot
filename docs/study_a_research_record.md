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

For context, SPY's adjusted first-open-to-last-close change was -18.407%
in 2022 and +25.551% in 2023. This is a fully invested reference; the
strategy has a 10% single-position cap, so those figures are **not** a
risk-matched performance comparison.

Reproduction with the existing commands, replacing `SYMBOL` and paths as
needed:

```powershell
python -m backtesting.research download --symbol SPY --start 2020-01-01 --end 2024-01-01 --timeframe 15Min --feed sip --adjustment all --output data/historical/SPY_15Min_2020_2023_study_a.csv
python -m backtesting.research backtest --dataset data/historical/SPY_15Min_2020_2023_study_a.csv --trade-start 2023-01-01 --trade-end 2024-01-01 --output data/reports/study_a_SPY_2023_rule_only.json
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

No paper candidate has been approved. No paper-order submission, risk
configuration approval, or deployment decision follows from this study.

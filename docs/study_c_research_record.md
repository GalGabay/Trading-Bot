# Study C: daily rule-only research record

**Status:** Fixed-rule development screen completed on 2026-10-23. The
preexisting walk-forward rule permitted daily tuning for only two symbols,
so the tuned basket arm and shared-cash portfolio study remain incomplete.
This is offline research; no order submission or paper activation is authorized.

## Predeclared scope

| Item | Choice |
| --- | --- |
| Instrument set | The same fixed pilot basket as Study A: AAPL, MSFT, JPM, JNJ, XOM, WMT, CAT, PG, NEE, SPY, QQQ, IWM |
| Timeframe and session | Alpaca `1Day` bars for regular US stock-market sessions |
| Strategy | Fixed default `trend_following_v1` rules, without ML or a newly tuned exit |
| Data | Alpaca historical SIP feed, `all` adjustment, 2019-01-01 inclusive through 2024-01-01 exclusive |
| Scored windows | 2022 and 2023 separately; earlier bars supply indicator warmup and development context |
| Reserved years | 2024 and 2025 remain unopened for final evaluation after candidate selection |
| Capital | $100,000 per **separate single-symbol simulation**; 10% equity position cap in the existing engine |
| Costs | Existing optimistic, base, and pessimistic scenarios in `backtesting/research.py` |
| Reference | SPY buy-and-hold, separately labeled when available |

Daily bars are stamped at New York midnight by Alpaca. A signal based on a
completed daily bar is filled no earlier than the next bar's open in the
existing backtester. The strategy exits when the completed daily close falls
below EMA50 or EMA20 falls below EMA50; there is no fixed holding period,
profit target, or protective stop order. Bars with no qualifying trades may
be absent; the strict downloader rejects an unexplained expected-session gap
instead of manufacturing a candle. Such rejections and any adjusted-price
or volume warnings will be disclosed. Alpaca documents the [daily bar timestamp
and feed rules](https://docs.alpaca.markets/us/docs/market-data-faq).

This first pass deliberately keeps the rule parameters fixed to isolate the
timeframe comparison. The proposed program also calls for daily-specific
training on earlier data; that is a separate, explicitly recorded step if
the fixed baseline merits more work. Neither 2022 nor 2023 is a final unseen
test here. Each symbol-year run resets cash, so individual returns cannot be
added into a basket return. The present engine cannot model shared cash,
simultaneous symbols, or the final paper risk policy. This fixed present-day
basket also cannot establish a market-wide historical edge because it omits
delisted stocks and historical membership.

## Work log

Record every accepted dataset and rejection, its manifest hash, the exact
research windows, cost cases, trade counts, and limitations here. A rejected
symbol stays in the intended basket and is never silently replaced. Do not
change this scope in response to the observed returns; record a changed design
as another study.

### 2026-10-23: data audit

All 12 SIP/`all` datasets passed the downloader's timestamp, calendar,
scheduled-session, duplicate, OHLC, and nonnegative volume checks. Each has
1,258 daily bars from 2019-01-02 through 2023-12-29. No missing candle was
filled. JNJ has a **warning** for four daily volumes above 10 times its
positive-volume median, on 2023-08-15, 08-16, 08-21, and 08-23. Their cause
has not been verified, so treat JNJ's 2023 research result with extra care.
No other dataset produced a validation warning.

| Symbol | Dataset SHA-256 |
| --- | --- |
| AAPL | `fec8fb06cd601fd6501ec467f58a47f71a2af395759f3d2c104bd9c44518f2d3` |
| MSFT | `20d7c0e41f93dec5927857536d078a7d7b0581e49fca7d8a17743b6e197617ea` |
| JPM | `978c2117a74ef7d8d58dd051d93bc5c364d525844d83e02b9e13d94ad27844d1` |
| JNJ | `a07b9415aa8e9efd89d3a15d6bc91bcc2feecc214f4e56d6cbe532fd28d0e286` |
| XOM | `0e120a2d3735cbe8e77f49785078262d40999fe39a589cf73c9ab09328046a12` |
| WMT | `b42d81b532fa62631e47e1c0bf97ee065ac82fdb410a8a6ea1db831ee3cf3f5e` |
| CAT | `2d76897ebc669922de8675aa89a6da16d6c3f267a6337dd3edb883eae303e09f` |
| PG | `6a390c81b5df68369116d5239f08d5444fd44d5cc5dd22b98dbf8e8d72fb5700` |
| NEE | `0cc7438b1125f99f33282fdb8720dd5e0a18139804702b867d2d25051cb8cdf4` |
| SPY | `163d331445b0e4edeec1f16e7814906b60a23483ecbce9941e9a43282ee8a1ed` |
| QQQ | `d5d73885ab736a4b448c95bcb1a1e87a0b918695534ec0ce44eb2f2e082f3faa` |
| IWM | `ff383df86d45b21e9c9e42274a809f1734a2038215513beca74b5126548078bd` |

The local CSVs and manifests are under ignored `data/historical/`; Git will
not carry them to the Raspberry Pi. They can be reproduced with, for example:

```powershell
.venv\Scripts\python.exe -m backtesting.research download --symbol AAPL --start 2019-01-01 --end 2024-01-01 --timeframe 1Day --feed sip --adjustment all --output data/historical/AAPL_1Day_2019_2023_study_c.csv
```

Repeat for each predeclared symbol with its own output name. The exclusive
2024-01-01 boundary ensures that this command does not open 2024 or 2025.

### 2026-10-23: fixed-rule comparison

Each accepted dataset was run with the default `TrendFollowingV1` parameters,
the existing 10%-of-equity position cap, and all three cost scenarios. Every
2022 and 2023 run used preceding years only to warm up indicators. The
percentages below are net changes in an independent $100,000 simulated
account. They are **not** combined basket returns. `Closed` counts complete
buy/sell round trips under base costs. `Open` means a position remained marked
at the last close of that annual run.

| Year | Symbol | Optimistic | Base | Pessimistic | Base max drawdown | Closed | Open |
| --- | --- | ---: | ---: | ---: | ---: | ---: | :---: |
| 2022 | AAPL | -0.832% | -0.880% | -1.037% | -1.294% | 4 | No |
| 2022 | MSFT | -0.646% | -0.658% | -0.674% | -0.658% | 1 | No |
| 2022 | JPM | -0.121% | -0.139% | -0.203% | -0.748% | 1 | Yes |
| 2022 | JNJ | -0.020% | -0.090% | -0.311% | -1.163% | 5 | Yes |
| 2022 | XOM | +4.376% | +4.319% | +4.122% | -2.983% | 4 | No |
| 2022 | WMT | -0.168% | -0.224% | -0.425% | -1.394% | 5 | No |
| 2022 | CAT | -0.516% | -0.556% | -0.690% | -2.466% | 3 | Yes |
| 2022 | PG | -1.037% | -1.088% | -1.260% | -1.324% | 4 | Yes |
| 2022 | NEE | -0.573% | -0.612% | -0.741% | -1.332% | 3 | Yes |
| 2022 | SPY | -1.413% | -1.459% | -1.611% | -1.517% | 4 | No |
| 2022 | QQQ | -0.311% | -0.322% | -0.362% | -0.322% | 1 | No |
| 2022 | IWM | -1.090% | -1.113% | -1.190% | -1.159% | 2 | No |
| 2023 | AAPL | +2.222% | +2.203% | +2.112% | -0.973% | 1 | Yes |
| 2023 | MSFT | +3.387% | +3.332% | +3.162% | -1.451% | 4 | Yes |
| 2023 | JPM | +1.418% | +1.364% | +1.184% | -0.832% | 4 | Yes |
| 2023 | JNJ | -0.845% | -0.892% | -1.045% | -0.961% | 4 | No |
| 2023 | XOM | -0.572% | -0.620% | -0.778% | -1.561% | 4 | No |
| 2023 | WMT | -1.090% | -1.158% | -1.392% | -1.158% | 6 | No |
| 2023 | CAT | +0.257% | +0.209% | +0.061% | -1.581% | 4 | No |
| 2023 | PG | -1.645% | -1.729% | -2.041% | -1.857% | 8 | No |
| 2023 | NEE | -0.977% | -0.993% | -1.071% | -1.061% | 2 | No |
| 2023 | SPY | +1.067% | +1.014% | +0.836% | -0.758% | 4 | Yes |
| 2023 | QQQ | +2.671% | +2.628% | +2.487% | -1.075% | 3 | Yes |
| 2023 | IWM | +0.950% | +0.908% | +0.751% | -0.850% | 3 | Yes |

The default cost settings are zero costs (optimistic), 5 basis points of
slippage plus 2 basis points full spread (base), and 20 basis points of
slippage plus 10 basis points full spread plus $1 per order (pessimistic).
These are scenarios, not verified broker costs. Under base costs, **1 of 12**
symbol-year runs gained in 2022 and **7 of 12** gained in 2023. There were
37 completed trades and 5 end-of-year open positions in 2022; 47 completed
trades and 6 open positions in 2023. Only 8/37 and 13/47 of completed trades
were winners in those years, respectively. The mean calendar holding time,
weighted by completed trades across the separate runs, was **24.76 days**
in 2022 and **34.32 days** in 2023. Open positions are excluded from these
trade and holding-time counts, though their last-close mark affects returns.

As a simple reference, SPY's adjusted first-day open to last-day close was
-18.406% in 2022 and +25.540% in 2023. A constant 10%-of-starting-capital
SPY position, with no costs, would contribute approximately -1.841% and
+2.554% to the whole account in those respective years. It is only a rough
reference: it has different timing, exits, and cost assumptions from the
strategy. The rule's SPY base returns were -1.459% and +1.014%.

For the five symbols accepted in Study A (AAPL, MSFT, SPY, QQQ, IWM), the
daily rule suffered much less cost erosion than the 15-minute version,
especially in the pessimistic case, because it traded far less often. In
2023 all five daily pessimistic returns were positive while all five
15-minute pessimistic returns were negative. This comparison is exploratory:
the rule has not demonstrated a stable, shared-cash basket advantage and
the 2022 daily results were mostly losses. XOM's 2022 gain is concentrated
in one favorable symbol, so it does not establish a general daily edge.

Reproduce an individual report with:

```powershell
.venv\Scripts\python.exe -m backtesting.research backtest --dataset data/historical/AAPL_1Day_2019_2023_study_c.csv --trade-start 2022-01-01 --trade-end 2023-01-01 --output data/reports/study_c_AAPL_2022_rule_only.json
```

Run the same command for each symbol and for 2023-01-01 through 2024-01-01.
The 24 JSON reports live under ignored `data/reports/`, and each references
its dataset hash and exact assumptions.

### 2026-10-23: existing walk-forward selection

The preexisting `backtesting.walk_forward` grid consists of baseline,
narrow, and broad rule parameters. It requires at least **20 completed
training trades** before selecting a candidate, using 2019–2021 for a 2022
fold and 2019–2022 for a 2023 fold. Keeping that rule, 10 of 12 symbols had
no eligible candidate before the first 2022 fold: AAPL, JPM, JNJ, XOM, WMT,
CAT, PG, NEE, SPY, and QQQ. No tuned result was produced for them. Lowering
the threshold now just to force eligibility would create a new, weaker
selection design after seeing these development results.

| Symbol | 2022 selected rule | 2022 base / pessimistic | 2023 selected rule | 2023 base / pessimistic |
| --- | --- | ---: | --- | ---: |
| MSFT | broad (29 training trades) | -1.938% / -2.070% | broad (33) | +2.864% / +2.603% |
| IWM | broad (23) | -0.972% / -1.050% | broad (25) | +1.203% / +1.062% |

These two isolated tuned results are not a tuned-basket result. Their JSON
reports are in `data/reports/study_c_MSFT_walk_forward.json` and
`data/reports/study_c_IWM_walk_forward.json`. For example:

```powershell
.venv\Scripts\python.exe -m backtesting.walk_forward --dataset data/historical/MSFT_1Day_2019_2023_study_c.csv --first-test-year 2022 --last-test-year 2023 --output data/reports/study_c_MSFT_walk_forward.json
```

## Interpretation and next decision

The fixed daily rule is less sensitive to the chosen transaction-cost range
than Study A's 15-minute rule, but its cross-symbol evidence is mixed and its
one-year trade counts are small. **Study C is a completed fixed-rule
feasibility screen, not a passed paper-trading gate.** Annual runs reset
cash, and positions left open at December's last close are not charged a
future exit cost or carried into the next year. The daily `all` adjusted
bars are research prices; corporate-action adjustments and cash dividends
are not a point-in-time fill and cash ledger. Historical SIP bars may differ
from the feed actually available to a paper process. The JNJ volume warning
needs investigation, and the fixed present-day basket has survivorship bias.

Before treating daily rules as a paper candidate, implement a shared-cash
12-symbol portfolio backtest with the chosen risk policy, continuous
year-to-year positions, broker-like exits, and data/feed sensitivity checks.
Define a **new daily-specific selection protocol** on development data if
daily tuning is still desired; report low sample size honestly instead of
relaxing the gate until a winner appears. Compare a frozen daily rule against
its matched ML filter in Study D only after this baseline is credible. Keep
2024–2025 unopened until the strategy and comparison are frozen.

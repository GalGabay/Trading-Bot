# Study C: daily rule-only research record

**Latest readiness outcome, 2026-10-27:** The [Apple/CBRE/SPY cached review](remaining_pilot_readiness.md)
revalidates 6,036 candles and reconciles 66 events, with 11 source checks.
It distinguishes usable price observations, supported issuer terms and
remaining independent evidence gaps. No new return result was produced.
The [finite next diagnostic proposal](next_pilot_experiment_proposal.md)
requires explicit scope/vendor/timing review and a separate mode before any
performance run. JPMorgan remains parked; old scores and membership are intact.

**Latest data outcome, 2026-10-27:** The [single capped JPMorgan follow-up](jpm_dividend_followup_results.md)
saved one additional declaration and stopped at four discovery calls. Twenty-nine
declaration targets and 15 original payable omissions remain. JPMorgan's active
engineering collection is now parked under the owner's fallback; continue
AAPL/CBRE qualification with SPY context. The historical register, registered
strategy control and old return results are unchanged. No new backtest, order,
purchase or holdout-candle read occurred.

**Latest verification, 2026-10-27:** The [offline collector/parser checks](public_source_test_results.md)
pass 99 tests with no failures, errors or skips. Stronger validation preserves
the previous 66 source-reconciliation rows byte for byte in CSV/JSON, with
16 original payable omissions and unapproved research timing still explicit.
No real network requests, downloads, strategy backtest or orders occurred.

**Latest source update, 2026-10-27:** The [bounded public collection](pilot_public_source_results.md)
saved 11 files, confirms three omitted SPY distributions and supplies primary
payable terms for 32 of 48 original provider omissions (one already known).
Sixteen omissions remain. The source comparison preserves one SPY precision
difference and unapproved timing flags. Collection stopped at HTTP 403 without
paid fallback. No strategy return, order or reserved price read occurred.

**Current data update, 2026-10-27:** The [cached four-history qualification](free_data_pilot_qualification.md)
validated 8,048 actual candles and recorded 94 provider events plus CBRE's
independent rename. Six specific primary event cross-checks are supported;
full-period identity/action completeness remains blocked. Forty-eight provider
dividend rows omit payable dates. No strategy return, broader backtest,
network request, purchase or order was produced by this review.

**Current planning update, 2026-10-27:** The [free-data pilot proposal](free_data_pilot_proposal.md)
specifies four cached histories (AAPL, JPM, CBRE and SPY context), exact dates,
proposed knowledge/payment conventions and hard exclusions. It schedules
data qualification only, with no new return calculation or strategy search.
The full historical register remains intact; research assumptions and a
later narrower basket scope are not automatically approved.

**Latest engineering update, 2026-10-27:** The [ownership verification and evidence review](ownership_verification_results.md)
passed 183 focused unit tests, 36 exact financial replays, 36 exact daily-risk
comparisons and 84 component checks. The risk reporter now rejects inconsistent
headline summaries. Twenty saved primary sources were revalidated; incomplete
historical cases remain blocked. No larger strategy study, revised return
result, purchase, broker/account call or order was made. Three free public-web
tool calls established no missing filing date. See [paper readiness](paper_trading_readiness.md)
for the remaining gates.

**Preceding engineering follow-up:** The [ownership-claim ledger](claim_accounting.md)
now handles delayed cash rights, successor/spin-off ownership and exact
fractional claims in standalone offline accounting. The 111 focused unit tests
and 84 saved-case/timeline checks pass. Historical payment/publication/delivery
gaps and missing quotes remain explicit; one missing-child-price arithmetic
check is synthetic. That increment did not connect a strategy adapter; the
latest update above records verification of that connection.
There is no new strategy return result, broader scoring or paper approval. Purchases, network
requests and orders in this increment were zero.

**Preceding engineering follow-up:** The [free collection/event review](free_collection_results.md)
has saved 23,748 raw observations and 249 provider event records across
representative cases. It resolves specific observed alias boundaries and
exposes ten required events missing from the API inventory. Claim/share
distribution accounting and full cohort evidence remain due before broader
strategy scoring. No returns were optimized, no orders placed, and no paid
data or subscription change purchased.

**Latest free-source audit:** [2016 cohort mapping and coverage](cohort_2016_audit_results.md)
identifies dated tickers for all 506 retained holdings, records ten event cases,
and checks 33 cached daily-price files. Complete raw/action-aware data remain
unavailable locally, so the broader study is not yet scored. No new purchases,
broker requests or orders occurred. The earlier $9.69 Apple figure was virtual
dividend income in an offline simulation, not a fee or an actual payment.

**Latest data-engineering follow-up:** The [raw-price/action pilot and historical-basket report](raw_action_pilot_and_historical_baskets.md)
checks real split/dividend accounting, extends daily risk diagnostics, and
extracts public historical holdings lists with 506/505 security rows. These
are fixed dated source baskets; broader identity/action/price coverage still
needs review before strategy scoring. No new Study C strategy return result
or paper approval follows from that accounting pilot.

**Later follow-up:** [Study C-R2](study_c_daily_improvement_results.md) evaluated
five fixed daily-rule arms and 86 simulations. Breakout rules improved
pessimistic returns to about +3.2%, but no candidate passed the full checks.
Those new variants are separately labeled and do not replace this original
Study C record.

The later [C-R3 allocation study](study_c_allocation_results.md) tested
smaller breakout position sizes and explicit daily halt/restart policies.
Its selected research allocation reduced losses and gains; it does not
approve paper trading.

The subsequent [C-R4 earlier-history study](study_c_earlier_history_results.md)
validated complete 2016-2018 daily coverage and kept the C-R3 candidate
frozen. Its 40 simulations passed the ten additional-history checks, with
+2.972% pessimistic return in 2017-2018 and +16.392% over a continuous
2017-2023 account. These backward checks retain the original evidence limits;
2024-2025 remain unopened and paper trading remains unapproved.

After the owner approved 6% annual return and 5% running-peak drawdown
research criteria, the [investment goal-fit audit](study_c_goal_fit_results.md)
replayed the unchanged candidate at $100,000 and $10,000. It does not meet
the approved investment objective. This later decision preserves all earlier
study results and keeps 2024-2025 unopened.

The approved [holding-time study](holding_period_study_results.md) has now
completed 36 simulations, including the owner's amendment allowing reviewed
continuation beyond 60 sessions. Both new variants freed slots but failed
the approved investment criteria. A broader-universe feasibility audit is
proposed next; no broad-market or paper-performance claim has been established.

**Status:** Fixed-rule development screen and continuous shared-cash portfolio
follow-up completed on 2026-10-23. The preexisting walk-forward rule permitted
daily tuning for only two symbols, so a tuned basket, full risk-policy replay,
and final evaluation remain incomplete. This is offline research; no order
submission or paper activation is authorized.

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
No other dataset produced a validation warning. The later
[SIP/IEX and JNJ follow-up audit](study_c_feed_audit.md) found corresponding
IEX activity and a contemporaneous Kenvue exchange offer, making an event
spike plausible while leaving the exact SIP volumes unverified. It also found
incomplete historical IEX coverage and material BUY-candidate differences.
The four warning bars remain unchanged.

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

The shared-cash follow-up below handles simultaneous positions and continuous
year-to-year holdings, but still lacks protective exits, full risk-policy
replay, and data/feed sensitivity checks. Define a **new daily-specific
selection protocol** on development data if daily tuning is still desired;
report low sample size honestly instead of relaxing the gate until a winner
appears. Compare a frozen daily rule against its matched ML filter in Study D
only after this baseline is credible. Keep 2024–2025 unopened until the
strategy and comparison are frozen.

## Predeclared shared-cash follow-up (recorded before portfolio results)

The owner requested this follow-up after reading the fixed-rule screen. Use
the same 12 validated daily datasets and the **unchanged default rule**.
Warm up indicators with 2019–2021, then simulate one $100,000 cash account
continuously from 2022-01-01 to 2024-01-01 exclusive. Carry positions and
the equity peak across the 2022/2023 boundary. Fill actionable signals at
the *following* session open, process sells before buys, and use alphabetical
symbol order to resolve simultaneous buys that compete for shared cash. Run
the same three cost scenarios, plus a reverse-alphabetical order sensitivity
check under base costs. No borrowed cash or forced end-of-year liquidation.

Research entry limits are configurable. For this first run, use the existing
**provisional, unapproved** limits where the simulator can represent them:
10% of equity per new position, 70% total exposure at entry, at most seven
positions, 3% daily equity loss, and 10% drawdown. A breached loss/drawdown
gate blocks future buys for the rest of the run; existing trend-rule sell
signals may still exit. It does **not** place protective stops or immediately
liquidate a holding. The 1% planned stop-risk cap cannot honestly be modeled
without a specified stop and execution rule; snapshot/signal age and optional
sector/volatility checks are also outside this historical simulation. These
research assumptions do not approve `config/risk_limits.json` for paper use.

Report whole-account 2022 and 2023 returns, total return, max drawdown,
closed-trade count, costs, concentration, open positions, and any limit halt.
Preserve separate Study A/C single-symbol findings rather than treating their
sum as the portfolio. Any later change to the risk rules, universe, priority,
or exits requires a separately labeled research run. Keep 2024–2025 closed.

### 2026-10-23: continuous shared-cash results

The new offline runner `backtesting.portfolio_research` verified all 12
dataset checksums and matching daily session timestamps. It built each
symbol's features from its own past bars, used one shared cash balance,
filled prior-close signals at the next session's open, and carried five
open positions from the end of 2022 into 2023. It did not reset equity or
the loss/drawdown peak at the calendar boundary. The five positions were
NEE, JNJ, PG, CAT, and JPM; all eventually received rule-based SELL fills
in 2023. No daily-loss or drawdown entry halt occurred.

**Execution-timing correction before the final report:** An initial local
draft sized BUYs directly from the next session's opening price. That price
is unknown when the signal forms. The final runner plans a maximum share
count from the completed signal close, then reduces or skips at the next
open if cash or exposure is insufficient. It never increases the planned
count because of a favorable opening gap. The earlier local
`study_c_shared_cash_alphabetical.json` and
`study_c_shared_cash_reverse_base.json` drafts are superseded; use only the
`close_planned` reports and figures below.

| Cost case | 2022 account return | 2023 account return | Two-year return | Max drawdown | Closed trades |
| --- | ---: | ---: | ---: | ---: | ---: |
| Optimistic | -2.027% | +6.025% | +3.876% | -6.109% | 83 |
| Base | -2.455% | +5.429% | +2.841% | -6.355% | 83 |
| Pessimistic | -3.928% | +3.543% | **-0.524%** | -7.644% | 83 |

These are **whole-account** returns on one initial $100,000 balance, with
positions, costs, and cash shared across all symbols. Annual returns use the
prior December's ending equity as the next year's starting equity, so the
2022 and 2023 percentages compound rather than add. The base case ended at
**$102,841.21**, with 23 winners among 83 completed trades, mean completed
holding time 31.82 calendar days, and profit factor 0.901. The pessimistic
case ended at **$99,475.62**. Each cost case had six open positions at the
final 2023 close, valued at that close without a future sale or exit cost.

The positive base-case account result is **not closed-trade profit**:
completed positions realized **-$2,031.07** combined, while six remaining
positions had **+$4,872.27** of marked unrealized P&L. Under pessimistic
costs those amounts were **-$5,141.28** and **+$4,616.90**, respectively.
Future exits could change the outcome. Base realized P&L from XOM alone was
+$3,879.91; this one favorable instrument offset losses elsewhere and is
evidence of concentration rather than basket-wide consistency.

The entry gate allowed at most seven positions and 70% exposure **when
opening**. It rejected 38 base-case BUY attempts because the seven-position
limit was full. The maximum *observed closing* exposure was 71.64%, because
existing holdings can move above the entry-time ceiling; there is no forced
rebalance. The 3% daily-loss and 10% drawdown gates never triggered in these
runs. This does not establish that the portfolio is safe under larger gaps or
different periods.

Reversing the alphabetical priority for simultaneous BUYs under base costs
gave **+2.786%** two-year return, with -2.177% in 2022, +5.073% in 2023,
and 82 completed trades. This modest change shows that simultaneous order
selection matters when cash or position slots are scarce. The predeclared
alphabetical run remains the primary result.

For a simple reference, buying 22 whole shares of adjusted SPY at the first
2022 session open with approximately 10% of starting capital, then holding
them through the last 2023 close, would produce about **+0.284%** whole-
account return under base entry costs and no exit. That reference holds just
one position at roughly 10% starting exposure, while this strategy may hold
seven, so their risks are not matched. Both use adjusted bars as proxies.

Reproduce the primary run locally after downloading the datasets listed
above (the output path must be new):

```powershell
$symbols = @('AAPL','MSFT','JPM','JNJ','XOM','WMT','CAT','PG','NEE','SPY','QQQ','IWM')
$datasets = @($symbols | ForEach-Object { "data/historical/${_}_1Day_2019_2023_study_c.csv" })
.venv\Scripts\python.exe -m backtesting.portfolio_research --datasets $datasets --trade-start 2022-01-01 --trade-end 2024-01-01 --output data/reports/study_c_shared_cash_close_planned.json
```

The full ignored JSON report contains each cost case's fills, daily equity
curve, skipped-order events, dataset hashes, provisional limits, and known
policy gaps. The reverse-priority base report is
`data/reports/study_c_shared_cash_close_planned_reverse_base.json`; repeat the command
with `--buy-priority reverse --scenarios base` and that output filename.

**Decision:** This portfolio check strengthens the conclusion that Study C
is exploratory. The fixed daily rule survived base modeled costs over these
two development years, but did not survive the pessimistic costs and most of
its final gain is unrealized. The rule still lacks a protective stop and a
complete risk-policy simulation. Do not open 2024–2025 or start paper
trading based on this result. A next research change needs a separately
registered design and later untouched evaluation; the owner must still
choose risk limits before paper activation.

The separately registered [Study C-P1 protective-exit variant](study_c_protective_exit_variant.md)
was subsequently tested on the same development window. Its fixed two-ATR
trailing stop and 1% planned-risk sizing **failed** the predeclared screen,
with worse pessimistic return and drawdown than this unchanged baseline.

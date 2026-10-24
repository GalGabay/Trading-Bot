# Study C-R4: earlier-history robustness results

Study date: 2026-10-23. The [protocol](study_c_earlier_history_protocol.md)
was recorded before the data download and performance calculations. This
study evaluates the frozen C-R3 volatility-sized 55/20 breakout; it does not
choose a new strategy or tune its settings. Personal paper-risk settings
remain unapproved. No orders were submitted and 2024-2025 remain unopened.

**Result: all ten predeclared additional-history checks passed.** The modest
returns and broader evidence limitations still prevent paper approval.

**Subsequent owner-goal review, 2026-10-24:** The owner finds approximately
2% annual returns insufficient and identified a $500 decline on $10,000 as
concerning. The [draft acceptance plan](investment_acceptance_proposal.md)
proposes a stricter investment-fit review and recommends keeping the final
holdout reserved while assessing that mismatch. It supersedes the immediate
next-step recommendation below, without changing any original results or
the C-R4 screening decision.

## Data audit and interpretation limits

All twelve declared instruments passed the primary coverage check:
**AAPL, MSFT, JPM, JNJ, XOM, WMT, CAT, PG, NEE, SPY, QQQ, IWM**.
Each extension contains **754 daily SIP/all-adjusted candles**: 252 in 2016,
251 in 2017, and 251 in 2018, from January 4, 2016 to December 31, 2018.
The saved Alpaca session calendar covers 2016-2023. Validation checked
checksums, aware timestamps, duplicates, OHLC, prices, volume, exact session
dates, and complete scheduled coverage. Holidays are excluded by that
calendar. No candles were fabricated, filled, or removed. The fallback
scope was unnecessary.

PG retained two volume warnings: 93,337,602 on September 28, 2016 and
123,971,668 on September 30, 2016, both above ten times its positive median.
P&G's [September 30 exchange-offer release](https://www.sec.gov/Archives/edgar/data/80424/000119312516726791/d415179dex991.htm)
and [completion filing](https://d18rn0p25nwr6d.cloudfront.net/CIK-0000080424/37ef699a-3446-42d4-b0dc-513caed45a01.html)
document its large Coty-related share exchange around those dates. That is
plausible event context, not independent confirmation of the exact provider
volumes. Both days are in the warmup year. Existing JNJ 2023 volume warnings
also remain in the old datasets and joined replay. Large price movements
are retained rather than clipped merely because a stock moved sharply.

The primary score is **2017-2018**, after 2016 indicator warmup. The second
score is one continuous **2017-2023** account using the new extension and the
unchanged 2019-2023 datasets. Each instrument has 2,012 joined candles.
Holdings, cash, the equity peak, and permanent halts carry across years.
Independent old two-year account results cannot be added to this replay.

These are **backward historical robustness checks**, not genuine historical
walk-forward or fresh forward out-of-sample evidence: the rule and sizing
were chosen using years later than 2017-2018. The fixed present-day survivor
basket excludes delisted stocks and has overlapping ETF/stock exposures.
All-adjusted provider histories are not point-in-time corporate-action data;
adjusted prices and integer shares are an approximation to historical
execution. Full earlier-period IEX coverage remains unavailable. Costs,
stop fills, and daily-bar execution are scenarios, not broker observations.
The old CSV hashes were also checked against C-R3: all twelve are unchanged.

## Rules, costs, and reproducibility

The candidate buys a completed-close breakout above the preceding 55-session
high, with the stock and SPY above EMA200. It exits on the preceding
20-session low, the stock/market filter turning off, or a fixed initial
three-ATR14 stop. Discretionary orders fill no earlier than the next session;
the original planned share quantity may shrink, never expand at the open.
There is a ten-complete-session reentry cooldown. Sells and stops continue
after an entry halt.

Sizing remains `min(5%, 1% / annualized_20_return_volatility)`, with 35%
portfolio entry exposure, 0.5% planned stop risk, and at most seven positions.
Daily 3% and drawdown 10% entry halts stay latched. These are experimental
research settings, not approvals for `config/risk_limits.json`.

The references are the same breakout with 10%/70%/1% allocation limits and
the original trend/RSI/volume rule without a protective stop. Optimistic
costs are zero modeled fees/spread/slippage. Base costs are 5 bps adverse
slippage plus 2 bps full spread. Pessimistic costs are 20 bps adverse slippage,
10 bps full spread, and $1 per order. Half the spread is charged per side.

The C-R3 candidate's metric fields and fills reproduced **exactly** on both
old windows and every cost case before scoring the new history. The study
contains 40 strategy simulations: six reference replays, 18 main runs, and
16 stress runs. Passive SPY and bootstrap calculations are additional.

## Candidate results

Each main window starts with $100,000. Returns include the stated modeled
entry/exit costs and mark any remaining holdings at the final close.

| Window | Optimistic total | Base total | Pessimistic total | Pessimistic CAGR | Pessimistic max closing drawdown | Closed trades |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2017-2018 | +4.308% | +4.010% | **+2.972%** | +1.475% | -4.437% | 50 |
| 2017-2023 continuous | +21.210% | +20.089% | **+16.392%** | +2.192% | -4.584% | 163 |

The new-only account ended at **$102,971.71** under pessimistic costs.
All positions had closed, so the **$2,971.71 gain is realized**; no final
liquidation charge remains. Fifty trades closed across all twelve instruments,
with profit factor 1.576 and mean calendar holding time 68.92 days (about
1,654 hours). Mean closing exposure was 23.27%, and the worst closing day
was -1.289%. No daily or drawdown halt occurred.

The seven-year account ended at **$116,392.02**: realized gains of
**$14,285.08** plus **$2,106.94** marked unrealized gains. Estimated adverse
costs to close the seven remaining positions are $100.26, producing a
hypothetical liquidated return of **+16.292%**. This is an approximation,
not a guaranteed sale at the closing price. Completed-trade profit factor
was 1.973 and mean holding time was 61.42 calendar days (about 1,474 hours).
Mean exposure was 19.07%; the worst closing day was -1.660%. There were no
daily halts, drawdown halts, or blocked sessions in any candidate cost case.

### Annual returns in the continuous candidate account

| Year | Pessimistic return | Entry-halt status |
| --- | ---: | --- |
| 2017 | +4.856% | No halt |
| 2018 | **-1.797%** | No halt |
| 2019 | +3.716% | No halt |
| 2020 | +4.419% | No halt |
| 2021 | +4.179% | No halt |
| 2022 | **-2.639%** | No halt |
| 2023 | +2.900% | No halt |

The long replay does not erase losing years. In particular, its 2022 return
differs from the independent C-R3 2022-2023 account because the joined run
carried holdings and account state from 2021. CAGR is geometric annual growth
over the full calendar window, not total return divided by the year count.

The 2.19% pessimistic CAGR is modest. A low drawdown at roughly 19% average
exposure does not establish superior stock selection, an attractive return
on all capital, or a safe maximum loss. Cash yield, taxes, inflation, and
some real execution effects remain omitted.

## Strategy and passive references

Pessimistic main results:

| Window / arm | Total return | Max closing drawdown | Permanent entry halt |
| --- | ---: | ---: | --- |
| 2017-2018 candidate | +2.972% | -4.437% | None |
| 2017-2018 full breakout | +7.167% | -9.379% | None |
| 2017-2018 original rule | +10.790% | -10.114% | Drawdown, 2018-06-28 |
| 2017-2023 candidate | +16.392% | -4.584% | None |
| 2017-2023 full breakout | +22.110% | -9.733% | Daily loss, 2020-06-11 |
| 2017-2023 original rule | +10.790% | -10.114% | Drawdown, 2018-06-28 |

Higher raw reference returns came with greater exposure and losses. The full
breakout's worst closing day was **-3.358%** in the long replay. Its 2021,
2022, and 2023 returns were all zero while the halt stayed active. The
original rule's 2019-2023 returns were zero under pessimistic costs for the
same reason. These are halted-account years, not successful active trading
or evidence of resilience. Stops and ordinary exits continued after the
halts. No automatic restart or annual risk reset was introduced.

Under optimistic/base costs, the original rule instead hit its permanent
drawdown halt on January 28, 2019. Different costs can change whether a
threshold is reached and therefore change later trading opportunities;
returns need not move smoothly with each extra basis point of cost.

| Passive reference | 2017-2018 pessimistic return | Drawdown | 2017-2023 pessimistic return | Drawdown |
| --- | ---: | ---: | ---: | ---: |
| SPY, 35% initial capital | +5.100% | -8.039% | +47.537% | -15.478% |
| SPY, 70% initial capital | +10.229% | -14.601% | +95.340% | -26.552% |
| Zero-yield cash | 0% | 0% | 0% | 0% |

The 35%-initial-SPY reference averaged 45.67% exposure over seven years,
versus the candidate's 19.07%, and had no matching halt, diversification,
or position cap. Neither passive strategy rebalanced. This comparison
shows the opportunity cost of low exposure but does not establish equal-risk
outperformance by either strategy. Estimated final exit costs reduce the
long passive returns to +47.330% and +94.926%, respectively. All three
cost cases are retained in the full report.

## Frozen stress checks and uncertainty

Each diagnostic below scores 2017-2018 with pessimistic costs and a fresh
$100,000 account. The 55/20 candidate remains unchanged.

| Diagnostic | Return | Max closing drawdown |
| --- | ---: | ---: |
| Main candidate | +2.972% | -4.437% |
| Reverse simultaneous BUY priority | +3.807% | -4.677% |
| Extra session delay plus 50 bps adverse stop slippage | +3.215% | -4.403% |
| Worst return after one instrument removal: AAPL | +2.173% | -4.881% |
| Faster 40/15 channel neighbor | +3.608% | -4.516% |
| Slower 70/25 channel neighbor | +2.349% | -4.436% |

All twelve single-instrument removals stayed positive, from +2.173% to
+4.332%. Their worst drawdown was -4.913% when JPM was removed. SPY remained
available as market context even when excluded from trading. No priority,
delay, removal, or channel-neighbor run hit a permanent halt. A delay doing
better in this sample is not a recommendation to delay orders: different
entry/exit timing changes which price path a strategy experiences.

The paired 20-session circular bootstrap used 2,000 draws and seed 20261023.
Against zero-yield cash, the observed candidate advantage was **+2.972
percentage points**, with a descriptive 95% range of **-5.744 to +11.791
points**. Against full breakout allocation, the observed difference was
**-4.195 points**, with a range of **-16.475 to +5.708 points**. Both ranges
include zero. These sample intervals are conditional on this selected rule
and survivor basket, not selection-adjusted significance tests or proof of
a reliable excess return. They do not include uncertainty about future
costs, missing historical universes, or regime changes.

All ten protocol checks passed: positive new-period return after estimated
exits, drawdown below 10%, no permanent halt, at least 20 completed trades
across five instruments, positive priority/delay/removal returns with
drawdown below 10%, positive returns for both channel neighbors, and a
positive continuous return after estimated exits without a permanent halt.
The primary two-year scope was complete; no fallback was used.

This result strengthens the frozen conservative hypothesis. It does **not**
repair C-R2's failed earlier-period selection and negative faster-channel
result in 2022-2023, remove C-R3's two-year dependence on open profits, or
turn this backward check into untouched forward evidence. No strategy,
symbol, sizing target, or halt threshold was changed after these results.

Local ignored artifacts:

- `data/reports/study_c_r4_coverage.json`: immutable coverage choice and audit.
- `data/historical/calendar_2016_2023_study_c_r4.json`: broker session snapshot.
- `data/reports/study_c_r4/report.json`: full report, manifests, source and data
  hashes, package versions, metrics, fills, equity paths, and screening checks.
- `data/reports/study_c_r4/{window}_{arm}.json`: individual main arm results.

Run from the repository root using an installed base environment and the
earlier Study C datasets plus the C-R3 reference report:

```powershell
.venv\Scripts\python.exe -m backtesting.earlier_history download --output data/reports/study_c_r4_coverage_new.json
.venv\Scripts\python.exe -m backtesting.earlier_history run --coverage data/reports/study_c_r4_coverage_new.json --output-dir data/reports/study_c_r4_new
.venv\Scripts\python.exe -m unittest tests.test_earlier_history tests.test_allocation_research tests.test_daily_research tests.test_portfolio_backtesting
```

Download uses read-only Alpaca data/calendar requests; run is entirely offline.
Choose fresh report paths; existing accepted CSVs may be reused only after
checksum and calendar validation. On the Pi use its own environment's
`python -m ...` equivalent. Git does not transfer the ignored datasets and
reports: copy the audited research artifacts separately or reproduce them.
Never copy the Windows virtual environment or commit API keys.

The protocol SHA-256 is
`37f38f12f700d1d82ec0d90d2742d8c7fc02bf53f96bb3ec6db71a79dc6f6368`.
The calendar contains 2,012 sessions; its SHA-256 is
`6ee26a1a13c55f83113e113e6260a1d8bf5134c6c9fd90daa491d473b60b69e1`.
The recorded environment was Python 3.12.3, NumPy 2.5.3, pandas 2.3.3,
and alpaca-py 0.10.0. No packages were installed for this study.

## Implementation and tests

`backtesting/earlier_history.py` separates read-only coverage acquisition
from offline scoring. It saves the session calendar, validates both
segments and their join, rejects provenance changes, preserves warnings,
checks warmup, and records annual halt status. The existing allocation
runner now accepts an optional breakout-channel configuration for the two
registered neighbors; its default remains 55/20. The six exact C-R3 replays
confirm that this extension did not change the candidate reference results.

**74 focused tests passed**, including **15 new tests** for calendar bounds,
holiday versus missing-session gaps, duplicate/unordered/naive sessions,
exclusive date boundaries, checksums, feed conventions, dropped symbols,
overlap/gaps at the join, incomplete-coverage refusal, protocol/calendar
mutation, retained halt years, CAGR, and default/neighbor rule forwarding.

The full suite ran **209 tests: 207 passed and two errored**. Both errors are
the existing optional ML tests importing absent `scikit-learn`; no assertion
failed. The final 15-test new suite was rerun successfully after refining a
CAGR fixture. Pi execution was not performed; Windows ran this research.

## Next work and owner decisions

The next implementation should prepare a **frozen final-evaluation protocol
and preflight checklist** for this exact candidate, with the original rule,
full breakout, cash, and passive references clearly distinguished. It should
state how to reject an inadequate result, how to handle data gaps and halts,
and what would invalidate the claim that 2024-2025 are untouched. Do not
open those prices simply to find a more attractive result. ML remains
deferred; a broader search would add selection risk.

**Codex:** Prepare that reviewable protocol and the guarded evaluation
command. Keep paper submission disabled. Separately finish broker protective
exits, the fill/activity ledger, and operational recovery checks before an
unattended loop can place orders.

**Owner:** Review whether this fixed basket and modest all-capital return
are useful for your goals, and decide the acceptable losses/drawdown and
evaluation criteria before the final period is inspected. I can propose a
concrete decision sheet; you do not need to code or download data. Your
personal risk JSON can remain incomplete while offline tooling is built,
but it must be explicitly completed/approved before any paper order. Scope,
results, paper-account state, successful recovery, and the paper-start
decision are separate checks in [your responsibilities](owner_responsibilities.md).

# Study C-R3 allocation and halt/restart results

Completed 2026-10-23 under the [registered protocol](study_c_allocation_protocol.md).
**Smaller allocations reduced losses and gains. The earlier-selected volatility
policy passed this allocation screen, but it is not a passed paper-trading
candidate.** The breakout strategy's negative 2022 result, parameter sensitivity,
small sample, and dependence on open gains remain concerns. No broker orders,
paper approvals, or production kill-switch resets occurred. 2024-2025 remain
unopened.

For the original five strategy definitions and examples of breakout exits,
see [the strategy guide](five_daily_strategies_explained.md).

## Fixed design and reproducibility

All six policy arms used the **same 55/20 breakout**, SPY/EMA200 filter,
fixed initial three-ATR14 stop, and ten-session reentry cooldown. The three
allocation choices were 10% position / 70% total entry caps, half-sized
5% / 35% caps, and volatility sizing below the same 5% / 35% caps. Smaller
allocations used a 0.5% planned stop-risk cap versus the 1% reference cap.
For each allocation, compare a lasting daily halt with a five-session pause
and prior-session market review proxy. All retain 3% daily and 10% drawdown
thresholds, with permanent drawdown halts.

The final run made **64 strategy simulations**: 36 main runs (six policies,
three cost cases, two windows), 16 selected-policy stress runs, and 12 matched
signal-feed runs. Cash and passive SPY references were also calculated.
All old C-R2 fixed-stop breakout metric fields and fills matched exactly in
both windows under all three cost scenarios before accepting new results.
The existing datasets and their validation warnings were preserved.

The complete ignored local report is
`data/reports/study_c_r3_final/report.json`. It contains manifests, dataset
and source hashes, fills, daily equity, costs, risk events, the earlier-period
selection, and failed/passed checks. The protocol hash is
`51f4cdff6e295e0aa0b6ad2b0ceef590cbfb3ed976753721b7679689f05c0e5c`.

## Earlier-period selection: 2020-2021

Each window starts a fresh $100,000 account. Within a window, positions and
the closing equity peak carry across years. The 2019 data supplies warmup.
Selection used only 2020-2021 and was written before scoring new policies on
2022-2023. These years are research/development data, not fresh final tests.

Pessimistic costs mean 20 bps adverse slippage, 10 bps full spread (half per
side), and $1 per order. They are scenarios, not verified broker execution.

| Policy | 2020 | 2021 | Total | Max closing drawdown | Worst closing day | Daily halts / restarts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Full, lasting halt | +4.439% | 0.000% | +4.439% | -7.606% | -3.356% | 1 / 0 |
| Full, five-session pause | +9.569% | +10.568% | +21.149% | -7.711% | -3.356% | 2 / 2 |
| Half, lasting halt | +4.170% | +3.976% | +8.311% | -4.090% | -1.721% | 0 / 0 |
| Half, five-session pause | +4.170% | +3.976% | +8.311% | -4.090% | -1.721% | 0 / 0 |
| Volatility, lasting halt | +4.319% | +4.093% | +8.590% | -4.100% | -1.665% | 0 / 0 |
| Volatility, five-session pause | +4.319% | +4.093% | +8.590% | -4.100% | -1.665% | 0 / 0 |

The full-allocation arms were diagnostic references, ineligible for selection.
The four smaller arms passed the earlier gates. **`vol_latched`** was selected
by the frozen worst-year-return rule. Its results tied its paused counterpart
because neither halted; lexical tie-breaking chose the lasting halt. The
small return difference from fixed half-sizing is not proof that volatility
sizing is generally superior.

The volatility formula is `min(5%, 1% / annualized_20_return_volatility)`.
For estimated annual volatility of 20%, the weight is capped at 5%; for 40%,
it is 2.5%. This 1% input is a sizing proxy for annualized return variability,
not a maximum loss or a promised portfolio volatility. Stop risk, cash, and
shared exposure caps can reduce the quantity further. Existing holdings are
not rebalanced each day.

## What the restart simulation showed

The full paused arm halted on **2020-06-11** and **2020-09-03**. It resumed at
the opens of **2020-06-19** and **2020-09-14**, respectively, after five full
market sessions and the exact previous session's SPY review. Weekends and
holidays did not consume pause sessions. Resumption did not reset the equity
peak, bypass a drawdown halt, or restore old BUYs. A fresh completed-close
signal was required before a new BUY could fill.

Those restarts explain the much higher full-paused earlier return: that arm
could trade the remainder of 2020 and 2021. It still had a day worse than the
3% threshold. A halt reacts after a loss is observed; it cannot guarantee a
maximum realized loss. The review proxy is a deterministic simulation, not
evidence of successful human incident review or permission to reset a real
kill switch.

Smaller allocations did not hit daily halts in either main window, so their
paused and lasting versions are identical here. There is **no measured benefit
from automatic restarts for the selected smaller policy** in this sample.

## Later development: 2022-2023

These returns use one continuous account within 2022-2023 and mark remaining
holdings at the last 2023 close. No forced year-end liquidation is assumed.

| Policy | Optimistic total | Base total | Pessimistic total | Pessimistic 2022 | Pessimistic 2023 | Pessimistic max drawdown | Worst closing day |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Full, lasting halt | +5.606% | +5.054% | **+3.209%** | -3.742% | +7.221% | -7.792% | -1.231% |
| Full, five-session pause | +5.606% | +5.054% | **+3.209%** | -3.742% | +7.221% | -7.792% | -1.231% |
| Half, lasting halt | +2.799% | +2.489% | **+1.563%** | -1.868% | +3.496% | -3.948% | -0.606% |
| Half, five-session pause | +2.799% | +2.489% | **+1.563%** | -1.868% | +3.496% | -3.948% | -0.606% |
| Volatility, lasting halt | +2.372% | +2.121% | **+1.280%** | -1.577% | +2.903% | -3.457% | -0.518% |
| Volatility, five-session pause | +2.372% | +2.121% | **+1.280%** | -1.577% | +2.903% | -3.457% | -0.518% |

Optimistic uses zero modeled costs; base uses 5 bps slippage and 2 bps full
spread with no commission. All six arms closed 42 trades in this window.
No daily or drawdown halt occurred. Their mean closing exposures were
approximately **20.58%, 10.26%, and 9.28%** for full, half, and volatility
allocations. The caps are maximums at entry, not target exposure levels.

The fixed half allocation earned more than volatility sizing in this later
window. We did not switch the earlier-selected policy based on that result.
The selected policy reduced absolute drawdown and daily losses while reducing
return; it did not discover a stronger predictive signal.

### Realized and open P&L

The selected policy ended at **$101,279.90** under pessimistic costs. Completed
trades realized **-$561.19**; seven remaining holdings were marked at
**+$1,841.09** unrealized P&L. Their combined result is the +1.280% account
return. Charging another **$88.23** in estimated adverse sale costs at the
observed closes gives a hypothetical liquidated return of **+1.192%**.
This is a diagnostic, not a guaranteed closing-price sale.

Only 11 of 42 closed trades won; closed-trade profit factor was **0.867**.
Completed trades averaged 29.71 calendar days across all symbols. These
metrics and the dependence on open gains remain weaknesses despite the
successful loss reduction.

## Selected-policy stress checks

The settings chosen on earlier years stayed fixed. Each result below uses
pessimistic costs in 2022-2023. Neighboring volatility targets are diagnostics;
the best observed target was not promoted.

| Diagnostic | Account return |
| --- | ---: |
| Main selected policy | +1.280% |
| Reverse BUY priority | +1.232% |
| Extra session of order delay plus 50 bps adverse stop slippage | +0.638% |
| Worst of 12 single-symbol removals: remove QQQ | +0.174% |
| Lower 0.75% volatility-contribution target | +0.881% |
| Higher 1.25% volatility-contribution target | +1.569% |

All these returns were positive and drawdowns stayed below 10%, so the
selected policy passed the **allocation screen**. The worst removal result
is small enough that unmodeled costs could readily matter. None of these
checks repairs C-R2's losing faster-channel result, creates a genuinely fresh
test, or demonstrates profitable closed trades.

The observed pessimistic return difference from full allocation was **-1.93
percentage points**. A paired 20-session circular-block bootstrap gave a
95% descriptive range from **-9.98 to +5.01 percentage points**. Lower
exposure changes both returns and risk; this interval is not an equal-risk
alpha test or selection-adjusted significance result.

## Feed and passive references

The 2023-only feed comparison uses matching March 2022 warmup and fresh 2023
accounts. Both signal feeds use the same SIP execution bars. All data is
calendar-aligned; no missing candle is filled. The previously recorded JNJ
volume warnings remain in dataset provenance.

| Allocation (either halt mode) | SIP signals / SIP execution | IEX signals / SIP execution |
| --- | ---: | ---: |
| Full | +7.245% | +7.307% |
| Half | +3.495% | +3.525% |
| Volatility | +2.859% | +2.936% |

The selected sizing rule showed a modest signal-feed difference in this
window. These returns do not replace the continuous two-year result; cash,
holdings, and warmup differ. Complete full-period IEX coverage is still absent.

A passive SPY reference initially allocating 35% returned **+0.941%** over
2022-2023 under pessimistic costs, with **-8.565%** maximum drawdown. At a
70% starting allocation it returned +1.884%, with -17.128% drawdown. These
references had roughly 32.3% and 67.3% mean exposure, versus 9.28% for the
selected active policy, and no matching position or halt policy. They provide
context, not a matched-risk ranking. Cash earns zero interest in this model;
inflation, taxes, and realistic cash yield are omitted.

## What is next and who does it

Retain **55/20 fixed-stop breakout + selected conservative sizing** as a
frozen research hypothesis. The next proposed work is to audit additional
earlier historical coverage and evaluate it across more market regimes,
with explicit data and universe limitations. Keep 2024-2025 reserved until
the candidate, costs, and evaluation criteria are frozen for final testing.
Avoid adding more thresholds or an ML filter simply to improve the old chart.
The R2 negative-year and channel-sensitivity failures remain on record.

Codex can implement the coverage audit and simulations. The owner can review
these findings without changing configuration. Personal risk limits still
need an explicit owner decision before paper activation; the tested 5%/35%
caps are research scenarios, not new approved defaults. A real restart policy,
safe broker exits, fill accounting, and readiness review remain separate
requirements in [owner responsibilities](owner_responsibilities.md).

## Implementation and verification

`backtesting/research_policy.py` isolates research allocation and halt state.
`backtesting/allocation_research.py` defines the finite study and audit log.
The existing portfolio engine accepts these optional policies while preserving
the reference financial results. It records first halt, current halt state,
permanent reason, restart events, and sessions blocked at the open. The legacy
`entry_halted_at` metric means **first halt**, not current state after a resume.
The production risk configuration and persistent kill switch were not changed.

From the repository root, after the existing SIP/IEX files and the R2 reference
report have been obtained/generated locally:

```powershell
.venv\Scripts\python.exe -m backtesting.allocation_research --output-dir data/reports/study_c_r3_new
.venv\Scripts\python.exe -m unittest tests.test_allocation_research tests.test_daily_research tests.test_portfolio_backtesting -v
```

Choose a new output directory. On the Raspberry Pi use its environment's
`python -m ...` equivalent; ignored data and JSON reports are not transferred
through Git. The report records Python, package, dataset, protocol, and source
versions/hashes. The final environment was Python 3.12.3, NumPy 2.5.3,
pandas 2.3.3, and alpaca-py 0.10.0.

**59 focused tests passed**, including 20 new allocation/restart cases. The
full run executed **194 tests: 192 passed, two errored** because optional ML
tests import `scikit-learn`, which is absent from this environment. No test
assertion failed in the final run. The new tests cover exact loss thresholds,
permanent drawdown halts, repeated daily breaches, pause length, prior-date
review, fresh orders after resumption, continued sells, canceled delayed BUYs,
volatility warmup, caps, future-data invariance, and earlier-only selection.

An initial attempt was stopped before completing the study to fix an exact
10% floating-point boundary in the halt comparison. The final run compares
equity directly with dollar thresholds, reproduces all reference metrics and
fills, and uses the same six frozen policy arms. The partial
`data/reports/study_c_r3/` attempt is superseded by `study_c_r3_final/`.

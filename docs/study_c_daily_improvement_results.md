# Study C-R2 daily improvement results

**Later follow-up:** The separately registered
[C-R3 allocation study](study_c_allocation_results.md) completed the proposed
sizing and daily halt/restart comparison. It passed an allocation screen
with smaller gains and losses; the strategy concerns recorded here remain.

Completed on 2026-10-23 under the [frozen protocol](study_c_daily_improvements.md).
**There is a useful improvement, but no selected or paper-ready candidate.**
Slower breakout entries roughly halved completed trades and improved the
2022-2023 pessimistic account return from -0.524% to +3.209%. They still
lost in 2022, had slightly worse maximum drawdown, and failed a neighboring
parameter check. No risk settings were approved and no orders were placed.
2024 and 2025 remain unopened.

## What was built and compared

The study made **86 strategy simulations**: five arms across three cost cases
in each of two chronological windows, 46 robustness runs, and ten separate
2023 signal-feed comparisons. It also calculated passive SPY and cash
references. Every result used shared cash, next-session execution, position
and loss limits, and separate realized/open P&L. No dataset gaps were filled.
The original Study C metrics and every fill matched exactly under all three
cost cases before the new variants were accepted.

The new offline modules are `backtesting/daily_strategies.py` and
`backtesting/daily_research.py`. Small additions to the existing simulator
support fixed initial stops, a different trailing distance, reentry pauses,
delayed execution, and separate signal/execution feeds. No optional ML
packages are needed for this study.

The main runs share one $100,000 account from 2022-01-01 through 2024-01-01
exclusive and use 2019-2021 for warmup. Annual returns compound; the 2023
account inherits 2022 holdings and equity. These development years had
already influenced the research direction and are not independent holdouts.

## The earlier-period selection returned no candidate

Selection was recorded using **2020-2021 only**, before the new arms were
scored on 2022-2023. No candidate met the protocol's earlier-year criteria.

| Arm | 2020 pessimistic return | 2021 return | Completed trades | Entry halt |
| --- | ---: | ---: | ---: | --- |
| Original baseline | +8.137% | 0.000% | 22 | 2020-06-11 |
| Baseline without volume | +7.303% | 0.000% | 24 | 2020-06-11 |
| Market-filtered trend | +3.241% | 0.000% | 27 | 2020-06-11 |
| Breakout, fixed stop | +4.439% | 0.000% | 17 | 2020-06-11 |
| Breakout, trailing stop | +2.907% | 0.000% | 18 | 2020-06-11 |

On June 11, the arms lost approximately **3.03%-3.70% in one account day**.
Their prior closing exposures were about 64%-71%. The existing provisional
3% daily-loss rule blocks future entries for the rest of a simulation; it
does not automatically resume the next day. Holdings could still exit, but
there was no 2021 trading. The zero 2021 returns reflect that halted policy,
not evidence that an active strategy would have broken even that year.
Both breakout arms also fell short of the 20-completed-trade requirement.

We retained the halt rather than resetting it after seeing the result.
A future risk-policy study needs to distinguish allocation, correlated
exposure, daily loss protection, and explicitly reviewed restart behavior.
The 70% exposure limit is a ceiling, not a suggested target allocation.

## Later development results

All figures below include the stated transaction costs. They are changes
in the entire simulated account, including the marked value of open
positions. DD means the largest peak-to-trough fall in closing account value.

| Arm | Optimistic total | Base total | Pessimistic total | Pessimistic 2022 | Pessimistic 2023 | Pessimistic max DD | Closed trades |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original baseline | +3.876% | +2.841% | **-0.524%** | -3.928% | +3.543% | -7.644% | 83 |
| Baseline without volume | +4.170% | +2.895% | **-0.849%** | -5.611% | +5.045% | -8.958% | 100 |
| Market-filtered trend | -0.549% | -1.549% | **-7.282%** | -6.348% | -0.997% | -10.079% | 59 |
| Breakout, fixed stop | +5.606% | +5.054% | **+3.209%** | -3.742% | +7.221% | -7.792% | 42 |
| Breakout, trailing stop | +5.576% | +5.026% | **+3.179%** | -3.965% | +7.439% | -7.997% | 42 |

Optimistic means zero modeled spread/slippage/commission. Base means 5 bps
slippage and 2 bps full spread. Pessimistic means 20 bps slippage, 10 bps full
spread, and $1 per order. Half the spread is applied on each side in addition
to adverse slippage. These are scenario assumptions, not verified fills.
The market-filtered trend reached its drawdown entry halt on 2023-04-12.

Removing volume alone did not help. Adding market filtering to the faster
trend rules also did not help. The two breakout variants improved the
pessimistic two-year result by approximately **3.7 percentage points** and
reduced traded notional from about $1.62 million to $0.87 million. Their
mean closing exposure was about **20.5%**, compared with 41.0% for baseline.
That is a material exposure difference; this study does not isolate each
individual rule's contribution to the improvement.

### How the breakout exits work

Entry requires a completed close above the **preceding 55-session high**,
above the symbol's EMA200, and a positive SPY trend (SPY above its EMA200).
Today's high is excluded from the historical entry channel.

After entry, sell at the next available open if the completed close falls
below the **preceding 20-session low**, below EMA200, or SPY's trend turns
off. These exits apply to winning and losing positions. There is no fixed
holding period. A stop initially placed three ATR14 values below the
signal close provides another modeled exit. ATR measures recent daily price
movement; a wider multiple gives the trade more room before an exit.

The trailing variant raises that stop after a completed close to at least
close minus four ATR14 values, effective next session. A gap below the stop
is priced at the opening price with adverse costs. Both variants wait ten
complete sessions after any exit before allowing another entry in that stock.
Actual broker protective stops and their lifecycle remain separate work.

The fixed-stop variant held completed trades for **29.71 calendar days on
average across all symbols** (about 713 hours). Only 11 of its 42 closed
trades won under pessimistic costs; low win rate can coexist with a few
larger gains, but it is not proof of a usable edge.

### Open positions still matter

Under pessimistic costs, the fixed-stop breakout ended at **$103,209.25**.
Closed trades realized **-$970.15**, while seven open positions contributed
**+$4,179.40** of marked unrealized P&L. Charging an estimated **$188.52**
of adverse exit costs at the final observed closes reduces the hypothetical
result to **+3.021%**. This is a liquidation diagnostic, not an executable
closing-price claim; the future value of the positions remains unknown.
The trailing variant's corresponding hypothetical result is +2.990%.

For context, a 70%-initial-allocation SPY buy-and-hold reference returned
**+1.884%** under pessimistic costs, or +1.703% after the same type of exit
cost estimate, with **-17.128%** maximum drawdown. It had about 67.3% mean
closing exposure and different concentration and risk rules. Cash earned
zero interest in this simulation. Neither reference is an equal-risk proof
that the new rule outperforms a passive investment.

## Robustness checks

All figures in this table are pessimistic two-year returns. The delay stress
fills discretionary orders two sessions after their signal rather than one,
keeps the original planned quantities, and adds 50 bps adverse stop slippage.
Existing protective stops remain active during delayed exits.

| Arm | Reverse BUY priority | Delay + worse stops | Worst of 12 symbol removals | 40/15 channels | 70/25 channels |
| --- | ---: | ---: | ---: | ---: | ---: |
| Market-filtered trend | -4.426% | -9.876% | -10.144% (remove XOM) | N/A | N/A |
| Breakout, fixed stop | +2.957% | +1.755% | +1.039% (remove QQQ) | **-0.344%** | +3.287% |
| Breakout, trailing stop | +2.942% | +2.054% | +1.020% (remove QQQ) | **-0.348%** | +3.435% |

Both breakout designs stayed positive when any single tradable symbol was
removed. SPY still supplied market context when excluded from trading.
That is encouraging for concentration, but the faster-channel losses reveal
sensitivity to the rule's time horizon. Do not select the 70/25 neighbor just
because its return looks better here. The fixed settings remain 55/20.

The paired 20-session block bootstrap's 95% descriptive range for the
fixed-stop breakout's pessimistic return difference against baseline was
**-11.40 to +16.77 percentage points**, around an observed +3.73 points.
The trailing variant's range was -11.40 to +16.58 points. Both include zero
and substantial underperformance. These intervals describe this short sample;
they do not correct repeated research choices or establish significance.

## Signal-feed check with identical execution prices

The 12 new IEX datasets each passed validation with **456 complete sessions**
from 2022-03-09 through 2023-12-29. The first 206 sessions provide matching
warmup; a fresh $100,000 account trades only 2023. Both signal-feed runs use
the **same SIP OHLC for execution and marking**, so differences arise from
the signal feed and its derived stop/quantity decisions. This improves on
the earlier feed audit, which changed the execution-price proxy too.
The four original JNJ SIP volume warnings and one JNJ IEX volume warning
remain recorded in provenance; their event-period explanation and remaining
uncertainty are described in the [feed audit](study_c_feed_audit.md).

| Arm | SIP signals, SIP execution | IEX signals, SIP execution |
| --- | ---: | ---: |
| Original baseline | +2.777% | +3.783% |
| Baseline without volume | +4.758% | +4.428% |
| Market-filtered trend | +1.615% | +1.317% |
| Breakout, fixed stop | +7.245% | +7.307% |
| Breakout, trailing stop | +7.471% | +7.555% |

The breakout rules were less sensitive to feed changes in this limited
window. The full 2022-2023 IEX replay remains unavailable because of the
previously documented gaps. These are 2023-only fresh-account results and
must not replace the main continuous two-year figures.

## Decision and what to do next

**No candidate passed the frozen development screen or earlier selection.**
The breakout variants fail the requirement for nonnegative returns in both
later years, their maximum drawdown is slightly worse than baseline, and a
channel sensitivity run loses money. The earlier selection also failed on
daily-loss halts and sample size. A prettier two-year total does not clear
those recorded criteria. The evidence supports retaining the breakout design
as a research hypothesis; the no-volume-only and faster-trend variants offer
no improvement in this study.

The next proposed work is a **separate portfolio-allocation and restart-policy
study**, with a frozen protocol before running it. Investigate lower or
volatility-scaled allocations under the same existing loss ceilings, rather
than treating 70% exposure as a target or raising loss limits to make the
results pass. Specify how a daily halt is reviewed and resumed separately
from a drawdown halt. Keep the 55/20 breakout fixed during that study and
include passive references. More complete earlier history and a larger,
point-in-time universe would then strengthen evidence before final holdout
evaluation. ML remains deferred.

Codex can implement and simulate that work. The owner does not need to choose
personal paper limits to perform an offline comparison. Before paper activation,
the owner still reviews the research, selects or accepts actual limits, reviews
account/recovery state, and explicitly starts the trial as described in
[owner responsibilities](owner_responsibilities.md). Safe broker exits and fill
accounting also remain unfinished prerequisites for an unattended loop.

## Reproduction, artifacts, and tests

The complete machine-readable report is ignored by Git:
`data/reports/study_c_r2_final/report.json`. The directory also preserves the
earlier-period selection (written before new later-arm scoring), baseline
regression, each arm's development results, and robustness reports. Reports
include dataset and source-code checksums, fills, daily equity, costs,
selection checks, and all failures. The protocol SHA-256 is
`39b498cbef5dd15eff39e2d706ce74910bc22aced63cb0a6f36d3032d69e239c`.

From the repository root, with the existing Study C SIP data and original
`study_c_shared_cash_close_planned.json` reference present:

```powershell
.venv\Scripts\python.exe -m backtesting.daily_research --output-dir data/reports/study_c_r2_new --iex-dir data/historical
.venv\Scripts\python.exe -m unittest tests.test_daily_research tests.test_portfolio_backtesting -v
```

Choose a new output directory. Obtain each short-window IEX dataset using
the existing downloader; repeat this example for all 12 declared symbols:

```powershell
.venv\Scripts\python.exe -m backtesting.research download --symbol AAPL --start 2022-03-09 --end 2024-01-01 --timeframe 1Day --feed iex --adjustment all --output data/historical/AAPL_1Day_2022_2023_study_c_r2_iex.csv
```

On the Raspberry Pi, use the local environment's `python -m ...` equivalent.
The ignored datasets and old baseline reference must be downloaded/generated
there as well; Git carries the code, protocol, and this result record. Source
data revisions will change checksums and can invalidate the exact replay.

This run used Python 3.12.3, NumPy 2.5.3, pandas 2.3.3, and alpaca-py 0.10.0.
The fixed present-day basket, adjusted prices, daily-OHLC stop assumptions,
unmodeled corporate-action cash flows, correlated ETFs/stocks, and short
development period remain limitations.

The new focused module contains **21 passing tests** for causal channels and
market context, feed separation, delayed orders, stop behavior during delays,
both types of cooldown, earlier-period selection, holdout guards, bootstrap
pairing, and baseline-format compatibility. An initial study attempt stopped
at the baseline schema check because the oldest report omitted a null stop
field. The restarted run normalized only that absent null metadata; every
original numeric field and fill matched, and no arm settings changed.

The final full discovery run executed **174 tests: 172 passed and two had
environment errors**, both in optional ML tests importing the absent
`scikit-learn` package. No assertion failed. Those dependencies are declared
in `requirements-ml.txt`; this study uses no ML. The focused new-research and
portfolio modules passed all **39 tests**.

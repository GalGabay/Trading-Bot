# Study C-P1: daily protective-exit research variant

**Registered before P1 performance was inspected; development screen failed
on 2026-10-23.** This is a new,
exploratory development study prompted by Study C's dependence on open
end-of-period gains. It does not replace or retroactively improve the
[unchanged Study C baseline](study_c_research_record.md), and it does not
authorize paper orders. No 2024–2025 data will be opened for this run.

## Frozen comparison

Use Study C's same 12 SIP, `all`-adjusted daily datasets; warm up on
2019–2021 and simulate one shared $100,000 cash account continuously from
2022-01-01 to 2024-01-01 exclusive. Keep the default
`trend_following_v1` entry and trend-exit rules, alphabetical buy priority,
the three existing cost scenarios, and the provisional 10% position, 70%
entry-exposure, seven-position, 3% daily-loss, and 10% drawdown gates.
Compare P1 directly with the close-planned baseline under each identical
cost case. Treat 2022 and 2023 as already inspected development years.

P1 adds exactly one fixed protective policy:

1. At a completed BUY-signal close, propose an initial stop **two ATR14
   values below that close**. Reject the BUY if ATR is unavailable or the
   stop is not a valid positive price below the planned entry price.
2. Cap whole-share size so the planned loss from estimated entry to that
   stop is at most **1% of current equity**, as well as meeting the existing
   position, exposure, cash, and position-count gates. If the next open
   raises the entry-to-stop distance, reduce size; never increase the
   share count after seeing the open. Reject an entry whose open is already
   at or below its planned stop.
3. After a BUY fills, the stop is active for that session. A regular-session
   opening gap at or below the stop exits at the **open**; otherwise a daily
   low at or below the stop exits at the **stop level**. Apply the scenario's
   adverse sell spread/slippage and commission. An existing stop gap takes
   precedence over a pending trend-rule SELL; both would otherwise exit at
   that open. Process all exits before competing entries.
4. Only after a session finishes, raise the remaining stop to at least
   `completed_close - 2 × completed_ATR14`; never lower it. This trailing
   update takes effect on the following session. Keep the original trend
   SELL at the next open when it arrives before the stop is hit.

The stop-level fill on an intraday touch is an **OHLC approximation**, not a
replay of the trade sequence or a guaranteed broker fill. A market stop can
execute below its stop price, particularly in a gap or fast market
([FINRA stop-order notice](https://www.finra.org/sites/default/files/notice_other_file_ref/Regulatory-Notice-16-19.pdf)).
Use an additional **50 basis points of adverse slippage on stop exits** as
a separate stress run under base costs; that is a sensitivity assumption,
not a forecast. An opening gap is priced at the open before that extra
adverse amount. Do not assume the 1% sizing cap limits realized losses to
1%; stops, gaps, and execution costs can exceed it.

## Decision rule and audit

Report matched whole-account 2022, 2023, and compounded returns, maximum
drawdown, completed and open trades, realized and marked P&L, stop exits,
gap stops, cost sensitivity, and concentration by symbol. If P1 does not
improve the **pessimistic** whole-account return without worsening maximum
drawdown, it fails this first screen. Even if it passes, one adjusted-feed
development sample cannot approve paper trading. The baseline and variant
must remain distinguishable, and any parameter change becomes a new study.

## Results: 2026-10-23

The baseline was rerun through the expanded engine before P1 was scored.
Its optimistic, base, and pessimistic returns and fill counts matched the
previous Study C shared-cash report **exactly**. This checks that enabling
the optional stop code did not alter the unchanged baseline.

| Cost case | Arm | 2022 return | 2023 return | Two-year return | Max drawdown | Closed trades | Stop exits |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Optimistic | Baseline | -2.027% | +6.025% | +3.876% | -6.109% | 83 | 0 |
| Optimistic | P1 | -2.813% | +5.447% | +2.480% | -7.025% | 142 | 121 |
| Base | Baseline | -2.455% | +5.429% | +2.841% | -6.355% | 83 | 0 |
| Base | P1 | -3.523% | +4.418% | +0.739% | -7.961% | 142 | 121 |
| Pessimistic | Baseline | -3.928% | +3.543% | -0.524% | -7.644% | 83 | 0 |
| Pessimistic | P1 | -5.878% | -4.912% | **-10.501%** | **-11.079%** | 90 | 76 |

Under base costs, P1 had **39 winners among 142 completed trades**. Its
mean completed holding time was **15.69 calendar days**, compared with
31.82 days for the baseline. Of the 121 base-case protective exits, **18**
were modeled opening-gap stops. The base P1 account realized **-$2,653.93**
on completed trades and ended with five open positions marked at **+$3,393.37**
unrealized; the total account return was only +0.739%.

The pessimistic P1 account reached the provisional **10% maximum-drawdown
entry halt on 2023-03-07**. It then accepted no new BUYs, while existing
positions could exit. That explains the smaller pessimistic trade count and
the lack of open positions at the end. The halt is part of the declared
policy, not a data or program error. It does not liquidate positions at the
threshold, and the observed maximum drawdown reached 11.079% before the
remaining exits. The +50-basis-point stop-fill stress under base regular
costs also reached the halt on 2023-03-07 and returned **-10.680%** over
the two years, with **-11.291%** maximum drawdown. Extra stop-fill costs
can therefore change the research outcome materially.

P1 triggered far more exits and re-entries than the baseline. That added
turnover is a plausible driver of its worse cost sensitivity; the result
does not prove that all protective exits are harmful. The P1 rule fails its
predeclared criterion because pessimistic return and maximum drawdown both
worsened. **Do not select P1 for paper trading, loosen its two-ATR stop after
seeing this result and call the rerun a confirmation, or open 2024–2025 to
rescue this design.** Any new stop, profit exit, or cooldown rule needs its
own registered study and later independent evaluation.

The full local reports (ignored by Git) are:

| Report | Content |
| --- | --- |
| `data/reports/study_c_p1_baseline_replay.json` | Exact baseline replay, three cost cases |
| `data/reports/study_c_p1_atr2.json` | P1, three cost cases |
| `data/reports/study_c_p1_atr2_extra50_base.json` | P1 base costs plus 50 bps adverse stop slippage |

Reproduce P1 using the same 12 checked CSVs listed in the Study C record:

```powershell
$symbols = @('AAPL','MSFT','JPM','JNJ','XOM','WMT','CAT','PG','NEE','SPY','QQQ','IWM')
$datasets = @($symbols | ForEach-Object { "data/historical/${_}_1Day_2019_2023_study_c.csv" })
.venv\Scripts\python.exe -m backtesting.portfolio_research --datasets $datasets --trade-start 2022-01-01 --trade-end 2024-01-01 --protective-atr-multiple 2 --max-risk-per-trade 0.01 --output data/reports/study_c_p1_atr2.json
```

Use a new filename if that output already exists. Add
`--scenarios base --stop-extra-slippage-bps 50` to reproduce the separate
stop-fill stress report. The checked datasets still include JNJ's four
unresolved volume-anomaly warnings. The model does not simulate quote-level
stop activation, partial fills, market impact, cash dividends, or a live
broker order lifecycle. Realized loss may exceed the planned 1% risk when a
stop gaps or executes adversely.

## Testing

The focused `tests.test_portfolio_backtesting` module has 18 passing cases
for shared cash, next-open sizing, year-end carry, loss halts, stop touches,
gap fills, trailing updates, stop-risk sizing, and dataset provenance. The
non-ML suite has 142 passing tests. The full 153-test discovery run had two
errors in `tests.test_ml_research` because optional `scikit-learn` is not
installed in this virtual environment; no test assertion failed. Those
optional dependencies are declared in `requirements-ml.txt`.

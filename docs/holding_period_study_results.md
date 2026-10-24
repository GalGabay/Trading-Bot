# Holding-time study results

Completed **2026-10-24** under the [approved amended protocol](holding_period_study_protocol.md).
The owner allowed continuation beyond session 60 when evidence remained
strong, with later reviews every 30 sessions. That amendment was recorded
before evaluating the variants. No hard maximum was used in that arm.

**Decision: neither new arm meets the approved investment criteria.**
Time exits freed position slots and reduced some closing losses, but did
not improve pessimistic net returns over the unchanged control. Do not
promote these variants, loosen the criteria, or open 2024-2025 to rescue them.

## What was implemented

`backtesting/holding_policy.py` isolates the optional holding-age rule.
The shared-cash engine records entry-fill age and cost basis, gives ordinary
exits/stops precedence, and can journal BUY planning/execution constraints.
The default has no holding-age policy. The finite offline runner is
`backtesting/holding_research.py`.

Three arms retained the same 55/20 breakout entries, stock/SPY EMA200
filters, initial three-ATR14 stop, volatility sizing, conservative exposure
and planned stop-risk caps, ten-session cooldown, and latched loss halts:

| Arm | Added holding-age rule |
| --- | --- |
| Control | None |
| Maximum 30 | Queue an exit after held session 30's close |
| Continuation review | Review at sessions 30, 35, 40, 45, 50, 55, 60, then 90, 120, ...; retain only with a fresh prior-20-session high, positive estimated net liquidation profit, and stock/SPY EMA200 filters |

Actual entry-fill session is age one; weekends and holidays do not count.
Discretionary exits fill at a subsequent open, never the decision close.
Between scheduled reviews, ordinary strategy exits and stops remain active.
No ML probability, stronger entry rule, larger universe, higher allocation,
or new ranking was added. Continuation gates are observations, not claims
that future profits are extremely certain.

## Scope and reference verification

The study ran **36 main simulations**: three arms, two capital amounts,
two development windows, and three cost cases. The full account spans
2017-2023 after 2016 warmup. The recent account independently spans
2022-2023 with the original 2019 warmup. They overlap and are already
inspected development history, not fresh out-of-sample evidence.

All use the same twelve SIP/all-adjusted stock/ETF datasets and saved actual
session calendar. Original dataset checksums and reference-chain hashes
were verified. No missing prices were filled and no new market data was
downloaded. The primary capital is $10,000; $100,000 is a size diagnostic.

**All twelve controls reproduced every original goal-fit metric and fill
exactly**, including original event counts, before variant scores were
accepted. Every main ledger reconciled to its closing marks. The extra
decision journals do not change reference trading behavior.

Neither new arm met the measured primary-account criteria in both windows.
The predeclared conditional diagnostics were therefore **not run**; stopping
at 36 was the registered rule, not a missing task. There was no further
parameter sweep or selection of a better-performing neighbor.

## Primary results: $10,000 accounts

Returns include pessimistic modeled costs **and estimated final exit costs**.
Pessimistic means 20 bps adverse slippage, 10 bps full spread (half per side),
and $1 per order. Those are scenarios, not observed broker executions.

| Arm | 2017-2023 total | 2017-2023 CAGR | Max closing drawdown | 2022-2023 total | 2022-2023 CAGR | Max closing drawdown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Control | +9.944% | **+1.363%** | -4.628% | +0.230% | **+0.115%** | -3.198% |
| Maximum 30 | +6.320% | **+0.879%** | -3.509% | -1.202% | **-0.603%** | -3.198% |
| Continuation review | +7.854% | **+1.086%** | -3.254% | -1.220% | **-0.612%** | -3.198% |

The seven-year net dollar gains after estimated exits were $994.35, $631.97,
and $785.40 respectively. The recent two-year outcomes were +$22.99,
-$120.20, and -$121.99. These are whole-account gains/losses, not returns
on only the capital briefly invested or returns per trade.

### Cost sensitivity: annualized after estimated exits

| Window / arm | Optimistic | Base | Pessimistic |
| --- | ---: | ---: | ---: |
| 2017-2023 control | +2.398% | +2.190% | +1.363% |
| 2017-2023 maximum 30 | +2.273% | +2.091% | +0.879% |
| 2017-2023 continuation | +2.536% | +2.330% | +1.086% |
| 2022-2023 control | +1.001% | +0.896% | +0.115% |
| 2022-2023 maximum 30 | +0.428% | +0.304% | -0.603% |
| 2022-2023 continuation | +0.419% | +0.295% | -0.612% |

The continuation arm slightly exceeded the full-period control before
pessimistic costs, but not after them. All cases remain far below the
approved 6% annual hurdle. This is not a reason to substitute optimistic
costs or loosen the hurdle.

### Annual returns: continuous $10,000 account, pessimistic costs

These mark each year-end account normally, without annual forced sales.

| Year | Control | Maximum 30 | Continuation review |
| --- | ---: | ---: | ---: |
| 2017 | +3.860% | +3.307% | +4.127% |
| 2018 | -2.071% | -1.030% | -0.716% |
| 2019 | +2.939% | +0.749% | +0.981% |
| 2020 | +2.973% | +2.637% | +2.995% |
| 2021 | +3.107% | +1.760% | +1.597% |
| 2022 | -2.589% | -1.392% | -1.398% |
| 2023 | +1.661% | +0.312% | +0.225% |

The independent recent account differs because it starts fresh in 2022;
the continuous account carries its previous holdings/equity into that year.
No yearly reset, halt reset, or new deposit was assumed within either run.

## Did freeing capital help?

Pessimistic seven-year $10,000 accounts:

| Measure | Control | Maximum 30 | Continuation review |
| --- | ---: | ---: | ---: |
| Completed trades | 163 | 255 | 251 |
| Average calendar holding days | 61.42 | 31.08 | 32.01 |
| Median completed holding sessions | 31 | 30 | 30 |
| Longest completed holding sessions | 216 | 30 | 45 |
| Average cash fraction at close | 83.47% | 87.15% | 86.95% |
| Modeled trading costs already deducted | $679.83 | $1,046.82 | $1,036.35 |
| Completed-trade profit factor | 1.598 | 1.241 | 1.316 |
| BUY attempts first blocked by seven-position limit | 152 | 35 | 48 |
| BUY attempts first blocked by cooldown | 50 | 215 | 194 |
| Sessions at the seven-position limit | 486 | 151 | 159 |

The slot constraint was real on some signal dates, even with cash available.
Age exits reduced those rejections. But cash use fell, turnover/costs rose,
cooldown rejections increased, and the net return deteriorated. Therefore
"freeing a slot" did not translate into better investment fit in this test.
The rejection counts are repeated decision attempts, not independent trades
or known profitable opportunities. Only the first rejecting check is
recorded; other constraints could also have applied.

The maximum arm had 129 time exits. Seventeen coincided with another
instrument buying at that open; 89 of 128 complete five-session followups
had another buy within five sessions. The continuation arm had 128 time
exits, 13 with another buy at the same open, and 86 of 127 complete
five-session followups with another buy. Each arm had one right-censored
followup near the end. These are counts per exit; one later buy can appear
in several exits' followups. They do not prove the sale was needed to fund
the purchase or that the replacement was profitable.

In the recent two-year $10,000 accounts, realized P&L remained negative:
-$116.84 control, -$218.31 maximum, -$220.10 continuation. Both new arms had
51 completed trades and profit factor about 0.55, failing the positive
realized-profit and 1.2 profit-factor criteria as well as the return goal.

## What happened to the beyond-60 exception?

It is implemented with no hard maximum and is tested at sessions 60, 90,
and 120. **It was not exercised by the historical study.** In the primary
seven-year continuation run, there were 161 reviews: 33 retain decisions
and 128 exit decisions. Reviews occurred at ages 30, 35, 40, and 45; no
position survived to the session-60 review. Every age-review exit failed
the fresh-high condition, and 16 also failed the net-profit condition.

This tells us the declared fresh-high gate was restrictive in this sample;
it does not tell us what a calibrated high-confidence model would do. Do
not relax that gate after seeing these returns and call the result a
confirmation of this registered hypothesis.

## Larger-account diagnostic and risk limits

At $100,000, pessimistic after-exit CAGR was:

| Window | Control | Maximum 30 | Continuation review |
| --- | ---: | ---: | ---: |
| 2017-2023 | +2.180% | +1.637% | +1.877% |
| 2022-2023 | +0.594% | -0.233% | -0.245% |

Neither larger-account variant rescued the investment goal. No main run
hit a permanent halt. The strategy's historical 3% daily / 10% drawdown
halt settings remained unchanged; the approved research acceptance ceiling
is a separate 5% account drawdown criterion, not paper-risk approval.

The primary seven-year daily-OHLC conservative drawdown bounds were about
-5.008% control, -3.894% maximum, and -3.647% continuation. These are not
observed intraday paths; their extrema need not occur together. Actual
intraday risk remains unmeasured, and a bound cannot guarantee a future
loss ceiling. Lower closing losses alone cannot repair a failed return goal.

## Reproduction and verification

With the existing audited datasets and original goal-fit report available:

```powershell
.venv\Scripts\python.exe -m backtesting.holding_research --output-dir data/reports/study_c_holding_new
.venv\Scripts\python.exe -m unittest tests.test_holding_policy tests.test_holding_research tests.test_goal_fit tests.test_risk_diagnostics tests.test_earlier_history tests.test_allocation_research tests.test_daily_research tests.test_portfolio_backtesting
```

Use the Pi environment's `python -m ...` equivalent there. Choose a fresh
output directory; existing reports are not overwritten. Git does not copy
ignored datasets/reports. Legacy `goal_fit` deliberately guards the exact
old engine source hash and will reject this new engine version; do not
remove that check. Use this new versioned runner with its twelve financial
control comparisons, or an original checkout for the original audit.

The complete ignored report is `data/reports/study_c_holding/report.json`.
Its 36 individual case files contain fills, equity, reviews, BUY journals,
risk envelopes, cost attribution, and source/data/reference/policy hashes.
Source code is portable; this study was run on Windows, not on a Pi.

**29 new tests passed**, covering holding schedules and continuation beyond
60, causal prior-high/profit gates, fill-based age, holidays, natural/delayed
exit precedence, gap/touch stops, reentry clocks, released slots, absence of
forced replacements, pending final exits, journals, censored followups, and
reference/coverage guards. **144 focused/related tests passed.** The full
suite ran **279 tests: 277 passed and two errored**, both existing optional
ML tests importing absent `scikit-learn`; no final assertion failed.

## Universe question and next work

The study used **nine familiar stocks and three ETFs**, not the whole
market. It isolates the holding-time idea on that fixed pilot basket. Its
results cannot justify launching a whole-market paper scanner, and wider
coverage cannot be assumed to improve returns. The current engine also
requires aligned histories, which is insufficient for IPOs/delistings in
a genuinely historical broad universe.

[The universe guide](stock_universe_research.md) explains available Alpaca
asset/bar APIs, historical-membership requirements, costs, and engineering
gaps. Tighter entries, new rankings, and wider membership require a matched
research scope before paper activation.

**Next proposed work:** a read-only broad-universe data-feasibility audit:
define the intended eligible instruments, establish historical membership
and delisting coverage, and assess what can be obtained within existing
access before proposing an entry/selection study. Keep these failed time
variants as references. Do not run more age thresholds automatically.

**Codex:** I can build the audit/tooling and present data limitations.
**Owner:** No new risk configuration is needed now. Review the next universe
scope when presented; any paid-data purchase needs a separate explicit
budget decision. No orders, paid source, broader-universe backtest, or
2024-2025 evaluation was authorized or performed by this study.

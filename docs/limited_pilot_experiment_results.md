# Limited Apple/CBRE experiment: completed results

Completed **2026-10-29**, after the owner's explicit approval of the
[finite proposal](next_pilot_experiment_proposal.md). Approval is recorded
[separately](next_pilot_experiment_approval.json); the old proposal and source
evidence remain unchanged.

**All 24 registered runs completed.** Financial and daily-risk ledgers
reconcile in every case. The experiment produces modest earlier gains and
recent losses. **Every run falls below the approved 6% annual return hurdle.**
The two-stock exploratory sample cannot qualify for paper trading.

**Actual purchases: $0. Actual broker/account requests and orders: zero.**
Every account balance, dividend, fee and return below is simulated. No money
was invested, charged or transferred. No new price or document download,
dependency installation or 2024–2025 candle read occurred.

## Primary results: $10,000 simulated accounts

Each period starts a fresh $10,000 account. Results include modeled entry/exit
costs, dividends and an **estimate** of selling the remaining whole-share
positions at the final close after costs. Those final sales were not executed
or added as fabricated fills. This table uses the proposed base dividend
availability convention: the first actual open strictly after issuer payable.
These particular base-credit runs have no unpaid rights at their endpoints.

| Trading period | Cost case | Net result after estimated share exits | Total return | Annualized return | Maximum closing drawdown |
| --- | --- | ---: | ---: | ---: | ---: |
| 2017–2021, five years | Base | **+$440.11** | +4.40% | +0.87% | -0.69% |
| 2017–2021, five years | Pessimistic | **+$311.87** | +3.12% | +0.62% | -0.82% |
| 2022–2023, two years | Base | **-$10.68** | -0.11% | -0.05% | -0.77% |
| 2022–2023, two years | Pessimistic | **-$53.09** | -0.53% | -0.27% | -1.01% |

The earlier +3.12% is **over five years**, not per year. It does not meet a
6%-per-year goal. The two independent account periods are not added together
as a continuous seven-year portfolio. Both use already explored development
history, not an untouched final test.

Base costs mean 5 bps adverse slippage per side, 2 bps full spread and no
per-order fee. Pessimistic costs mean 20 bps slippage per side, 10 bps full
spread and $1 per order. Half the full spread applies on each side. Those
fees are virtual assumptions, not bills or observed broker executions.

The $100,000 size diagnostic also misses the annual return hurdle: its
pessimistic after-estimated-exit return is +5.40% total over 2017–2021
(about +1.06% annually) and -0.30% over 2022–2023 (about -0.15% annually).
All capital/cost/cash combinations are retained in the
[24-row results CSV](research_data/limited_pilot_experiment_results.csv).

## What the strategy actually did

The unchanged swing rule uses a prior-55-session breakout entry, prior-20-
session exit channel, stock/SPY EMA200 filters, a fixed initial three-ATR14
stop and ten-session reentry cooldown. The approved continuation policy
reviews positions at held sessions 30,35,40,45,50,55,60 and every 30 thereafter.
Retention requires a fresh prior-20-session high, positive estimated net sale
profit and stock/SPY above EMA200. Ordinary exits and stops remain active.

The old research allocation is preserved: 5% per-position / 35% account caps,
0.5% planned stop risk, 1% annualized volatility contribution and seven-position
maximum. Existing latched 3% daily / 10% drawdown halts are unchanged. These
are research controls, not newly approved personal paper-risk settings or a
guarantee of the separate 5% research drawdown rejection level.

In the pessimistic $10,000 base-credit cases:

- **2017–2021:** 35 completed trades; average completed holding time **24.09
  sessions**, maximum 40. Mean closing invested exposure was **2.56%**, with
  about **97.44% in spendable cash**.
- **2022–2023:** 11 completed trades; average **13.36 sessions**, maximum 30.
  Mean exposure was **1.34%**, with about **98.66% in spendable cash**.

These are trading sessions, not calendar days; open positions are excluded
from completed holding averages and remain separately recorded. Both periods
have two instruments with closed trades. No position in these cases reached
the beyond-60-session extension reviews.

With only two candidate stocks, tight entry rules and the frozen small sizing,
most capital was idle. Cash availability was not the obstacle in this sample.
Increasing exposure was not an approved experiment and would change the risk
and return question. No sizing or entry threshold was changed after results.

### Contributions: pessimistic $10,000 base-credit cases

The following marked contributions include trading costs and earned dividends
but precede the separate estimated final share-sale costs:

| Period | Apple | CBRE | Combined marked profit before estimated final exits |
| --- | ---: | ---: | ---: |
| 2017–2021 | +$286.12 | +$28.08 | +$314.20 |
| 2022–2023 | +$4.62 | -$54.05 | -$49.43 |

For example, the earlier $314.20 consists of **$246.45 realized trading P&L**,
**$57.58 open-position marked P&L** and **$10.17 earned/credited dividends**.
Estimated final share exits cost another $2.33, producing the $311.87 table
result. The later -$49.43 consists of -$86.54 realized trading P&L, +$36.18
open marked P&L and +$0.94 dividends; estimated final exits cost $3.66.
These are simulations, not money received or charged to the owner.

## Cash-delay sensitivity: what changed

All eight window/capital/cost groups produced the **same fills** under base
credit, five-session delayed credit and no credit. Their marked returns agree
within floating-point precision because there was ample uninvested cash;
cash reuse never changed the selected quantities or trade path.

That does **not** mean the no-credit scenario received dividends. Its earned
rights stay unpaid, with `pay_session: null`, and cannot fund a purchase.
The $10,000 no-credit cases finish with $10.17 of rights in the earlier window
and $0.94 in the later window. Spendable cash is lower by those amounts.
Marked equity includes the nominal rights, and their hypothetical fully
liquidated return is explicitly unavailable. Estimated share exits do not
settle those rights. No arbitrary future payment date or future session was
invented. Delay insensitivity here does not establish actual broker timing or
insensitivity in a more invested portfolio.

## Verification and implementation

Implemented a separate `DiagnosticUniverse`/input path in
`backtesting/pilot_diagnostic.py`, reusing the existing strategy, portfolio,
split, holding and ordinary-dividend machinery. An approval record authorizes
the modeling assumptions; independent entitlement and broker-credit flags stay
false. The strict universe/ownership loaders are unchanged. Risk reporting
accepts an unscheduled cash right only with the explicit approved diagnostic
schedule; an untagged missing payment date remains an error.

**Passed before performance scoring:**

- **209 unit tests: 26 new diagnostic tests and 183 related regressions**,
  zero failures, errors or skips.
- Six actual-data window/cash schedules, preserving raw aliases and the real
  saved calendar; no filling or ticker guessing.
- Seven saved Apple accounting-pilot checks, including exact split/dividend
  accounting and financial/risk reconciliation. This is one legacy
  verification replay, separate from the 24 new strategy experiments.

Tests cover deferred and delayed cash, duplicate protection, prior-holder
entitlement versus same-open purchases/sales, invalid dates/amounts, holiday/
weekend boundaries, split quantities/features/stops/holding age, alias
continuity, unapproved mode rejection and preservation of strict evidence
and paper flags. Socket connection methods are blocked during verification
and execution.

**Passed after scoring:** the report validator checks the exact 24-case
Cartesian scope and attempt budget, approval/source/code hashes, every saved
case hash, P&L/contribution totals, cash-right treatment and all risk ledgers.
All 24 outcomes are preserved. No failures triggered retuning or extra runs.

The suite was focused; the entire project/optional-ML suite and Raspberry Pi
execution were not run. Windows execution is verified. A few helper imports
expose existing research modules, but this path constructs no broker client,
loads no credentials and makes no network requests.

## Decision and remaining limits

**This is a completed accounting/strategy diagnostic, not an approved
investment candidate.** All 24 annualized results are below 6%. The recent
period loses money under both cost cases. Thirty-five earlier completed
trades meet the trade-count floor in isolation; 11 recent trades do not.
The five-instrument requirement cannot be met by two stocks.

Closing drawdowns are small in these runs, but daily-OHLC bounds are not an
observed intraday path. The pessimistic $10,000 conservative drawdown bounds
are approximately -0.95% and -1.02%. Sparse exposure and a small convenience
sample do not establish future loss protection.

Apple ex-dates, clipped identity coverage and action completeness remain
vendor-dependent exploratory inputs. CBRE's original tax label is retained,
with no REIT filter. SPY supplies raw price-only market context, not a traded
asset or a passive total-return benchmark. Taxes and idle-cash yield are
omitted. Old studies used different universes/price conventions, so these
numbers cannot isolate strategy improvement versus those earlier results.

The original 506-row register, registered nine-stock control, acceptance
criteria and strict evidence records remain intact. JPMorgan collection stays
parked. No paid-data fallback, personal paper-risk approval or paper activation
was added.

## Evidence and reproduction

- [Owner approval](next_pilot_experiment_approval.json).
- [Original frozen proposal](next_pilot_experiment_proposal.json).
- [Tracked execution/verification/results summary](limited_pilot_experiment_summary.json).
- [All 24 results](research_data/limited_pilot_experiment_results.csv).
- Local tests, schedule checks and legacy replay:
  `data/reports/limited_pilot_verification_v1`.
- Local execution journal and all 24 complete cases:
  `data/reports/limited_pilot_experiment_v1`.
- Independent result validation/exports:
  `data/reports/limited_pilot_results_v1`.

The registered 24-run allowance has been consumed. The runner rejects the
existing output directory and does not automatically repeat the batch.
The following command validates/reports the saved outcomes, without running
any strategy, and requires a fresh report directory:

```powershell
python -m backtesting.pilot_diagnostic_report --output data/reports/a_fresh_limited_pilot_summary
```

The focused tests can be repeated with the modules named in the tracked
verification summary. Ignored raw data/reports must be kept for reproduction;
a clean clone alone cannot reconstruct them. No previously reported source
or code hash was silently updated to accept a changed historical input.

## What is next, and whose work?

**My next proposed engineering work:** prepare a finite broader-universe
follow-up from cached coverage, targeting at least five eligible stocks and
recording exact identity/action/price gaps. Freeze the research scope before
new scores, retain unavailable/failed-company cases and keep JPMorgan's
collection stop. This means preparing a reviewable dataset/experiment plan,
not automatically replacing the registered control or promising that free
coverage can satisfy every gate.

**Your part now:** no purchase, risk JSON or account setup. You approved and
received this limited experiment. I will explain any materially changed
research scope before seeking its approval. Personal risk limits and paper
activation remain later decisions. No profitable paper candidate or launch
date is established by these results.

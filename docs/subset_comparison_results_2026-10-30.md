# Completed 76-stock comparison: Steps 3 and 4

**Decision: retain this as research; do not promote the frozen strategy to paper
trading for the approved investment objective.** None of the 24 cases meets
the recorded 6% annualized return goal. All broader-basket cases also exceed
the 5% closing drawdown limit. This is the engineering assessment against the
owner's existing criteria, not an owner approval of a new strategy or paper trial.

## Execution and verification

Step 3 completed all **24 distinct cases**: two baskets, two independent date
windows, two cost settings and three accounting-availability scenarios. Three
accepted cases came from the original stopped batch; 21 came from the approved
recovery. **25 lifetime attempts** include the original timeout. No failed
attempt was erased and no completed strategy case was rerun.

The recovery took **18.97 minutes**, below its 60-minute allowance. Its longest
accepted case took **125.44 seconds**, below the ten-minute case allowance.
It had zero failures. The original stopped batch and its timing discrepancy
remain documented in the [partial report](subset_partial_results_2026-10-30.md).
Before recovery, **320 focused offline tests passed**, zero failures, errors
or skips; all three saved financial/risk reports matched exactly and six
synthetic controls passed. Each new case passed internal ledger replay and
external-price/risk reconciliation. Combined per-stock contributions reconcile
to each account's marked profit. Raspberry Pi execution/timing is unverified.

**No money was spent.** Trading costs, account balances, dividends, gains and
losses below are simulated. No purchases, broker/account requests, paper/live
orders, credential access or reserved 2024-2025 candle reads occurred.

## Matched results

Both baskets use the same frozen daily breakout strategy, sizing and entry
limits: 70% total exposure, 5% per stock and 20 positions. The table uses the
base accounting-availability scenario. The two-stock control is AAPL/CBRE.
Each row starts a separate simulated $10,000 account; do not add or compound
the two date windows into a continuous account result.

| Period | Basket | Cost setting | Total net marked return | Annualized return | Max closing drawdown | Average cash | Closed trades |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2017-2021 | Two-stock control | Base | +4.40% | +0.87% | -0.69% | 97.35% | 35 |
| 2017-2021 | 76 stocks | Base | +6.29% | +1.23% | -10.02% | 80.63% | 305 |
| 2017-2021 | Two-stock control | Pessimistic | +3.12% | +0.62% | -0.82% | 97.36% | 35 |
| 2017-2021 | 76 stocks | Pessimistic | -2.66% | -0.54% | -10.93% | 81.81% | 277 |
| 2022-2023 | Two-stock control | Base | -0.11% | -0.05% | -0.77% | 98.66% | 11 |
| 2022-2023 | 76 stocks | Base | -2.60% | -1.31% | -7.70% | 80.75% | 222 |
| 2022-2023 | Two-stock control | Pessimistic | -0.53% | -0.27% | -1.01% | 98.66% | 11 |
| 2022-2023 | 76 stocks | Pessimistic | -10.96% | -5.64% | -11.17% | 94.78% | 134 |

Returns include modeled trade costs and estimated final whole-share exit costs,
and include nominal unpaid rights. They are marked economic results, not
fully settled cash gains. [Definitions and concrete drawdown examples](subset_return_metrics_explained.md)
explain why +6.29% over five years is not close to a 6% annual objective.

Base costs model 5 bps adverse slippage per side, a 2 bps full spread and no
fixed order fee. Pessimistic costs model 20 bps per side, a 10 bps full spread
and $1 per order. These are frozen scenarios, not measured broker charges.
Costs affect sizing, eligibility and halt timing, so the difference between
two rows is not simply the cost of executing an identical list of trades.

## What changed when the basket grew?

The five-year base case increased average committed capital from roughly
2.65% to 19.37%, including unpaid rights, and closed trades from 35 to 305.
Average actual stock/pending-share exposure was 17.92%; unpaid cash rights
reserve exposure but cannot fund another purchase. The 70% entry ceiling did
not require or achieve 70% average investment. The broader sample reached
20 simultaneous positions, so the position-slot limit also affected entries.

The five-year broad base case hit its permanent drawdown entry halt on July
30, 2018. Under pessimistic costs it halted on June 25, 2018. New entries then
remained disabled, which contributes to high average cash over later years.
In the two-year window, the broader base-cost case did not permanently halt;
it still returned -2.60%. The pessimistic case halted on February 8, 2023.
Permanent halts therefore help explain utilization, but do not explain away
all losses or establish that restarting would improve returns safely.

Average modeled holding durations for the broader cases were 29.49 / 30.22
calendar days for five-year base / pessimistic costs, and 16.19 / 9.16 days
for the corresponding two-year cases. These are averages of completed modeled
sales; daily bars do not establish exact intraday holding hours.

## Assessment against the approved goals

The declared primary comparisons use **pessimistic costs and base availability**.
Both broader-basket primary cases fail annual return, closing drawdown, profit
factor (0.85 / 0.15 versus the 1.2 floor), positive realized profit and the
no-permanent-halt check. Both exceed the 30-trade and five-instrument evidence
floors. More observations do not turn failed performance into a passed result.

Both pass the daily *closing* loss threshold of 2%, but that does not establish
an intraday loss bound: the five-year pessimistic case's conservative daily
OHLC bound is about -2.72%. That is a modeled possible envelope, not a recorded
intraday account path. The corresponding closing drawdowns already reject
the candidate, without relying on that conservative bound.

The legacy research halt remains 10% drawdown; the owner's acceptance limit
remains 5%. Those settings were intentionally preserved for this comparison.
An entry halt reacts to observed losses, does not immediately liquidate all
holdings, and cannot guarantee an exact maximum loss.

## Availability sensitivity and remaining limits

All three accounting scenarios have identical 2017-2021 net returns here.
For the broader 2022-2023 case, delayed availability matches base; no-credit
gives -2.58% at base costs and -10.94% at pessimistic costs, versus -2.60% and
-10.96%. These small changes do not reverse the rejection. Scenario ordering
is not guaranteed to rank returns monotonically, because availability changes
which trades can occur. It does not prove actual historical receipt dates.

This is an exploratory subset selected by historical data availability. It
does not represent the whole market or remove survivorship/selection concerns.
The original 100-stock protocol retains its 24 deferred roots and 188 gates.
Modeled retrospective corporate-action knowledge and nominal unsettled claims
remain diagnostic assumptions. The 2017-2023 years have been inspected during
development and are not fresh final validation data. 2024-2025 remain reserved.

## Step 4 decision and next work

**Steps 3 and 4 are complete for this approved comparison.** The decision is
to reject this frozen candidate for paper promotion against the existing
investment criteria, while retaining all results for further research. This
does not complete the original full-100 study, implementation Phase 15 or
paper-trading readiness. The owner has not approved a new strategy or trial.

**Next - engineering:** prepare a small, preregistered follow-up proposal that
separates entry/ranking changes from drawdown/halt-policy changes. Reuse the
qualified basket, include the frozen baseline, preserve the running equity
peak and disclose every variant and cost case. Use the previous allocation
and halt studies as context, not evidence of a fresh successful strategy.
Do not start a parameter search, change the 6%/5% goals or open reserved years.

**Next - owner:** review that concrete proposal before another performance
batch. Nothing needs installing or editing in the personal risk file now.
Personal paper-risk approval, safe exit protection/fill accounting, account
state/startup recovery review and explicit trial activation still belong to
the later paper-readiness workflow.

## Evidence

- [Full compact summary of all 24 cases](research_data/subset_final_2026-10-30_summary.json)
- [All-case CSV](research_data/subset_final_2026-10-30_all_cases.csv)
- [Per-stock contributions](research_data/subset_final_2026-10-30_root_contributions.csv)
- [Completion, budget and decision verification](subset_final_verification_2026-10-30.json)
- [Recovery approval and implementation](subset_recovery_approved_2026-10-30.md)
- [Current driver test/source proof](subset_recovery_driver_verification_2026-10-30.json)

Full local case files/logs remain in the original and recovery directories
under `data/reports/`; preserve those ignored archives with the research.

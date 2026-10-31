# Proposed follow-up: entries, risk and invested capital

October 31, 2026. **Proposal for review; no new simulation or paper order is
authorized by creating this document.** The preceding comparison's Steps 1-4
are complete. This is a new research scope, with a new budget if approved.

## 1. Your priorities and my recommendation

You want to learn through paper trading and want around 70% of the account
invested in stocks, potentially with an 80-85% ceiling. The previous 80.63%
average cash balance is a reason to investigate deployment and halts. Raising
an entry ceiling alone does not make a strategy buy more qualifying positions.

I propose **70% as a deployment target and 85% as the ceiling to study**, with
65-75% as a weekly rebalance band. These are proposed research settings, not
approved personal paper-risk settings. The existing 6% annual return and 5%
running-peak drawdown criteria remain unchanged.

A target directs allocation when valid opportunities and risk capacity exist.
A ceiling restricts new orders. A hard 70% minimum would force stock exposure
even during sell signals, a market filter failure or a risk halt. That would
require a different strategy and an explicit change to the risk brief.

For scale, a 10% drop in stocks held at 70% account exposure implies roughly
a 7% account decline before costs, assuming the cash portion is unchanged.
At 85% exposure it implies about 8.5%. This arithmetic is not a forecast; it
shows why a high investment target cannot guarantee a 5% maximum drawdown.
The SEC explains allocation as a choice tied to time horizon and risk
tolerance in its [asset-allocation guide](https://www.investor.gov/introduction-investing/getting-started/asset-allocation).

## 2. Why paper trading is useful, and what is ready

**I support moving toward a separately scoped paper engineering trial alongside
research.** Such a trial can measure whether orders, fills, exits and recovery
operate correctly even while the strategy remains an unsuccessful investment
candidate. A short profitable trial would not reverse the historical rejection.

The repository currently has risk, order-idempotency and startup-recovery
components. The automatic paper loop, complete broker fill/activity ledger and
protective exit/stop workflow still need implementation and verification.
`config/risk_limits.json` is still empty and unapproved. A sizing stop price
does not establish that a protective broker order exists.

The concrete route is:

1. Build a **shadow observer** that records completed current-market signals,
   intended allocations and rejection reasons without submitting orders. Pin
   the version and define the dataset/universe before observation starts.
2. Complete broker fill reconciliation, partial-fill handling, protective
   exits, restart recovery and a supervised loop. Verify unknown submission
   outcomes, duplicate prevention, disconnects and protection failures offline.
3. Present the working paper-preview/recovery reports and a proposed operational
   trial policy. You then approve complete paper-risk limits, review existing
   account positions/orders and explicitly authorize a paper-only trial.
   No personal-risk edit is due for this proposal-writing task.
4. For a proposed first engineering trial, observe at least **20 completed
   trading sessions** with a frozen version. Record all actual opportunities;
   sparse fills mean limited evidence. Do not force trades to manufacture
   coverage. Stop and version material fixes, then report each version's
   results separately. This is an observation period, not a profitability test
   or a promise of a launch date.

Current tradeable identities and feed availability need checking before a
prospective trial; the historical 76-root basket is not automatically today's
paper universe. Use only already available free access, without upgrades.
Prospective data and warmup must stay separate from the reserved 2024-2025
evaluation candles; missing warmup is a blocker, not permission to open them.

Alpaca describes paper trading as a real-time simulation. Its documentation
lists omitted effects such as latency slippage and market impact, and states
that paper accounts do not simulate dividends. A later trial must reconcile
its broker ledger separately from any research dividend ledger; do not add
theoretical dividends to broker cash or infer that paper fills remove modeled
cost sensitivity. See [Alpaca's paper specification](https://docs.alpaca.markets/us/docs/paper-trading).

This proposal does not waive existing investment-acceptance gates. An
operational-only trial of a rejected strategy would need its own explicit
learning objective and approval after the execution workflow is reviewable.
No account query, credential inspection, broker order, account reset or
subscription change is part of this documentation task.

## 3. Frozen comparison design

Use the same qualified **76 original roots**, saved raw prices, diagnostic
action schedules and SPY context as the completed study. Keep the other 24
roots in the original full-100 inventory. No new data collection or all-market
claim is proposed. Historical availability selection can bias results.

Use two separate simulated $10,000 accounts/windows:

| Evaluation | Warmup | Purpose |
| --- | --- | --- |
| 2017-2021 | 2016 | Earlier development comparison |
| 2022-2023 | 2019-2021 | Later development robustness comparison |

These periods have already been inspected. Neither is a fresh holdout. Keep
2024-2025 reserved. Report every arm in both windows and costs; do not select
or tune thresholds after inspecting the later results.

| Cost case | Adverse slippage per side | Full spread | Fee per order |
| --- | ---: | ---: | ---: |
| Base | 5 bps | 2 bps | $0 |
| Pessimistic | 20 bps | 10 bps | $1 |

Use the existing **base accounting-availability scenario** for this finite
comparison. It is a retrospective diagnostic assumption, not verified receipt
timing. Delayed/no-credit performance reruns are not included in the budget;
the prior sensitivity results remain evidence, and any later expansion needs
a separately bounded proposal. Corporate-action ledger verification still
covers all supported accounting scenarios offline.

All arms retain 55-session breakout entries unless explicitly stated, 20-session
channel/EMA exits, stock/SPY EMA200 filters, initial 3-ATR14 stops, ten-session
reentry cooldown, 20 positions and the approved continuation holding reviews.
Signals use completed bars; execution uses the following actual session open.

## 4. Six policies: exact comparisons

| ID | Change from its comparator | Question | Comparator |
| --- | --- | --- | --- |
| P0 | Exact frozen baseline: alphabetical entries, 70% ceiling, no deployment target, existing sizing and 3% daily/10% drawdown latched entry halts | Does the new implementation reproduce the completed study? | Four pinned historical baseline cases |
| E1 | Rank competing eligible BUYs by prior 63-session stock return minus matched SPY return | Does a deterministic opportunity order improve slot allocation? | P0 |
| E2 | E1 plus the two predefined entry filters below | Do stricter entries help when ranking is held fixed? | E1 |
| R1 | Earlier loss controls and smaller new-entry risk, defined below; keep P0 entries/order and 70% ceiling | Does the risk policy better fit 5% drawdown, and what return/cash tradeoff results? | P0 |
| C1 | Raise only P0's total entry ceiling from 70% to 85% | Is the ceiling actually preventing investment? | P0 |
| C2 | C1 plus a weekly 70% target allocator under the existing individual risk limits | Can deliberate deployment increase invested time without failing risk/cost criteria? | C1 |

Do not combine an E winner with R or C during this batch. That would be a new
policy with unmeasured interactions. E2 versus E1 isolates the added filters
under ranked ordering; there is no claim about filters under every other order.

### E1 and E2: causal ranking and entry filters

Rank descending by `stock_close[t] / stock_close[t-63] - 1` minus the equivalent
SPY return over the same completed sessions. Use stable instrument ID to break
ties. The ordering is a momentum hypothesis, not an estimated win probability.

E2 also requires:

- Signal-session volume at least **1.5 times the preceding 20-session median**,
  excluding the signal session from that median.
- The 63-session stock return exceeds SPY by at least **five percentage points**.

These thresholds come from the existing entry-study proposal, not a search
over the latest results. Returns and volume need causal split-consistent
units, with no future adjustments. Missing or unreliable required inputs
disqualify the candidate and are counted; they are not assigned neutral scores
or filled. Cash dividends remain explicitly accounted for, not counted twice.
Stricter qualification may increase cash and reject eventual winners.

### R1: risk and halt policy, without entry changes

Keep P0's 5% position cap, 70% ceiling and 20 slots. Change the planned
per-position stop-risk cap from 0.5% to **0.25% of account equity**, and the
annualized volatility-contribution sizing input from 1% to **0.5%**. These are
sizing inputs, not guarantees of maximum loss.

- A **1% daily account-loss observation** blocks new entries for five complete
  sessions. Resume only at a following open after those five sessions and a
  valid prior-session SPY-above-EMA200 review. New completed signals are
  required; stale queued BUYs do not revive.
- A **3% drawdown observation** blocks entries for the rest of that account
  window and schedules all deliverable whole-share positions for sale at
  the following actual session open, with modeled costs. Check the same open
  and close observation points as the existing engine; an open observation
  schedules the next session's open, not an invented earlier fill.
- Protective stops and ordinary sells remain active. A triggered drawdown
  action overrides the daily restart. Preserve pending economic rights;
  missing tradable prices block accounting rather than imply a cash recovery.
- Preserve the original running equity peak and full-window return series.
  No automatic drawdown reset, new capital or account restart is permitted.

R1 deliberately tests a more defensive policy. It can leave *more* cash and
permanently stop entries. We do not claim it solves the deployment objective.
A 3% observed trigger may overshoot 5% before a later fill; it is not a loss
guarantee. Automatic drawdown restart is outside this first follow-up.

### C1 and C2: capacity versus a deployment target

C1 changes only the total entry ceiling to 85%. The 5% per-stock, 0.5% planned
stop-risk, 1% volatility sizing input, 20-slot and legacy halt settings remain.
At 5% per stock, 70% needs at least 14 full-sized positions and 85% needs 17.
Smaller risk-sized weights need more positions; 20 slots can be insufficient.

C2 adds the following deliberately different allocation behavior:

1. Ordinary C1 daily signal processing remains active. The following weekly
   rebalance is additional behavior; between weekly reviews, new daily entries
   and price moves can take exposure above the target band, subject to the
   85% entry ceiling. At the final completed session of each calendar trading week, assess actual
   delivered-stock exposure. If it is outside **65-75%**, plan a rebalance
   toward 70% for the following actual session open. No minute-by-minute
   rebalancing or intraday fill claims are made from daily data.
2. Eligible holdings must still pass the stock and market trend filters and
   all original exit/holding reviews. New names require P0's fresh breakout
   signal and alphabetical order. A valid exit always takes precedence.
3. Retain eligible holdings, then admit new qualifying names up to 20 slots.
   Start with equal weights `min(5%, 70% / number_of_selected_names)`. Reduce
   each weight for its existing volatility and **combined-position** stop-risk
   limits. Do not scale weights upward again to spend risk-blocked cash.
4. Rebalance may trim existing positions and add to an existing position only
   when its completed close is above its historical average entry cost and
   its existing stop permits the combined quantity within the risk cap.
   Keep that stop unchanged; do not average down or reset the holding clock.
   Fresh positions receive the usual initial stop. Each partial sale/addition
   needs exact basis, fees and protection-quantity accounting.
5. Plan from completed-close information. At the next open, apply sells first,
   then recheck actual opening prices, individual risk, cash, slots and the
   85% total economic-exposure entry ceiling. Reduce or reject quantities
   after gaps; do not rerank on future closes or redistribute rejected budgets
   to exceed another position's cap. Use whole shares and no leverage.
6. Missing signals, too few eligible names, market filters, stops and halts
   permit cash. No ETF filler, weaker entry, borrowing or assumed delivery
   is allowed to meet the target. Do not top up during a halt.
7. If a completed close shows economic exposure above 85% because of price
   moves, schedule reductions toward 70% at the next actual open, with costs.
   An entry ceiling and delayed trimming cannot guarantee a continuous limit.

Target utilization counts **delivered stocks**, excluding unpaid cash and
undelivered share rights. The economic risk ceiling still counts all valued
rights under the approved diagnostic policy. Report both measures separately.
Partial rebalancing and winner additions are new behavior requiring explicit
implementation and accounting verification; they are not already supported
by simply changing an existing JSON percentage.

## 5. Budget, prerequisites and scoring

**Six policies x two windows x two costs = 24 new strategy attempts maximum.**
Run all four P0 cases first and reconcile their fills, financial curves and
metrics to the pinned prior cases before proceeding. Those four runs count
against the 24; no extra historical strategy run is hidden as verification.
Then run E1, E2, R1, C1 and C2, each in both windows and costs in the JSON order.

Proposed limits: one worker, **ten minutes per case, 90 minutes overall**,
including a zero-strategy input/profile gate. Reserve attempts persistently
before launch. Stop on the first error, discrepancy, timeout, changed pin or
missing required evidence. Failed/interrupted reservations consume attempts.
No automatic retry, extra variant, time extension or budget reset is allowed.
This proposal itself authorizes **zero** new strategy runs.

Before performance: implement modular policies; verify synthetic causality,
ranking/ties, calendar/holiday weekly boundaries, gap sizing, partial rebalance
basis/protection, held-session clocks, rights handling, halt precedence,
five-session counting, persistent peaks and no target-driven risk bypass.
Verify Windows operation and preserve portability; do not claim Pi validation.
Pin source/data/policy inputs and run the focused checks before the batch.

Primary investment assessment remains pessimistic costs/base availability
against all existing acceptance criteria. Report every policy, all failed
criteria, realistic costs, trade count/quality, concentration, holding periods,
drawdown, closing daily loss, conservative risk bounds and unsettled value.
Do not score only an arm's active months or reset the equity peak after a halt.

For capital use report, over **all evaluation sessions**, including halts:

- Average/median delivered-stock exposure and cash fraction; economic exposure
  and pending rights separately.
- Fraction of daily closes above 65% and 70%, and within the 65-75% band.
- Target shortfall and first-deployment time; gap/rounding effects.
- Blocker counts and time attributable to inadequate candidates, sizing,
  slots, market filters and halts. Report overlapping reasons transparently.
- Separate market-on/off and pre/post-halt diagnostics as secondary breakdowns,
  without removing bad periods from the primary result.

For review, C2's proposed additional utilization screen is **at least 65%
mean delivered-stock exposure and at least 75% of daily closes at or above
65%**. This is a tolerance around a 70% target, not acceptance of a guaranteed
70% floor. Return/risk failures still reject a high-utilization policy. If
none satisfies the combined brief, report that outcome without loosening
criteria or buying unwanted stocks. The owner must accept this proposed
tolerance before treating it as an agreed objective.

## 6. Decisions and next work

**My next work after scope approval:** implement and verify these six policies,
freeze the current execution protocol and run only the bounded 24-case batch.
Shadow-observer/paper infrastructure is a separate engineering workstream;
this document is not an implementation or launch approval for that workflow.

**Your part:** review the proposed 70% target/85% ceiling and its risk-first
exceptions, the utilization tolerance and this finite scope. You can approve
or amend them in chat. No file editing, paid data or installation is needed.
An “always invested” requirement would need a different explicitly reviewed
allocation strategy and risk tradeoff before implementation.

The [machine-readable proposal](subset_followup_improvement_proposal_2026-10-31.json)
pins the baseline evidence, unchanged acceptance criteria, policies, case order
and budget. The original study and approved risk/election evidence stay intact.

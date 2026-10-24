# Investment acceptance plan: proposal for owner review

Date: **2026-10-24**. Status: **DRAFT — NOT APPROVED**.

This records the owner's goals and proposes research acceptance criteria.
It does not authorize a historical holdout run, change strategy parameters,
approve paper-risk settings, or enable orders. No new strategy simulations
or 2024-2025 data inspection were performed to prepare this document.

## 1. What you have already told me

| Owner statement | Recorded meaning | Still an assumption or proposal |
| --- | --- | --- |
| The strategy should demonstrate attractive investment returns first. | Learning/software reliability alone is insufficient to advance the strategy toward paper trading. | What numerical return is attractive remains your decision. |
| A temporary $500 decline on a $10,000 paper account would concern me. | A 5% decline is a concern level, not permission to lose 5%. | I propose interpreting this as peak-to-trough account drawdown; confirm whether you instead mean $500 below starting capital or a fixed $500 ceiling. |
| A 2% return is not enough. | Approximately 2% annually is below your objective in the context of the discussion. | This does not automatically approve a 6%, 8%, or other annual target. |
| Propose the other criteria for review. | Prepare a concrete written proposal. | Approval of those criteria, final testing, and paper trading remain separate decisions. |

At a $10,000 equity peak, 5% drawdown is $500. At a $12,000 peak, 5% is
$600. Losing $500 from starting capital and losing 5% from an account peak
are different policies. The $10,000 amount is an illustration; this message
does not establish your actual Alpaca account balance or a deposit amount.

## 2. Proposed numerical review standard

These are project-specific screening choices for your review, not industry
standards, forecasts, or recommended personal investment allocations.

| Criterion | Proposed requirement | Why / how to interpret it |
| --- | --- | --- |
| Net annualized return | **At least 6% CAGR** on the entire starting account under pessimistic modeled costs, after estimated costs to exit remaining holdings. | A concrete hurdle materially above the roughly 2% you rejected. It is not a promise that this return is attainable at your loss tolerance. |
| Account drawdown | **Reject at 5% or greater observed drawdown** from the running equity peak, including unrealized P&L and costs. | Treat your concern level as a ceiling for screening. A result below 5% is not evidence that future losses cannot exceed it. |
| Risk margin | A 4% drawdown is an **early concern / review flag**, not an automatic pass or fail. | Leaves a one-percentage-point margin before the proposed rejection level. A result between 4% and 5% requires explicit review. |
| Worst observed daily loss | **Reject at a 2% or greater account-equity loss in a day.** | An additional proposed warning against using most of the 5% concern budget in one day. This is not an approved daily kill-switch setting. |
| Breadth | **At least 30 completed trades across at least five instruments** in a two-year scored window. | A minimum evidence floor, not enough by itself to establish reliability. Fewer trades means inconclusive evidence, not permission to lower the floor. |
| Closed-trade result | Realized net P&L positive and **profit factor at least 1.2**, after modeled costs. | Avoid advancing solely because a few open trades are marked at a profit. Divide summed profits on winning closed trades by the absolute summed losses on losing closed trades, including costs in each trade. No losses or too few losses requires special review, not an automatic infinite score. |
| Cost robustness | The 6% hurdle must hold in the existing pessimistic case; report optimistic and base too. | Zero-cost profits do not qualify. Do not reduce the cost assumptions to manufacture a pass. |
| Execution/concentration robustness | Predeclared delayed-order, extra stop-cost, reverse-priority, and single-instrument-removal diagnostics remain profitable with drawdown below 5%. | A stress run need not itself achieve 6%, but cannot turn materially negative or breach the concern level. |
| Parameter robustness | Both predeclared neighboring channel rules remain profitable with drawdown below 5%; retain the original candidate. | A neighbor is a fragility check, never a replacement selected after seeing the final test. |
| Halt behavior | No permanent entry halt; report any pauses, blocked sessions, and whether exits remain possible. | Years spent in cash after a halt are not successful active-trading years. |
| Data and causality | Complete accepted scope, no unexplained gaps or fabricated candles, causal signals and next-session fills, no unresolved material data failure. | Financial metrics cannot compensate for an invalid simulation. |

**6% annually means approximately $10,000 growing to $11,236 over two years**
with compounding. It does not mean 6% every year, every trade, or on only the
fraction temporarily invested. Inflation and personal taxes are excluded
from this nominal research hurdle and must be identified as omissions.

Propose using this standard on both the full development replay and its
latest two-year development window before spending the final holdout. This
is intentionally demanding: the goal is to reject a strategy that does not
meet your objective. Individual years may lose money; report every year and
do not hide a losing year behind the cumulative return.

Higher desired returns with a small loss allowance are a demanding
combination, and taking more risk does not guarantee higher returns. See
[Investor.gov on risk tolerance and allocation](https://www.investor.gov/introduction-investing/getting-started/asset-allocation).
If no candidate qualifies, the valid decision is to stop or revise the goal,
not to keep searching until a historical chart happens to pass.

## 3. What the existing candidate says against this draft

These are comparisons with already inspected research, not new backtests or
new independent evidence. The previous studies retain their original
screening decisions; this owner-goal review does not rewrite their protocols.

| Existing result | Observation | Relation to proposed standard |
| --- | --- | --- |
| 2017-2023 pessimistic account return | +16.392% total; **2.192% CAGR** before estimated final sale costs | **Fails the proposed 6% return hurdle.** Charging final exit costs reduces the return slightly further. |
| 2022-2023 independent C-R3 selected-policy account | +1.280% total; +1.192% after estimated final exits | Also fails the proposed 6% annual hurdle; realized trade P&L was negative in this window. |
| 2017-2023 maximum closing drawdown | **4.584%** | Below 5%, but inside the proposed 4%-5% concern band. |
| 2017-2023 worst closing day | **-1.660%** | Below the proposed 2% daily-loss ceiling. |
| 2017-2023 completed trades / profit factor | 163 / 1.973 | Useful supporting evidence, but cannot repair the inadequate return or the weak recent window. |
| Account risk between daily closes | **Not established by the closing drawdown metric** | We cannot claim that your 5% concern was respected throughout each trading day. |
| Mean closing exposure | About **19.1%** | Low exposure explains part of the modest account return; it does not justify dividing account return by average exposure or increasing allocation without a new risk study. |
| Cash treatment | Uninvested cash earns zero in the existing research | Separate trading profit from any realistically available cash yield before making a real investment-value claim. Never assume the broker pays interest. |

**Recommendation: do not advance the current candidate to a final
2024-2025 investment-validation test yet.** It already misses the proposed
return requirement on inspected development data. Testing more years is not
a sound way to rescue that mismatch. Keep it as a frozen reference.

The older 3% daily-loss / 10% drawdown research halts also do not implement
your expressed 5% concern. They remain unchanged in the historical candidate.
If research halt settings are tightened, that creates a new policy requiring
its own declared development evaluation; do not silently change them in the
final holdout. A halt in the existing code stops new entries and does not
automatically close all holdings.

Stops and halts cannot guarantee an account-loss ceiling. Gaps, market
closures, stale observations, and adverse executions can produce overshoots.
The SEC explains that a [stop price is not a guaranteed execution price](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15).

## 4. Concrete sequence I propose

### Step A — Review these goals before another strategy search

**Owner:** Approve or amend the proposed 6% annual hurdle, the interpretation
of the $500 concern, and the other acceptance criteria. No Python edits or
account changes are required. The reply template below is enough.

**Codex:** Record the agreed criteria with a date and version. Do not put
them into the paper-risk JSON as though you had approved order submission.

### Step B — Audit investment value using development data only

**Codex's next proposed implementation**, after this review:

1. Produce an automated goal-fit report for the frozen candidate using
   existing 2017-2023 results, with 2022-2023 shown separately. Show every
   acceptance check as pass, fail, or not yet measurable. Preserve original
   study results and all previous failed hypotheses.
2. Attribute the account outcome to completed trades, open gains, transaction
   costs, idle cash, and exposure. Assess actual cash-yield assumptions
   separately if relevant data and account eligibility are established;
   do not credit a hypothetical rate as actual broker income.
3. Define and implement conservative daily-OHLC portfolio risk diagnostics,
   distinguishing observed closing drawdown, adverse same-day bounds, and
   genuinely measured intraday equity. Daily candles cannot reconstruct
   which lows occurred simultaneously across instruments. Intraday data,
   if needed to resolve the 5% question, requires its own coverage audit.
4. Add predeclared passive SPY references at **20% and 35% initial capital**,
   plus zero-yield cash, under the same cost cases. Report return, exposure,
   drawdown, and estimated exit costs. Initial allocation differs from
   average exposure because prices drift; these are opportunity-cost
   references, not exactly matched-risk portfolios. Do not choose the
   benchmark allocation after seeing which one the strategy beats.
5. Report the result as **does not qualify / inconclusive / worth further
   development**, without automatically launching another parameter search.
   Missing intraday risk evidence cannot count as a pass.

This work clarifies whether low capital use and accounting assumptions
explain the mismatch; it does not promise to improve the trading signal.
Do not increase exposure, add leverage, add more symbols, or add ML merely
to target a higher historical return.

### Step C — Decide whether this strategy line deserves one more study

If the goal-fit report still rejects the candidate, stop advancing it.
Codex can then propose one separately registered, finite alternative study
with a named economic hypothesis, fixed variants, and a research budget;
the owner decides whether it is worth pursuing. Define that study before
running it. Keeping a full trial log is required because repeated reuse of
2017-2023 increases selection bias; those years cannot become fresh evidence
again. A new study is not automatically authorized by approving this draft.

Retiring this strategy line is a valid outcome. The already completed data,
backtesting, risk, and order-management software remains useful.

### Step D — Conditional final 2024-2025 evaluation

Proceed only after a candidate qualifies on development evidence and the
owner approves a complete, frozen final protocol. No download/evaluation
command is implemented or activated by this proposal.

The proposed final scope is a fresh $10,000 simulated account on
**2024-01-01 through 2026-01-01 exclusive**, using 2023 only for indicator
warmup, the same twelve instruments, SIP/all-adjusted daily data, and one
continuous 2024-2025 account. No inherited 2023 positions are assumed.
Check whole-share sizing explicitly at $10,000; the old $100,000 results do
not simply scale because rounding and per-order fees matter. Any strategy
reaching this stage must first be evaluated at that same capital on the
development windows. A $10,000 simulation does not reset your paper account.

Before opening data, freeze the candidate code/settings, account size,
data conventions, scope, the criteria in Section 2, costs, benchmark arms,
stress definitions, and reporting rules. For breakout candidates retain
the existing 40/15 and 70/25 channel diagnostics, reverse BUY priority,
one additional discretionary-session delay plus 50 bps adverse stop
slippage, and all twelve single-instrument removals. SPY remains signal
context when excluded from trading. Any materially different candidate
needs its own explicit diagnostics before final evaluation.

Report the candidate plus unchanged original-rule/full-breakout references,
the fixed passive benchmarks, and cash. References provide context; do not
promote whichever arm wins the final period. Evaluate all predetermined
cases once, including failures. Do not drop a stock, change dates, ignore
an unexplained data gap, or lower a target after observing the result.

- **Reject:** A measurable return, risk, or robustness requirement fails.
  Do not start investment-oriented paper trading with that candidate.
- **Inconclusive:** Required coverage, trade count, risk observations, or
  accounting are insufficient. Resolve the evidence gap without claiming
  a pass or weakening the criteria.
- **Passes this screen:** All agreed checks pass. This supports a further
  readiness review, not proof of profit, absence of survivor bias, or order
  authorization. A two-year holdout remains limited evidence.

If inspected final results lead to changes, 2024-2025 become development
data for those changes; they cannot be reused as untouched confirmation.
SIP/all adjustments and this fixed survivor basket retain their previously
documented limitations even if performance passes.

### Step E — Separate paper activation decision

Only after accepted research and execution readiness:

- The owner approves the actual account size and every required field in
  `config/risk_limits.json`.
- Codex completes safe broker exits/protective stops, fill/activity
  accounting, and operational/recovery checks.
- The owner reviews the account's actual positions/open orders and a
  successful startup recovery report, then explicitly chooses to start a
  monitored paper trial.

Research approval never means permission to submit an order.

## 5. How you can respond

No file editing is necessary. Reply in chat, for example:

```text
Annual return hurdle: approve proposed 6% / change to ___%
$500 concern: 5% below the running account peak /
              $500 below starting capital / another interpretation: ___
Other draft research criteria: approve / changes: ___
Next work: prepare the development-only goal-fit audit from Step B.
```

Alternatively, ask for explanations or revisions before approving anything.
An approval here is limited to the specified research criteria and work; it
does not approve personal risk settings, a final holdout run, or paper
orders. `config/risk_limits.json` remains empty and
`approved_for_paper` remains `false`.

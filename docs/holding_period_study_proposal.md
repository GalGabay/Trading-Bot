# Proposal: holding-time exits and capital reuse

Date: **2026-10-24**. Status: **prepared for owner review; not evaluated**.

**Subsequent approval and amendment:** The owner approved implementation,
allowing continuation beyond session 60 with further reviews every 30
sessions. The original hard-maximum description below is retained as the
proposal history and is superseded by the
[approved amended protocol](holding_period_study_protocol.md). Implementation
and evaluation use that amended protocol, not the old maximum-60 rule.

The owner suggested selling an old holding to make room for another stock,
unless there is unusually strong evidence to keep it. The authorized work
in this turn is focused audit testing and this concrete next-study proposal.
No holding-time strategy or new backtest has been implemented/run here.
2024-2025 remain reserved, and paper orders remain disabled.

## 1. Which strategy was audited?

The frozen **55/20 breakout with conservative volatility sizing**, named
`vol_latched` in the research code:

- Enter when a completed daily close exceeds the highest high of the
  **preceding 55 sessions**, while the stock and SPY are above EMA200.
- Exit when the close breaks the preceding **20-session low**, the stock
  falls below EMA200, or SPY's market filter turns off. Those discretionary
  orders execute no earlier than the next session open.
- An initial **three-ATR14 stop** also exits, using the existing daily-OHLC
  execution approximation. This selected version does not trail that stop.
- No scheduled holding-time exit currently exists. Positions can run for
  days, weeks, or months. Completed trades averaged 61.42 calendar days in
  the continuous 2017-2023 account and 29.71 days in the separate $100,000
  2022-2023 account.
- Position value is sized using `min(5%, 1% / annualized_20_return_volatility)`,
  then limited by cash, whole shares, 0.5% planned stop risk, portfolio
  exposure, and the seven-position cap. It does not use a calibrated
  probability of future profit. Competing buys use alphabetical priority.

See the [audit results](study_c_goal_fit_results.md). Its failure against the
owner's approved 6% annual / 5% drawdown research criteria remains unchanged.

## 2. Hypothesis and reasons it might fail

**Hypothesis:** reviewing stale holdings after a fixed age may reduce time
spent in weak positions and free a binding position slot or budget for
another already qualifying signal. It may improve after-cost account
returns without increasing allocation limits.

**Important contrary evidence:** the audited $10,000 account averaged about
83% cash over 2017-2023 and 92% cash in the independent 2022-2023 window.
There was often money available already. Old positions may have consumed
one of seven slots, but that must be measured on actual signal dates.
Selling does not create an attractive replacement signal.

A time exit can cut a continuing winner, add turnover/costs, or leave the
money idle through the existing ten-session reentry cooldown. Therefore
"shorter holdings" is not itself a success criterion. The owner's account
return, realized profit, and risk criteria remain the decision standards.
Backtests do not establish future profitability; see the
[SEC's performance-claims bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-47).

## 3. Exactly three main arms

All retain identical entry signals, natural exits, initial stops, sizing,
costs, cash handling, cooldown, loss halts, and buy priority. Change only
the following optional holding-age policy:

| Arm | Additional exit policy | Purpose |
| --- | --- | --- |
| **Control** | None: the frozen audited strategy. | Establish the unchanged reference. |
| **Maximum 30 sessions** | At the close of the 30th held market session, schedule a full exit for the next open. | Test a simple maximum holding period, roughly six market weeks. |
| **Review at 30, hard maximum 60** | Review at closes of held sessions 30, 35, 40, 45, 50, and 55. Exit next open unless every continuation condition below holds. Schedule an unconditional exit after session 60. | Test a measurable exception for a continuing strong trend, while still imposing a maximum age. |

The continuation conditions are all required at the review close:

1. The close is **strictly above the preceding 20-session high**, excluding
   the current bar.
2. The position is profitable after its entry costs and estimated sale costs
   at that completed close. This estimate is a decision input, not an actual
   closing-price execution or a forecast of next-open profit.
3. The stock and SPY remain above their completed-close EMA200 values.

These are **observable continuation rules, not "extremely sure" odds**.
There is no validated probability forecast in the current strategy. No ML,
earnings prediction, or discretionary exception is introduced.

Thirty sessions is a declared first hypothesis, not an optimized number.
Do not add a grid of 10/15/20/40/90-session variants after seeing results.
Any amendment requested before evaluation must be recorded before running.

## 4. Exact timing, cash, and execution assumptions

- Count the actual **entry-fill session as held session 1**. A signal waiting
  for execution does not start the clock. Weekends/holidays do not count.
- At session 30's completed close, an age exit is queued for session 31's
  open. At the hard session-60 limit, it is queued for session 61's open.
  A gap can change its proceeds. No exit fills at the close used to decide.
- Stops and ordinary strategy exits can happen earlier. A queued natural
  exit is never canceled to extend a position. If a gap stop exits before
  a queued time exit, the queued sell cannot execute a second time.
- Touching a protective stop on an entry day still closes the position;
  the new clock does not suppress risk exits.
- Full exits return proceeds after costs to shared cash, and retain the
  same ten-complete-session reentry cooldown. A later actual reentry starts
  a new clock. No new position is forced merely because cash was freed.
- Exits are processed before already queued entries at the model open.
  A replacement buy still needs a valid earlier completed-close signal,
  sufficient cash, and all existing entry limits. No future winner is used
  to decide which old position should have been sold.
- At the dataset boundary, record a scheduled-but-unfilled exit and mark the
  remaining position normally. Do not manufacture a next-session price.
- Keep the simulator's cash-reuse assumptions explicit; this does not
  establish real broker buying power or settlement timing.

## 5. Fixed development scope and finite budget

Use only the existing audited twelve-symbol SIP/all-adjusted datasets and
actual saved session calendar. Same stock/ETF basket and adjustment/selection
limitations as earlier studies. No additional data purchase or symbol search.

| Item | Proposed fixed scope |
| --- | --- |
| Full development replay | 2017-01-01 through 2024-01-01 exclusive, 2016 warmup; one continuous account |
| Recent development check | Independent 2022-01-01 through 2024-01-01 exclusive, original 2019 warmup |
| Primary capital | **$10,000**, whole shares |
| Capital diagnostic | $100,000, without retuning any rule |
| Costs | Existing optimistic/base/pessimistic cases; retain the pessimistic $1 per-order fee assumption |
| Main replay budget | **36**: three arms × two windows × two account sizes × three cost cases |
| References | Same fixed 20%/35%-initial SPY and zero-yield cash, separately labeled |
| Final holdout | No 2024-2025 access |

These development windows have already influenced previous research and
overlap each other. They cannot become fresh evidence by changing the exit
rule. No claim of independent out-of-sample or statistical confirmation is
permitted. Record this as another hypothesis in the accumulated trial log.

### Conditional diagnostics, fixed in advance

Only if a new arm meets the measured primary-account criteria on **both**
development windows, run its declared pessimistic $10,000 diagnostics:

- Reverse simultaneous BUY priority.
- Add one session of discretionary order delay plus 50 bps adverse stop
  slippage; retain the original planned quantities and active stops.
- Remove each of the twelve instruments in turn; retain SPY market context
  when SPY is excluded from trading.
- Use the existing 40/15 and 70/25 entry/exit channel neighbors, preserving
  that arm's holding-age policy. The continuation-review high window stays
  20 sessions; do not tune it along with the channels.

That is **16 diagnostics per window, 32 per promising arm**, at most 64 for
the two new arms. The total finite strategy-simulation budget is therefore
**at most 100** (36 main + 64 conditional). No further variants are added.
Passive references and accounting summaries are not additional strategy arms.
If neither new arm meets the measured main criteria, stop after 36 replays.

No arm is automatically selected by its development ranking. If more than
one qualifies, present both with their limitations for the next decision.
Missing actual intraday risk evidence remains inconclusive even if a
candidate qualifies for these conditional development diagnostics.

## 6. Required reporting: does capital reuse really improve?

In addition to all approved goal-fit checks, report:

- After-cost total/CAGR and annual returns; realized/open P&L, estimated
  exit costs, closed trade profit factor, breadth, and loss halts.
- Average/median/max holding length; time exits versus natural and stop
  exits; positions still open at the end.
- Exposure, idle cash, turnover, order costs, and position-slot occupancy.
- On every qualifying BUY attempt, record whether the binding blocker is
  position count, cash, portfolio value cap, cooldown, stop risk, or missing
  valid sizing information. Do not infer this from average cash or label
  a rejected signal profitable using its future price.
- Following each time exit, report whether another instrument actually
  enters on that open or within the next five market sessions. This is an
  ex-post utilization diagnostic, never a signal input or proof that the
  sale funded that purchase. Cash may have been available beforehand.
- Compare the time-exit and control account paths at portfolio level. For
  early-sold positions, describe subsequent control holding behavior only
  as an ex-post attribution; do not choose the policy from those outcomes.
- Closing drawdown plus conservative daily-OHLC risk envelopes, distinctly
  labeled. An envelope is not an observed intraday equity path.

No leverage, higher exposure, changed loss halts, new rankings, or
confidence-weighted position sizing is bundled into this hypothesis.

## 7. Implementation and verification before accepting results

Codex would add a modular optional holding-age policy with no policy as
the default. Reproduce the original control fills/metrics at both account
sizes and every cost/window combination before accepting variant results.
Preserve the legacy reports and protocols; record new source hashes rather
than changing old ones to make provenance checks pass.

Focused tests must cover entry-fill age versus signal age, holidays, exact
review/maximum boundaries, causal continuation conditions, original exit
precedence, gap/touch stops, no duplicate sells, cooldown/reentry clocks,
session-60 hard exit, delayed discretionary orders, and unfilled final
exits. Verify that released cash can fund only a legitimately queued entry
and that default/no-policy reference results remain unchanged. Test and run
offline; no Alpaca order endpoint is part of this study.

## 8. Decision and owner action

The approved research criteria remain unchanged: at least 6% whole-account
annual return after pessimistic costs and estimated exits, closing drawdown
below 5% with review above 4%, daily closing loss below 2%, positive realized
P&L, profit factor at least 1.2, and at least 30 trades across five instruments
per two-year window. Stress/neighbor returns must remain positive with
drawdown below 5%, and unmeasured intraday risk cannot count as cleared.
See [the full acceptance plan](investment_acceptance_proposal.md).

If both new arms fail, retain the control reference and report that the
holding-time idea did not solve investment fit. Do not open the holdout or
continue searching maximum ages. Retiring this strategy line remains valid.

**Codex:** The next implementation would build/test the optional policy,
capacity diagnostics, and finite runner, then evaluate and report the exact
approved scope. No policy or strategy evaluation has been implemented here.

**Owner:** Review the three arms and the 30/60-session interpretation of
"a long time." You can approve this scope in chat or request a change before
evaluation; no Python or JSON editing is needed. This review step follows
Step C of the already approved [investment plan](investment_acceptance_proposal.md):
a new strategy study needs a concrete scope before it runs. Approval of this
proposal would cover offline development only, not holdout access, personal
paper-risk settings, or paper activation.

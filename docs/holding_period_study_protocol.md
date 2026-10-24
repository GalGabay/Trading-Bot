# Holding-time study: approved amended protocol

Registered 2026-10-24 before evaluating the variants. The owner approved the
[three-arm proposal](holding_period_study_proposal.md), with one amendment:
positions can remain open beyond session 60 if continuation evidence passes,
then are reviewed every 30 sessions. The original hard maximum is removed.
The owner also asked about broader universes; this study keeps its existing
twelve-symbol scope, so entry rules and universe effects are not confounded
with holding-age changes. No orders, paid data, or 2024-2025 inspection.

## Arms and interpretation

1. **control**: unchanged frozen `vol_latched` 55/20 breakout, stock/SPY
   EMA200 filters, initial fixed three-ATR14 stop, ten-session cooldown,
   volatility sizing, 5% position / 35% portfolio caps, 0.5% planned stop
   risk, seven positions, and existing latched 3% daily / 10% drawdown halts.
2. **maximum_30**: same rules, plus a full exit queued after the completed
   close of held session 30, filled no earlier than the next session open.
3. **continuation_30**: review at held sessions 30, 35, 40, 45, 50, 55, 60,
   and every 30 thereafter (90, 120, ...). Retain only if the completed close
   is strictly above the preceding 20-session high, estimated proceeds after
   sale costs exceed actual entry cost including commission, and the stock
   and SPY are above EMA200. Otherwise queue an exit for the next open.

These continuation gates are the proposal's observable proxy for
"extremely promising," not calibrated probabilities or a guarantee. There
is **no hard maximum** in the amended continuation arm. Natural exits and
stops remain active between reviews and may exit earlier. Do not add a
profit target, trailing stop, confidence model, ranking, or tighter entry.

Count the actual BUY-fill session as age one; use market sessions, not
calendar days or signal age. Stops precede queued sells at the open; only
one full exit is allowed. Existing exits are never canceled by an extension.
New entries require their own earlier completed-close signals and available
cash/limits. Cooldown applies after every exit, and a reentry resets age.
Final queued exits without a following session remain unfilled. Retain
previous planned quantities during delayed-execution diagnostics.

## Finite scope and decision gates

The original proposal's numerical scope, costs, risk and decision criteria,
reporting requirements, and finite budget remain:

- Same audited 2016-2023 SIP/all-adjusted daily files and saved calendar.
- Continuous 2017-2023 account (2016 warmup) and independent 2022-2023 account
  (original 2019 warmup). Already inspected, overlapping development data;
  not independent out-of-sample evidence or a new final test.
- $10,000 primary and $100,000 diagnostic accounts, all three cost cases:
  **36 main simulations**. Replay all twelve controls first; require exact
  old goal-fit metric and fill matches at each size/window/cost before
  accepting variant scores. The extra journal may not change these fields.
- Reuse the original fixed passive 20%/35% SPY references and zero-yield cash
  with their original capital, costs, and exposure caveats.
- Keep `config/research_acceptance.json` unchanged. Each new arm needs the
  approved measured checks on both primary-account windows. Actual intraday
  risk remains inconclusive; passing closing-risk checks is not clearance.
- Only a promising arm proceeds to its predeclared 16 pessimistic $10,000
  diagnostics per window: reverse priority; extra execution session plus
  50 bps stop slippage; twelve single-symbol removals with SPY context
  retained; 40/15 and 70/25 channel neighbors. Keep continuation's review
  high-window fixed at 20. At most 32 diagnostics per new arm, 64 total,
  so the study stops at **100 strategy simulations maximum**. No parameter
  search, threshold relaxation, or promotion of whichever neighbor wins.

## Capital and exit diagnostics

Record per-BUY planning/execution attempts, snapshot cash/equity, quantity
constraints where evaluated, position count, held ages, and the first
blocking check reached. Stop after the first rejecting check, as the
existing engine does: other blockers may also exist. Zero-share budgets
can identify tied binding constraints. A blocked attempt is not a proven
profitable opportunity, and repeated daily attempts are not independent
trades. Missing sizing data and sub-share planning are distinct from cash.

Report position-slot occupancy, average cash/exposure, holding-time
distributions, age/natural/stop exits, reviews beyond 60, turnover, costs,
and after-cost performance. After a time exit, report whether a different
instrument buys at that open or within five sessions, censoring incomplete
future windows. This is ex-post utilization, not proof the sale was needed
to fund the buy or a future-price input to decisions. Do not force a new BUY.

Reconcile every ledger with its closing marks using the existing risk
envelope helper. Keep realized/open P&L and estimated final sale costs
separate. A daily-OHLC envelope is a conservative bound, not an observed
intraday path. Preserve old source hashes/reports; record new hashes and
financial reference replay evidence rather than rewriting provenance.

If neither new arm meets the measured primary criteria, stop at 36. Report
all failures and retain the control as a reference. If one qualifies,
complete its fixed diagnostics and report any missing evidence; there is
no automatic final-holdout or paper authorization. A broader universe or
entry redesign requires its own scope and validation before use in paper.

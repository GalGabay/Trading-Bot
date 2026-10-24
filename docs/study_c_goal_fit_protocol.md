# Development-only investment goal-fit audit

Registered 2026-10-24 before the new $10,000 replays. The owner approved the
6% annual return hurdle, 5% loss/drawdown concern, the remaining acceptance
criteria, and Step B of the investment acceptance plan. Interpret 5% as the
draft's running-equity-peak drawdown; it is not a fixed $500 amount after
the account grows. This approval is for research and this audit only.

Machine-readable review criteria: `config/research_acceptance.json`.
Personal paper policy remains in `config/risk_limits.json` and is unchanged.
Do not change the frozen strategy's 3% daily / 10% drawdown halt settings to
make this audit fit the owner's 2% daily / 5% drawdown acceptance criteria.
Report the difference. A new halt policy would require a separate study.

## Fixed scope

- Same twelve symbols, SIP/all-adjusted daily bars, 2016-2023 datasets and
  saved market calendar. No API requests or 2024-2025 data access.
- Same `vol_latched` 55/20 breakout, stock/SPY EMA200 filters, fixed initial
  three-ATR stop, ten-session reentry cooldown, and conservative sizing.
- Full development account: 2017-01-01 to 2024-01-01 exclusive, with 2016
  warmup. Recent development account: independent 2022-01-01 to 2024-01-01
  exclusive with the original 2019-2023 warmup history, matching C-R3.
- Optimistic/base/pessimistic cost cases, each at $100,000 and $10,000:
  **twelve main simulations**. Reproduce C-R4 full and C-R3 recent $100,000
  metrics and fills exactly before accepting the audit. The smaller account
  changes initial capital only; no threshold or allocation is tuned.
- Fixed passive SPY references at 20% and 35% initial capital, each window,
  cost case, and account size. They are opportunity-cost context with drift,
  concentration, and halt differences, not exact risk matches. Cash yields
  zero throughout; no hypothetical interest is credited as broker income.
- Reuse C-R3/C-R4 declared stress results at their actual $100,000 scope.
  Do not extrapolate their performance to $10,000 or fabricate missing
  recent-period channel results. Missing risk/stress evidence is inconclusive.
  No additional parameter variations are selected or run in this audit.

## Accounting and risk diagnostics

Reconcile the actual saved fills against every closing equity and exposure
observation and the final positions. Account for commissions, modeled
slippage/spread, realized and open P&L, estimated final exit costs, cash,
exposure, holding time, and the gap to 6% compounded account growth.

Adding back costs on the realized fill path is an accounting decomposition,
not a zero-cost counterfactual: removing costs can change later quantities,
halts, and trades. Estimate no cash yield without evidence of eligibility
and an appropriate historical rate. Do not divide account return by mean
exposure to claim a return on invested capital.

Daily risk reporting must distinguish closing drawdown, model open-equity
marks, a conservative daily-OHLC envelope, and genuinely observed intraday
equity. Reconstruct cash and positions from fills. Treat ordinary fills and
gap stops as model-open events. For touched stops, allow both pre-exit
holdings valued within that day's high/low and after-exit net cash proceeds.
Combine their independent extrema conservatively with the other positions.
For a worst drawdown bound, permit an upper-equity envelope peak before a
later lower-envelope value, including within one session.

These extrema need not occur together or in that order. An envelope beyond
5% does not prove an actual 5% breach. It means daily data cannot resolve the
question. Even an envelope within 5% is conditional on this simulation's
execution assumptions, not evidence of actual broker/intraday behavior.
Never label the envelope an observed loss or feed it into the strategy.
Actual intraday equity remains unmeasured. Reject missing prices or ledger
inconsistencies; do not fill prices or manufacture intraday timestamps.

## Decisions and limits

Evaluate the approved criteria on pessimistic net returns after estimated
final sale costs, using full calendar-year CAGR. Preserve all cost cases.
Use pass/fail/inconclusive labels, a separate 4% drawdown review flag, and
retain failed checks even when another requirement is unmeasurable.
Fewer than 30 completed trades or five instruments is inconclusive breadth.
Undefined profit factor is inconclusive, never an automatic pass.

Any measured failure means the candidate **does not qualify**, even if some
other checks are inconclusive. No change in the new goal-fit decision may
rewrite the historical C-R3/C-R4 screen results. Existing survivor-basket,
corporate-action, selection/repeated-development, and fill assumptions remain.
The $10,000 replay illustrates capital sensitivity; it does not set or alter
the actual Alpaca account. Cash reuse follows the existing simulator and
does not establish available buying power or settlement behavior at a broker.

Deliver a JSON audit plus a readable result record. No orders, configuration
approval for paper, holdout opening, ML, leverage, confidence-based sizing,
or new strategy search are part of this task. If the candidate fails,
preserve it as a reference and propose a separate, finite next research
decision rather than searching automatically for parameters that pass.

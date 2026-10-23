# Study C-R4: frozen breakout on earlier history

Registered 2026-10-23 before downloading or inspecting the new period's
performance. The owner authorized the historical-coverage audit and fixed
strategy evaluation. No orders, paid data purchase, personal risk approval,
or 2024-2025 evaluation are authorized by this study.

## Scope and evidence limits

Use the same fixed 12 symbols and Alpaca SIP/all-adjusted daily bars.
[Alpaca documents historical equities since 2016](https://docs.alpaca.markets/us/docs/about-market-data-api)
and [historical SIP access rules](https://docs.alpaca.markets/us/docs/market-data-faq).
Actual availability and quality must be checked; documentation is not proof
that every requested bar exists.

Request **2016-01-01 through 2019-01-01 exclusive** for every symbol. Audit
checksums, timestamps, duplicate/OHLC/price/volume checks, and the broker's
actual session calendar. Preserve warnings and investigate material anomalies.
Capture a calendar snapshot covering 2016-2023 for repeatable offline checks.
No missing candles may be manufactured, filled, or bypassed by dropping a stock.

Primary new-history window: warm up on 2016 and score **2017-2018** continuously
with one $100,000 account. If any primary dataset fails, attempt the coverage-only
fallback **2017 warmup / 2018 score**, fetching a separate complete 2017-2018
dataset for every symbol. Select a window based only on data completeness,
before any performance calculation. Disclose the incomplete primary scope;
never describe a fallback as completing the two-year test. If the fallback
also fails, stop scoring the basket and report the specific blockers.

The secondary replay joins the accepted new datasets with the unchanged
2019-2023 SIP datasets and validates the full joined calendar. Use a single
account, continuous holdings, and retained equity peak over **2017-2023**
(or 2018-2023 under the coverage fallback). Do not reset a loss halt at a year
boundary. Distinguish these long-window results from old independent runs.

This is **backward historical robustness research**. The rules were chosen
using 2020-2023, which is later than the new dates. It cannot establish a
genuine historical walk-forward deployment or fresh forward out-of-sample
performance. The present-day survivor basket and future corporate-action
adjustments retain their selection/point-in-time biases. IEX's previously
audited coverage does not support an equivalent pre-2019 feed comparison.

## Frozen arms, with no new selection

1. **candidate:** C-R3 `vol_latched`, unchanged 55/20 breakout and SPY/EMA200
   filter, fixed initial three-ATR14 stop, ten-session reentry cooldown,
   at most seven positions, 5% position / 35% total entry caps, 0.5% planned
   stop-risk cap, and `min(5%, 1% / annualized_20_return_volatility)` sizing.
   Daily 3% and drawdown 10% halts stay latched. No automatic restart.
2. **full_breakout_reference:** unchanged C-R3 `full_latched`: same breakout,
   stop, and cooldown, but 10%/70% caps and 1% planned stop risk.
3. **original_rule_reference:** unchanged original trend/RSI/volume strategy,
   its original 10%/70%/seven-position limits, and no protective stop or cooldown.

All use the existing optimistic/base/pessimistic cost cases, next-session
execution, prior-close share planning, and gap-aware stop-price approximations.
Sells and stops remain permitted after a halt. Reproduce the C-R3 candidate
metrics and fills on its two old windows and all costs before accepting new
scores. No arm, target, channel, stop, symbol, or risk threshold is tuned here.

## Frozen diagnostics and reporting

Run all three arms under all three cost scenarios on the new-only and joined
windows. Include annual returns and total/CAGR, closing drawdown and worst
day, exposure, completed/open trades, realized/unrealized P&L, estimated exit
costs, and permanent/daily halts. Explicitly flag years spent halted.

On the **new-only window**, run these candidate diagnostics under pessimistic
costs, regardless of the main return:

- Reverse simultaneous BUY priority.
- Delay discretionary orders by one additional session and add 50 bps adverse
  stop slippage, keeping stops active and original planned quantities.
- Remove each symbol in turn, retaining SPY as market context when excluded.
- Use 40/15 and 70/25 channel neighbors as fragility checks only. Preserve
  55/20 as the frozen rule; do not select a neighbor using this new evidence.
- Report a paired circular 20-session, 2,000-draw bootstrap against zero-yield
  cash and against the full breakout reference, using fixed seed 20261023.
  Intervals describe this sample, not selection-adjusted statistical proof.

Provide passive SPY references at 35% and 70% initial allocations, all cost
cases, and zero-yield cash for both windows. These have different exposure,
concentration, and halt behavior; they are context rather than equal-risk tests.

The frozen candidate passes this additional-history screen only if the new
window's pessimistic return stays positive after estimated final exit costs,
closing drawdown is below 10%, no permanent halt occurs, at least 20 trades
close across five instruments, priority/delay/all stock-removal returns stay
positive with drawdown below 10%, both channel neighbors remain positive,
and the joined pessimistic account remains positive after estimated exits
without a permanent halt. Report every failure and any negative year.
Insufficient trade count is inconclusive evidence, not a reason to lower
the threshold. A coverage fallback cannot pass the primary two-year scope.

Regardless of outcome, retain C-R2's existing negative-year/channel failures
and C-R3's open-profit dependence. Do not open 2024-2025 to rescue a failure.
Passing this historical screen alone does not approve paper activation,
replace owner risk decisions, or complete broker exits and fill accounting.

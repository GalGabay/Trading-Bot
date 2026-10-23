# Study C-R2: daily strategy improvement study

Protocol registered on 2026-10-23 before inspecting these new arms' returns.
This is exploratory development on already opened years. The owner authorized
designing and evaluating improvements; this does not approve paper orders,
personal risk limits, or opening 2024-2025. Results will be appended below.

## Motivation and fixed scope

Study C's two-year pessimistic return was -0.524%; its two-ATR trailing-stop
variant P1 returned -10.501% and traded much more often. The feed audit found
material differences in volume-based entry candidates. Test fewer, slower,
price-based decisions and explicit broad-market exits rather than optimizing
the old thresholds repeatedly. Trend-following research supplies a general
motivation, not evidence for this particular stock basket or these rules
([Hurst, Ooi and Pedersen](https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing)).
Repeated backtests increase selection bias; this study therefore has a fixed
candidate list, earlier-period selection, and explicitly labeled diagnostics
([Bailey et al.](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)).

Use the same 12 immutable SIP/all daily datasets, 2019-2023, and the same
provisional 10% position, 70% entry exposure, seven-position, 1% planned
stop-risk, 3% daily-loss, and 10% drawdown limits. The loss/drawdown halt remains
latched until the simulation ends. Stops can gap beyond the planned risk.
Signals form at completed session closes; orders are sized from that close
and fill no earlier than the next open. Warmup uses preceding data only.
Positions and the equity peak carry across years within each run.

## Frozen arms

| ID | Purpose and rules |
| --- | --- |
| baseline | Unchanged `trend_following_v1`, no stop or cooldown. Reference only. |
| no_volume | Same rule and exits as baseline, omit volume confirmation only. Diagnostic ablation; not eligible for selection. |
| regime_trend | BUY when SPY close > its EMA200, symbol close > EMA200, EMA50 > EMA200, EMA20 > EMA50, and RSI14 >= 50. No upper RSI limit or volume filter. SELL at next open after symbol close < EMA50, EMA20 < EMA50, or SPY close <= EMA200. Fixed initial stop at signal close minus 3 ATR14. |
| regime_breakout | BUY when SPY close > its EMA200, symbol close > EMA200, and close exceeds the highest high of the preceding 55 completed sessions (exclude today's high). SELL at next open after close falls below the preceding 20-session low, below EMA200, or SPY close <= EMA200. Fixed initial stop at signal close minus 3 ATR14. |
| regime_breakout_trail | Same breakout rules and initial 3 ATR14 stop; after each completed close, raise the stop to at least close minus 4 ATR14. Never lower it; the raised level starts next session. |

All three eligible arms prohibit reentry until ten complete sessions after
any exit: an exit in session i permits the next fill in session i+11.
Both market and symbol data must be available on exactly the signal date.
Missing candles are rejected, never filled. Protective stops are daily-OHLC
execution proxies; no profit target forces an otherwise healthy trend out.

## Chronology and selection

1. Warm up on 2019, score a continuously funded account over 2020-2021.
   Fixed settings above are not fitted by a parameter grid.
2. An eligible arm needs positive pessimistic returns in **both** earlier
   years, no entry halt, drawdown within 10%, at least 20 completed trades,
   and completed trades in at least five instruments. Select once by the
   highest pessimistic worst-year return, then fewer completed trades, then
   lexical arm ID. Return **no selection** if none qualifies.
3. Freeze that selection before scoring 2022-2023. Report all arms in that
   later, already inspected development period; do not switch the selected
   arm because another later result looks better. These years are not a
   fresh holdout, including for new variants informed by their old results.
4. Reproduce the old baseline exactly before accepting any research numbers.

## Comparisons and robustness

Run all five arms in the three existing cost cases. Report whole-account
returns by year and in total, max drawdown, closed trades, holding time,
mean exposure, profit factor, realized versus marked P&L, fees/turnover,
entry halts, and estimated adverse end-of-period liquidation costs. Keep
both marked and hypothetical liquidated figures; a final liquidation at
the observed close is a diagnostic, not a claim of executable closing fills.

Compare with cash (zero interest) and 70%-initial-allocation SPY buy-and-hold
under the same cost cases, including hypothetical exit costs. That benchmark
has different concentration, position caps, exposure drift, and no risk halt;
it supplies market context, not an equal-risk hurdle.

For the arm selected on earlier years, or all three eligible arms if there
is no selection, run predeclared diagnostics without choosing a new winner:

- Reverse simultaneous BUY priority under pessimistic costs.
- Fill entry and discretionary-exit orders one additional session later,
  preserving original signal quantities; existing protective stops remain
  active. Apply pessimistic costs and 50 extra bps adverse stop slippage.
- Remove each tradable symbol in turn under pessimistic costs. SPY remains
  available solely as external regime context if removed from trading.
- For breakout arms only, perturb channels to 40/15 and 70/25 sessions.
  These are sensitivity checks; do not promote the best neighbor.
- Compare SIP and IEX signals on the complete 2022-03-09 to 2023-12-29 window,
  with 206 warmup sessions and a fresh 2023 account. Use **SIP execution bars
  for both** to isolate signal-feed effects. Validate all 12 IEX datasets
  first. Keep this shorter window separate from the two-year main result.
- A paired circular block bootstrap (20-session blocks, 2,000 draws, fixed
  seed) describes uncertainty in two-year pessimistic return differences
  against baseline. It is exploratory, conditional on this selected sample,
  and does not correct earlier human choices or repeated research trials.

An arm merits further development only if its pessimistic later return is
positive, exceeds baseline without worse drawdown, both later annual returns
are nonnegative, no entry halt occurs, at least 20 trades close across five
instruments, hypothetical liquidation remains positive, and the predeclared
priority, delay/stop-cost, symbol-removal, and channel checks remain positive
without drawdown beyond 10%. Report which requirements fail. A bootstrap
interval spanning zero means improvement remains statistically uncertain.
Passing these development checks alone cannot authorize paper activation.

If all fail, record the failure and propose the next evidence-gathering step;
do not keep altering rules within this study until a winner appears. Preserve
the complete trial log and unopened 2024-2025 final holdout.

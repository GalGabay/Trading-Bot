# Study C-R3: allocation and daily halt/restart protocol

Registered on 2026-10-23 before inspecting the new policies' returns.
The owner authorized implementing and simulating this study. It is offline
research; no broker orders or personal risk approvals are involved. Keep
2024-2025 unopened. The fixed present-day universe and inspected development
years retain the limitations documented in C-R2.

## Hypothesis and unchanged strategy

Study C-R2's fixed-stop 55/20 breakout improved pessimistic 2022-2023 return
to +3.209%, but lost in 2022 and failed its broader screen. All earlier-period
arms hit a 3% daily halt on June 11, 2020 and stayed inactive afterward.
Investigate smaller allocations and explicitly modeled daily-halt recovery.
Do not change entry channels, exits, initial stop distance, or cooldown.

Use the same 12 validated SIP/all daily datasets, with 2019 warmup. Select
on a fresh $100,000 continuously funded 2020-2021 account before simulating
a separate $100,000 2022-2023 account. Both retain holdings and peaks across
their internal year boundary. The same three cost scenarios apply.

## Six fixed policy arms

All use the fixed-stop 55/20 breakout, a three-ATR initial stop, ten complete
sessions of symbol cooldown, at most seven holdings, a 3% daily loss threshold,
and a 10% drawdown threshold. Sizes are planned at the signal close and can
only shrink at the execution open.

| ID | Position/total entry caps | Planned stop-risk cap | Sizing | Daily halt |
| --- | --- | --- | --- | --- |
| full_latched | 10% / 70% | 1% | Fixed caps, C-R2 reference | Lasts through run |
| full_pause | 10% / 70% | 1% | Fixed caps, diagnostic reference | Five-session pause + review proxy |
| half_latched | 5% / 35% | 0.5% | Fixed smaller caps | Lasts through run |
| half_pause | 5% / 35% | 0.5% | Fixed smaller caps | Five-session pause + review proxy |
| vol_latched | At most 5% / 35% | 0.5% | Volatility sizing below | Lasts through run |
| vol_pause | At most 5% / 35% | 0.5% | Volatility sizing below | Five-session pause + review proxy |

For volatility sizing, estimate annualized standard deviation from the last
20 completed close-to-close returns using the existing feature. Target
weight = `min(0.05, 0.01 / estimated_annualized_volatility)`, before stop risk,
cash, and total exposure caps. At 20% annual volatility this gives 5%; at
40% it gives 2.5%. Missing, nonfinite, or nonpositive volatility blocks a BUY.
There is no leverage, future volatility estimate, or resizing existing holdings.
This is a per-instrument risk-budget proxy, not a portfolio-volatility target:
correlations, jumps, and estimation error can overwhelm it. Volatility research
motivates testing reduced exposure when volatility rises; it does not establish
these settings as optimal ([Moreira and Muir](https://www.nber.org/papers/w22208)).

Entry caps do not force rebalancing when existing positions appreciate. Stops
and halts cannot guarantee a realized loss ceiling or execution price.

## Explicit offline halt state machine

- A daily equity loss of at least 3% from the previous session close blocks
  entries immediately when detected at an open or close. Sells and protective
  stops remain active. Paused arms cancel all pending BUYs and do not queue
  new BUYs while halted. Permanently latched arms retain the legacy skipped
  candidate audit but never execute those BUYs. Keep one daily-halt event per
  session in paused arms, including repeated breaches
  on later paused sessions. A close breach after an open breach extends the
  same day's pause without double-counting the daily event.
- In latched arms, that daily halt remains active through the run.
- In paused arms, a breach in session i blocks the next **five complete
  sessions**, i+1 through i+5. Earliest review is the open of i+6. A new daily
  breach during the pause moves that deadline forward from the new breach.
- Review is a **research-only proxy**: the immediately preceding session's
  SPY close must be above its EMA200, and current opening loss/drawdown must
  be below their thresholds. Exact prior-date data is required; never use
  today's future SPY close. Failed review leaves entries blocked. After
  resumption, require a fresh actionable close signal; stale canceled BUYs
  do not reappear.
- A 10% drawdown from the continuously retained closing equity peak creates
  a permanent drawdown halt in every arm, including during a daily pause.
  There is no automatic drawdown reset, peak reset, forced liquidation, or
  historical insertion of owner decisions.
- Record daily halts, restarts, permanent halts, and sessions blocked at the
  open. The production kill switch and approved-paper configuration are not
  changed. A real restart would need its own reviewed operational design.

## Selection and evaluation

The two full-allocation arms are diagnostics, not eligible selections. Among
the other four arms, require positive pessimistic returns in both 2020 and
2021, at least 20 completed trades across five symbols, drawdown less than
10%, worst closing daily loss no worse than 3%, and no permanent halt at end.
Select by highest pessimistic worst-year return, then smaller drawdown, then
fewer completed trades, then lexical ID. Write the selection before any new
arm's 2022-2023 scores. If none qualifies, report no selection.

Report all six arms under all costs on both windows, including annual and
total return, closing max drawdown and worst day, exposure, closed-trade
counts, realized/open P&L, hypothetical exit costs, halt counts and reasons,
restart dates, and blocked sessions. Verify full_latched against C-R2's
fixed-stop breakout metrics and fills before accepting new results.

This study evaluates an **allocation trade-off**, with risk criteria written
explicitly before results. Further allocation research requires positive
pessimistic later return after hypothetical exits, improved drawdown and
worst day versus full_latched, no permanent halt, at least 20 closed trades
across five instruments, and passing stresses below. Report any negative
year prominently. This does not overturn C-R2's failed nonnegative-year or
channel-sensitivity criteria or approve paper trading.

For the earlier-selected arm, or all four eligible arms if none selects,
run these diagnostics under pessimistic costs:

1. Reverse BUY priority.
2. Delay discretionary orders by one additional session and add 50 bps adverse
   stop slippage; stops stay active during the delay.
3. Remove each tradable stock/ETF in turn, retaining SPY solely as context if
   excluded from trading. Require positive total returns and drawdown <10%
   in these priority, execution, and symbol-removal checks.
4. For a selected paused arm, test one- and ten-session pauses without selecting
   the best duration. For a selected volatility arm, test contribution targets
   0.75% and 1.25%, retaining the 5%/35% hard caps. Treat failures as fragility.
5. Report a paired 20-session circular-block bootstrap (2,000 draws, fixed
   seed) for return difference versus full_latched. It is descriptive and
   does not correct previous trial choices.

For all six arms, separately compare 2023 SIP and IEX signals on the validated
complete March 2022-December 2023 window, always using SIP execution bars.
Use fresh 2023 accounts and matching warmup. Compare cash and passive SPY
with initial 35% and 70% allocations; clearly label their different position
and halt policies. No parameter sweep or new strategy arms are added after
results. Preserve every outcome and leave the final holdout closed.

# Daily shadow observer: signals and allocation previews

Implemented October 31, 2026. **This records observations, not broker orders or
simulated trades.** Personal paper-risk approval is not needed to use it.
The preceding research comparison's Steps 1-4 remain complete.

## Current verified status

[137 offline tests and the first collection are complete](shadow_observer_validation_results_2026-10-31.md).
This includes 66 new observer tests and 71 regressions, with zero final
failures/errors/skips. Tests exposed and fixed Windows SQLite connection
cleanup. One authorized collection used 43 GETs and produced the October 30
observation: three BUY / 17 HOLD, with a 10.40% hypothetical allocation from
an unchanged flat reference book. Offline replay matched exactly; duplicate
recording retained one journal row. There were no orders, simulated fills,
purchases or account queries. No scheduler is installed; Pi remains unverified.
Use `latest` below to inspect the saved report without another request.

## What you can see

- Each watched stock's BUY, SELL, HOLD or UNAVAILABLE signal and explanation.
- Completed session, observation timestamp, SPY trend filter and next session
  open. Daily signals expire at that next open; an old signal is not rolled
  forward to another opening just because the observer ran late.
- Reference stock exposure, intended share quantities, planned exposure and
  shortfall from the **70% target**, with an **85% entry ceiling**.
- Whether cash remains because of signals, data gaps, warmup, position slots,
  stop/volatility sizing, target room, cash or a reference risk diagnostic.
- Data-quality warnings, excluded unfinished bars and blocked symbols. Symbols
  with bad data remain visible in the report; the watchlist is not silently
  reselected.

The observer reuses the existing feature builder, daily 55/20 breakout rules,
stock/SPY EMA200 filters, volatility sizing and continuation-review logic.
It does not implement the proposed stricter entries, momentum ranking or
weekly C2 rebalancing. This is not a performance run of the six-policy proposal.

## Reference portfolio and sizing

By default, every observation starts from an explicitly **flat $10,000
reference book**. No account/positions endpoint is queried. No hypothetical
fill is carried into the next observation. A repeated BUY can appear again
on a later date; it is another observation, not a duplicate broker order.
There is no observer return, P&L, dividend credit or paper-account balance.

Preview BUY sizing uses alphabetical priority and the smallest whole-share
capacity permitted by target room, the 85% ceiling, 5% per-stock cap, 20 slots,
cash, the existing 0.5% planned stop-risk input and 1% annualized-volatility
contribution input. These last two values are frozen research sizing inputs,
not newly approved personal paper-risk limits. The estimated entry uses the
completed close plus the existing base-cost proxy; it is not a current quote
or a guaranteed next-open price. The stop preview is three ATR14 below close.
The 70% target does not force purchases when these checks limit quantity.

An optional `--reference PATH` lets you supply a book explicitly describing
the latest completed session, with `as_of_session`, `cash`, `peak_equity`,
`day_start_equity` and a `positions` array. Each position requires `symbol`,
current `asset_id`, positive whole-share `quantity`, `average_entry_price`,
`stop_price` and an available `entry_session`. The fixed initial stop must
remain below entry. Quantities, basis and cash must already reflect actual
company events; this tool does not infer missing events or settlements.

Reference holdings are marked only with valid latest-session prices. Unknown
held prices or inconsistent references block the allocation preview. Natural
exits, completed-close stop breaches and due continuation reviews are reported
as intended exits. **A SELL never frees preview cash or slots until a new
explicit reference book reflects it.** The observer does not simulate a sale.
Exit history/cooldown and full event-adjusted holding ages are not inferred.

For supplied books, the old 3% daily/10% drawdown research entry-halt diagnostics
are clearly labelled. They are not the owner's 5% acceptance criterion or the
later personal paper-risk policy. References above exposure/position caps
also block new allocations. No kill switch is reset and no position is closed.

## Data and operating defaults

The editable [shadow configuration](../config/shadow_observer.json) contains a
20-stock starter **observation sample**, with SPY reserved for context. It is
not the historical 76-stock basket, a whole-market screen, a recommendation
to buy those stocks or an approved paper universe. You can change the explicit
watchlist before beginning an observation version; at most 50 stocks are
supported. Current asset identity, active status and tradability are checked
for every stream when collecting.

Collection uses **IEX, daily, split-adjusted signal bars** under existing
access. IEX coverage differs from the earlier SIP research. Provider split
adjustments are current signal normalization, not proof of historical known-at
factors or broker cash accounting. See the official
[bar API specification](https://docs.alpaca.markets/us/reference/stockbars).

The fixed transport supports only GET requests for stock bars, individual
asset metadata and the market calendar. It has no account, order, cancellation,
billing or subscription operation, no endpoint override, no redirects, no
automatic retry and no SIP/paid-feed fallback. There is a 110-request run cap,
three-page-per-symbol cap, 20-second request timeout and bounded response size.
A 180-second collection budget is checked before/after requests; an in-flight
network call still depends on its socket timeout rather than a process watchdog.
An access/rate/transport failure stops the collection. Requests do not upgrade
entitlements or purchase data.

History starts in **2026**, preserving the reserved 2024-2025 candles. At least
200 complete sessions are required, using at most the latest 252 sessions.
The exchange calendar handles holidays, weekends and early closes. A default
15-minute post-close settling buffer excludes the current/unsettled daily bar;
it is an operating assumption, not a vendor finality guarantee. Missing
scheduled observations are coverage blockers, not invented candles or assumed
trading losses. No prices are filled, and no prior close substitutes for a
missing latest bar. The collector does not fetch intraday quotes or candles.

## Commands

Run from the repository root using that machine's Python environment.

### Collect once and write an observation

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m app.shadow.observer collect
```

Raspberry Pi/Linux equivalent (not yet validated on the Pi):

```bash
./.venv/bin/python -m app.shadow.observer collect
```

Only `collect` constructs the read-only transport and loads existing credentials
through the central loader. No credential values are printed. It reads the
existing environment/repository `.env`; do not paste keys into these commands.
No dependency installation, subscription change or paper-risk approval is
performed. The first verified collection loaded credentials through this loader; no values were inspected or logged.

### View the latest saved observation

```powershell
.\.venv\Scripts\python.exe -m app.shadow.observer latest
```

### Evaluate a saved bundle without credentials or network calls

```powershell
.\.venv\Scripts\python.exe -m app.shadow.observer observe --bundle data/shadow/bundles/REPLACE_WITH_SAVED_BUNDLE_HASH.json
```

Saved-bundle observations use the bundle's recorded observation time. They
must not be presented as new current signals. No trade-performance backtest
is run by this command.

## Output, versions and repeated use

- `data/shadow/observer.sqlite3`: separate observation journal; the existing
  trading database/schema is not changed. Non-shadow tables are rejected.
- `data/shadow/bundles/`: immutable collected input files.
- `data/shadow/reports/`: immutable JSON and readable Markdown per observation.
- Console: the same signal/allocation summary.

The same bundle/config/reference/code/environment is idempotent. A revised
data bundle produces a distinct auditable observation; it does not overwrite
the previous report. Payload checksums detect stored-content corruption.

Code, configuration and dependency versions are recorded. A changed version
must use a fresh `--database`, for example
`--database data/shadow/observer_v2.sqlite3`; it cannot silently mix with the
previous observation version. Keep bundles, databases and reports as local
research/runtime files. They are covered by the existing `data/` Git ignore.

This is **one-shot**, with no background service or scheduler installed. Run
it after a completed US session plus the settling buffer, or before the next
session opens. Running on a weekend can report the last completed session.
Run `latest` to inspect an existing report without another data request.
Ongoing collection/scheduling can follow the first reviewed run.

## Implementation status and next work

Focused verification and one current-data collection are now complete; see
[the result and review](shadow_observer_validation_results_2026-10-31.md).
The first implementation record and initial failing-test evidence remain
historical, with original guide/source snapshots preserved separately.

Next engineering work is calendar-aware repeated observation with a visible
status/report command, explicit request/run budgets and restart behaviour.
Review the concrete schedule before installing an OS task or unattended
service. You do not need personal paper-risk approvals for these no-order steps.

Before actual paper orders, complete the broker fill ledger, protective exits,
recovery and supervised loop, then review full paper-risk limits/account state
and explicitly authorize a paper trial. Shadow outputs cannot bypass these
gates. The prior four-step research comparison remains complete; this is the
first implementation toward prospective observation.

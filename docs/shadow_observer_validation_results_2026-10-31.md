# Shadow observer: offline verification and first reviewed collection

Completed October 31, 2026. **137 offline tests passed; one read-only collection
and its offline replay completed.** The observer has not placed orders or
created simulated fills. No repeat task or background service is installed.
Previous research Steps 1-4 remain complete.

## Tests and fixes

- **66 new observer tests** cover config/JSON validation, complete-bar selection,
  holiday/weekend calendars, early closes, settling time, missing/duplicate/
  invalid candles, volume warnings, warmup, signal expiry, reference identity,
  holding reviews, sizing/cash/position limits and no implicit fills.
- **71 related regression tests** cover market data, features, strategy,
  holding policy and daily research.
- Final result: **137 run, zero failures, errors or skips**, with network
  connections blocked and fake credentials/responses for transport tests.
- Real-account/trading-client construction and credential loading are forbidden
  in the saved-data tests. Transport tests cover endpoint allowlists, GET-only
  requests, access/rate/redirect stops, pagination, time/request/size limits
  and the lack of paid-feed fallback.
- Persistence tests cover idempotence, changed code/config/environment,
  immutable exports, corruption detection and rejection of non-shadow databases.

The first focused run had 58 tests, zero assertion failures and seven errors.
Those errors exposed open SQLite handles on Windows: a transaction context
does not itself close a connection. Production and fixture connections now
close explicitly, including failure paths. The new regression verifies that
Windows can move the database immediately afterward. Duplicate recording also
checks the stored payload checksum. Config type errors now consistently reject
invalid values. The initial log/source snapshot and subsequent passing runs
are retained; the initial result is not overwritten.

[Passing verification and exact source/log hashes](shadow_observer_verification_2026-10-31.json)

## The authorized collection

The collection was registered before execution and ran once through a
240-second supervisor. The transport retained its 180-second checked budget,
110-request cap, response/page limits and no-retry behaviour.

Actual collection:

| Item | Result |
| --- | --- |
| Observed | October 31, 2026, 11:16:56 Israel time |
| Completed session evaluated | October 30, 2026 |
| Stocks / market context | 20 watched stocks plus SPY |
| Daily candles | 209 per stream; 4,389 total |
| GET requests | 43: one calendar, 21 asset metadata, 21 bars |
| Transport / access failures | Zero |
| Data warnings / unavailable stocks / global blockers | Zero |
| SPY trend filter | On |
| Runtime | About 25.1 seconds |
| Signal counts | Three BUY, 17 HOLD |
| Orders / simulated fills / purchases | Zero |

All bars were from 2026, IEX and split-adjusted. No reserved 2024-2025 candles
were accessed. Existing credentials were loaded only by the authorized
transport; their values were not inspected or logged. The audit confirms
that no account, positions, orders, billing or subscription endpoint was used.

The next session in the provider calendar is **Monday, November 2, 2026,
09:30 New York / 16:30 Israel**. The recorded signal preview expires at that
open. This calendar accounts for the US daylight-saving change over the
weekend; it is not a fixed UTC-offset assumption.

## What the preview says

These quantities use the latest completed close plus the existing base-cost
estimate. They are **observed strategy proposals, not investment instructions,
orders, actual execution prices or money spent**.

| Symbol | Intended shares | Estimated notional | Binding sizing cap |
| --- | ---: | ---: | --- |
| ABBV | 1 | $294.99 | Volatility sizing |
| WMT | 3 | $370.75 | Volatility sizing |
| XOM | 2 | $374.74 | Volatility sizing |
| **Total** | | **$1,040.49** | |

The hypothetical planned exposure is **10.40%**, with **$8,959.51** remaining
after those intended buys. No buys actually occurred: the stored reference
remains flat with $10,000 cash and no positions. There is no profit/loss result.

The 70% target and 85% ceiling were not the limiting factors in this snapshot.
Only three stocks qualified for fresh entries, and risk sizing plus whole-share
rounding reduced their quantities. At most three 5% positions could have used
15% even before those additional sizing constraints. The other 17 stocks were
HOLD because there was no prior-high breakout.

This is one flat-start observation in a 20-name operational sample. It does
not measure average exposure of a running portfolio with accumulated holdings,
performance of the proposed weekly target allocator, or the whole market.
No entry rule, sizing limit or watchlist was changed to force investment.

## Review and persistence

After collection, the saved bundle was reevaluated offline with credential
loading forbidden. The complete canonical report matched exactly. Re-recording
it returned the existing observation, and the journal retained **one row**.
Every proposed quantity was independently checked against the per-position
notional and planned stop-risk caps; totals reconcile to the allocation preview.
The reports and input bundle are pinned by checksum.

- [Full first observation: all 20 symbols](shadow_observer_first_observation_2026-10-31.md)
- [Collection summary](shadow_observer_first_collection_2026-10-31.json)
- [Offline review and allocation checks](shadow_observer_first_review_2026-10-31.json)
- [Registered single-collection scope](shadow_observer_collection_protocol_2026-10-31.json)
- [Operating guide](shadow_observer.md)

The full local input, SQLite journal, JSON report and request audit remain
under `data/shadow/` and `data/reports/shadow_first_collection_2026_10_31_v1/`.
These large runtime artifacts are ignored by Git; retain them with the local
observation archive. The tracked reports do not contain credentials.

To read this saved observation without another request:

```powershell
.\.venv\Scripts\python.exe -m app.shadow.observer latest
```

## Next work and your part

**Next - engineering:** prepare calendar-aware repeated observation, so a new
completed session produces one reviewed snapshot and weekends/holidays do not
trigger full duplicate collections. Provide a visible status/report command,
an explicit run/request budget, interruption/restart behaviour and instructions
for Windows and the Pi. Review the concrete schedule before installing any
OS task or unattended service. Until then, this remains a successful single
collection, not an ongoing observer.

**Your part now:** inspect the saved observation if useful. No personal risk
approval, API-key change, installation or paid data is needed for this no-order
work. The initial 20-name watchlist is explicitly an observation sample;
expanding it is separate from historical research membership or paper approval.

Raspberry Pi execution remains unverified. Actual paper orders still require
the complete fill/protective-exit/recovery workflow, reviewed personal risk
limits and explicit trial activation. The proposed six-policy research batch
has not been run by this task.

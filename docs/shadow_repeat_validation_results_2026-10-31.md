# Repeat controller: offline tests and reviewed tick

Completed October 31, 2026. **207 tests passed, then one reviewed tick completed.**
No recurring task or foreground loop was installed or started. Historical
research Steps 1-4 remain complete. This work does not activate paper orders.

## Test results

| Scope | Passed |
| --- | ---: |
| New repeat-controller tests | 70 |
| Existing shadow-observer tests | 66 |
| Related market-data/features/strategy/holding/daily-research regressions | 71 |
| **Total** | **207** |

Final result: **zero failures, errors or skips**, about 30 seconds on Windows.
Network connections were blocked. Synthetic candles/calendars and fake
transports were used; no real keys or broker clients were needed. Subprocess
lock checks used local Python processes only.

The new tests cover:

- Settled-close boundaries, weekends, explicit holidays, early closes, New
  York calendar dates, the US DST change, expired signals and missed sessions.
- Calendar refresh limits and the bounded refresh-then-collect sequence.
- Durable request reservation before credential/client construction; exact
  budget boundaries, attempt caps and expiry without refunds or resets.
- Access/transport failure, secret suppression, interruption, explicit resume,
  unknown request counts and no automatic retry.
- Saved-bundle recovery, corruption, wrong sessions and idempotence after a
  simulated crash or exception following the actual SQLite journal commit.
- Real Windows process locking, refusal of overlapping processes, release
  after abrupt process death, and atomic-state write failures.
- Policy/config changes, no carried positions/fills/cash changes, visible
  data blockers, local status/latest, foreground exit and endpoint restrictions.

The initial run had **62 tests, one assertion failure and zero errors**.
That assertion compared an in-memory tuple with the list produced by JSON
loading. It now compares canonical saved content. Eight further cases were
added before the final run. **No production controller code change was
required.** Initial logs/source snapshots are retained separately.

[Verification, source hashes and test-log reference](shadow_repeat_verification_2026-10-31.json)

## One reviewed tick

The tick was registered after the passing tests, with a limit of one tick
and **zero requests**. Preflight checked that the real saved campaign and
calendar called for waiting. Credential loading, transport construction,
trading-client construction and socket connections were forbidden during
execution. The actual CLI entry point ran once with the real clock/state.

| Item | Result |
| --- | --- |
| Tick exit code | 0 |
| Action | Waiting: no new completed, settled session |
| Last recorded session | October 30, 2026 |
| Collection/calendar attempts in campaign | 0 / 0 |
| Reserved/known requests in campaign | 0 / 0 |
| New observations | 0 |
| Credentials loaded / transports constructed | 0 / 0 |
| Campaign bytes and original one-shot journal | Unchanged |
| Personal risk JSON | Unchanged |
| Orders / fills / purchases | 0 |

October 31 is a weekend; the reviewed October 30 observation was already
known. Skipping collection is the expected result. No stock data was
downloaded again. The next local-calendar refresh checkpoint is November 1,
04:00 UTC, **if the controller is invoked then**; no background process will
wake itself. This is not a new trading session or a scheduled execution.

[Registered tick protocol](shadow_repeat_tick_protocol_2026-10-31.json) and
[review, before/after state and execution log references](shadow_repeat_tick_review_2026-10-31.json)
preserve the evidence. Runtime artifacts live under
`data/reports/shadow_repeat_tick_2026_10_31_v1/` and are ignored by Git.

## What remains and who does it

**Engineering next:** prepare concrete Windows/Pi recurring-task definitions,
visible failure reporting and installation/removal instructions for review.
The proposed cadence remains one tick every 30 minutes plus a startup trigger
on one host. No OS task is installed. Actual Pi execution and a real due
collection through the controller remain unverified; the existing one-shot
collector's successful collection is separate evidence.

**Your next observation decision, when the schedule is ready:** choose one
host (Windows PC or Pi), its operating hours and approve the concrete recurring
task. If using Pi, provide that machine and its own environment/keys and let
me guide its checks. No personal trading-risk approval is needed for shadow
observation.

**Before actual paper orders, later:** approve the personal risk policy,
review the selected strategy/results and limitations, understand existing
paper-account positions/open orders, review the startup recovery and verified
fill/protective-exit workflow, then explicitly approve the bounded trial.
The [owner checklist](owner_responsibilities.md#upcoming-decisions-in-order)
explains the sequence. You can tell me decisions in plain language; I can
prepare the appropriate configuration for review.

There is no profit/loss result from this tick: shadow observation still
does not create fills or accumulate positions.

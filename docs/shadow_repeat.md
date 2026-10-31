# Calendar-aware repeated shadow observation

Implemented October 31, 2026. This extends the [daily observer](shadow_observer.md)
with a separate repeat controller. **No scheduled task, background process or
service is installed or running.** Initialization adopted the reviewed October
30 observation without new requests, orders or purchases.

**Current verification:** [207 offline tests passed and one reviewed tick completed](shadow_repeat_validation_results_2026-10-31.md).
This includes 70 controller tests and the earlier 137 observer/regression
checks. The actual tick correctly waited without credentials, requests or a
duplicate report. No recurring task/process is running. Real due collection
through the controller and Raspberry Pi execution remain unverified. The
earlier implementation record remains historical, with its guide snapshot
preserved in [the archive record](shadow_repeat_history_2026-10-31.json).

## Calendar and reporting

Each tick reads local state and the actual exchange calendar. It refreshes
the calendar once per New York calendar date when needed: one GET, including
on weekends if invoked. Full stock collection happens only for a new session
whose actual close plus the existing settling buffer has passed (15 minutes
by default). Holidays, early closes and daylight-saving changes use the
calendar rather than a fixed closing hour.

Already recorded sessions do not trigger another full collection. A missed
session whose next opening has passed is expired; wait for a new settled
close. After a longer outage, missed sessions are listed in the next campaign
event. No historical signal is backdated as current, and no candles are filled.
A missing or invalid calendar halts instead of assuming a holiday.

The existing GET-only collector still uses daily IEX, split-adjusted bars and
2026-or-later history. There are no account, positions, order, billing or
subscription operations and no paid fallback. A transport/access failure
halts instead of triggering automatic retries. Data blockers remain in the
day's report; there is no automatic recollection to erase a bad-data result.

Every observation still uses a **flat reference portfolio**. Repeated BUY
previews do not accumulate positions. There are no fills, dividends or P&L.
The signal rules, 20-stock observation sample, 70% target and 85% ceiling are
unchanged. This is not a profitability experiment or paper activation.

## Budgets and timing

[config/shadow_repeat.json](../config/shadow_repeat.json) contains:

| Limit | Default |
| --- | ---: |
| Campaign duration from initialization | 30 days |
| Full collection attempts | 22 |
| Separate calendar-refresh attempts | 35 |
| Total reserved requests | 2,500 |
| Foreground local polling interval | 300 seconds |
| One foreground run | 8 hours; at most 24 |

A full attempt permanently reserves **110 requests**, even if it uses fewer.
A separate calendar refresh reserves one. These are conservative API-request
allowances, **not money charged**. Known requests appear separately; a killed
process may leave the count unknown. Failed/uncertain attempts retain their
allowance after resume. Expired/exhausted campaigns do not automatically reset.

The existing transport retains its three-page-per-symbol cap, bounded response
size, 20-second socket timeout and 180-second budget checked around requests.
The controller also prevents new requests after campaign expiry. It has no
process watchdog: in-flight calls depend on socket timeouts, and processing
or saving can finish after a duration limit. Foreground hours bound polling;
an already-started collection is allowed to finish. These are not hard process
kill deadlines.

`init` refuses an existing campaign. `resume` cannot extend/reset limits.
A deliberately new campaign uses a fresh directory; preserve the old evidence.

## Commands

Run from the repository root with that machine's virtual environment. The
default Windows campaign is already initialized from the saved first report.

### Inspect locally, without requests or credentials

```powershell
.\.venv\Scripts\python.exe -m app.shadow.repeat status
.\.venv\Scripts\python.exe -m app.shadow.repeat status --json
.\.venv\Scripts\python.exe -m app.shadow.repeat latest
```

Status shows the saved session, signal expiry, next action/check, campaign
expiry, attempts, reserved/known requests, pending work, policy match, recent
events and latest data blockers. `ready` means the campaign can be run; it
does **not** mean a process is currently watching the market.

### One tick or foreground repetition

The focused verification and reviewed no-op tick are complete. For a later
explicit manual tick or foreground session:

```powershell
.\.venv\Scripts\python.exe -m app.shadow.repeat tick
.\.venv\Scripts\python.exe -m app.shadow.repeat run --hours 8
```

`tick` may refresh the calendar and collect if due, then exits. Otherwise it
exits without a full collection. `run` repeats this in the foreground. Keep
the terminal/computer awake; closing it stops observation. There is no
detached process or automatic start after reboot. Ctrl+C while waiting stops
the loop; Ctrl+C during collection preserves the reservation and halts work.

### Pause and recover

```powershell
.\.venv\Scripts\python.exe -m app.shadow.repeat pause
.\.venv\Scripts\python.exe -m app.shadow.repeat resume
```

`pause` prevents future work when no other tick holds the lock; it does not
interrupt an active request. `resume` acknowledges a halt after review; it
does not itself make requests.

- Crash after a bundle was durably saved: the next tick can finish that same
  report offline. Already-recorded journal entries are idempotent.
- Crash without a saved bundle: the next tick halts the uncertain attempt.
  Inspect status, then resume explicitly if appropriate. A subsequent tick
  may collect only if the session remains eligible and budgets permit it.
- Normal failures remain halted. For a halted attempt with a saved bundle,
  resume arranges recovery of that bundle, not another download.
- Corrupted state/artifacts require restoration. Never delete a campaign to
  hide an uncertain attempt or reset its counters.

A Windows/Linux OS file lock prevents concurrent collections in the same
directory and releases on process exit. Writes use a checksum, temporary file,
flush and atomic replacement. Request reservations are saved before loading
credentials. Use local disk and back up the whole campaign; these measures do
not guarantee recovery from every power/disk failure. Do not run one campaign
on two machines. Never remove a lock file while a controller might hold it.

## Files, versions and Pi

Default runtime directory: `data/shadow/repeat/`, ignored by Git:

- `campaign.json`: version, calendar, counters, pending operation and events.
- `controller.lock`: synchronization; its presence alone means nothing about
  whether a process is running.
- `bundles/` and `reports/`: immutable collected inputs and readable reports.
- `observations.sqlite3`: separate journal for newly collected reports. The
  adopted seed is identified in state and copied into `reports/`.

The original one-shot journal and trading database are not modified. Controller
code, observer code, configuration and Python/dependency versions are pinned.
A changed version requires a fresh campaign directory, not relabeling old state.

On a fresh machine, produce/review a one-shot observation in that machine's
environment first, then initialize from it:

```bash
./.venv/bin/python -m app.shadow.repeat init
./.venv/bin/python -m app.shadow.repeat status
```

Windows uses `.\.venv\Scripts\python.exe` for the same commands. Optional
`--seed-database PATH` / `--seed-bundle PATH` select the saved seed. For a
new version, pass `--directory data/shadow/repeat_v2` on every command. The
seed must match the observer code/config/environment and flat no-fill policy.
Absolute artifact paths and environment pins mean copying an active Windows
campaign to Linux is not a supported migration. Real Pi execution remains due.

## Proposed schedule and next work

Focused verification is complete. Next review one `tick` **every 30 minutes**, on one
host, plus its startup trigger. Calendar logic decides whether data is due;
there is no fixed US-close hour in the OS schedule. The machine must be awake
and online. A report may arrive up to about 30 minutes after the 15-minute
settling buffer, depending on trigger timing.

Windows Task Scheduler would use the full Python path, arguments
`-m app.shadow.repeat tick`, the repository as working directory and no
parallel task instances. Pi would use a systemd timer/service with explicit
interpreter/working directory. Review the actual task/service and failure
reporting before installation. **Nothing has been installed by this work.**

**Engineering next:** prepare concrete recurring-task definitions, visible
failure reporting and installation/removal instructions for Windows and Pi.
Review the actual schedule and verify the chosen host before installation.
The existing default campaign still expires November 30; verification did
not extend its duration or reset its counters.

**Owner now:** no risk-file edits, purchase or settings needed. Later choose
Windows PC or Pi as the single observation host when the concrete schedule
is ready. Personal risk approval and explicit paper-trial activation remain
required before paper orders. Prior research **Steps 1-4 remain complete**.

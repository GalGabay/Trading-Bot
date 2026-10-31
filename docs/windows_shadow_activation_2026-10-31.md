# Windows observer installed and first invocation reviewed

**Installed October 31, 2026, after owner approval: "Approve Windows installation".**
`TradingBot-ShadowObserver` is enabled under the signed-in
`GALGABAY-LAPTOP\galga` account, with run level **Limited**. The account is
not an administrator. This enables recurring read-only observation.
Historical research Steps 1-4 remain complete.

## Actual result

| Item | Observed result |
| --- | --- |
| Registration | Installed and enabled; state Ready after its first invocation |
| First launch | Requested through the real Task Scheduler, October 31 at 19:36 Israel time |
| Task result / heartbeat | `0` / healthy, no issues |
| Controller action | Waiting: no new completed, settled session |
| Last observed session | October 30, 2026 |
| New requests / full collections | 0 / 0 |
| Orders / fills / purchases | 0 |
| Campaign and personal risk JSON | Byte-for-byte unchanged |
| Installed definition | `data/shadow/schedule/review_v3/` |

The exported registered task matches the approved 30-minute/sign-in cadence,
account, least privilege, no waking, no overlap, five-minute limit, exact
program/arguments/working directory and expiry. Windows omits some default
XML values and normalizes account names/timezones; native properties confirm
Limited and WakeToRun false. Windows truncates fractional trigger-expiry
seconds, ending less than one second earlier than the campaign.

The first launch was requested via Task Scheduler to check the actual OS
launcher/Python/reporting path. A natural timer/sign-in trigger and a real
due collection remain to be observed. This waiting run is not a new data
download or a performance result.

[Registration, exported task, first-run and heartbeat evidence](windows_shadow_activation_2026-10-31.json)

## Account correction before registration

The initial `review_v2` draft used Codex's isolated `CodexSandboxOffline`
identity. The installer ran as the actual signed-in user `galga`. Its owner
guard correctly rejected the mismatch before registering anything.

The approved current-user task was regenerated as `review_v3` for `galga`.
Comparison confirmed that only the two owner fields and review-directory
argument changed. The approved schedule, limits and privileges were preserved.
No administrator task or sandbox-account task was created. The previously
tested source files are unchanged.

[Owner-correction comparison](windows_shadow_owner_correction_2026-10-31.json)

## What happens now

- Checks run every **30 minutes** and at sign-in. Keep Windows **awake,
  online and logged in**. A locked screen works; VS Code and a terminal do
  not need to remain open.
- Full collection runs only for a new completed session plus the settling
  buffer. Weekends/holidays normally wait; a daily calendar refresh can use
  one GET. Missed observations are not invented afterward.
- Budgets remain 22 full attempts, 35 separate calendar attempts and 2,500
  reserved requests. Expiry is **November 30, 2026, 13:58 Israel time**.
  No duration or counter resets automatically.
- Reports are local, with no push/email notification. Shadow observations
  do not accumulate positions or report P&L.
- Failed/uncertain collections halt for review. Source/configuration changes
  are also guarded. Keep this deployed revision stable; develop changes in
  a separate checkout and deliberately review/version later deployments.

## Read status

From a normal Windows terminal at the repository root:

```powershell
Get-ScheduledTask -TaskName TradingBot-ShadowObserver
Get-ScheduledTaskInfo -TaskName TradingBot-ShadowObserver | Select-Object LastRunTime, LastTaskResult, NextRunTime
.\.venv\Scripts\python.exe -m app.shadow.scheduled status
.\.venv\Scripts\python.exe -m app.shadow.repeat status --json
```

`scheduled status` reads the heartbeat. OS commands confirm registration.
The standalone repeat controller does not query OS registration: its
`scheduler_installed_by_this_controller=false` describes that module's own
actions, not this Windows task. Use the OS query for installation status.

Disable future triggers with:

```powershell
Disable-ScheduledTask -TaskName TradingBot-ShadowObserver
```

Disabling does not interrupt an active tick. After any active tick finishes,
remove the task if desired:

```powershell
.\deploy\windows\Remove-ShadowObserver.ps1 -WhatIf
.\deploy\windows\Remove-ShadowObserver.ps1
```

Counters, reports and databases are retained. See the
[full operating guide](shadow_schedule.md) for interruption/recovery details.

## Next work and your part

**Engineering next:** review an automatic trigger and the next new-session
report when available. Continue paper-execution preparation with the broker
fill/activity ledger and protective-exit workflow in an isolated development
checkout, keeping this observer revision stable.

**Your part now:** keep Windows available when observation should run and
inspect status/reports as useful. No Pi setup or risk-file edit is needed
for observation. Before paper orders, approve personal limits, review the
strategy/results, account positions/open orders and startup recovery, then
explicitly approve the bounded trial after execution/protection checks.

No additional unit tests were run for installation because no application
source changed. The 272 passing tests remain pinned. Actual Pi operation
and paper execution remain unverified and disabled.

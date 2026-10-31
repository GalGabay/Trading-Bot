# Windows shadow task: installation approval

**Update: approved and installed.** See [the actual activation report](windows_shadow_activation_2026-10-31.md).
The task runs under the signed-in `galga` account using `review_v3`. An owner
mismatch correctly blocked the isolated-tool-account draft before registration.
The following proposal/commands document the earlier review and are historical;
use the activation/operating guide for the installed version.

Original status: verified and ready for owner review; not yet installed.
The owner selected Windows as the starting host. [272 tests passed](shadow_schedule_validation_results_2026-10-31.md),
including 65 new scheduling/deployment tests. Actual registration/trigger
operation has not happened, and Pi operation remains unverified.

## Exact task proposed

| Setting | Proposed value |
| --- | --- |
| Name | `TradingBot-ShadowObserver` |
| Host/account | This Windows PC, current signed-in user; least privilege, no stored password |
| Cadence | Every 30 minutes, every day, plus sign-in |
| Availability | PC awake, online and logged in; locked screen is supported |
| Wake from sleep / power-plan changes | None |
| Window | Hidden PowerShell process; task remains visible in Task Scheduler |
| Operation | One calendar-aware shadow tick with local heartbeat/failure reports |
| Data access | Existing GET-only IEX bars, asset metadata and calendar; no paid fallback |
| Overlap / run limit | Ignore overlapping OS instances; five-minute OS execution limit |
| Campaign | Existing `data/shadow/repeat/`; no reinitialization or budget reset |
| Budgets | 22 full attempts, 35 separate calendar attempts, 2,500 reserved requests, 30-day campaign |
| Current expiry | November 30, 2026, 11:58 UTC / 13:58 Israel time; triggers stop at the saved expiry |
| Reports | Local `data/shadow/schedule/` plus the existing observer reports |
| Trading | Zero order operations; no fills, carried positions or P&L |

A check may only read local state. A calendar refresh can use one GET per
New York date; a full collection runs only for a new completed, settled
session. Sleep/offline periods can cause missed observations; signals are
not backdated as current. An eligible/missed trigger may execute soon after
registration. VS Code does not need to remain open once installed.

The exact generated files and source fingerprints are under
`data/shadow/schedule/review_v2/`: `windows-task.xml`, the future Pi examples
and `manifest.json`. The original `review/` is preserved as an earlier draft.
The current task checks its reviewed source/configuration/output fingerprints
again before a tick. Code changes require a fresh review.

## What approval means

Approval authorizes registration of **this recurring read-only Windows
observer**, periodic requests under existing free access/budgets, and local
logs/reports. It does not authorize paper/live orders, purchases, personal
risk-policy approval, wake-from-sleep changes or Pi installation.

Installation needs your decision because it creates a persistent Windows OS
task that can run later without another chat message. Your earlier request
explicitly called for review before installation. You do not need to choose
the host again or edit any configuration file to answer.

## Concrete commands

Already checked locally without registration:

```powershell
.\.venv\Scripts\python.exe -m app.shadow.schedule verify --review-directory data/shadow/schedule/review_v2
.\deploy\windows\Install-ShadowObserver.ps1 -ReviewDirectory data/shadow/schedule/review_v2 -WhatIf
```

**After explicit approval**, engineering can run:

```powershell
.\deploy\windows\Install-ShadowObserver.ps1 -ReviewDirectory data/shadow/schedule/review_v2
```

Then inspect the task, first invocation and local heartbeat. If automatic
registration needs Windows account privileges unavailable to the current
session, stop and explain the exact limitation rather than enabling elevated
execution or changing the owner silently. Installation success alone does
not establish strategy profitability or paper readiness.

Removal later uses `deploy/windows/Remove-ShadowObserver.ps1`; it keeps all
budgets and reports, checks ownership and refuses an active run unless
explicitly stopped. Full operation/removal instructions are in
[the schedule guide](shadow_schedule.md).

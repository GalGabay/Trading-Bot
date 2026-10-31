# Windows-first observation schedule: files and review

Prepared October 31, 2026. **Windows is the selected starting host**, including
the intended initial paper-trading stage later. Pi migration comes after the
workflow is stable and verified there. This decision does not enable paper
orders or approve personal trading-risk limits.

**Installed and enabled after owner approval:** [activation and first invocation](windows_shadow_activation_2026-10-31.md).
The actual signed-in user `galga` runs the least-privilege `review_v3` task.
Its first Task Scheduler invocation returned 0 with a healthy heartbeat and
zero requests. Campaign/risk settings are unchanged and no paper orders are
enabled. Historical research Steps 1-4 remain complete.

**Current verification:** [272 offline tests passed](shadow_schedule_validation_results_2026-10-31.md),
including 65 new schedule/deployment tests. The tested code produced the
fresh `review_v2` task; in-memory XML validation and installer/remover
`-WhatIf` checks passed. See [the exact installation review](windows_shadow_installation_for_review_2026-10-31.md).
Those preflight-only records preceded installation. The installed owner correction and actual results are in the activation report.

## What you chose, and what remains to review

| Option | What it means | Current decision |
| --- | --- | --- |
| Windows PC | Uses the development computer, its existing environment and paper keys. Observation needs the PC awake, online and logged in. | **Chosen for the start.** No Pi setup needed now. |
| Raspberry Pi | A separate host with its own environment, keys and runtime state. Can stay powered independently of the PC. | Future migration after checks on the actual Pi. |

You understood the sequence correctly: Windows observation, a separately
approved Windows paper trial after the execution workflow is ready, then
possible migration to Pi. Moving hosts does not improve strategy returns.
Stable operation and a profitable strategy are separate questions.

The installed schedule is:

- **One check every 30 minutes, every day, plus a check when you sign in.**
- Runs as your current Windows user, without administrator privileges or a
  stored account password. A locked screen is fine; signing out stops this
  current-user task from running.
- The task is visible in Task Scheduler; its PowerShell window is hidden.
- No wake-from-sleep, power-plan change or automatic dependency installation.
  A sleeping/shut-down PC cannot observe. Keep it available around the US
  close plus the settling buffer, or before the following opening.
- Windows defers execution when it considers the network unavailable. A
  missed trigger can run when eligible; there is no burst of historical
  observations. Startup/sign-in collection can halt if connectivity fails.
- Calendar logic selects the completed session. Most checks only inspect
  local state. A calendar refresh can make one GET per New York date,
  including weekends; full collections happen only for new eligible sessions.
- New reports are normally available about **15-45 minutes after the actual
  close**, if the PC is available. Daily observation is unchanged: this is
  not a 30-minute trading strategy or the future paper execution loop.
- Five-minute OS execution limit and no overlapping task instances. An
  interrupted request is handled by the existing durable recovery rules.
- Existing campaign limits stay **30 days / 22 full attempts / 2,500 reserved
  requests**. The current Windows triggers expire with the campaign on
  **November 30, 2026**; no counters or duration reset automatically.

VS Code can be closed: Task Scheduler starts the program independently.
The task is now registered and can run while the PC is available.

**Host choice and installation approval are complete.** Keep Windows awake,
online and logged in when observation should run. Personal risk approval is
still a later decision before paper orders.

## Files prepared

| File | Purpose |
| --- | --- |
| [schedule.py](../app/shadow/schedule.py) | Generate exact Windows XML/Pi units; verify source, output and campaign fingerprints locally. Never registers tasks. |
| [scheduled.py](../app/shadow/scheduled.py) | One bounded tick with local heartbeat/failure reports; offline health command. |
| [Invoke-ShadowObserver.ps1](../deploy/windows/Invoke-ShadowObserver.ps1) | Hidden task entry point; captures local stdout/stderr and a fallback report if Python cannot start or the observer fails. |
| [Install-ShadowObserver.ps1](../deploy/windows/Install-ShadowObserver.ps1) | Verify the review, owner SID and Task Scheduler XML; refuse existing tasks; support `-WhatIf`. |
| [Remove-ShadowObserver.ps1](../deploy/windows/Remove-ShadowObserver.ps1) | Remove only this repository's named task; retain all campaign data. Refuse a running task unless explicitly requested. |
| [service template](../deploy/systemd/shadow-observer.service.in) / [timer template](../deploy/systemd/shadow-observer.timer.in) | Future Pi oneshot job and 30-minute/boot timer. No automatic retry/reset. |

The exact current Windows XML, future Pi examples and checksum manifest are
generated locally under `data/shadow/schedule/review_v3/` for the installed
signed-in owner. `review/` and `review_v2/` are historical drafts; the latter
used the isolated tool account. They contain actual
paths and your Windows user SID, but no keys/passwords. Runtime files are
ignored by Git; the generator, scripts and templates are in the repository.

## Local failure reporting

Read health without network or credential access:

```powershell
.\.venv\Scripts\python.exe -m app.shadow.scheduled status
.\.venv\Scripts\python.exe -m app.shadow.scheduled status --json
.\.venv\Scripts\python.exe -m app.shadow.repeat status
```

| Exit/result | Meaning |
| --- | --- |
| `0` | Last completed wrapper invocation reported no issues. This alone does not prove a scheduler is installed. |
| `2` | Failure: policy change, halted controller, blocked observation, interrupted/stuck run, unreadable report or launcher failure. |
| `3` | Attention: no heartbeat yet, stale heartbeat, paused/finished/expired campaign, unavailable symbols or a tick currently in progress. |

Before activation, a missing heartbeat correctly returned exit 3. The installed
task now has a real successful wrapper heartbeat; use `scheduled status` to
read its current result. The standalone repeat controller does not query OS
registration; use `Get-ScheduledTask` for that, rather than inferring it from
the controller's own `scheduler_installed_by_this_controller` field.

New local artifacts under `data/shadow/schedule/`:

- `runs/`: immutable started/finished JSON for each invocation; records issues,
  time and controller counters without raw credential/client exception text.
- `latest.json`: atomic checksum-pinned pointer to the latest event.
- `launcher_logs/`: stdout/stderr captured by the Windows entry point.
- `launcher_failure.json`: fallback if Python/observer launch fails. A later
  successful invocation supersedes its alert; the file remains as evidence.

No heartbeat for **90 minutes** is reported as stale. A started run without
completion for ten minutes is interrupted/stuck. Reports retain hard errors
when also stale. The wrapper lock prevents concurrent wrappers, and the
existing controller still owns durable request reservations and data access.
A disk failure can prevent local reporting; consult Task Scheduler as well.

These are **local reports**, not email, Telegram or push notifications.
Read them and the Windows task result. Nothing can send an immediate alert
from a powered-off PC. No connection to a messaging service was created.

## Windows installation and future reinstallation

Run from the repository root in your normal Windows terminal. The task is
already installed; do not register it again. For a deliberately reviewed
future version after stopping/removing the old task, choose a fresh directory:

```powershell
$taskOwnerSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
.\.venv\Scripts\python.exe -m app.shadow.schedule prepare --windows-user $taskOwnerSid --review-directory data/shadow/schedule/review_v4
```

Review the XML, manifest and scripts. `verify` and `-WhatIf` are local:

```powershell
.\.venv\Scripts\python.exe -m app.shadow.schedule verify --review-directory data/shadow/schedule/review_v3
.\deploy\windows\Install-ShadowObserver.ps1 -ReviewDirectory data/shadow/schedule/review_v3 -WhatIf
```

If using a versioned review directory, supply `--review-directory` to `verify`
and `-ReviewDirectory` to the installer. A changed source/output fingerprint,
wrong Windows SID or non-ready campaign blocks installation. XML is also
checked in memory by the local Task Scheduler parser without registration.
The OS-triggered wrapper checks the prepared source/configuration/output
fingerprints again before each tick. Editing/pulling changed code requires a
fresh reviewed definition; it cannot silently switch an installed job's version.
Runtime verification permits halted/finished state so it can report/recover
appropriately; it never resets the campaign.

**For an explicitly reviewed reinstallation after removing the existing task only:**

```powershell
.\deploy\windows\Install-ShadowObserver.ps1 -ReviewDirectory data/shadow/schedule/review_v3
```

This creates `TradingBot-ShadowObserver` for the current user. It does not
replace an existing task. Its PowerShell `-ExecutionPolicy Bypass` applies
only to that task process; it does not change the system execution policy.
An eligible/missed trigger may run soon after registration and may collect
read-only data. No paper order path is involved.

Inspect the registered job and its last outcome:

```powershell
Get-ScheduledTask -TaskName TradingBot-ShadowObserver
Get-ScheduledTaskInfo -TaskName TradingBot-ShadowObserver | Select-Object LastRunTime, LastTaskResult, NextRunTime
.\.venv\Scripts\python.exe -m app.shadow.scheduled status
```

For a manual task start after installation, `Start-ScheduledTask -TaskName
TradingBot-ShadowObserver` is possible; it may make requests if due. Avoid
manual starts merely to repeat a collection. Normal halted states need the
documented review/resume workflow; the task never resets them automatically.

### Remove or temporarily disable

```powershell
Disable-ScheduledTask -TaskName TradingBot-ShadowObserver
.\deploy\windows\Remove-ShadowObserver.ps1 -WhatIf
.\deploy\windows\Remove-ShadowObserver.ps1
```

Disabling prevents future triggers but does not stop an active run. Removal
checks the repository ownership marker and refuses an active task. Let it
finish first. `-StopRunning` explicitly stops it before removal if needed;
then review any uncertain pending request before a later resume. No database,
report, log, request counter or credential file is deleted. Moving the repo
requires removing the old registration before generating a fresh one.

## Future Pi installation and migration (not now)

1. Disable Windows collection and let any active tick finish. Preserve the
   Windows campaign archive. Do not run two copies of a campaign.
2. Pull the reviewed Git revision onto the Pi. Use a repository path without
   spaces, for example `/home/pi/trading-bot`, owned by a non-root user. Build
   its own environment and `.env`; do not copy Windows virtual environments.
3. Run the focused tests on the actual Pi, review one permitted one-shot
   collection there, then initialize a fresh Pi campaign from that Pi report.
   The existing guide describes this. Do not relabel/copy active Windows
   campaign state: paths and environment versions differ.
4. Render the units on the Pi from the checked-in templates. No Windows SID
   is needed for the Pi-only command:

```bash
./.venv/bin/python -m app.shadow.schedule prepare-pi
./.venv/bin/python -m app.shadow.schedule verify
```

`prepare-pi` uses that repository's actual path, current non-root user and
default runtime directories. The template's writable area is limited to
`data/shadow`; code and credentials are read-only to the service. It runs one
tick per invocation, after network startup, with a five-minute timeout and
whole-process-group termination. A 30-minute wall-clock timer plus a
two-minute boot trigger invokes it; a missed timer runs once when eligible.
Pi unit semantics and operation remain unverified until checked there.

After host checks and explicit migration approval, review and run on the Pi:

```bash
sudo systemd-analyze verify data/shadow/schedule/review/shadow-observer.service data/shadow/schedule/review/shadow-observer.timer
sudo install -m 0644 data/shadow/schedule/review/shadow-observer.service /etc/systemd/system/shadow-observer.service
sudo install -m 0644 data/shadow/schedule/review/shadow-observer.timer /etc/systemd/system/shadow-observer.timer
sudo systemctl daemon-reload
sudo systemctl enable --now shadow-observer.timer
systemctl list-timers shadow-observer.timer
journalctl -u shadow-observer.service -n 50 --no-pager
```

Pi removal, preserving runtime state:

```bash
sudo systemctl disable --now shadow-observer.timer
systemctl is-active shadow-observer.service
# Let an active service finish before the following removal commands.
sudo rm -- /etc/systemd/system/shadow-observer.timer /etc/systemd/system/shadow-observer.service
sudo systemctl daemon-reload
```

Stopping the timer alone does not interrupt a running service. If explicitly
stopping the service is necessary, review its pending attempt afterward.
The Pi timer does not renew campaigns: after expiry it can keep reporting a
finished campaign without requests until disabled or deliberately reconfigured.

Later migration of **actual paper trading** additionally requires matching
broker positions, orders, fills, protection and recovery. It cannot use the
flat shadow-reference migration steps as a trading-state transfer.

## Verification and next work

Preparation checks include Python compilation, PowerShell parsing, local
Task Scheduler XML parsing, review-fingerprint preflight and installer
`-WhatIf`. The first XML draft's encoding declaration was rejected by COM;
the corrected draft omits that declaration and is accepted. Those checks did
not register a task. Approved installation followed afterward; the earlier
draft remains in the local preparation archive.

**Current result: 272 tests pass**, including 65 new wrapper/generator/
deployment cases. See the [verification report](shadow_schedule_validation_results_2026-10-31.md)
for issues found and fixed. Native scheduler mutations in unit tests are
mocked. Actual Windows registration and a requested Task Scheduler launch
are now checked; natural triggers, due collection and Pi operation remain
to be observed. A real healthy heartbeat was saved without changing campaign
state or making requests.

**Next:** review the first automatic trigger/new-session report, then continue
paper fill-accounting and protective-exit engineering in a separate checkout,
keeping this deployed revision stable. No further installation approval or
personal risk-file change is needed for the approved observation campaign.
Paper orders retain their separate approvals/gates.

# Scheduling verification and Windows installation review

Completed October 31, 2026. **272 offline tests passed; no Windows task was
installed or started.** Historical research Steps 1-4 remain complete.

## Results

| Scope | Passed |
| --- | ---: |
| New schedule, heartbeat and Windows deployment tests | 65 |
| Existing repeat-controller tests | 70 |
| Existing observer tests | 66 |
| Related market-data/features/strategy/holding/daily-research tests | 71 |
| **Total** | **272** |

Final result: **zero failures, errors or skips**, about 44 seconds on Windows.
Network and real credential loading were forbidden. Test campaigns and reports
were temporary synthetic files. No dependency installation was required.

The new tests exercise XML settings/paths, manifest checksums and consistency,
campaign readiness, heartbeat corruption/timestamps, stale/failed runs,
atomic reporting, runtime version checks, locking and exception sanitization.
Seventeen Windows boundary/launcher cases exercise:

- Refusing an existing task, wrong owner, altered review or halted campaign.
- `-WhatIf`, correct handling of relative paths, and repository ownership.
- Refusing to remove running/foreign tasks; explicit stop and removal paths.
- Missing Python, correct launcher arguments with spaces, exit codes 0/2/3,
  preserved logs and the fixed fallback failure message.

**All scheduler mutations in unit tests are mocked.** Native scheduler
mutators also receive a protective `-WhatIf` default in the harness. Local
COM parsing validates XML without registration. The launcher cases execute
an inert temporary Python module; they do not run the market-data collector.
This is verification of the boundaries, not a claim that real registration,
triggering or Pi operation has happened.

## Issues found and fixed

The initial 61-case run recorded eight failed assertions/subtests and one
error. It is retained separately, including the exact executed sources.

- Manifest source/output sets now reject duplicates. Verification compares
  the complete Windows XML against the manifest/code, including runtime
  paths and campaign expiry, while retaining its original local start date.
- Malformed heartbeat objects, phases and exit codes now produce a structured
  error. Finish-before-start timestamps cannot report healthy operation.
- The installer resolves the review directory before changing directories,
  so relative input works from outside the repository.

Four additional Windows launcher cases were added before the final run.
The underlying repeat controller, signal rules, risk configuration, existing
campaign counters and original observation journal were not changed.

[Verification, source pins and logs](shadow_schedule_verification_2026-10-31.json)

## Fresh definition and preflight

The tested code generated a **new** review under
`data/shadow/schedule/review_v2/`. The earlier `review/` stays historical and
must not be installed with the changed sources. Current source/output hashes,
campaign readiness and Task Scheduler XML validation passed. The installer
and remover were invoked only with `-WhatIf` against the actual local host;
the task is absent. No wrapper tick or recurring process was started.

**Zero new requests, orders or purchases occurred.** The first real scheduled
heartbeat will appear only after an explicitly approved activation invokes
the wrapper. Real trigger behavior and actual Pi execution remain unverified.

## Approval and next work

The exact task, schedule, limits and activation command are in
[the Windows installation review](windows_shadow_installation_for_review_2026-10-31.md).
The next owner decision is **whether to install that persistent read-only
Windows task**. Windows host choice is already resolved. Personal risk-limit
approval and paper-trial activation remain separate, later steps.

After installation is approved, engineering will register this reviewed task,
inspect its first invocation and verify local heartbeat/status reporting
within the existing request limits. No paper orders will be enabled by it.

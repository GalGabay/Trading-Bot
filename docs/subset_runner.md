# Step 3: finite execution of the approved comparison

October 30, 2026. This implements the separately approved 76-stock versus
two-stock exploratory comparison. The research strategy, allocation, dates,
costs and three accounting scenarios are unchanged.

## Actual execution status

**Step 3 stopped incomplete:** four attempts, three accepted cases, one timeout.
See [partial results and the deadline limitation](subset_partial_results_2026-10-30.md).
The original deadline used monotonic time; recorded wall timestamps show a long
pause or clock discontinuity in the failed case. Post-stop code checks both
clocks in parent and worker, so expiry is detected when execution resumes.
No further strategy attempt has run. The original output cannot be restarted.

Post-stop accounting/cache fixes and deadline changes pass **184 focused tests**,
including **37 runner tests and 12 report tests**; all three saved financial and
external-price reports match exactly. [Current engineering proof](subset_recovery_verification_2026-10-30.json)
archives original executed sources. Older proofs below apply to those archived
sources; current-path hashes intentionally differ after the fixes. A new
[recovery segment](subset_recovery_for_review.md) is proposed, not approved or
implemented. The original production command must not be used for recovery.

## Runtime and persistence

`backtesting/subset_runner.py` runs one compute subprocess at a time on Windows
or Linux. It does not import a broker client or load account configuration.
Workers block network connections while preparing data and computing cases.

The single production output directory is
`data/reports/approved_subset_comparison_v1/`.
The persistent budget is `budget/ledger.json` inside it. The runner refuses a
second invocation when this directory already exists. It has no automatic
retry, resume, replacement-output or budget-reset option. Do not remove state
to reopen the approval.

- At most **24 strategy attempts**, including failed or interrupted attempts.
- One immutable, fsynced reservation file is saved before each worker launch.
- An exclusive worker claim prevents duplicate execution of one reservation.
- **600 seconds per case**, including loading, simulation, reconciliation and
  saving. The parent kills/reaps a timed-out worker; the worker also has its
  own deadline if the supervising process crashes.
- **7,200 seconds overall**, including the initial profile. Each case receives
  the smaller of its case allowance and the remaining overall allowance.
- A failure, timeout, changed source pin, accounting discrepancy or interruption
  stops the batch. Completed cases and consumed reservations remain recorded.
- JSON updates use a flushed/fsynced temporary file and atomic replacement.
  Leftover state is not silently repaired or reinitialized.

The exact order and limits were
[registered before execution](subset_comparison_execution_protocol_2026-10-30.json).
Each date-window/cost/accounting combination runs the two-stock control and then
its 76-stock challenger. There is no profit-driven reselection or parameter search.

## Gates before performance

The runner checks the separately recorded owner approval, unchanged acceptance
criteria, current Step 2 implementation/control verification and the new runner
verification. Input/source checksums are checked in the worker and before/after
each accepted case.

An initial profile loads the saved inputs, compiles the larger 2017-2021 window,
builds the actual causal feature views, and repeats the fixed saved-data
accounting checks. It makes **zero strategy calls**. This profile passed in
**26.7 seconds** on the Windows development computer. It is a preparation profile,
not a prediction that every complete simulation will finish within its timeout.
The observed wall/monotonic discrepancy and subsequent fixes are documented above.

## Verification

- [Pre-execution runner verification](subset_runner_verification_v2_2026-10-30.json):
  **35 tests passed; zero failures, errors or skips.** Covers reservations,
  consumed failures, concurrency, expired budgets, mismatched results, case
  order, worker termination, independent watchdogs, source pins, marked returns
  and evaluation-boundary calculations.
- [Result-report verification](subset_results_verification_2026-10-30.json):
  **12 tests passed; zero failures, errors or skips.** Covers per-root realized
  and unrealized profit, cash payments, pending claims, duplicate-credit
  detection and honest stopped/incomplete reports.
- The earlier runner proof is preserved as historical evidence. Source/path
  identity normalization and exclusive worker claims were hardened before the
  current proof and before any performance attempt.
- The preceding 236-test Step 2 proof remains unchanged; it is not added to the
  new 47-test total. Raspberry Pi execution/timing remains unverified.

## Saved outputs and interpretation

Each accepted case has its own `result.json`, compressed `case.json.gz`, phase
progress, worker claim and stdout/stderr logs. The full case retains fills,
financial marks, pending rights, signal decisions, holding reviews, risk bounds
and external-price reconciliation. The budget ledger references accepted
results by checksum.

`backtesting/subset_results.py` reads completed or stopped saved batches without
running strategies or reading new price data. It produces all-case CSV rows,
per-root profit contributions, and a summary with explicitly selected
pessimistic-cost/base-availability comparisons. Root contributions must sum to
the marked account profit before estimated final exits. Stopped batches remain
incomplete; they are never described as 24 successful runs.

Net marked returns include the nominal value of unpaid rights and estimated
exit costs for whole shares. They are not settled cash gains. The 2017-2021 and
2022-2023 windows start separate simulated accounts; they are not a continuous
seven-year compounded account. Mean share exposure is reported separately from
unpaid cash rights, which reserve exposure but cannot fund purchases. Daily
OHLC risk envelopes are conservative bounds, not observed intraday equity.

The price-availability-selected subset can bias returns. This experiment alone
does not establish paper readiness. No purchase, paid data, account request,
live/paper order, reserved 2024-2025 candle access or strategy change is authorized
by the runner. All account values and trading costs here are simulated.

## Commands

The production command is deliberately one-shot:

```powershell
.\.venv\Scripts\python.exe -m backtesting.subset_runner
```

After the batch completes or stops, summarize it to a fresh report directory:

```powershell
.\.venv\Scripts\python.exe -m backtesting.subset_results `
  --output data/reports/approved_subset_results_v1
```

The current execution status and final research-step status belong in the
[four-step tracker](broad_backtest_step_tracker.md) and the generated result
record. **Your part now: decide on the separate recovery proposal; no configuration or purchase is needed.**
Step 4 follows with the interpretation and decision, rather than automatic
paper activation.

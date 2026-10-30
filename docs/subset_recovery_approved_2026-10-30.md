# Approved recovery: execution and verification

The owner's instruction to proceed in response to the bounded recovery request
is [recorded separately](subset_recovery_owner_approval_2026-10-30.json).
The earlier [review document](subset_recovery_for_review.md) and machine-readable
proposal remain unchanged as historical evidence of what was approved.

## Exact scope

- Preserve the original stopped ledger: four attempts, three completed cases.
- Retain the three completed results without rerunning their strategies.
- Retry the failed case once, then run the 20 unattempted cases in their original
  order: at most 21 additional attempts, **25 lifetime attempts**.
- Use one worker, at most 600 seconds per case and a separate 3,600-second
  recovery segment, including the initial zero-strategy profile.
- Stop at any failure, timeout, source change or reconciliation discrepancy.
  There is no automatic retry, resume, replacement directory or budget reset.
- Keep strategy, costs, dates, accounting assumptions and acceptance criteria
  unchanged, including 70% total entry exposure, 5% per stock and 20 positions.
- No purchases, account/broker requests, orders, credential access or reserved
  2024-2025 candle access. All monetary figures are simulated.

## Implementation

`backtesting/subset_recovery.py` uses the existing worker and persistent Budget
implementation. The original CLI remains confined to its original directory
and approval; the new CLI has a separate fixed directory and approval gate.

The recovery ledger records the original four-attempt offset, original ledger
checksum and 25-attempt lifetime cap. Every new attempt has an immutable
reservation before its worker can start, and every worker claims its reservation
exclusively. Parent and worker enforce both wall and monotonic time. A suspended
computer cannot execute a handler until it resumes; expired work is rejected.

The authority gate verifies the exact approved exception, original stopped
results, historical Step 2 source snapshots and current verification/source
checksums. The original proofs are not rewritten to describe the new code.

Combined reporting verifies both ledgers and accepted result files. It reports
all 25 consumed attempts if all remaining cases complete, and precisely 24
distinct successful cases. Duplicated, missing or reordered cases cannot be
presented as a completed comparison. The original reporter still rejects more
than 24 attempts unless the separately approved recovery evidence is validated.

## Verification before execution

**320 offline tests passed, zero failures, errors or skips**, including 30 new
recovery tests. Tests cover missing approval, changed limits, forbidden retries,
ordering, lineage offsets, failed profiles, preserved failed attempts,
duplicate cases, honest partial reports and prevention of directory resets.
All three saved financial and external-risk reports reproduce exactly, and
six synthetic financial control comparisons pass. These verification replays
make zero new research strategy attempts.

- [Current driver verification and source checksums](subset_recovery_driver_verification_2026-10-30.json)
- [Case order and limits registered before execution](subset_recovery_execution_protocol_2026-10-30.json)
- [Return, cash and drawdown explained](subset_return_metrics_explained.md)

The fixed recovery output is `data/reports/approved_subset_recovery_v1/`.
Its budget is `budget/ledger.json`; its terminal state is `summary.json`.
The combined report output is `data/reports/approved_subset_combined_results_v1/`.
These local large files/logs are ignored by Git and should be retained with the
research archive. Compact tracked summaries will describe the actual outcome.

The one-shot command is `python -m backtesting.subset_recovery`; once its output
exists it refuses to start again. After terminal completion or stop, the
separate `--report` command creates the combined report in its fixed fresh
directory without another strategy call. Do not remove state to rerun it.

Raspberry Pi execution/timing remains unverified. Selection by historical data
availability limits this research; completing the comparison does not establish
paper readiness or authorize paper activation. Consult the
[four-step tracker](broad_backtest_step_tracker.md) for current execution status.

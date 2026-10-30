# Proposed recovery of the stopped comparison

**Status: proposed, not approved. Still Step 3 of 4.**

The first batch completed three cases and stopped on a timeout in attempt four.
Its original two-hour window has elapsed. Finishing all 24 distinct planned
cases now requires 21 more attempts: retry the failed case once, then run the
20 unattempted cases in their original order. That makes **25 lifetime attempts**,
counting the failed attempt. The failed attempt is not erased.

## Concrete proposal

- Keep the three completed cases and their unchanged results.
- Permit **up to 21 additional attempts, 25 total across both batches**.
- Give the recovery segment **60 minutes overall**, with **ten minutes per
  case and one worker**. Loading, simulation, reconciliation and saving all
  count against those limits.
- Preserve the original stopped ledger. A separate ledger must record the
  four-attempt offset, fixed remaining case order and original evidence hashes.
- Stop on the next failure, timeout, changed input or accounting discrepancy.
  No automatic retry, resume or budget reset is permitted.
- Keep all strategy, data, date, cost and risk settings unchanged: 70% total
  entry exposure, 5% per stock, 20 positions, and the existing halt rules.
- Keep the 2024–2025 reserve untouched. Make no purchase or broker request and
  place no paper/live order. This is local simulated research only.

The slow accounting path and deadline handling have been fixed. The
[verification record](subset_recovery_verification_2026-10-30.json) reports 184
passing tests and exact financial replay of all three saved cases, without new
strategy attempts. Timings do not guarantee all remaining cases will finish.

## Why your decision is needed

Your previous approval explicitly capped attempts at 24 and required stopping
on a failure. It does not authorize a retry plus a 25th lifetime attempt or a
new execution window. This decision changes only that execution allowance;
it does not change your investment goals or authorize paper trading.

You can approve this bounded recovery or keep the stopped partial results.
No JSON, Python, risk file, installation or account setting needs editing by you.
There is no recovery command to run yet: after approval, engineering must
implement and verify a separate driver that checks the new authority, preserves
the original evidence and combines both segments without duplicate cases.

[Machine-readable scope and exact remaining order](subset_recovery_proposal_2026-10-30.json)

**Next — engineering:** implement/verify that driver, then execute only if this
proposal is explicitly approved. Step 4 follows with the completed results and
decision, or an explicitly agreed closure of the incomplete comparison.

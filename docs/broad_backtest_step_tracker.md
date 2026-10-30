# Broader backtest: four-step progress tracker

Updated October 30, 2026. These four steps describe the current broader-stock
research work, not development phases 1-4. After each implementation response,
report the current step and its remaining work until Step 4 is complete.

| Step | Work and completion condition | Current status | Responsibility |
| --- | --- | --- | --- |
| 1 | Prepare and qualify the fixed 100-stock history, including ownership-changing events and dividends. Every unresolved economic term must have a supported treatment. | **In progress.** 641 offline tests pass, including 70 new holder/preparation/formula tests. MAC's reported no-election conversion is recorded; ownership/settlement and other terms still leave 188 overlapping blocking rows. | Engineering; no new owner setting is required now. |
| 2 | Connect the qualified history and pending-rights ledger to the portfolio simulator. Verify once-only transfers, ownership after sales, feature resets, stale-order invalidation, valuation and risk integration. | Pending Step 1 admission. The full bridge is not implemented. | Engineering. |
| 3 | Run the finite, reviewed experiment on the fixed universe and periods. Report return, drawdown, costs, exposure, cash use and sensitivity. | Pending verified integration and review of a concrete performance-run plan. No new batch is authorized by the accounting approvals. | Engineering prepares and runs; owner reviews the concrete final scope when ready. |
| 4 | Explain the results, compare them with the approved return/drawdown goals, and record the decision and remaining paper-readiness work. | Pending Step 3 results. | Engineering analysis plus owner decision. |

Step 4 completion means this research comparison and its decision are documented.
It does not automatically activate paper trading. Personal paper-risk limits,
historical-results review, account-state/recovery checks, safe exit protection,
fill accounting and explicit paper-trial activation remain applicable.

## Latest evidence

- [Ownership tests and completed MAC formula review](broad_holder_tests_results_2026-10-30.md)
- [641-test verification](broad_holder_tests_verification_2026-10-30.json)
- [Current preparation replay](broad_holder_tests_replay_2026-10-30.json)
- [Current individual gates](broad_holder_tests_preflight_2026-10-30.json)
- [Current remaining-work inventory](broad_holder_tests_remaining_work_2026-10-30.json)

Earlier holder preparation, preserved as historical evidence:

- [Latest holder schedules and remaining shared gaps](broad_holder_terms_results_2026-10-30.md)
- [Latest preparation replay](broad_holder_terms_replay_2026-10-30.json)
- [Latest individual remaining gates](broad_holder_terms_preflight_2026-10-30.json)
- [Grouped work inventory](broad_holder_terms_remaining_work_2026-10-30.json)

Earlier verification, retained as historical evidence:

- [Focused tests, fixes and remaining terms](broad_action_election_results_2026-10-30.md)
- [Test summary: 571 passed, zero failed/errors/skipped](broad_action_election_verification_2026-10-30.json)
- [Saved-event replay](broad_action_election_saved_replay_2026-10-30.json)
- [Individual remaining gates](broad_action_election_preflight_2026-10-30.json)

The approved research allocation is unchanged: 70% total entry exposure,
5% per-stock entry cap and 20 simultaneous positions. Historical holders follow
documented no-election defaults. No purchase or repeat approval is needed for
those choices.

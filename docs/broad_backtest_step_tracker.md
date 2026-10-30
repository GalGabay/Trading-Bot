# Broader backtest: four-step progress tracker

Updated October 30, 2026. These four steps describe the current broader-stock
research work, not development phases 1-4. After each implementation response,
report the current step and its remaining work until Step 4 is complete.

**Current route: the separately approved 76-stock exploratory comparison.**
Step 1 inputs are prepared; **Step 2 integration is verified; Step 3 is next**. The owner approved
the exact scope and a maximum of 24 simulations after its integration/control
checks pass. There is no pending owner setting or repeat approval now.
The original fixed-100 study remains separately blocked at Step 1; it retains
all 188 economic-data gate rows and all original evidence.

| Step | Work and completion condition | Current status | Responsibility |
| --- | --- | --- | --- |
| 1 | Prepare separately pinned inputs for the approved 76-root subset, retaining the other 24 roots in the original inventory. Check event admission, calendar coverage, candles and provenance under the approved diagnostic assumptions. | **Inputs prepared.** 79 streams and 149,113 daily candles pass preparation validation; zero subset event gates. Selection by historical data availability can bias returns. This is not full-100 or strict evidence certification. New preparation utilities have not had unit tests run; the prior 641-test result is preserved separately. | Engineering; owner's separate scope approval is recorded. |
| 2 | Connect the qualified history and pending-rights ledger to the portfolio simulator. Verify once-only transfers, ownership after sales, feature resets, stale-order invalidation, valuation and risk integration. | **Complete for the approved diagnostic subset.** 236 focused tests pass, including 42 new tests; 36 saved-data accounting checks and six synthetic financial control comparisons pass. All 12 basket/window/scenario schedules compile. | Engineering verification recorded; no research performance batch has run. |
| 3 | Run the finite, reviewed experiment on the fixed universe and periods. Report return, drawdown, costs, exposure, cash use and sensitivity. | **Next, conditionally authorized.** Implement/verify the persistent attempt ledger and runtime enforcement, then profile the runner. At most 24 attempts: 2 arms x 2 windows x 2 cost cases x 3 accounting scenarios, one simulated $10,000 account size. Stop on failed checks or timeout. | Engineering; no repeat approval required within these limits. |
| 4 | Explain the results, compare them with the approved return/drawdown goals, and record the decision and remaining paper-readiness work. | Pending Step 3 results. | Engineering analysis plus owner decision. |

Step 4 completion means this research comparison and its decision are documented.
It does not automatically activate paper trading. Personal paper-risk limits,
historical-results review, account-state/recovery checks, safe exit protection,
fill accounting and explicit paper-trial activation remain applicable.

## Latest evidence

- [Step 2 simulator integration and verification](subset_simulator_integration.md)
- [Combined Step 2 verification record](subset_integration_verification_2026-10-30.json)
- [236-test run and source pins](subset_integration_tests_2026-10-30.json)

Earlier input preparation and approval:

- [Prepared subset inputs and remaining Step 2 work](approved_subset_preparation_results.md)
- [Owner approval of the separate scope and conditional 24-attempt cap](faster_research_owner_approval_2026-10-30.json)
- [Tracked preparation summary](approved_subset_preparation_summary.json)
- [Exploratory scope and exact limits as presented](faster_research_scope_for_review.md)
- [All 100 originals and the explicit subset/deferred inventory](research_data/faster_research_scope_inventory.csv)
- [Bounded MAC/SLG search closure](broad_targeted_schedule_results_2026-10-30.json)

Previous full-100 evidence, unchanged:

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

# Broader backtest: four-step progress tracker

Updated October 30, 2026. These four steps describe the current broader-stock
research work, not development phases 1-4. After each implementation response,
report the current step and its remaining work until Step 4 is complete.

**Current route: the separately approved 76-stock exploratory comparison.**
Step 1 inputs are prepared; Step 2 integration was verified; **Step 3 stopped
incomplete after four attempts (three completed, one timeout)**. No retry ran.
[Partial results and fixes](subset_partial_results_2026-10-30.md) are documented.
A [separate recovery proposal](subset_recovery_for_review.md) requires a decision
because it permits one retry, 25 lifetime attempts and a new bounded window.
The original fixed-100 study remains separately blocked at Step 1; it retains
all 188 economic-data gate rows and all original evidence.

| Step | Work and completion condition | Current status | Responsibility |
| --- | --- | --- | --- |
| 1 | Prepare separately pinned inputs for the approved 76-root subset, retaining the other 24 roots in the original inventory. Check event admission, calendar coverage, candles and provenance under the approved diagnostic assumptions. | **Inputs prepared.** 79 streams and 149,113 daily candles pass preparation validation; zero subset event gates. Selection by historical data availability can bias returns. This is not full-100 or strict evidence certification. New preparation utilities have not had unit tests run; the prior 641-test result is preserved separately. | Engineering; owner's separate scope approval is recorded. |
| 2 | Connect the qualified history and pending-rights ledger to the portfolio simulator. Verify once-only transfers, ownership after sales, feature resets, stale-order invalidation, valuation and risk integration. | **Complete for the approved diagnostic subset.** 236 focused tests pass, including 42 new tests; 36 saved-data accounting checks and six synthetic financial control comparisons pass. All 12 basket/window/scenario schedules compile. | Historical integration verification recorded; current post-stop fixes pass 184 focused tests and all three saved-case financial replays. |
| 3 | Run the finite, reviewed experiment on the fixed universe and periods. Report return, drawdown, costs, exposure, cash use and sensitivity. | **Stopped, incomplete.** Four attempts consumed; three completed, fourth timed out. Zero-strategy profile passed in 26.7 seconds. No pessimistic-cost or 2022?2023 case completed. Post-stop accounting/deadline fixes pass 184 offline tests; three saved-case reports match exactly. No new strategy run after stopping. | Engineering fixes verified; owner decision needed for the separate 21-attempt recovery segment (25 lifetime attempts), followed by recovery-driver implementation/verification. |
| 4 | Explain the results, compare them with the approved return/drawdown goals, and record the decision and remaining paper-readiness work. | Pending completion or explicitly agreed closure of Step 3; partial interpretation is documented. | Engineering analysis plus owner decision. |

Step 4 completion means this research comparison and its decision are documented.
It does not automatically activate paper trading. Personal paper-risk limits,
historical-results review, account-state/recovery checks, safe exit protection,
fill accounting and explicit paper-trial activation remain applicable.

## Latest evidence

- [Partial returns and exact stop status](subset_partial_results_2026-10-30.md)
- [184-test post-stop verification and unchanged saved reports](subset_recovery_verification_2026-10-30.json)
- [Separate recovery proposal, not approved](subset_recovery_for_review.md)

Historical pre-execution evidence:

- [Step 3 runner, deadlines and report interpretation](subset_runner.md)
- [Registered case order and execution limits](subset_comparison_execution_protocol_2026-10-30.json)
- [35 passing current runner tests](subset_runner_verification_v2_2026-10-30.json)
- [12 passing report tests](subset_results_verification_2026-10-30.json)

Earlier Step 2 evidence:

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

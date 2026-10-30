# Broader backtest: four-step progress tracker

Updated October 30, 2026. These four steps describe the current broader-stock
research work, not development phases 1-4. After each implementation response,
report the current step and its remaining work until Step 4 is complete.

| Step | Work and completion condition | Current status | Responsibility |
| --- | --- | --- | --- |
| 1 | Prepare and qualify the fixed 100-stock history, including ownership-changing events and dividends. Every unresolved economic term must have a supported treatment. | **In progress.** 571 offline tests pass, including 87 new action/election/cash-merger tests. The latest preparation still has 191 overlapping blocking rows. | Engineering; no new owner setting is required now. |
| 2 | Connect the qualified history and pending-rights ledger to the portfolio simulator. Verify once-only transfers, ownership after sales, feature resets, stale-order invalidation, valuation and risk integration. | Pending Step 1 admission. The full bridge is not implemented. | Engineering. |
| 3 | Run the finite, reviewed experiment on the fixed universe and periods. Report return, drawdown, costs, exposure, cash use and sensitivity. | Pending verified integration and review of a concrete performance-run plan. No new batch is authorized by the accounting approvals. | Engineering prepares and runs; owner reviews the concrete final scope when ready. |
| 4 | Explain the results, compare them with the approved return/drawdown goals, and record the decision and remaining paper-readiness work. | Pending Step 3 results. | Engineering analysis plus owner decision. |

Step 4 completion means this research comparison and its decision are documented.
It does not automatically activate paper trading. Personal paper-risk limits,
historical-results review, account-state/recovery checks, safe exit protection,
fill accounting and explicit paper-trial activation remain applicable.

## Latest evidence

- [Focused tests, fixes and remaining terms](broad_action_election_results_2026-10-30.md)
- [Test summary: 571 passed, zero failed/errors/skipped](broad_action_election_verification_2026-10-30.json)
- [Saved-event replay](broad_action_election_saved_replay_2026-10-30.json)
- [Individual remaining gates](broad_action_election_preflight_2026-10-30.json)

The approved research allocation is unchanged: 70% total entry exposure,
5% per-stock entry cap and 20 simultaneous positions. Historical holders follow
documented no-election defaults. No purchase or repeat approval is needed for
those choices.

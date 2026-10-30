# Step 1: corporate-action/election verification and remaining terms

October 30, 2026. **Step 1 remains in progress. Step 2 is not admitted.**
See the [four-step tracker](broad_backtest_step_tracker.md) for the path to
the broader backtest results and the subsequent paper-readiness decision.

## Tests completed

**571 tests passed; zero failures, errors or skips in the final run.** This
includes 87 new focused tests: 29 corporate-action, 42 election-schedule and
16 cash-merger tests, plus 484 related regression tests. Network connections
and real research-credential loading were blocked during the test run.

The first 63-test run exposed 11 failing assertions and one error (some failures
were subtests). Additional cases then exposed date/evidence checks and covered
the newly supported declaration. The final run includes all fixes. Earlier
code was snapshotted before editing; current executed code/tests were copied
with the verification log.

### Fixes driven by the tests

- Alias admission now requires preservation of features and holding age, plus
  invalidation of symbol-bound execution state.
- Split admission requires pending-share-right rebasing; malformed ratios stay
  blocked. Cost-basis, stop, fractional-claim and order safeguards remain.
- Election compilation rejects duplicate schedules/provider identities,
  mismatched record IDs, nonpositive split multipliers and invalid dates.
- All nested saved evidence pins in election inputs are verified. SLG defaults
  require directly reviewed declarations matching the correct record/payment
  dates; a previous year's default cannot fill another year's gap.
- A conditional election schedule remains blocked if someone removes its text
  blockers. Duplicate preflight schedules are rejected. There is no admitted
  election-ledger instruction adapter yet.

The approval tests cover altered approval/proposal files, unsupported choices,
incorrect scope, omitted/relaxed restrictions and nonzero or incorrectly typed
purchase budgets. An approved choice never grants trading or performance-run
authority.

## Saved-event replay

The normal preparation and preflight completed offline for base, five-session
delay and no-credit scenarios:

- All 100 original members and 2,698 provider dividend records remain.
- Fifteen action instructions compile: six aliases, five forward splits and
  four preinvestment reference actions.
- Five election schedules retain the approved no-election holder rule.
- Four cash mergers produce 12 scenario-specific conditional receivable plans.
  No invented payment date or spendable cash is supplied in any scenario.
- Nielsen still uses the October 12, 2022 first nontradeable session and the
  preceding October 11 ownership close, rather than an October 11 opening exit.
- Dividend plans are unchanged from the preceding preparation. No provider
  record was deleted or fabricated to make a gate pass.
- The readiness assertion rejects Step 2 handoff as expected.

These are instruction/data replays, not a strategy performance experiment.

## Remaining-term source work

A separate capped free review used three search queries and two page opens.
The [SL Green December 2, 2021 filing](https://www.sec.gov/Archives/edgar/data/1040971/000110465921145907/tm2134440d1_8k.htm)
establishes that January 2022 non-electing holders were assigned the stock
election, subject to proration. The compiler now selects that documented branch.
This resolves the missing default, **not** exact holder allocation: the saved
final allocations remain approximate, and fractional/ownership terms remain
unadmitted.

The next issuer-hosted Macerich document failed to fetch. Collection stopped
immediately; no alternate path, retry, paid source or new collection batch was
started. Its search excerpt remains discovery only. MAC conversion and AIV 2019
entitlement details were not resolved in this capped attempt. Earlier barriers
and closed protocols remain preserved.

- [Scope](broad_election_completion_scope_2026-10-30.json)
- [Closed collection facts and failure record](broad_election_completion_facts_2026-10-30.json)
- [Versioned election inputs](broad_election_schedule_inputs_v3_2026-10-30.json)

## What remains before Step 2

| Blocking rows | Count | Main work |
| --- | ---: | --- |
| Material events | 18 | Stock/mixed mergers, spin-off/restructuring ownership schedules, remaining CSRA holder terms |
| Dividends | 143 | Election lineage, unresolved ordinary components/date conflicts and foreign/special distributions |
| Provider identity/events | 25 | Unsupported split/identity/ownership routes; retain their original rows |
| Election schedules | 5 | Exact permitted allocations, ex-date/due-bill ownership and fraction handling |
| **Total** | **191** | Overlapping rows, not 191 companies or independent research decisions |

The count is unchanged because confirming one branch does not complete the
other required terms in that schedule. Eighty-four dividend rows still share
unresolved election-lineage dependencies. They are not 84 independent data
collection projects.

Next engineering work is to resolve and encode the remaining holder/ownership
schedules and dated dividend/provider decisions, starting with shared election
dependencies. Any further public-source review needs a new finite scope and
must preserve the failed-URL records; it will not resume this closed attempt.
Do not present Step 1 as complete or start a new performance batch while those
economic gates remain open. No additional owner setting is needed now.

## Verification evidence and limits

- [Test report and execution pins](broad_action_election_verification_2026-10-30.json)
- [Saved-event replay assertions](broad_action_election_saved_replay_2026-10-30.json)
- [Current preparation](broad_action_election_preparation_2026-10-30.json)
- [Current preflight / individual gates](broad_action_election_preflight_2026-10-30.json)

Tests ran on Windows with the existing virtual environment. Raspberry Pi
execution remains unverified. The saved-data replay requires the pinned local
cache; unit tests use synthetic temporary fixtures. No packages were installed,
no credentials read, no broker requests or orders placed, no paid data purchased,
no new price data downloaded, and no reserved 2024-2025 candle files read.
No new historical return or profit/loss result was calculated.

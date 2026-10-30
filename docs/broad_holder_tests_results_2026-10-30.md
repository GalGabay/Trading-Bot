# Step 1: ownership tests and completed Macerich formula review

October 30, 2026. **Still Step 1 of 4.** The requested focused tests and a bounded
primary-source review are complete. Remaining economic terms still block Step 2;
there are **188 overlapping blocking rows**. See the
[four-step tracker](broad_backtest_step_tracker.md).

## Test results

**641 tests passed, with zero failures, errors or skips.** The 70 new tests
comprise 52 ownership/source/timing/routing tests, ten synthetic preparation and
preflight checks, and eight Macerich formula tests. The other 571 tests are the
related regression suite. Network connections and real research-credential
loading were blocked throughout the test run.

The initial 50-test ownership run had 15 failing tests. Those failures exposed
checks missing from the previous implementation. Two subsequent cases exposed
missing-base and cross-scenario consistency gaps; both were fixed before the
final suite. No failure is concealed by skipping a test or weakening an expected
result.

### Corrections driven by the tests

- Reject duplicate material/stream identities and wrong provider roots.
- Require valid record/session dates and an economic timestamp on the correct
  New York event date. An unrelated year cannot pass as the distribution time.
- Bind an election boundary to its event identity, instrument and record date.
- Verify modeled releases against the exact saved-calendar schedule for each
  supported scenario. A premarket timestamp or removed five-session delay cannot
  pass as scheduled availability.
- When a saved window ends before delayed delivery, keep the right pending;
  do not invent a later date or discard the right.
- Require all three consistent due-bill scenario plans, including base. Reject
  duplicate scenarios and inconsistent entitlement ratios.
- Match a represented provider row by provider event ID as well as parent and
  canonical event. An unrelated row cannot borrow another event's admission.

Synthetic preparation checks cover optional-review absence, missing election
schedules, owner approval, input preservation, fresh output paths and changed
review/evidence/execution/output checksums. A clean synthetic data gate still
leaves engine integration, paper trading and performance authorization false.

## Remaining-term work: Macerich's completed distribution

The [issuer's 2020 annual report](https://www.sec.gov/Archives/edgar/data/912242/000091224221000004/mac-20201231.htm)
was retrieved and directly reviewed. Note 14, printed page 98, documents the
completed June 3, 2020 distribution, the explicit no-election 20% cash / 80%
stock treatment, and the reported stock conversion price of $7.2956. The
original announcement already supplies the $0.50 declared value and record date.

The compiler now records the conditional reported formula for the approved
no-election holder:

| Per eligible record share | Conditional reported amount |
| --- | --- |
| Fixed cash component | $0.50 x 20% = $0.10 |
| Stock-value component | $0.50 x 80% = $0.40 |
| Share right before fractional settlement | $0.40 / $7.2956 = 1000/18239 of a share |

This is exact arithmetic on the issuer's reported per-holder formula. No
individual allocation is inferred from aggregate shares issued, and no rounded
share rate is promoted to exact precision. The formula remains conditional on
eligible holdings and schedule admission. It does not certify an actual broker
allocation, fix fractional cash, release buying power or enable execution.

The new formula tests reject search-only evidence, wrong issuer/class, incomplete
distribution status, approximate allocation labels, conflicting payment dates,
percentages or declared values, and invalid conversion prices. Without the
separate owner election approval the formula remains unselected. Its presence
does not remove the election preflight gate or alter original provider records.

## Free-source review and access stop

The separately scoped review used nine search queries, three page opens/clicks
and two find operations on opened documents. Two opens succeeded: the SEC
annual report and the issuer's dividend-information locator. The locator's
historical table explicitly identifies Mergent as its third-party provider; it
is not used as primary ex-date or holder-allocation evidence.

The linked 2020 dividend tax form returned 403. All new requests stopped at that
failure. No failed URL was retried, no access barrier was bypassed and no paid
fallback was used. SLG exact quantities and AIV ownership gaps remain unresolved;
search discoveries are not treated as directly reviewed proof.

- [Finite review scope](broad_election_formula_scope_2026-10-30.json)
- [Primary facts, locator distinction and closed failure record](broad_election_formula_facts_2026-10-30.json)

## Saved-data preparation

All three accounting scenarios prepared offline with the current code and
versioned source inputs. Replay assertions confirm:

- All 100 selected members and 2,698 dividend identities remain.
- Dividend plans are unchanged from the preceding preparation.
- All three K/KLG plans pass the strengthened scenario/instruction contract.
- Macerich selects the reported formula while its schedule stays blocked.
- Preflight still rejects Step 2 handoff.

| Remaining overlapping gate rows | Count |
| --- | ---: |
| Material-event terms | 17 |
| Dividend terms | 143 |
| Provider identity/event terms | 23 |
| Election schedules | 5 |
| **Total** | **188** |

The row count stays unchanged because resolving Macerich's conversion formula
does not resolve its ownership and fractional-settlement schedule. Its 14 later
dividend rows still depend on that schedule. The other shared dependencies are
24 AIV/descendant rows and 46 SLG rows, for 84 total. Special/foreign payouts,
ambiguous components and source-date conflicts remain independent gates.

The [updated remaining-work inventory](broad_holder_tests_remaining_work_2026-10-30.json)
records Macerich's newly selected conditional allocation, while retaining every
remaining dividend group, material event and provider route. None was removed
to improve readiness or performance.

## Evidence and practical limits

- [641-test report, log and executed source pins](broad_holder_tests_verification_2026-10-30.json)
- [Current preparation](broad_holder_tests_preparation_2026-10-30.json)
- [Current preflight / individual gates](broad_holder_tests_preflight_2026-10-30.json)
- [Saved-data replay and executed sources](broad_holder_tests_replay_2026-10-30.json)

Tests ran in the existing Windows virtual environment. Raspberry Pi execution
is unverified. The replay requires pinned local cached artifacts; the new unit
tests use temporary synthetic inputs and do not need historical downloads.
No dependencies were installed, credentials read, broker requests made, orders
placed, purchases made, new price data downloaded or strategy performance batches
run. Reserved 2024-2025 candle files were not read. These results add no new
profit/loss percentage.

## Next work and the owner's part

Engineering, **still Step 1**: complete Macerich's primary ex-date/ownership and
fractional-claim schedule, then resolve the exact SLG holder terms and the
remaining AIV/dividend/material-event admissions in the work inventory. Any new
source review needs its own finite scope and must preserve the closed 403 record.
Step 2 remains conditional on those data checks; Steps 3 and 4 are pending.

Owner: no configuration, purchase or repeated approval of the research allocation
or no-election policy is required now. The frozen 70% total entry exposure,
5% per stock, 20 positions and existing accounting defaults remain unchanged.

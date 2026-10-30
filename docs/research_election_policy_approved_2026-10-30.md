# Approved historical research election policy

On October 30, 2026, the owner selected:

> Use documented no-election defaults (Recommended)

The simulator's research holder makes no election and follows each issuer's
documented default. The rule is applied consistently, without choosing a branch
after seeing performance. It does not change the approved research allocation,
personal paper-risk settings or any real account instruction.

## Implementation

- [Separate owner approval](research_election_owner_approval_2026-10-30.json)
  pins the exact [original proposal](research_election_policy_for_review.md).
  The proposal is preserved, including its earlier pending-status wording;
  this approval record establishes the current status.
- Election inputs v2 bind `no_election` to this approval. Editing a selection
  flag alone cannot select a holder policy. The compiler and preflight validate
  both the record and the proposal checksum.
- All five schedules record the selected holder action and their documented
  default branch. AIV's reported no-election allocations are selected as
  conditional terms, without certifying entitlement, receipt or execution.
- SLG 2021's approximate allocations remain blocked. SLG 2022's unestablished
  default remains unknown. MAC's missing final conversion terms remain blocked.
- Selecting a policy removes the missing-owner-choice reason only. Missing
  provider events, ex-date/due-bill ownership, fractional fixing, approximate
  allocations and other data gates remain effective. No share or cash release
  is authorized by this selection.

## Verification and status

Normal offline preparation and preflight completed for base, five-session delay
and no-credit scenarios. All 100 members and 2,698 provider dividend identities
remain in the preparation. The five conditional election schedules now record
`selected_holder_election: no_election`.

The readiness report still has 191 overlapping blocking rows: 18 material-event,
143 dividend, 25 provider identity/event and five election-schedule rows. The
holder policy is approved; those five schedules still lack other admission
terms. Step 1 and Step 2 integration remain incomplete.

- [Approved preparation summary](research_election_approved_preparation_2026-10-30.json)
- [Updated readiness report](research_election_approved_preflight_2026-10-30.json)

No unit tests were added or run for this approval increment. Earlier unit-test
results describe earlier code. No network requests, purchases, trades or new
historical performance runs occurred. Original inputs and preceding execution
snapshots were preserved; new preparation uses approved diagnostic policy v12
and a separate election approval, without rewriting the original owner record.

## What is next

Engineering: focused tests for the new action/election modules and approval
binding, followed by the remaining source and schedule terms before Step 2
integration. The research election choice is resolved; the owner has nothing
further to configure for this choice. Personal paper-risk decisions and paper
activation remain later tasks.

# Approved defaults, focused tests and event review

October 30, 2026. **Step 1 remains incomplete; full Step 2 integration is blocked
by economic/identity data gates.** A readiness gate was implemented and executed.
The main portfolio engine has not been connected to the new delayed-rights book.

## Your decisions are recorded

[The separate owner record](broad_diagnostic_owner_approval_2026-10-30.json)
approves the frozen [accounting assumptions](broad_diagnostic_assumptions_for_review.md)
and **70% total entry exposure, 5% per stock and 20 concurrent positions**, for
historical research. No repeated owner approval of those defaults is needed.
The original proposal/document remain unchanged and hash-pinned. An approved
policy version records assent separately from the original unapproved proposal.

This does not approve a source purchase, paper activation or a new finite
performance batch. Run allowance remains zero. Unknown source facts, elections
and exact settlement do not become verified because modeling defaults were accepted.

## Tests and defects fixed

**Final run: 421 tests passed, zero failures, errors or skips.** This includes
**66 new focused tests and 355 related regression tests**. Final code/test
snapshots and the log are retained under
`data/reports/diagnostic_verification_2026_10_30_v3`.

New focused tests cover:

- Saved-session timing, holidays, early closes, delayed availability, missing
  payment dates, reserved development boundaries and invalid input dates.
- Ordinary-dividend classification, exact decimal/rational amounts, due-bill
  ambiguities, special/foreign/currency flags and unverified source provenance.
- Pending cash/share rights, early/duplicate releases, exact fractions, missing
  or stale/future quotes, unknown cash values, atomic failures and journal copies.
- JCI predecessor isolation, PEAK one-for-one legal continuity, PHIN distribution
  versus quote timing, immutable original inputs and changed-source rejection.
- Owner approval binding, unchanged allocation/defaults, no inferred paper or
  performance authority, conditional election terms and blocked engine handoff.
- Multiple dividend records at one security/ex-date, without deleting records
  or treating their sum as an automatically valid distribution.

Fixed a no-credit input-validation bypass, an out-of-calendar material-event
planning error, and an admission gate that incorrectly treated an ineligible
predecessor reference as a possible portfolio claim. PEAK one-for-one terms can
be admitted in the approved diagnostic convention after exact primary-source
and identity checks; actual delivery and strict evidence flags remain unverified.

Final run counts, code/test hashes and the detailed log are in the
[verification summary](broad_diagnostic_verification_2026-10-30.json).
Related engine, ownership, risk, universe, source and accounting regression
tests were run with real socket and credential loading blocked. Synthetic unit
fixtures do not constitute a new historical strategy experiment. Initial
failing runs and intermediate successful runs remain historical evidence; the
final verification summary identifies the final code versions.

## Event terms reviewed using free primary sources

This separate [bounded source review](broad_remaining_terms_scope_2026-10-30.json)
used **8 search queries and 6 successful page opens**, with no denied/timed-out
URL retries or purchases. Browser operations do not count hidden HTTP hops.
Saved browser text remains distinct from an original HTML archive and from
broker receipt evidence. Earlier collection barriers and budgets were preserved.

The [reviewed terms and source pins](broad_remaining_terms_review_2026-10-30.json)
establish these additional facts:

| Case | Resolved facts | Remaining gate |
| --- | --- | --- |
| JCI/ADNT 2016 | Distribution/regular trading October 31, 2016; one ADNT share per ten JCI shares; parent share count unchanged. | Use a feature reset at the first post-distribution session. Membership is not investable until November 30, so no portfolio ADNT entitlement is fabricated. The reset is carried in the readiness package, not yet applied by a new engine adapter. |
| AIV 2019 | No-election holders follow the non-lottery prorated branch. Cash-election lottery winners have a different outcome. Published per-record-share terms and conversion price are saved. | No simulated holder election/lottery result has been selected; preserve record-date ownership, earlier reverse split, fractions and availability. |
| AIV 2020 | No election is deemed a cash election, then prorated into cash plus stock; it is not an all-cash payment. | Correct stock issuance/reverse-split ordering and record-date holdings are still needed. Final release was published after the stated payment date; it is not proof of earlier information availability. |
| SLG 2021/2022 | Direct filings establish conditional cash/stock outcomes and reverse-split dates. This resolves the earlier SLG 2022 search-only limitation for these terms. | Published share allocations are approximate. They remain blocked as exact ledger inputs; the reviewed releases do not establish all no-election/default details or actual broker receipts. |

Sources: [ADNT completion filing](https://www.sec.gov/Archives/edgar/data/833444/000110465916153134/a16-20376_1ex99d2.htm),
[ADNT information statement](https://www.sec.gov/Archives/edgar/data/833444/000104746916015901/a2229903zex-99_2.htm),
[AIV 2019 election results](https://investors.aircommunities.com/press-releases/news-details/2019/Apartment-Investment-and-Management-Company-Announces-Election-Results-for-Special-Dividend-03-22-2019/default.aspx),
[AIV 2020 election results](https://investors.aircommunities.com/press-releases/news-details/2020/Apartment-Investment-And-Management-Company-Announces-Election-Results-For-Special-Dividend/default.aspx),
[SLG 2021 filing](https://slgreen.gcs-web.com/static-files/a434008a-6e7d-43ff-a32e-2a9a741998f6),
[SLG 2022 filing](https://www.sec.gov/Archives/edgar/data/1040971/000110465922003152/tm222480d1_8k.htm).

[Conditional election resolution](../backtesting/election_terms.py) uses reported
per-holder terms, never company aggregate totals. It requires an explicit
election/lottery branch and preserves precision/receipt limitations. General
owner approval does not select a favorable historical election.

## A newly identified provider-data gap

There are **22 security/ex-date groups containing 44 dividend records** with
different provider event IDs. Some differ by CUSIP. Two records on one date
could be duplicates or separate economic components. Both remain saved and
blocked until reconciled; no record is silently deleted or credited twice.

For example, provider records label AIV's November 2020 and SLG's relevant
election distributions `special: false`, while reviewed primary documents
describe stock/cash elections. Provider classification alone cannot admit them
as ordinary all-cash dividends. Existing election gates and the new multiplicity
gate keep these cases blocked.

## What the Step 2 readiness gate says

The [offline gate](../backtesting/diagnostic_preflight.py) checks the approved
policy, pinned input files and remaining economic/identity records. It preserves
all **100 original members**, applies the reviewed ADNT feature-reset requirement
to the handoff metadata, and reports unresolved inputs in structured form.

See [the current gate report](broad_diagnostic_preflight_2026-10-30.json) and
[remaining review rows](research_data/broad_diagnostic_remaining_gates_2026-10-30.csv).
Rows can describe related constraints on the same event; their count does not
mean that many distinct company events or trades occurred.

The final report contains 238 overlapping gate rows: 25 material-event terms,
170 dividend-term records and 43 provider identity/economic records. PEAK's
one-for-one continuity has diagnostic admission; it has no strict settlement
verification. JCI's reviewed ADNT reset is carried in the handoff metadata.

The current approved executable preparation policy is
[version 5](broad_diagnostic_accounting_policy_v5.json). Earlier versions and
compiled outputs remain intermediate evidence; their execution pins should not
be changed to fit current code. The original proposal remains unchanged.

Reproduce the final preparation into fresh workspace directories:

```powershell
.\.venv\Scripts\python.exe -m backtesting.diagnostic_preparation --revision data/reports/broad_corrected_input_v1 --policy docs/broad_diagnostic_accounting_policy_v5.json --output data/reports/a_fresh_approved_preparation
.\.venv\Scripts\python.exe -m backtesting.diagnostic_preflight --preparation data/reports/a_fresh_approved_preparation --output data/reports/a_fresh_step2_preflight
```

The compiler requires an explicit versioned policy to avoid silently using a
stale proposal. These commands prepare/review inputs; they do not score strategies.

Assent clears the modeling-choice gate. It does not clear material terms,
approximate allocations, multiple dividend components or unresolved identity
records. `engine_adapter_integrated`, `engine_handoff_ready`, strict admission
and performance readiness remain false. No new return percentages are available.

## Next and responsibilities

**My work:** reconcile multiple dividend components, finish conditional
election/identity admission and implement the main engine bridge after the data
gates clear. The existing strict ownership runtime must continue rejecting
unverified delivery; the diagnostic bridge needs its own clearly labelled
settlement, basis, stop-state and risk treatment. A finite performance comparison
plan remains separate from unit tests and preparation.

**Your part now:** no additional setup, purchase, personal risk file edit or
repeat approval of these defaults. New economic facts remain my research work.
If another modeling choice is genuinely necessary, I will present the concrete
choice with its effect rather than infer your answer.

No brokerage requests, paid sources, orders, dependency installs, reserved
2024–2025 candles or new historical performance runs were used. Windows tests
only; Raspberry Pi execution remains unverified. Retain the ignored report,
browser-evidence and cached-input folders when transferring research artifacts.

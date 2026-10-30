# Reconciliation tests and remaining event terms — 2026-10-30

## Status

**This continues Step 1.** The approved 70% total entry exposure, 5% per stock,
20-position limit and diagnostic accounting defaults remain recorded. No new
owner configuration or purchase is needed for the current engineering work.

Step 2 simulator integration remains incomplete. No new historical return has
been calculated. This increment adds tests, fixes validation defects and
reconciles additional dividend and event records. It does not complete every
remaining economic-data gate.

## Tests and fixes

**Final result: 484 passed, zero failures, zero errors and zero skips** in about
66 seconds. This includes 63 new focused tests (41 dividend-component tests and
22 event-term tests), the existing 66 diagnostic tests and 355 related
regressions. The full project's unrelated suites were not run.

The initial 35-test run found three failures: changing a nested browser source
was not detected, provider record IDs were not checked against the enclosing
row, and a review could be applied to an unrelated security's audit row.
All three were fixed. Identical duplicate provider rows are now rejected too;
the loader cannot silently overwrite them while grouping records.

New tests cover exact component arithmetic, genuine separate dividends,
aggregate/component double counting, repeated representations of the same
payment, malformed decisions, changed evidence, date conflicts, all three
payment scenarios, election blocking, preinvestment events, incoming-child
records, feature resets and preservation of unverified receipt/availability.
Fixture tests deny socket connections and real credential loading.

The final test counts, selected modules, source hashes, execution snapshots and
log are in [the verification record](broad_reconciliation_verification_2026-10-30.json).
The runs use synthetic inputs and saved research evidence on Windows. Raspberry
Pi execution remains unverified. Original frozen inputs and reports were retained;
the previously executed reconciliation/compiler/preflight files were archived in
`docs/research_data/diagnostic_executed_v6/` before changes.

## Dividend progress

Five additional SL Green groups have explicit same-payment representation
decisions: ex-dates 2020-10-29, 2020-11-27, 2021-04-29, 2021-05-27 and
2021-06-29. The
[2020 fourth-quarter issuer results](https://slgreen.gcs-web.com/node/25891/pdf)
support the November/December payments; the
[2021 second-quarter issuer results](https://www.sec.gov/Archives/edgar/data/1040971/000104097121000021/a21q2supplemental.htm)
support the May/June/July payments. These reports support nominal cash amounts
and payment dates, not independent verification of the provider ex-dates.

One representative row carries each payment amount; each other representation
keeps its original provider record but has no independent entitlement. None
becomes executable while the separate lineage/election gates remain unresolved.
Across the original 22 ambiguous groups, ten now have explicit economic
interpretations; three of those ten remain cash/stock election cases. Twelve
groups still lack a complete component interpretation. This is not a claim
that ten groups are ready for trading or return scoring.

The [issuer-hosted dividend-history table](https://slgreen.gcs-web.com/stock-information/dividends-splits)
identifies its data as coming from Mergent. It shows November 29, 2020 (a Sunday)
and May 28, 2021, where the provider rows show November 27 and May 27. Those two
groups retain explicit date-conflict blockers. No date was silently replaced,
and hosting a third party's table on the issuer site was not treated as
independent issuer-authored payment evidence.

AIV ordinary dividend groups, STX identity/foreign treatment, the other SLG
groups and holder election allocations remain unresolved. The broad AIV/SLG
lineage blocks are retained; resolving a monthly amount does not establish the
number of shares that a holder would own after a stock/cash election.

## Company-event progress

- BorgWarner's [2023 second-quarter filing](https://www.sec.gov/Archives/edgar/data/908255/000090825523000044/bwa-20230630.htm)
  confirms one PHINIA share per five BorgWarner shares, distribution July 3,
  2023, with June 23 as the record date. The ratio is now primary-supported;
  due-bill entitlement, fractional cash and schedule admission remain gated.
- The WK Kellogg [information statement](https://www.sec.gov/Archives/edgar/data/1959348/000119312523233549/d543757dex991.htm)
  supports the one-for-four ratio, announced October 2 timing, fractional sale
  mechanism and due-bill transfer conditions. An
  [audited plan filing](https://d18rn0p25nwr6d.cloudfront.net/CIK-0001959348/f6b6505e-0648-4614-8fe1-0f36f10313de.pdf)
  corroborates completion on October 2, 2023. Announced 12:01 a.m. timing is not
  treated as independently verified intraday completion or broker receipt.
  No holder entitlement, cash fixing or account credit was invented.
- APD/VSM, HCP/QCP and YUM/YUMC warmup events occurred before the portfolio's
  November 30, 2016 membership availability. They generate no simulated
  portfolio entitlements. Parent feature history must reset at the first saved
  session on or after each distribution; these reset requirements are exported
  for the future Step 2 adapter. They are not applied to an engine yet.
- Incoming VTRS, KLG and PHIN distribution records on their received-security
  streams are context. Owning the child does not earn another parent
  distribution. The corresponding parent events retain their separate gates.

The new public review closed after eight searches and eight opens, with a $0
purchase budget, no price collection and no retry of earlier denied or timed-out
URLs. It did not resume an old collection batch. Saved browser extractions and
the primary/third-party distinctions are pinned in
[the follow-up facts](broad_terms_followup_facts_2026-10-30.json).

## Rebuilt readiness

The offline compiler and preflight completed for base, five-session delay and
no-credit scenarios, retaining all 100 original members and 2,698 provider
dividend records. Six previously blocking rows are now correctly inapplicable:
three preinvestment material events and three incoming-context records.

| Overlapping gate rows | Before | Now |
| --- | ---: | ---: |
| Material-event terms | 25 | 22 |
| Dividend terms | 166 | 166 |
| Provider identity/event terms | 43 | 40 |
| Total | 234 | 228 |

These are overlapping constraints, not 228 stocks or 228 separate trades. In
particular, 111 dividend rows share unresolved AIV/SLG election lineage
dependencies. Payment-component review does not remove those dependencies.

Current preparation uses approved policy v7 and explicitly pinned component v2
and event-term overlays. It does not rewrite the original proposal or infer
additional owner approval. The
[preparation summary](broad_diagnostic_verified_preparation_2026-10-30.json)
and [remaining-gate report](broad_diagnostic_verified_preflight_2026-10-30.json)
record the results. `data_gates_clear` and `engine_adapter_integrated` remain
false. There were zero broker requests, orders, purchases and new historical
performance runs; reserved 2024–2025 candle files were not read.

## Next work and owner responsibilities

Engineering: complete AIV/SLG election and ordinary-dividend schedules, foreign
and special-distribution terms, and the remaining split/identity/event mappings.
Apply the exported feature resets and pending rights atomically when the Step 2
bridge is integrated. Run focused checks on each remaining change. Missing
holder choices and economic facts must be reported explicitly, not filled with
an all-cash outcome, a zero amount or a fabricated settlement date.

Owner: no new setting is required now. If the remaining evidence requires a new
modeling choice, it will be presented concretely for review before a new
performance batch. Personal paper-risk settings and paper activation remain
separate later decisions; the approved research allocation is already recorded.

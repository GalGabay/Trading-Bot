# Election, dividend and identity resolution — 2026-10-30

## Current status

**Step 1 progressed but is incomplete. Step 2 is not connected.** The input
preparation and readiness gate completed offline for base, five-session delay
and no-credit scenarios. The result retains all 100 selected members and all
2,698 provider dividend records. No price observations or frozen source inputs
were rewritten, and no 2024–2025 candle files were read.

There were no purchases, broker requests, orders or new historical profit/loss
runs. This is preparation for the larger simulated experiment.

The research allocation remains approved: 70% total entry exposure, 5% per stock
and 20 positions. No repeat risk-setting approval is requested.

## Changes completed

### 1. Identity changes and split instructions

Added 15 reviewed instructions, preserving every provider row:

| Kind | Count | Treatment |
| --- | ---: | --- |
| Same-instrument ticker changes | 6 | Keep holdings, cost basis, position age and features; invalidate symbol-bound execution state |
| Forward splits | 5 | Multiply shares, preserve total basis, rebase stops and pending share rights; keep unresolved fractions as claims |
| Preinvestment reference actions | 4 | No portfolio quantity or cash credit; require fresh features at the boundary |

The alias cases are FB/META, FISV/FI, CTL/LUMN, CBS/VIAC, VIAC/PARA and
NLOK/GEN. Fourteen previously blocked provider rows now have reviewed routing;
the fifteenth instruction overlaps the already excluded JCI predecessor action.

The [CBS completion filing](https://www.sec.gov/Archives/edgar/data/1339947/000119312519306335/d833313dex991.htm)
states that existing CBS holders retained their shares and that VIAC trading
began December 5, 2019. The provider's February 13, 2020 notice must not create a
second economic event or move the transition away from the already configured
December boundary. The Viacom-holder exchange ratio is not applied to CBS lots.

The split cases are AAPL, AFL, NEE, AMZN and BF.B. Each ratio has issuer or
clearinghouse support. Some session labels use the disclosed convention of the
provider ex-date being the first saved session after the issuer's reported
split/distribution date. That is not independent verification of an intraday
effective instant or actual broker receipt. GEN's session similarly remains an
announced date corroborated by provider metadata, not independent completion
evidence. Strict evidence flags remain false.

The [corporate-action review](broad_corporate_action_review_2026-10-30.json)
binds sources, provider IDs, stream segments, dates and ratios. The new compiler
emits `corporate_actions.json`; no instruction has executed against a portfolio.

### 2. Election schedules and a missing provider event

Added conditional schedules for AIV 2019, AIV 2020, SLG 2021, SLG 2022 and
MAC 2020. They separate record ownership, share issuance, reverse splits and
payment availability. They do not select an investor election.

| Case | Required ordering / remaining limitation |
| --- | --- |
| AIV 2019 | February split precedes record ownership; March issuance follows. The provider inventory omits this issuer-documented special dividend entirely. |
| AIV 2020 | Record ownership precedes November issuance; issuance precedes the reverse split. |
| SLG 2021 | Record ownership and issuance precede the January split. The newly reviewed default is a stock election subject to proration; reported final allocations remain approximate. |
| SLG 2022 | Record ownership and issuance precede the later January split. Exact holder quantities and the default branch remain unresolved. |
| MAC 2020 | Cash/stock allocation and conversion terms remain unresolved; the conflicting provider amounts cannot become ordinary cash credits. |

SLG's [December 2020 filing](https://www.sec.gov/Archives/edgar/data/1040971/000110465920132238/tm2037666d1_8k.htm)
establishes the default stock election and the ordinary/special components of
the combined distribution. This does not establish an exact prorated allocation
or select a choice for a hypothetical research holder.

The saved [AIV 2019 issuer notice](https://investors.aircommunities.com/press-releases/news-details/2019/Apartment-Investment-and-Management-Company-Announces-Election-Results-for-Special-Dividend-03-22-2019/default.aspx)
describes the missing $2.02 special distribution. Its conditional stock/cash
terms are inventoried without fabricating a provider row or an ex-date. Issuer
aggregate share totals are not individual holder allocations. A taxable stock
valuation is not automatically a fractional-cash fixing price.

Unreleased share rights must retain correct units through a subsequent split;
already fixed cash receivables must not be multiplied by a share ratio. These
requirements are encoded in the schedule contract for the later adapter. They
are not implemented as portfolio transfers yet.

Five explicit election gates now cover these schedules. The previous dividend
row gates alone could not detect the entirely omitted AIV event.

### 3. Dividend dependency corrections

An unresolved future election cannot alter shares used by an earlier ordinary
cash dividend. Dependency cutoffs now begin at the first relevant split or share
issuance: February 21, 2019 for AIV and January 15, 2021 for SLG. Component,
special, foreign, date-conflict and same-boundary blockers remain independent.

This removes inappropriate future-event dependencies from 37 previously blocked
rows. Conversely, MAC has an election without a linked reverse split: 14 later
ordinary rows now correctly depend on its unresolved June 2020 stock issue.
The net dividend gate reduction is 23 rows. No difficult member was dropped.
The ordinary AIV/SLG duplicate groups without sufficient source support remain
unresolved; this correction does not deduplicate them by matching amounts alone.

### 4. Cash-merger rights and the Nielsen boundary

A separate, closed five-document review supports gross fixed USD consideration
for XL, RHT, NLSN and MON. Four conditional cash-merger receivable plans are now
admitted at the data level. They consume parent lots once and require invalidation
of stale orders/stops at the configured terminal boundary.

The [Nielsen completion notice](https://www.nielsen.com/news-center/2022/nielsen-announces-closing-of-transaction-with-evergreen-and-brookfield-led-consortium/)
states that NYSE trading ended from October 12, 2022. Its accounting plan now
uses the October 12 open and prior October 11 close ownership; the frozen
October 11 legal completion date is retained separately. It no longer proposes
consuming the holding at the October 11 open. A duplicate provider cash-merger
record routes to this same canonical event.

Cash availability is **unknown** for all four admitted receivables. They carry
known gross face value but release no buying power in any scenario. No payable
date, tax deduction or actual account credit was invented. Nominal gross cash
valuation follows the approved research convention and is not a personal tax
calculation. These plans still need the Step 2 ledger bridge before execution.

CSRA remains gated: the reviewed acquirer filing confirms its tender price and
short-form merger, but was not accepted as sufficient minority-holder conversion
evidence for this admission.

## Readiness results

| Overlapping gate rows | Previous | Current |
| --- | ---: | ---: |
| Material-event terms | 22 | 18 |
| Dividend terms | 166 | 143 |
| Provider identity/event terms | 40 | 25 |
| Explicit election schedules | 0 | 5 |
| Total | 228 | 191 |

The five new schedule gates expose existing economic gaps rather than certifying
their resolution. Counts overlap: they are not 191 companies or necessarily 191
independent events. Eighty-four dividend rows retain election-lineage dependencies.
Foreign/special distributions, unresolved components and source-date conflicts
also remain gated. The remaining material cases include CSRA and the stock/mixed
mergers, spin-offs and DWDP restructuring chain.

The existing approved defaults are unchanged. New current outputs use policy v11,
component decisions v2, event overlay v2 and explicit corporate/election inputs.
Earlier proposals, source barriers, protocol versions and execution snapshots
remain preserved. Version numbers identify preparation snapshots, not new phases.

- [Current preparation](broad_resolution_final_preparation_2026-10-30.json)
- [Current readiness report and individual gates](broad_resolution_final_preflight_2026-10-30.json)
- [Primary source facts and access limitations](broad_resolution_facts_2026-10-30.json)
- [Cash-merger evidence](broad_cash_terms_facts_2026-10-30.json)

## Verification and limits

Normal offline preparation and preflight completed for all three scenarios with
their runtime source/checksum, date, ratio and schedule checks. All 2,698 original
provider dividend identities are preserved. Earlier executions and current
executed sources were snapshotted with their reports.

**No unit tests were added or run for this increment.** The earlier 484 passing
tests describe the earlier code and do not verify these new modules or changes.
Raspberry Pi execution remains unverified. Full Step 2 integration is incomplete:
`data_gates_clear` and `engine_adapter_integrated` remain false. No new strategy
performance batch has been authorized or run.

The two new public reviews closed at eight searches / sixteen opens and zero
searches / five opens. There were nineteen successful opens overall; the SLG
press-list timeout and oversized AIV filing remain documented failures and were
not retried. Earlier denied RTN/Ball/Bayer URLs were not retried. No paid source,
account endpoint, download of new candles or purchase was used.

## Next and the owner's part

Engineering: focused tests for the new routing/schedules, then the remaining
exact election/fractional terms, dated dividend components, stock/mixed merger
and spin-off entitlement schedules, and unsupported split/identity cases.
Complete the Step 2 pending-rights bridge only when its admission checks clear.

Owner: no purchase, environment setup or repeat allocation decision is needed.
The research holder's election rule remains unspecified. A
[concrete no-election proposal and alternatives](research_election_policy_for_review.md)
have now been presented in chat for the owner's choice. No response or choice
is inferred from elapsed time. General accounting approval
does not authorize guessing a holder choice or silently treating rounded source
numbers as exact allocations. Paper activation remains a separate later step.

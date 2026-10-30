# Step 1: holder ownership schedules and remaining shared gaps

October 30, 2026. **Still Step 1 of 4.** Preparation now has **188 overlapping
blocking rows, down from 191**. Step 2 integration and new performance runs
remain blocked. The [four-step tracker](broad_backtest_step_tracker.md) records
the current position.

## What was resolved

### Kellogg / WK Kellogg: follow the holder entitled to the shares

Previously saved primary sources establish the one-for-four distribution,
its October 2, 2023 completion, regular-way due bills and fractional treatment.
The [issuer announcement](https://newsroom.kellanova.com/2023-09-11-KELLOGG-COMPANY-BOARD-OF-DIRECTORS-APPROVES-SEPARATION-INTO-TWO-COMPANIES%2C-KELLANOVA-AND-WK-KELLOGG-CO)
explains that regular-way sales through September 29 transfer the WK Kellogg
share right to the buyer. Separate when-issued/ex-distribution markets existed;
the cached strategy input uses regular-way parent shares only.

The new source-bound instruction therefore uses the September 29 saved close
to determine the modeled entitlement before the October 2 open. Simply owning
Kellogg on September 21's record date is insufficient if those shares were later
sold regular-way with the right attached. This prevents crediting the old seller
and missing the later buyer. Buying at the October 2 ex-distribution open earns
no right; a later parent sale cannot erase a right already established.

The instruction preserves the parent quantity, creates the child right once,
requires fresh parent features after the raw-price distribution, and invalidates
stale order/stop state. No portfolio quantities have actually been changed.

Under the previously approved diagnostic delivery convention:

| Scenario | Modeled whole-share availability |
| --- | --- |
| Base | October 2, 2023 saved open |
| Five additional saved sessions | October 9, 2023 saved open |
| No credit/delivery | No release; retain and value the right |

These are modeled availability times, not broker receipt. The provider's October
3 due-bill redemption label is retained separately and is not used as a verified
share-delivery timestamp. Fractions stay exact unspendable share claims marked
under the approved current-quote convention. The
[information statement](https://www.sec.gov/Archives/edgar/data/1959348/000119312523233549/d543757dex991.htm)
describes aggregation and sale of fractions, but actual sale proceeds, fees,
withholding and receipt remain unknown. No cash fixing or spendable payment was
invented; there is no fixed cash leg apart from unresolved fractional proceeds.

Three previously blocking rows are now represented by reviewed instructions:

1. The canonical K-to-KLG material distribution.
2. Its duplicate provider representation on the parent stream.
3. The KLG.WI-to-KLG alias at the child's first regular session, which creates
   no additional holding or feature history from the when-issued market.

The separate incoming distribution record on the child remains context, as
before. All original provider records are retained; the event is not applied twice.

### SL Green January 2021 election: corroborated ex-distribution boundary

The saved [OCC notice hosted by MIAX](https://www.miaxglobal.com/sites/default/files/alert-files/SLG_Dividend_47969.pdf)
establishes December 14, 2020 as the ex-distribution date, with December 15 record
ownership and January 15 payment. Its annotated daily ownership instruction
uses the prior December 11 saved close, before ex-date opening fills.

This corroboration is separate from the exact share-allocation problem. The
notice's options deliverables are not common-holder allocations. Reported final
SLG shares remain approximate, and the election schedule remains conditional
and blocked. No historical known-at, actual holding or broker receipt flag was
promoted.

## Implementation and replay

[The holder-terms module](../backtesting/holder_terms.py) validates the review's
provider/spec/source pins, issuer/class relationships, completed ratio, regular
session boundaries, provider records and alias scope. Preparation accepts an
optional `--holder-terms` review. Preflight accepts only the supported complete
instruction contract; routing a provider row to an unsupported event cannot
clear its gate.

Normal preparation and readiness checks completed offline for all three
scenarios. Runtime assertions confirmed:

- All 100 selected members and 2,698 dividend identities remain.
- Provider identities are unchanged and dividend plans are unchanged.
- The three new scenario plans pass their instruction-contract checks.
- Fractions have no fabricated cash fixing; no scenario creates spendable cash.
- SLG's corroborated boundary does not remove its allocation blocker.
- Step 2 handoff is still rejected as expected.

**No unit tests were added or run in this increment.** The preceding 571-test
result applies to the preceding code. Focused tests for the new holder module
and preparation/preflight paths remain to be run. Raspberry Pi execution is
also unverified. Runtime preparation is not a substitute for those tests.

## Public-source attempt and its limits

A separately capped review used three search queries and one page open. The
first directly requested DTCC election form returned 404, so new requests stopped.
There were no new primary documents admitted. Search excerpts about MAC's
conversion remain discovery only; they were not substituted for opened evidence.
The subsequent implementation used previously saved primary documents.

The failed URL, response and unused budget are recorded in the
[closed collection record](broad_holder_terms_collection_2026-10-30.json).
It will not be retried or silently resumed. Older failed MAC/SLG/SEC URLs and
their closed scopes remain preserved. There were no paid fallbacks, package
installs, broker requests, orders, price downloads or profit/loss runs. No
reserved 2024-2025 candle files were read.

## What remains before Step 2

| Category | Before | Now |
| --- | ---: | ---: |
| Material-event terms | 18 | 17 |
| Dividend terms | 143 | 143 |
| Provider identity/event terms | 25 | 23 |
| Election schedules | 5 | 5 |
| **Overlapping rows** | **191** | **188** |

The five election schedules are not resolved. AIV 2019 still lacks an admitted
ownership boundary for its omitted special dividend; AIV 2020 still needs full
schedule admission. SLG's reported approximate allocations cannot be treated
as exact holder quantities. MAC's final conversion/fractional terms are not
established by directly reviewed evidence in this work.

Shared election-lineage dependencies affect 84 later dividend rows:

| Original root | Dependent dividend rows |
| --- | ---: |
| AIV and its received descendant | 24 |
| SLG | 46 |
| MAC | 14 |

Those are shared dependencies, not 84 separate election research projects.
Other special/foreign distributions, component ambiguities and ex-date conflicts
remain independent gates. The remaining 143 blocked dividend rows form 124
instrument/ex-date groups. Remaining material cases include stock/mixed mergers,
other spin-offs, the DWDP chain and CSRA holder terms.

The [structured remaining-work inventory](broad_holder_terms_remaining_work_2026-10-30.json)
lists each election's resolved/unresolved dimensions, the shared roots, every
blocked dividend group, all 17 material rows and 23 provider routes. It is an
inventory of missing facts, not permission to infer them or drop difficult stocks.

## Evidence and next work

- [Source-backed holder review](broad_holder_terms_review_2026-10-30.json)
- [Additional review of cached primary facts](broad_holder_terms_cached_facts_2026-10-30.json)
- [Preparation summary](broad_holder_terms_preparation_2026-10-30.json)
- [Readiness / individual blocking rows](broad_holder_terms_preflight_2026-10-30.json)
- [Offline replay assertions and executed source snapshots](broad_holder_terms_replay_2026-10-30.json)

Next engineering work, **still Step 1**: focused tests of these holder schedules
and their routing, followed by the exact election allocations and the dated
dividend/material terms identified in the inventory. Further source retrieval
requires its own finite scope and must preserve the access-stop records.
Step 2 starts after admission checks clear; no new performance batch is authorized.

Owner: no new configuration, purchase or repeat approval of 70% total entry
exposure, 5% per stock, 20 positions or the no-election rule is needed now.

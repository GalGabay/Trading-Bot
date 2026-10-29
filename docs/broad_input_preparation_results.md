# Step 1: historical input preparation

**Later verification:** see [Step 1 tests and event review](broad_input_verification_results.md)
for 193 passing tests, hardened input checks, cached-data replay and the reviewed
event queue. The original acquisition/reconstruction record below is preserved.

**2026-10-29. Price collection and candidate reconstruction completed;
Step 1 is not fully cleared for performance scoring.**

There were **$0 purchases, no account requests, no orders and no backtests**.
The selected 70% research capacity is retained as metadata; no runtime or
paper-risk setting changed. No new dependency was installed.

## What is now implemented and available

| Deliverable | Result |
|---|---|
| Frozen historical members | All original 100 retained; no survivor replacements |
| New historical price probes | 30, including later aliases and received-stock branches |
| New observed daily candles | 19,958 |
| Cumulative historical API GETs | 60: 30 bars and 30 actions, within 192 allowed |
| Reconstructed candidate streams | 119: 100 member streams, 16 received-security streams and 3 warmup-only references |
| Candidate interval coverage | All 119 configured intervals have observed scheduled candles; no fills or interpolations |
| Independent source-to-output comparison | All 203,683 output rows agree with pinned input observations |
| Candidate material-event records | 25, with explicit consuming and resulting instrument IDs |
| Acquirer-only provider records | 10 classified as context; no cash/share credit to buyer shareholders |
| Unresolved event-review records | 39: 25 candidate material terms, 13 nonstandard ratios and one same-symbol reorganization |
| New public document archival | First SEC request returned 403; batch stopped, zero documents archived |

**Complete configured intervals does not mean 100 companies traded for all
eight years or that 119 securities are eligible for new purchases.** Some
original securities end at mergers; successors and children have distinct
streams. All identities remain provisional for execution. The three short
2016 reference probes are explicitly not complete child histories: those
distributions precede conservative membership availability and the uninvested
warmup, so no portfolio holdings earn them in the declared scored windows.

### Ticker and ownership corrections

- Reconstructed dated candidate chains for FB/META, BLL/BALL, FISV/FI,
  CBS/VIAC/PARA, CTL/LUMN, SYMC/NLOK/GEN and HCP/PEAK.
- Retained original Delphi Automotive as the APTV parent; separated the
  distributed DLPH child and its later BWA successor. BWA's PHIN distribution
  was discovered in the new provider inventory and received its own probe/ID.
- Separated original DOW, the DWDP/DD successor, and the new DOW/CTVA children.
  Child distributions and the reverse split consume the DWDP holder, not the
  original security or an unrelated child.
- Restricted original XL, LLL and MON candidate intervals instead of attaching
  later reused-ticker observations. Original files remain intact, and rows
  outside a specific binding are reported rather than deleted from evidence.
- Added candidate RTX, VTRS, CI, LHX and BHGE/BKR valuation streams, plus
  KTB, JBGS, CEG, AIRC and KLG distribution branches. When-issued VTRSV remains
  a separate probe, not an automatic replacement for regular VTRS trading.

The CBS discovery resolves the earlier date conflict at the source-note level:
existing CBS Class B shares continue as VIAC from December 5, 2019, not the
vendor's later processing date. The subsequent PARA regular-trading transition
is February 17, 2022. Healthpeak's own reporting places PEAK regular trading
on November 5, 2019, differing from the saved provider processing date.
These are curated candidate boundaries with source references, not archived
full-source or actual broker-delivery certification.

Primary references include the
[CBS completion exhibit](https://www.sec.gov/Archives/edgar/data/1339947/000119312519306335/d833313dex991.htm),
[Paramount's financial reporting](https://www.sec.gov/Archives/edgar/data/813828/000081382822000033/R9.htm),
[Healthpeak's annual report](https://www.sec.gov/Archives/edgar/data/765880/000162828020001456/healthpeak10-k12312019.htm),
[DowDuPont's merger release](https://www.investors.dupont.com/news-and-media/press-release-details/2017/DowDuPont-Merger-Successfully-Completed/default.aspx)
and [the Dow separation release](https://investors.dow.com/en/news/news-details/2019/Dow-completes-separation-from-DowDuPont/default.aspx).
Exact source URLs and review terms are in the frozen source queue below.

### Company-event handling in this data package

The package separates ordinary dividends, potential real splits, nonstandard
provider adjustment ratios, parent distributions, acquirer context and
same-symbol reorganizations. **No event has been posted to a portfolio ledger.**
The existing accounting engine is reused later during integration; these
records describe input economics and unresolved terms.

For example, a cash-merger record returned for an acquirer's ticker does not
create a payment to holders of the acquirer's stock. A distribution of child
shares also cannot be replaced with a provider price-adjustment factor that
simply increases parent shares. Nonstandard ratios remain review candidates;
some may be genuine fractional splits. None is automatically declared wrong
or booked as verified economics.

Each material event records its actual consuming instrument, share legs,
economic anchor and any cash amount. **Delivery timestamps, entitlement
verification and fractional-cash fixings remain unset.** Historical amounts
describe proposed simulation inputs, not money received or spent here.

## What remains blocked, exactly

1. **Primary-source capture:** the new 32-document queue stopped at its first
   request, a SEC 403. Remaining documents were not attempted. Earlier Ball
   and Bayer barriers remain preserved; their denied URLs were not retried.
   Sixteen bounded search queries supplied discovery/source notes, not original
   HTML archives or independent full-period verification. No access workaround,
   paid service or automatic continuation was used.
2. **Material economic terms and identity admission:** the
   [39-row event review queue](research_data/broad_unresolved_event_terms.csv)
   records precise candidates, consuming securities, dates and reasons.
   Nonstandard AIV/SLG/JCI and other provider factors, class/entitlement terms,
   and actual cash/share/fractional availability still need resolution.
   Some records concern warmup only; the table does not mean 39 erroneous
   events or 39 distributions earned by the strategy.
3. **Dividend timing and availability:** after interval binding, provider
   inventories contain 2,698 dividend candidates; 1,383 lack a payable date
   and all lack declaration dates. These counts differ from the earlier
   two-stock/100-query snapshots because successor data is now included.
   Known source terms and previously approved assumptions are not silently
   extended. Missing dates do not become ex-date cash, fabricated payments or
   permission to use future information.
4. **Diagnostic assumptions and checks:** full histories, event ownership and
   any diagnostic timing/receipt policy still need a consistent implementation
   and focused verification before integration/scoring. The separate 70%
   selection is already recorded; it does not certify these facts or approve
   a performance batch.

Consequently, `performance_ready`, `step1_fully_complete`, strict evidence
flags and paper approval remain **false**. This is a concrete candidate input
package, not an accepted `HistoricalUniverse` or `OwnershipSchedule`. It cannot
be advertised as a qualified 100-stock return experiment yet.

## Reproducibility and validation

Implemented:

- [Successor collector](../backtesting/successor_collection.py), reusing the
  fixed GET-only historical query builders and central credential loader.
- [Single child-branch probe](../backtesting/successor_branch_probe.py), carrying
  the original 58-attempt ledger forward to 60, within the same 32-interval /
  192-attempt allowance and original conservative 15-minute clock. It does not
  reopen or reset a previous acquisition allowance.
- [Offline input builder](../backtesting/historical_input.py), with explicit
  identities, intervals, raw-source provenance and acquirer/holder roles.

Protocols and evidence:

- [Input-preparation scope](broad_input_preparation_scope.json).
- [Exact initial 29-probe plan](broad_successor_collection_plan.json) and
  [one reviewed PHIN probe](broad_successor_branch_probe.json).
- [Exact public-source queue](broad_input_public_sources.json).
- [Historical-input specification](broad_historical_input_spec.json).
- [Candidate manifest](broad_candidate_input_manifest.json),
  [119-stream inventory](research_data/broad_prepared_stream_inventory.csv),
  [30-probe inventory](research_data/broad_successor_probe_inventory.csv) and
  [event-review queue](research_data/broad_unresolved_event_terms.csv).
- [Preparation summary](broad_input_preparation_summary.json) and
  [independent source reconciliation](broad_input_source_reconciliation.json).

Validation passed for raw timestamps, timezones, duplicate/invalid candles,
OHLC/positive prices, volume, saved sessions, scope bounds, complete configured
intervals, source hashes and original-observation equality. Every output row
was independently compared with its pinned source group. Request numbering,
caps, no-purchase flags, material-event IDs/ratios and retained membership were
also checked. Warnings are preserved separately from hard errors.

**No unit-test suite was added or run in this increment.** The earlier 147
passing tests remain evidence for their named code versions, not for these
new modules. An initial local builder error (duplicate dictionary keyword)
was corrected; the failed folder and intermediate reconstruction were retained.
The final successful package is `data/reports/broad_historical_input_v3`.
No new networking occurred during reconstruction or reconciliation.

Ignored payload/ledger directories:
`data/reports/broad_successor_collection_v1`,
`data/reports/broad_successor_branch_probe_v1`,
`data/reports/broad_input_public_sources_v1` and
`data/reports/broad_historical_input_v3`. Retain these plus the older pinned
sources; Git alone does not transfer local evidence to the Pi. Collection
journals are closed and must not be deleted to restart a denied/exhausted scope.

Rebuild candidate streams **offline**, into a fresh directory:

```powershell
.\.venv\Scripts\python.exe -m backtesting.historical_input --output data/reports/a_fresh_input_reconstruction
```

On the Pi use its own environment's `python` and retained source evidence.
Windows execution only has been checked; Pi execution remains unverified.
No 2024-2025 candles, personal risk file changes or paper submissions were used.

## Next and responsibilities

**My work:** verify these new modules with focused offline tests when requested,
then resolve the bounded event/source gaps or prepare the exact remaining
diagnostic assumptions for review. Do not start Step 2 performance integration
under an assertion that Step 1 is fully cleared. A failed public archive must
not trigger purchases or another automatic collection attempt.

**Your part now:** no purchase, installation or repeated approval of 70%.
Before return simulations, review only the concrete remaining assumptions and
scope that I present; a paper-risk decision is still a separate later task.

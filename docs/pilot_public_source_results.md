# Pilot public-source collection and reconciliation

Date: 2026-10-27. **New purchases: $0. Orders: zero.**

**Verification follow-up:** The [focused offline tests](public_source_test_results.md)
now pass 57 new tests and 42 related regressions (99 total). Input and
provenance checks were strengthened. A fresh offline replay matches the
previous CSV and JSON exactly. The acquisition findings below are preserved;
no network collection was resumed.

## What was collected

We saved **11 public source files**: six substantive company/fund documents
and five index pages. The [review catalog](pilot_public_source_review.json)
records exact URLs, timestamps, file hashes, request logs and source targets.
Raw files remain in `data/reports/pilot_public_sources_v1`.

| Source | Saved document(s) | What the new review establishes |
| --- | --- | --- |
| Apple | [Official dividend history](https://investor.apple.com/dividend-history/) | 32 regular-cash declaration/record/payable/nominal-amount rows in 2016-2023; the page says amounts are not split adjusted |
| JPMorgan | [May 17, 2016 declaration](https://www.jpmorganchase.com/ir/news/2016/common-stock-dividend-051716) and [September 21, 2021 declaration](https://www.jpmorganchase.com/ir/news/2021/jpmorgan-chase-declares-increased-common-stock-dividend) | Two dated common-stock announcements with amounts, record dates and issuer payable dates |
| CBRE | [2016 Form 10-K](https://ir.cbre.com/financial-reports/sec-filings/content/0001193125-17-064772/d291832d10k.htm) and [2023 Form 10-K](https://ir.cbre.com/financial-reports/sec-filings/content/0001138118-24-000006/cbre-20231231.htm) | Class A common-stock/listing anchors, dated CBG/CBRE lineage and the issuer's statement that no common cash dividends had been declared or paid since inception |
| State Street / SPY | [Official historical distributions workbook](https://www.ssga.com/library-content/products/fund-data/etfs/us/spdr-etf-historical-distributions.xlsx), linked from its [distribution index](https://www.ssga.com/us/en/institutional/resources/documents/etf-dividend-distributions) | 32 SPY distributions with independently supplied ex-dates, record dates, payable dates and dividend amounts in 2016-2023 |

The five saved index pages are discovery/provenance evidence. An index or a
JavaScript shell is not itself a complete historical event schedule. None of
these sources is a brokerage statement or proof of account cash availability.

## What improved

The [66-row reconciliation](research_data/pilot_collected_dividends.csv)
contains 32 Apple rows, 32 SPY rows and two JPMorgan rows. Original provider
responses and the preceding 95-row matrix remain unchanged.

### Apple: all 32 provider dividends have issuer declaration/payable terms

The nominal amounts agree with all 32 saved provider rows. The joins use
the symbol, exact nominal amount and a unique declaration-to-record-date
interval containing the provider ex-date. Existing provider record/payable
fields also agree where present. No event is matched merely because it is
the next quarter.

**The Apple table has no ex-date column.** A matching provider ex-date is
therefore a cross-reference, not independent ex-date or entitlement proof.
The table supplies 17 payable fields absent from the raw provider file.
One of those, February 2020, was already supported by the earlier cached
announcement. Do not count that as a newly discovered payment.

The table is retrieved now. Its historical declaration dates are reported
facts; this retrieval does not establish exact historical public release
timestamps. Proposed knowledge bounds remain assumptions needing review.

### SPY: three omitted provider events now have primary-source records

The fund workbook supplies these additional rows:

| Ex-date | Dividend per unit | Issuer payable date |
| --- | ---: | --- |
| 2016-03-18 | $1.049604 | 2016-04-29 |
| 2018-06-15 | $1.245568 | 2018-07-31 |
| 2023-12-15 | $1.906073 | 2024-01-31 |

These rows resolve the three **previously observed empty-quarter questions**
using an actual source rather than an inferred quarterly pattern. All 29
provider ex-dates match fund-workbook rows. This is a reconciliation to that
published schedule, not a universal guarantee that every possible action
category is present.

For **28 of the 29 shared events**, the dividend amounts agree exactly.
For June 19, 2020, the provider has `1.3662419` and the workbook displays
`1.366242`: a difference of **$0.0000001 per unit**. We preserve both values
and flag the exact difference. It is consistent with display precision, but
no rounding rule or nominal ledger amount is silently selected.

The workbook distinguishes dividends from short/long capital gains. Empty
capital-gain cells remain empty; this review does not automatically convert
them to zero or declare a complete total-distribution convention. The workbook
also does not supply historical declaration/publication instants.

The late-2023 payable date is **metadata about a historical obligation**.
No 2024 price was read, no cash was credited and no simulation was run.
Any later research ending in 2023 must report a remaining right rather than
pretend that January 2024 cash was available in December.

### JPMorgan: two declarations, with the consolidated source blocked

The saved releases cross-reference the July 2016 and October 2021 provider
events using explicit declaration terms and their record/payment dates.
The older one supplies another absent provider payable field. Their stated
record dates do not independently establish ex-dates; no settlement lag was
used to manufacture them.

The official JPMorgan investor index links its consolidated dividend history
on `jpmorganchaseco.gcs-web.com`. That issuer-hosted link was explicitly
reviewed and added to the request queue's allowlist before requesting it.
It returned **HTTP 403**, and the collection stopped immediately. No alternate
route, login, paid service or retry was attempted after the barrier.
**403 does not establish that a paid subscription is necessary.**

Thirty other JPMorgan provider events still lack newly collected primary
declarations. Sixteen JPMorgan payable fields remain unavailable from the
reviewed evidence. They remain gaps, not guessed dates.

### CBRE: stronger common-share and dividend-policy evidence

The 2016 filing identifies Class A common stock on the NYSE under CBG. The
2023 filing describes CBG-to-CBRE continuity and reiterates the absence of
common cash dividends since inception. The filings provide independent
evidence beyond the empty provider action response.

The original 2016 fund filing's REIT label remains preserved. We now have
issuer support for the **common-share class/listing**, but this review does
not certify historical REIT tax status or rewrite that source label. Nor does
a no-cash-dividend statement certify absence of every split, distribution,
reorganization or other lifecycle event.

These filings are retrospective evidence for auditing past facts. They must
not become future knowledge used to select stocks or close positions in a
past simulation.

### Missing payable-field count

Of the **48 original provider omissions**, reviewed primary sources now
supply **32**: Apple 17, SPY 14 and JPMorgan one. **Sixteen remain unresolved**.
Because one Apple field was already known, the new batch resolves **31 additional
omissions beyond the preceding cached evidence**. These are issuer payable
terms, not actual cash credits or new payments to the owner.

## Limits followed and acquisition stop

- **Five** public search/open/click discovery calls, within the limit of 12.
  Search-service internal HTTP counts are not asserted.
- **18** direct document GET attempts, within the limit of 40: six initial
  sandbox connection failures, 11 saved responses and the final HTTP 403.
- The initial six failed connections received no HTTP response. After network
  permission was approved, the six explicitly requeued requests succeeded.
  Both sets count against the budget; there were no automatic retries.
- No automatic redirects, unbounded link following, credentials, broker/account
  calls, new stock-price requests, subscription changes, purchases or orders.
- No further acquisition occurred after the HTTP access barrier. Unused
  request capacity is not permission to work around that stop rule.

The not-attempted queue tail, including another Apple release, is recorded.
The result is a bounded, partly successful collection, not a claim that all
12 source targets are resolved. No dependency was installed: HTML and XLSX
reconciliation uses the standard library and existing project modules.

## Saved artifacts and reproduction

- [Source catalog and acquisition record](pilot_public_source_review.json).
- [Reconciliation summary](pilot_public_source_summary.json), including exact
  input/code hashes, unresolved items and the precision discrepancy.
- [66-row reconciliation CSV](research_data/pilot_collected_dividends.csv).
- Local raw documents, discovery results, queues and response logs:
  `data/reports/pilot_public_sources_v1`.
- Final offline report and full structured reconciliation:
  `data/reports/pilot_public_source_reconciliation_v2`.

Reproduce **offline**, from the repository root with its environment active:

```powershell
python -m backtesting.public_source_review --output data/reports/a_fresh_public_source_review
```

It needs the pinned local saved files, refuses changed hashes or an existing
output directory, and performs no HTTP. The v1 reconciliation remains preserved;
v2 makes source amounts human-readable decimals and checks the reviewed
JPMorgan event ID explicitly. Acquisition logs and old reports are not rewritten.
The downloader is a separate helper; do not rerun the stopped batch as an
automatic fallback or overwrite its evidence.

**Executed:** bounded public downloads, source checksums, source-table parsing,
event joins, exact amount/date comparisons, and static Python/document checks.
**Not run:** unit-test suites, strategy backtests, ML training, cash-delay
simulations, Raspberry Pi execution or broker-credit verification. Earlier
183-test results do not apply to these newly added collection/review helpers.

## What is next, and your part

**Next after verification:** prepare a separately bounded issuer-news
follow-up for the remaining JPMorgan declaration terms. The stopped batch
is not automatically resumed; see the verification report for its limits.

**Your part now:** no purchase, setup or personal risk-limit change. Before a
performance study uses modeled knowledge/payment timing, explicitly review
section 3 of the [pilot proposal](free_data_pilot_proposal.md). Those assumptions
and any later narrower strategy universe remain unapproved. This source
collection does not approve a paper candidate or change the acceptance criteria.

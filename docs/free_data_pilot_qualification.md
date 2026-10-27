# Four-history pilot: what qualifies and what is missing

Date: 2026-10-27. **Cached-data review completed. No strategy backtest run.**

## The result in plain language

We already have the daily price files for **AAPL, JPM, CBRE and SPY** over
2016-2023. All **8,048 candles** pass the calendar and OHLCV checks and match
their saved raw responses. No data-quality errors, volume warnings or
zero-volume rows were found under the declared validation policy.

What is incomplete is the history of **which security each ticker represents
and what happened to its shares and dividends**. The cached sources support
specific facts, including Apple's 2020 announcements and CBRE's rename.
They do not yet establish complete histories suitable for strategy scoring.

**Four price streams pass this data-quality/provenance review. Zero full-period
histories are approved for strategy scoring.** These are different conclusions;
no return estimate or paper-trading approval follows from either.

## 1. Qualification matrix

Each stream has **2,012 actual saved sessions**, January 4, 2016 through
December 29, 2023. The requested interval is `[2016-01-01, 2024-01-01)`.

| History | What qualifies as a supported fact | What remains missing | Scoring status |
| --- | --- | --- | --- |
| AAPL | Saved raw observations; membership in the dated 2016 source basket; 2018 common-stock/Nasdaq/AAPL listing anchor; four 2020 issuer dividend amounts/payable dates/announcement dates; 4-for-1 split and August 31, 2020 split-basis date | Continuous full-period identity/action completeness; primary terms/announcements for the other 28 provider dividends; independent ex-date/share-basis/entitlement review; review of proposed cash timing | Blocked |
| JPM | Saved raw observations; named common-stock holding and dated ticker crosswalk in the 2016 sources | Cached JPM issuer listing/class history; primary terms/announcements for all 32 provider dividends; independent ex-date/share-basis review; full-period action completeness and proposed cash timing | Blocked |
| CBRE | Saved raw observations and recorded CBG-to-CBRE translation; March 19, 2018 rename in the issuer presentation, filed March 8; Class A source labels in the 2016 and 2020 fund reports | Resolve the 2016 `REIT` classification against independent issuer evidence; full-period listing/action history and explicit dividend-policy evidence rather than treating an empty response as no events | Blocked |
| SPY | Saved raw observations; the cached 2016/2020 reports identify the trust/fund; the 2020 report identifies SPY-listed units; conditional quarterly distribution policy | Continuous fund/listing/split history; complete distribution schedule, dated amounts/ex-dates/payables and applicable distribution types; proposed income-accounting conventions | Both context-signal and total-return benchmark admission remain blocked |

A dated holding is a membership anchor, not certification of every later
alias/class or event. The 2018 Apple listing document cannot be used as
advance evidence in 2017; the 2020 SPY report cannot be used as advance
evidence in 2016. Retrospective documents can corroborate historical facts
without making those facts public earlier than their actual publication.

### CBRE classification finding

The `REIT` marker is present in the **original cached 2016 fund filing**,
not just the extracted CSV. The cached 2020 fund filing shows Class A without
that marker. This does not establish a tax-status change or prove which
classification was correct in 2016. The original register is preserved;
the conflicting classification stays blocked pending issuer evidence.

### CBRE price provenance

The reviewer independently reconstructs 555 old-label candles, the one real
March 19 boundary candle and 1,456 subsequent new-label candles. It compares
all OHLCV values and source labels with the reviewed combined file. Only the
boundary candle's market alias is translated; its original CBG label and
actual values remain recorded. No candle, price or volume is fabricated.

## 2. Event-by-event findings

The [95-row action matrix](research_data/free_data_pilot_actions.csv) contains
**94 provider events** and **one independently documented CBRE rename**.
Each row separates provider fields, corroborated primary terms, proposed
knowledge/payment timestamps, unverified entitlement/credit and missing evidence.

| History | Provider dividends | Other provider events | Provider dividends without payable dates | Cached primary cross-check completed |
| --- | ---: | --- | ---: | --- |
| AAPL | 32 | One forward split | 17 | Four 2020 dividend announcements plus the split |
| JPM | 32 | None returned | 17 | No per-event issuer source cached for this review |
| CBRE aliases | 0 | None returned | 0 | Independent rename; absent from the provider inventory |
| SPY | 29 | None returned | 14 | Fund identity/policy and aggregate reporting, not individual event terms |
| **Total** | **93** | **One split** | **48** | **Six specific event cross-checks, including the rename** |

The four reviewed Apple announcements establish these issuer terms:

| Provider ex-date, not independently certified here | Amount per share | Issuer payable date | Dated issuer announcement |
| --- | ---: | --- | --- |
| 2020-02-07 | $0.77 | 2020-02-13 | 2020-01-28 |
| 2020-05-08 | $0.82 | 2020-05-14 | 2020-04-30 |
| 2020-08-07 | $0.82 | 2020-08-13 | 2020-07-30 |
| 2020-11-06 | $0.205 | 2020-11-12 | 2020-10-29 |

These amounts are **historical contractual terms**, not charges or payments
to/from your account. No holding or investment is simulated in this review.

The February provider record lacks a payable date; the saved January issuer
announcement independently supplies February 13. That repairs one field in
the new evidence matrix only. It does not edit the original response, infer
broker credit, or resolve the other missing primary-source terms.

The provider has payable dates in **45 of 93** dividend rows. An existing
provider payable date is still not primary corroboration or broker-credit
proof. There are 48 provider omissions, with one independently supplied by
the cached Apple announcement; the other 47 are not repaired by this review.
For 89 dividend rows, no complete primary amount/payable/dated-announcement
cross-check has been completed. Apple's 2018 annual filing also discusses
dividend policy retrospectively; it is not a replacement for the missing
event-specific dates or their advance-publication evidence.

### SPY: three quarters to investigate

No dividend record appears in the saved provider response for **2016 Q1,
2018 Q2 or 2023 Q4**. This is an observed inventory gap, not proof of exactly
three missing payments. The fund policy says distributions are conditional;
special or additional distributions can also require review. Do not create
amounts, dates or events from a quarterly pattern or annual aggregate totals.

An eventual late-2023 distribution could have a 2024 payable date. Source
metadata may establish that obligation, but this does not permit reading
2024 prices, crediting cash before the window ends, or extending the reserved
price holdout. Unknown/late credits remain separately disclosed rights.

## 3. Assumptions remain proposed

The action matrix shows the earlier proposal's timing calculations **only
where a dated source supports the necessary inputs**:

- Knowledge bound: second actual exchange open after a date-only announcement.
- Base modeled cash: first exchange open on a New York date after issuer payable date.
- Later modeled cash: five additional exchange opens after that base date.

No timestamp is guessed from `process_date`, and no unknown payable date is
filled from a pattern. The proposed no-credit sensitivity remains a scenario,
not an assertion that a broker withheld cash. All approval/entitlement/actual
broker-credit flags remain false. The ownership adapter's existing evidence
requirements are unchanged. The human-readable proposal still needs your
review before these conventions are used in a performance study.

## 4. Exact next source work

The [bounded collection targets](free_data_pilot_source_collection.json)
define **12 source-discovery targets**, three per history:

| History | Identity target | Action-history target | Dated-terms target |
| --- | --- | --- | --- |
| AAPL | Issuer class/listing anchors across the scope | Complete 2016-2023 dividend/split history | Missing event-specific declarations, independent ex-date/share-basis and payable terms |
| JPM | Issuer common-share/listing history | Complete 2016-2023 dividend/action history | All 32 provider events' dated primary terms and independent ex-date/share basis |
| CBRE | Class A versus imported REIT classification; dated aliases/listings | Annual action/dividend policy and completeness review | Independent coverage supporting absence or presence of other events, not an empty API result |
| SPY | Trust units, ticker and listing continuity | Complete 2016-2023 fund distribution/split schedule | All recorded distributions plus investigation of the three empty quarters; no aggregate-to-per-unit inference |

The machine-readable list names the missing event IDs and allowed primary
domains. Exact document download URLs have **not** yet been established;
they must be discovered and reviewed, not invented. The proposed batch permits
at most **12 public search/open discovery tool calls** and **40 direct public
document GET attempts**, with no automatic retries or unbounded link following.
Tool-call counts do not assert how many internal requests a search service makes.

These are bounds for the **next batch**, not a promise that every gap will be
resolved within them. Stop on payment/access requirements or the limit, record
remaining gaps, and do not buy data or silently expand the search. No new
stock-price requests, account/broker requests or credentials belong in that
public-document batch. It has not been executed by this increment.

## 5. Reproduction and saved evidence

```powershell
python -m backtesting.pilot_qualification --output data/reports/a_fresh_pilot_qualification
```

On Windows this run used `.\.venv\Scripts\python.exe`. Use the separate Pi
environment there; **Pi execution was not checked**. The runner reads only
pinned local files and cannot reproduce this review from a clone that lacks
the ignored saved data. It refuses an existing output directory and changed
input hashes. It does not create a trading client or load `.env`.

- [Review protocol](free_data_pilot_review.json): primary files, checksums,
  literal checks and explicit limits on what each source establishes.
- [Qualification summary](free_data_pilot_qualification_summary.json): input
  and code hashes, per-stream errors/warnings, source checks and readiness.
- [Action matrix](research_data/free_data_pilot_actions.csv): all 95 rows,
  including the independent rename and unapproved proposed timestamps.
- [Source collection targets](free_data_pilot_source_collection.json): the
  next bounded free/public evidence targets; not a downloader configuration.

Detailed report and full original-record action JSON are in
`data/reports/free_data_pilot_qualification_v2`. The first local execution
remains preserved in `free_data_pilot_qualification_v1`; v2 clarifies per-row
missing-evidence labels and separates supported provider events from the
independent rename. The summary pins the final v2 execution and tracked exports.
Old protocols, raw responses, reports and the 506-row register were not changed.

**Executed:** input/source hash checks, raw-payload reconstruction, actual
calendar/OHLCV validation and primary-source term checks. Twelve primary
files and nine declared source checks were revalidated. Numeric CSV/JSON
roundtrips use the documented relative `1e-12` and absolute `1e-8` tolerance.
Volume warnings use a retrospective 10x full-stream positive median; that
quality check is not an entry signal or a causal trading feature.

**Not run:** unit-test suites, strategy performance simulations, ML training,
payment-delay replays or a broader basket backtest. This report does not
relabel the earlier 183-test results as verification of this new audit runner.

**Cost/account activity:** $0 purchases; zero network calls, broker/account
requests, orders, subscription changes or dependency installations. No
2024-2025 prices read. The wider excluded lifecycle cases remain blocked.

## What happens next, and your part

**My work:** perform the bounded free/public source batch above, then update
the same evidence categories with new source files and fresh reports. We
have price files; the next collection is for official company/fund documents.

**Your part now:** no setup, purchase or personal risk-limit change. Before
a performance study uses modeled knowledge/payment timing, review section 3
of the [pilot proposal](free_data_pilot_proposal.md) and explicitly accept or
request changes. That decision does not resolve missing facts, approve a
fixed-2016-basket strategy scope, lower your investment criteria or activate
paper orders. Source collection can proceed without that decision.

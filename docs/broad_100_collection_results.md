# Fixed 100-stock collection: results and remaining evidence

Completed **2026-10-29** using existing historical-data access.
**$0 purchases; no account requests, trades, subscriptions or new backtests.**

## What changed

Implemented [bounded collection](../backtesting/broad_collection.py) and a
separate [offline event review](../backtesting/broad_evidence_review.py).
They reuse the existing credential loader, fixed historical query builders,
candle validator, saved exchange calendar, action parser and hash checks.
No dependency installation or changes to the existing trading code were needed.

The original 100-name roster, 506-row parent register, comparison proposal,
previous experiment/approval, acceptance criteria and source evidence remain
unchanged. The owner authorized **this collection**, recorded in a new
[executable protocol](broad_100_collection_protocol.json). That does not
authorize the proposed 48 strategy attempts or paper activation.

## Actual collection

| Item | Result |
|---|---:|
| Frozen historical candidates retained | 100 / 100 |
| New HTTP GET attempts | 192 / 800 allowed |
| Batches | 5 |
| Newly downloaded raw-price queries | 97 |
| Reused full raw-price streams | 3: AAPL, CBG/CBRE, original UA Class A |
| New company-action queries | 95 |
| Candidates with reused provider action queries | 5 |
| Raw candle observations checked | 188,191 |
| Newly collected candle observations | 182,155 |
| Full 2016-2023 raw calendars observed | 83 |
| Partial calendars observed | 17 |
| Empty histories | 0 |
| Provider event records inventoried | 2,463 |
| Candidates with non-cash provider events | 29 |
| Saved primary-source files hash checked | 19 |
| New public-company document requests | 0 |
| Newly admitted stocks / strategy runs | 0 / 0 |

The final request started about **141 seconds** after acquisition began.
All requests returned saved payloads; no access/transport stop occurred.
Batch attempts were **44, 46, 46, 48 and 8**. Original response bytes and
checksums are saved. No resource needed another page in this actual batch.

Only the fixed historical bars and corporate-action GET endpoints were used.
Bars use **SIP, raw, daily, asof=-, USD, 2016-01-01 inclusive through
2024-01-01 exclusive**. No 2024-2025 candles were requested or read. JPMorgan
remains parked. There were no extra successor/alias probes, retries,
redirects, feed substitutions, paid fallbacks or account/billing calls.

## What passed, and what coverage does not establish

All 100 returned price streams passed the structural and saved-calendar
checks: timestamps/timezones, duplicates, positive finite prices, OHLC
relationships, nonnegative volume and scheduled daily timestamps. No hard
price-validation error was recorded. CSV observations were compared with the
reconstructed frames; saved payload/source hashes were checked.

There are **no unobserved exchange sessions between each stream's first and
last observed candle**. The 17 partial streams all stop before the end of
2023. This is not a claim that their trailing dates are missing candles:
renames, mergers, delistings and symbol reuse require dated evidence. No
prices were fabricated, filled, spliced to a guessed successor or replaced
with adjusted prices. Sixty-one streams have volume warnings, separate from
hard errors; the warnings are preserved in the inventory.

**83 complete calendars does not mean 83 approved company histories.** A
vendor can return apparently continuous candles for a reused ticker. All
100 candidates remain unapproved for this broader scoring scope.

### Partial observations requiring lifetime/alias review

Every row below begins on 2016-01-04. These are observed vendor aliases,
not approved security lifetimes or exit dates.

| Snapshot alias | Observations | Last observation |
|---|---:|---|
| RTN | 1,070 | 2020-04-02 |
| FB | 1,620 | 2022-06-08 |
| CBS | 988 | 2019-12-04 |
| BLL | 1,599 | 2022-05-09 |
| FISV | 1,869 | 2023-06-06 |
| DLPH | 1,196 | 2020-10-01 |
| MYL | 1,228 | 2020-11-16 |
| XL | 1,729 | 2022-11-11 |
| ESRX | 748 | 2018-12-20 |
| CTL | 1,186 | 2020-09-17 |
| LLL | 1,704 | 2022-10-07 |
| BHI | 378 | 2017-07-03 |
| RHT | 883 | 2019-07-08 |
| SYMC | 967 | 2019-11-04 |
| NLSN | 1,706 | 2022-10-11 |
| CSRA | 566 | 2018-04-03 |
| MON | 1,758 | 2022-12-23 |

## Company-event evidence: what is still missing

The provider inventory contains **2,421 cash dividends**, 13 forward splits,
six stock mergers, ten name changes, six reverse splits, five cash mergers
and two spin-offs. Query results are not automatically events belonging to
our historical share class; ownership and affected issuer must be reviewed.

- **1,334 dividend records have no provider payable date.** Ex/process dates
  do not establish when cash becomes spendable. Prior supported primary terms
  and diagnostic assumptions are preserved, not automatically extended.
- **All 2,421 provider dividend records lack announcement/declaration dates.**
  This is a provider-field gap, not proof that no public declaration exists.
  Historical availability cannot be certified from these records alone.
- **21 daily close changes of at least 40%** are flagged for investigation.
  These include possible splits, distributions, identity problems and actual
  moves. The threshold does not label them all errors or adjust any price.
- **XL and LLL have incoming-alias flags:** the saved provider records report
  PIC entering XL in December 2020 and KBSF entering LLL in October 2021.
  Those observations require independent issuer-continuity/reuse review;
  neither returned stream is attached wholesale to the 2016 issuer.
- The earlier primary evidence for Under Armour's class distributions/rename
  and CBRE's rename is retained with unresolved execution terms. An empty
  action query cannot erase these known events. Prior AAPL/CBRE admission
  remains limited to the completed two-stock diagnostic assumptions.

There is now an explicit [review task record for every selected stock](research_data/broad_100_event_review_targets.json),
including its coverage boundaries, event categories, missing terms and
investigation priorities. These are saved-data review tasks, **not** an
unbounded document crawler or authorization for additional downloads. No
stock was dropped or replaced because its history is difficult.

## Reproduction, safeguards and practical limits

Tracked artifacts:

- [Executed protocol and frozen queue](broad_100_collection_protocol.json).
- [Collection/qualification summary](broad_100_collection_summary.json).
- [All 100 collected statuses and blockers](research_data/broad_100_collected_inventory.csv).
- [Event evidence summary](broad_100_evidence_summary.json).
- [Per-stock remaining review tasks](research_data/broad_100_event_review_targets.json).
- [Position-count preference](broad_position_count_preference.md).

Original payloads, derived CSVs, complete event records, price-move flags and
execution ledger live in ignored `data/reports/broad_100_collection_v1`.
Keep that directory and the older pinned sources for reproduction. Git does
not transfer them to the Pi. Requests contain secrets only in memory; reports
do not include credentials, headers, raw HTTP error bodies or access tokens.

The fixed one-shot journal is
`data/reports/broad_100_collection_execution.json`. Collection refuses to
restart this protocol, overwrite its output or reset its allowance in a new
folder. Any future acquisition needs a separate reviewed scope/budget. Do not
delete the journal to retry. The global cap is cumulative, with four pages per
resource, 24 candidates/192 attempts per batch, 60/15-minute global/batch limits,
30-second socket timeouts, 8 MB page limits and 0.4-second request spacing.
Access/payment/rate denials, redirects, server or transport failures stop the
whole acquisition. Unsupported-query 400/404/422 responses stay explicit gaps.

Offline replay, from the repository root with its own environment:

```powershell
.\.venv\Scripts\python.exe -m backtesting.broad_collection qualify
.\.venv\Scripts\python.exe -m backtesting.broad_evidence_review
```

On the Pi, use its own environment's `python` and retained source files. All
artifact paths are repository-relative. **Windows execution only** has been
checked; Pi execution remains unverified.

This increment ran actual collection, source/data validation and request-budget
checks. **No unit-test suite was added or run.** Successful live responses do
not test denial/transport stops, corrupt pagination, timeout interruption or
interrupted-process recovery. Those need focused offline tests before relying
on the collector for another acquisition.

## What happens next, and whose work it is

**My work:** focused offline collector/qualifier tests, then a bounded evidence
resolution plan prioritizing the 17 partial histories, incoming aliases and
material distributions/mergers. The aim is supported issuer/alias intervals
and actual share/cash outcomes, with an explicit list of any assumptions we
would need for a development diagnostic. No further purchases are planned.

Before new performance runs I will present the concrete expanded input and
assumption package, plus any amendment for holding more than seven stocks.
The 35% total-exposure cap is a separate choice; it has not changed. A count
change must not be hidden in a comparison described as changing universe size
only. No promise of improved returns or a paper start date follows from these
downloads.

**Your part now:** nothing to configure, install or buy. Later, review that
concrete package before expanded performance runs. Personal paper-risk limits,
the investment acceptance gate and final paper activation remain separate.

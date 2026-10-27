# Public-document collector and parser verification

Date: 2026-10-27. **99 tests passed; zero failures, errors or skips.**

## What ran

| Verification | Result |
| --- | --- |
| New collector tests | 17 passed |
| New HTML/XLSX parser and reconciliation tests | 40 passed |
| Existing related source, historical-holdings, raw-action-pilot and evidence tests | 42 passed |
| Combined focused run | **99 passed** |
| Saved-document reconciliation replay | CSV and JSON match the prior results **byte for byte** |
| Unmocked socket connection attempts | **Zero** |

New tests use synthetic HTML/workbooks, temporary directories and mocked HTTP
responses. Real socket connections are forbidden in these fixtures and the
combined test run. The saved-document replay reads only pinned local files;
it does not resume the stopped source collection. No `.env`, account state,
market-price endpoint or broker submission is needed.

The tests are portable and require no ignored historical data. The separate
saved-source replay needs the pinned local documents from the preceding
collection. This execution used the Windows Python 3.12 environment; Pi
execution and the complete project/optional-ML suite were not run.

## Coverage and fixes

Negative tests initially exposed input-validation and reconciliation gaps.
Those cases now pass with the following behaviour:

- **Request bounds:** accept integer limits from 1 through 40; reject boolean,
  fractional, negative, zero and excessive limits before creating a session.
  Purchase budgets must explicitly be numeric zero. Empty/duplicate/over-budget
  queues and missing target metadata are rejected before the first request.
  Duplicate filenames are compared without case, so `first` and `FIRST`
  cannot overwrite each other on Windows while appearing distinct on Pi.
- **Public URL/file controls:** require reviewed HTTPS domains, reject user
  credentials, ports, fragments and missing hosts. Prevent path traversal and
  Windows reserved filenames. No automatic redirects, retries or ambient
  authentication. Test successful raw-byte preservation, hash logging,
  timeouts, inter-request spacing, response signatures and the 16 MB cap.
- **Access stops:** mocked 401, 402, 403, 407 and 429 responses each stop before
  the next request. A 404 or transport failure is recorded once. A redirect is
  recorded for review without following its destination. Sessions close and
  partial oversized documents are not saved.
- **Source formats:** verify Apple table headings and SPY workbook column
  meanings. Reject missing/duplicate source rows, unsupported distributions,
  altered/duplicate known splits, wrong fund identity and malformed or
  oversized workbooks. Unsupported workbook formats fail clearly rather than
  leaking a low-level ZIP/member exception.
- **Amounts and dates:** reject nonfinite, zero/negative amounts and impossible
  declaration/ex-date/record/payment ordering. Restrict event selection to
  the declared development years. A genuine later payable date remains
  metadata: a 2023 event can retain its 2024 payment date without reading
  2024 prices or crediting cash in the earlier window.
- **Provider joins:** reject missing/duplicate provider IDs, incomplete
  pagination, ambiguous joins and conflicting record/payment dates. Validate
  events even outside the small explicitly matched JPMorgan subset.
- **Precision:** exact matches retain zero exact difference. Differences
  within half the source's last displayed decimal unit remain explicit,
  unapproved warnings; larger differences are hard errors. This prevents a
  substantive amount conflict from being mislabeled as display precision.
  The threshold does not prove rounding, select a ledger amount or approve
  performance use. Blank capital-gain cells remain blank.
- **Provenance:** recorded request counts must equal logged attempts; discovery
  counts must match saved discovery records and remain within the cap. Check
  queue hashes, archived executed-collector hashes and saved-response hashes
  against the reviewed source catalog. Reject collection after an earlier
  barrier, or a final access denial not marked stopped.
- **Evidence preservation:** changed input hashes, escaping paths or existing
  output directories are rejected. Source and cash assumptions remain
  unapproved; no test converts issuer payable terms into broker-credit proof.

The frozen archived collector describes the earlier acquisition version.
Its logs are compared with that archived version, not relabeled with today's
code hash. The current collector/parser versions are recorded separately.

## Saved-source regression

The hardened review still produces exactly the preceding 66 reconciliation
rows: **32 Apple, 32 SPY and two JPMorgan declarations**. It retains the three
source-only SPY events, one exact amount-precision warning and **16 unresolved
original payable-field omissions**. Scoring and broker-credit approval remain
false. No original source responses, protocols, reports or CSVs were rewritten.

Fresh local evidence:

- `data/reports/public_source_unit_verification_v2`: final 99-test log, counts,
  code hashes, environment and connection guard result.
- `data/reports/public_source_test_replay_v2`: final offline source replay.
- [Tracked verification summary](public_source_test_summary.json): hashes,
  exact comparisons, scope and limitations.

The first negative-test execution is retained separately in
`data/reports/public_source_tests_initial_v1`; it records findings before fixes,
not the final pass result.
Earlier v1 verification/replay outputs also remain preserved; v2 includes
the final Windows filename-collision rejection case.

## Reproduce

From the repository root with its environment active:

```powershell
python -m unittest tests.test_public_document_collection tests.test_public_source_review tests.test_raw_action_pilot tests.test_historical_holdings tests.test_ownership_evidence_review tests.test_universe_sources
python -m backtesting.public_source_review --output data/reports/a_fresh_verified_source_replay
```

On Windows this run used `.\.venv\Scripts\python.exe`. On Pi use that machine's
environment. Do not rerun the downloader to reproduce an offline test.

**Cost and activity:** $0 purchases; zero real network requests, downloads,
broker/account calls, orders or dependency installations. No reserved prices
were read. Mocked response counters in tests do not represent actual HTTP calls.

## Next work and your responsibility

**Execution update:** the [single JPMorgan follow-up](jpm_dividend_followup_results.md)
has now stopped at its discovery cap, with one newly archived declaration.
Remaining JPMorgan collection is parked as the owner authorized. My next work
is qualification of the remaining pilot histories from cached evidence; no
further JPMorgan collection is scheduled. This execution did not rerun tests.

**Preceding plan:** the [separate JPMorgan plan](jpm_dividend_followup_plan.md)
prepared one attempt capped at four discovery
calls, eight direct document GETs and ten minutes on the main issuer site;
current access is not yet verified. The consolidated-history HTTP 403 stays
recorded, and that host is excluded. If gaps remain, park JPMorgan's active
engineering-pilot work as the owner requested and continue other pilot
histories. Original historical membership and strategy controls stay intact.
Remaining ex-date, full-period identity/action and precision-policy gaps stay
visible; narrower performance scope is a separate review.

**Your part now:** no configuration, purchase or personal risk-limit decision.
Before a new performance study uses modeled knowledge/payment timing, review
section 3 of the [pilot proposal](free_data_pilot_proposal.md). That approval
does not supply missing source facts or approve a changed strategy universe.
Paper activation remains separate.

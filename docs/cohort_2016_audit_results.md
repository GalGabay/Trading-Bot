# Historical stock identity and saved-data audit — no purchases

Updated 2026-10-24. **New purchases: $0. Broker requests: 0. Orders: 0.**

## First: what the earlier $9.69 meant

The earlier Apple figure was **simulated dividend income in an offline
historical calculation**. It was not a fee, bill, withdrawal, deposit or actual
dividend payment to this account. The example used imaginary starting cash
and historical prices; it placed no live or paper order. “Real-data pilot”
meant the input candles came from historical observations, not that money
was invested. The wording has been clarified in the pilot report.

The owner requires this work to incur **no new data or service charges**.
Use saved files and freely accessible public sources. Do not buy data,
start paid trials, subscribe, upgrade an account or treat a failed free
download as permission to pay. No payment card or billing access is needed.

## What this increment did

The new command `backtesting/cohort_audit.py` runs **entirely offline**. It
reads reviewed snapshots and existing local candles; it has no HTTP client,
broker client, credential loading, trading loop or package-installation step.
Source acquisition for this increment used unauthenticated public issuer/SEC
downloads, with bounded GET requests and no login/payment action.

### Dated ticker identification for every retained holding

All **506 original September 2016 SPY holdings remain in the register**:

- **449** link uniquely after declared name/footnote cleanup, corroborated
  against prices in the two funds' holdings on the same historical date.
- **56** need explicit reviewed name/share-class pairs, preserved in the
  [name crosswalk review](research_data/spy_2016_name_crosswalk_review.json).
  No fuzzy score automatically assigns a ticker.
- **1** is Dell's Class V tracking stock, **DVMT**, corroborated separately
  by its [2016 SEC filing](https://www.sec.gov/Archives/edgar/data/1571996/000119312516706567/d238698d8k.htm).
  It is absent from the corroborating fund's equity list, is retained, and
  is flagged as an unsupported tracking class.

The corroborating source is the issuer's free
[IVV historical holdings download](https://www.blackrock.com/varnish-api/blk-one01-product-data/product-data/api/v1/get-fund-document?appType=PRODUCT_PAGE&appSubType=ISHARES&targetSite=us-ishares&locale=en_US&portfolioId=239726&userType=individual&asOfDate=20160930&component=holdings).
Its internal date is verified as **September 30, 2016**. It supplies 505 equity
rows plus four cash/derivative rows, which are reported separately and not
treated as stock identities. All 505 equity rows are accounted for in the
crosswalk. Each corresponding one-date price agrees within the declared
1.5-cent tolerance. This comparison checks identity; it does not select stocks
by future returns.

A legacy download URL returned HTML despite a CSV content type. That response
was rejected, preserved as evidence, and never treated as a 2016 holdings file.
Malformed rows, duplicate tickers, changed hashes, a wrong historical date,
ambiguous names or inconsistent prices block the audit.

The full [506-row dated alias CSV](research_data/spy_2016_dated_aliases.csv)
is tracked in Git, along with the [audit summary](2016_cohort_audit_summary.json)
and [source/evidence review](2016_cohort_source_review.json). Original security
names and source row keys are preserved. Local `COHORT-2016-...` IDs identify
these retained rows; they are not claimed to be permanent market identifiers.

**A ticker identified on one date is not a verified eight-year ticker history.**
The IVV file is a retrospective historical source with no certified original
publication timestamp. Membership availability remains anchored to the
earlier SEC filing review; this download does not create an invented 2016
`known_at` timestamp. Every row remains `ready_for_simulation: false` until
its required identity, price and action evidence is complete.

### Ten sourced event cases

| Retained holding | Sourced event | Why it matters |
| --- | --- | --- |
| Under Armour Class A and Class C (two rows) | December 7, 2016 ticker changes | Class A becomes UAA; UA then refers to Class C. The same letters must not join two classes into one price history. |
| CBRE Class A | March 19, 2018 CBG → CBRE | A dated rename must preserve the original security identity. |
| Original Alcoa | November 1, 2016 separation | Original Alcoa becomes Arconic; the new Alcoa uses AA. A reverse split also affects warmup. This is not one continuous AA identity. |
| Original Twenty-First Century Fox Class A and B (two rows) | March 19, 2019 distribution/ticker reuse | New Fox receives FOX/FOXA; original 21CF moves to TFCF/TFCFA before the Disney transaction. Treating today's FOX history as the old company is unsafe. |
| Aetna | November 28, 2018 cash-and-stock acquisition | Successor shares and fractional cash cannot be replaced by a made-up cash sale. |
| Level 3 | November 1, 2017 cash-and-stock acquisition | The same unsupported mixed consideration problem applies. |
| Whole Foods | August 28, 2017 cash acquisition | Closing/consideration are corroborated, but cash availability must still be established. |
| Original Bed Bath & Beyond | September 29, 2023 equity cancellation | Cancellation without value is explicitly sourced, not inferred from a missing quote. OTC/suspension history still needs review. |

Evidence comes from dated issuer announcements and filings:
[Under Armour](https://www.prnewswire.com/news-releases/under-armour-announces-change-of-class-a-and-class-c-ticker-symbols-300368197.html),
[CBRE](https://www.sec.gov/Archives/edgar/data/1138118/000156459018004821/cbg-ex991_6.htm),
[Alcoa separation](https://www.sec.gov/Archives/edgar/data/4281/000119312516760946/d487729dex991.htm),
[Fox distribution](https://www.sec.gov/Archives/edgar/data/1308161/000119312519079034/d721340d8k.htm),
[Aetna](https://www.sec.gov/Archives/edgar/data/64803/000119312518336591/d650950d8k.htm),
[Level 3](https://ir.lumen.com/news/news-details/2017/CenturyLink-completes-acquisition-of-Level-3/default.aspx),
[Whole Foods](https://www.sec.gov/Archives/edgar/data/865436/000114420417045261/v474128_8k.htm),
and [Bed Bath & Beyond](https://www.sec.gov/Archives/edgar/data/886158/000119312523247428/d579010d8k.htm).
The [2016 Fox filing](https://www.sec.gov/Archives/edgar/data/1308161/000156459016023961/fox-10k_20160630.htm)
also corroborates the original share classes.

These are reviewed **event candidates**, not a complete history of company
events. Exact historical knowledge bounds, payment availability and some
listing boundaries remain unresolved. No event is auto-promoted into the
simulator. Unsupported spin-offs, stock mergers and uncertain quote gaps stay
visible. Failed/blocked additional public downloads are recorded in the source
review; no purchase or login was used to bypass them.

### Audit of the prices already on disk

The command checked **33 saved daily-price files** against their saved hashes
and market calendar. The calendar has **2,012 actual sessions** over 2016–2023,
including warmup. No new candles were downloaded in this increment.

| Saved-data finding | Count | Meaning |
| --- | ---: | --- |
| Cohort rows with candidate raw observations | 1 | Apple has 505 raw daily observations from the earlier accounting pilot, covering only 2019–2020. |
| Cohort rows with candidate adjusted observations | 14 | Other saved studies/probes provide some adjusted history, not certified raw/action-aware input for this broader run. |
| Cohort rows with complete raw calendar coverage | 0 | The required broader raw dataset is not already on disk. |

Coverage counts are observations under candidate tickers, **not proof that
each quote belongs to the right historical security**. In particular, a ticker
rename/reuse needs identity review before series can be attached. Full calendar
coverage is a data-inventory diagnostic, not a requirement to invent candles
after a genuine delisting. Listing lifetimes and independently sourced outcomes
must explain those intervals in an executable universe.

No missing prices were fabricated, forward-filled, silently removed or
turned into assumed zero-value outcomes. The command excludes manifests
outside the permitted pre-2024 window before opening their candles. The
reserved 2024–2025 candle datasets remain untouched.

## Reproduce the audit

From the repository root, with the original saved inputs retained:

```powershell
.\.venv\Scripts\python.exe -m backtesting.cohort_audit --output data/reports/a_fresh_2016_cohort_audit
```

This command needs **no API keys or internet access**. It refuses to overwrite
an existing output directory. Full evidence is in
`data/reports/cohort_2016_audit_v3/`: report, complete cohort JSON/CSV, event
candidates and checked-price inventory. Earlier v1/v2 outputs are preserved
as intermediate evidence; old source hashes are not rewritten. Public source
downloads are in `historical_mapping_sources_v1`. On another machine those
local snapshots must be copied separately or reacquired/reviewed; they are
not bundled with the Git repository.

The actual audit completed with all four declared integrity checks passing.
Python compilation and diff checks passed. **No unit tests were added or run
in this increment**; this was the requested source/coverage audit, not another
strategy simulation. Earlier test totals belong to their earlier increments.
Windows execution is recorded; Raspberry Pi execution remains unverified.

## What comes next, and who does it

**Codex:** prepare a bounded, reproducible no-purchase raw-price/action
acquisition plan for the retained cohort. Prioritize a small set representing
ordinary stocks, renames, cash acquisitions, stock acquisitions and spin-offs;
finish evidence/adapter gaps before scaling. Any use of account-based data
must stay within existing access, with no subscription/payment change. A
denied or unavailable source is a recorded gap, never permission to pay.
Do not label an incomplete survivor-only subset a validated broad universe.

The broader entry/ranking study remains unscored. This increment does not
demonstrate improved investment returns. Before performance scoring, freeze
the feasible scope and disclose any departure from the original full-market
proposal. Paper activation and personal paper-risk settings remain separate.

**Owner:** no card, data purchase, manual ticker collection or risk JSON edit
is needed for the next engineering step. Optional ML dependency installation
is unrelated to this audit and is not needed to continue it.

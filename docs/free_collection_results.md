# Free historical collection and company-event review

Updated 2026-10-24. **New purchases: $0. Subscription changes: 0. Orders: 0.**

## What actually ran

The [frozen collection plan](free_collection_plan.json) defined 24 ticker/date
intervals before any new price request. These deliberately cover ordinary
stocks, renames, acquisitions, spin-offs and a bankruptcy. They are engineering
cases, not stocks chosen by future profit. The 506-stock register remains
intact; this sample does not replace it with survivors.

We collected **23,747 raw daily candles** and recovered **one additional
observed CBRE boundary candle**, for **23,748 observations**. There were
**46 historical-data GET requests**: 24 initial price requests, 21 distinct
symbol-level company-event queries and the one boundary request. Reused symbol
event responses were read from the saved files, not requested again. These
counts exclude the separate free public issuer/SEC document downloads.

The event inventory contains **249 unique provider event records**:
239 cash dividends, one forward split, two cash mergers, four name changes
and three reverse splits. These are unverified provider records to review,
not 249 approved simulation events.

No account balances/positions were queried, no order was submitted, no
package installed, and no plan upgrade, paid trial or purchase occurred.
Existing credentials were used only for the allowlisted data GET endpoints.
We did not inspect or certify the account's billing/subscription status.

## How collection prevents accidental spending or trading

`app/broker/research_client.py` is a separate GET-only historical transport.
It reuses the existing central credential loader without creating a trading
client. Its only allowed paths are the stock-bars and corporate-actions
endpoints on `https://data.alpaca.markets`.

- No account, order, billing, subscription or endpoint-override operations.
- No redirects, automatic retries, automatic paid upgrades or feed fallback.
- At most 192 actual HTTP attempts per run, with at least 0.4 seconds between
  starts, a 30-second timeout, and an 8 MB response-page limit.
- Authentication/entitlement/rate denial stops further collection rather than
  trying to change access. Other failures remain recorded source gaps.
- Fixed raw daily SIP bars, USD, 2016-2023 only. Reserved 2024-2025 candles
  cannot enter this transport.
- Saved raw pages, checksums, bounded pagination and structured failures.
  Credentials, headers and HTTP error bodies are not written to reports.

Alpaca documents Basic as a free default plan, with history since 2016 and
200 historical requests/minute; its recent-data restriction is irrelevant
to this pre-2024 collection. Existing entitlement is used as-is, never changed
([official plan documentation](https://docs.alpaca.markets/us/docs/about-market-data-api)).
This work incurred no new data/service purchases. It does not authorize any
future paid service if a free source becomes unavailable.

## Important ticker control

Bars explicitly request **`asof="-"`**. The API's default mapping can otherwise
return earlier ticker history under a later name. With mapping disabled,
each observed ticker interval stays separate until independently reviewed
([official historical-bars documentation](https://docs.alpaca.markets/us/reference/stockbars)).

For example, Under Armour Class A's old UA history stops before December 7,
2016; Class A then uses UAA, while UA refers to Class C. Old/new Alcoa,
Arconic and Fox likewise remain separate identities or branches. This avoids
silently concatenating different investments because their ticker letters
match. Bar labels alone do not certify full historical identity.

## Gaps resolved with actual evidence

### 1. Under Armour Class C: 66 absences explained

The old Class C response starts on **April 8, 2016**. Its 66 absent earlier
calendar sessions all precede that date. The issuer's
[2016 annual filing](https://www.sec.gov/Archives/edgar/data/1336917/000133691717000017/ua-20161231x10k.htm)
confirms Class C's issuance/trading boundary. The earlier
[March 16 announcement](https://www.prnewswire.com/news-releases/under-armour-announces-class-c-stock-dividend-300237041.html)
describes the new class distribution and intended UA.C listing.

These are pre-issuance absences, not 66 candles to fabricate. The observed
Class C alias stream has **1,946 sessions** from April 8, 2016 through 2023,
with no unexplained session gap over that reviewed interval. Class A's
separate observed alias stream has **2,012 sessions** over 2016-2023.

Their raw histories still need the documented class-distribution accounting
or explicitly reviewed warmup boundaries. The provider returned no actions
for these ticker queries despite the primary evidence. In particular, the
June 2016 additional Class C distribution is not assumed away.

### 2. CBRE: an actual candle recovered at the rename

The new CBRE response began March 20, 2018, leaving March 19 unobserved under
that label. A separately declared one-day query found the **real March 19
candle under CBG**, the vendor's old label. The
[dated issuer filing](https://www.sec.gov/Archives/edgar/data/1138118/000156459018004821/cbg-ex991_6.htm)
confirms the rename effective March 19.

The offline reviewer translates only that observed candle's market alias
to CBRE, records `source_symbol: CBG`, and preserves its original OHLCV and
timestamp. No price or volume is invented. The combined reviewed CBRE stream
now has **2,012 observed sessions**. Original responses/files remain unchanged;
the translated stream and its evidence journal are separate outputs.

### 3. Bed Bath & Beyond: Nasdaq boundary established

The listed-ticker response ends May 2, 2023. The company's
[April 25 suspension filing](https://www.sec.gov/Archives/edgar/data/886158/000119312523115523/d89202d8k.htm)
states that Nasdaq trading would be suspended at the May 3 open. This explains
the 104 later sessions in the requested listed-ticker interval; they are not
assumed to be ordinary missing Nasdaq candles.

The BBBYQ query returned a **genuine empty response**. The OTC history,
valuation after suspension, and eventual cancellation remain unresolved.
The separate sourced September cancellation does not justify marking the
holding worthless in May, inventing a sale, or carrying a stale quote to
September. Bankruptcy cases stay visible and blocked.

## Company-event completeness: a substantive remaining problem

The reviewer checks **11 independently sourced required events** against the
provider inventory. **Ten have no matching effective/ex-date record in the
queried API responses.** Only the selected ATVI merger has a corresponding
provider entry in this cross-check. This does not mean only one company event
exists; the primary sources establish the omitted events independently.

Missing matches include Under Armour's distributions/rename, CBRE's rename,
the Whole Foods merger, Aetna/Level 3 mixed acquisitions, and the Alcoa,
Arconic and Fox distributions. Source evidence is retained for each.
The [ATVI SEC filing](https://www.sec.gov/Archives/edgar/data/718877/000110465923108985/tm2328253d1_8k.htm)
also resolves a previously unavailable primary-source download through the
original public SEC document, without purchasing access.

**Do not turn an empty or incomplete event response into an event-free
manifest.** Alpaca itself does not guarantee when corporate actions become
available; processing dates are not announcement timestamps
([official action endpoint documentation](https://docs.alpaca.markets/us/reference/corporateactions-1)).

The reviewer also quarantines **77 event references whose effective/ex-date
falls outside the particular alias price interval**. These are references,
not 77 distinct events. They remain in the original evidence. For example,
an ARNC symbol query returns a 2023 acquisition of the newer Arconic company;
that payment cannot be attached to the old company, which became Howmet.

The API's apparent fractional “reverse split” entries at certain distribution
boundaries must not be blindly converted into position share counts. Primary
evidence describes different companies/branches, including the
[2020 Arconic/Howmet separation](https://www.sec.gov/Archives/edgar/data/1790982/000110465920043138/tm2014707d1_ex99-2.htm).
The current split adapter supports genuine split ratios, not replacement of
a spin-off with a generic fractional multiplier.

## Publication dates and cash availability

Seven publication reviews now have dated source evidence. The research
convention is two calendar days after the dated release/filing, then the first
saved exchange-session open. It is a conservative availability convention,
not proof of an exact historical release timestamp or broker credit time.

Under that convention, both Under Armour class renames, CBRE's rename and
the Nasdaq suspension have advance evidence. Same-day merger/distribution
filings and the late September cancellation do not establish knowledge at
that morning's open. Those timing gaps remain blocked instead of backdating
knowledge. Intraday SEC acceptance strings were preserved but not silently
converted into exact public release timestamps.

Cash-availability convention remains **unset** in this review. An issuer
payable date is not proof of spendable broker cash. Terminal cash rights,
successor shares, fractional claims and suspension-period valuation need
explicit evidence and supported accounting before strategy scoring.

## Reproduce and inspect

From the repository root on Windows:

```powershell
# Network: GET-only historical collection using existing credentials.
.\.venv\Scripts\python.exe -m backtesting.free_collection --output data/reports/a_fresh_free_collection

# Offline: review the pinned original collection and primary evidence.
.\.venv\Scripts\python.exe -m backtesting.event_gap_review --output data/reports/a_fresh_event_review
```

Both commands require a new output directory. The first freezes the plan in
that directory before requesting prices. To review a different collection,
prepare a separate source review pointing to its hashes; do not rewrite an
old review/report to accept new data. Existing sources/calendar snapshots
must be copied or reacquired/reviewed separately on another machine.

Artifacts:

- [Frozen collection plan](free_collection_plan.json).
- [Event/source review](free_collection_event_review.json).
- [Tracked results summary](free_collection_summary.json).
- `data/reports/free_collection_v1/`: raw pages, original CSVs, reports and
  an archived copy of the actually executed collector.
- `data/reports/free_collection_evidence_v1/`: new primary documents/indexes.
- `data/reports/cbre_boundary_v1/`: declared boundary query and real response.
- `data/reports/free_collection_review_v1/`: reviewed alias streams, label
  translation journal, event inventory, quarantine and gap report.

The original run displayed reused action responses as “downloaded” and
classified the empty OTC result as an empty-candle validation error. The
collector now labels reuse/empty responses explicitly. The offline review
correctly reconciles the original saved evidence to **21 distinct action
queries and an empty OTC response**. No old report or source hash was edited.

The actual collection and offline source/calendar review completed. Python
compilation and diff checks passed. No unit tests or strategy performance
simulations were added/run in this increment. Windows execution is recorded;
Raspberry Pi execution remains unverified. Raw market data stay ignored by
Git, credentials remain local, and 2024-2025 candles remain reserved.

## Next work and owner responsibilities

The collection workflow now exists and has run. Next engineering work is
**corporate-action accounting with delayed claims and branches**: terminal
cash rights that are not yet spendable, mixed cash/share acquisitions,
spin-off ownership, fractional claims and a documented valuation policy.
Before scaling, validate these against the representative saved cases and
review the remaining dividend/publication evidence. Unavailable OTC/history
sources remain explicit blockers; no paid source or plan upgrade is a fallback.

Broader strategy results remain unscored. No claim of improved investment
returns or readiness for paper trading follows from this data collection.
The owner has no card, purchase, manual download or risk JSON task now.

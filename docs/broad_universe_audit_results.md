# Broad-universe feasibility audit: completed results

Executed on Windows on 2026-10-24. This is a **data-feasibility audit**, not a
new profit backtest. The earlier trading simulations are backtests: they
apply historical signals, execution rules, cash constraints and costs to
past observations. Research choices made after seeing results remain
development research, not independent confirmation.

## What was actually fetched

Following the [registered protocol](broad_universe_audit_protocol.md):

- Alpaca's complete returned US-equity catalog, without an active-only filter.
- Both public Nasdaq current symbol directories: 5,625 Nasdaq-listed and
  7,674 other-listed rows. Their file creation footers say 2026-10-23 21:31.
- Alpaca's actual **2,012 exchange sessions** in 2016-2023.
- All pages of SIP/all-adjusted daily bars for **56 preselected symbols**,
  from 2016-01-01 through 2024-01-01 exclusive. No 2024-2025 bars were fetched.

No account balances, positions or order endpoints were needed. No trades,
subscription purchases, package upgrades or risk-setting changes occurred.

## Catalog findings

| Observation | Count |
| --- | ---: |
| Catalog asset records | 33,560 |
| Active / inactive records | 14,398 / 19,162 |
| Active and currently tradable records, all returned exchanges | 13,504 |
| Active and tradable on the five sampled exchanges | 13,187 |
| Ticker strings appearing in more than one catalog record | 257 |

These are **asset records, not a count of ordinary common stocks**. The
catalog includes ETFs, warrants, preferred securities and OTC entries. It
contains current IDs/status/tradability, but no dated listing/delisting
intervals or historical common-stock classification. The 257 repeated
symbols are concrete evidence that grouping everything by ticker alone is
unsafe; they do not by themselves prove which records are reused tickers.

The current Nasdaq flags identified 18 sample symbols as ETFs and 25 as
non-ETFs; 13 sample symbols had no exact directory match. Non-ETF does not
establish common-stock status. Directory spelling differences, ended
securities and missing classifications need explicit identity handling.

## Coverage findings

| Fixed sample | Full 2,012-session coverage | Partial history | Empty response | API rejection |
| --- | ---: | ---: | ---: | ---: |
| 40 active/tradable probes | 14 | 12 | 14 | 0 |
| 8 inactive probes | 0 | 0 | 7 | 1 |
| 8 explicit lifecycle probes | 1 | 7 | 0 | 0 |
| **Total: 56** | **15** | **19** | **21** | **1** |

The final execution downloaded **49,538 bars**, about **3.21 MB** of CSVs,
in **38.266 seconds** including setup/catalog/directory work. This measures
one small daily-bar sample on the development PC, not a market-wide or Pi
capacity benchmark. Snapshot JSON storage is additional. Single-symbol
probes do not establish large-batch throughput or rate-limit headroom.

All 34 nonempty histories passed the reused timestamp, duplicate, OHLC,
price, volume-sign and calendar-boundary hard checks. Warnings remain:
29 histories have volume-anomaly warnings, ten have zero-volume warnings,
and 19 have unobserved scheduled dates. Counts are affected histories, not
anomalous rows. The one rejected inactive identifier is `617990809`
(HTTP 400); it remains in the report rather than being replaced.

**Do not interpret 15/56 as market coverage or a failure rate.** Many sampled
current products did not trade throughout 2016-2023. Seven inactive probes
are currently OTC entries, and the requested feed was SIP, not OTC. The
active sample also contains newer funds and non-common securities. Their
empty/partial histories need lifecycle classification; they are not proof
of corrupt bars or poor investment performance. No performance was scored.

### Why lifecycle and identity matter

| Probe | Observed historical span | Observation |
| --- | --- | --- |
| META | 2016-01-04 to 2023-12-29 | Full history under default current mapping |
| FB | 2016-01-04 to 2022-06-08 | 392 later sessions have no bars under this requested ticker |
| TWTR | 2016-01-04 to 2022-10-27 | 294 later sessions without bars |
| ATVI | 2016-01-04 to 2023-10-13 | 53 later sessions without bars |
| SIVB | 2016-01-04 to 2023-03-09 | 204 later sessions without bars |
| FRC | 2016-01-04 to 2023-04-28 | 169 later sessions without bars |
| ABNB | 2020-12-10 to 2023-12-29 | 1,244 earlier sessions without bars |
| UBER | 2019-05-10 to 2023-12-29 | 843 earlier sessions without bars |

These eight probes have no internal unobserved sessions between their first
and last bars. These are **observed price spans, not certified listing or
delisting dates**. An ended history does not supply acquisition cash, an
OTC continuation, a bankruptcy recovery or a guaranteed sale at its last
close. FB/META also demonstrates why we cannot treat every symbol as an
independent company. Alpaca documents the symbol mapping behavior in its
[historical bars reference](https://docs.alpaca.markets/us/reference/stockbars).

## Engineering changes and execution checks

- Added read-only catalog access to the centralized broker gateway.
  The pinned SDK rejects nine TXSE entries through its old exchange enum;
  the new method preserves raw public metadata without changing global
  trading-client modes or upgrading dependencies.
- Added bounded, paginated multi-symbol bar access. The original SDK
  single-symbol parser raised `AttributeError` on 21 no-history responses.
  The final path records genuine empty results correctly and rejects
  malformed pages/repeated pagination tokens.
- Added `backtesting/universe_audit.py`: deterministic sampling before price
  requests, calendar-aware coverage, existing hard validation and warnings,
  raw CSV evidence, hashes and structured failures. No filling or replacing
  inconvenient instruments.
- The original and final catalog **and frozen sample hashes match**. This
  was a transport correction, not a different coverage sample.
- All 34 nonempty CSVs are byte-identical between the original and final
  transports. Execution source hashes still match the code that ran.
- Post-run checks passed for the catalog, sample, calendar and all **55**
  saved CSV hashes, including 21 empty CSVs. The rejected request has no CSV.
  All observed bars end before 2024. No new unit tests were added or run in
  this task; runtime coverage and artifact verification are not substitutes
  for broker-boundary failure tests. Raspberry Pi execution is unverified.

## Evidence locations and reproduction

Final local evidence: `data/reports/broad_universe_audit_final/report.json`.
Alongside it: `assets.json`, `sample.json`, `calendar.json`, the two public
directory files, `directory_flags.json`, numbered `bars/*.csv` files, and
`verification.json` with ten passing artifact/provenance checks.
Raw catalogs, data and reports remain ignored by Git. This document records
the outcome for the repository; a future fetch need not reproduce a current
catalog that changes over time.

Original SDK attempt: `data/reports/broad_universe_audit_v2/`. Earlier failed
setup attempts are also retained. The final report records source hashes,
download times, parameters, row counts and file hashes. Key final hashes:

```text
assets.json  2d2527bca306b1e2bee63eb7866f49821e2ee3b21f5b54b55565fd661758c1ea
sample.json  8d402a39c9ef83033a581e8b88f918adf5620ebc81c3004153ffc351d0ed73d3
calendar.json 543641716aae762d2a0ba9d5ba431da80f00cbac5c3c7e79fc0528170064cca7
```

From the repository root, use a **new** output directory:

```powershell
.\.venv\Scripts\python.exe -m backtesting.universe_audit --output data/reports/broad_universe_audit_next
```

On Linux/Pi, the same module runs with `.venv/bin/python`. Heavy research
stays on the development PC. No new dependencies were introduced.

## Decision and the next study

**Broad daily price access is demonstrated; historically correct broad-market
performance research is not ready.** We lack audited historical eligibility,
security classification, identity events, corporate actions/terminal outcomes,
and a dynamic-universe portfolio engine. A current-assets backtest selecting
only complete survivors would conceal those gaps.

The subsequent [entry/selection study](broad_entry_selection_study.md) is now
scoped: eight matched combinations of small/broad universe, original/stricter
entry, and alphabetical/momentum ranking. It specifies the stricter gates,
causal timing, unchanged capital/exit policy and a maximum 92-run budget with
early stopping. **It has not been simulated**, because its data gate failed.
No claim that these changes raise returns is supported yet.

Codex's next engineering work is a dated universe/lifecycle data contract,
source/adapter evaluation and dynamic-universe support. No further owner risk
settings are needed for that work. A prospective read-only membership/signal
record is the available no-purchase route while historical inputs are sought.

Possible historical-source leads, **not purchases or verified compatibility**:

- [CRSP US Stock Databases](https://www.crsp.org/research/crsp-us-stock-databases-2025-layout/)
  advertises active/inactive histories, corporate actions and permanent IDs.
  Verify required daily OHLCV fields, date coverage, terminal-event semantics,
  personal-use licensing, delivery and price before proposing any purchase.
- [Nasdaq Daily List specifications](https://www.nasdaqtrader.com/content/technicalSupport/specifications/dataproducts/dlcompletespec.pdf)
  describe listing/change/deletion events. Such an event product alone is
  not complete historical prices or terminal proceeds.

No price or license entitlement was obtained for either source. Any paid
proposal needs the owner's approval. Paper activation and opening the
reserved 2024-2025 evaluation remain separate later decisions.

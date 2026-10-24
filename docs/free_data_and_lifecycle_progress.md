# Data costs and historical-stock support

Updated 2026-10-24. **Current spending policy: $0 in new data purchases.**
The owner is unsure about paying, so continue with existing access and public
sources. Do not subscribe, start a paid trial or upgrade an account to unblock
research. Reconsider that policy only if the owner explicitly changes it.

**Latest result:** The [real accounting pilot and public historical-basket work](raw_action_pilot_and_historical_baskets.md)
adds action-aware risk diagnostics and 506/505-row historical source lists.
Company identity, full event/price coverage and unsupported events remain
research gates. The owner reports having no billing card configured; no
billing account inspection, subscription change or purchase was performed.

**Subsequent engineering update:** [Lifecycle/action verification](corporate_action_progress.md)
now includes 69 passing focused tests, 36 exact historical financial replays,
split and ordinary-dividend accounting, and a reviewed AAPL split record.
The earlier implementation/next-work notes below describe the original
increment; current blockers are verified historical membership/event coverage
and unsupported corporate-action/risk cases, not a required data purchase.

## Do I already have paid data?

We have not inspected your billing/subscription screen, so we cannot establish
whether you already pay for an Alpaca plan. Working API keys and successful
SIP downloads do not prove that a paid plan is active. No purchase or upgrade
was made by this project.

Alpaca's [plan documentation](https://docs.alpaca.markets/us/docs/about-market-data-api)
lists Basic as its default free plan, with historical data since 2016 and
restricted access to the latest 15 minutes. Its
[market-data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
explicitly permits historical SIP queries without a subscription when the
end is at least 15 minutes old. Our 2016-2023 queries are well outside that
recent-data restriction. SIP describes a feed, not proof of a subscription.

If you want to check your existing plan, open Alpaca's **Plans & Features**
page and inspect the current Market Data plan/billing. Do not click Upgrade
to continue this project. You do not need to share credentials or payment
information with Codex.

**Paid data is not necessary for the engineering work or the historical price
and company-event requests demonstrated so far.** A clean, complete historical
record for every US common share is a different requirement: we have not
established that existing/public sources provide all of it. We can continue
without buying anything, but must limit claims to what the evidence supports.
A paid real-time price plan would not automatically solve historical
membership, identity and delisting-outcome gaps.

## What the engineering means in plain language

1. **Give each investment its own permanent research ID.** A name change does
   not create a new holding, and a reused ticker does not merge two companies.
2. **Record when it existed and could be researched.** A 2020 IPO is absent
   in 2017; the simulator waits for its own price history to build indicators.
3. **Record what happened when it stopped trading.** A verified cash payment
   can resolve held shares. Unknown outcomes block scoring; we do not invent
   a sale at the last price or assume a bankruptcy paid zero.
4. **Keep one shared account across those different histories.** Real rows
   drive signals and fills; actual cash can be reused. No manufactured prices
   make different instrument lifetimes look identical.

## Sources evaluated under the $0 policy

| Source | What it can contribute | What is still missing |
| --- | --- | --- |
| Existing Alpaca historical prices | Actual daily price/volume coverage; 56 pre-2024 probes already completed | Complete dated historical membership, common-stock classification and event outcomes are not certified by bars |
| Existing Alpaca company-event API | Four new read-only requests succeeded; raw split/dividend/merger/name-change records | Historical availability, complete event coverage, payment timing and security matching need review |
| Public Nasdaq current symbol directories | Current symbols and ETF/test-issue flags; snapshots already saved | Current non-ETF flags do not establish common-stock status or past membership |
| Public SEC EDGAR APIs/filings | Company filing histories and source documents that can support dated event review | Not a ready daily stock-universe/price database; company CIK is not a permanent share-class ID |
| Prospective saved catalogs | A dated record of what our scanner observed from now on | Cannot reconstruct past daily membership by looking at today's list |

The [Nasdaq directory definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs)
describe the current directory flags. The
[SEC API guide](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
describes public unauthenticated submissions/XBRL APIs and current ticker/
exchange metadata. SEC source documents can help verify individual events;
we have not downloaded a complete historical SEC-derived universe here.
No paid vendor is required or selected in this increment.

## Actual company-event access check

The bounded command `backtesting.universe_sources` made four queries on
2026-10-24 with the configured keys. Dates below are **provider process-date
filters**, not guarantees of when information became public.

| Symbol query / year | Returned records | Access |
| --- | --- | --- |
| META / 2022 | Two name changes | Succeeded |
| TWTR / 2022 | One cash merger | Succeeded |
| ATVI / 2023 | One cash dividend and one cash merger | Succeeded |
| AAPL / 2020 | Four cash dividends and one forward split | Succeeded |

All responses fit one page each. No price bars, account information, order
endpoints, 2024-2025 evaluation or billing operation was involved. Success
demonstrates **existing access**, not whether your current plan is paid or
whether every historical event is available.

The META response is particularly instructive: one record links FB to META
with CUSIP `30303M102`, while another links a different META security to METV
with CUSIP `53656F417`. A symbol-only match would combine different securities.
Even CUSIP needs dated mapping across changes; it is not a universal permanent
identity. Preserve provider event IDs and source evidence for review.

The TWTR response includes an effective date and rate, but no independently
verified historical publication time or actual cash availability time. We
therefore do **not** automatically turn its effective date into spendable
cash at that day's open. Alpaca's
[company-event reference](https://docs.alpaca.markets/us/reference/corporateactions-1)
also warns that event availability can be delayed and filters by process date.

Local evidence:

- `data/reports/free_source_access_v1/report.json`: four access outcomes and
  raw page checksums.
- `META_1.json`, `TWTR_1.json`, `ATVI_1.json`, `AAPL_1.json`: raw public records.
- `candidates.json`: ten normalized review candidates; all deliberately have
  unknown historical publication/payment fields and readiness false.

The offline normalizer verifies raw page hashes, preserves identity fields,
deduplicates event IDs and makes no extra API requests. Its output is a
review queue, not certified lifecycle input. Artifacts are ignored by Git.

Reproduce with a fresh directory, and review it offline:

```powershell
.\.venv\Scripts\python.exe -m backtesting.universe_sources --output data/reports/free_source_access_next
.\.venv\Scripts\python.exe -m backtesting.universe_sources --review-existing data/reports/free_source_access_next
```

At most four symbols × five pages can be requested. An entitlement failure
is recorded; there is no automatic upgrade path. The same commands use
`.venv/bin/python` on Linux.

## Implementation delivered

- [Historical-universe contract and example](historical_universe_format.md):
  dated aliases, listing intervals, evidence timestamps and cash outcomes.
- Optional dynamic-universe mode in the existing shared-cash simulator:
  later IPOs, ended listings, stable holdings through ticker changes,
  contiguous indicator warmup, expiring unavailable entries, and known
  terminal cash payments. Missing in-lifetime data blocks scoring.
- A separate cash-settlement ledger and reconciled account P&L. Cash events
  are not counted as stock-sale fills or ordinary completed trades.
- Explicit refusal by the old OHLC risk helper to ignore terminal cash events.
- Bounded company-event access and an offline review-candidate adapter.

## What remains, and whose job it is

**Codex:** First add focused lifecycle/accounting/failure tests and replay
the unchanged historical controls. Then extend corporate-action handling
for splits/dividends and review free-source event identity/publication/
payment evidence. Work toward an explicitly documented historical universe
or a narrower valid scope; a prospective read-only record is another path.
Entry/ranking study simulations remain gated on data and accounting readiness.

This increment's source access and offline candidate extraction were executed;
Python compilation and diff checks were performed. No automated unit tests,
unchanged-control simulations or new strategy-return study was run. Dynamic
support remains an initial engineering capability, not validated broad-market
performance or paper-readiness evidence. Pi operation is unverified.

**Owner:** No payment, risk JSON edits, manual stock collection or account
upgrade is required now. You can keep the $0 budget. Historical accuracy may
limit how broad a credible no-purchase study can be; we will report those
limits rather than label a survivor-selected test as the whole market.

# Broad-universe feasibility audit: registered scope

Registered 2026-10-24 before fetching the new catalog or coverage sample.
The owner authorized a read-only feasibility audit and a subsequent finite
entry/selection study. This protocol buys no data and places no orders.

## Questions and finite request budget

1. Snapshot all US-equity assets returned by Alpaca, including inactive and
   nontradable entries. Count statuses, exchanges, and available metadata.
   The catalog is current, not a historical membership database.
2. Fetch Nasdaq's two public current symbol directories for ETF/test-issue
   flags. A non-ETF is **not necessarily a common stock**: preferred shares,
   depositary receipts, units, warrants and other securities need explicit
   historical classification. Save download failures rather than substituting
   a different universe.
3. Before inspecting prices, freeze up to eight current active/tradable
   symbols per exchange: NYSE, NASDAQ, AMEX, ARCA, BATS. Rank within each
   exchange by SHA256 of `broad-universe-audit-v1|asset_id|symbol`. This is a
   coverage sample of up to 40 assets, not a recommended investment basket.
   Keep ETFs and unknown types in the audit; report their classification.
4. Add up to eight hash-ranked inactive assets, plus eight explicit lifecycle
   probes: META, FB, TWTR, ATVI, SIVB, FRC, ABNB, UBER. These deliberately
   probe aliases, incomplete lifetimes and ended histories; do not treat them
   as random observations or assert listing/delisting dates from prices.
   Deduplicate requests without replacing failed symbols. Maximum 56 symbols.
5. Fetch daily SIP/all-adjusted bars only from 2016-01-01 through
   2024-01-01 **exclusive**, with API end capped at 2023-12-31 23:59:59 UTC.
   Fetch every page through the multi-symbol endpoint (maximum 100 pages per
   request; repeated tokens are errors). Its installed request model lacks `asof`;
   record default/current symbol mapping as an unresolved historical identity
   issue. No 2024-2025 bars, performance calculations or parameter search.

## Coverage analysis and interpretation

Use Alpaca's actual session calendar. Preserve every raw returned bar in a
hashed CSV, including duplicates or invalid data; do not forward-fill, drop
failures, truncate to common dates, or replace bad symbols. Reuse existing
OHLCV/timestamp validation. Count scheduled dates before the first observed
bar, inside the observed span, and after the last observed bar separately.
Report unexpected timestamps and out-of-range responses as hard problems.
Missing dates are **unexplained observations**, not automatically missing
candles: IPOs, suspensions, no trades, delistings and feed defects require
independent lifecycle evidence. Empty/error responses remain in the report.

Save the frozen sample before bar requests; record times, request conventions,
source hashes, file hashes, elapsed times, rows and warnings. Summarize resource
use for this sample only; estimates are not a complete-market benchmark.
Use generic API failure classes/status codes, never credentials or headers.

## Decision gates

- Historical daily bar access and structural integrity may pass while a
  historically correct broad-universe backtest remains blocked.
- Require dated common-stock classification, listing/delisting membership,
  stable identities/aliases, corporate actions and terminal outcomes before
  claiming market-wide historical performance. An inactive catalog entry or
  an available old price is insufficient evidence of completeness.
- The existing identical-calendar portfolio engine must be extended for
  genuine dynamic universes. Never solve this by discarding incomplete names
  or treating a last close as guaranteed delisting proceeds.
- If these gates fail, complete and publish the audit and finite entry/selection
  protocol. Do not silently substitute a survivor-selected performance study.
  A forward-only shadow study can build prospective membership at no data
  purchase, subject to verifying current-feed access and runtime requirements.
- Any paid source must be reviewed for coverage, licensing, required OHLCV,
  stable identifiers and terminal events before an owner-approved purchase.
  Public product descriptions alone do not establish adapter compatibility.

The owner's existing 6% net annual return / 5% drawdown research criteria stay
unchanged. Tighter entries and a larger search are hypotheses, not approval
to change risk limits, inspect the reserved years, or activate paper trading.

### Transport compatibility amendment

The initial execution found two pinned-SDK limitations: its asset-exchange
enum rejects nine new TXSE catalog entries, and its legacy single-symbol
bar parser raises `AttributeError` for some no-history responses. The final
audit preserves raw catalog metadata and uses the documented multi-symbol
bars endpoint with explicit pagination and empty-response handling. Keep
the original attempt and its failures. Repeat the identical metadata-ranked
sample, without replacing names or changing dates, and verify the saved
sample hashes match. This changes transport only, not study hypotheses.

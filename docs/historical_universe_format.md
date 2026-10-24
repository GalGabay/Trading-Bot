# Historical-universe support: what the new code does

**Latest update:** [Split/dividend accounting and lifecycle verification](corporate_action_progress.md)
add version-2 action records, causal split feature views and separate
ordinary-dividend entitlement/payment ledgers. All 36 prior holding-study
replays match exactly; 69 focused lifecycle/action/source tests pass.

## In ordinary words

We need a history of **which investment existed when**, not only a pile of
price files. Three examples:

- A stock first listed in 2020 cannot be bought in a 2017 simulation. It
  needs its own earlier price observations before indicators are ready.
- If OLD becomes NEW, its shares and holding age do not magically disappear
  and restart. Both tickers refer to the same stable investment ID.
- If a company is acquired for cash, shares are replaced by the documented
  payment when it actually becomes available. If it stops trading and we
  don't know what happens next, stop the calculation instead of inventing
  a profitable sale, a stale valuation or a zero recovery.

This implementation adds those basic mechanics to the existing shared-cash
simulator. It does **not** supply or certify a complete historical market
database, and it does not change paper-order permissions.

## Versioned format and evidence

`backtesting/universe.py` defines `HistoricalUniverse`, `ListingPeriod`,
`CashOutcome`, `SplitAction` and `CashDividend`. The version-1 [JSON example](examples/historical_universe.example.json)
is fictional and demonstrates a ticker change, a later IPO and a terminal
cash payment. It contains only four sessions, so it cannot satisfy the
200-session entry warmup and is not a profit study.

| Field | Meaning |
| --- | --- |
| `sessions` | Actual exchange opens/closes, with timezone offsets; daily bar labels are New York midnight converted to UTC |
| `instrument_id` | Stable research key for one security, independent of its ticker; not automatically a company CIK or a current ticker |
| `symbol`, `exchange`, `security_type` | Historically valid alias, venue and common-stock classification for the interval |
| `start_session`, `end_session_exclusive` | Inclusive start and optional exclusive end of a documented listing interval |
| `start_known_at`, `end_known_at` | When each historical boundary became public; not our later download time |
| `source` | Evidence reference for independent review; a nonempty reference is required but not proof that its contents are correct |
| `price_basis`, `action_scope` | Raw prices plus either the version-1 event-free declaration or version-2 explicit split/ordinary-dividend scope; adjusted inputs are rejected |
| `cash_outcomes` | Unique documented terminal payments: stable ID, actual payment session, USD per share, publication time and evidence |

Version 2 keeps those fields and requires `splits` and `dividends` arrays,
plus `action_scope: explicit_splits_and_ordinary_cash_dividends`. Arrays may
be empty; supplied events need independent evidence. Add records in this form
to a full manifest (the snippet alone is not a complete manifest):

```json
{
  "splits": [{
    "event_id": "EXAMPLE-SPLIT",
    "instrument_id": "EXAMPLE-001",
    "effective_session": "2023-01-05",
    "new_shares": 2,
    "old_shares": 1,
    "known_at": "2023-01-04T12:00:00Z",
    "source": "FICTIONAL EXAMPLE: replace with reviewed evidence"
  }],
  "dividends": [{
    "event_id": "EXAMPLE-DIVIDEND",
    "instrument_id": "EXAMPLE-001",
    "ex_session": "2023-01-05",
    "pay_session": "2023-01-06",
    "cash_per_share": 1.0,
    "known_at": "2023-01-04T12:00:00Z",
    "source": "FICTIONAL EXAMPLE: cash available at specified open",
    "kind": "ordinary_cash",
    "share_basis": "post_split"
  }]
}
```

`pay_session` means cash is available under an explicit reviewed convention;
do not automatically copy a vendor date. `known_at` covers all supplied terms.
A payment after the saved calendar remains an outstanding nominal USD claim.

Only explicitly classified ordinary common stock and REIT common shares on
NYSE/NASDAQ/NYSE American (`AMEX`) are supported. Unknown security types or
venues are rejected. A dated alias cannot refer to two different investments
at the same time. Reused tickers in nonoverlapping periods require different
stable IDs when they represent different securities. Evidence must be known
by the modeled effective session open. Boundaries outside the saved calendar
are conservatively required to be known by local midnight on that date.

The loader rejects unsupported manifest versions, overlapping intervals,
ambiguous aliases, absent end evidence, duplicate terminal outcomes,
unsupported currencies, negative/nonfinite payments and late knowledge.
Its manifest SHA256 and supplied evidence are included in dynamic results.
Evidence references still require source coverage and content review.
The price/action declarations are mandatory, not an automatic independent
verification of the source. A supplied file with undeclared splits or dividends
does not become valid because a caller labels it event-free.

## Connecting the simulator

The existing aligned-data mode remains the default. To use the new mode:

```python
from pathlib import Path
from backtesting.universe import HistoricalUniverse

universe = HistoricalUniverse.load(Path("data/universe/verified_manifest.json"))
# Each DataFrame has canonical timestamp/symbol/open/high/low/close/volume.
# Keys are stable IDs. Source symbol columns retain the dated real tickers.
result = engine.run(
    datasets_by_stable_id,
    trade_start=trade_start,
    trade_end=trade_end,
    universe=universe,
)
```

`PortfolioBacktestEngine` now accepts sparse histories when this manifest is
provided. It maps real rows to the explicit calendar without creating price
rows. It retains every declared instrument and validates each historical
alias. Empty in-lifetime histories and unexplained in-lifetime gaps are hard
errors; do not discard those instruments to make a broad study run.

Before an IPO and after a documented end, absence of bars is expected.
Indicators are built from actual contiguous positive-volume observations;
warmup restarts after a documented listing gap or zero-volume observation.
BUY planning requires 200 such sessions. Ordinary next-session execution,
shared cash, position gates, stops and holding policies are reused. A ticker
change alone preserves the position, cost basis, indicator history and age.
Trade ledgers use stable IDs; dated ticker metadata is retained separately.

A BUY whose scheduled execution session is unavailable expires; it is not
left waiting indefinitely for a favorable later price. No price or stop
fill is invented on a missing/zero-volume session. If a held position lacks
an observable tradable bar and no supported payment resolves it at that open,
the simulation raises `UniverseDataError`. A result is not returned as if
the missing investment were harmless.

## Cash events and accounting

Terminal cash is processed at the specified session open, before discretionary
trades. Only the quantity actually held receives it. Associated pending orders
and stops are canceled in the simulation. A payment of zero needs explicit
evidence just like a positive payment. Merger effective date and payment
availability date must not be conflated.

Payments appear in `cash_settlements`, **not as broker stock-sale fills**.
`summarize_portfolio` includes their realized P&L when reconciling account
equity, but trade win rate, profit factor, completed-trade counts and trade
holding duration exclude these cash events. Separate settlement metrics show
how positions were resolved. `daily_research.pack` preserves the full event
ledger and universe metadata. The old OHLC risk-envelope helper explicitly
rejects cash-event cases rather than dropping events and reporting false risk.

## Deliberate limits of this increment

- This is initial lifecycle support, **not a finished broad-market research
  engine**. Dynamic metadata explicitly reports market-wide readiness false.
- Splits and ordinary cash dividends now have explicit accounting adapters.
  Stock mergers, spin-offs, fractional-share cash-in-lieu, special/due-bill
  dividends, delayed terminal-payment claims, taxes and FX remain unsupported.
  Never combine all-adjusted bars with explicit cash/share events. Real
  performance scoring still needs verified action/membership coverage.
- Payment is modeled only when known and available at a session open. A
  nontrading claim waiting for a later payout needs an explicit valuation and
  settlement model; absent quotes before payment currently block the run.
- Independently documented suspensions/no-trade gaps need further adapters.
  Unexplained gaps are rejected; neither last price nor listing status is
  enough to fabricate daily liquidity.
- Separate signal/execution feeds in dynamic mode are rejected until their
  dated action conventions are audited. Entry ranking and stricter volume/
  momentum gates from the eight-arm study are not implemented in this increment.
- 69 focused lifecycle/action/source tests pass and 36 saved holding-study
  financial replays match exactly. Full-suite results and the two missing
  optional ML-dependency errors are in the progress report. Raspberry Pi
  execution remains unverified.

No 2024-2025 price data, order endpoints or paid products are involved.

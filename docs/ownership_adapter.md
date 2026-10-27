# Ownership accounting connected to the portfolio simulator

Date: 2026-10-27. This is offline engineering, with no purchases, network
requests, account access, orders or dependency installation. The 2024–2025
candle holdout remains reserved. Paper submission remains disabled.

## What changed

The existing `PortfolioBacktestEngine.run` now accepts an optional reviewed
`OwnershipSchedule`. In this mode, the exact ownership ledger supplies cash
and positions throughout the simulation, including every simulated fill.
Legacy runs retain their existing path and report shape. Exact legacy-result
preservation still requires the regression replays below; it is not claimed
from code inspection alone.

The adapter connects:

- Delayed fixed cash rights, whole successor shares, spin-offs and fractional
  claims to opening/closing equity and the available cash for new purchases.
- Split conversions and ordinary dividend rights on inherited whole holdings.
  An ordinary dividend's issuer `pay_session` is informational in this mode;
  spendable cash needs a separate availability instruction.
- Inherited economic basis and oldest holding age to the existing holding
  review. Existing destination holdings retain separate underlying lots;
  the strategy-level holding age is the oldest of its lots.
- Corporate-action order cancellation, stop rebasing, exposure, position
  counts and feature-history resets.
- Summary/serialization and an accounting replay that reconstructs the
  journal, claims, fills, closing values and daily risk bounds. The external
  risk reporter additionally compares used quotes with the actual complete
  raw histories and dated identities supplied by the caller.

No representative source case was automatically approved for strategy scoring.
The previous mechanics scenarios used declared timing/delivery assumptions;
they cannot supply missing historical entitlement or broker delivery evidence.

## Explicit input contract

Use a version-2 `HistoricalUniverse` manifest with raw daily bars and:

```json
"action_scope": "explicit_ownership_splits_and_ordinary_dividends"
```

Then load a **separate** schedule:

```python
from backtesting.ownership_adapter import OwnershipSchedule
from backtesting.universe import HistoricalUniverse

universe = HistoricalUniverse.load(universe_path)
schedule = OwnershipSchedule.load(schedule_path)
result = engine.run(
    datasets, trade_start=start, trade_end=end,
    universe=universe, ownership=schedule,
)
```

This is the Python research API. The older fixed-symbol portfolio CLI does
not acquire these inputs or bypass their review. Datasets must retain every
declared stable identity, including inherited-only successors, and still pass
the existing calendar/lifetime/alias checks. New-mode development calendars
must end before 2024.

The paired [fictional universe](examples/ownership_universe.example.json) and
[fictional schedule](examples/ownership_schedule.example.json) illustrate the
format. They contain only four sessions, no supplied prices and no 200-session
entry warmup. They are not a research dataset, performance example, or actual
approved company-event evidence.

### Ownership reviews

Each `ReviewedOwnership` requires:

- Complete `OwnershipEvent` terms, source and public knowledge timestamp.
- `reviewed_for_research: true` following an actual engineering evidence
  review. This flag does not approve paper risk limits.
- `eligibility_policy: "prior_close_holders_confirmed"`, its evidence source
  and when that evidence was known. The source must establish which prior-close
  holders own the right at the effective open. A record date alone does not
  resolve due-bill or ex-distribution ownership.
- For share legs, delivery evidence, delivery knowledge and an actual delivery
  instant equal to the effective saved exchange open. Undelivered whole shares
  need another adapter and are rejected here.

All terms/entitlement/delivery knowledge must be available by that open.
Exchange parents require documented ended identities; retained parents and
delivered destinations require valid dated listings. Genuine splits remain
in the universe's split records. Overlapping ownership events or split/
dividend/terminal events affecting the same identity at the same open require
explicit consolidated terms; the adapter rejects ambiguous ordering.

`entry_instrument_ids` is the explicit set permitted for **new purchases**.
Receiving a successor/child does not automatically add it to that set.
Inherited holdings may be sold and reviewed even when new entry is prohibited.

### Fixing and payment instructions

Schedules have separate `fixings` and `payments`, each with a unique
`instruction_id`, `claim_id`, exact `at`, `known_at`, `amount` and `source`.
Every instant must be an actual saved exchange open. Unknown amounts/dates
produce no guessed instruction; the right remains outstanding.

- A fixing replaces fractional ownership with a documented total cash
  allocation. It creates no spendable cash. Aggregate issuer cash totals do
  not establish an individual holder's allocation.
- Fixings declare `amount_basis`. A sourced `per_fractional_share` rate scales
  with the exact simulated fractional units. A `fixed_total` payout instead
  requires `expected_fractional_units` and rejects a different holding quantity.
  A payout observed for one hypothetical holder cannot silently apply to every
  strategy/account size. Neither mode guesses a rate from future market prices.
- A payment credits an existing fixed cash right at its reviewed availability
  instant. An exact amount can be supplied, or the literal `outstanding_claim`
  explicitly pays that right's already fixed balance. This allows a contractual
  per-share cash right to scale with the simulated eligible holdings.
- A fractional payment needs a preceding matching fixing. Multiple payments/
  fixings per claim and cash amounts that disagree with the right are rejected.
  Payments use `fixed_total` and have no `expected_fractional_units`; the
  `outstanding_claim` option settles the previously fixed amount exactly.
- A flat-start scenario may never have owned a right or may have received an
  exact whole number of shares. Instructions for such uncreated claims have
  no cash effect. Duplicate instructions are rejected at schedule validation;
  a real outstanding claim is never forgiven or removed by that rule.

The `fill-` instruction prefix is reserved for the simulator's fill journal.

Ordinary dividend claim IDs are `dividend:<event_id>`. Ownership component
claim IDs are `action:<event_id>:<component_index>`: retained parent first if
applicable, then a cash leg if present, then share legs in declared order.
Only a fractional remainder creates a claim for a share component. Genuine
split fractional claims use component index zero.

## Causal execution and research conventions

1. At the session open, the ledger processes genuine splits, reviewed ownership
   events, ordinary dividend rights, fractional cash fixings, cash payments and
   verified immediate terminal outcomes. Same-day split/dividend handling uses
   post-split whole units. Fractional entitlement ambiguity causes a hard error.
2. Ownership basis is allocated using **opening component values**, including
   nominal fixed cash rights. Only the opening price is supplied to that
   calculation. The standalone ledger's default close-reference policy remains
   available for its separate non-strategy accounting scenarios.
3. Queued orders for affected parents and destinations are canceled. They are
   not relabeled or executed in obsolete share units. Ordinary genuine splits
   continue rebasing unfilled quantity ceilings and stop units.
4. Protective research stops carry the prior parent floor in proportion to
   current opening component values. With prior quantity `q`, stop `s` and
   total opening component value `V`, the inherited stop factor is `q*s/V`;
   each affected whole-share leg uses `leg_open * factor`. A pre-existing
   destination stop may tighten, never loosen. A breached inherited floor
   invokes the existing gap-stop model at that open. This is an explicit
   research convention, not a broker guarantee or a new personal risk limit.
5. Affected identities start fresh feature history at that session. No invented
   pre-event price adjustment joins different securities or distributions.
   New entries need 200 continuous tradable observations after the reset;
   inherited shares remain sellable and keep their holding age. Missing ATR
   does not remove an inherited stop. A continuation review lacking sufficient
   confirmation cannot justify an extension merely because the shares arrived
   through a company event.
6. Fixed cash rights count in equity but cannot fund purchases. Whole and
   fractional ownership count in stock exposure and beneficial position count.
   A passive distribution may exceed an entry cap; it blocks further purchases
   without inventing a forced sale. An existing fractional-only holding also
   blocks a fresh whole-position purchase in that identity.
7. Intraday protective exits and closing marks update the same ledger. Daily
   risk envelopes consider opening states, pre-touch whole holdings, net stop
   proceeds, fractional exposure and closing values. They are conservative
   bounds, not observed intraday equity or a promise of a 5% maximum loss.

Fractions remain untradeable claims. The adapter does not pretend to place
protective orders on them. Actions/dividends on unresolved fractional ownership
need reviewed chained entitlement terms; current support rejects them. Other
gaps include delayed whole-share delivery, election/proration, installments,
special dividends/due bills, tax, FX and uncertain recoveries.

## Reports and verification status

The new report has `accounting_ledger_version: 1` and an
`ownership_accounting` section. It contains the reviewed schedule, universe,
journal, exact marks, used session quotes, fill phases and daily risk envelopes.
Schedules loaded from a file also retain that input file's SHA-256; inline
schedules retain their complete normalized specification without a file hash.
Legacy corporate-action arrays are not substituted with misleading empty
records in this format. Fixed cash, dividend rights and fractional values have
separate equity-curve fields.

`summarize_portfolio` replays internal financial accounting. The optional
`daily_risk_envelope(packed, raw_datasets)` also checks actual source prices.
Neither process recertifies evidence declarations or reruns strategy selection.
Stock exit statistics exclude cash payments; inherited branch sales are
whole-position exits after economic basis allocation, not separate original
investment decisions. A report with outstanding claims has no purported fully
liquidated return; it separately labels a marked return after whole-share exit
costs.

**This increment:** Python compilation and whitespace/diff checks were performed.
No unit tests, saved-case replay, historical regression replay or strategy
performance study was run. In particular, the previous **111 unit tests / 84
mechanics checks** are historical results for the preceding component version;
they are not fresh integration results. Previous source/report snapshots remain
unchanged. Windows execution of the integrated engine and Pi execution both
remain to be verified.

## Next work

The next engineering step is focused integration tests and regression replays:
cash/share mergers, spin-offs, fractional payment delays, inherited holding
reviews/stops, canceled queued orders, fresh entry warmup, split/dividend
handling, missing quotes, false evidence approvals, report corruption and
event-free result preservation. That verification is a gate before expanding
the historical study. Then continue reviewing the free source gaps; unavailable
evidence stays blocked and never triggers a purchase.

Your action now: none. The [paper-readiness checklist](paper_trading_readiness.md)
explains the later owner decisions and why a launch date is not established.

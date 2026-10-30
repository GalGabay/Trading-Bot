# Approved exploratory subset: Step 1 inputs prepared

October 30, 2026. **Step 1 inputs are prepared for the separately approved
76-stock scope. Step 2 integration is next.** Steps 3 and 4 remain pending.
The original 100-stock study remains incomplete at Step 1.

## What changed after your approval

You approved the [concrete comparison](faster_research_scope_for_review.md),
including its data-availability selection bias and conditional maximum of
24 strategy attempts. Your exact answer, the presented proposal and unchanged
acceptance criteria are bound by a [separate approval record](faster_research_owner_approval_2026-10-30.json).
The original frozen protocol, previous approvals and source records are unchanged.
The proposal/review files remain as presented; their pending status is historical.
The later owner record supplies approval without rewriting that evidence.

The targeted MAC/SLG search exhausted its six-query discovery cap without a
new matching primary schedule to open. No new exact holder terms were admitted.
Rather than wait for those documents, the approved exploratory scope explicitly
defers those stocks and 22 other original roots. All 100 remain accounted for
in the [inventory](research_data/faster_research_scope_inventory.csv).

## Implemented

- `backtesting/scope_feasibility.py` classifies existing gates by original root,
  preserves descendants and controls, and exports a complete 100-row inventory.
  It selects on data availability, never strategy profits; this can still bias
  results and does not establish survivorship control.
- `backtesting/subset_preparation.py` requires the pinned approval and exact
  subset. It uses the existing preflight implementation and source-evidence
  gates, then checks the selected prices and accounting schedules separately.
- The existing full-100 loaders, policy validators and simulator are unchanged.
  The subset has its own manifest, exact schedules and source/execution pins.

The preparer verifies the original full preflight again, preserving its exact
188 blocking rows. It checks selected parent/child mappings and rejects any
remaining subset economic-data gate. For every selected price stream it checks
the checksum, symbol/ID, row count, timestamp ordering, OHLC/price/volume rules
and exact coverage of its configured intervals using the saved market calendar.
No missing candles are fabricated. Original CSV files are referenced unchanged.

## Preparation results

| Check | Result |
| --- | ---: |
| Selected original roots | 76 |
| Explicitly deferred original roots | 24 |
| Selected legal/reference/received-security streams | 79 |
| Observed daily candles checked | 149,113 |
| Additional frozen raw SPY context candles checked | 2,012 |
| Missing candles inside selected configured intervals | 0 |
| Remaining subset event admission gates | 0 |
| Original full-100 gates, preserved | 188 |
| Provider dividend records retained | 1,899 |
| Dividend plan rows across three scenarios | 5,697 |
| Material-event plan rows across three scenarios | 18 |
| Reviewed corporate-action instructions | 11 |
| Stream-level volume-anomaly warning records | 47 |

Volume warnings are retained in the price-check report. They are warnings under
the configured validator, not silent removals or proof of bad data. The count
is warning records across streams, not the number of anomalous candle rows.

These are vendor-dependent diagnostic inputs under the approved assumptions.
Zero current gates does not prove every historical company event was captured
or that every provider fact is independently verified. Strict historical
entitlement/delivery flags remain false. Availability-selected results alone
cannot establish paper readiness.

The prior **641 passing unit tests** describe the earlier holder/preparation
implementation. No unit tests were added or run for the new scope/preparation
utilities in this increment. The actual preparation command and its built-in
data/admission validation completed successfully; that is not a unit-test-suite
result. Raspberry Pi execution remains unverified.

The final [metadata integrity check](approved_subset_integrity_2026-10-30.json)
also confirms all 37 pins referenced by seven new scope/approval/evidence
documents match their files. Git's tracked-change whitespace check passed.

## Reproduce preparation using saved data

The historical cache must already exist with the recorded checksums. Choose a
fresh output path; an existing report is never overwritten.

```powershell
.\.venv\Scripts\python.exe -m backtesting.subset_preparation `
  --output data/reports/approved_subset_inputs_new
```

Executed output: `data/reports/approved_subset_inputs_2026_10_30_v2/`.
The first preparation is preserved separately; v2 also explicitly checks and
pins the frozen raw SIP SPY context through the original pilot lineage. SPY is
price-only context, not a traded member or passive total-return benchmark.
The [tracked summary](approved_subset_preparation_summary.json) pins the original
manifest, new input manifest, price checks, preflight, schedules, approval and
executed source snapshot. Generated candle data remains outside Git.

## What remains before profit/loss results

**Step 2 — engineering:** integrate these inputs and pending rights into the
portfolio simulator. Cash/share releases must transfer once, pending rights
must retain value after the original stock is sold, fractional rights must
remain unspendable, and unknown marks must block scoring/new entries. Apply
feature resets and invalidate stale orders/stops at relevant events. Verify
accounting and the two-stock control before any performance attempt.

**Step 3 — engineering, already conditionally authorized:** execute at most
24 attempts, comparing AAPL/CBRE with the 76-root scope on the frozen strategy,
70% total exposure / 5% per-stock entry cap / 20 positions, two development
windows, two cost cases and three accounting scenarios. Enforce one worker,
10 minutes per case and 120 minutes overall. Stop on a failed check or timeout;
do not substitute stocks, search parameters or add automatic reruns.

**Step 4 — explanation and decision:** report net returns, drawdowns, capital
use/cash, trades, holding time and sensitivity against the approved criteria.
Disclose this subset's selection bias. This does not automatically activate
paper trading.

**Your part now:** nothing to configure, purchase or approve again within this
scope. Personal paper-risk decisions and explicit paper activation come later.
No new profit/loss run, credential read, purchase, broker request, trade or
reserved 2024-2025 candle access occurred in this preparation.

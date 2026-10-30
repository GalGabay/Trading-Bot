# Corrected mappings and diagnostic accounting preparation

**Subsequent work, 2026-10-30:** see [approved defaults, focused tests and event
review](diagnostic_tests_and_event_review_2026-10-30.md). Owner assent is recorded,
unit tests have now been run, and the remaining Step 2 data gates are explicit.
The preparation record below describes the earlier unapproved/untested state.

October 29, 2026. **Still Step 1.** Step 2 integration and performance runs have
not started. This increment used cached evidence only: zero network requests,
purchases, broker requests, trades and strategy runs. No personal risk file changed.

## Implemented

### A new mapping revision

[The revision builder](../backtesting/corrected_input.py) creates a new
candidate package without modifying the old spec, stream files or acquisition
journals. The existing input builder now accepts an optional `--spec` path;
its default behavior and strict evidence gates remain.

- **JCI:** original selected member history begins September 6, 2016. The 170
  earlier candle rows have their own reference-only predecessor ID and are
  prohibited from later feature warmup or portfolio ownership. The vendor's
  old-Tyco 0.955 ratio is routed away from new-JCI share accounting. ADNT's
  later warmup distribution remains an explicit feature blocker.
- **PEAK:** the old legal-parent stream ends at the February 10, 2023 boundary.
  A separate successor stream contains 223 later observations. A one-for-one
  candidate exchange connects the legal identities; the provider reorganization
  must not be applied again. Economic/feature continuity is proposed for review.
- **PHIN:** the candidate economic event is July 3, 2023 at 17:00 Eastern;
  regular quotes still begin July 5. No intervening candles or receipt times
  were fabricated. The 1/5 distribution ratio remains provider-dependent.

The revised package has **121 streams**, **100 original selected members**,
**26 material-event candidates** and **203,683 candle rows**. The extra two
streams represent legal/reference identities, not newly selected stocks.
The original 25-event candidate spec is preserved.

The source-key/timestamp/source-symbol/OHLCV observation multiset matches the
previous package exactly. Canonical identity labels changed at the reviewed
boundaries; observed values and original membership were retained.
See the [revision summary](broad_corrected_input_summary.json),
[observation reconciliation](broad_corrected_input_reconciliation.json),
[corrected candidate spec](broad_corrected_historical_input_spec.json) and
[mapping rules](broad_corrected_input_mapping.json).

Sources remain the previously saved
[primary review](broad_event_primary_review.json) and
[browser evidence inventory](broad_event_browser_evidence.json). No new source
retrieval or admission certification occurred.

### Proposed accounting mechanics

[Diagnostic accounting](../backtesting/diagnostic_accounting.py) implements:

- Calendar-based base, five-extra-session-delay and no-credit availability.
- Exact rational pending cash/share rights and one-time release records.
- Whole-share delivery with remaining fractions retained as claims.
- No invented cash fixing, unknown-to-zero conversion or early cash spending.
- Current saved-close claim marks; missing values make equity incomplete.
- Explicit assumed provenance, with actual broker receipt/known-at unverified.

The pending-rights book has no trading interface or buy/sell methods. Its
released-cash and delivered-share totals are transfer records for future Step 2
integration; they are not account balances or a complete portfolio ledger.
The existing `ClaimLedger`, strict `OwnershipSchedule`, legacy diagnostic
approval and trading paths were not changed.

[The policy compiler](../backtesting/diagnostic_preparation.py) prepared
conditional schedules from the corrected provider records:

| Base-scenario category | Records | Meaning |
| --- | ---: | --- |
| Proposed payment schedule | 1,173 | A modeled release could occur if approved terms and eligible holdings exist. |
| Receivable only | 1,358 | No modeled release in the available window. |
| Blocked terms | 167 | Special/foreign/unclassified, election-lineage or reference-only cases remain blocked. |
| Total | 2,698 | Provider records; no simulated holdings or income earned. |

There are 8,094 dividend-plan rows and 78 material-event-plan rows across three
scenarios. These are conditional accounting plans, not trades or performance
results. **All 26 material events still require the relevant terms and policy
review before execution.** Of the 2,698 dividend records, 1,383 still lack a
payable date. Blocker counts overlap, so they need not sum to the blocked total.

See the [compiled summary](broad_diagnostic_preparation_summary.json) and
[event routing table](research_data/broad_diagnostic_event_routes.csv).

## What ran and what did not

The corrected-input CLI and policy-preparation CLI completed offline, with their
normal input hashes, calendar, candle and schema validation. Observation
reconciliation retained every original row. This is preparation evidence.

**No unit tests were added or run in this increment.** The earlier 193 passing
tests describe the previous code version. Its builder was preserved in the
[v2 code archive](research_data/step1_executed_v2/README.md), with the old hash
unchanged. The new rights-book operations still need focused unit tests;
the preparation CLIs do not exercise portfolio cash/share releases.

Intermediate policy outputs and their frozen copies were retained. The final
compiled output is `data/reports/broad_diagnostic_policy_v3`. A preparation
review corrected share-availability planning to respect each child's configured
regular-quote start, including distributions before that date. Corrected inputs are in
`data/reports/broad_corrected_input_v1`. Both directories and the older source
evidence must be retained when transferring research artifacts to the Pi.
Windows execution only; Pi execution remains unverified.

## Next and owner review

Read [the concrete assumptions and allocation defaults](broad_diagnostic_assumptions_for_review.md).
You can approve or change them in chat. Your existing **70% total entry exposure**
selection needs no repeated approval. The proposed 5%-per-stock and 20-position
settings are separate research choices, not paper-risk activation.

**My next work:** focused tests for these modules, remaining event/feature terms,
and the Step 2 bridge once its assumptions are settled. Unresolved economic facts
remain hard gates even after an owner accepts modeling defaults. A finite return
experiment still needs a concrete scope/run budget. Step 1, strict evidence,
performance readiness and paper authorization remain incomplete/false.

Reproduce preparation into fresh directories from the repository root:

```powershell
.\.venv\Scripts\python.exe -m backtesting.corrected_input --output data/reports/a_fresh_corrected_input
.\.venv\Scripts\python.exe -m backtesting.diagnostic_preparation --revision data/reports/a_fresh_corrected_input --output data/reports/a_fresh_diagnostic_policy
```

Use the Pi's own `python` environment for the same modules. These commands
prepare candidate data; they do not download sources, run strategies or trade.

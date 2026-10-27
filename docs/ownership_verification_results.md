# Ownership integration: tests, replays and remaining evidence

Date: 2026-10-27. **Engineering verification passed for the scope below.**
The broader strategy study is still blocked by data evidence. No strategy
has been approved for paper trading by this work.

## Results

| Check | Result | What it establishes |
| --- | --- | --- |
| New ownership integration tests | 45 passed | Synthetic end-to-end engine, serialization and external-price reconciliation |
| New evidence-review tests | 9 passed | Source-term/date checks, timing boundaries, mechanics consistency and blocked admission |
| Existing related unit tests | 129 passed | Ledger, universe, corporate actions, risk reporting and portfolio engine regression |
| Combined focused unit run | **183 passed; zero failures, errors or skips** | Windows Python execution, not the entire project suite |
| Saved financial regression | **36/36 exact matches** | Metrics, costs, fills, equity curves, events and risk events unchanged |
| Saved daily-risk regression | **36/36 exact matches** | Every saved daily envelope unchanged |
| Standalone accounting replay | **84 checks passed; zero failed**, seven cases | Component arithmetic and synthetic settlement timeline; not proof of actual historical delivery |
| Saved-source evidence audit | **20 primary sources revalidated** | Checksums and reviewed terms; no automatic event approval |

The 36-case replays cover three holding policies, two capital amounts, two
development windows and three cost assumptions. They reuse frozen references
through 2023. They do not search for better parameters or produce new strategy
return estimates. Old reports and reference hashes were preserved.

Fresh local outputs are in:

- `data/reports/ownership_unit_verification_v1` (full test log, counts, environment and code hashes).
- `data/reports/ownership_legacy_replay_v1` (36 financial comparisons).
- `data/reports/ownership_risk_replay_v1` (36 risk comparisons).
- `data/reports/ownership_component_replay_v1` (84 standalone checks).
- `data/reports/ownership_evidence_review_v1` (source review and fresh collection inventory).

These report directories and raw source files are local ignored artifacts.
The tracked [verification summary](ownership_verification_summary.json) pins
their hashes, counts and code versions. The tracked
[evidence summary](ownership_evidence_summary.json) retains the new review.
The standalone replay's `legacy_strategy_adapter_connected: false` describes
that standalone runner, not the now-tested portfolio adapter.

## What the new tests cover

Cash-only and mixed mergers; retained-parent spin-offs; exact fractional
rights; delayed fixing and cash payments; rights surviving share sales;
cash unavailable for purchases before credit; payout scaling across account
sizes; existing destination lots; inherited stops and holding ages; opening
gaps and intraday touches; commissions, spreads and extra stop slippage;
canceled queued orders; fresh feature warmup; passive exposure/position
limits; later genuine splits/dividends; documented zero terminal outcomes;
unowned rights; source immutability; schedule roundtrips and hashes.

Rejection tests cover unapproved/late entitlement, delayed whole-share
delivery, non-session events, unended exchange parents, unknown/duplicate
instructions, missing whole/fractional quotes, unresolved fractional
dividends, wrong payouts, altered external prices/aliases/volume and corrupted
reports. A reserved-calendar rejection uses dates only and reads no holdout
prices. Synthetic weekday calendars and source declarations are test fixtures,
not evidence about actual company events or exchange holidays.

## Bug found and fixed

The external ownership-risk replay already checked the journal, daily curves
and source prices, but could accept a separately altered headline summary.
It now checks initial/final capital, return, closing drawdown, exposure,
beneficial position count, realized/unrealized P&L, fill/trade statistics and
final whole-position values against the reconstructed ledger. Inconsistent
starting capital in execution-cost settings is also rejected. The new tests
demonstrated this failure before the fix and pass after it.

This is financial reconciliation of the supplied fills and data. It does not
authenticate evidence declarations or rerun strategy selection. Daily risk
bounds remain conservative bounds, not observed intraday equity or guaranteed
loss limits.

## Remaining data-evidence review

The [review protocol](ownership_evidence_review.json) pins the previous source
review, mechanics cases and cohort review. Its offline command rechecks saved
raw payloads and source hashes; it does not download replacement prices.

| Case or gap | Finding | Still required |
| --- | --- | --- |
| Initial Under Armour Class C distribution | Saved March 16, 2016 announcement supports planned one-for-one distribution; conservative publication bound precedes the first regular quoted session | Confirm entitled holders/market stream and actual delivery; later additional distribution remains separate |
| Arconic/Howmet 2020 branch | Saved February 6 announcement supports one new share per four old shares and distinguishes markets with/without the distribution right | Certify vendor stream, entitlement, actual delivery, new Arconic child prices and fractional treatment |
| Alcoa 2016 advance publication | Cached cover letter has a date placeholder | Establish actual publication timing; no date inferred from accession number or completion release |
| WFM, ATVI, Aetna and Level 3 | Saved primary sources support reviewed economic terms | Actual eligibility, cash availability, delivery where applicable, and fractional allocations; issuer payable dates alone are insufficient |
| Fox/Disney | Election/proration/conversion not resolved | Complete reviewed terms rather than selecting a convenient outcome |
| Additional Under Armour distribution | Aggregate issuer totals do not certify a holder's per-share allocation | Reviewed per-unit terms; no division of aggregate totals to guess a ratio |
| Bed Bath suspension/OTC/cancellation | Missing OTC quotes remain missing | Credible valuation through the lifecycle; no stale marks or assumed early zero |
| Full 506-security basket | Representative collection remains incomplete | Dated prices/actions/identities across the actual study scope |

The fresh inventory still finds **10 required events missing from provider
responses** and **77 event references quarantined outside their queried alias
interval**. Missing API events do not establish that no event occurred. None
of the seven mechanics cases was approved for historical strategy scoring.

Three bounded free public-web tool calls attempted to establish the Alcoa
filing date. The index addresses were inaccessible and search did not establish
the matching filing. That attempt remains an explicit gap; there is no paid
fallback. No missing observation or entitlement was fabricated.

## Reproduce

From the repository root with its environment active:

```powershell
python -m unittest tests.test_ownership_adapter tests.test_ownership_evidence_review tests.test_claim_accounting tests.test_universe tests.test_corporate_actions tests.test_action_risk tests.test_risk_diagnostics tests.test_portfolio_backtesting
python -m backtesting.lifecycle_replay --output data/reports/a_fresh_financial_replay
python -m backtesting.lifecycle_replay --risk-only --output data/reports/a_fresh_risk_replay
python -m backtesting.claim_accounting_audit --output data/reports/a_fresh_component_replay
python -m backtesting.ownership_evidence_review --output data/reports/a_fresh_evidence_review
```

The unit tests use synthetic fixtures and tracked examples. Saved-case replays
and the evidence audit also need the pinned local data/source files; a fresh
clone without those files cannot reproduce them. Each audit output directory
must be new. On Windows this execution used `.\.venv\Scripts\python.exe`.
On Raspberry Pi use that machine's Python environment. **Pi execution and the
full optional-ML suite were not run.**

## Cost, status and next step

Purchases: **$0**. Subscription changes, broker/account requests and orders:
**zero**. No dependencies installed. Tests/replays/audit ran offline; the
three public-web tool calls are recorded separately. No 2024-2025 candles
were used. All cash/share amounts in these checks are simulated accounting,
not investments, fees or money moved in an account.

**My next work:** prepare a bounded free-data research pilot proposal. It
must separate sourced economic terms from any proposed timing/valuation
assumptions, specify sensitivity checks and hard exclusions, and state which
free price gaps can actually be filled. Public issuer documents generally
cannot certify a particular broker's credit timing. Repeating source checks
cannot make those facts appear. An alternative research convention would
need a separately reviewed protocol and must not set today's verified-evidence
flags to true. Do not expand or score the basket until that gate is resolved.

**Your action now:** none. No purchase or personal risk-setting decision is
due. I will present that concrete proposal before asking you to review any
material change to the research scope or assumptions. Paper activation still
requires the separate [readiness gates](paper_trading_readiness.md).

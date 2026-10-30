# Step 2: approved subset connected to the simulator

October 30, 2026. **Step 2 of 4 is complete for the separately approved
76-stock exploratory scope. Step 3 is next.** No new research performance
case has run. The original fixed-100 study retains its 188 unresolved gate rows.

## What the implementation does

`backtesting/diagnostic_bridge.py` adds a separate diagnostic universe, schedule,
ledger and runtime. `PortfolioBacktestEngine.run(..., diagnostic=schedule)` uses
this path only with the corresponding diagnostic universe. Omitting the
schedule or combining it with the strict ownership adapter is rejected.

The implementation reuses the existing exact fill ledger, pending-right book,
feature views and daily risk-envelope mechanics. Strict ownership delivery and
evidence validators are unchanged. Pre-edit shared-source snapshots are retained
in `docs/research_data/before_subset_integration_v1/`.

- **Cash rights:** earned dividends and reviewed merger consideration remain
  separate from spendable cash. The pending-right book and main ledger transfer
  a scheduled payment once. Unknown payment dates remain unpaid receivables.
- **Share rights:** supported spin-offs retain the parent and create exact
  child claims. Base/delay/no-credit scenarios control whole-share delivery.
  Fractions retain their value and basis without an invented cash sale.
- **After a sale:** a parent sale does not erase its already-earned child or
  cash rights. Delivered child lots retain the original economic holding age.
- **Risk:** both unpaid cash and undelivered share rights reserve total entry
  exposure, as approved. They are included once in equity and never used as
  buying power before availability. Unspendable whole shares and fractional
  remainders are reported separately. A missing current share mark aborts
  valuation/scoring and prevents new entries.
- **Position slots:** whole-stock holdings and pending share identities count
  toward the held-name cap. Fixed cash receivables reserve exposure but are not
  additional stock-position slots. Cash rights remain nominal; credit risk,
  discounting, tax and FX are not modeled.
- **Stops/orders/features:** genuine splits rebase owned units and stop prices;
  affected queued orders are invalidated under the approved action plans.
  Material boundaries reset affected feature history. Delivered child shares
  inherit the previously established proportional protective floor, including
  a possible gap exit when delayed shares finally become available. Alias
  changes preserve economic units/age and invalidate queued execution state.
- **Reports:** exact economic basis and realized/unrealized P&L reconcile to
  equity. Saved journals, quotes, fill phases, claims and daily OHLC bounds are
  replayed independently of strategy signal generation. Headline financial
  fields, final holdings and external price observations are cross-checked.

Accounting-only vendor timing remains explicitly modeled. Historical known-at,
verified entitlement and actual broker-receipt flags are not promoted.
Chained actions on outstanding share claims require separately reviewed terms;
the adapter rejects unsupported cases instead of assuming a treatment. None is
needed by the current admitted selected schedules.

## Inputs and frozen settings

`backtesting/subset_integration.py` binds the recorded owner approval to the
prepared manifest, retains all 79 selected streams, clips only to the two
approved development windows and compiles all three accounting scenarios.
Empty histories whose entire configured interval lies outside a window retain
their declared identity; in-interval gaps still fail. SPY remains raw price-only
market context.

The engine factory uses the presented breakout strategy and **70% total entry
exposure / 5% per stock / 20 positions**, a simulated $10,000 account and the
existing base/pessimistic costs. Research halts remain the frozen 3% daily and
10% drawdown controls; the stricter 6% CAGR / 5% drawdown / 2% daily-loss
evaluation criteria are unchanged. These are not personal paper-risk approval.

The reviewed FCX component already included in its total payment is retained as
a context-only row linked to that total. It does not generate a second right.
An unsupported zero dividend is still rejected.

## Verification results

| Verification | Result |
| --- | --- |
| Focused unit/integration/regression tests | **236 passed; 0 failures, errors or skips** |
| New focused tests within that total | 42: 33 bridge tests and 9 window/factory tests |
| Compiled basket/window/accounting combinations | 12: two baskets x two windows x three scenarios |
| Saved-data accounting checks | **36 passed** |
| Synthetic financial compatibility comparisons | **6 passed** |
| New research strategy/performance runs | **0** |

The 36 accounting checks use saved observations for Apple's split, XL/RHT/MON
cash rights, all three K/KLG availability scenarios, and FCX's reviewed
total/component payment. Holdings are manual simulated fixtures, not real or
paper account holdings. These checks produce no investment-return percentages.

The six synthetic control comparisons reproduce legacy event-free fills and
financial curves under both cost cases and all three accounting modes. They
are not claims of equality with older real-market research returns. The next
comparison's two-stock control uses the same current 70/5/20 settings and
accounting conventions as its 76-stock challenger.

Two initial compilation attempts stopped on the empty outside-window stream
and FCX total/component cases. Both were corrected and covered by focused
tests; the final compilation passes. Earlier attempt directories remain
preserved. No performance attempt was consumed by those compilation failures.

- [Combined Step 2 verification record](subset_integration_verification_2026-10-30.json)
- [Unit/regression counts and executed-source pins](subset_integration_tests_2026-10-30.json)
- [Input compilation and saved accounting replay pins](subset_integration_compilation_2026-10-30.json)
- [Six synthetic control comparisons](subset_integration_controls_2026-10-30.json)

The previous 641-test result is historical and is not added to this total;
the suites overlap. This is focused verification, not the entire repository
test suite. Execution was on Windows; Raspberry Pi execution is unverified.

## Reproduce without starting a performance experiment

Requires the saved development cache and its recorded checksums. Use a fresh
output directory for each command:

```powershell
.\.venv\Scripts\python.exe -m backtesting.subset_integration `
  --output data/reports/subset_integration_new

.\.venv\Scripts\python.exe -m tests.subset_control_replay `
  --output data/reports/subset_controls_new
```

The first command compiles schedules, constructs engines without running them,
and checks saved-data accounting. The second uses synthetic scripted fixtures.
Neither starts the frozen research strategy or contacts a broker.

## Next: Step 3, engineering work

Implement and verify a persistent attempt ledger and enforced runtime limits,
then profile the runner before starting the approved comparison. It must use
one worker, at most 10 minutes per case, at most 120 minutes overall and at most
24 strategy attempts. Failure/timeout stops the batch without an automatic
rerun or budget reset. Step 2 completion alone does not bypass those conditions.

After that check passes, run the two-stock versus 76-stock comparison within
the existing approval. Step 4 explains net returns, drawdowns, capital use,
trades/holding time and sensitivities. Historical data-availability selection
can bias the result; this scope alone cannot establish paper readiness.

**Your part now:** no configuration, purchase or repeated approval is needed
within the approved scope. Personal paper-risk choices and explicit paper
activation come later. No credentials, broker endpoints, purchases, downloads,
reserved 2024-2025 candles or live/paper orders were used in this work.

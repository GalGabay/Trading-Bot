# Lifecycle tests, historical replays and split/dividend accounting

**Latest increment:** [Real raw-price pilot, action-aware risk diagnostics and historical baskets](raw_action_pilot_and_historical_baskets.md).
The February payable-date evidence gap is resolved for the reviewed Apple
pilot by the January issuer release. Broker cash availability remains an
explicit research convention, not a verified account observation. Earlier
test counts below describe the previous increment.

## What changed in ordinary language

If ten $100 shares become twenty $50 shares in a split, the account has not
made or lost money. The simulator now changes share counts, per-share cost,
protective stop prices and pending order units together. A ticker rename
still refers to the same investment.

For an ordinary dividend, entitlement and cash payment are separate. Prior
holders earn the payment at the explicit ex-dividend session; new buyers
at that open do not. Selling at that open does not discard an earned payment.
Until cash is actually available, it is recorded as a receivable, valued at
its documented nominal USD amount, and cannot finance a purchase. The amount
is credited once on the declared cash-availability session, even if the stock
was already sold or resolved by a terminal cash payment.

These rules follow the general mechanics described by
[Investor.gov on splits](https://www.investor.gov/introduction-investing/investing-basics/glossary/stock-split)
and [ordinary ex-dividend entitlement](https://www.investor.gov/introduction-investing/investing-basics/glossary/ex-dividend-dates-when-are-you-entitled-stock-and).
Special/due-bill distributions need different handling and remain rejected.
No current settlement rule is used to calculate historical ex-dates: those
dates must be explicitly sourced for the actual event.

## Supported behavior and research conventions

- Version-1 event-free manifests remain supported. Version 2 adds explicit
  `splits` and `dividends` under raw execution prices and
  `action_scope: explicit_splits_and_ordinary_cash_dividends`.
- Splits use positive integer **new-shares / old-shares** ratios. Owned
  quantities must convert exactly to whole shares. Fractional claims stop
  the run until verified cash-in-lieu handling exists; no rounding away loss.
- Pending BUY share ceilings convert into new units, rounding down only an
  unfilled proposed order if necessary. Held share claims are never rounded.
- Indicator/history views rebase only past prices and volume after a split
  becomes effective. Earlier decisions never see future split factors. Raw
  observed execution candles are retained unchanged. Several splits work
  cumulatively; no future-adjusted download is substituted.
- Dividends do not alter this rule's raw-price trend signals or fixed nominal
  stop level. Only splits change stop units. Ordinary dividend gaps may trigger
  those research stops. This is an explicit strategy convention, not a claim
  that a broker adjusts its stop orders the same way.
- Same-session order: split conversion, ordinary dividend entitlement using
  declared post-split per-share rates, available dividend cash, terminal cash,
  then ordinary simulated trades. Ambiguous/special action conventions must
  be resolved before supplying a manifest.
- Split share counts, dividend claims/payments and terminal cash have separate
  audit ledgers. Trade win rate/profit factor remain stock-trade-only. Cash
  income and outstanding claims are reported separately, while whole-account
  equity and total return include earned ordinary dividends exactly once.
- Summary checks reconcile entry quantities, split conversions, cash events,
  dividend entitlements/payments, outstanding claims, final cash and total P&L.
  The OHLC risk-envelope helper now independently reconciles supported split,
  dividend and terminal-cash ledgers, while retaining its conservative daily
  bounds and the explicit limit that intraday equity was not observed.
- No tax withholding, reinvestment, FX, stock mergers, spin-offs, fractional
  cash-in-lieu, uncertain recoveries, or delayed terminal-payment claim
  valuation is assumed. Nominal dividend claims are not discounted or insured;
  unsupported payment cancellations/corrections block certified research.

See the [historical-universe format](historical_universe_format.md) and
`backtesting/corporate_actions.py` for integration details. No action is
automatically approved just because its provider record has a processing date.

## Additional review of existing free-source records

No paid data or fresh stock-price download was needed. We inspected the saved
2020 AAPL company-event response and checked the split against Apple's
[2020-07-30 announcement](https://www.apple.com/newsroom/2020/07/apple-reports-third-quarter-results/)
and [OCC memo 47369](https://infomemo.theocc.com/infomemos?number=47369).
Both support a four-for-one ratio and split-basis trading on **2020-08-31**.
The record/payment date is not automatically the effective trading date.

The [review record](aapl_2020_action_review.json) preserves the provider event
ID, original page hash, source links and a conservative knowledge bound
before the effective session. It is one reviewed event, not a complete AAPL
data manifest or a market-wide security master. The availability bound is
deliberately later than the dated announcements; it is not an invented exact
press-release time.

The free response's February 2020 dividend lacks a payable date and a populated
CUSIP. That is a concrete remaining evidence gap. Other rows contain an issuer
payable date, but do not certify when a particular broker made the cash
spendable. These rows are not auto-promoted into verified `CashDividend`
inputs. Existing-source access works, while complete historical event and
membership coverage remains unresolved.

## Verification

The lifecycle, split/dividend and source/gateway tests use synthetic calendars,
mock HTTP responses and temporary files. No broker orders or network requests
occur in those tests. They cover IPO warmup, aliases, invalid evidence,
missing/zero-volume observations, terminal cash/zero recovery, forward/reverse
and multiple splits, fractional-share refusal, indicator causality, protective
stops and holding age, dividend entitlement/payment, future receivables,
post-sale/post-terminal payments, source checksums, duplicates and pagination.

Historical regression command:

```powershell
.\.venv\Scripts\python.exe -m backtesting.lifecycle_replay --output data/reports/a_fresh_lifecycle_replay
```

It validates saved input and reference artifact hashes, then replays the
36 prior holding-study cases: three policies × two capital sizes × two
windows × three costs. Exact comparisons include metrics, costs, fill ledger,
equity curve, event strings and risk events. Original reports/hashes are
never rewritten. This is a regression check, not a new profitable-strategy
search or independent confirmation of the old strategy.

**Executed results:**

- **69/69** focused tests pass in `test_universe`, `test_corporate_actions`
  and `test_universe_sources`.
- **36/36** historical holding-study replays match exactly across all six
  compared financial/event fields. This includes all twelve original controls
  and both holding-time variants at both capital sizes and windows/all costs.
- Replay evidence is saved in `data/reports/lifecycle_regression_v1/report.json`;
  original datasets and reports remain unchanged. Execution source hashes
  remain in that report; no old hashes were revised to accept new code.
- Full-suite result: **348 tests run, 346 passed, two errors**. Both errors
  are existing optional ML tests whose imports require missing `sklearn`:
  `PipelineTests.test_runner_keeps_final_test_out_of_training_and_compares_same_costs`
  and `WindowTests.test_metrics_handle_one_class_without_claiming_auc`.
  No optional ML packages were installed or test failures hidden.
- No new strategy-return search, fresh price download or account/order call
  was made. Changes compile and `git diff --check` passes.

Raspberry Pi execution remains unverified. 2024-2025 prices stay reserved,
paper submission stays disabled, risk settings stay unapproved, and new data
purchases stay at **$0**.

## Next work and owner responsibilities

Codex's next research task is to establish an explicit no-purchase historical
membership/event dataset or narrow its scope honestly. That includes verifying
security types, aliases, ex/effective dates and actual cash-availability
conventions, then auditing raw price coverage against those lifetimes. Action
mechanics alone do not certify a whole-market backtest. The eight-arm universe/
entry/ranking study remains gated on those inputs and suitable risk diagnostics.

The owner has no risk JSON edits, payment, account upgrade or manual stock
collection to perform now. Any eventual paper trial still needs its separate
readiness review and approval.

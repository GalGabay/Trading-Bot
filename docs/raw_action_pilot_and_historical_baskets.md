# Raw-price pilot and broader historical stock lists

Updated 2026-10-24. New data purchases: **$0**. No orders placed.

## What this accomplishes

1. A real-data accounting pilot checks one Apple investment across its 2020
   split and four ordinary dividends, using unadjusted prices.
2. The daily risk diagnostic now reconciles those events and terminal cash.
3. Two public SEC filings provide dated historical stock lists, retaining
   every disclosed common-stock holding, including later failures/acquisitions.

This establishes source membership for a **fixed historical large-cap basket**.
It does not establish a complete, executable historical US stock universe.
The eight-arm entry/ranking study remains unscored.

## Apple pilot: actual inputs and declared experiment

The [review JSON](aapl_raw_action_pilot_review.json) pins all input hashes,
source URLs, dates, event identifiers, and assumptions. The offline runner is
`backtesting/raw_action_pilot.py`. It checks hashes before interpreting inputs,
refuses unexpected events/incomplete pagination, cross-checks provider terms
against issuer evidence, and preserves a full version-2 universe manifest.

- **505 actual SIP/raw daily candles and 505 saved exchange sessions** from
  2019-01-01 through 2021-01-01 exclusive; 2019 is uninvested feature warmup.
- **253 trading sessions** in the 2020 accounting experiment.
- One predetermined BUY decision after the first completed 2020 session,
  filled at the next session's open; HOLD to the end. No parameter search.
- $10,000 shared cash, 10% entry position cap, whole shares; base costs of
  5 basis points slippage plus half of a 2 basis point spread at entry.
  Loss gates are disabled for this accounting fixture only. No stops or
  personal paper-risk settings are selected by this experiment.
- The clipped listing coverage starts in 2019; it is **not an inferred IPO**.
  [Apple's 2018 Form 10-K](https://www.sec.gov/Archives/edgar/data/320193/000032019318000145/a10-k20189292018.htm)
  establishes the common-stock identity, Nasdaq listing, and AAPL symbol
  before this coverage begins.
- Raw historical candles remain unchanged. Past feature prices/volume are
  rebased only when a split becomes effective. Ordinary dividend price gaps
  remain in raw-price signals. No pre-2020 dividend entitlements are asserted
  because the account owns no shares during the 2019 warmup.

### Payment and knowledge conventions

Provider records identify the historical ex-dates. Their processing dates
are never treated as announcement times. Announcement availability is modeled
conservatively at the **second actual trading-session open after the dated
issuer release**, before the event's ex/effective date.

Issuer payable dates are corroborated by Apple's
[January](https://www.apple.com/newsroom/2020/01/apple-reports-record-first-quarter-results/),
[April](https://www.apple.com/newsroom/2020/04/apple-reports-second-quarter-results/),
[July](https://www.apple.com/newsroom/2020/07/apple-reports-third-quarter-results/),
and [October](https://www.apple.com/newsroom/2020/10/apple-reports-fourth-quarter-results/)
2020 announcements. January's release supplies the February 13 payable date
that was absent from the saved provider row. Its missing provider CUSIP is
documented; this one local event identity is corroborated against the issuer,
not promoted automatically into a permanent market-wide security master.

**Research cash availability = the first actual exchange-session open strictly
after the issuer payable date.** This explicitly delays simulated buying power;
it does not certify when Alpaca credited any account. Broker availability
remains unverified. An earned dividend is a nominal USD receivable until that
modeled session, included in equity but unavailable to buy another stock.

| Ex-session | Issuer amount/share | Issuer payable date | Modeled cash session | Held shares | Earned cash |
| --- | ---: | --- | --- | ---: | ---: |
| 2020-02-07 | $0.77 | 2020-02-13 | 2020-02-14 | 3 | $2.31 |
| 2020-05-08 | $0.82 | 2020-05-14 | 2020-05-15 | 3 | $2.46 |
| 2020-08-07 | $0.82 | 2020-08-13 | 2020-08-14 | 3 | $2.46 |
| 2020-11-06 | $0.205 | 2020-11-12 | 2020-11-13 | 12 | $2.46 |

The July release corroborates the 4-for-1 split and August 31 split-basis
trading date. The August 28 distribution date is not substituted for it.

### Executed pilot results

All **seven declared checks passed**. The January 3 purchase was three shares
at a modeled $297.32829 each. The August split converted them into twelve
shares without a sale, profit, or artificial loss. All four dividends were
credited once, totaling **$9.69**, with no outstanding year-end receivable.

Ending marked equity was **$10,709.99**: $700.30 marked stock gain plus $9.69
dividends. The position remained open; no final sale or final exit cost was
executed. This is one deliberately selected accounting fixture, with zero
completed trades, and cannot approve a strategy under the owner's criteria.

Saved evidence:

- `data/reports/raw_action_pilot_v1/`: original source files and raw candles.
- `data/reports/raw_action_pilot_results_v2/`: final reviewed `universe.json`,
  `financial.json`, `risk.json`, and `report.json`, including execution hashes.
- Earlier `raw_action_pilot_results_v1` is preserved as intermediate evidence;
  its recorded source hashes have not been rewritten.

Reproduce offline from the repository root, retaining the original inputs:

```powershell
.\.venv\Scripts\python.exe -m backtesting.raw_action_pilot --output data/reports/a_fresh_raw_action_pilot
```

The runner refuses an existing output directory. Downloads/reports stay
ignored by Git; the review JSON and extracted membership CSVs are tracked.
The membership CSVs have a scoped Git attribute preventing line-ending
conversion so their reviewed hashes survive Windows/Pi checkouts.
On another machine, source files must be obtained from the pinned references
and match their hashes. Changed vendor history requires a new explicit review,
not silently accepting new hashes. No credentials are stored in these reports.

## Risk diagnostics across company events

`backtesting/risk_diagnostics.py` independently reconstructs holdings, cash,
and outstanding dividend claims before marking each day. Splits convert
quantities before post-split prices are used. Dividend claims enter equity
once and become cash once; they do not count as stock exposure. Terminal
cash removes the holding without requiring a made-up delisted quote.

Invalid share conversions, duplicate entitlements, unmatched/early payments,
incorrect terminal cash, and differences from saved equity/cash/claims fail
explicitly. The engine's supported event order is preserved.

Daily highs/lows provide **conservative bounds**, not an observed intraday
account path. Nominal dividend claim valuation does not model default,
withholding, payment cancellation, or broker processing uncertainty. No
intraday 5% loss compliance is certified by this increment.

All **36 saved holding-study cases** retain exactly the same daily risk
envelopes, using their original, hash-validated inputs and financial reports.
Evidence: `data/reports/action_risk_regression_v1/report.json`.

```powershell
.\.venv\Scripts\python.exe -m backtesting.lifecycle_replay --risk-only --output data/reports/a_fresh_action_risk_replay
```

This rechecks existing simulations; it does not run a new strategy search or
revise old provenance. The previous 36 exact financial replays remain separate
historical evidence in `lifecycle_regression_v1`.

## Broader historical source membership

The extractor, `backtesting/historical_holdings.py`, verifies the fund, the
investment schedule's date, the SEC filing index's report/publication dates,
distinct source security names, and exact aggregate common-stock value.
Every disclosed security row is retained. Source row keys are **not** permanent
security IDs, and company names are **not** executable historical tickers.

| Source | Holdings date | SEC filing date | Conservative availability bound | Security rows | Common-stock value, sum reconciled |
| --- | --- | --- | --- | ---: | ---: |
| [2016 annual report](https://www.sec.gov/Archives/edgar/data/884394/000119312516777823/d235904dn30d.htm) | 2016-09-30 | 2016-11-28 | 2016-11-30 UTC | 506 | $197,172,469,106 |
| [2020 annual report](https://www.sec.gov/Archives/edgar/data/884394/000119312520305082/d72640dn30d.htm) | 2020-09-30 | 2020-11-30 | 2020-12-02 UTC | 505 | $293,908,088,428 |

The associated [2016 index](https://www.sec.gov/Archives/edgar/data/884394/000119312516777823/0001193125-16-777823-index.html)
and [2020 index](https://www.sec.gov/Archives/edgar/data/884394/000119312520305082/0001193125-20-305082-index.html)
establish publication dates. The two-calendar-day availability bound avoids
claiming an exact public release time. Never use a holdings report date as its
availability date. `require_available()` rejects earlier or naive trade starts.

Tracked, complete extracted rows:

- [2016: 506 security rows](research_data/spy_2016_disclosed_holdings.csv).
- [2020: 505 security rows](research_data/spy_2020_disclosed_holdings.csv).
- [Source review, hashes and outstanding gates](historical_membership_source_review.json).

Share classes are separate securities. Retained examples include Bed Bath &
Beyond and Aetna in 2016, and SVB Financial Group and Twitter in 2020. They
are not removed because they later failed, disappeared, or were acquired.
Footnote suffixes and share-class labels remain in the original source names.
Original full unresolved registers are saved beside the filings in the local
input directory.

Rebuild the first register offline into a new file:

```powershell
.\.venv\Scripts\python.exe -m backtesting.historical_holdings --filing data/reports/raw_action_pilot_v1/spy_2016_filing.html --index data/reports/raw_action_pilot_v1/spy_2016_filing_index.html --asof 2016-09-30 --source-url https://www.sec.gov/Archives/edgar/data/884394/000119312516777823/d235904dn30d.htm --output data/reports/a_fresh_2016_membership.json
```

### Scope and remaining work

The 2016 disclosed basket can be fixed **before 2017** and followed thereafter,
subject to identity/action/price checks. The 2020 list can only support trading
after its actual publication; applying it to 2017 would introduce look-ahead.
Neither list tracks subsequent additions/removals from the index or includes
every listed US stock. US-listed foreign issuers and REIT/share-class rows
need explicit classification against the eventual eligibility rules.

Next engineering work is to map the **2016 cohort's 506 retained rows** to dated
security identities and ticker aliases, then audit raw price, company-action,
and terminal-outcome coverage. Unknown or unsupported cases must stay visible
as blockers, not be dropped to create a profitable survivor sample. Stock
mergers, spin-offs, fractional cash, and uncertain recoveries may require more
adapters. One Apple pilot cannot certify their handling.

This fixed 2016 cohort is a concrete no-purchase candidate for a narrower
broad-basket experiment. It does not silently replace the original study's
daily all-eligible-US-stock scope. Before scoring, publish the mapping/coverage
report and freeze the exact feasible scope and entry/ranking protocol. The
owner need not collect stocks, change risk JSON, or purchase data for this
engineering step. A material scope revision should be presented for review
before interpreting strategy returns.

## Optional ML dependency

`scikit-learn` is unnecessary for this rule-only accounting/data work. To
enable ML tests/research, open the VS Code PowerShell terminal **in the repo
root on Windows** and install into the existing project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe -m unittest tests.test_ml_research -v
```

The requirements file includes core dependencies, compatible NumPy,
scikit-learn, and XGBoost. No global installation or source-code edit is needed.
Python's import name is `sklearn`; its package name is `scikit-learn`.
The project follows the [scikit-learn environment installation guidance](https://scikit-learn.org/stable/install.html).
Install dependencies separately in a Pi virtual environment when deploying;
never copy the Windows `.venv`. No ML package was installed by this change.

## Verification and boundaries

Executed on Windows:

- **118/118 focused tests passed**, including 33 new tests covering the action
  risk ledger, source extraction/publication bounds and pilot input review.
- **381 tests ran in the full suite: 379 passed, two errors.** Both are existing
  optional ML tests blocked by `ModuleNotFoundError: No module named 'sklearn'`:
  `PipelineTests.test_runner_keeps_final_test_out_of_training_and_compares_same_costs`
  and `WindowTests.test_metrics_handle_one_class_without_claiming_auc`.
  No tests were hidden or changed to skips, and no dependency was installed.
- The actual raw-price pilot passed all seven declared checks.
- All 36 saved daily-risk envelope cases matched exactly.
- Python compilation and `git diff --check` passed.

Commands:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_historical_holdings tests.test_raw_action_pilot tests.test_action_risk tests.test_corporate_actions tests.test_risk_diagnostics tests.test_universe tests.test_universe_sources -q
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Unit tests use synthetic candles/calendars and temporary source files, with
no API calls. The real pilot and historical-envelope replay use saved,
reviewed data. Public documents and 2019-2020 raw prices/calendar were acquired
read-only for this increment; no account or order action was performed.
2024-2025 price data remain reserved. Personal paper-risk limits and order
submission remain unapproved/disabled. Raspberry Pi execution is unverified.

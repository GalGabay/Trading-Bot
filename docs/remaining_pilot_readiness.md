# Apple, CBRE and SPY: cached evidence review

**Follow-up, 2026-10-29:** the owner approved the explicitly labeled
diagnostic assumptions, and [all 24 simulations are complete](limited_pilot_experiment_results.md).
That approval does not certify the missing independent evidence below or
approve a paper candidate. The cached review remains the preserved baseline.

Date: 2026-10-27. **Review completed offline; no new strategy returns calculated.**
JPMorgan collection remains parked. No purchases, downloads, credentials,
broker/account requests, orders or reserved candle reads were involved.

## What is ready, and what is not

We have usable saved **price observations** for all three histories from
**January 4, 2016 through December 29, 2023**: 2,012 sessions each, **6,036
candles** in total. They match their raw responses and pass the actual
calendar/OHLCV validation with no warnings. No gaps were filled.

The review reconciles **66 events**: 32 Apple dividends, one Apple split,
32 SPY distributions and one CBRE ticker change. The old primary-source CSV
replays byte for byte. These facts support preparing a finite, explicitly
labeled exploratory experiment; they do not complete the strict evidence
gate or approve another performance run.

| History and exact coverage | Supported by saved evidence | Remaining limits and their relevance |
| --- | --- | --- |
| AAPL, 2016–2023 | All 32 nominal dividend amounts, declaration/record/payable dates; the July 2020 release supports the four-for-one split effective August 31; provider/raw candles agree | All 32 dividend ex-dates remain provider cross-references: the issuer table has no ex-date column. Entitlement and full-period identity/action completeness are not independently certified. A diagnostic can explicitly disclose vendor reliance; strict scoring stays blocked. |
| CBRE/CBG, 2016–2023 | Class A/NYSE issuer anchors, the March 19, 2018 ticker boundary, and the issuer's retrospective statement that no common cash dividends were paid since inception | No independent all-category noncash-action completeness certificate. The original fund REIT label remains unresolved, but that tax-subtype question does not itself prevent inspecting Class A price data. A study filtering REITs still needs that classification resolved. |
| SPY, 2016–2023, context only | Price observations, 2016/2020 fund identity anchors and 32 fund distributions with explicit ex-dates | Full-period identity/action certification remains incomplete. Gain-cell, publication-time and payment details affect a dividend-inclusive reference; they do not enter a completed raw-price EMA200 market filter. Context-only use still needs its scope/vendor-reliance choice stated. |

These are retrospective evidence reviews, not information that the historical
strategy automatically knew. Later filings cannot be used to select stocks
or exit positions earlier in a simulation.

## Exact event and date findings

### Apple

All 32 dividend source amounts match their provider cross-references exactly.
Issuer payable terms are available for all 32, including the 17 omissions in
the original provider response. Proposed date-only knowledge bounds, at the
second subsequent actual session open, fall before their provider ex-opens.
This checks a proposed convention; it does not approve it or independently
establish those ex-dates.

The four-for-one split has independent issuer support for the ratio and
August 31, 2020 effective trading boundary. A raw-data simulation must adjust
held share quantities, per-share cost/stops and historical feature views
consistently, only when the split becomes effective. A price drop caused by
the split is not a trading loss. The existing strict evidence flags remain
unchanged; no prospective schedule has been approved by this audit.

### CBRE

The reconstructed stream contains **556 vendor CBG labels** and **1,456 vendor
CBRE labels**. The actual March 19 boundary candle was supplied under the
vendor's CBG label and retains that `source_symbol`; its reviewed market
alias is CBRE. The source values were not fabricated or edited. The ticker
change is the same Class A security, not an automatic sale, purchase or
share-quantity change.

The 2016 and 2023 issuer filings corroborate common Class A listings and
the no-cash-dividend statement. The latter supports that stated cash-dividend
history through its reporting scope; it does not prove the absence of stock
distributions, splits, reorganizations or other categories. Generic clauses
about possible stock splits in incentive plans are not evidence that a split
actually happened. No new event was invented from those clauses.

### SPY: context and a passive total-return benchmark are separate uses

The saved fund schedule independently supplies the three distributions absent
from provider data: March 18, 2016; June 15, 2018; and December 15, 2023.
The last is contractually payable January 31, 2024. The saved calendar ends
in 2023, so it cannot establish a modeled credit instant for that payment.
No 2024 session or candle was invented or read.

The 32 source rows contain **28 blank short-term gain cells and 30 blank
long-term gain cells**. Those blanks remain unknown, not zero. One shared
dividend amount differs by $0.0000001 per unit between provider and displayed
fund precision. The source table has no declaration timestamps. These details
remain blockers for the proposed fully reviewed passive total-return reference.

For a **price-only SPY market filter**, dividends, gain cells, credit timing
and that amount-precision choice are not inputs. We can leave the passive
reference unavailable while proposing the raw-price filter, with its provider
identity/action reliance disclosed. SPY must not be counted as a third traded
stock or presented as a completed total-return benchmark.

## What supports the next backtest

The exact saved files support **preparing** this [finite experiment proposal](next_pilot_experiment_proposal.md):

- Candidate stocks: AAPL and CBRE; SPY context only. No replacements ranked
  by past returns, new price downloads, tighter entries or ML search.
- Already explored development windows: 2017–2021 with 2016 warmup, then a
  separate 2022–2023 account with 2019–2021 warmup. The windows are specified
  before scores; neither is an untouched final evaluation.
- One existing breakout/continuation rule, the old conservative allocation,
  two cost cases and three explicit cash-availability scenarios. At most
  **24 strategy runs**, with every result retained.

This route needs an **explicitly labeled diagnostic mode**. It would accept
named vendor inputs with visible evidence gaps and model cash timing. It
must not mark assumptions as independently verified entitlement or broker
credit. Under the original strict standard, **zero full-period histories
are newly cleared for scoring**. Owner approval can accept a research model;
it cannot turn absent facts into verified evidence or override contradictory
terms, invalid prices, missing sessions or failed accounting checks.

The separate proposal is reviewable now. It is unapproved, non-executable
and schedules no automatic performance run. No new owner risk percentages
are requested. The 506-row register, nine-stock control, 6% annual return
criterion, 5% drawdown rejection and five-instrument/30-trade minimum remain
unchanged. Two traded stocks cannot satisfy the investment-universe gate.

## When can we see returns again?

**A small exploratory experiment can be the next research implementation**
after you accept its listed vendor/scope/timing assumptions. I then need to
implement and verify that separate mode and its event/accounting handling
before running the finite batch. There is no further JPMorgan search or
paid-data step in this route. It can report profits or losses; it is not a
promise of better returns.

I cannot give an honest elapsed-time or completion-date estimate before that
verification. If the checks fail, the failure must be fixed or reported
before scores. The larger historical-universe profit comparison still has
incomplete price/lifecycle coverage and no dependable completion date.
The exploratory two-stock run cannot replace it or approve paper trading.

The old 5% per-position entry cap also leaves most money uninvested with just
two names. We are checking data/accounting behavior with the frozen policy,
not claiming this tiny basket should reach 6% annually or raising exposure
to make a return chart look better.

## Evidence and reproduction

- [Frozen offline review inputs](remaining_pilot_review.json).
- [Tracked final summary](remaining_pilot_summary.json).
- [66-row event inventory](research_data/remaining_pilot_events.csv), with
  source hashes, independent versus provider dates, proposed cash dates and
  unapproved flags.
- [11 identity/source fact checks](research_data/remaining_pilot_identity_facts.csv).
- [24 stream/year coverage rows](research_data/remaining_pilot_year_coverage.csv).

Run from the repository root, with the local environment active:

```powershell
python -m backtesting.pilot_readiness_review --output data/reports/a_fresh_remaining_pilot_review
```

On Windows this run used `.\.venv\Scripts\python.exe`; the Pi needs its own
environment and has not been checked. A clone without the ignored raw files
cannot replay the review. The command refuses existing output directories,
checks pinned files, blocks socket connections during review and does not
load credentials or invoke a trading engine. Local final evidence is in
`data/reports/remaining_pilot_review_v3`.

The first local execution hit a new-runner schema bug: it expected a split
`effective_date`, while the saved response uses `ex_date`. The reader now
accepts the supported explicit keys without changing the record. The failed
v1 output/reason is preserved separately. The successful v2 review is also
retained; final v3 uses portable forward-slash source paths and also blocks
`connect_ex`. The final run passed with the same financial inputs and counts.

**Executed:** input/source hashes, raw-payload reconstruction, calendar/OHLCV
validation, exact amount/date joins, proposed timing bounds, alias checks and
source replay. **Not executed:** unit-test suites, strategy simulations, ML,
payment-sensitivity runs or Pi verification. These data checks are not a
new unit-test total, strategy acceptance result or paper authorization.

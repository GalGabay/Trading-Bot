# Study C: investment goal-fit audit results

Completed **2026-10-24**, under the [registered audit protocol](study_c_goal_fit_protocol.md).
**Decision: the frozen breakout candidate does not qualify for your approved
investment objective.** Keep 2024-2025 reserved and do not advance this
candidate to investment-oriented paper trading.

The owner approved 6% annual account return after pessimistic modeled costs,
a 5% running-peak drawdown rejection level, and the other criteria in the
[acceptance plan](investment_acceptance_proposal.md). The versioned research
policy is `config/research_acceptance.json`. Personal paper-risk settings
remain empty/unapproved in `config/risk_limits.json`; no orders were placed.

## What was evaluated

Twelve unchanged-strategy simulations: two account sizes ($100,000 and
$10,000), two windows, and three cost cases. Use the same twelve instruments,
SIP/all-adjusted bars, fixed 55/20 breakout and stock/SPY EMA200 filters,
initial three-ATR14 stop, ten-session reentry cooldown, volatility sizing,
5% position / 35% total entry caps, 0.5% planned stop-risk cap, and seven
maximum positions. The historical 3% daily / 10% drawdown entry halts were
preserved. They are different from the owner's acceptance criteria.

The full window is a continuous 2017-2023 account, with 2016 warmup. The
recent window is an independent 2022-2023 account with the original 2019
warmup history, matching C-R3. Neither resets equity or holdings at an
internal year boundary. They overlap and are not independent evidence.
The $10,000 case changes initial capital only; it does not resize the actual
Alpaca account or tune the strategy.

The $100,000 full-window results reproduced every C-R4 metric and fill;
the recent-window results reproduced C-R3 exactly, under all three costs.
Every one of the twelve fill ledgers reconciled to every saved closing
equity/exposure point and to the final positions. Dataset, calendar, source,
reference, policy, and protocol hashes are recorded in the local JSON.

## Returns against the approved 6% annual hurdle

All annual returns below use the whole account and include estimated final
sale costs for remaining positions. Daily holdings are marked to market;
there is no forced annual liquidation.

| Starting account | Window | Pessimistic total after estimated exits | Annualized net return | Max closing drawdown | Closed trades | Decision |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| $100,000 | 2017-2023 | +16.292% | **+2.180%** | -4.584% | 163 | Does not qualify |
| $100,000 | 2022-2023 | +1.192% | **+0.594%** | -3.457% | 42 | Does not qualify |
| $10,000 | 2017-2023 | +9.944% | **+1.363%** | -4.628% | 163 | Does not qualify |
| $10,000 | 2022-2023 | +0.230% | **+0.115%** | -3.198% | 41 | Does not qualify |

The existing +16.392% figure marks the open holdings without a final sale
cost. The +16.292% here deducts that estimate; neither is a yearly return.
At $10,000, whole shares consume larger chunks of a position budget, and a
fixed $1 fee is a larger fraction of capital. The smaller account cannot be
obtained by dividing every old quantity and profit by ten.

### Individual acceptance checks under pessimistic costs

- **Return:** All four accounts/windows fail the 6% annual hurdle.
- **Closing drawdown:** All stay below 5%. Both seven-year accounts enter the
  approved 4%-5% concern band and require review, rather than an unqualified
  risk clearance.
- **Closing daily loss:** All stay below 2%; the worst days were -1.660%,
  -0.518%, -1.325%, and -0.439%, respectively in the table's order.
- **Breadth:** All satisfy the 30-trade and five-instrument evidence floors.
- **Completed-trade quality:** Both seven-year accounts have positive
  realized profit and profit factors above 1.2. Both recent accounts fail:
  realized P&L is negative and profit factor is 0.867 at $100,000 and 0.706
  at $10,000.
- **Halts:** No permanent halt occurred in these accounts/windows.
- **Actual intraday drawdown:** Unmeasured; daily bars do not produce an
  observed intraday portfolio path. This remains inconclusive.

A measurable failure is enough to reject investment fit, even if another
check is inconclusive. The earlier studies retain their original screen
results; this is a subsequent review against newly approved owner goals.

## Where the return went

Pessimistic full-window accounting, before estimated final sales:

| Item | $100,000 account | $10,000 account |
| --- | ---: | ---: |
| Realized closed-trade P&L | +$14,285.08 | +$854.53 |
| Open marked P&L | +$2,106.94 | +$153.74 |
| Net account profit | **+$16,392.02** | **+$1,008.27** |
| Modeled slippage | $3,258.74 | $277.47 |
| Modeled half-spread costs | $814.69 | $69.37 |
| Order commissions | $333.00 | $333.00 |
| Total modeled trading costs already included in net profit | **$4,406.43** | **$679.83** |
| Estimated additional cost to close remaining positions | $100.26 | $13.91 |
| Net profit after estimated final exits | **+$16,291.77** | **+$994.35** |
| Profit needed for seven years at 6% compounded | $50,363.03 | $5,036.30 |

The costs are scenarios, not assertions about actual broker fees. Slippage
and spread are reconstructed against each fill's proper reference; a stop
fill's reference is its stop/gap execution basis, not blindly the session
open. Commissions and both sides of completed trades are included.

Adding the costs back to the same fills gives approximately $20,798.45 and
$1,688.10 of profit, still well short of the six-percent growth goals. This
is an accounting decomposition, not the result of rerunning the strategy
without costs. Removing costs can change later share quantities and trades.
The separately simulated optimistic cases also failed the annual hurdle.

### Idle capital

| Window / size | Average closing exposure | Average closing cash fraction | Sessions entirely in cash |
| --- | ---: | ---: | ---: |
| 2017-2023 / $100,000 | 19.07% | 80.93% | 398 / 1,760 |
| 2017-2023 / $10,000 | 16.53% | 83.47% | 398 / 1,760 |
| 2022-2023 / $100,000 | 9.28% | 90.72% | 260 / 501 |
| 2022-2023 / $10,000 | 7.62% | 92.38% | 264 / 501 |

Cash earned zero in every case. No interest was credited without evidence
of broker eligibility and an applicable historical rate. A separate realistic
cash-return analysis could change the total investment comparison, but would
not establish a stronger trading signal. Do not divide total account return
by average exposure to claim a tradable annual return on invested capital.

Low capital use is one explanation for the modest return. Simply increasing
allocation is not an accepted fix: it increases losses too, and the older
full-allocation breakout reference hit a permanent daily-loss halt. The
recent negative realized P&L is a separate signal-quality concern.

## Improved risk reporting

The new `backtesting/risk_diagnostics.py` rebuilds cash and positions from
fills, checks their closing marks, and computes a conservative daily-OHLC
equity envelope. It handles both opening-gap and intraday-touched stops.
For touched stops, each holding may contribute either its pre-exit price
range or its after-exit net proceeds, independently of the other holdings.

| Size / window | Observed max closing drawdown | Conservative drawdown bound | Status of actual intraday equity |
| --- | ---: | ---: | --- |
| $100,000 / 2017-2023 | -4.584% | -4.979% | Not observed |
| $10,000 / 2017-2023 | -4.628% | -5.008% | Not observed |
| $100,000 / 2022-2023 | -3.457% | -3.601% | Not observed |
| $10,000 / 2022-2023 | -3.198% | -3.336% | Not observed |

The long-window worst bound occurs on March 8, 2019; the recent one occurs
on April 25, 2023. The envelope permits adverse price combinations and an
intraday high-before-low order that may never have happened. The $10,000
bound beyond 5% therefore **does not prove an observed 5% breach**. It means
this conservative daily analysis cannot establish that the concern level
was respected throughout every session. Even the bound below 5% in the
larger account is conditional on the simulator's execution model, not a
guarantee about real fills or future losses.

No intraday candles or timestamps were manufactured. The envelopes are
retrospective diagnostics, never inputs to entry sizing, signals, or exits.
Finer data would need a separate availability/coverage audit if the risk
question must be resolved. It is not needed to conclude that this candidate
already fails the return goal.

## Passive references and saved stress evidence

Fixed passive references use 20% and 35% initial SPY allocation with remaining
cash earning zero, the same cost cases, and whole-share sizing. They do not
rebalance, diversify, or implement the candidate's halts or position cap.

Seven-year pessimistic results after estimated final exit costs:

| Account | Candidate return / closing drawdown | 20%-initial SPY return / drawdown | 35%-initial SPY return / drawdown |
| --- | --- | --- | --- |
| $100,000 | +16.292% / -4.584% | +26.969% / -9.508% | +47.330% / -15.478% |
| $10,000 | +9.944% / -4.628% | +26.422% / -9.341% | +44.932% / -14.826% |

All cost cases and the recent windows are in the JSON. These passive
allocations earned more in the long period but had larger closing losses
than the approved 5% concern. They are context, not approved alternatives.
Their weights drifted as prices changed; initial allocation is not average
exposure and these are not exactly risk-matched portfolios.

The audit separately reviews the already registered C-R4 2017-2018 and
C-R3 2022-2023 priority, delay/stop-cost, and twelve stock-removal results
under the new five-percent closing-drawdown ceiling. C-R4's two channel
neighbors are confined to 2017-2018. There are no equivalent recorded
recent-period channel results for the selected smaller sizing, or $10,000
stress runs. These gaps are marked explicitly; old $100,000 stress results
cannot certify small-account robustness or intraday risk. No new variation
or parameter search was run.
All thirty reused priority/delay/removal/channel cases were profitable and
below 5% closing drawdown in their recorded scopes. That does not repair
the main candidate's failed return and recent closed-trade criteria.

## Your trading-style and sizing questions

**Yes: the simulated account sells a holding, returns net proceeds to shared
cash, and can buy another instrument on a qualifying signal or wait in cash.**
Open-session exits are processed before pending entries, allowing the model
to reuse proceeds. A new discretionary order needs an earlier completed-bar
signal. This does not establish that broker buying power or unsettled cash
is available on identical terms; the actual paper execution workflow is
still disabled and incomplete.

There is no mandatory three-week holding period. The frozen rule sells on
the prior 20-session low, a stock/market trend-filter exit, or its initial
three-ATR protective-stop proxy. It may keep a position for days, weeks, or
months. Completed trades averaged **61.42 calendar days** over 2017-2023,
and **29.71 days** in the separate $100,000 2022-2023 account. It is better
described as medium-term daily trend/breakout trading than a strict
three-week swing schedule. No live/paper bot is currently carrying it out.

**Sizing is based on risk and available capital, not a validated prediction
of which stock will perform best.** The research rule uses:

```text
target position fraction = min(5%, 1% / estimated annual return volatility)
```

At $10,000 equity, 20% annualized volatility gives a 5% target ($500), while
40% volatility gives a 2.5% target ($250). Stop distance, the 0.5% planned
stop-risk cap ($50 at $10,000), whole shares, cash, portfolio exposure, and
the seven-position cap can reduce or block that purchase. These ceilings
are different quantities: $500 of stock value is not $500 of planned loss.
No daily rebalancing is applied to existing positions.

This frozen rule has no calibrated win probability or confidence ranking.
Competing pending buys use the recorded alphabetical priority; the reverse
order was a research stress check, not a predicted-profit ranking.
Its signal-confidence field is not a position-sizing forecast. The optional
ML prototype is not active in this study; confidence-based sizing would be
a separate hypothesis requiring independent research before use.

## Reproduction, verification, and limits

From the repository root, with the existing C-R3/C-R4 audited local inputs:

```powershell
.venv\Scripts\python.exe -m backtesting.goal_fit --output-dir data/reports/study_c_goal_fit_new
```

On the Pi use its own `python -m ...` environment. Pick a fresh output path.
The command makes no API calls and accepts no later date range. It checks
the original reference chain, source/protocol/data/calendar hashes, recorded
development approval, exact reference fills/metrics, and every replay's
ledger invariants. It fails on incomplete prices or inconsistent accounting.
Legacy absolute Windows source paths in the original reports are resolved
against the current repository, so the source checks can also run after
the audited artifacts are transferred to the Pi.

The final ignored local report is `data/reports/study_c_goal_fit_final/report.json`.
Individual account/window files retain complete cases, fills, equity,
envelope rows, checks, attribution, and benchmarks. The final environment
was Python 3.12.3, NumPy 2.5.3, pandas 2.3.3, alpaca-py 0.10.0.

Verification in the original audit consisted of the twelve authorized replays, six
exact original-reference comparisons, and all twelve complete ledger
reconciliations. Unit tests were not added or run at that point; the follow-up
below records their subsequent completion.
No Pi execution, actual cash-yield validation, or intraday data acquisition
was performed. Present-day survivor selection, adjusted historical prices,
repeated development use, and execution assumptions remain limitations.

The first complete audit at `data/reports/study_c_goal_fit/` was followed
by a final replay after improving legacy Windows-path resolution for Pi
portability. Strategy parameters and acceptance criteria were unchanged.
The final artifact path above supersedes that first run.

### Subsequent focused verification and proposal

The next authorized work added **41 focused audit tests** in
`tests/test_goal_fit.py` and `tests/test_risk_diagnostics.py`.
**115 focused/related tests passed**. The full suite ran **250 tests: 248
passed and two errored**, both existing optional ML cases importing missing
`scikit-learn`. No final test assertion failed.

The tests exposed defensive-validation gaps: malformed numeric policy
settings raised unclear type errors, legacy source paths could resolve
outside the intended code folders, and the standalone envelope helper did
not reject some nonfinite/impossible OHLC prices. The fixes reject these
inputs while retaining the original calculation for valid inputs.

Every risk envelope, goal decision, and attribution result in all twelve
saved audit cases was recomputed with the stricter helpers and matched
**exactly**. No new strategy simulation was needed, and the original JSON
report and its original source hashes were preserved. The separate local
verification record is `data/reports/study_c_goal_fit_helper_verification.json`.
Its hashes identify the new reporting code. No 2024-2025 prices were read,
paper settings changed, orders placed, or packages installed.

The owner's suggestion about old holdings is now a concrete
[holding-time/capital-reuse study proposal](holding_period_study_proposal.md).
It defined three fixed arms, causal session counting, evidence requirements,
and a finite replay budget. The owner subsequently approved an amendment
allowing reviewed continuation beyond session 60; the
[completed study](holding_period_study_results.md) found neither new variant
met the approved investment criteria. Its amended protocol and new source
hashes are separate from this original audit.

## What comes next and who does it

Keep this candidate as a frozen reference and **stop advancing it toward
paper trading under the approved investment criteria**. Do not spend
2024-2025 or add exposure/ML to rescue the old chart.

**Codex's next proposed work:** prepare one concrete, finite alternative
study proposal that names the hypothesis, candidate variants, development
windows, cost/risk checks, and stopping rule before evaluation. Record
the accumulated trial history. Retiring this strategy line must remain a
valid outcome; no candidate in this project has established that it meets
all the approved criteria. This audit does not authorize a new strategy search.
The focused audit tests above are complete. The concrete
[holding-period study](holding_period_study_results.md) is now complete under
the owner's amended approval. Its proposed next step is broader-universe
data feasibility, rather than further automatic age-rule optimization.

**Owner:** Nothing more needs configuring to finish this audit. Review this
result, then decide whether the separate next study is worthwhile once its
scope is presented. No need to edit Python or approve the paper-risk JSON
now. Any eventual paper trial still requires reviewed qualifying research,
safe broker exits/fill accounting/recovery, actual account review, approved
personal limits, and explicit permission to start.

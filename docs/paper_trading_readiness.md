# How far are we from paper trading?

**Latest observation implementation, October 31: [repeat controller](shadow_repeat.md).**
Calendar-aware repetition, status, budgets and restart handling are implemented
and initialized offline. New controller tests and a reviewed tick remain due;
no recurring task or paper trading is active. This continues the observation
route without new risk approvals or purchases. Prior Steps 1-4 remain complete.
Earlier status entries follow historically.

**Current verified status, October 31, 2026: [observer tests and first collection complete](shadow_observer_validation_results_2026-10-31.md).**
137 offline tests pass, including 66 new observer tests; Windows SQLite handle
cleanup is fixed. One bounded read-only collection evaluated October 30 using
43 GETs and 209 daily candles per stream. All 20 watched stocks plus SPY passed
coverage checks. Three BUY / 17 HOLD signals produced a 10.40% hypothetical
allocation from the unchanged flat $10,000 reference. Saved replay matches
exactly and duplicate recording leaves one observation. No orders, fills,
purchases, account requests or reserved-year candle reads occurred. No scheduler
is installed and Pi execution remains unverified. Next: calendar-aware repeated
observation and a concrete schedule, followed by the remaining paper-execution
work. Personal risk approval is not needed for observation. Earlier entries
below are historical; previous research Steps 1-4 remain complete.

**Current implementation, October 31, 2026: [shadow observer](shadow_observer.md).**
The daily no-order observer now records signals, data blockers and reference
allocations toward a 70% target under an 85% entry ceiling. It uses a separate
journal and JSON/Markdown reports, with saved-data observation or explicit
bounded IEX collection. It does not create fills, carry virtual positions,
report profit or access account/order endpoints. The 20-name default watchlist
is an observation sample, not the historical 76-stock or approved paper universe.
Personal risk approvals do not block observation. Syntax compilation and CLI
help were checked; new unit tests and the first current-data run remain due.
No observer session, background task or paper orders started in this task.
Next: focused offline observer tests, then review one collection before repeat
scheduling. Prior research Steps 1-4 remain complete. Earlier entries follow.

**Current proposal, October 31, 2026:** the
[entry, risk and capital-deployment follow-up](subset_followup_improvement_proposal_2026-10-31.md)
is written for review: six fixed policies, 24 new attempts including four
baseline checks, one worker, ten minutes per case and 90 minutes overall.
It separates ranking/entry changes, earlier risk controls, an 85% entry ceiling
and a weekly 70% stock-deployment target. The owner's preference for roughly
70% invested and a possible 80-85% ceiling is recorded; risk-first exceptions
and the proposed utilization tolerance are not yet accepted. No performance
run or paper activation is authorized by the proposal. Research acceptance
remains 6% annual return/5% drawdown. The document also defines a route through
shadow observation and verified execution to a separately approved paper
engineering trial. Personal risk approval remains due before paper orders.
The preceding comparison's Steps 1-4 remain complete; earlier status entries
below are historical.

**Latest completed research, 2026-10-30: Steps 3 and 4 complete.**
[Final comparison and assessment](subset_comparison_results_2026-10-30.md)
retain all 24 distinct cases and 25 lifetime attempts, including the original
timeout. The approved recovery completed without failures in 18.97 minutes.
320 focused offline tests passed before recovery; all completed case ledgers,
external-price checks and per-stock profit contributions reconcile.
**Decision: do not promote this frozen candidate to paper trading.** The
76-stock base-cost returns were +6.29% total for 2017-2021 and -2.60% for
2022-2023; pessimistic returns were -2.66% and -10.96%. None meets the 6%
annual return goal, and broader cases exceed the 5% drawdown limit.
My next work is a bounded follow-up research proposal; you review that proposal
before another performance batch. No personal risk-file edit, installation,
purchase or paper activation is needed now. The original full-100 study remains
separate and blocked; earlier entries below are historical.

**Latest progress, 2026-10-30: Step 3 recovery is approved and running.**
[Approval, implementation and verification](subset_recovery_approved_2026-10-30.md)
retain the original four attempts and allow at most 21 additional attempts,
25 lifetime attempts, one worker, ten minutes per case and a separate 60-minute
segment. 320 offline tests, three exact saved financial/risk replays and six
synthetic control checks passed before execution. Strategy/data/risk settings
are unchanged; no purchase, configuration or further owner reply is needed
within this scope. Step 4 remains pending. Earlier entries below are historical.

**Current progress, 2026-10-30: Step 3 stopped, incomplete.**
[Three completed cases and one timeout](subset_partial_results_2026-10-30.md) are preserved.
The 76-stock 2017?2021 base-cost case returned +6.29% total (+1.23% annualized),
with a ?10.02% closing drawdown; it fails the approved return/drawdown goals.
No pessimistic-cost or 2022?2023 case completed. Post-stop fixes pass 184 offline
tests and all three saved financial reports match exactly. No retry ran.
A [separate recovery proposal](subset_recovery_for_review.md) needs your decision because it
requires one retry, 25 lifetime attempts and a fresh 60-minute window. No risk
setting, purchase or installation is needed. Step 4 and paper activation remain
incomplete. Earlier status entries below describe historical work.

**Current progress, 2026-10-30: Step 2 verified; Step 3 is next.**
[The approved subset now connects to the simulator](subset_simulator_integration.md),
with 236 passing focused tests, 36 saved-data accounting checks and six
synthetic financial compatibility comparisons. Runtime/attempt enforcement and
runner profiling must precede the approved 24-case performance comparison.
No new research return results yet. Step 4 will explain those results and the
decision; paper activation remains separate. No new owner configuration or
purchase is required within this scope. Earlier status entries follow.

**Current route, 2026-10-30:** the owner approved a separate 76-stock exploratory
comparison, capped at 24 strategy attempts after integration checks pass.
[Step 1 subset inputs are prepared](approved_subset_preparation_results.md).
**Step 2 is next:** connect the pending-rights ledger to the portfolio simulator
and verify control accounting. Step 3 runs the comparison; Step 4 evaluates and
explains it. No new profit/loss batch has run and no paper trial is approved.
The original 100-stock study remains blocked by 188 economic-data rows; its
scope and evidence are preserved. Availability-selected subset results alone
cannot establish paper readiness. See the [current tracker](broad_backtest_step_tracker.md).

The status entries below describe earlier work.

**Latest verification, still Step 1:**
[641 tests pass and MAC's reported conversion formula is recorded](broad_holder_tests_results_2026-10-30.md).
All three accounting scenarios prepare offline. Ownership/settlement and other
economic terms still leave 188 overlapping blocking rows before Step 2. No new
performance run or paper activation occurred. Earlier entries follow.

**Latest holder-term work, still Step 1:**
[K/KLG ownership and SLG ex-date corroboration](broad_holder_terms_results_2026-10-30.md)
reduce overlapping data gates from 191 to 188. All three scenario preparations
complete offline; focused new-module tests and unresolved election/event terms
remain before Step 2. No new performance run or paper activation occurred.
Earlier entries below describe earlier code.

**Latest status: Step 1 of the [four-step research track](broad_backtest_step_tracker.md).**
[571 offline tests pass](broad_action_election_results_2026-10-30.md), including
87 new action/election/cash-merger tests. Saved-event preparation passes, but
191 overlapping data gates still block Step 2 integration. No expanded
performance batch or paper activation occurred. Earlier status entries follow.

**2026-10-30:** [diagnostic defaults approved; focused tests and primary-event
review completed](diagnostic_tests_and_event_review_2026-10-30.md).
The new readiness gate still blocks unresolved event/identity inputs. Full
Step 2 engine integration and expanded return experiments have not started.
No additional owner setup or repeat approval of 70% / 5% / 20 is needed now.

**Current Step 1 preparation:** [event mappings revised and diagnostic accounting
implemented](broad_mapping_and_accounting_results.md). The owner can now review
[concrete simulation assumptions](broad_diagnostic_assumptions_for_review.md).
New module tests, remaining economic terms and Step 2 integration remain;
no new return experiment or paper activation occurred.

**Latest verification:** [193 tests passed; Step 1 event review progressed](broad_input_verification_results.md).
Step 1 remains incomplete, and Step 2 performance integration has not started.
Current work requires no owner setup or purchase. There are no new return results.

Status: 2026-10-29.

**Latest Step 1 result:** [price reconstruction is complete for the configured
candidate intervals](broad_input_preparation_results.md): 100 original members,
119 separate streams and 203,683 source-matched observations. Successor
prices have been collected, but primary archival stopped at SEC 403 and
event/delivery admission is incomplete. We are still at Step 1's evidence
gate below, not ready to report broader performance. The earlier four
mixed-history flags led to additional DOW/HCP corrections; original evidence
and all members are retained. No new unit suite or strategy run occurred.

## Current route from research to paper trading

**Owner decision:** 70% total account entry exposure is selected for the next
research design, recorded in [the decision journal](research_exposure_decision.json).
At $10,000 equity, that means up to about $7,000 invested across stocks when
entering trades. It is not a 70% per-stock allocation or a requirement to
invest $7,000. Do not ask the owner to approve this same research cap again.
The 90% arm is not selected for the current design. The old proposal is retained
as a dated record; remaining assumptions, position slots and the run allowance
are not automatically approved by this exposure decision. Paper settings
remain disabled and separate.

**Return results already exist:** the latest completed
[two-stock experiment](limited_pilot_experiment_results.md), using $10,000 and
pessimistic costs, returned **+3.12% total over 2017-2021** (about +0.62%
annualized) and **-0.53% total over 2022-2023** (about -0.27% annualized), after
estimated final share exits. These are separate simulated periods, not actual
money or the new 100-stock strategy at 70%. No broader return is available yet.
Passing unit tests measures code behavior, not investment performance.

| Milestone | Concrete remaining work | Owner / coding agent |
|---|---|---|
| 1. Usable 100-stock research input - current stage | Correct the mixed histories, obtain required later aliases/successor quotes within a finite $0 scope, and handle supported merger/share/cash outcomes without inventing data. All selected names remain accounted for. | Coding agent; no owner download, purchase or installation. |
| 2. Connect inputs to the existing simulator | Build and verify the broader diagnostic input/runner, use the selected 70% research cap, retain matched old controls, and finalize the remaining assumptions and finite run allowance. The backtester already exists. | Coding agent prepares a runnable package; owner reviews remaining choices together. No repeat approval of 70%. |
| 3. Historical performance results | Run the approved finite experiment on development history and report whole-account gains/losses, CAGR, drawdown, costs, invested cash and outstanding rights. | Coding agent runs it; owner reviews the actual report. |
| 4. Candidate evaluation | Apply the existing 6% annual-return and 5% drawdown rejection criteria plus the other approved checks. If a candidate qualifies, freeze it and separately define/approve untouched final evaluation. Keep 2024-2025 prices reserved until then. | Coding agent evaluates; owner reviews results. A failed candidate does not automatically advance. |
| 5. Paper workflow and deliberate launch | Complete the unattended loop, protective exit/stop workflow and fill/activity ledger; verify restart/recovery. Review personal paper limits, existing paper positions/orders and startup report, then explicitly authorize the trial. Check the Pi before unattended deployment there. | Coding agent implements/checks execution; owner chooses personal paper limits and launch. |

The immediate deliverable is the corrected research input plus its integration
with the simulator. There is no defensible promise of a paper launch date:
neither the larger universe nor 70% capacity guarantees a qualifying strategy.
This route does not authorize purchases, paper orders or a new performance
batch before its inputs/remaining assumptions are ready.

## Earlier milestone records

The [latest offline verification/history review](broad_history_review_results.md)
passes 147 tests, with four identity conflicts and additional economic/delivery
gaps still blocking the broader backtest. The owner's higher-exposure request
is reflected in a [concrete research proposal](broad_expanded_backtest_proposal.md),
not an enabled allocation: 35%/70%/90% total entry capacity, 5% per-stock entries
and 7/20 slots. All performance and paper approval gates remain. No money,
paper order or account access was used in this increment.

The [bounded 100-stock collection](broad_100_collection_results.md) has now
executed. Its current results supersede the older pre-collection cache counts
below. Price coverage alone does not resolve historical identity, company-event
terms or investment acceptance. The owner's openness to additional concurrent
holdings is recorded separately; no paper settings or performance approval
changed. No setup or purchase is due from the owner for this collection.

The [100-name comparison plan](broad_100_comparison_plan.md) has completed
cached qualification but cannot score yet: 97 selected names lack full-window
raw streams, and lifecycle/action evidence remains incomplete. This is a
larger candidate search under unchanged 35% entry-exposure/5% position caps,
not a paper allocation or an approved full-account investment. No additional
owner setup is due; new scope/evidence assumptions require review before
performance runs. The data, return, execution and activation gates still apply.

The owner-approved [limited diagnostic is complete](limited_pilot_experiment_results.md):
209 tests and all 24 financial/risk ledgers pass. Every annualized return
misses 6%, with recent losses; the two-stock scope cannot meet the
five-instrument acceptance requirement. This closes the named research task,
not the investment/activation gates. No additional approval or personal risk
setting is due for that completed task; no paper candidate is established.

The [Apple/CBRE/SPY cached review](remaining_pilot_readiness.md) has completed
price/source checks, with strict evidence gaps retained. A
[limited return experiment](next_pilot_experiment_proposal.md) subsequently
received scope/vendor/timing approval, a separate diagnostic input path and
verification before its completed 24-run batch. It cannot clear the five-instrument
criterion or paper gate. This is a research decision, not a request to choose
personal risk limits or activate orders.

The [final capped JPMorgan attempt](jpm_dividend_followup_results.md) has ended
with one additional dividend declaration and unresolved gaps. JPMorgan's active
engineering collection is parked; qualification can continue for AAPL/CBRE
with SPY context. This does not clear the data or strategy gate, alter the
registered strategy control, or satisfy the five-instrument research minimum.
No purchase, account access, order or new backtest occurred. You have no setup
task now; the remaining gates below still apply.

We have a substantial research and safety codebase. **Several substantial
milestones remain before an approved paper trial.** The main uncertainty is
finding a strategy that satisfies the approved investment criteria. More
engineering or more stocks cannot guarantee that result, so there is no
defensible launch date yet.

The numbered implementation phases measure code structure. They do not mean
that completing Phase 14 leaves only one small action before paper trading.
Data reliability, research acceptance and operational readiness are separate
gates.

The [current free-data pilot proposal](free_data_pilot_proposal.md) makes the
next data step concrete: qualify AAPL/JPM/CBRE and SPY context from saved
2016-2023 files. It is an engineering sample, not a candidate-selection study.
Its timing assumptions need review before performance use. No personal risk
configuration is due for that cached-source review.

That [cached-source review is now complete](free_data_pilot_qualification.md):
all four price streams pass the documented checks, while full-period identity/
action completeness remains blocked. A bounded free/public document collection
list is next. Personal paper-risk settings remain separate; the proposed
research timing conventions are not accepted by this data review.

The subsequent [bounded public-source batch](pilot_public_source_results.md)
saved 11 files and resolves additional dividend evidence gaps. It stopped at
an HTTP access barrier with 16 original payable omissions still unresolved.
Source facts do not approve modeled timing or verify broker credit; paper
activation and personal risk settings remain separate.

The [collector/parser verification](public_source_test_results.md) now passes
99 focused/related tests and reproduces the saved-source comparisons exactly.
That verifies the documented engineering scope; it does not close the
remaining historical evidence or strategy-acceptance gates.

| Gate | Current position | Work still needed | Who does it? |
| --- | --- | --- | --- |
| Reliable historical data and simulation | The ownership adapter passed 183 focused tests, 36 exact financial replays, 36 exact risk comparisons and 84 component checks. Twenty primary sources were revalidated. Broader company-event evidence is incomplete. | Reviewed eligibility/delivery/payment facts or separately proposed research assumptions; required child/OTC prices or explicit blockers; complete the scoped dataset without purchases. | Coding agent. No owner configuration due now. |
| A strategy accepted for the investment goal | Earlier candidates did not pass. The broader entry/selection study remains unscored. | Evaluate the separately scoped finite study on credible development data, assess costs/risk and the approved criteria. Reserve final evaluation until a candidate and protocol are frozen. | Coding agent runs research; owner reviews results and any materially changed scope. |
| Verified paper execution workflow | Risk gate, idempotent order manager, recovery and kill-switch components exist. Submission is disabled. The unattended paper loop, complete fill/activity accounting and safe exit/stop workflow still need work. | Complete the Phase 15 workflow, exercise failures/restarts, reconcile fills/cash/positions, and verify that protection and shutdown behavior operate correctly. | Coding agent builds it; owner later reviews the operational result. |
| Deliberate activation | No approved paper candidate or launch decision. Paper-risk JSON remains unapproved. | Choose/approve personal paper-risk limits, review research results and cost sensitivity, understand existing paper positions/open orders, review a successful startup/recovery report, and explicitly authorize the trial. | Owner with guidance from the coding agent. |

Your previously approved **6% annual return hurdle and 5% running-peak
drawdown rejection criterion** are research acceptance criteria. They are not
completed personal risk settings and cannot guarantee the bot's future return
or maximum loss. The existing [research acceptance configuration](../config/research_acceptance.json)
and [owner checklist](owner_responsibilities.md) retain the detailed conditions.

## What you need to do now

Nothing to buy, download, configure or approve for the present integration
work. No payment card, paid data upgrade or risk JSON change is required.

I will tell you when a concrete research result or paper-risk decision is
ready for your review. Your risk configuration and activation approval must
be completed before paper orders are enabled. See the
[risk-limit workbook](risk_limit_decision_workbook.md) when that decision is due.

Windows and Raspberry Pi must each use their own environment and credentials.
The Pi's setup and execution checks remain separate. We can first establish
paper operation on Windows; moving unattended operation to the Pi also
requires that machine's deployment and recovery checks.

Tests, replays and the saved-source audit ran offline. Three bounded free
public-web tool calls sought an unavailable filing date; they established no
new event evidence. No broker/account requests, orders, purchases or subscription
changes occurred. Historical simulated cash, dividends and event payments are
accounting values; no money has been invested or moved in an account by this work.

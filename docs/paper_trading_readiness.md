# How far are we from paper trading?

Status: 2026-10-27.

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

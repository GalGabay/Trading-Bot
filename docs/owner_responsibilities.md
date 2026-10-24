# Your responsibilities in the trading-bot project

This is the project owner's checklist. It follows the numbered phases and
sections in the [development plan](../AI_Enhanced_Alpaca_Trading_Bot_Development_Plan_For_Coding_AI.md).
The bot remains **paper-only**. I can write code, tests, research commands,
documentation, and deployment instructions. You make the choices about what
the bot should study, the paper-account risk policy, and whether to enable
paper orders. You also control your accounts and Raspberry Pi.

For a proposed sequence of stock and timeframe studies and the conditions for
starting a paper trial, review the
[research program](proposed_research_program.md) before completing the
[research-scope workbook](research_scope_decision_workbook.md).

## Where we are now

**Latest engineering step:** The [2016 cohort source/coverage audit](cohort_2016_audit_results.md)
identifies dated tickers for all 506 retained holdings, records ten event cases
and checks 33 saved daily-price files. It uses free public/local sources with
$0 in purchases and zero new broker/account requests. The earlier $9.69
dividend figure was virtual simulation income, not a charge or real payment.
My next work is a bounded no-purchase acquisition plan and remaining event/
adapter evidence, starting with a representative small set. You need not gather
stocks, edit the risk JSON, add a card or install ML dependencies for that work.
Before scoring a materially revised research scope, I will present it for
review. Installing the optional ML requirements on Windows can clear the two
ML dependency errors; commands are in the linked update. Raspberry Pi setup
is still a later, separate task.

Phases 0–13, the Phase 14 offline ML research workflow, and the standalone
safeguards in Sections 23–24 have been built. The ML workflow has not been run
against a newly chosen untouched evaluation period.
Phase 12 has an order manager, but no command or scheduler calls it. Paper
submission is disabled by default and has not been activated. You do **not**
need to choose risk percentages to continue coding or review.

The [strategy guide](five_daily_strategies_explained.md) explains the five
tested daily rules. The [latest allocation study](study_c_allocation_results.md)
compares experimental position sizes and halt behavior. Those research
numbers are not approvals or new defaults for your paper-risk JSON.

The subsequent [earlier-history check](study_c_earlier_history_results.md)
passed its ten predeclared checks for the same smaller candidate. The
pessimistic seven-year return was modest (about 2.19% annually); losing years,
backward selection, survivor-basket bias, and the earlier strategy failures
remain relevant. Before a final 2024-2025 evaluation, review the proposed
frozen criteria, acceptable losses, and whether this research scope fits
your goals. You do not need to write code or personally fetch data. This
review does not itself enable paper orders or approve risk settings.

**Owner update, 2026-10-24:** You want attractive investment returns before
paper trading, said approximately 2% annually is insufficient, and identified
a $500 temporary decline on $10,000 as concerning. The
[investment acceptance plan](investment_acceptance_proposal.md) records
these preferences. You subsequently approved its 6% annual return hurdle,
5% running-peak drawdown rejection level, other research criteria, and the
development-only goal-fit audit. The versioned criteria are in
`config/research_acceptance.json`; they are not paper-order risk approval.
No further owner action is needed for the authorized audit. 2024-2025 stay
reserved and `config/risk_limits.json` remains empty/unapproved.

The [completed audit](study_c_goal_fit_results.md) rejects the frozen
candidate for the approved investment goal. No further configuration is
needed now. The next owner decision is whether to pursue a separately
defined finite alternative study after reviewing its concrete proposal.

You approved the holding-time study with continuation beyond session 60 and
subsequent reviews every 30 sessions. Its
[36 completed simulations](holding_period_study_results.md) found that neither
variant meets the investment criteria; the new policies are research only.
You subsequently authorized broader-market data feasibility and a scoped
entry/selection study. The [completed audit](broad_universe_audit_results.md)
checked 33,560 asset records and 56 coverage probes. Price access works;
historical membership, identity and terminal outcomes remain unresolved.
The [eight-arm study](broad_entry_selection_study.md) is defined but has not
been simulated, because its historical-data gate is not met. Codex owns
the source/adapter and dynamic-universe engineering work. No Python, JSON,
account or additional risk-limit changes are required from you now.
**Your cost preference is now recorded as $0 in new data purchases.** No
upgrade, paid trial or subscription is needed for the next engineering work.
The [free-data/lifecycle update](free_data_and_lifecycle_progress.md) records
four successful company-event queries under existing access and ten review
candidates. The [subsequent action/accounting work](corporate_action_progress.md)
adds split and ordinary-dividend support, 69 passing focused tests and 36
exact historical replays. Supported action-aware risk diagnostics now exist,
along with a reviewed Apple pilot and historical fund holdings lists. Complete
cohort identity/action/price coverage remains due before a broad return study. No Python,
JSON, billing or manual stock-collection action is required from you now.
Paper activation remains a separate decision.

Before Phase 12 is connected to paper-order submission, choose or explicitly
accept the risk limits in `config/risk_limits.json`. It now exists with all
limits set to `null` and `approved_for_paper: false`; the loader rejects it
until you complete and approve it. The historical-results review, account
review, recovery report, and decision to start are separate owner steps below.

## Phase-by-phase checklist

| When in the plan | Your decision or action | How to do it | Status / what I can do |
| --- | --- | --- | --- |
| **After Phase 0 — Define the Trading Scope (§6), before using research results to choose a strategy** | Decide the initial asset class, timeframe, and small set of symbols to study. Keep the first scope understandable. | Tell me your preferred symbols and whether you want 15-minute or hourly bars. If unsure, ask me to propose a research scope and explain its tradeoffs. | The code and examples use US equities and 15-minute AAPL research. A broader historical universe has **not** been validated; this choice can be revisited before paper activation. |
| **After Phase 1 — Alpaca Paper Account (§7), before any broker API call on a machine** | Maintain a paper account and its own API keys. | Put paper keys in that machine's `.env`, with `ALPACA_PAPER=true`. Keep Windows and Pi `.env` files separate. Never commit keys or paste them into a chat, screenshot, log, or Markdown file. | You have configured Windows keys. I can explain setup; I do not need to see the values. |
| **After Phase 2 — Set Up Python (§8), whenever setting up a new machine** | Create that machine's Python environment and install dependencies. | Follow [README setup](../README.md). Use a new `.venv` on Windows and on the Pi; do not copy the Windows environment. | Windows setup is done. Pi setup is due at Phase 16. |
| **After Phase 8 — Backtesting (§16–20) and Phase 9 — Walk-Forward (§21), before treating results as evidence for paper trading** | Choose the symbols, years, untouched evaluation period, and how much cost sensitivity you will tolerate. Review losses and drawdowns as well as returns. | Use the [research-scope decision workbook](research_scope_decision_workbook.md) or tell me your choices in plain language; I can download permitted historical data and run the documented commands. Keep an untouched period for final evaluation. | Existing AAPL case studies are illustrative and cost-sensitive, not proof of an edge. You do not need to personally write the downloader or train a model. |
| **After Phase 12 coding, before enabling any paper order** | **Choose or explicitly accept every required paper-risk limit** and decide whether to use the optional sector and volatility limits. Decide the paper-account size the policy is meant to represent. | Use the [risk-limit decision worksheet](risk_limit_decision_workbook.md). Edit the existing `config/risk_limits.json` or tell me your choices. Optional limits may remain `null`. Set `approved_for_paper` to `true` only after review. Commit the reviewed JSON so the Pi receives the same policy. | Phase 12 is built but disabled. The empty JSON blocks submission until you decide. |
| **Before the first Phase 12 paper-order submission (§26–27)** | Confirm that the account's existing positions and open orders are understood, the approved risk config is loaded, and you want paper orders enabled. | Run or ask me to guide the Phase 13 startup report: `python -m app.recovery.state_recovery --database data/trading_bot.sqlite3`. Review it and investigate unexpected holdings, orders, or accounting gaps. The kill switch must be healthy and explicitly reset after review. | Phase 12 has an offline preview, order journal, and focused tests. Phase 13 recovery has 17 offline tests; an exit/stop workflow and broker fill ledger are still needed before an automatic paper workflow. |
| **After Phase 13 — State Recovery (§28), before unattended operation** | Review how the bot behaves after a restart or network outage, especially if an order's result is unknown. | Run `python -m unittest tests.test_recovery -v` and review the startup report. Resolve any unexplained paper orders in the Alpaca dashboard before resuming. | The recovery command reports and latches suspicious state; it does not reset the kill switch or enable submission. The focused tests pass on Windows; Pi checks remain due. |
| **After Phase 14 — Machine Learning (§29–36), if you decide to pursue ML** | Define what you want the model to predict and which later data must remain unseen; approve any paid data source before purchase. | Use the [research-scope decision workbook](research_scope_decision_workbook.md) to choose or request proposed defaults. I can use the offline `backtesting.ml_research` command on Windows after you choose a genuinely uninspected final period. | ML is optional for the first paper bot. The research command and 11 offline unit tests exist but have not trained a reviewed model or enabled ML in paper orders. |
| **After Phase 15 — Paper Trading Engine (§40–42), during the paper trial** | Decide when to start the paper trial and review operation over varied market conditions. Investigate unexplained orders, repeated kill-switch trips, gaps, and drawdowns. | Review broker activity, the bot's logs/reconciliation, and periodic performance reports. Record any decision to change risk limits or strategy settings; retest before restarting. | I can build monitoring, reports, and incident instructions. Paper fills do not prove how live fills will behave. |
| **After Phase 16 — Raspberry Pi Deployment (§43–50, §71), before leaving the Pi unattended** | Supply and control the Pi, network access, paper credentials, and the decision to start its service. | Pull the reviewed Git revision; create a Pi `.venv` and separate `.env`; run the tests on the Pi; run a manual read-only/dry-run check; then enable the service only after those checks pass. Set up OS updates, restricted access, and backups. | I can write the scripts and exact commands. Pi tests and service operation have not happened yet. The Pi cannot be treated as validated until those checks run there. |
| **After sustained paper validation (§41–42, §72)** | Decide whether to continue, change the strategy, or stop. | Compare out-of-sample, stress-test, and paper results with the limits you chose. Keep a record of changes. | Live trading is outside the current paper-only implementation and would require a separate design and explicit decision. |

## Optional Sections 37–39

Section 37 proposes later market-regime awareness. It is not a gate for the
first paper bot. Before changing strategy or exposure by regime, choose a
benchmark and what actions the bot should take in each regime; I would need
aligned historical benchmark data and a backtest of those changes. Section 38
explicitly postpones news and sentiment beyond V1. If you pursue it later,
you would choose or approve the data source and any cost. Section 39 is design
guidance: an LLM does not get independent order-submission authority. It
requires no action from you now.

## The decisions needed soon

1. **Before interpreting ML results:** choose the symbols, timeframe,
   target/horizon, untouched test period, and data budget using the
   [research-scope decision workbook](research_scope_decision_workbook.md).
   I can propose a scope for your review. ML is optional for the first paper bot.
2. **Before Phase 12 can submit a paper order:** enter your chosen risk limits
   or explicitly accept the example values after reading the
   [worksheet](risk_limit_decision_workbook.md). Review the existing
   `config/risk_limits.json` and then set `approved_for_paper` to `true`.
3. **Before the first paper order:** review the tested historical strategy
   results, including losses, drawdown, and sensitivity to transaction costs;
   confirm and resolve the paper account's existing positions and open orders;
   review a successful Phase 13 startup recovery report; decide to start the
   paper trial and authorize enabling paper submission; and explicitly reset
   the kill switch after review. I must first implement and check a safe
   exit/stop workflow and broker fill/activity ledger. A proposed `stop_price`
   currently sizes risk; it is not a protective broker stop order.
4. **Before Phase 16 Pi deployment:** prepare the Pi and its own paper keys,
   then run checks on that machine. The same Git repository supplies code and
   reviewed risk settings; secrets and local databases stay on each machine.

You can tell me your decisions in plain language. I can translate them into
the appropriate repository files and commands for your review. The decision
about acceptable risk and whether to start paper execution remains yours.

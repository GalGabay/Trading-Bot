# Your responsibilities in the trading-bot project

This is the project owner's checklist. It follows the numbered phases and
sections in the [development plan](../AI_Enhanced_Alpaca_Trading_Bot_Development_Plan_For_Coding_AI.md).
The bot remains **paper-only**. I can write code, tests, research commands,
documentation, and deployment instructions. You make the choices about what
the bot should study, the paper-account risk policy, and whether to enable
paper orders. You also control your accounts and Raspberry Pi.

## Where we are now

Phases 0–13 and the standalone safeguards in Sections 23–24 have been built.
Phase 12 has an order manager, but no command or scheduler calls it. Paper
submission is disabled by default and has not been activated. You do **not**
need to choose risk percentages to continue coding or review.

The next owner decision becomes necessary **before Phase 12 is connected to
paper-order submission**: choose or explicitly accept the risk limits in
`config/risk_limits.json`. It now exists with all limits set to `null` and
`approved_for_paper: false`; the loader rejects it until you complete and
approve it.

## Phase-by-phase checklist

| When in the plan | Your decision or action | How to do it | Status / what I can do |
| --- | --- | --- | --- |
| **After Phase 0 — Define the Trading Scope (§6), before using research results to choose a strategy** | Decide the initial asset class, timeframe, and small set of symbols to study. Keep the first scope understandable. | Tell me your preferred symbols and whether you want 15-minute or hourly bars. If unsure, ask me to propose a research scope and explain its tradeoffs. | The code and examples use US equities and 15-minute AAPL research. A broader historical universe has **not** been validated; this choice can be revisited before paper activation. |
| **After Phase 1 — Alpaca Paper Account (§7), before any broker API call on a machine** | Maintain a paper account and its own API keys. | Put paper keys in that machine's `.env`, with `ALPACA_PAPER=true`. Keep Windows and Pi `.env` files separate. Never commit keys or paste them into a chat, screenshot, log, or Markdown file. | You have configured Windows keys. I can explain setup; I do not need to see the values. |
| **After Phase 2 — Set Up Python (§8), whenever setting up a new machine** | Create that machine's Python environment and install dependencies. | Follow [README setup](../README.md). Use a new `.venv` on Windows and on the Pi; do not copy the Windows environment. | Windows setup is done. Pi setup is due at Phase 16. |
| **After Phase 8 — Backtesting (§16–20) and Phase 9 — Walk-Forward (§21), before treating results as evidence for paper trading** | Choose the symbols, years, untouched evaluation period, and how much cost sensitivity you will tolerate. Review losses and drawdowns as well as returns. | Tell me the research scope; I can download permitted historical data and run the documented commands. Keep an untouched period for final evaluation. | Existing AAPL case studies are illustrative and cost-sensitive, not proof of an edge. You do not need to personally write the downloader or train a model. |
| **After Phase 12 coding, before enabling any paper order** | **Choose or explicitly accept every required paper-risk limit** and decide whether to use the optional sector and volatility limits. Decide the paper-account size the policy is meant to represent. | Use the [risk-limit decision worksheet](risk_limit_decision_workbook.md). Edit the existing `config/risk_limits.json` or tell me your choices. Optional limits may remain `null`. Set `approved_for_paper` to `true` only after review. Commit the reviewed JSON so the Pi receives the same policy. | Phase 12 is built but disabled. The empty JSON blocks submission until you decide. |
| **Before the first Phase 12 paper-order submission (§26–27)** | Confirm that the account's existing positions and open orders are understood, the approved risk config is loaded, and you want paper orders enabled. | Run or ask me to guide the Phase 13 startup report: `python -m app.recovery.state_recovery --database data/trading_bot.sqlite3`. Review it and investigate unexpected holdings, orders, or accounting gaps. The kill switch must be healthy and explicitly reset after review. | Phase 12 has an offline preview, order journal, and focused tests. Phase 13 recovery exists, but its focused tests and an exit/stop workflow are still needed before connecting an automatic paper workflow. |
| **After Phase 13 — State Recovery (§28), before unattended operation** | Review how the bot behaves after a restart or network outage, especially if an order's result is unknown. | Ask me to run the recovery tests and show you the state and order-reconciliation report. Resolve any unexplained paper orders in the Alpaca dashboard before resuming. | The recovery command reports and latches suspicious state; it does not reset the kill switch or enable submission. Focused recovery tests are still due. |
| **After Phase 14 — Machine Learning (§29–36), if you decide to pursue ML** | Define what you want the model to predict and which later data must remain unseen; approve any paid data source before purchase. | Tell me the intended question, data budget, and acceptable complexity. I can construct the dataset, train on Windows, and compare against the fixed rule-based baseline. | ML is optional and is not required for the first paper bot. No training command exists yet. |
| **After Phase 15 — Paper Trading Engine (§40–42), during the paper trial** | Decide when to start the paper trial and review operation over varied market conditions. Investigate unexplained orders, repeated kill-switch trips, gaps, and drawdowns. | Review broker activity, the bot's logs/reconciliation, and periodic performance reports. Record any decision to change risk limits or strategy settings; retest before restarting. | I can build monitoring, reports, and incident instructions. Paper fills do not prove how live fills will behave. |
| **After Phase 16 — Raspberry Pi Deployment (§43–50, §71), before leaving the Pi unattended** | Supply and control the Pi, network access, paper credentials, and the decision to start its service. | Pull the reviewed Git revision; create a Pi `.venv` and separate `.env`; run the tests on the Pi; run a manual read-only/dry-run check; then enable the service only after those checks pass. Set up OS updates, restricted access, and backups. | I can write the scripts and exact commands. Pi tests and service operation have not happened yet. The Pi cannot be treated as validated until those checks run there. |
| **After sustained paper validation (§41–42, §72)** | Decide whether to continue, change the strategy, or stop. | Compare out-of-sample, stress-test, and paper results with the limits you chose. Keep a record of changes. | Live trading is outside the current paper-only implementation and would require a separate design and explicit decision. |

## The decisions needed soon

1. **For the next coding:** nothing is required from you yet. Phase 12 tests
   pass; I can add focused Phase 13 recovery tests with submission disabled.
2. **Before Phase 12 can submit a paper order:** enter your chosen risk limits
   or explicitly accept the example values after reading the
   [worksheet](risk_limit_decision_workbook.md). Review the existing
   `config/risk_limits.json` and then set `approved_for_paper` to `true`.
3. **Before the first paper order:** review the broker account's existing
   positions/open orders, approve enabling paper execution, and explicitly
   reset the kill switch after the order manager provides a safe workflow.
4. **Before Phase 16 Pi deployment:** prepare the Pi and its own paper keys,
   then run checks on that machine. The same Git repository supplies code and
   reviewed risk settings; secrets and local databases stay on each machine.

You can tell me your decisions in plain language. I can translate them into
the appropriate repository files and commands for your review. The decision
about acceptable risk and whether to start paper execution remains yours.

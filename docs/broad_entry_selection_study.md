# Broader universe, stricter entries and signal ranking: finite study

Defined 2026-10-24 after registering the coverage audit, before calculating
any new strategy returns. This document scopes the subsequent study; it
does not claim the required historical-universe data or simulator exists.

## Hypothesis in plain language

Searching more stocks might supply opportunities the twelve-instrument pilot
misses. Stronger entry evidence might reject weak breakouts. Ranking might
allocate the seven available slots better than alphabetical priority.
Each change can also hurt: filters can reject later winners, ranking can
concentrate correlated stocks, and more signals can increase turnover.
We will measure these effects separately, rather than assume stronger
historical momentum means a calibrated chance of future profit.

## Required data gate

**Historical research cannot begin until these inputs are audited:**

- Dated membership and common-stock classification on NYSE, NASDAQ and
  NYSE American; US-listed ordinary common shares, including REIT common
  shares. Exclude ETFs/funds, preferreds, warrants, rights, units, depositary
  receipts and OTC-only listings. This is a defined US scope, not global.
- Stable instrument identities, dated symbol/exchange changes, listing and
  suspension intervals, delisting events, and supported terminal proceeds.
  A ticker is not a permanent identity; last observed price is not a cash exit.
- Calendar-checked raw daily OHLCV and corporate actions for 2016-2023.
  Features need split-consistent historical windows without using future
  adjustment factors as nominal price eligibility or assumed fill prices.
  Cash distributions must be credited explicitly; avoid counting them twice.
- Explicit handling of no-bar sessions: no fabricated candles, valuation,
  stop execution or tradability. Separate true lifetime boundaries from feed
  defects with independent event evidence. Unresolved defects block scoring.
- A dynamic-universe shared-cash engine with those lifecycle semantics and
  accounting checks. First replay the original twelve-instrument controls
  against their saved metrics/fills; don't revise old provenance hashes.

The audited current asset catalog is useful for prospective snapshots, but
does not satisfy this historical gate. Do not select only names with complete
2016-2023 files: that explicitly removes IPOs and many failed/delisted names.

## Eight arms, with three independent factors

| Factor | Control | Challenger |
| --- | --- | --- |
| Search universe | Nine original stocks: AAPL, MSFT, JPM, JNJ, XOM, WMT, CAT, PG, NEE | Every historically eligible common share in the defined exchanges |
| Entry rule | Frozen 55-session breakout and stock/SPY EMA200 filters | Same rule plus the two evidence gates below |
| Competing-entry order | Alphabetical symbol, permanent ID breaks ties | Highest completed 63-session return minus SPY's matched 63-session return; permanent ID breaks ties |

Run every combination: **2 × 2 × 2 = eight arms**. In this new study SPY is
market context and a separately reported passive reference, not an eligible
trade; QQQ and IWM are excluded from trading in both universes. The small
stock-only control is therefore distinct from the older twelve-instrument
baseline, whose separate replay checks software continuity.

Both universes use identical causal eligibility screens at each completed
session: historically eligible/tradable common stock, raw close at least
$5, median prior-20-session raw close × volume at least $10 million, and
200 completed valid session observations in the current continuous eligible
history. An IPO can become eligible after its own warmup; no requirement to
have existed in 2016. Suspensions and genuine missing data require explicit
rules before implementation, rather than a filled price series.

The **strict-entry challenger** adds both:

1. The completed signal session's volume is at least **1.5 times** the
   preceding 20 sessions' median volume, measured on a split-consistent basis
   known at that close. Exclude the signal session from the comparison median.
2. Its completed **63-session return exceeds SPY's by at least 5 percentage
   points**, using the same completed session endpoints and a documented
   causal corporate-action convention.

These are predeclared research thresholds, not optimized values or a claim
to identify the "best" stock. Missing required inputs disqualify that signal
and are counted. A new proposal is required to change thresholds after
viewing results; all previous attempts remain part of the research record.

## Unchanged capital, exits and timing

Keep the frozen `vol_latched` research allocation: at most 5% per position,
35% total exposure, seven positions, 0.5% planned stop risk, inverse-volatility
sizing, ten-session reentry cooldown, and the existing latched research loss
halts. These are comparison settings, not the owner's paper-risk approval.
Use the owner's approved continuation policy: reviews at held sessions
30, 35, 40, 45, 50, 55, 60, then every 30 thereafter, subject to the frozen
profit/new-high/EMA evidence gates. Natural exits and fixed initial 3-ATR
stops remain active. No independent take-profit or new trailing-stop search.

Calculate entries, filters, ranking, position size and review decisions from
completed data. Freeze the candidate order at that close. Fill discretionary
orders no earlier than the next actual available tradable session, under an
explicitly bounded stale-signal policy finalized before scoring; no use of
next-session returns to rank signals. Exits precede buys; respect cash and
whole shares. Retain daily-OHLC stop/intraday uncertainty disclosures.

## Finite evaluation and stop rules

- **12 original control replays**, both saved capital sizes, original two
  windows and three costs, must reproduce saved financial results first.
- Primary new account: **$10,000**. Warmup begins in 2016. Score 2017-2021
  development first: eight arms × three existing cost assumptions = **24**
  simulations. Freeze a candidate before revealing later-window scores.
- Candidate selection: only an arm meeting all measured approved acceptance
  criteria under pessimistic costs may qualify. Among qualifiers prefer
  higher net CAGR; ties within 0.1 percentage point prefer fewer added entry
  gates, then alphabetical selection, then the smaller universe. Predeclare
  exact rounding/tie handling in the runnable configuration before scoring.
- If none qualifies, stop at **36** runs. Do not lower the 6% return hurdle
  or increase allowed loss to select a winner.
- If one qualifies, evaluate all eight frozen arms in independent 2022-2023
  accounts with 2019-2021 warmup, all three cost cases: **24** more runs.
  These years have already informed earlier research. Call this development
  robustness, not a fresh holdout. Do not replace a failed selected candidate
  with whichever later-window arm looks best.
- Only if the preselected candidate passes both primary windows, run its
  **16** predeclared pessimistic diagnostics per window: nine removals of one
  original stock; three removals of one stable-ID hash tercile of the broad
  universe (tercile assignment fixed before returns); reversed ranking;
  one additional execution-session delay with 50 bps extra stop slippage;
  channel neighbors 40/15 and 70/25. No diagnostic becomes the new winner.
- **Maximum 92 simulations**: 12 + 24 + 24 + 32. No ML training, random search
  or expansion after seeing scores. No opening 2024-2025 in this study.

## Reporting and readiness

Report every arm, cost case, exclusion and data error. Include total and
annualized whole-account returns after costs and estimated final exits;
running-peak drawdown and daily losses; closed/open P&L; trade count and
profit factor; per-year and per-instrument concentration; shared-capital
utilization, idle cash, turnover, realized costs and liquidity; signal counts
before/after each filter; simultaneous qualifiers, ranking effects and
rejected candidates. A blocked signal's later gain is not free realized P&L.

Show passive SPY and zero-yield cash references with explicit exposure and
risk differences. The approved 6% annual / 5% drawdown / other acceptance
criteria remain in `config/research_acceptance.json`. Daily bars cannot
establish observed intraday loss compliance. Historical results alone cannot
authorize paper activation.

## Execution status and responsibilities

**Engineering update:** Initial [historical-universe support](historical_universe_format.md)
now exists for dated listings/aliases and verified terminal cash. Existing
Alpaca access also returned company-event records. The
[free-data/source assessment](free_data_and_lifecycle_progress.md) records
the $0 new-purchase policy. Unit validation, unchanged-control replays, split/
dividend adapters and historical data completeness remain outstanding; the
study's scoring gate is still closed.

**Scoped, not yet simulated.** The feasibility audit determines which data
gates remain. Codex owns source/adapter evaluation, lifecycle-aware engine
work, executable protocol details, downloads and simulations once inputs
meet the gate. The owner need not select thousands of stocks, edit risk JSON
or write code now. Continue with existing/public sources; do not assume a
subscription purchase is the next step.

If historical membership cannot be acquired without a purchase, the available
no-purchase path is a **prospective read-only shadow study**: start recording
dated catalogs and causal signals now, establish current-feed access, and
accumulate future evidence. It is not a reconstruction of past market-wide
performance and does not submit paper orders. Snapshot acquisition software
can be built while a historical source is evaluated.

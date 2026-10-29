# Expanded backtest and higher-exposure proposal

**2026-10-29: prepared for owner review; no performance runs authorized.**

This makes the requested next experiment concrete. It does not alter paper
settings or the original [two-versus-100 proposal](broad_100_comparison_plan.md).
The [machine-readable proposal](broad_expanded_backtest_proposal.json) pins the
roster, original rules, costs, acceptance criteria and reviewed history report.

## 1. What 35% meant

It meant **35% of total account equity across all stock holdings**, not 35%
per stock. With $10,000 equity, the old research entry limit allowed about
$3,500 in stocks collectively, with roughly $6,500 elsewhere in the account.
The separate **5% per-stock entry cap** allowed about $500 in one stock.
Actual sizes could be smaller because of volatility, stops and whole shares.

These are entry limits in the simulator. They do not continuously rebalance
holdings: subsequent price moves can push measured exposure above an entry
cap. We must report that drift rather than claim a continuous guaranteed cap.

You have now said you want more capacity than 35% and are open to more than
seven holdings. That preference is recorded. It does not mean you selected
35% per stock, a new numerical account cap or a paper setting.

## 2. Proposed comparisons

Keep the per-stock maximum at **5%**. Propose **70% total capacity** as the
main higher-exposure arm and **90%** as a separately declared sensitivity.
Twenty entry positions allow these caps to be reachable in principle without
putting a large fraction in one company. Twenty is a proposed limit, not an
instruction to own twenty stocks or a newly approved personal risk limit.

| Arm | Historical candidates | Total entry cap | Per-stock entry cap | Position slots | Purpose |
|---|---:|---:|---:|---:|---|
| A | Original 2 | 35% | 5% | 7 | Reproduce the completed control exactly |
| B | Fixed 100 | 35% | 5% | 7 | Measure universe-size effect |
| C | Fixed 100 | 35% | 5% | 20 | Measure extra-slot effect |
| D | Fixed 100 | 70% | 5% | 20 | Main higher-exposure comparison |
| E | Fixed 100 | 90% | 5% | 20 | Upper-exposure sensitivity |

At $10,000, these total limits correspond to approximately $3,500, $7,000 and
$9,000 invested. **They are maximums, not targets or minimums.** The bot can
still hold cash when entries do not qualify, sizes are small, cash is tied up
in unpaid claims, or another limit blocks buying. No forced buying, leverage,
weaker entry rule, larger stop-risk allowance or confidence-based sizing is
introduced. Twenty volatility-sized positions might still use far less than
90%; that would be a result to explain, not permission to enlarge them silently.

Higher exposure increases sensitivity to market losses. For example, if all
stocks held fell 10% while 90% of the account was invested, the simple direct
effect would be roughly a 9% account loss before other effects. This can exceed
your $500-on-$10,000 concern. Stops cannot promise a 5% maximum account loss.
The SEC's [Investor.gov allocation guide](https://www.investor.gov/introduction-investing/getting-started/asset-allocation)
explains the relationship between allocation, diversification and risk.

The approved **6% annual return goal and 5% drawdown rejection criterion**
remain unchanged. Raising exposure cannot turn a result that breaches those
criteria into an acceptable candidate. The old simulated 3% daily/10% drawdown
latched halts remain controls for matching the earlier strategy; they are not
your acceptance limits, nor protection guaranteeing a 5% maximum decline.

## 3. Fixed rules, periods and finite budget

Retain the original 55/20 breakout, stock/SPY EMA200, fixed 3-ATR stop,
volatility-based sizing, 30-session continuation reviews, cooldown, stable-ID
alphabetical priority, next-session execution and all other frozen settings.
No new parameter/ranking search or ML is included.

Every arm gets the same 24 cases:

- 2017-2021 with 2016 warmup, and independent 2022-2023 with 2019-2021 warmup.
- $10,000 primary and $100,000 whole-share sensitivity accounts.
- Existing base and pessimistic transaction costs.
- Three declared cash-availability scenarios, with unknown dates treated as
  unknown rather than invented. See the assumptions below.

That is **5 x 2 x 2 x 2 x 3 = 120 strategy attempts**, including the 24 exact
control replays. It needs a new approved run allowance and runner; it does not
reopen the consumed 24-run budget or automatically approve the earlier 48-run
proposal. Match the old control first. Report every attempted case and stop
on data/ledger errors, control mismatch or exhausted limits.

Proposed compute ceiling: one worker, 15 minutes per case, six hours total,
Windows first, subject to profiling before approval/execution. A timeout
means incomplete results, not a reset or an extra run. Profile separately
before running on the Pi. **2024-2025 candles remain reserved.**

## 4. Concrete data assumptions to review

| Topic | Proposed treatment | Current status |
|---|---|---|
| Historical universe | Retain all fixed 100 identities, including difficult mergers; keep the 506-row source register. No replacements or dropping failed names. | Frozen roster available; complete execution inputs blocked. |
| Raw execution prices | SIP/raw daily observations only, with checked issuer/class/alias intervals. Pure renames retain identity; unrelated ticker reuse does not. | Four unsegmented identity conflicts identified; later alias prices still needed. |
| Ordinary dividend fields | Any diagnostic use of vendor ex-dates/rates must be named and approved, kept separate from independent verification. No announcement-prediction strategy. | Not approved for the expanded scope. |
| Missing payable dates | Never invent a date. Earned rights remain unspendable during the window. If a supported payable date exists, compare first actual open after it, five more sessions, and no credit. | 1,334 provider dividend records lack payable dates; earlier primary sources may resolve some. |
| Missing announcement dates | Provider records do not certify historical availability. Any effective-date knowledge convention must be stated explicitly in the diagnostic path; strict known-at checks stay strict. | All 2,421 provider dividend records lack declarations; no expanded timing approval. |
| Merger/spin-off economics | Require correct parent/child/acquirer, ratios, cash rights, delivery assumptions, fractions and valuation streams. Do not replace an event with a last-price sale or unknown zero recovery. | Reviewed anchors exist, but full delivery/valuation evidence is incomplete. |
| Non-roster shares received | No new discretionary entries in an unselected child/acquirer. Proposed disposal is the first supported regular open after delivery, with costs. Keep valuation until sale; unknown delivery blocks execution. | Needs per-case terms, prices, implementation and review. |
| Ticker conflicts | DLPH/XL/LLL/MON streams stay unapproved until independently segmented. Preserve originals and document every segment; do not trim around an event to manufacture returns. | Conflicts reviewed; no segmentation or successor acquisition performed. |

These are proposed diagnostic treatments, **not approved facts or a way to
bypass unresolved identity and economic outcomes**. A marked dividend/merger
claim is not cash available for buying. Report ending spendable cash, share
liquidation value, unpaid rights and assumptions separately. Uncertain
recoveries cannot be quietly valued at face value or zero to pass a screen.

## 5. What must happen before running

1. Resolve each selected issuer/class and required ownership branch, including
   CBS's unresolved transition and the four identified mixed histories.
2. Archive/check primary sources beyond search excerpts, preserving the Ball
   403 and earlier barriers. Review missing events even on complete calendars.
3. Obtain necessary successor/alias raw data under a separate finite $0
   protocol. This proposal does not start those requests.
4. Implement and verify the broader diagnostic input path, event delivery and
   finite runner. Strict admission must not be weakened by diagnostic flags.
5. Present the finalized inputs, assumptions and allocation amendment for
   your approval; record that approval against hashes, then run within bounds.

Measure account returns and drawdown, realized versus unpaid gains, invested
exposure/cash distributions, slot/exposure/sizing/cash blockers, turnover,
concentration, holding time and daily-OHLC risk bounds. The first rejected
check does not prove there were no other blockers; instrument diagnostics
accordingly. Sector/correlation caps are not currently added or claimed.
Report all five arms, not only the highest historical return. More testing
on already explored development years does not provide untouched validation.

## Your part and my next work

**Your part now:** review this proposal, especially 70%/90% total capacity,
20 position slots and 5% per-stock entries. You can respond in chat; you do
not need to edit JSON or Python. Your preference for more exposure is already
recorded, so no repeated account setup or personal paper-risk form is needed.

**My next work:** build the corrected historical segments and exact bounded
successor-data/evidence package, then implement the broader diagnostic path
and runner. A new performance batch waits for ready inputs and review of the
concrete final assumptions. Paper activation remains a separate later step.

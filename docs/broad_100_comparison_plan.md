# Next universe comparison: two stocks versus 100 fixed historical candidates

Prepared **2026-10-29** after the owner's request for a larger stock search
with the same rules. **This is a qualified-cache inventory and proposed
comparison, not a completed 100-stock dataset or an authorized new backtest.**
The [machine-readable plan](broad_100_comparison_plan.json) fixes membership,
settings, gates and limits. No download, purchase or strategy run occurred.

## What changes, and how much money could be used?

Change the **number of eligible stock candidates: two versus 100**. Keep the
breakout, market filter, exit/holding rules, sizing, fees, delays and capital
amounts from the completed [small diagnostic](limited_pilot_experiment_results.md).
SPY remains price-only market context and is not one of the 100 stocks.

Under the unchanged entry policy, a $10,000 account can allocate at most
5%—initially $500—to each position, with seven positions and a 35% account
exposure cap. Seven sufficiently sized opportunities could therefore use
about **$3,500**, leaving $6,500 unallocated at that point. Volatility sizing,
whole shares, market filters and opportunity availability can reduce that
amount. Market price changes can move observed weights after entry.

Searching 100 names gives the strategy more opportunities to fill those
seven slots. It does not require buying seven stocks, make weak signals
qualify, or guarantee a higher return or exposure. Using 70–100% of the
account would require a **separate allocation/risk experiment**; it is not
part of this comparison. Personal paper-risk settings remain unapproved.

## 1. The actual 100-stock candidate basket

The [frozen roster](research_data/broad_100_candidate_roster.csv) names every
historical identity and its September 2016 ticker. It is derived from the
preserved 506-row September 30, 2016 fund holdings register, not today's list
of surviving stocks:

1. Retain Apple and CBRE, the two existing control identities, so the smaller
   universe is nested within the larger one. CBRE's historical ticker is CBG.
2. Exclude **DVMT's tracking-share class** from candidate eligibility, using
   the already reviewed 2016 classification evidence. Keep its row in the
   original 506-row register and inventory.
3. Of the remaining 503 pool rows, select the 98 lowest SHA-256 values of
   `broad-fixed-2016-v1|<instrument_id>`; stable ID breaks ties. The eligible
   population before removing the two forced controls has 505 rows.
4. Do not reroll the seed, replace an unavailable name, select by return,
   choose only complete files or remove an acquired company after selection.

The seed/algorithm were fixed before this new cache qualification. No new
returns were calculated. The roster intentionally still contains old aliases
such as FB, RTN, DOW, CBS, MON and FISV. These are **snapshot aliases**, not
instructions to attach any current company using those letters. Every dated
identity/alias/lifecycle must be reviewed before trading history is admitted.

JPMorgan was in the eligible parent population but **was not selected by the
fixed hash**. No JPM-specific exclusion or alternate seed was used. Its
collection remains parked and its original register/control rows are intact.

This is a finite historical-fund sample with two forced engineering controls.
It is not an unbiased sample of all US stocks, every later IPO, daily index
membership or global equities. The source filing date is November 28, 2016;
the existing availability bound is November 30, 2016. The first scored year
is 2017. Earlier prices are uninvested warmup, not permission to trade using
unpublished membership.

## 2. What the cache actually supports

The new offline command reuses the existing cohort and company-event
reviewers, validates source hashes and raw-response reconstructions, and
retains all **506 parent rows** as well as the selected 100.

| Finding among the selected 100 | Count | Meaning |
| --- | ---: | --- |
| Full 2016–2023 raw calendar observed | **3** | AAPL; CBRE/CBG; original Under Armour Class A (UA then UAA) |
| Partial raw streams only | **2** | CTL and CVS, each with 251 saved reference observations |
| No bound raw stream in the audited cache | **95** | Source price/lifecycle work is still needed |
| Without a full-window raw stream | **97** | This is an inventory count, not a claim of 97 ordinary missing-candle errors |
| Candidate adjusted observations | **5** | Apple plus FB, JNJ, NEE and WMT; these cannot substitute for raw input |
| Existing limited-diagnostic admissions | **2** | Apple/CBRE only, under the previous approved assumptions |
| Newly admitted stocks / runnable broad comparison | **0 / no** | No silent extension of that approval to 98 additional names |

Under Armour's full observed Class A price stream does **not** clear its
class-distribution/ownership evidence. Known missing company events remain
blockers. CTL/CVS reference snippets do not establish eight-year histories.
FB's adjusted observations cover 1,620 sessions; JNJ, NEE and WMT have 2,012
candidate adjusted timestamps each. Adjustment conventions are not silently
changed to turn those files into raw execution data.

The audit rechecked 33 legacy daily files and replayed the saved raw collection
of 23,747 observations plus the genuine CBRE boundary candle. Three reviewed
alias streams were compared with their original saved versions. The cache
inventory has 60 entries: 59 price files/derived streams and one separately
recorded empty/unavailable source. Overlapping files are not extra stocks or
independent observations.

Across the full 506-row parent register, 14 rows have bound candidate raw
observations and four have full-calendar raw observations. None of those
counts independently certifies identity, action completeness or eligibility.
Raw child/parent quotes under reused AA or FOXA aliases are **not automatically
joined** to an old company. Only the previously reviewed CBRE/Under Armour
alias streams are concatenated.

## 3. Exact comparison, once data and scope qualify

| Setting | Fixed choice |
| --- | --- |
| Control | Existing Apple/CBRE diagnostic inputs |
| Challenger | All 100 roster identities, with required lifecycle branches |
| Warmup and evaluation | 2016 warmup / 2017–2021 account; separate 2019–2021 warmup / 2022–2023 account |
| Capital | $10,000 primary; $100,000 size diagnostic |
| Entry/exit | Existing 55-session breakout, 20-session exit channel, stock/SPY EMA200 filters |
| Stops/holding | Existing fixed initial 3-ATR14 stop, ten-session cooldown and approved continuation reviews |
| Allocation | Existing 5% position / 35% portfolio caps, seven positions, 0.5% planned stop risk, 1% volatility contribution |
| Halts | Existing latched 3% daily / 10% drawdown research controls |
| Competing entries | Existing alphabetical ordering over stable engine instrument IDs; no new ranking model |
| Costs | Same base and pessimistic cases as the small diagnostic |
| Cash scenarios | Same base credit, five-session delay and no-credit cases; unpaid rights remain separate |
| Context/reference | SPY raw price EMA200 only; zero-interest cash reference; no passive SPY total-return benchmark |

The priority clarification matters: the existing engine sorts its instrument
keys, which are stable IDs in historical mode. For Apple/CBRE that also agrees
with ticker order. This plan retains that actual behavior in the larger
universe rather than quietly introducing a new return/confidence ranking.
No stricter entry, extra liquidity threshold, new price screen, ML model,
profit target, trailing-stop change or allocation increase is added.

First replay **all 24 original controls**, requiring exact financial metrics
and fills. New approval/metadata may identify the separate comparison, while
economic behavior must match. A mismatch stops the study before challenger
scores. Then run **24 challenger cases** with the same windows, sizes, costs
and cash scenarios. **Maximum: 48 strategy attempts**, including controls;
no extra neighbors, replacements or retuning.

This would require its own comparison approval and execution allowance. The
completed small experiment's consumed 24-run budget is not reopened. The
100-name input/assumption path is not implemented or authorized by this audit.
Use Windows first, one worker, at most 15 minutes per case and 180 minutes
overall; stop on expiry. Profile runtime/memory before any Pi execution.

## 4. Data gate: don't remove difficult names to make the study run

All 100 selected identities must be accounted for. A stock need not have
2012 quotes if independently supported listing/lifecycle boundaries explain
its actual lifetime. Do not require candles before issuance or after a
delisting, forward-fill a suspension, invent a sale, or value an unknown
terminal outcome at zero.

Required for each applicable historical interval:

- Dated security/class/exchange/alias identity; no automatic mapping from
  current tickers or current asset-catalog status.
- Actual raw SIP/USD daily bars, calendar checks and documented gaps.
- Complete relevant splits, dividends and ownership events with supported
  economic terms, effective boundaries and explicitly labeled timing.
- Supported successor/child prices, entitlement, delivery and fractional/cash
  handling where a selected parent's event creates those holdings. Such a
  branch is not automatically a new discretionary BUY candidate.
- Passed schedule/accounting checks and clear distinction between approved
  research assumptions and independently verified evidence flags.

The old two-stock vendor/timing approval does not cover 98 new companies or
unreviewed mergers/spin-offs. Known contradictory/missing events cannot be
waived by changing a flag. If any required selected history remains unresolved,
the challenger stays blocked. Retain the stock and its blocker; do not replace
it, truncate just before its difficult event or run only the easy survivors.

The older registered eight-arm whole-market/entry/ranking study remains a
separate, blocked study. This proposed two-versus-100 experiment does not
silently replace its nine-stock control or claim whole-market readiness.

## 5. Concrete next data work: free, bounded and not yet executed

The cache alone cannot support the 100-stock comparison. The companion JSON
proposes a finite raw-data acquisition scope for these exact identities:

- **100 candidate IDs maximum**, with 97 lacking full-window raw streams in
  cache. Reuse valid existing files; missing raw quotes and lifecycle evidence
  are separate tasks.
- Only the existing historical bars and company-action **GET endpoints**,
  fixed `sip` / `raw` / `1Day` / `asof="-"`, within `[2016-01-01, 2024-01-01)`.
  Do not change a subscription, feed or adjustment to obtain a response.
- **800 HTTP attempts globally**, at most four pages per symbol/resource,
  at most 24 reviewed probe intervals and 192 attempts per batch. Failed and
  redirect responses count. Budgets accumulate across all batches and any
  separately reviewed successor/alias probes; they never reset.
- Thirty-second request timeout, at least 0.4 seconds between request starts,
  15-minute batch and 60-minute global elapsed-time limits. Stop all batches
  at the first access/payment/rate denial, transport failure or reached limit.
  No automatic retries, redirects, feed fallback, paid upgrade or new batch
  after a global stop.
- Historical snapshot aliases may be probed as **untrusted candidates**;
  save and quarantine returned data until the identity and dates are reviewed.
  A matching ticker string is not an approved attachment. No current-ticker
  substitutions or inferred corporate actions.
- **$0 purchase budget; no JPMorgan, account, order, billing or subscription
  requests.** Public issuer/SEC evidence would need a separate exact-target
  collection list and cap before any document batch; no unbounded searching.

This is a planning specification, not a downloader queue or a purchase request.
The collection helper and cumulative ledger still need implementation. A
bounded collection may end partially successful; it cannot promise every
selected stock will become research-ready for free.

## 6. What we will measure

Report every case: net whole-account return/CAGR after costs and estimated
share exits; realized/open P&L and unpaid rights; closing drawdown and daily-
OHLC uncertainty; per-stock/issuer concentration, turnover, holding periods,
fees and cash. Keep marked rights distinct from spendable money.

For the universe question specifically, compare average/distribution of
invested exposure and spendable cash, days with no holdings or seven holdings,
simultaneous qualifying candidates and rejected entry reasons. Journals that
record the first rejecting check must not be described as measuring every
possible blocker. A rejected trade's later price gain is not realized profit.

More invested capital is a measured outcome, not success by itself. Retain
the 6% annual return goal, 5% running-peak drawdown rejection, five-instrument/
30-trade floors and all other approved acceptance checks. No threshold is
lowered and no cash scenario is selected because it looks better. These are
already explored development years; 2024–2025 remain reserved.

## Evidence, verification scope and responsibilities

- [Frozen 100-name roster](research_data/broad_100_candidate_roster.csv).
- [All 506 current cache statuses](research_data/broad_506_cached_inventory.csv).
- [Selected 100 cache statuses/blockers](research_data/broad_100_cached_inventory.csv).
- [Price-file/source inventory](research_data/broad_cached_file_inventory.csv).
- [Pinned review protocol](broad_sample_qualification_review.json),
  [qualification summary](broad_sample_qualification_summary.json) and
  [comparison/collection specification](broad_100_comparison_plan.json).

Replay only the **offline qualification** into a fresh directory:

```powershell
python -m backtesting.broad_sample_qualification --output data/reports/a_fresh_broad_sample_qualification
```

This run used Windows `.\.venv\Scripts\python.exe`. Local evidence is in
`data/reports/broad_sample_qualification_v1`; ignored source data/reports must
be retained for reproduction. The runner blocks socket connections, checks
input/source hashes and seed selection, replays prior audits and compares raw
CSV/payload/alias observations. It never invokes a strategy engine or loads
credentials. No unit-test suite or Pi execution ran in this increment; the
previous 209-test result belongs to the completed small experiment.

**My next work:** implement and execute the finite free raw-data acquisition
and qualification workflow for the frozen roster, within existing access and
the stated limits. Keep issuer/ownership evidence collection separately scoped.
Report partial coverage and exact blockers without changing the sample.

**Your part now:** no stock picking, purchase, account setup or personal risk-
limit change. Before new performance runs, review the concrete expanded scope
and any new evidence assumptions; this planning task does not approve the 48
runs or paper trading. No approval of paid services is being requested.

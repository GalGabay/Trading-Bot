# Proposed free-data pilot: qualify four saved histories

Date: 2026-10-27. Status: **proposal; no performance runs scheduled or executed
by this increment**.

**Follow-up:** [Cached-source qualification is complete](free_data_pilot_qualification.md).
All four price streams pass the documented checks; full-period identity/action
evidence is still incomplete. The report supplies the action matrix and
bounded free-source collection targets. The proposal and assumptions below
remain unapproved for performance use.

## My recommendation

First qualify **AAPL, JPM and CBRE**, with **SPY as market context**, using
the saved daily raw data from **January 2016 through December 2023**. Review
their identities, splits, dividends and ticker changes before asking the
simulator to calculate another strategy result.

This pilot answers: **Can we build a small, reproducible research dataset
with an honest account of its evidence and assumptions?** It does not answer
whether three stocks can meet your investment goal or whether searching the
whole market improves profit. It is an engineering pilot, with zero strategy
arms, zero parameter searches and zero ML training.

You do not need to select more stocks, change risk limits, install anything
or buy data for this step. I can perform the cached-data qualification work.
The proposed timing assumptions below need review before any later performance
study uses them. Creating this document does not accept them for you.

## 1. Exactly which stocks and why

| Security | Stable research identity / aliases | Role | Saved observations | Evidence still needed |
| --- | --- | --- | ---: | --- |
| Apple | `COHORT-2016-0047`; AAPL | Candidate stock; split and ordinary-dividend case | 2,012 | Full-period identity/action review; the existing 2020 accounting pilot covers only part of this range |
| JPMorgan Chase | `COHORT-2016-0259`; JPM | Candidate stock; ordinary-dividend case | 2,012 | Full-period class/listing and distribution review |
| CBRE Group Class A | `COHORT-2016-0088`; CBG then CBRE | Candidate stock; same-security ticker-change case | 2,012 in the reviewed combined stream | Historical common-share classification and action completeness; empty provider action responses are insufficient |
| SPDR S&P 500 ETF | Separate context identity to be documented; SPY | Market filter, and a passive reference only after its distributions are reviewed | 2,012 | Fund identity/splits; complete distributions for a total-return reference |

**Current status: price coverage observed; none of these full-period histories
is newly certified for strategy scoring.** The data files contain 8,048
observations in total, with the calendar coverage recorded by the preceding
audit. Complete timestamps alone do not establish correct security identity,
complete corporate actions, historical liquidity or executable fills.

These names were already selected for the free engineering collection. They
exercise different data paths without new price downloads. This is a deliberate
convenience sample and includes surviving companies. Do not treat it as an
unbiased investment universe, compare its gains with a full-market strategy,
or replace the 506-row historical register with whichever rows pass.

All three stock rows exist in the saved September 2016 holdings register.
That source became available under the existing conservative convention on
November 30, 2016, not on its September holdings date. This establishes the
dated source basket, not an automatic approval of every identity or action.
CBRE's imported roster label contains `reit_common`; that classification must
be independently checked rather than copied into an executable manifest.

### What is actually saved

- AAPL: 32 provider dividend records and one forward-split record.
- JPM: 32 provider dividend records.
- CBRE: zero provider action records for its queried aliases, despite the
  independently established rename. The actual March 19, 2018 boundary candle
  was recovered under the vendor's CBG label. Use the separate reviewed stream
  and evidence journal; preserve the original bars and `source_symbol`.
- SPY: 29 provider dividend records. This count does **not** certify completeness
  or identify how many records are missing. Review fund distributions independently.

Provider counts are an inventory, not approved event lists. In particular,
do not infer a missing payment amount or date from a quarterly pattern.

## 2. Exact dates and data conventions

| Item | Proposed scope |
| --- | --- |
| File coverage | `[2016-01-01, 2024-01-01)`; start inclusive, end exclusive |
| Actual first / last saved candle | January 4, 2016 / December 29, 2023 |
| Calendar | Existing pinned exchange calendar: 2,012 sessions, including real holidays and early closes |
| Candles | One daily candle per scheduled covered session, saved SIP/raw/USD data; no feed substitution |
| Time labels | Daily bar labels are New York midnight represented in UTC; exchange opens/closes are separate calendar instants |
| Symbol mapping | Existing `asof="-"` source requests; independently reviewed dated aliases, no automatic ticker stitching |
| Reserved prices | Do not read or acquire 2024-2025 candles |
| New price requests in this pilot | Zero; use the four pinned saved streams |

Inspect all eight years for data quality, including warmup data. Warmup
prices can precede the source basket's publication because they are already
historical when a later decision is made; membership must never be used to
trade before its publication bound.

If a later strategy study is separately proposed, keep the earlier development
windows: 2016 warmup followed by 2017-2021 evaluation, then an independent
2022-2023 account with 2019-2021 warmup. Those are already explored development
years, not untouched tests. This document schedules **no performance runs**
in either window and does not establish a newly approved train/test protocol.

## 3. Evidence facts versus proposed research assumptions

A source can establish an issuer's contractual amount and payable date without
showing when a particular broker made cash spendable. We should label that
difference rather than demand unavailable account records or pretend an
assumption is a verified fact.

| Topic | Required source facts | Proposed convention requiring review before performance use |
| --- | --- | --- |
| Public knowledge | Dated primary announcement, contractual terms and effective/ex-session | If only the publication date is known, use the **second actual exchange-session open after that date**, excluding the publication day. This is a conservative modeling convention, not proof of the release time. If it falls after the required event boundary, keep the case blocked |
| Ordinary dividends | Reviewed security identity, ex-date, amount, share basis and issuer payable date | Recognize an economic cash right for the entitled held whole shares; make it spendable at the **first exchange open on a date strictly after the issuer payable date**, in New York calendar dates |
| Payment-delay sensitivity | Same reviewed terms and entitlement | Also evaluate availability **five additional exchange-session opens later** and a **no cash credit before the evaluation window ends** scenario. Keep earned rights outstanding; never delete them or count them twice |
| Equity valuation | Valid quoted holdings and known fixed USD cash rights | Show fixed rights at nominal contractual value, separately from spendable cash. This carries issuer/settlement risk; it is not guaranteed recovery or a fully liquidated cash result |
| Signal prices | Raw candles and effective splits known at the decision time | Rebase past feature prices/volume only for splits effective by that completed session. Retain raw dividend gaps in price-based signals; do not use future-adjusted prices or add dividends twice |
| Cash outside holdings | Actual simulated uninvested cash | Zero interest, unless a separate reviewed study changes that assumption |

The public-knowledge convention here uses **two actual sessions**, consistent
with the earlier Apple research pilot. Some previous source inventories used
two calendar days followed by the next open. They are different conventions.
Preserve those old reports; do not silently reuse their timestamps as though
this proposal had already been applied.

Payment delays are sensitivity assumptions, not a statistically established
range for Alpaca. The no-credit scenario tests cash reuse; nominal rights can
still keep marked equity above spendable cash. Unpaid claims prevent claiming
a fully liquidated return. Never manufacture payment beyond the available
calendar to make year-end balances disappear.

These are **proposed research conventions**. The current ownership adapter's
confirmed entitlement/delivery/availability requirements remain in force.
Do not set verified-evidence flags to true using these assumptions. If a
separate assumption-labeled research mode is needed, propose and implement
it explicitly after review; ordinary issuer terms are not broker-credit proof.
No real merger, spin-off or fractional payout is admitted by this table.

SPY price context and a dividend-inclusive passive SPY reference are separate
uses. Valid raw context prices do not authorize an incomplete total-return
benchmark. If distributions cannot be reviewed, mark that benchmark unavailable;
do not silently substitute a price-only benchmark and call it total return.

## 4. Cases excluded from this pilot

The original cohort and blocked-case register remain intact. Exclusion here
means **outside this engineering sample**, not a historical sell, zero loss,
or permission to erase a failed company from a larger backtest.

| Case | Why it stays outside scored research for now |
| --- | --- |
| WFM and ATVI cash mergers | Eligibility and spendable cash timing not certified; no conversion to an immediate cash exit |
| Aetna/CVS and Level 3/CTL | Delivery, cash availability and fractional allocation unresolved; reference quotes alone are insufficient |
| Original Alcoa / later Arconic / Howmet / new Arconic | Distinct retained-parent/child identities, entitlement and delivery; new Arconic child prices missing; Alcoa advance-publication timing unresolved |
| Under Armour Class A and Class C | Separate classes, distributions and reused aliases; additional Class C per-unit allocation unresolved |
| Fox / Disney | Election, proration, conversion and fractional terms unresolved |
| Bed Bath / BBBYQ | Missing OTC prices and suspension-to-cancellation valuation; no stale mark, fabricated sale or assumed early zero |
| Other 2016 cohort rows | Not yet qualified; retain every original row and its blocker rather than quietly selecting complete files |
| New IPOs after the fixed basket date | Outside a fixed 2016-cohort design; that design cannot claim to cover later IPO opportunities |
| Other asset classes, intraday bars, ML and current all-market scans | Outside this finite daily data pilot |

Do not censor a history just before a difficult event, close holdings using
later knowledge, or choose a shorter period because its return looks better.
If a new unresolved event appears in one of the four chosen streams, stop its
qualification and report it. No automatic replacement stock or easier window.

## 5. Concrete work and stop conditions

### Step A — cached-source qualification: my next engineering work

1. Recheck the four saved stream hashes, source-page provenance and calendar
   coverage. Keep originals unchanged and use a fresh output directory.
2. Produce an identity/alias/classification matrix, including the CBRE label
   issue, and a full-period action matrix: amount, basis, announcement source,
   ex/effective date, issuer payable date, evidence status and proposed timing.
3. Compare provider records with saved primary documents. A later annual
   filing may corroborate a term but cannot establish advance knowledge.
   Record exact missing documents rather than approving all provider records.
4. Separate results into **qualified facts**, **proposed assumptions** and
   **blocked gaps** per stream. An unexplained missing/duplicate candle,
   impossible OHLCV, ambiguous identity, unreviewed event or unsupported
   distribution prevents scoring. Explain volume warnings separately.
5. Deliver a qualification report and, if needed, a finite free public-document
   collection list with exact targets and request limits. This first step uses
   local files only: **zero HTTP requests and zero strategy simulations**.

Do not reopen an unbounded source search. If cached evidence is insufficient,
the result is a clear collection list or blocker. No payment card, paid trial,
subscription change, new dependency or automatic feed fallback.

### Step B — validate a reviewed research convention, only when ready

If you accept the relevant assumptions and the source facts qualify, I can
prepare the separately labeled research input format, accounting checks and
bounded cash-delay replays. The proposal must name the exact runs before
executing them. A sensitivity failure cannot be fixed by choosing whichever
payment delay produces the best return.

### Step C — larger strategy research remains a separate gate

The [existing eight-arm study](broad_entry_selection_study.md) targets historical
market-wide eligibility. A **fixed 506-row September 2016 basket** is a narrower
alternative, needs your scope review, and still requires complete supported
lifecycles, raw prices and actions. It must retain failed/acquired securities
and include supported successor branches. It is not every US stock or daily
index membership. Do not silently substitute it into the eight-arm plan.

Passing this small data pilot permits preparing that next dataset and proposal;
it does not certify the 506 rows or authorize their performance runs. If free
coverage cannot meet that gate, report the historical study as blocked. A
separately proposed prospective read-only shadow study is an alternative:
record future eligible symbols/signals without submitting orders. It cannot
reconstruct missing past evidence and does not start automatically.

## 6. Your decisions, and when

| Decision | Needed now? | How to do it |
| --- | --- | --- |
| Let me qualify these four cached histories | No extra action; the requested engineering work is already authorized | I can do Step A next and show the report |
| Accept modeled knowledge/payment timing | Before a performance study relies on it; not needed to inspect cached evidence | Review section 3 and tell me your choice in chat; I will record an explicit approval rather than invent one |
| Use a fixed 2016 basket instead of historical whole-market eligibility | Before designing/scoring that narrower strategy comparison | Review the separate scope proposal after the pilot; no need to choose hundreds of tickers |
| Change the investment target | No | Keep the approved criteria: at least 6% annualized net return, 5% drawdown rejection and all other acceptance checks |
| Choose personal paper-risk limits | Later, before activation | Use the existing risk workbook and JSON with guidance; research conventions do not approve paper risk |
| Authorize paper trading or paid data | No | This proposal authorizes neither; the no-purchase policy continues |

The current acceptance configuration also requires at least **five instruments**
and **30 completed trades**, among other checks. Three candidate stocks cannot
satisfy the instrument requirement, even if their hypothetical return is high.
Do not lower acceptance thresholds or call this pilot a paper candidate.

## 7. Reviewable artifacts and limits of this increment

The companion [proposal JSON](free_data_pilot_proposal.json) records the exact
files/hashes, scope, blocked cases, proposed assumptions and unapproved status.
It is a planning artifact, not an executable universe, approved schedule,
download command or trading configuration. It is not loaded by the bot.

This increment creates documentation only. No unit tests, new accounting
replays, strategy backtests, downloads or API calls were run. The previously
reported 183 tests/36 financial/36 risk/84 mechanics results remain historical
evidence for that preceding increment, not new results for this proposal.
No purchases, orders, account access or 2024-2025 price reads occurred.

**Next after the completed Step A:** collect the bounded free/public primary
sources listed in the qualification report. You have no configuration task;
assumption and research-scope approval are needed before their later use in
performance research.

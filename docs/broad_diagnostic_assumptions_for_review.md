# Diagnostic accounting assumptions to review before Step 2

Status: proposed, October 29, 2026. **No approval inferred.**

This document describes how a historical simulation would handle company events
when public/provider data does not establish exact broker receipt. These are
research conventions. They do not enable paper orders, spend money, or certify
that the broker actually delivered cash or shares at the modeled times.

Your **70% total account entry exposure** decision is already recorded. You do
not need to approve it again. Personal paper-risk limits remain a later decision.

## What I recommend for your review

| Item | Proposed default | What it means |
| --- | --- | --- |
| Research mode | Explicitly labelled, vendor-dependent diagnostic research. | We can investigate performance while reporting the remaining evidence limitations. Strict source/settlement certification stays false. |
| Ordinary dividends | Prior saved-session close whole-share ownership establishes the modeled right, before ex-date open fills. | Buying on the ex-date earns no dividend. Selling after the right is established does not erase it. Special/foreign/unclassified distributions stay blocked. |
| Missing announcement dates | Historical `known_at` stays unknown. Vendor accounting metadata is assumed observable at the event boundary for the replay. | This retrospective assumption is used for accounting only. It must never become a strategy entry, ranking or confidence feature. It does not prove what a live system knew. |
| Known payable date | Base: cash becomes available at the first saved exchange open strictly after that date. | A weekend/holiday is handled by the saved calendar. A payable date is not treated as a verified broker credit timestamp. |
| Missing payable date | Keep a receivable; give it no spendable cash or invented payment date. | A known gross amount may contribute to marked equity, but cannot fund another purchase. The result is not fully liquidated cash. |
| Received whole shares | Base: release at the first saved open at or after the economic event and regular trading start, once required terms are resolved. | Shares cannot be sold before that modeled availability. This is an assumed delivery rule, not broker confirmation. |
| Timing sensitivity | Also run a five-additional-session delay and a no-credit/no-delivery scenario. | No-credit leaves known rights outstanding and valued; it does not delete their economic value. These scenarios are not guaranteed upper/lower return bounds. |
| Fractional shares | Keep an exact fractional claim; do not automatically sell it or invent a cash fixing. | Mark it using an exact current-session quote when available. A later cash payment needs explicit fixing/payment terms. |
| Unknown values | Mark equity incomplete and block scoring and new entries. | Missing quotes or unknown cash amounts never become zero, stale marks, or future prices. |
| Cash/share valuation | Known fixed cash at face value; pending shares at the exact current saved-session close. | This is a research valuation assumption. It assumes collection of known nominal cash and has no tax, FX or counterparty-discount model. |
| Dividend currency and share basis | Gross USD for provider nonforeign ordinary records; assumed post-split share basis. | Provider records often omit currency. Foreign/special/ambiguous records and simultaneous split/dividend boundaries require further review. This is not independent currency/share-basis verification. |
| Election/proration events | Block until individual holder terms are resolved. | We cannot choose an AIV/SLG all-cash or all-stock outcome, or copy aggregate company totals into a portfolio. Your approval of defaults does not supply missing economic facts. |
| Pending rights and risk | Include their marked values in equity/exposure; unknown risk marks block new entries. | Unpaid rights are not buying power. Step 2 must integrate their risk contribution atomically with the main ledger. |
| PEAK continuity | Preserve the economic holding/age and candidate feature history through the one-for-one legal-parent change, with stale execution state invalidated. | A legal reorganization creates no extra profit, cash or new purchase. The first February 10 session open is a daily modeling convention; exact intraday effective time remains unverified. |
| JCI continuity | Reset at September 6, 2016; keep earlier predecessor prices reference-only. | Do not feed the old company into later JCI indicators. The separate ADNT distribution still needs resolution before features can warm through that event. |

The implementation stores these choices in
[the proposed policy JSON](broad_diagnostic_accounting_policy.json).
It currently has `owner_approved: false`, `performance_authorized: false`,
`paper_authorized: false` and a strategy-run allowance of zero.

## Two proposed allocation settings

These are **simulation settings for your review**, not personal paper-risk limits:

- **5% per stock at entry**, or up to $500 of a hypothetical $10,000 account.
  Existing stop/volatility sizing may allocate less. This is an entry cap, not a
  guarantee that market movements keep the holding below 5% afterwards.
- **20 simultaneous positions**, allowing more than the old seven. Combined
  entries still respect your selected **70% total exposure**. Neither the cap
  nor the position allowance forces the strategy to invest when signals are absent.

These two numeric defaults remain proposed; they are not inferred from your
70% selection. Keep the existing deterministic strategy, costs and pre-2024
development/validation boundaries when the eventual experiment is frozen.
A new performance-run budget and comparison scope still need a concrete plan;
this preparation does not approve or consume strategy attempts.

## What approval would cover

If these defaults suit you, you can say:

> I approve the proposed diagnostic accounting defaults and the 5%-per-stock /
> 20-position research settings. Keep unresolved terms blocked.

Or specify which rows/settings you want changed. You can reply here; you do
not need to edit Python, JSON, `.env`, or a personal risk file. I will record any
decision in a separate versioned approval record. Do not flip flags in old
protocols or replace their hashes.

This approval would cover the stated research assumptions and allocation
defaults. It would not authorize a purchase, paper activation, a new performance
batch, fabricated source evidence, or ignoring unresolved company events.

## Engineering work that remains mine

1. Focused unit tests for the new mapping and accounting modules; the earlier
   193-test result covers the prior implementation only.
2. Resolve JCI/ADNT feature handling, AIV/SLG election economics and the remaining
   primary terms/identity gaps. Keep all 100 selected members in the inventory;
   do not silently remove difficult stocks or interpret an unknown event as no event.
3. Implement the approved Step 2 bridge: apply ownership changes once, preserve
   rights after sales, carry claims through window boundaries, invalidate stale
   order/stop state, reconcile transfers and include pending values in risk.
   The main strategy simulator is not connected to the new pending-rights book yet.
4. Present the finite performance comparison plan and its remaining limitations
   before calculating new returns. Paper readiness and activation come afterwards.

No purchases, broker requests, market-data downloads, orders or profit/loss runs
occurred during this implementation. New unit tests were not added or run.

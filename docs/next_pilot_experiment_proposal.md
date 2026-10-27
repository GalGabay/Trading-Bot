# Next return experiment: limited AAPL/CBRE diagnostic

**Proposed, not approved or executed.** This is the concrete route following
the [cached evidence review](remaining_pilot_readiness.md). The
[JSON specification](next_pilot_experiment_proposal.json) freezes input/code
hashes, assumptions, costs, dates and the run limit. It is not a bot config.

## What this experiment would answer

How does the existing swing-trading rule behave on the saved Apple/CBRE raw
histories when the documented split, ticker change and Apple dividends are
accounted for explicitly, including different cash delays and trading costs?
This is a small exploratory accounting/strategy diagnostic. The sample was
selected for available engineering cases and includes surviving stocks.
It cannot establish unbiased market performance or qualify a paper strategy.

## Fixed scope: 24 runs maximum

| Item | Proposed choice |
| --- | --- |
| Traded stocks | AAPL and CBRE, with reviewed CBG/CBRE alias mapping |
| Market filter | SPY raw completed-close price relative to EMA200; no SPY trades |
| Candles | Saved SIP/raw/USD daily bars only; no new downloads |
| First window | 2016 warmup, independent account trading 2017–2021 |
| Second window | 2019–2021 warmup, independent account trading 2022–2023 |
| Capital | $10,000 primary; $100,000 size diagnostic |
| Rule | Existing 55-session breakout / 20-session exit channel, stock/SPY EMA200 filters, fixed initial three-ATR14 stop and ten-session reentry cooldown |
| Holding review | Existing `continuation_30`: review after held sessions 30,35,40,45,50,55,60 and then 90,120,...; retain only with a fresh prior-20-session high, positive estimated net sale profit and stock/SPY above EMA200; ordinary exits/stops remain active |
| Allocation | Existing `vol_latched`: 5% position / 35% account caps, 0.5% planned stop-risk cap, 1% annualized volatility contribution, seven-position maximum, alphabetical BUY priority |
| Research halts | Existing latched 3% daily-loss / 10% drawdown controls; no new personal paper-risk approval |
| Costs | Base: 5 bps adverse slippage per side, 2 bps full spread, no per-order fee. Pessimistic: 20 bps slippage per side, 10 bps full spread, $1 per order. Half the spread is applied per side. |
| Cash timing | First actual exchange open strictly after the issuer payable date; five additional opens later; no cash credit within the window with rights retained |

One rule × two windows × two capital amounts × two cost cases × three cash
scenarios = **24 runs**. No parameter sweep, additional arms, stock replacement,
larger exposure, ML, 2024–2025 candles or automatic follow-on runs.

The windows are already explored development history. The two-name scope
differs from the old universe, and raw causal split treatment differs from
the old all-adjusted inputs. Differences in returns therefore cannot be
attributed solely to a better strategy or solely to dividend accounting.
The original registered control and historical results remain unchanged.

The two-stock scope leaves substantial idle cash under the existing position
caps. This experiment is not expected or required to establish the 6% goal;
the original investment acceptance checks remain in force for a future
adequately scoped candidate. The old research halt values do not guarantee
the separate 5% drawdown rejection threshold will be respected.

## Assumptions requiring your review

1. **Vendor reliance for this diagnostic only.** Use saved provider Apple
   dividend ex-dates and the reviewed ticker mappings/action inventory as
   exploratory inputs. Independent full-period identity/action certification
   and Apple ex-date proof remain missing. Report these limitations rather
   than label the histories certified or clear strict evidence flags.
2. **Knowledge timing.** For date-only Apple declarations, use the second
   actual exchange-session open after that date. Use the dated issuer split
   announcement and CBRE filing for their events. Reject a required event if
   its modeled knowledge bound falls after its effective boundary. This is
   a convention, not a verified historical publication timestamp.
3. **Ordinary dividend entitlement.** Model Apple cash rights for held whole
   shares at the provider ex-date, with source-supported nominal amounts and
   payable dates. No special distributions, unreviewed due bills or fractions.
   This does not prove how a real broker credited a shareholder.
4. **Cash delays and valuation.** Run all three listed timing scenarios.
   Report fixed nominal receivables separately from spendable cash. A right
   that has not been paid is not settled profit; keep it outstanding rather
   than inventing a payment or discarding it.
5. **Prices and context.** Retain raw dividend price gaps; rebase past feature
   prices/volume for a split only once effective. SPY provides a price-only
   trend filter. Do not calculate a passive SPY total-return reference, turn
   blank gain cells into zero or use dividend metadata to trade the filter.
   Cash earns zero interest. No REIT-tax-status filter uses CBRE's unresolved
   original label.

These choices relax the evidentiary admission standard **only for this named
diagnostic**. They cannot cure impossible prices, missing sessions, conflicting
source terms, unsupported event kinds or accounting failures. Any such issue
stops the runs. The strict universe/ownership workflow and its independently
verified entitlement/payment requirements stay intact.

## What I must implement and verify before running it

- A separate versioned diagnostic input/mode and explicit assumption journal;
  owner approval and verified source flags remain different fields.
- Pinned event/calendar input derivation, without modifying raw files or
  original protocols.
- Split share/feature/stop handling, alias continuity, ordinary cash rights,
  exact-once event processing, the three payment scenarios and ledger checks.
- Failure handling that stops on invalid/contradictory inputs or failed
  accounting checks before accepting a performance result.

No assumption-based mode is implemented by the current evidence review.
The engine must not receive fabricated strict evidence approvals merely to
make a manifest load. Verification can use synthetic cases and saved-data
replays; this proposal requests approval of that work before performance use.

## Results you would receive

All 24 results, including losses and failed criteria: net marked return/CAGR,
drawdown and daily-OHLC uncertainty, fees/slippage/spread, trade and holding
statistics, per-stock contribution, idle cash, cash availability and unpaid
rights. Separate realized profit, open holdings and estimated final sale costs.
Do not call an account with outstanding rights fully liquidated.

SPY total-return benchmarking stays unavailable for this experiment. A
zero-yield cash reference is explicit. Do not pick the best payment delay or
window and suppress the others. Because there are only **two traded stocks**
and unresolved evidence assumptions, the run cannot satisfy the existing
five-instrument gate or approve paper trading, even with high returns.

## Your decision and timing

To take this route, you can reply:

> Approve the limited AAPL/CBRE diagnostic and its listed vendor/timing assumptions.

That approves the named research implementation, verification and bounded
performance batch after checks pass. It does **not** approve purchases,
personal paper-risk settings, paper trading, changed investment criteria or
the broader historical-universe study.

After approval, my next implementation is the separate diagnostic mode and
its verification, followed by this finite batch if the checks pass. It does
not require another JPMorgan search or a paid source. I cannot promise a
date, positive profits or success on the investment goal; failures remain
visible rather than triggering another search or relaxed criteria.

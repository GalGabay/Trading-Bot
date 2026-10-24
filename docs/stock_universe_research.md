# Stock-universe scope: what these studies can establish

## Current scope

The daily studies use **12 fixed stocks and ETFs**: AAPL, MSFT, JPM, JNJ,
XOM, WMT, CAT, PG, NEE, SPY, QQQ, IWM. The current paper workflow is disabled;
it does not automatically scan or trade the whole market. The reviewed
research universe must match the intended paper scope before activation.

These are present-day familiar survivors, not a historical market-wide
universe. Results cannot establish what would have happened when searching
all stocks, including failures and delistings. A poor small-basket result
does not rule out every other universe; it also does not imply larger-basket
results will be better.

## Does a wider search make sense?

It can create more entry opportunities and different diversification, but
also more weak/noisy signals, competing entries, correlated positions, data
exceptions, and costs. With only seven positions, we need an explicit
selection rule when many stocks qualify. Existing alphabetical priority is
not a ranking of expected future profit. A broader search or tighter entry
rules changes the strategy and must be researched before paper use.

Tighter entry conditions do not automatically mean better stocks: they can
reduce trading opportunities and increase idle cash. Keep universe, entry,
and exit hypotheses distinct enough to measure what caused a difference.
The approved holding-time study deliberately leaves universe and entries
fixed. It is useful for that narrow comparison, not broad-market readiness.

## Can research cover all stocks?

**Broad US-equity research is technically possible**, subject to data
coverage, account entitlement, storage, API limits, and engineering work.
"All stocks" needs a definition: for example, historically listed US common
stocks on selected exchanges, versus current Alpaca-tradable assets. It does
not mean every global stock is available through one broker.

Alpaca supplies an [asset-list API](https://docs.alpaca.markets/us/reference/get-v2-assets-1)
and [historical bars for lists of symbols](https://docs.alpaca.markets/us/reference/stockbars).
The bars response is paginated; its limit is per response rather than per
symbol. Today’s assets list alone does not establish daily historical
membership, prior tradability, or complete delisting outcomes. Those must
be separately obtained and audited; do not claim the endpoint solves
historical survivor selection by itself.

The current shared-cash engine requires identical candle dates for all
symbols. A historical broad universe has IPOs, suspensions, and delistings,
so extending it requires:

1. Stable instrument identity, historical listing/eligibility dates, ticker
   changes, and delisting/corporate-action handling.
2. Membership and eligibility checks using information available on each
   historical date. Price/liquidity screens must use prior information.
3. Session-aware missing-data rules that distinguish a pre-IPO period from
   a missing candle during an eligible trading period. No price filling.
4. A portfolio engine that can handle entries/exits from the universe and
   terminal outcomes, rather than intersecting all histories and discarding
   inconvenient instruments or dates.
5. A predeclared ranking/tie-break rule, shared capital/cost/risk constraints,
   and a matched small-versus-broad comparison with an untouched later test.
6. Read-only availability and coverage auditing before committing to a
   paid source. Research runs belong on Windows/the development machine;
   profile and bound the Pi runtime before deploying any large scanner.

## Suggested sequence

Finish and report the already approved holding-time comparison. Then make
the next scope decision from its results. A sensible separate next proposal
is a **broad-universe data-feasibility audit**, followed by a finite matched
universe/entry study only if historical membership and coverage are adequate.
The outcome may be a narrower, explicitly qualified universe rather than
an unsupported "entire market" claim.

The owner does not need to collect thousands of CSVs manually. Codex can
build the tooling after the scope is agreed. Any data subscription needs
separate approval; no purchase, all-market download, entry tightening,
ranking model, or paper activation was performed in this task.

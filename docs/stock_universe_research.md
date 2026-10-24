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

The default shared-cash engine requires identical candle dates. Initial
[optional historical-universe support](historical_universe_format.md) now
accepts explicitly dated IPO/listing intervals and known terminal cash
payments. Full historical-universe research still requires:

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

The owner authorized the **broad-universe feasibility audit**, now
[completed](broad_universe_audit_results.md): 33,560 catalog records and 56
fixed historical coverage probes. Broader daily price access works, but the
catalog does not supply complete historical membership or lifecycle outcomes.

The finite [entry/selection study](broad_entry_selection_study.md) is scoped
with eight matched arms. Simulation waits for audited historical inputs,
validated dynamic-universe behavior and corporate-action coverage. The
[free-data update](free_data_and_lifecycle_progress.md) records the owner's
$0 new-purchase policy and newly demonstrated company-event access. No owner
risk settings or account upgrade are needed for the next engineering work.
No whole-market performance claim or paper activation is approved.

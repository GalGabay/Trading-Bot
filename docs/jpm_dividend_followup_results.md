# JPMorgan capped follow-up: completed, remaining work parked

**Executed 2026-10-27.** The single attempt found and archived one additional
common-stock dividend declaration. It stopped when the public-discovery cap
was reached. **JPMorgan is now parked outside active engineering-pilot
collection**, following your instruction to move forward if incomplete.
No further JPMorgan collection is scheduled.

## Activity and stop

| Measure | Actual | Limit |
| --- | --- | --- |
| Public discovery tool calls | 4 | 4 |
| Direct public-document GET attempts | 1 | 8 |
| Successfully saved documents | 1 | — |
| Elapsed collection time | 117.42 seconds | 600 seconds |
| Purchases / subscription changes | $0 / 0 | $0 / 0 |
| Broker/account requests / orders | 0 / 0 | 0 / 0 |
| Price requests / strategy runs | 0 / 0 | 0 / 0 |

The [plan](jpm_dividend_followup_plan.md) says to stop when any cap is reached.
Reaching four discovery calls therefore ended acquisition with unused direct
GET capacity. The limit was not reset or reinterpreted to extend the attempt.
Other individual announcements appeared in search results, but they were not
downloaded or counted as newly archived confirmation. No reviewed multi-event
document resolved the remaining targets within the cap. This is a bounded
partial result, not proof that the other documents are unavailable or paid.

The only direct request returned **HTTP 200** on the allowed main issuer host.
Its execution used explicit network permission, no ambient credentials/proxy
authentication, no automatic retries and no automatic redirects. The earlier
HTTP 403 and its stopped batch remain unchanged; that host was not retried.
There was no new access-barrier response in this attempt.

## Evidence found

The [issuer's December 8, 2015 announcement](https://www.jpmorganchase.com/ir/news/2015/id-946137)
declares a **$0.44 common-share dividend**, with record date **January 6,
2016** and contractual payable date **January 31, 2016**. The archived amount
matches exactly the provider event whose ex-date is January 4, 2016.

The new [one-row reconciliation](research_data/jpm_dividend_followup_reconciliation.csv)
retains both provider and issuer fields, source URL/hash and the join basis.
The release does not independently state an ex-date. Matching amount and
declaration/record boundaries does not certify entitlement, exact historical
public availability or broker credit. A weekend contractual payable date is
retained as stated, not silently changed to the next trading day.

| Evidence count | Before | After |
| --- | --- | --- |
| JPM provider dividends with collected primary declarations | 2 of 32 | 3 of 32 |
| Remaining declaration targets | 30 | **29** |
| Original provider payable omissions still without collected primary terms | 16 | **15** |

The [29-row remaining list](research_data/jpm_dividend_followup_remaining.csv)
records the parked disposition. The original provider CSV, original 66-row
primary reconciliation, target checklist and earlier summaries are untouched.
The one new row is a separate overlay, not a rewrite of the old report.
December 2015 declaration metadata is within this plan's allowance for the
January 2016 dividend. No reserved 2024–2025 candles were read. Unrelated
later-year search results were discarded from the evidence review.

## Evidence preservation and checks

The [tracked execution summary](jpm_dividend_followup_summary.json) pins the
plan, old inputs, new outputs and local request/source evidence. Raw evidence
is in `data/reports/jpm_dividend_followup_v1`, including four discovery logs,
the reviewed exact-URL queue, HTTP report, saved HTML, cumulative state,
executed collector snapshot and offline reconciliation script. Local source
files remain outside Git; keep them to reproduce the source review.

Offline checks passed for input/source/queue hashes, 4/1 request counters,
elapsed time, source terms, an exact Decimal amount comparison and the
30-minus-one target difference. No conflicts were found in the single matched
row. These are data checks, not new unit-test-suite results. No unit tests,
dependency installations, Raspberry Pi execution or strategy backtests ran.
Earlier test totals remain historical evidence.

## Move forward without another JPMorgan search

The active engineering candidates are now **AAPL and CBRE**, with **SPY as
context only**. Next I will review their remaining identity/action and timing
gaps from cached evidence and report which exact dates/events qualify, which
remain blocked and whether a defensible next backtest scope can be proposed.
Their qualification is not assumed merely because JPMorgan is parked.

JPMorgan remains in the 506-row historical register and registered nine-stock
strategy control. Old results and minimum acceptance requirements are unchanged.
No replacement has been chosen based on returns. A two-stock engineering
sample cannot satisfy the existing five-instrument/30-trade research minimum
or establish whole-market performance. Any narrower performance experiment
needs an explicit scope review; this result does not approve strategy scoring.

**Your part now:** nothing to configure or buy. Research timing assumptions
still need your review before performance use, and personal paper-risk limits
and activation remain separate later decisions. No real money moved and no
paper or live trades were submitted.

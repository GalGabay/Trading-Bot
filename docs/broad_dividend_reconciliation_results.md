# Dividend reconciliation — 2026-10-30

## Where this fits

**Still Step 1: qualify and reconcile the historical inputs.** Step 2 connects
these inputs and the diagnostic accounting to the portfolio simulator. That
integration remains gated by unresolved company-event and dividend terms.
There are no new broader-basket profit/loss results in this increment.

The owner's accepted research settings remain 70% total entry exposure, 5% per
stock and 20 concurrent positions. No additional owner configuration is needed
for this data work. Those settings do not guarantee that 70% will be invested.

## Completed

Reviewed five of the 22 ambiguous dividend groups, retaining all ten provider
records. An explicit decision file records the economic treatment; the original
44 records across all 22 groups remain untouched.

| Issuer / ex-date | Finding | Implemented treatment |
| --- | --- | --- |
| CTAS / 2020-11-05 | Separate annual $2.81 and quarterly $0.70 payments, both payable December 4 | Retain both entitlements: $3.51 total per eligible share |
| FCX / 2023-10-12 | The $0.15 total includes $0.075 base plus $0.075 variable | Retain the total; mark the base representation as having no independent entitlement |
| MAC / 2020-04-21 | $0.50 value distributed through cash and stock elections | Block ordinary cash credit; neither provider rate becomes assumed cash |
| AIV / 2020-11-03 | Previously saved primary evidence describes a cash/stock election | Replace the generic component ambiguity with an explicit election block |
| SLG / 2020-12-14 | Previously saved primary evidence describes a cash/stock election | Replace the generic component ambiguity with an explicit election block |

The [Cintas annual report](https://www.cintas.com/pdf/Cintas-FY2022-10K.pdf),
printed page 23, lists both payments. The
[Freeport declaration](https://investors.fcx.com/investors/news-releases/news-release-details/2023/Freeport-McMoRan-Declares-Quarterly-Cash-Dividends-on-Common-Stock-fc4bfaa40/default.aspx)
states the component breakdown. The
[Macerich announcement](https://investing.macerich.com/news-releases/news-release-details/macerich-announces-reduction-quarterly-dividend-050-share)
describes the election and its default cash/stock proportions. Its conversion
price and actual holder treatment are not established by that announcement.

Seagate's issuer history supports a single $0.67 ordinary payment for the
May 12, 2021 record date, payable July 7. It does not independently resolve the
two provider identities or the foreign/currency treatment. Both rows stay gated.
Other ordinary AIV/SLG duplicate groups still need dated primary support;
matching amounts alone do not qualify them for deletion or aggregation.

## Implementation and reproducibility

- `backtesting/dividend_components.py` validates complete observed groups,
  unique decisions, pinned evidence, dates and exact rational component amounts.
- Preparation accepts an explicit `--dividend-review` file. Omission retains
  the original conservative behavior. Every decision is attached to its audit
  rows; unrelated blockers remain effective.
- A component represented by a total keeps its original provider record, has
  zero independent entitlement and no cash-release time. No rows are deleted.
- Election rows have unknown cash amounts and no cash-release time. No default
  holder choice or share conversion is invented.
- The preflight checks the pinned decision file and evidence files. Strict
  ownership admission, verified historical availability and actual receipt
  flags remain unchanged.
- Prior executed compiler/preflight sources were archived under
  `docs/research_data/diagnostic_executed_v5/`. Policy v5 and earlier reports
  remain intact; this run uses policy v6.

The separate bounded public review closed after eight searches and eight page
opens. Four opened pages are saved together as browser text; four additional
opens are listed in the facts record and are not used to admit the decisions.
Browser extractions are not original HTML archives. No previously denied URLs
were retried and no collection batch is left open.

## Offline preparation results

Preparation succeeded for base, five-session delay and no-credit scenarios.
All 100 original members and all 2,698 provider dividend records are retained.
The output contains 8,094 dividend audit rows across the three scenarios.

Base dividend statuses: 1,170 modeled payments, 1,358 receivable-only candidates,
169 blocked rows and one component represented by its aggregate total.
The readiness gate has **234 overlapping blocking rows**, down from 238:
25 material-event terms, 166 dividend terms and 43 provider identity/event rows.
These counts are constraints on the data, not counts of proposed trades or
necessarily distinct economic events. The three excluded predecessor reference
rows remain in the audit output without becoming portfolio rights or run gates.

The normal compiler and preflight ran successfully with their runtime checks.
**No unit-test suite ran for this increment.** Earlier reported test totals
describe earlier code; they are not verification of these new changes.
No strategy, historical performance batch, trade, broker request or purchase ran.
No reserved 2024–2025 price files were read.

Current artifacts:

- [Explicit component decisions](broad_dividend_component_decisions_2026-10-30.json)
- [Primary facts and closed request journal](broad_dividend_primary_facts_2026-10-30.json)
- [Preparation summary](broad_diagnostic_component_preparation_2026-10-30.json)
- [Readiness report and remaining gates](broad_diagnostic_component_preflight_2026-10-30.json)

## Next

Engineering work: focused offline tests for the reconciliation, then resolve
the remaining dated dividend and material-event terms. Step 2 integration
follows when the readiness gate clears. A bounded performance experiment must
be defined separately before reporting new historical returns. The owner has
nothing further to configure or buy for the current data work.

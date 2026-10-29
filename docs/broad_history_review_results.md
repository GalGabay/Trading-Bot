# Collector tests and partial-history review

Completed **2026-10-29**. No new broker/price requests, purchases, orders or
strategy simulations occurred. Historical cash amounts below describe old
company-event terms; they are not money spent or received by this project.

## Tests

**147 passed, 0 failures, 0 errors, 0 skips** in the final verification run:
76 new tests (64 collector/qualifier/evidence and 12 history-review tests),
plus 71 related candle/public-collector/parser tests.

The new tests cover:

- Cumulative and batch request caps, clocks, request spacing and timeout bounds.
- Payment/access/rate/server denials, redirects, connection failures and no retry.
- Original byte preservation, page-size limits and malformed JSON.
- Repeated pagination, four-page exhaustion, cache reuse and exact roster order.
- Existing-output protection, one-shot journal and interrupted-request accounting.
- Candle timestamps/timezones, duplicates, dates/session boundaries, OHLC,
  nonpositive prices, volume errors/warnings, unordered/empty/partial data.
- Identical versus conflicting action duplicates, missing payment/declaration
  fields, price-move flags, incoming aliases and unapproved evidence status.
- Economic event dates separated from last trading and actual delivery dates;
  no mutation, invented transition, dividend credit or successor attachment.

Fake credentials and temporary synthetic workspaces were used. The final
runner blocked actual socket connections and real credential loading.
An earlier extended run had nine errors because its temporary fixture lacked
the source file needed for a code-hash record; the fixture was corrected.
No production collector or original frozen protocol was changed to make
the tests pass.

Evidence: [structured test summary](broad_collection_test_summary.json).
The verbose log is retained in ignored
`data/reports/broad_collection_verification_v1/unit_tests.log`.
Windows only; no Pi execution or full-project test suite is claimed.

## Review findings for the 17 partial histories

The new [offline review module](../backtesting/broad_history_review.py)
checks preserved observations against a separately recorded
[primary-fact/discovery journal](broad_history_review_facts.json).
All 100 original candidates remain; only the 17 partial cases are classified
here. Their current [case table](research_data/broad_partial_history_review.csv)
and [review summary](broad_history_review_summary.json) preserve exact sources,
access levels and remaining tasks. No returned price was edited or joined.

| Original alias | Review finding | What remains |
|---|---|---|
| RTN | April 3, 2020 merger; 2.3348 UTC/RTX shares per old share, with fractional cash. | Successor valuation/actions, delivery and fractions. |
| FB | META replaces FB on June 9, 2022; same class/CUSIP. | Later raw META quotes and full event checks. |
| CBS | Saved series stops December 4, 2019; provider rename date is February 13, 2020. | Adequate primary terms and exact transition still unresolved. |
| BLL | Primary search evidence supports BALL from May 10, 2022. Direct page returned 403. | Preserve barrier; archive/check source and later quotes/split history. |
| FISV | FI begins June 7, 2023 after exchange transfer. | Dated FI quotes and complete class/event review. |
| DLPH | Original parent becomes APTV; one child share per three parent shares; child later uses DLPH. | Separate parent and child; distribution/merger/fractional accounting. |
| MYL | One Viatris share per Mylan share in November 2020 combination. | Resolve VTRSV versus VTRS, regular trading and delivery. |
| XL | Original issuer converted to $57.60 cash rights in September 2018; vendor series continues into 2022. | Separate identities and cash delivery; later XL is not presumed the original holding. |
| ESRX | December 20, 2018 merger; $48.75 plus 0.2434 New Cigna shares. | New CI valuation/actions, cash/share delivery and fractions. |
| CTL | LUMN replaces CTL from September 18, 2020. | Dated successor quotes and later distributions/actions. |
| LLL | June 2019 merger; 1.3 LHX shares per old share; original LLL stopped June 28. | Separate later reused ticker, delivery and LHX valuation. |
| BHI | One BHGE Class A share plus $17.50 special dividend; BHGE opens July 5, 2017. | Entitlement/due bills, July 6 payable terms and later successor history. |
| RHT | July 9, 2019 acquisition for $190 cash per share. | Actual receipt policy and complete dividend/event record. |
| SYMC | Remaining company becomes NLOK on November 5, 2019 after asset sale. | Subsequent quotes, distributions and later aliases; not a whole-company cash exit. |
| NLSN | October 11, 2022 closing at $28/share; no exchange trading from October 12. | Cash delivery and full event history. |
| CSRA | SEC closing filing gives April 3, 2018 and $41.25/share; issuer page metadata differs. | Precise suspension/delivery timing; do not infer from the last candle. |
| MON | June 7, 2018 Monsanto acquisition at $128/share; vendor MON continues through 2022. | Separate later identities, exact original boundary and cash receipt. |

The four unsegmented streams **DLPH, XL, LLL and MON cannot represent the
original 2016 holdings as downloaded**. The journal marks the inference from
the historical source and returned data; it does not automatically certify
where every later candle belongs.

For example, [Delphi's SEC filing](https://www.sec.gov/Archives/edgar/data/1707092/000119312517364954/d494581d8k.htm)
distinguishes the retained Aptiv parent from the distributed Delphi child.
[L3Harris's completion release](https://investors.l3harris.com/news/news-details/2019/L3Harris-Technologies-Merger-Successfully-Completed-Board-of-Directors-Leadership-and-Organization-Structure-Announced-07-01-2019/default.aspx)
states the original LLL trading end and conversion. The
[XL closing filing](https://www.sec.gov/Archives/edgar/data/875159/000087515918000068/axaclosing8-k.htm)
and [Monsanto completion exhibit](https://www.sec.gov/Archives/edgar/data/1110783/000119312518186836/d602943dex991.htm)
support their original cash outcomes. Those facts explain why a structurally
valid candle stream can still produce an invalid backtest.

## Public-source bounds and remaining limitations

The [new review protocol](broad_history_review_protocol.json) allowed at most
18 search queries and 20 page opens, $0 purchases, no price/account endpoints,
and no automatic retries. Actual use: **18 search queries and 8 page opens**
dispatched, seven successful and one Ball **403**. Six other opens were already
in that same dispatched batch; no further retrieval started after the barrier
was observed. The earlier Bayer-site denial is preserved; the Monsanto fact
above came from a distinct SEC exhibit in this separately scoped review.

Source access levels are explicit: seven fact references were opened, Ball
remains search evidence with a denied direct open, eight other references
are search-only discoveries, and CBS lacks an adequate primary reference.
No original HTML body was archived in this increment. These notes do not
constitute complete executable source evidence or a publication-time record.
Counts refer to tool queries/opens, not undocumented internal search-service
HTTP traffic. No access workaround or paid alternative was used.

The earlier **1,334 missing provider payable dates**, 2,421 missing declaration
dates, known Under Armour distributions, and other material events remain
gates. Complete calendars do not automatically establish complete actions.
No new stock was admitted, and no broader return has been calculated.

## Expanded assumptions and allocation

Your request for more invested capacity is reflected in the concrete
[higher-exposure backtest proposal](broad_expanded_backtest_proposal.md):
five matched arms separate universe size, 7-versus-20 slots and 35%/70%/90%
account exposure. The per-stock entry cap stays 5%. It declares all periods,
cost/cash scenarios, 120 maximum attempts, missing-date treatment, successor
disposal proposal, unchanged acceptance criteria and implementation gates.
It is prepared for review, not approved execution or a paper-risk change.

**Next - my work:** correct and verify historical issuer/alias segments and
the exact free successor-data/event package, then implement the broader
diagnostic input/runner. **Your part:** review the proposed research caps and
expanded assumptions in chat before that future performance batch. No purchase,
installation or paper-risk JSON change is due now.

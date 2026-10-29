# Step 1 verification and event review — October 29, 2026

This continues **Step 1: prepare historical inputs**. Step 2 connects the
prepared input to the existing simulator. **Step 1 remains in progress.**
Your selected **70% total account entry exposure** is unchanged. No purchase,
subscription change, broker request, price download, trade or return simulation
occurred in this increment. Free public-source browsing was separate from tests.

## Tests and fixes

**193 tests passed; zero failures, errors or skips:** 46 new focused tests and
147 related regression tests. See the [test summary](broad_input_verification_summary.json).

Coverage includes saved response bytes, request journals, response-read failures,
access/rate/server stops, no retries, cumulative request/time budgets, pagination,
malformed/oversize responses, exclusive outputs, source/code hashes, stopped
parent collections, timezone-aware budget clocks and credential setup failures.
Input tests cover all 100 retained IDs, dated alias intervals, missing/duplicate/
invalid candles, calendar boundaries, event roots, exact ratios, unknown cash,
invalid cash amounts, and refusal to promote delivery or execution flags.
Review tests distinguish direct primary support from search-only discovery.

Fixed the existing modules and added a small shared
[input guard module](../backtesting/input_guards.py). Tests use synthetic
temporary files, fake credentials and blocked real socket/credential access.
An initial test-fixture error was corrected. A real-data replay also caught an
overly strict check on unknown cash: `null` is now preserved, never changed to
zero. Both have regression coverage. Intermediate successful runs are retained.

The hardened builder reconstructed **119 candidate streams** from saved data.
All **203,683 candle rows match the original v3 files byte-for-byte**, and all
100 original members were retained. No candles were fabricated or forward-filled.
See the [replay comparison](broad_input_replay_verification.json) and
[rebuild summary](broad_input_verified_rebuild_summary.json). Complete configured
intervals remain candidate coverage, not complete issuer-lifecycle admission.
The builder's `unit_tests_run: 0` means it does not itself invoke tests; the
separate test summary records the suite above.

The new local package is `data/reports/broad_historical_input_verified_v4`.
The original v3 output and frozen protocols remain preserved. The
[three originally executed modules](research_data/step1_executed_v1/README.md)
were archived byte-for-byte; their hashes match the old execution records.
Current collectors intentionally fail the old execution-code pins because those
acquisition plans are closed. Do not update old hashes or delete journals to
restart collection. Future collection needs a separate bounded protocol.

## Source findings

A separate [review scope](broad_event_review_scope.json) used eight searches and
eight browser opens: seven returned primary text; the SLG 2022 filing timed out
and was not retried. PHINIA's browser open automatically resolved an issuer path
redirect; no separate redirect followup was requested. Counts describe browser
tool calls, not hidden HTTP hops. Earlier SEC/Ball/Bayer access barriers remain
preserved. No previously denied URL was retried.

The [primary review](broad_event_primary_review.json) and
[browser evidence inventory](broad_event_browser_evidence.json) distinguish
direct browser text, search-only discovery, original HTML capture and actual
broker settlement. Browser text is not an original HTML archive or settlement
certification.

| Event | Finding | Remaining work |
| --- | --- | --- |
| AIV 2019 | Genuine 1-for-1.03119 reverse split linked to a special stock/cash dividend. | Individual election, proration, ownership and fractions. |
| AIV 2020 | Special dividend share issuance precedes a genuine 1-for-1.23821 reverse split. | Preserve ordering and model each holder's outcome. |
| SLG 2021 | Genuine reverse split after a special election dividend. | Common-stock election/proration terms; option deliverables are not stockholder allocations. |
| SLG 2022 | Search-only filing text indicates a dividend/reverse-split sequence. | Direct primary filing remains missing after timeout. |
| BF.B 2018 | Genuine 5-for-4 stock split; a fractional ratio can be valid. | Fractional handling and receipt/known-at policy. |
| PEAK 2023 | Holding-company reorganization with equivalent shares, one for one. | Explicit old/new legal-parent mapping and effective-time policy. |
| JCI 2016 | The 0.955 ratio belongs to old Tyco; old JCI holders had different merger outcomes. | Separate predecessor histories before computing warmup indicators. |
| BWA/PHIN 2023 | Distribution completed July 3 after close; regular trading started July 5. | Correct the economic date in a new spec; ratio and broker receipt remain unverified. |

Primary sources: [AIV 2019](https://investors.aircommunities.com/press-releases/news-details/2019/Apartment-Investment-and-Management-Company-Sets-Ratio-for-Reverse-Stock-Split-02-13-2019/default.aspx),
[AIV 2020](https://investors.aircommunities.com/press-releases/news-details/2020/Apartment-Investment-And-Management-Company-Sets-Ratio-For-Reverse-Stock-Split/default.aspx),
[OCC SLG memo](https://infomemo.theocc.com/infomemos?number=48188),
[SLG filing, search-only after timeout](https://www.sec.gov/Archives/edgar/data/1040971/000104097122000014/slg-20211231.htm),
[Brown-Forman](https://investors.brown-forman.com/investors/stock-information/dividend-history/default.aspx),
[Healthpeak](https://ir.healthpeak.com/news/news-details/2023/Healthpeak-Announces-Closing-of-Holding-Company-Reorganization-02-10-2023/default.aspx),
[JCI filing](https://www.sec.gov/Archives/edgar/data/53669/000110465916143072/a16-17944_18k.htm),
[PHINIA](https://www.phinia.com/newsroom---events/newsroom/news/2023/07/04/phinia-inc.-completes-spin-off-from-borgwarner).

### The 39-record review queue

The new [offline review module](../backtesting/event_review.py) retains every
original ID and date in a [review overlay](research_data/broad_event_review.csv).
Its [summary](broad_event_review_summary.json) records:

- **6 provider-event interpretations supported by direct primary text**:
  AIV twice, SLG 2021, BF.B, PEAK and JCI.
- **7 provider records linked to existing candidate events**: APD, VNO, VFC,
  AIV's separation, two Dow/DuPont factors and the Delphi child. These need
  economic reconciliation; applying both a provider adjustment and a child
  distribution could double count.
- **1 SLG 2022 record remains search-only.**
- **25 material candidate records remain**, including PHIN's proposed date
  correction from direct primary text.

Several economic ambiguities were clarified. **All 39 records still have
execution-admission work**; none was dropped, booked or marked settled.

## Remaining work and next step

**My next work, still Step 1:**

1. Create an event-corrected candidate revision for JCI's predecessor boundary,
   PEAK's legal-parent transition and PHIN's distribution/trading dates.
   Uninvested warmup prevents portfolio credits but cannot prevent contaminated
   indicators from incorrectly joined predecessor prices.
2. Resolve linked AIV/SLG dividend-election mechanics and remaining child,
   merger, entitlement and fractional terms. PHIN's ratio and K/KLG still need
   direct primary support. This source-review budget is closed; no automatic
   retry, source purchase or paid fallback follows.
3. Implement a clearly labelled diagnostic settlement/timing policy for research
   where actual historical broker receipt cannot be observed. Present concrete
   assumptions before expanded return simulations; never mark assumed times
   as verified broker delivery.
4. Address dividend availability: **1,383 of 2,698 candidates lack payable dates;
   all 2,698 lack declaration dates** in the provider records. No ex-date cash,
   invented payment date or future-known signal is allowed. Missing income
   needs an explicit accounting/valuation policy.

Then **Step 2** integrates the prepared input with the existing backtester.
`performance_ready`, strict admission and paper authorization remain false.
There are **no new win/loss percentages** in this increment.

**Your part now:** nothing to install, buy or configure; no repeated approval of
70%. Before the expanded return run, review the concrete simulation assumptions
and scope I present. Personal paper-risk limits and activation remain later
decisions. Windows was verified; Pi execution remains unverified.

Re-run the focused suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_input_preparation -v
```

Use the Pi's own environment `python` for the same test module. Retain the ignored
evidence folders when transferring research evidence; Git alone does not copy them.

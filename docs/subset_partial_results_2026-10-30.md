# Step 3: partial results and stopped execution

October 30, 2026. **Step 3 is incomplete; Step 4 has not been completed.**
The approved run stopped on its fourth attempt: three cases completed and one
timed out. No automatic retry or further strategy attempt was made. All amounts
below belong to simulated $10,000 accounts; purchases and orders were zero.

## What the completed comparison says

Both rows use the same frozen breakout rules, **2017–2021**, base trading costs
and base payment/delivery assumptions. Returns cover the entire five-year window.
The third completed case is the two-stock control with delayed availability;
its financial returns matched the first control case.

| Measure | AAPL/CBRE control | 76-stock sample |
| --- | ---: | ---: |
| Total net marked return | +4.40% | +6.29% |
| Annualized return | +0.87% | +1.23% |
| Simulated net marked profit | $440.11 | $629.21 |
| Maximum closing drawdown | −0.69% | −10.02% |
| Average spendable cash | 97.35% | 80.63% |
| Closed trades | 35 | 305 |
| Profit factor | 2.52 | 1.16 |

More stocks provided more trades and increased average committed capital from
about 2.65% to 19.37%, including unpaid rights. A 70% entry cap is a maximum,
not a target allocation. Qualification, sizing, exits and risk halts still
limit investment. The larger sample reached its frozen 10% drawdown halt on
July 30, 2018, after which new entries remained disabled under that rule.
This helps explain the low utilization over the full window.

The broader case **fails the approved 6% annualized return and 5% drawdown goals**,
and its profit factor is below 1.2. Its average modeled holding time was 29.49
calendar days. The results do not justify starting paper trading.

These are marked account returns after modeled costs and estimated whole-share
exit costs, including nominal unpaid rights; they are not settled cash gains.
The 5% per-stock and 70% total limits apply to entries; market moves can make
later marked percentages higher. No pessimistic-cost case or 2022–2023 case
completed. The declared primary pessimistic-cost comparison is unavailable.
Historical data-availability selection can bias this exploratory subset.

## Why execution stopped and what was fixed

The original protocol allowed 24 attempts, ten minutes per case and two hours
overall, stopping at the first failure without retries. The fourth attempt
timed out; its uncompleted result is excluded. Recorded timestamps also show a
long pause or clock discontinuity. Its reservation-to-stop wall interval was
about 26 minutes despite the monotonic ten-minute deadline. The precise cause
of the scheduling/clock discrepancy is unknown. A suspended computer cannot
execute a timeout handler until it resumes.

After stopping, engineering added wall-clock checks alongside monotonic checks
in both supervisor and worker. It also removed repeated full-calendar copies
from diagnostic financial transactions and cached validated session sets.
Rollback tests retain once-only transfers and complete restoration on failure.
New mutable ledger state fails closed until its rollback policy is reviewed.

**184 focused offline tests passed; zero failures, errors or skips.** These
include 37 runner tests and 12 report tests. All three saved cases reproduce
their original financial and external-price reports exactly. A saved control
accounting replay fell from 36.17 to 1.41 seconds; that measurement is not a
new strategy simulation. No strategy attempt occurred after the stop.
Raspberry Pi execution and timing remain unverified.

## Evidence and next action

- [Tracked partial summary](research_data/subset_partial_2026-10-30_summary.json)
- [All completed cases](research_data/subset_partial_2026-10-30_all_cases.csv)
- [Per-stock contributions](research_data/subset_partial_2026-10-30_root_contributions.csv)
- [Post-stop tests, saved replays and original source snapshots](subset_recovery_verification_2026-10-30.json)
- [Recovery proposal requiring a separate decision](subset_recovery_for_review.md)

The original stopped ledger, approvals, protocol and historical verification
records are preserved. Current source checks intentionally differ from the
original execution proofs after the fixes; old proofs must not be rewritten.
Original full case files and logs remain under the ignored local
`data/reports/approved_subset_comparison_v1/` directory. Keep that directory
with the research archive; the compact tracked reports do not replace it.

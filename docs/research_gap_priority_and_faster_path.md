# Which data gaps can wait, and a faster route to results

October 30, 2026. **Step 1 of 4.** The owner asked whether minor unresolved
details could be skipped to make faster progress. This review separates already
approved accounting conventions from missing economic facts and proposes a
separate, smaller exploratory scope.

## What does not need perfect evidence before diagnostic research

- We do not need an actual broker credit timestamp for every old payment. The
  approved base/delay/no-credit scenarios model availability explicitly.
- We do not need to invent a fractional cash payment. Exact unspendable share
  claims can retain their value under the approved current-quote convention.
- Historical announcement timing that remains unknown can stay unknown under
  the approved retrospective accounting-only convention; it must not become an
  entry/ranking feature or independently verified historical knowledge.

Those conventions already avoid unnecessary evidence requirements. They still
require a correct right and share quantity, supported ownership timing, and a
valid current mark. An unknown value cannot be treated as zero.

## What cannot be silently labelled unimportant

- Wrong issuer/ticker identity, missing merger/spin-off terms and an unknown
  share multiplier can change the holding itself and create false profits.
- An ambiguous cash component can cause the same payment to be credited twice.
- An unsupported ex-date/record-date rule can credit a seller instead of the
  buyer, or award a dividend to an ex-date opening purchase.
- Approximate share quantities do not provide an exact holder allocation unless
  an explicit supported formula establishes it. A rounded number alone is not
  evidence of the rounding rule, precision or error bound.

The dollar effect depends on simulated holdings and later trading decisions.
We have not run a valid sensitivity analysis proving these outstanding terms
immaterial. Small-looking source numbers are not sufficient justification to
remove a gate.

## Bounded MAC/SLG review

A final targeted scope allowed six search queries and six page opens. Six
queries were used; no new matching primary schedule was found to open. Matching
SLG notices continue to describe approximate final shares. No new matching
primary MAC ex-distribution notice was located. No previous failed URL was
retried, and no discovery excerpt was promoted to proof.

The saved primary SLG notice already supplies a reverse-split fractional cash
pricing rule based on the relevant closing price. That is separate from the
unresolved exact dividend allocation and actual account payment. Confirming a
fractional pricing rule alone does not resolve the original share quantity.
MAC's reported formula remains documented, with its ownership schedule still
unadmitted. No economic gate was removed in this review.

- [Separate search scope](broad_targeted_schedule_scope_2026-10-30.json)
- [Closed review record](broad_targeted_schedule_results_2026-10-30.json)

## The practical faster path

The existing 188 blocking rows map to **24 original roots**, including their
descendants. The other **76 original roots** have no rows flagged by the current
preflight report. Their inputs represent 79 legal/reference/received-security
streams. This is not an assertion of complete independent data certification.

The [offline scope audit](faster_research_scope_audit.json) checks input/output
pins, roster identity, explicit descendant mappings and complete classification
of all 100 originals. It reads no candle files, profits, credentials or broker
accounts. A reproducible command is available:

```powershell
.\.venv\Scripts\python.exe -m backtesting.scope_feasibility `
  --preparation data/reports/broad_diagnostic_approved_2026_10_30_v14/summary.json `
  --preflight docs/broad_holder_tests_preflight_2026-10-30.json `
  --output data/reports/scope_feasibility_new
```

The proposed comparison uses the fixed 76-root subset against AAPL/CBRE, with
the same approved 70% total exposure / 5% per stock / 20 positions, existing
strategy and development windows. Limiting it to a $10,000 simulated account
gives 24 maximum cases across the existing cost/accounting scenarios. There
is no paid collection or paper activation.

The original fixed-100 protocol explicitly forbids omitting members. Excluding
24 stocks is therefore a scope decision, rather than a minor accounting fix.
The exact proposal and complete inventory have been prepared before asking for
that decision:

- [Plain-language comparison and limits](faster_research_scope_for_review.md)
- [Exact proposed IDs, parameters and budgets](faster_research_scope_proposal.json)
- [Pinned review context and unchanged acceptance criteria](faster_research_scope_review.json)
- [All 100 originals and their proposed classifications](research_data/faster_research_scope_inventory.csv)

Selecting a subset using observed historical data availability can bias results.
It is explicitly an exploratory comparison and cannot establish full-basket
performance or paper readiness. The deferred 24 stocks remain in the original
inventory. Their events are not silently ignored in a held position, and no
replacement stocks are selected.

## Current state and next work

The audit completed offline; its 76/24 split accounts for all 100 original roots.
The original 188 gates and the full-basket Step 1 status are unchanged. This
increment added no unit tests or new performance runs. The preceding 641-test
result covers the prior ownership/trading code, not the new scope-audit utility.
Raspberry Pi execution remains unverified.

The original conditional wording "we can try to skip it maybe" was not treated
as approval to exclude 24 stocks. A concrete proposal was prepared and presented.
The owner then explicitly replied **"Approve 76-stock comparison (Recommended)"**.
That separate [approval record](faster_research_owner_approval_2026-10-30.json)
binds the presented proposal, review context and unchanged acceptance criteria.
The proposal/review files retain their pre-decision status as frozen evidence;
the separate owner record supplies the decision.

The [approved subset preparation](approved_subset_preparation_results.md) now
validates 149,113 observed candles across 79 streams, replays the original full
preflight unchanged and finds zero subset economic-data gates. Step 1 inputs
are prepared for this separate diagnostic scope. Step 2 is next: implement and
verify the pending-rights/portfolio bridge and control accounting. The capped
Step 3 comparison is authorized only after those checks pass; no performance
attempt has occurred. Step 4 explains results and remaining paper-readiness work.
The original full-100 research still has unresolved MAC/SLG and other gates.

No money was spent, subscriptions changed, packages installed, credentials read,
broker requests made, orders placed or price data downloaded. No reserved
2024-2025 candle files were read and no new profit/loss result was calculated.

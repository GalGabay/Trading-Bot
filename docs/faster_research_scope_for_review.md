# Faster exploratory research: a separate 76-stock scope

## My recommendation

Use the **76 original stocks with no currently reported preflight blockers** for
the next exploratory comparison. Keep all 100 in the original inventory and
retain the 24 deferred cases and their unresolved events. This avoids waiting
for every obscure company-event document before learning more about capital use.

This is a **new research scope**, not completion of the full 100-stock study.
The existing frozen plan explicitly requires every original member and forbids
removing unavailable members. Your suggestion to skip unimportant issues does
not clearly approve excluding 24 entire stocks; that is the concrete choice
presented here.

## What was checked

The offline audit matched the pinned preparation and readiness report, checked
their execution/output checksums, mapped every descendant to its original root,
and retained the original roster order. It found:

| Item | Count |
| --- | ---: |
| Original stocks retained in the inventory | 100 |
| Proposed exploratory stocks | 76 |
| Their legal/reference/received-security streams | 79 |
| Deferred original stocks | 24 |
| Existing blocking rows belonging to deferred stocks | 188 |

"No reported blockers" means the existing listed checks found none on those
roots. It is not a fresh price/source certification or proof that all corporate
actions have been captured. The separately prepared subset still needs input
validation and Step 2 ledger integration.

The complete list is in [the 100-row inventory](research_data/faster_research_scope_inventory.csv).
The 24 deferred snapshot symbols are RTN, EOG, DOW, BLL, FISV, DLPH, MYL,
ESRX, LLL, BHI, EXC, COST, RCL, VNO, NLSN, VFC, STX, CSRA, JCI, AIV, HCP,
SLG, BF.B and MAC. These are historical snapshot labels, not a current ticker
catalog. No replacement stocks or rerolls are proposed.

## Exactly what I propose to compare

- **Two arms:** the existing AAPL/CBRE control versus the fixed 76-stock subset.
- **Same allocation in both:** 70% total entry exposure, 5% per-stock entry cap,
  at most 20 positions. Signals and sizing can use less; no forced investment.
- **Same frozen daily breakout strategy:** 55-session entry, 20-session exit,
  stock/SPY EMA200 filters, existing ATR stop/sizing, cooldown, alphabetical
  priority and approved holding-review rules. No parameter search or ML.
- **Two existing development windows:** 2017-2021 with 2016 warmup, and 2022-2023
  with 2019-2021 warmup. Each starts its own account; they are not a continuous
  compounded return. Warmup is uninvested; existing membership-availability
  constraints remain. Do not access reserved 2024-2025 candles.
- **One simulated account size:** $10,000, reducing the previous proposed batch.
- **Two existing cost cases:** base (5 bps slippage per side, 2 bps full spread,
  zero commission) and pessimistic (20 bps slippage per side, 10 bps full spread,
  $1 commission per order).
- **Three approved accounting scenarios:** base availability, five additional
  saved-session delay, and no credit/delivery within the window. Known unpaid
  rights retain value and cannot fund buys; unknown marks block scoring/entries.
- **24 maximum strategy attempts:** 2 arms x 2 windows x 2 costs x 3 accounting
  scenarios. No automatic parameter changes, reruns or replacement candidates.
- **Runtime cap:** one worker, 10 minutes per case, 120 minutes overall. Profile
  and enforce the limits before performance runs; stop on timeout or a failed
  input/ledger check. The cap may end an incomplete batch; never count it as a pass.
- **Report:** net return/CAGR, peak drawdown, capital use/cash, trade count,
  holding time, concentration and cost/accounting sensitivity. Keep the existing
  6% annual return / 5% drawdown evaluation criteria unchanged, together with
  2% daily-loss rejection, at least 30 completed trades, five instruments and
  1.2 profit factor. Passing these numbers on this subset alone is insufficient
  for paper acceptance.

The strategy's frozen historical halt settings remain 3% daily loss and 10%
drawdown. These differ from the stricter evaluation/rejection criteria above;
the experiment must report and reject a threshold breach, not claim those halt
settings guarantee a 5% maximum loss. They are not personal paper-risk approval.

These dollar values describe simulated account size and cost assumptions.
No actual money is spent. No subscription, purchase, broker request or paper
order is proposed.

## What can be simplified, and what cannot

| Gap | Treatment |
| --- | --- |
| Actual broker payment/receipt timestamp absent | Use the already approved diagnostic availability scenarios; do not wait for a personal-account receipt document. |
| Fractional payment amount/date unknown | Keep an exact unspendable share claim with the approved current-quote valuation; do not invent a cash sale or discard its value. |
| Incorrect issuer identity, unknown share multiplier, conflicting dividend components or unsupported holder rights | Cannot silently ignore these in a held security. They can change cash, shares, signals, exits and measured returns. |
| Difficult stock excluded from an exploratory scope | List it explicitly, keep its original evidence, and disclose selection bias. Do not present subset returns as full-basket returns. |

Fractions are not automatically negligible: their value depends on the share
price and quantities. The existing pending-claim method avoids needing an exact
cash settlement without assuming the economic right is zero.

## Limits of the proposed results

The subset is selected **after observing historical data availability**. That
can bias returns, even though no strategy profits were inspected to choose it.
It is not an unbiased historical all-market or full-basket experiment. It may
contain acquisitions and received shares; those still need supported accounting.

Use the results to investigate whether more opportunities improve capital use
and whether the strategy merits further research. Higher returns are not
guaranteed. A successful subset result alone does not establish paper readiness
or fulfil all acceptance requirements. Full-universe evidence and later paper
activation remain separate.

## What an approval would authorize

Approval would cover this separate scope, its disclosed selection bias and the
capped 24-run comparison **after** its input, integration and control checks pass.
It would not alter the original 100-stock protocol, authorize dropping held
rights, permit unknown economic facts to be fabricated, allow paid data, or
activate paper trading. The original files remain frozen.

The work before any performance attempt is mine: prepare the separate pinned
inputs, complete and verify the Step 2 bridge, reconcile control accounting and
enforce run limits. This proposal removes the requirement to resolve the 24
deferred stocks before that separate experiment; it does not remove this
engineering work.

**Current status: Step 1.** Proposed subset approval is pending; no new strategy
run has occurred. You can approve in chat; no Python, JSON or `.env` editing is
needed.

- [Exact proposed IDs, parameters, windows and budgets](faster_research_scope_proposal.json)
- [Audit summary and execution pins](faster_research_scope_audit.json)
- [Original roster classification](research_data/faster_research_scope_inventory.csv)

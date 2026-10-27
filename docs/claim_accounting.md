# Delayed cash, successor shares and spin-off accounting

**Subsequent integration, 2026-10-27:** The [ownership adapter](ownership_adapter.md)
now connects this ledger to the simulator through a separate reviewed schedule.
It uses opening reference values, inherited stop/order policies, feature resets
and claim-aware report replay. Compilation is complete; new integration tests
and regression execution remain due. The 111/84 results below are historical
evidence from the preceding standalone component, not fresh integration results.

## What this step does

The offline [ownership ledger](../backtesting/claim_accounting.py) now accounts
for cash rights that have not been paid, acquisitions involving cash and
successor shares, retained-parent spin-offs, same-class stock distributions,
and fractional-share claims. It uses exact rational arithmetic and stable
company/security IDs. A reused ticker never determines who owns a claim.

**All holdings, cash and profit/loss in these checks are simulated.** Nothing
was purchased, paid to a broker, invested or traded in an account. This step
uses saved files only: zero network requests, credentials, orders, subscription
changes, package installations or new purchases. No 2024–2025 candles were read.

This increment provided a checked accounting component and replay command.
It was subsequently connected through the optional adapter above. Earlier historical-universe action scopes
remain restricted to their supported split/dividend/immediate-cash events;
they continue rejecting unsupported event declarations. Daily risk reporting
still rejects standalone ledger snapshots; structured adapter reports now
have a separate accounting replay instead of omitting their claims.
The larger entry/selection study remains unscored.

## Accounting rules

| Item | Recorded value | Spendable? | What resolves it? |
| --- | --- | --- | --- |
| Fixed cash merger right | Exact contractual nominal USD amount | No | A separate reviewed cash-availability instruction |
| Whole delivered successor/child shares | Actual identity-matched current quote | Held shares; sale requires an explicit simulated fill | Sale or another supported event |
| Fractional-share claim | Exact fractional units × actual current successor quote | No; cannot be submitted as a whole-share sale | A reviewed total cash allocation, followed by a separate payment |
| Fixed fractional cash allocation | Exact documented total cash, replacing the share-priced claim | No | A separate reviewed cash-availability instruction |

There is no automatic T+N assumption. An issuer payable date does not establish
spendable broker cash. Unknown payout amounts/dates leave claims outstanding,
including at the end of a replay. Claims survive sale of the related whole
shares; payment removes the claim and credits cash exactly once.

An exchange consumes the original holding. A spin-off retains it and creates
a distinct child holding/claim. An existing successor holding remains a
separate lot; it is never overwritten. A same-class stock dividend adds units
without treating those units as a market purchase. No event generates a fake
buy/sell fill or adds event income to a stock-trade win count.

### Basis and valuation conventions

- The original economic book basis is allocated across retained shares,
  successor shares, fractional units and cash rights in proportion to their
  **contemporaneous close values**. This is a research reconciliation policy,
  **not tax basis**. Future prices or future fractional cash allocations do
  not determine the allocation.
- A converted parent holding is aggregated using its oldest acquisition time.
  Existing destination lots remain separate. This is not preservation of every
  original tax lot; a strategy adapter must explicitly accept the age convention.
- Rational values such as `1/3` are stored/reportable exactly. There is no
  silent cent or share rounding. A real fractional payout must supply the
  reviewed total allocation rather than derive a price from aggregate issuer
  cash totals. Reporting strings containing `/` are fractions, not errors.
- Fixed cash rights are valued at nominal USD, without discounting or a credit
  risk model. This assumption does not establish risk-free recoverability.
- Equity equals spendable cash plus fixed cash rights plus whole/fractional
  ownership value. Cash, economic basis and realized/unrealized P&L must
  reconcile exactly. Claims never increase the cash available for a purchase.
- `ClaimLedger.mark` also reports conservative lower/upper daily OHLC bounds.
  Fractions contribute price exposure until a cash allocation is known. Fixed
  rights do not contribute stock exposure. Simultaneous highs/lows are bounds,
  not observed intraday portfolio values. These are **current-ownership snapshot
  bounds**: they exclude pre-event/pre-fill holdings and cannot certify a full
  session drawdown or the approved research drawdown goal.

### Timing and unresolved inputs

All timestamps must be timezone aware. Operations and successful marks advance
one accounting clock; a caller cannot inspect a future mark then backdate an
event. Each required quote must match the exact accounting instant and stable
identity. Missing, stale or future quotes raise; nothing is forward-filled.

Ownership terms must be explicitly approved with `terms_complete=True`, known
by their effective accounting instant, and processed before affected fills
at that instant. Same-parent simultaneous events must be consolidated into
reviewed terms. Every event/payment/fixing has a unique ID; repeats raise
without mutation. Failed operations restore the entire prior ledger state.

The ledger expects **already established eligible ownership**. It does not
infer record-date or due-bill entitlement from a distribution-date holding.
The caller must certify delivery of whole shares at the recognition instant.
Undelivered whole-share rights, elections/proration, actions on outstanding
fractional ownership, partial cash installments, withholding/tax, FX, special
dividends and uncertain recoveries need further adapters/evidence. They must
not be approximated as ordinary splits or immediate cash.

## Checks using the saved cases

The [case specification](claim_accounting_cases.json) pins the earlier review
and gap report. The replay verifies primary-file hashes, the original collection
report, raw-price CSV hashes, calendar hashes, source phrases and the actual
event-session quote. It does not make a network request or load `.env`.

Each case starts with hypothetical eligible holdings at an arbitrary declared
entry price. Timing/delivery assumptions are stated separately from sourced
historical terms. Those assumptions **do not clear the real evidence gaps**.

| Saved case | Arithmetic checked | Remaining historical limitation |
| --- | --- | --- |
| Whole Foods | Three shares become a simulated fixed cash right; parent disappears, cash stays unchanged | Public-knowledge timing and spendable credit unverified |
| Activision | Same delayed-right treatment using the sourced merger amount | Provider payable date is not broker credit evidence |
| Aetna → CVS | Three parent shares create two whole CVS shares, exactly 0.5134 fractional units and a cash right | Publication, delivery and actual fractional payout/credit timing |
| Level 3 → CenturyLink | Three parent shares create four whole CTL shares, exactly 0.2858 fractional units and a cash right | Publication/delivery and fractional-treatment evidence |
| Old Alcoa → retained Arconic + new Alcoa | Ten eligible post-reverse-split parent shares remain ten, with three child shares and exactly 1/3 fractional unit | Record-date/due-bill eligibility, delivery and payout |
| Old Arconic → retained Howmet + new Arconic | Three parent shares remain three; the child right is exactly 3/4 of a share | Missing child quote correctly rejects valuation; a separate synthetic quote checks arithmetic only |
| Under Armour Class A → additional distinct Class C | Three Class A shares remain three and create three Class C shares | Mechanical scenario uses first regular quote April 8, not the actual April 7 distribution; entitlement and source timing unverified |

The last two cases must not be interpreted as corrected historical portfolio
paths. In particular, the newer Arconic price was **not** downloaded, inferred
from Howmet or fabricated in a historical CSV. Its invented arithmetic quote
is labeled synthetic and remains confined to a non-scoring check artifact.

A separately labeled **fully synthetic settlement timeline** checks sale of
whole shares, continuing fractional exposure, delayed cash credit, fractional
cash fixing, a later credit, and duplicate rejection. It does not supply any
of the missing historical payment dates or payout amounts.

Fox/Disney remains blocked for unresolved election/conversion terms. The saved
Under Armour annual report confirms an additional distribution's aggregate
shares/cash, but does not certify a per-share ratio or individual fractional
allocation; none is invented. Bed Bath's missing OTC history and late
cancellation evidence remain blocked.

## Verification and reproduction

On Windows, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_claim_accounting tests.test_universe tests.test_corporate_actions tests.test_action_risk tests.test_risk_diagnostics
.\.venv\Scripts\python.exe -m backtesting.claim_accounting_audit --output data/reports/a_fresh_claim_accounting_check
```

The core ledger uses the Python standard library. The replay uses existing
project dependencies and the previously saved ignored evidence. On a Pi use
that machine's Python/virtual environment; copy/review the evidence separately
if replaying there. Pi execution is not yet verified. A missing local source
fails; it never triggers an automatic download or purchase.

Verification on Windows: **111 unit tests passed** (26 new ownership-ledger
tests plus 85 existing universe/action/risk tests), **84 saved-case/timeline
checks passed**, zero final failures. The first unit run found a shallow-copy
mistake in a rollback test; the test snapshot was fixed to use a deep copy.
An initial source-phrase check stopped on the abbreviated Level 3 publication
date; the case now uses the exact saved full date. Neither failed run wrote
or altered old evidence. The complete unrelated/optional-ML test suite was not
run in this step.

The current [tracked summary](claim_accounting_summary.json) records the
inputs, code hashes, checks, scenario assumptions and blockers. Detailed marks
and journals are under `data/reports/claim_accounting_v2/`. The earlier v1
mechanics report remains separate and is not rewritten after code changes.

## Next work and your responsibilities

**At the end of this component increment, my next work was:** connect the component to the portfolio simulator through
an explicit historical-event adapter. That must cover event timing/eligibility,
delivery, pending orders and stops, inherited-position holding reviews, feature
history across distributions, ordinary dividends/splits on inherited holdings,
and cash/exposure/risk reporting. The adapter must reject unsupported inputs
and preserve prior event-free results. Continue free-source evidence review
for payment availability, fractional outcomes and missing child/OTC prices.

That opt-in connection is now implemented in the subsequent adapter. Its
focused integration/regression verification and remaining evidence review are
still gates before expanding/scoring the larger basket; passing
mechanical accounting checks is not proof of higher strategy returns.

**Your work now:** nothing to configure, purchase, download or approve for
this engineering step. No risk-limit JSON change is due now. Research-scope
review and eventual paper activation remain separate owner decisions.

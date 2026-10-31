# Choosing paper-trading risk limits

For a step-by-step decision worksheet with fill-in dollar amounts, see the
[risk-limit decision workbook](risk_limit_decision_workbook.md). For the exact
phase when your decision is needed, see the
[owner responsibilities checklist](owner_responsibilities.md).

The bot is paper-only. These limits are for a *paper account's equity*, not a
percentage of household savings. The values in
`config/risk_limits.example.json` are provisional b development examples; they
are not a recommended allocation or a claim that a strategy is profitable.

## What each value means

| JSON field | Meaning | Example at $10,000 paper equity |
| --- | --- | --- |
| `max_portfolio_exposure` | Maximum gross value of open holdings divided by equity | `0.70` permits up to $7,000 in holdings |
| `max_single_position` | Maximum value of one new position divided by equity | `0.10` permits up to $1,000 in one stock |
| `max_risk_per_trade` | Maximum *planned* loss to the proposed stop divided by equity | `0.01` gives a $100 stop-risk budget |
| `max_daily_loss` | Equity drop from the previous trading-day close at which new orders stop | `0.03` stops new orders at a $300 drop |
| `max_drawdown` | Equity drop from the recorded peak at which new orders stop | `0.10` stops new orders at a $1,000 drop from a $10,000 peak |
| `max_positions` | Maximum number of simultaneous long positions | `7` |
| `max_snapshot_age_seconds` | Oldest acceptable account snapshot at decision time | `300` seconds |
| `max_signal_age_seconds` | Oldest acceptable strategy signal at decision time | `300` seconds |

For a proposed entry at $100 and stop at $90, the stop distance is $10/share.
A $100 planned stop-risk budget permits 10 whole shares *before* the other
caps are applied. The position sizer takes the smallest permitted quantity
under stop risk, single-position value, portfolio exposure, cash, and optional
sector exposure. A stop price is not a guaranteed execution price; actual
loss can be larger, especially in a gap or volatile market.

`max_sector_exposure` and `max_annualized_volatility` are `null` by default.
Only enable them after reliable sector classifications or volatility estimates
are available. If enabled, the risk gate requires the corresponding data.

## How to choose your numbers

1. Decide what the paper account is meant to simulate and how much loss in
   dollars you are willing to observe before stopping and investigating.
2. Convert your dollar ceilings to fractions of that paper equity. For
   example, a $200 daily stop on $10,000 is `0.02`. The JSON fields use
   fractions, not whole percentages: `0.02` means 2%.
3. Check whether several correlated positions could lose together. A low
   per-trade budget does not guarantee a low portfolio loss.
4. Review the strategy's out-of-sample drawdowns and worse-cost scenarios.
   Treat those results as evidence for stress testing, not a promise of future
   losses or returns. Reconsider the limits if a plausible bad day or drawdown
   would exceed what you can tolerate.
5. Keep the freshness limits short enough that decisions use recent account
   and signal state; they are time limits, not investment percentages.

There is no universally correct percentage. Risk tolerance depends on goals,
time horizon, finances, and willingness to take losses. Read the
[SEC's risk-tolerance guide](https://www.investor.gov/introduction-investing/investing-basics/save-and-invest/gauge-your-risk-tolerance)
and [asset-allocation guide](https://www.investor.gov/introduction-investing/getting-started/asset-allocation).
For stop-order behavior, read [FINRA's stop-order notice](https://www.finra.org/sites/default/files/notice_other_file_ref/Regulatory-Notice-16-19.pdf).

## Where to put the decision

Open the existing `config/risk_limits.json` in the repository. It has empty
`null` values for the limits. Replace them with your chosen numbers, leave `approved_for_paper` as
`false` while undecided, and set it to `true` only after you have reviewed
every field. The optional sector and volatility fields may stay `null` if you
choose not to use those gates. Commit that reviewed JSON file so the Raspberry Pi gets the same
limits when it pulls the repository. It contains no API credentials. This is
the machine-readable policy. A Markdown note can explain your reasoning, but
editing Python source is unnecessary.

Phase 12 loads the approved JSON, reconciles a complete portfolio, checks
the persistent kill switch, and rerun the risk gate immediately before any
paper order submission. The kill switch defaults to denied until an operator
explicitly resets it after review. It stops new orders; it does not liquidate
positions. The order manager is present but disabled by default; no command or
scheduler submits orders. Focused order tests pass; startup recovery and an
exit/stop workflow still need to be completed before automated paper orders.

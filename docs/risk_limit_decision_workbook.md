# Workbook: choose your paper-trading risk limits

Use this after **Phase 10 — Risk Management (§22)** and **Sections 23–24 —
Position Sizing and Kill Switch**, and before **Phase 12 — Order Manager (§26)**
is allowed to submit paper orders. Phase 12 code and tests can be written
while this worksheet is unfinished. The existing [short guide](risk_limits.md)
defines every field; this workbook helps you make and record the decision.

## 1. Start with the account and the purpose

Choose the paper-account equity you want to use as the reference amount. The
policy limits are fractions of **that account's equity**, not fractions of
all your savings. If you later change the paper-account size significantly,
revisit the dollar effects of every limit.

Fill in for yourself:

```text
Paper-account equity to plan around: $________
Purpose of the paper trial (software reliability, strategy research, both): ________
Maximum paper-account loss that would make me pause and investigate: $________
```

This is a personal choice. The SEC explains that risk tolerance depends on
your goals, time horizon, finances, and willingness to take losses:
[Gauge Your Risk Tolerance](https://www.investor.gov/introduction-investing/investing-basics/save-and-invest/gauge-your-risk-tolerance).
No official source prescribes this bot's percentages.

## 2. Separate the kinds of limits

These percentages are **independent ceilings**; they are not slices that add
to 100%.

| Limit in `config/risk_limits.json` | Question to answer | Convert your answer |
| --- | --- | --- |
| `max_portfolio_exposure` | What maximum dollar value should all open holdings represent? | Total holding value ÷ equity |
| `max_single_position` | What maximum dollar value should one stock represent? | One-stock value ÷ equity |
| `max_risk_per_trade` | What *planned* dollar loss to a proposed stop can one new trade use? | Planned loss budget ÷ equity |
| `max_daily_loss` | At what equity drop from the day's baseline should new orders stop? | Daily stop dollars ÷ baseline equity |
| `max_drawdown` | At what equity drop from the recorded peak should new orders stop? | Drawdown dollars ÷ peak equity |
| `max_positions` | How many simultaneous long positions can you review and monitor? | Whole number, not a percentage |
| `max_snapshot_age_seconds` | How old may broker account state be at an order decision? | Seconds, not a percentage |
| `max_signal_age_seconds` | How old may the strategy signal be? | Seconds, not a percentage |

The plan's **provisional examples** are 70% total exposure, 10% for one
position, 1% planned stop risk per trade, 3% daily loss, 10% drawdown, seven
positions, and 300 seconds for each freshness limit. They are examples for
testing the code, not a recommended policy for you.

At $10,000 equity, those examples mean $7,000 maximum gross holdings, $1,000
maximum value in one new stock, $100 planned stop-risk budget for one trade,
a $300 daily stop, and a $1,000 drawdown stop from a $10,000 peak. The daily
and drawdown limits **stop new orders**; the kill switch does not automatically
close positions or guarantee a maximum loss.

## 3. Work through one trade

Suppose a proposed BUY has a conservative estimated entry price of $100 and
a proposed stop price of $90. The stop distance is $10 per share. A $100
planned stop-risk budget suggests `floor($100 ÷ $10) = 10` whole shares.

The bot then takes the smallest whole-share count allowed by:

```text
planned risk ÷ stop distance
single-position dollar ceiling ÷ estimated entry price
remaining gross-exposure room ÷ estimated entry price
available cash ÷ estimated entry price
optional remaining sector-exposure room ÷ estimated entry price
```

It skips the trade if even one share cannot pass the risk gate. A stop price
is **not** a guaranteed exit price. A price gap or volatile market can make
the actual loss larger than the planned stop-risk amount; see
[FINRA's stop-order notice](https://www.finra.org/sites/default/files/2021-03/Regulatory-Notice-21-12.pdf).

## 4. Stress-check the combination

Before choosing numbers, write down answers to these questions:

- If several holdings fall together, could their combined loss exceed your
  daily stop before the bot has time to react? A per-trade cap does not control
  correlation between stocks. Diversification can reduce some concentration
  risk; see the [SEC asset-allocation and diversification guide](https://www.investor.gov/introduction-investing/getting-started/asset-allocation).
- Would a loss at your daily stop cause you to pause trading and investigate,
  or would you prefer to pause earlier?
- Would a drawdown at your chosen ceiling be acceptable to observe over a
  longer paper trial, including a difficult market regime?
- Does the single-position ceiling still make sense if the bot fills several
  orders quickly? Are your chosen symbols concentrated in one industry?
- Do the strategy's out-of-sample results and pessimistic cost scenarios
  support trying paper trading at all? The current AAPL study is a narrow,
  cost-sensitive example; it does not establish a reliable edge.
- If account data or a signal is five minutes old, is it still suitable for
  your intended timeframe? The age fields are operational safety limits.

Alpaca notes that paper trading does not model every live-market effect,
including market impact and order queue position. Treat the paper trial as
an engineering and research check, not as a guarantee of live performance:
[Alpaca paper-trading documentation](https://docs.alpaca.markets/us/v1.4.2/docs/paper-trading).

## 5. Optional limits

`max_sector_exposure` and `max_annualized_volatility` are `null` in the
template. Leave them `null` unless reliable sector classifications and
volatility estimates are available. Turning one on makes the risk gate require
that data; it does not silently guess a value.

The kill switch also has a separate API-failure threshold, currently three
consecutive failures by default. That is a count, not a loss percentage. The
Phase 12 workflow must call the kill switch for API failures, invalid account
state, and other safety events, then check its status before each order.

## 6. Record the decision in the repository

On your Windows development computer:

```powershell
Copy-Item config/risk_limits.example.json config/risk_limits.json
```

Open `config/risk_limits.json` in VS Code. Enter fractions such as `0.02` for
2%, not `2`. Keep `approved_for_paper` as `false` while deciding. When you
have reviewed every field and intentionally approve the paper policy, change
it to `true`. The loader rejects an absent, unapproved, or invalid file.

Commit the reviewed JSON so the Raspberry Pi receives the **same policy**
when you pull the repository. API credentials belong only in each machine's
separate `.env`; never add them to this JSON. If you prefer, tell me your
numbers in plain language and I can create the JSON for your review.

This workbook is for reasoning; `config/risk_limits.json` is the actual
machine-readable policy. Editing Python source is unnecessary. Creating the
JSON does not submit orders. Phase 12 still needs an explicitly enabled paper
workflow, fresh reconciled account state, risk checks, and a healthy kill
switch before any submission.

## Your decision record (optional notes)

```text
Decision date: __________
Paper-account equity used for calculations: $__________
Maximum planned loss to a stop per new trade: $__________  => fraction ______
Maximum daily equity drop: $__________                      => fraction ______
Maximum drawdown from peak: $__________                     => fraction ______
Maximum value in one stock: $__________                     => fraction ______
Maximum gross value of all holdings: $__________            => fraction ______
Maximum simultaneous positions: ______
Oldest acceptable account snapshot: ______ seconds
Oldest acceptable strategy signal: ______ seconds
Reasoning / circumstances that would make me revise these: __________
```

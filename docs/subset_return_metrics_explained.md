# Understanding the return, cash and drawdown numbers

## Is +6.29% close to the 6% target?

The two numbers cover different lengths of time:

- **+6.29% total over 2017-2021:** simulated $10,000 became about $10,629.
- **+1.23% annualized:** the constant compounded yearly rate that gives the
  same five-year total. Actual years can have different gains and losses.
- **Your 6% annual target:** compounding at 6% for five years would turn
  $10,000 into about $13,382, a **33.82% total gain**.

The 76-stock result improved on the matched two-stock control's +4.40% total
by about 1.89 percentage points, or $189 on the simulated starting account.
It also increased closing drawdown from 0.69% to 10.02%. More trades and more
capital use do not by themselves make the result fit your investment goal.
This comparison uses only the completed 2017-2021 base-cost/base-availability
cases. Other periods and cost scenarios must be reported separately.

## What does average cash remaining mean?

At each daily close we divide spendable cash by the account's marked total
value, then average those daily fractions over the evaluation period.
**80.63% average cash** means that, on average, most account value was still
available as uninvested cash. On an illustrative $10,000 account, 80.63%
would be $8,063; the actual account value changes through time.

The remaining roughly 19.37% includes positions and unpaid rights. An unpaid
dividend or undelivered share can have modeled value but cannot fund a purchase.
Cash earns zero in this model. The 70% exposure cap is an entry ceiling; it does
not instruct the strategy to invest 70% at all times. Signals, sizing and risk
halts can keep investment much lower. This completed broader case stopped new
entries after reaching its frozen drawdown halt in July 2018, which contributes
to its low average utilization across the full five-year period.

## What is maximum closing drawdown?

At each daily close, compare total account value with its highest earlier daily
closing value. The largest percentage fall from such a peak is the maximum
closing drawdown. It includes modeled open-position gains/losses and rights,
not just the cash balance or losses on completed trades.

For example, a decline from a $10,000 peak to $8,998 is a **10.02% drawdown**.
If the peak were $12,000, a 10.02% drawdown would be about $1,202. It is a loss
relative to the previous peak, so it is not necessarily the loss relative to
the original deposit. An account can end with a positive total return while
having suffered a large temporary drawdown along the way.

In the actual completed 76-stock base case, the relevant peak was about
**$11,702 on January 26, 2018**, followed by about **$10,530 on July 30, 2018**.
That is a roughly **$1,172 decline from the peak**, even though the account
remained above its initial simulated $10,000.

Its daily-marked yearly returns were approximately +12.07% in 2017, -5.16% in
2018, then 0% in each of 2019, 2020 and 2021. The permanent entry halt prevented
new trades during those later years. These yearly figures precede the separate
final hypothetical exit estimate; the reported full-window +6.29% includes it.
We keep all five years in the evaluation; the profitable first year alone does
not establish a sustained 6% annual return. Changing halt/restart rules would
be a separate experiment after this frozen comparison is reported.

Daily closing measurements can miss larger falls during a trading day.
Separate conservative daily-OHLC bounds are retained in the full reports;
they are not observed intraday account paths. The research strategy's existing
10% halt is separate from your **5% drawdown acceptance limit**. This case
failed your limit; the halt cannot guarantee an exact maximum loss.

All money figures here are simulated accounting values. No money was invested,
charged or paid out by these experiments.

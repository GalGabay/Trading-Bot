# The five daily strategies, explained

These are the five fixed arms evaluated in [Study C-R2](study_c_daily_improvement_results.md).
One bar means one market session. Indicator numbers refer to sessions, not
calendar days. Every discretionary decision uses a completed close and can
fill no earlier than the following session's open. Positions have no fixed
expiry: the holding period follows the exit rules.

## First, the indicators

- **EMA20 / EMA50 / EMA200:** smoothed averages of recent closing prices,
  giving more weight to recent sessions. Comparing them describes shorter
  and longer trends. EMA200 represents roughly ten trading months.
- **RSI14:** a 0-100 momentum measure. These rules use 50 as a positive
  momentum threshold. The original rule also rejects values above 70.
- **Volume ratio:** today's volume divided by its 20-session average.
  A value above one means above-average volume in that particular feed.
- **ATR14:** an estimate of recent daily price movement, expressed in dollars
  per share. If ATR is $2, a three-ATR stop is $6 below its reference price.
  It describes distance, not a guarantee that the stop will fill there.

## 1. Original trend rule

BUY only when close > EMA200, EMA20 > EMA50, RSI is between 50 and 70
inclusive, and the volume ratio is greater than one. The idea is to join an
established upward trend with positive momentum and volume confirmation.
The upper RSI limit avoids the strongest momentum readings; whether that
helps is an empirical question.

SELL after a close below EMA50 or EMA20 below EMA50. The simulator fills
that signal at the next open. This arm has no protective price stop and no
reentry pause; its provisional portfolio loss limits can still block entries.

## 2. Original rule without volume

All original price, RSI, and exit conditions remain. Omit only the volume
requirement. This isolates whether volume confirmation helps, especially
because IEX and consolidated SIP volume differ. It is a diagnostic arm;
removing the filter did not improve the pessimistic two-year result.

## 3. Market-filtered trend

BUY only when SPY close > its EMA200, the symbol close > EMA200,
EMA50 > EMA200, EMA20 > EMA50, and RSI >= 50. There is no upper RSI ceiling
or volume requirement. Compared with the original, the medium/long trend
must also agree and the broad market must support entry.

SELL after close < EMA50, EMA20 < EMA50, or SPY close <= EMA200. A fixed
protective stop begins at the signal close minus three ATR14 values. Wait
ten complete market sessions after any exit before another entry fill.
These filters and stops did not improve the tested development results.

## 4. Breakout with a fixed stop

Instead of repeatedly buying whenever several trend indicators agree, wait
for a specific price event: a completed close above the highest high of the
**preceding 55 sessions**. Also require the symbol close > EMA200 and SPY
close > its EMA200. There is no RSI or volume entry condition.

For example, if the previous 55 sessions' highest high was $100 and today's
close is $101, the stock qualifies. Today's own high is excluded from that
historical comparison. The proposed trade can fill at the next open, whose
price may be different from $101. Portfolio limits can still reduce or reject
the trade.

There are four possible exits:

1. Close below the lowest low of the **preceding 20 sessions**.
2. Close below the stock's EMA200.
3. SPY close at or below its EMA200.
4. A touch or opening gap through the initial protective stop, set three ATR
   values below the entry signal's close.

The first three produce a next-open sell. The stop uses a daily-OHLC model
and can exit within the session. If entry was near $100, price later rose to
$130, and a close then broke a prior 20-session low at $125, the channel exit
can sell a winning position. It is not necessary to wait for a loss. The
next open and costs determine the actual modeled proceeds.

The initial stop stays fixed. It does not rise automatically as the stock
rises. After an exit, wait ten full sessions before reentry. The **55/20**
notation means a 55-session entry channel and 20-session exit channel; it
does not mean holding a trade for 20 or 55 days.

## 5. Breakout with a trailing stop

Use exactly the same breakout entries, channel/EMA/market exits, ten-session
pause, and initial three-ATR stop as strategy 4. Only the stop update differs:

`next stop = max(existing stop, completed close - 4 * completed ATR14)`

The new level becomes active next session. It can rise but never fall. For
example, an entry signal close of $100 with ATR $2 gives an initial stop at
$94 in both strategies. Later, a completed close of $110 with ATR still $2
raises strategy 5's stop to $102; strategy 4 keeps its stop at $94. A later
proposal below $102 leaves the trailing stop at $102. Thus strategy 5 can
exit sooner when a rising position gives back some gains. Wider distance and
updated ATR mean it will not lock in every profit.

When price opens below an active stop, the simulator uses that lower open
with adverse costs. Broker fills can differ from this approximation. The
four-ATR trailing variant was almost tied with the fixed-stop variant in
this sample; it did not demonstrate a clear improvement.

## What the next study changes

The [allocation and halt/restart protocol](study_c_allocation_protocol.md)
keeps **strategy 4's 55/20 rules and fixed three-ATR stop** unchanged. It tests
how much capital goes into each trade and when entries can resume after a
daily loss. Those are portfolio-policy questions, separate from predicting
an entry or exit. Personal paper limits and paper activation remain owner
decisions.

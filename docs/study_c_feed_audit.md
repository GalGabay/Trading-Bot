# Study C historical feed and JNJ data audit

**Run date:** 2026-10-23. **Scope:** Read-only Alpaca `1Day`, `all`-adjusted
US stock bars for Study C's fixed 12 symbols, requested from 2019-01-01
inclusive to 2024-01-01 exclusive. No orders were placed. The reserved 2024
and 2025 data were not requested. The full machine-readable result is the
ignored local file `data/reports/study_c_feed_audit_final.json`.

Alpaca's [market data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
describes SIP as consolidated US exchange data and IEX as one exchange. The
existing SIP CSVs were loaded only after checking their manifests and SHA-256
hashes. Fresh IEX responses went through the same timestamp, OHLCV, market
calendar, and warning checks as the downloader. The audit never filled a
missing bar or silently dropped a symbol.

## Coverage finding

The local Alpaca IEX response begins on **2020-07-27** for every symbol.
Thus **394 scheduled sessions from the requested 2019 start are absent** for
all 12. AAPL, MSFT, SPY, QQQ, and IWM have 864 bars and no further missing
sessions. JPM, JNJ, XOM, WMT, CAT, PG, and NEE have 861 bars and lack the
same three additional sessions: **2021-04-19, 2021-10-25, and 2022-03-08**.
Short, direct requests for JNJ on those dates returned no usable IEX bar
(the installed SDK raised an error while parsing an empty bar); AAPL returned
one bar on each. This confirms an unavailable JNJ response on those dates,
but does not distinguish no IEX trades from a provider data omission. We
cannot claim the original uninterrupted 2019–2023 IEX dataset exists for
this account/API response. The strict downloader correctly rejected the
full-range JNJ download rather than creating the 397 absent candles.

On the **overlapping 2022–2023 dates**, the median absolute SIP/IEX close
difference by symbol was between **0.011% and 0.020%**; the 95th percentile
was between **0.042% and 0.096%**. Median IEX volume was only **1.3%–3.7%**
of SIP volume, depending on symbol. That volume difference is expected in
direction because IEX is one exchange, but it matters to the strategy's
20-day volume-ratio entry rule. These close statistics use available paired
dates only and are not a substitute for the missing candles.

## JNJ warning check

The SIP validator marked four JNJ dates because their daily volumes exceed
10 times JNJ's positive-volume median for the 2019–2023 dataset. IEX also
shows elevated volume on those dates compared with its own available-period
median. `all`-adjusted closes differ by at most **0.06%** between feeds.

| Date in 2023 | SIP volume | SIP / median | IEX volume | IEX / median | SIP close | IEX close |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Aug 15 | 88,924,923 | 11.75x | 1,488,225 | 6.77x | 157.66 | 157.62 |
| Aug 16 | 85,894,288 | 11.35x | 1,780,617 | 8.10x | 157.16 | 157.19 |
| Aug 21 | 151,319,484 | 19.99x | 2,395,745 | 10.90x | 152.57 | 152.66 |
| Aug 23 | 119,011,433 | 15.72x | 867,904 | 3.95x | 150.00 | 150.03 |

Johnson & Johnson [announced the exchange offer's pricing window as August
14–16](https://www.jnj.com/media-center/press-releases/johnson-johnson-launches-exchange-offer-for-separation-of-kenvue-inc)
and [reported the final Kenvue exchange results on August
23](https://www.jnj.com/media-center/press-releases/johnson-johnson-announces-final-results-of-exchange-offer-and-finalizes-separation-of-kenvue-inc).
The dates and second feed make unusual market activity a **plausible**
explanation. Neither source independently verifies Alpaca's exact consolidated
volume or proves the offer caused each bar's volume. Keep the validator
warning and the original bars; no JNJ price or volume was changed.

## Controlled comparison where sessions align

The last shared IEX gap is 2022-03-08. From **2022-03-09 through 2023-12-29**,
all 12 symbols have the same 456 session dates in both feeds. The first 206
sessions warm up indicators; the following 250 sessions form a **2023-only**
research comparison. Both runs start with a new $100,000 simulated account
on 2023-01-01, use the unchanged rule and provisional research limits, and
apply the same cost scenarios. On the 3,000 matched symbol-days in 2023,
the feeds disagree on **228 flat-position BUY candidate days** and **4
holding-position SELL candidate days**. These are predicate comparisons,
not order counts; portfolio holdings and limits determine actual fills.

| Feed | Cost case | 2023 return | Max drawdown | Completed trades |
| --- | --- | ---: | ---: | ---: |
| SIP | Optimistic | +5.350% | -6.123% | 45 |
| SIP | Base | +4.787% | -6.307% | 45 |
| SIP | Pessimistic | +2.777% | -6.970% | 45 |
| IEX | Optimistic | +6.514% | -6.028% | 47 |
| IEX | Base | +5.911% | -6.248% | 47 |
| IEX | Pessimistic | +3.803% | -6.973% | 47 |

The **full 2022–2023 portfolio replay remains unavailable** on IEX because
seven symbols lack the three intervening sessions. The 2023-only result
resets holdings and equity in January; it cannot replace Study C's continuous
two-year SIP result, which carried positions from 2022 into 2023. The replay
uses each feed's historical open as its own fill-price proxy, so its return
difference combines signal and price-proxy effects. Historical IEX bars do
not establish the actual prices a paper order would receive. A larger IEX
return in this limited comparison is not a reason to select a feed by its
backtest score. Feed selection for paper trading must follow the account's
actual entitlement and a separately reviewed execution design.

## Reproduce and next decision

From the repository root, with the existing Study C SIP datasets and paper
data credentials configured:

```powershell
.venv\Scripts\python.exe -m backtesting.feed_audit --output data/reports/study_c_feed_audit_new.json
```

The command makes historical-data and market-calendar requests only. Choose
a new report path on each run. For the Raspberry Pi, use its environment's
`python -m backtesting.feed_audit ...` equivalent after obtaining the SIP
datasets locally; ignored data files are not carried by Git. Provider data
can be revised between runs, so compare response hashes and dates before
interpreting changes.

**Decision:** The audit supports retaining JNJ's four volume warnings as
plausible event-period observations, with exact SIP volume unverified. It
shows material feed sensitivity in entry candidates. It does **not** clear
Study C for paper trading. The next research work is to decide whether to
develop a better daily rule on the already opened development years, with a
complete feed-aligned evaluation design and risk/exit policy. Preserve
2024–2025 as the final holdout until that candidate and its tests are frozen.

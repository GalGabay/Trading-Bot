"""Read-only Study C SIP/IEX coverage and signal-sensitivity audit.

Run with ``python -m backtesting.feed_audit --output data/reports/study_c_feed_audit.json``.
The command fetches historical IEX bars and reads the existing Study C SIP
files. It never submits orders or fills absent bars. A matched portfolio replay
is produced only when every symbol has aligned, complete daily sessions from
the common IEX start through 2023.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import pandas as pd
from alpaca.data.enums import Adjustment, DataFeed

from app.ai.features import build_features
from app.broker.alpaca_client import AlpacaClient
from app.data.market_data import MarketDataService
from app.strategy.strategy_v1 import TrendFollowingV1, TrendFollowingV1Config
from backtesting.portfolio_engine import PortfolioBacktestEngine, ResearchPortfolioLimits, summarize_portfolio
from backtesting.research import COST_SCENARIOS, _utc_date, load_dataset, TIMEFRAMES

SYMBOLS = ("AAPL", "MSFT", "JPM", "JNJ", "XOM", "WMT", "CAT", "PG", "NEE", "SPY", "QQQ", "IWM")
START, END = "2019-01-01", "2024-01-01"
TRADE_START, TRADE_END = "2022-01-01", "2024-01-01"
JNJ_DATES = ("2023-08-15", "2023-08-16", "2023-08-21", "2023-08-23")


def _buy_and_sell_conditions(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the unchanged strategy predicates to each completed bar.

    BUY means an entry candidate while flat, not an executable order. SELL
    means an exit candidate while holding. Portfolio state is replayed later.
    """
    config = TrendFollowingV1Config()
    features = build_features(frame).set_index("timestamp")
    buy = (
        (features["close"] > features["ema_200"])
        & (features["ema_20"] > features["ema_50"])
        & features["rsi_14"].between(config.rsi_minimum, config.rsi_maximum)
        & (features["volume_ratio_20"] > config.minimum_volume_ratio)
    )
    sell = (features["close"] < features["ema_50"]) | (features["ema_20"] < features["ema_50"])
    return pd.DataFrame({"buy_candidate": buy.fillna(False), "sell_candidate": sell.fillna(False)})


def _quantile(values: pd.Series, q: float) -> float | None:
    return None if values.empty else round(float(values.quantile(q)), 6)


def _jnj_rows(sip: pd.DataFrame, iex: pd.DataFrame) -> list[dict[str, object]]:
    joined = sip.set_index("timestamp").join(iex.set_index("timestamp"), lsuffix="_sip", rsuffix="_iex")
    joined["date"] = joined.index.strftime("%Y-%m-%d")
    median_sip = float(sip.loc[sip["volume"] > 0, "volume"].median())
    median_iex = float(iex.loc[iex["volume"] > 0, "volume"].median())
    rows = []
    for day in JNJ_DATES:
        match = joined.loc[joined["date"] == day]
        if match.empty:
            rows.append({"date": day, "present_in_sip": False, "present_in_iex": False})
            continue
        row = match.iloc[0]
        rows.append({
            "date": day, "sip_volume": int(row["volume_sip"]),
            "iex_volume": None if pd.isna(row["volume_iex"]) else int(row["volume_iex"]),
            "sip_volume_multiple_of_full_period_median": round(float(row["volume_sip"]) / median_sip, 2),
            "iex_volume_multiple_of_available_period_median": (
                None if pd.isna(row["volume_iex"]) else round(float(row["volume_iex"]) / median_iex, 2)
            ),
            "sip_close": round(float(row["close_sip"]), 4),
            "iex_close": None if pd.isna(row["close_iex"]) else round(float(row["close_iex"]), 4),
        })
    return rows


def run_audit() -> dict[str, object]:
    client = AlpacaClient()
    market_data = MarketDataService(client)
    sip_bars: dict[str, pd.DataFrame] = {}
    iex_bars: dict[str, pd.DataFrame] = {}
    symbols: dict[str, dict[str, object]] = {}
    for symbol in SYMBOLS:
        path = Path(f"data/historical/{symbol}_1Day_2019_2023_study_c.csv")
        sip, manifest = load_dataset(path)
        if (manifest["feed"], manifest["adjustment"], manifest["start_utc"], manifest["end_exclusive_utc"]) != (
            "sip", "all", START, END
        ):
            raise ValueError(f"{symbol}: unexpected SIP study manifest")
        iex, validation = market_data.get_historical_candles(
            symbol, start=_utc_date(START), end=_utc_date(END),
            timeframe=TIMEFRAMES["1Day"], feed=DataFeed.IEX, adjustment=Adjustment.ALL,
        )
        sip_dates, iex_dates = set(sip["timestamp"]), set(iex["timestamp"])
        absent = sorted(sip_dates - iex_dates)
        iex_first = iex["timestamp"].min()
        absent_after_start = [day for day in absent if day >= iex_first]
        overlap = sip.set_index("timestamp").join(
            iex.set_index("timestamp"), how="inner", lsuffix="_sip", rsuffix="_iex"
        )
        scored = overlap.loc[(overlap.index >= _utc_date(TRADE_START)) & (overlap.index < _utc_date(TRADE_END))]
        close_delta = ((scored["close_iex"] / scored["close_sip"] - 1).abs() * 100)
        sip_volume = scored["volume_sip"].where(scored["volume_sip"] > 0)
        iex_share = (scored["volume_iex"] / sip_volume * 100).dropna()
        symbols[symbol] = {
            "sip_sha256": manifest["sha256"],
            "iex_response_sha256": hashlib.sha256(
                iex.to_csv(index=False, date_format="%Y-%m-%dT%H:%M:%SZ").encode("utf-8")
            ).hexdigest(),
            "sip_rows": len(sip), "iex_rows": len(iex),
            "iex_first": iex_first.isoformat(), "iex_last": iex["timestamp"].max().isoformat(),
            "scheduled_sessions_absent_in_iex": validation.time_gaps,
            "sip_sessions_absent_in_iex_before_first_bar": len(absent) - len(absent_after_start),
            "sip_sessions_absent_in_iex_after_first_bar": len(absent_after_start),
            "first_absent_after_start": [day.isoformat() for day in absent_after_start[:10]],
            "iex_warnings": [asdict(issue) for issue in validation.warnings],
            "scored_overlap_sessions": len(scored),
            "close_abs_percent_difference_median": _quantile(close_delta, 0.5),
            "close_abs_percent_difference_p95": _quantile(close_delta, 0.95),
            "iex_volume_as_percent_of_sip_median": _quantile(iex_share, 0.5),
            "iex_volume_as_percent_of_sip_p95": _quantile(iex_share, 0.95),
        }
        sip_bars[symbol], iex_bars[symbol] = sip, iex
        print(f"{symbol}: IEX {len(iex)} bars; {validation.time_gaps} absent sessions; "
              f"{len(absent_after_start)} absent after first bar", flush=True)

    common_start = max(frame["timestamp"].min() for frame in iex_bars.values())
    report: dict[str, object] = {
        "method": "read_only_study_c_sip_iex_feed_audit", "requested_start": START,
        "requested_end_exclusive": END, "scored_start": TRADE_START,
        "scored_end_exclusive": TRADE_END, "adjustment": "all", "timeframe": "1Day",
        "symbols": symbols, "common_iex_start": common_start.isoformat(),
        "jnj_warning_dates": _jnj_rows(sip_bars["JNJ"], iex_bars["JNJ"]),
        "matched_portfolio_replay": None,
    }
    sip_trim = {symbol: frame.loc[frame["timestamp"] >= common_start].reset_index(drop=True)
                for symbol, frame in sip_bars.items()}
    iex_trim = {symbol: frame.loc[frame["timestamp"] >= common_start].reset_index(drop=True)
                for symbol, frame in iex_bars.items()}
    common_dates = sip_trim[SYMBOLS[0]]["timestamp"]
    can_replay = common_start < _utc_date(TRADE_START) and all(
        sip_trim[symbol]["timestamp"].equals(common_dates)
        and iex_trim[symbol]["timestamp"].equals(common_dates)
        for symbol in SYMBOLS
    )
    replay_start = TRADE_START
    if not can_replay:
        # The full 2022-23 comparison is impossible with gaps. An explicitly
        # labeled 2023-only check can still be made if every symbol has a
        # shared, uninterrupted 200-session warmup after the final gap.
        all_absent = sorted(set(sip_trim[SYMBOLS[0]]["timestamp"]).difference(iex_trim[SYMBOLS[0]]["timestamp"]))
        for symbol in SYMBOLS[1:]:
            all_absent.extend(set(sip_trim[symbol]["timestamp"]).difference(iex_trim[symbol]["timestamp"]))
        uninterrupted_start = max(all_absent) if all_absent else common_start
        sip_trim = {symbol: frame.loc[frame["timestamp"] > uninterrupted_start].reset_index(drop=True)
                    for symbol, frame in sip_bars.items()}
        iex_trim = {symbol: frame.loc[frame["timestamp"] > uninterrupted_start].reset_index(drop=True)
                    for symbol, frame in iex_bars.items()}
        common_dates = sip_trim[SYMBOLS[0]]["timestamp"]
        replay_start = "2023-01-01"
        can_replay = (
            int((common_dates < _utc_date(replay_start)).sum()) >= 200
            and all(
                sip_trim[symbol]["timestamp"].equals(common_dates)
                and iex_trim[symbol]["timestamp"].equals(common_dates)
                for symbol in SYMBOLS
            )
        )
        if can_replay:
            report["full_2022_2023_replay_status"] = "Unavailable: seven symbols lack three IEX sessions after July 2020, including 2022-03-08."
    if can_replay:
        for symbol in SYMBOLS:
            sip_flags = _buy_and_sell_conditions(sip_trim[symbol])
            iex_flags = _buy_and_sell_conditions(iex_trim[symbol])
            paired = sip_flags.join(iex_flags, lsuffix="_sip", rsuffix="_iex")
            paired = paired.loc[(paired.index >= _utc_date(replay_start)) & (paired.index < _utc_date(TRADE_END))]
            symbols[symbol]["matched_replay_signal_comparison"] = {
                "sessions": len(paired),
                "buy_candidate_days_sip": int(paired["buy_candidate_sip"].sum()),
                "buy_candidate_days_iex": int(paired["buy_candidate_iex"].sum()),
                "buy_candidate_disagreements": int((paired["buy_candidate_sip"] != paired["buy_candidate_iex"]).sum()),
                "sell_candidate_disagreements": int((paired["sell_candidate_sip"] != paired["sell_candidate_iex"]).sum()),
            }
        replay = {}
        for feed, datasets in (("sip", sip_trim), ("iex", iex_trim)):
            replay[feed] = {}
            for name, scenario in COST_SCENARIOS.items():
                costs = replace(scenario, periods_per_year=252)
                result = PortfolioBacktestEngine(
                    strategy=TrendFollowingV1(),
                    costs=costs, limits=ResearchPortfolioLimits(),
                ).run(datasets, trade_start=_utc_date(replay_start), trade_end=_utc_date(TRADE_END))
                replay[feed][name] = summarize_portfolio(result)
        report["matched_portfolio_replay"] = replay
        report["replay_trade_start"] = replay_start
        report["replay_warmup_start"] = common_dates.iloc[0].isoformat()
        report["replay_warmup_sessions"] = int((common_dates < _utc_date(replay_start)).sum())
        report["replay_status"] = (
            "Complete matched daily sessions from the stated warmup start; both feeds replayed with identical "
            "dates and settings. A 2023-only replay resets cash and holdings at 2023 start and is not the "
            "original continuous 2022-23 Study C result."
        )
    else:
        report["replay_status"] = (
            "No portfolio replay: IEX and SIP sessions do not align completely from the common IEX start, "
            "or fewer than one warmup period is available. Missing bars were not filled."
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Audit report already exists; choose a new output path")
    report = run_audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Report: {args.output}\nReplay: {report['replay_status']}")


if __name__ == "__main__":
    main()

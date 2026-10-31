"""Completed-session observations and hypothetical allocations, never orders.

No virtual fills, positions, cash credits or P&L are created. Each report uses
an explicitly supplied reference book (flat by default) and immutable inputs.
"""

import argparse
from datetime import datetime, timezone
from math import floor, isfinite
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.ai.features import build_features
from app.data.market_calendar import TradingSession
from app.data.market_data import CANONICAL_CANDLE_COLUMNS, ValidationConfig, validate_candles
from app.shadow.config import ROOT, canonical, digest, implementation, load_config, read_json, utc
from app.shadow.store import ObservationStore, write_once
from app.strategy.base import SignalAction
from backtesting.daily_strategies import DailyResearchStrategy, DailyRuleConfig
from backtesting.holding_policy import HoldingEntry, HoldingPolicy
from backtesting.research_policy import AllocationPolicy


class SavedCalendar:
    def __init__(self, sessions):
        self.rows = sessions

    def sessions(self, start, end):
        return [s for s in self.rows if start <= s.opens_at.date() <= end]


def sessions_from(rows):
    sessions = []
    for row in rows:
        day = pd.Timestamp(row["date"])
        if day.tzinfo is not None or day.time().isoformat() != "00:00:00":
            raise ValueError("Calendar dates must be date-only values")
        values = []
        for key in ("open", "close"):
            value = pd.Timestamp(f"{row['date']}T{row[key]}")
            if value.tzinfo is not None:
                raise ValueError("Calendar clock fields must be local New York times")
            values.append(value.tz_localize("America/New_York").tz_convert("UTC"))
        sessions.append(TradingSession(*values))
    opens = [s.opens_at for s in sessions]
    if not opens or opens != sorted(set(opens)):
        raise ValueError("Calendar sessions must be nonempty, unique and ordered")
    return sessions


def daily_stamp(session):
    return session.opens_at.tz_convert("America/New_York").normalize().tz_convert("UTC")


def checked_asset(asset, name):
    if (not isinstance(asset, dict) or asset.get("symbol") != name or
            asset.get("class") != "us_equity" or asset.get("status") != "active" or
            asset.get("tradable") is not True or not isinstance(asset.get("id"), str) or not asset["id"]):
        raise ValueError("Current asset identity/status/tradability is unavailable")
    return asset["id"]


def prepare(bundle, name, sessions, completed, config):
    asset_id = checked_asset(bundle["assets"].get(name), name)
    bars = bundle["bars"].get(name)
    if not isinstance(bars, list) or not bars:
        raise ValueError("No observed daily bars")
    frame = pd.DataFrame([dict(timestamp=r["t"], symbol=name, open=r["o"], high=r["h"],
        low=r["l"], close=r["c"], volume=r["v"]) for r in bars], columns=CANONICAL_CANDLE_COLUMNS)
    # Validate *before* dropping the in-progress bar or old lookback rows.
    validate_candles(frame, config=ValidationConfig(timeframe=TimeFrame.Day),
        calendar=SavedCalendar(sessions), requested_start=utc(config.history_start + "T00:00:00Z"),
        requested_end=utc(bundle["observed_at"]))
    frame["timestamp"] = [utc(t) for t in frame["timestamp"]]
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column])
    frame = frame.sort_values("timestamp", ignore_index=True)
    expected = {daily_stamp(s) for s in completed[-252:]}
    complete_stamps = {daily_stamp(s) for s in completed}
    partial = int((~frame["timestamp"].isin(complete_stamps)).sum())
    used = frame.loc[frame["timestamp"].isin(expected)].reset_index(drop=True)
    missing = expected - set(used["timestamp"])
    if missing:
        raise ValueError(f"No observed bar in {len(missing)} required completed sessions; coverage unresolved, not filled")
    if len(used) < 200:
        raise ValueError(f"EMA200 warmup unavailable: {len(used)} complete sessions; need 200")
    if used.iloc[-1]["volume"] <= 0:
        raise ValueError("Latest completed bar has zero volume; actionable price freshness is unresolved")
    validation = validate_candles(used, config=ValidationConfig(timeframe=TimeFrame.Day))
    return build_features(used), dict(asset_id=asset_id, completed_bars=len(used),
        incomplete_bars_excluded=partial,
        warnings=[dict(code=w.code, message=w.message, rows=w.row_count) for w in validation.warnings])


def positive(value, name, *, zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or (value < 0 if zero else value <= 0):
        raise ValueError(f"Reference {name} must be finite and {'nonnegative' if zero else 'positive'}")
    return float(value)


def reference_book(reference, config, latest, frames, bundle, completed):
    if reference is None:
        return dict(cash=config.reference_cash, equity=config.reference_cash, positions={},
            peak_equity=config.reference_cash, day_start_equity=config.reference_cash, stock_value=0.0,
            source="Flat observation reference; no account lookup and no simulated fills")
    if set(reference) != {"as_of_session", "cash", "peak_equity", "day_start_equity", "positions"}:
        raise ValueError("Reference book requires session, cash, peak/day equity and positions")
    if reference["as_of_session"] != latest.opens_at.date().isoformat() or not isinstance(reference["positions"], list):
        raise ValueError("Reference book must explicitly describe the latest completed session")
    positions, stock = {}, 0.0
    for row in reference["positions"]:
        if set(row) != {"symbol", "asset_id", "quantity", "average_entry_price", "stop_price", "entry_session"}:
            raise ValueError("Reference position fields are incomplete or unsupported")
        name = row["symbol"]
        if name in positions or name not in config.symbols or name not in frames:
            raise ValueError("Reference position duplicated, outside watchlist or without valid current prices")
        if checked_asset(bundle["assets"].get(name), name) != row["asset_id"]:
            raise ValueError("Reference position identity differs from current asset identity")
        if type(row["quantity"]) is not int or row["quantity"] < 1:
            raise ValueError("Reference positions require positive whole shares")
        positive(row["average_entry_price"], "entry price")
        positive(row["stop_price"], "stop price")
        if row["stop_price"] >= row["average_entry_price"]:
            raise ValueError("Reference stop must match the supported fixed initial stop below entry")
        dates = [s.opens_at.date().isoformat() for s in completed]
        if row["entry_session"] not in dates:
            raise ValueError("Reference entry session is not in the available completed calendar")
        positions[name] = dict(row, entry_index=dates.index(row["entry_session"]))
        stock += row["quantity"] * float(frames[name].iloc[-1]["close"])
    cash = positive(reference["cash"], "cash", zero=True)
    equity = positive(cash + stock, "equity")
    peak = positive(reference["peak_equity"], "peak equity")
    if peak < equity:
        raise ValueError("Reference peak equity cannot be below current marked equity")
    return dict(cash=cash, equity=equity, positions=positions, stock_value=stock, peak_equity=peak,
        day_start_equity=positive(reference["day_start_equity"], "day-start equity"),
        source="User-supplied current-share-unit reference only; not reconciled broker state")


def observe(bundle, config, *, reference=None):
    if (bundle.get("schema_version") != 1 or bundle.get("feed") != "iex" or
            bundle.get("adjustment") != "split" or bundle.get("timeframe") != "1Day" or
            bundle.get("history_start") != config.history_start or bundle.get("symbols") != list(config.symbols)):
        raise ValueError("Saved bundle differs from the explicit IEX/daily/split-adjusted watchlist policy")
    observed = utc(bundle["observed_at"])
    if observed > utc(datetime.now(timezone.utc)) + pd.Timedelta(seconds=5):
        raise ValueError("Observation timestamp is in the future")
    sessions = sessions_from(bundle["calendar"])
    floor_date = pd.Timestamp(config.history_start).date()
    if any(s.opens_at.date() < floor_date for s in sessions):
        raise ValueError("Calendar includes sessions before the allowed shadow history start")
    completed = [s for s in sessions if s.closes_at + pd.Timedelta(minutes=config.close_settle_minutes) <= observed]
    if not completed:
        raise ValueError("No fully completed, settled session is available")
    latest = completed[-1]
    following = [s for s in sessions if s.opens_at > latest.closes_at]
    next_open = following[0].opens_at if following else None
    blockers = []
    if next_open is None or next_open - latest.closes_at > pd.Timedelta(days=14):
        blockers.append("next_session_calendar_unavailable")
    elif observed >= next_open:
        blockers.append("next_open_already_passed_wait_for_new_completed_session")
    frames, quality, rows = {}, {}, []
    if set(bundle["assets"]) != set((*config.symbols, "SPY")) or set(bundle["bars"]) != set(bundle["assets"]):
        raise ValueError("Bundle has missing or extra watchlist/context streams")
    for name in (*config.symbols, "SPY"):
        try:
            frames[name], quality[name] = prepare(bundle, name, sessions, completed, config)
        except (ValueError, KeyError, TypeError) as exc:
            quality[name] = dict(blocked=True, reason=f"{type(exc).__name__}: {exc}")
    market_on = None
    if "SPY" not in frames:
        blockers.append("market_context_unavailable")
    else:
        spy = frames["SPY"].iloc[-1]
        market_on = bool(float(spy["close"]) > float(spy["ema_200"]))
    book = None
    try:
        book = reference_book(reference, config, latest, frames, bundle, completed)
    except (ValueError, KeyError, TypeError) as exc:
        blockers.append(f"reference_book_unavailable: {exc}")
    if book is not None:
        # These frozen old research thresholds are observation diagnostics only.
        if book["equity"] <= book["day_start_equity"] * .97:
            blockers.append("reference_legacy_daily_loss_halt_3_percent")
        if book["equity"] <= book["peak_equity"] * .90:
            blockers.append("reference_legacy_drawdown_halt_10_percent")
        if len(book["positions"]) > config.max_positions:
            blockers.append("reference_position_count_above_cap")
        if book["stock_value"] > config.entry_ceiling * book["equity"]:
            blockers.append("reference_exposure_above_ceiling")
        for name, position in book["positions"].items():
            if position["quantity"] * float(frames[name].iloc[-1]["close"]) > config.position_cap * book["equity"]:
                blockers.append(f"reference_position_above_cap: {name}")
    strategy = DailyResearchStrategy(DailyRuleConfig("breakout", 55, 20),
        regime={daily_stamp(latest): market_on} if market_on is not None else {}) if market_on is not None else None
    for name in config.symbols:
        row = dict(symbol=name, signal="UNAVAILABLE", reason="", preview_quantity=0,
            preview_notional=0.0, blockers=[], quality=quality[name])
        if name not in frames or strategy is None or book is None:
            row["reason"] = quality[name].get("reason", "Market context or reference book unavailable")
            row["blockers"] = ["data_or_reference_unavailable"]
            rows.append(row)
            continue
        frame, position = frames[name], book["positions"].get(name)
        bar = frame.iloc[-1]
        result = strategy.generate_signal(frame, SimpleNamespace(quantity=position["quantity"] if position else 0))
        row.update(signal=result.action.value, reason=result.reason, signal_bar_timestamp=result.timestamp.isoformat(),
            reference_close=float(bar["close"]), atr14=float(bar["atr_14"]),
            annualized_volatility=float(bar["historical_volatility_20"]))
        if position is not None:
            review = HoldingPolicy("continuation").review(frame,
                HoldingEntry(position["entry_index"], position["quantity"], position["quantity"] * position["average_entry_price"]),
                len(completed) - 1, market_on=market_on, sale_multiplier=.0006, sale_commission=0)
            row["holding_review"] = review
            if row["reference_close"] <= position["stop_price"]:
                row.update(signal="SELL", reason="Reference stop breached at completed close; no exit executed")
            elif row["signal"] != "SELL" and review is not None and review["decision"] == "exit":
                row.update(signal="SELL", reason=review["reason"])
            if row["signal"] == "SELL":
                row.update(preview_exit_quantity=position["quantity"], exit_status="signal_only_no_sale_or_cash_credit")
        rows.append(row)
    planned, cash, slots = (book["stock_value"], book["cash"], len(book["positions"])) if book else (0, 0, 0)
    for row in sorted(rows, key=lambda r: r["symbol"]):
        if row["signal"] != "BUY":
            continue
        row["blockers"].extend(blockers)
        if book is None or row["blockers"]:
            continue
        price = row["reference_close"] * 1.0006  # Existing base-cost estimate; no quote/fill claim.
        stop = row["reference_close"] - 3 * row["atr14"]
        vol = row["annualized_volatility"]
        if not all(isfinite(v) for v in (price, stop, vol)) or stop <= 0 or vol <= 0:
            row["blockers"].append("invalid_stop_or_volatility")
            continue
        if slots >= config.max_positions:
            row["blockers"].append("position_slots_full")
            continue
        weight = AllocationPolicy(config.volatility_contribution).fraction(config.position_cap, vol)
        caps = dict(position_cap=config.position_cap * book["equity"] / price,
            volatility_sizing=weight * book["equity"] / price,
            stop_risk=config.planned_stop_risk * book["equity"] / (price - stop),
            target_room=(config.target_exposure * book["equity"] - planned) / price,
            ceiling_room=(config.entry_ceiling * book["equity"] - planned) / price, available_cash=cash / price)
        binding = min(caps, key=caps.get)
        quantity = max(0, floor(min(caps.values())))
        row.update(estimated_entry=price, proposed_stop=stop, binding_cap=binding,
            preview_quantity=quantity, preview_notional=quantity * price)
        if quantity == 0:
            row["blockers"].append(f"{binding}_below_one_whole_share")
        else:
            planned += row["preview_notional"]
            cash -= row["preview_notional"]
            slots += 1
    sources = implementation()
    from importlib.metadata import version
    environment = dict(python=sys.version.split()[0], pandas=pd.__version__,
        numpy=version("numpy"), alpaca_py=version("alpaca-py"))
    result = dict(schema_version=1, mode="shadow_observation_only", observed_at=observed.isoformat(),
        session=latest.opens_at.date().isoformat(), session_close=latest.closes_at.isoformat(),
        next_session_open=None if next_open is None else next_open.isoformat(), market_filter_on=market_on,
        id=digest(dict(bundle=digest(bundle), config=config.record(), reference=reference,
            implementation=sources, environment=environment)), environment=environment,
        config=config.record(), implementation=sources, bundle_sha256=digest(bundle),
        reference=book, global_blockers=blockers, market_context_quality=quality["SPY"], signals=rows,
        preview=dict(target=config.target_exposure, ceiling=config.entry_ceiling,
            current_stock_exposure=None if book is None else book["stock_value"] / book["equity"],
            planned_stock_exposure=None if book is None else planned / book["equity"],
            reference_cash_after_planned_buys=None if book is None else cash,
            target_shortfall=None if book is None else max(0, config.target_exposure - planned / book["equity"])),
        orders_submitted=0, simulated_fills=0, broker_account_requests=0, paper_risk_approved=False,
        limitations=["Reference-close sizing is not an executable quote or an approved order",
            "No fills/P&L/position transitions are simulated; repeated BUYs remain observations",
            "No weekly rebalance, winner additions or new entry/ranking policy is implemented",
            "No inferred dividends, delivery, cooldown or event-adjusted holding ages; supplied references require review",
            "IEX differs from the historical SIP study; the configurable watchlist is an operational sample",
            "3%/10% legacy halt diagnostics and sizing inputs are not approved personal paper-risk limits"])
    canonical(result)  # Reject any accidental NaN/Infinity before persistence.
    return result


def markdown(report):
    preview = report["preview"]
    pct = lambda value: "unavailable" if value is None else f"{value:.2%}"
    lines = ["# Shadow observation", "", f"Session: {report['session']} | observed: {report['observed_at']}",
        "", "**Observation only. No orders, simulated fills or profit claims.**", "",
        f"Stock exposure: {pct(preview['current_stock_exposure'])} | planned: {pct(preview['planned_stock_exposure'])}",
        f"Target: {pct(preview['target'])} | entry ceiling: {pct(preview['ceiling'])} | target shortfall: {pct(preview['target_shortfall'])}",
        "", f"Market filter: {report['market_filter_on']} | next session open: {report['next_session_open']}",
        "", "Global blockers: " + ("; ".join(report["global_blockers"]) or "none"), "",
        "| Symbol | Signal | Intended buy shares | Reason / blockers |", "| --- | --- | ---: | --- |"]
    for row in report["signals"]:
        reason = (row["reason"] + "; " + "; ".join(row["blockers"])).replace("|", "/").replace("\n", " ")
        exit_note = f"; intended exit shares: {row['preview_exit_quantity']} (not executed)" if "preview_exit_quantity" in row else ""
        lines.append(f"| {row['symbol']} | {row['signal']} | {row['preview_quantity']} | {reason}{exit_note} |")
    lines += ["", "## Limits", ""] + ["- " + text for text in report["limitations"]]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("collect", "observe", "latest"))
    parser.add_argument("--config", type=Path, default=ROOT / "config/shadow_observer.json")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--reference", type=Path, help="Explicit reference book, never fetched from a broker")
    parser.add_argument("--database", type=Path, default=ROOT / "data/shadow/observer.sqlite3")
    parser.add_argument("--output", type=Path, default=ROOT / "data/shadow")
    args = parser.parse_args()
    try:
        store = ObservationStore(args.database)
        if args.command == "latest":
            print(markdown(store.latest()))
            return
        config = load_config(args.config)
        if args.command == "collect":
            if args.bundle is not None:
                raise ValueError("collect uses current data; use observe for a saved bundle")
            from app.shadow.data import ShadowDataClient
            bundle = ShadowDataClient().collect(config)
            write_once(args.output / "bundles" / (digest(bundle) + ".json"), canonical(bundle) + "\n")
        else:
            if args.bundle is None:
                raise ValueError("observe requires --bundle; no credentials are loaded")
            bundle = read_json(args.bundle)
            print("Saved-bundle evaluation at its recorded observation time; not a current quote.\n")
        report = observe(bundle, config, reference=read_json(args.reference) if args.reference else None)
        created = store.record(report)
        destination = args.output / "reports" / report["id"]
        write_once(destination.with_suffix(".json"), canonical(report) + "\n")
        write_once(destination.with_suffix(".md"), markdown(report))
        print(markdown(report))
        print(f"{'Recorded' if created else 'Already recorded'}: {destination.with_suffix('.md')}")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, sqlite3.Error) as exc:
        parser.exit(2, f"Shadow observer stopped: {exc}\n")


if __name__ == "__main__":
    main()

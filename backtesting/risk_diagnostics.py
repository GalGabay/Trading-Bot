"""Reconcile a long-only fill ledger and bound daily-OHLC portfolio equity.

This is retrospective reporting, never a signal input or a stop simulator.
Daily highs/lows do not reveal cross-instrument timing. The envelope allows
every combination of pre/post intraday stop exits and therefore deliberately
overstates possible excursions. It is not an observed intraday equity path.
"""

from __future__ import annotations

from collections import defaultdict
from math import isclose, isfinite
from numbers import Real

import pandas as pd


def _finite_number(value):
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(value)


def daily_risk_envelope(case: dict, datasets: dict[str, pd.DataFrame]) -> dict:
    """Reconcile saved fills against closes; return conservative risk bounds.

    Ordinary fills and GAP_OPEN stops occur at the model's session open.
    TOUCH stops may occur at any time within the session. Only full-position
    exits are supported, as used by the current research engine. Cash earns
    zero, positions are long-only, and no unsettled-funds restriction is
    reconstructed. Missing prices, inconsistent fills, and mismatched equity
    raise; no prices are filled and no path is fabricated.
    """
    if case.get("cash_settlements"):
        raise ValueError("This OHLC risk helper cannot score terminal cash events; do not drop them from the ledger")
    curves = case["equity_curve"]
    if not curves:
        raise ValueError("Risk diagnostics require a nonempty equity curve")
    dates = [pd.Timestamp(point["timestamp"]) for point in curves]
    if any(day.tzinfo is None for day in dates) or dates != sorted(set(dates)):
        raise ValueError("Equity dates must be aware, unique and ordered")
    if any(day >= pd.Timestamp("2024-01-01", tz="UTC") for day in dates):
        raise ValueError("Reserved holdout cannot enter development diagnostics")
    prices = {symbol: frame.set_index("timestamp", verify_integrity=True) for symbol, frame in datasets.items()}
    grouped = defaultdict(list)
    allowed_dates = set(dates)
    for fill in case["fills"]:
        day = pd.Timestamp(fill["timestamp"])
        if day not in allowed_dates or fill["symbol"] not in prices:
            raise ValueError("Fill lies outside declared dates or instruments")
        if fill["side"] not in {"BUY", "SELL"} or not _finite_number(fill["quantity"]) or fill["quantity"] <= 0 or int(fill["quantity"]) != fill["quantity"]:
            raise ValueError("Invalid fill side or quantity")
        if not _finite_number(fill["fill_price"]) or not _finite_number(fill["commission"]) or fill["fill_price"] <= 0 or fill["commission"] < 0:
            raise ValueError("Invalid fill price or commission")
        grouped[day].append(fill)
    initial_cash = case["costs"]["initial_cash"]
    if not _finite_number(initial_cash) or initial_cash <= 0:
        raise ValueError("Initial cash must be finite and positive")
    cash = float(initial_cash)
    positions = {}
    upper_peak = cash
    close_peak = cash
    previous_close = cash
    rows = []

    def apply(fill):
        nonlocal cash
        symbol, quantity = fill["symbol"], fill["quantity"]
        if fill["side"] == "BUY":
            if positions.get(symbol, 0):
                raise ValueError("Unexpected pyramiding in research ledger")
            cash -= quantity * fill["fill_price"] + fill["commission"]
            positions[symbol] = quantity
        else:
            if positions.get(symbol) != quantity:
                raise ValueError("Exit must match the complete open position")
            cash += quantity * fill["fill_price"] - fill["commission"]
            del positions[symbol]
        if cash < -1e-6:
            raise ValueError("Negative cash in reconstructed ledger")

    for day, point in zip(dates, curves):
        day_fills = grouped[day]
        touches = [fill for fill in day_fills if fill["signal_reason"].startswith("PROTECTIVE_STOP_TOUCH:")]
        opens = [fill for fill in day_fills if fill not in touches]
        needed = set(positions) | {fill["symbol"] for fill in day_fills}
        if any(day not in prices[symbol].index for symbol in needed):
            raise ValueError("Missing session prices for a held/traded instrument")
        bars = {symbol: prices[symbol].loc[day] for symbol in needed}
        for symbol, bar in bars.items():
            values = [bar[name] for name in ("open", "high", "low", "close")]
            if not all(_finite_number(value) and value > 0 for value in values):
                raise ValueError(f"{symbol}: OHLC prices must be finite and positive")
            open_, high, low, close = values
            if low > min(open_, close) or high < max(open_, close) or low > high:
                raise ValueError(f"{symbol}: impossible OHLC relationships")

        def mark_open():
            return cash + sum(quantity * float(bars[symbol]["open"]) for symbol, quantity in positions.items())

        open_marks = [mark_open()]
        for fill in opens:
            apply(fill)
            open_marks.append(mark_open())
        stopped = {fill["symbol"]: fill for fill in touches}
        if len(stopped) != len(touches):
            raise ValueError("Duplicate intraday stop exits")
        low_value = high_value = cash
        for symbol, quantity in positions.items():
            lower = quantity * float(bars[symbol]["low"])
            upper = quantity * float(bars[symbol]["high"])
            if symbol in stopped:
                fill = stopped[symbol]
                if fill["quantity"] != quantity:
                    raise ValueError("Partial intraday stop is unsupported")
                proceeds = quantity * fill["fill_price"] - fill["commission"]
                lower, upper = min(lower, proceeds), max(upper, proceeds)
            low_value += lower
            high_value += upper
        if not set(stopped).issubset(positions):
            raise ValueError("Intraday stop has no open position")
        for fill in touches:
            apply(fill)
        close_equity = cash + sum(quantity * float(bars[symbol]["close"]) for symbol, quantity in positions.items())
        if not isclose(close_equity, point["equity"], rel_tol=1e-11, abs_tol=1e-6):
            raise ValueError(f"Fill ledger and saved equity differ on {day}")
        lower = min(low_value, close_equity, *open_marks)
        upper = max(high_value, close_equity, *open_marks)
        if lower <= 0:
            raise ValueError("Nonpositive conservative equity bound")
        close_peak = max(close_peak, close_equity)
        upper_peak = max(upper_peak, upper)
        exposure = (close_equity - cash) / close_equity
        if not isclose(exposure, point["exposure"], abs_tol=1e-9):
            raise ValueError("Fill ledger and saved exposure differ")
        rows.append({"timestamp": day.isoformat(), "cash_at_close": cash,
                     "equity_at_close": close_equity, "equity_lower_envelope": lower,
                     "equity_upper_envelope": upper, "observed_closing_drawdown": close_equity / close_peak - 1,
                     "conservative_drawdown_bound": lower / upper_peak - 1,
                     "conservative_daily_return_bound": lower / previous_close - 1,
                     "model_open_equity_minimum": min(open_marks)})
        previous_close = close_equity
    final_positions = {symbol: position["quantity"] for symbol, position in case["metrics"]["open_positions"].items()}
    if positions != final_positions:
        raise ValueError("Reconstructed final positions differ from report")
    worst = min(rows, key=lambda row: row["conservative_drawdown_bound"])
    return {"ledger_reconciled": True, "intraday_equity_observed": False,
            "observed_max_closing_drawdown": min(row["observed_closing_drawdown"] for row in rows),
            "conservative_drawdown_bound": worst["conservative_drawdown_bound"],
            "conservative_drawdown_bound_date": worst["timestamp"],
            "conservative_daily_return_bound": min(row["conservative_daily_return_bound"] for row in rows),
            "limitation": "Daily extrema and pre/post-stop states need not coexist. A bound breach is not an observed breach; this does not reconstruct real intraday equity.",
            "daily_envelopes": rows}

"""One offline, reviewed AAPL accounting pilot, never a strategy search.

Inputs and exact source hashes are pinned in the review JSON. No API clients,
network access, package installation or order submission belong in this tool.
"""

import argparse
from dataclasses import replace
from datetime import date
import hashlib
import json
from math import isclose
from pathlib import Path

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.data.market_calendar import TradingSession
from app.data.market_data import ValidationConfig, validate_candles
from app.strategy.base import Signal, SignalAction, Strategy
from backtesting.daily_research import pack
from backtesting.historical_holdings import FilingRows
from backtesting.portfolio_engine import PortfolioBacktestEngine, ResearchPortfolioLimits
from backtesting.research import COST_SCENARIOS
from backtesting.risk_diagnostics import daily_risk_envelope
from backtesting.universe import HistoricalUniverse

REVIEW = Path("docs/aapl_raw_action_pilot_review.json")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_file(root: Path, entry: dict) -> Path:
    path = (root / entry["path"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Source path escapes the declared directory")
    if digest(path) != entry["sha256"]:
        raise ValueError(f"Reviewed source checksum changed: {entry['path']}")
    return path


def source_text(path: Path) -> str:
    parser = FilingRows()
    parser.feed(path.read_text(encoding="utf-8"))
    return " ".join(" ".join(parser.text).split())


def session_after(sessions: list[TradingSession], day: str, *, offset: int = 1) -> TradingSession:
    """Explicit convention, not an assertion about broker processing time."""
    if type(offset) is not int or offset < 1:
        raise ValueError("Session offset must be a positive integer")
    matches = [s for s in sessions if s.opens_at.tz_convert("America/New_York").date() > date.fromisoformat(day)]
    if len(matches) < offset:
        raise ValueError("Calendar cannot establish the declared availability convention")
    return matches[offset - 1]


def curate_manifest(review: dict, provider: dict, sessions: list[TradingSession], texts: dict[str, str]) -> dict:
    """Cross-check an explicit review; never normalize unknown events silently."""
    if review["prices"]["adjustment"] != "raw" or review["prices"]["feed"] != "sip":
        raise ValueError("Pilot requires explicitly reviewed raw SIP prices")
    if provider.get("next_page_token"):
        raise ValueError("Incomplete corporate-action pagination")
    actions = provider["corporate_actions"]
    if set(actions) != {"cash_dividends", "forward_splits"}:
        raise ValueError("Unexpected action category requires manual review")
    identity = texts["listing"]
    if not all(term in identity for term in ("Apple Inc.", "Common Stock", "Nasdaq", "symbol AAPL")):
        raise ValueError("Historical filing does not establish the reviewed common-stock identity")
    if "2018-11-05" not in texts["listing_index"]:
        raise ValueError("Historical listing evidence publication date changed")
    records = actions["cash_dividends"]
    expected = review["dividends"]
    if len(records) != 4 or len(expected) != 4 or len({r["id"] for r in records}) != 4:
        raise ValueError("Expected exactly four distinct reviewed ordinary dividends")
    dividends = []
    for item in expected:
        matches = [r for r in records if r["id"] == item["event_id"]]
        if len(matches) != 1:
            raise ValueError("Reviewed dividend identifier missing")
        row = matches[0]
        if (row["symbol"] != "AAPL" or row["ex_date"] != item["ex_session"]
                or row["rate"] != item["cash_per_share"] or row.get("special") is not False
                or row.get("foreign") is not False or row.get("cusip") not in {"", "037833100"}):
            raise ValueError("Dividend terms differ from the explicit review")
        if row.get("payable_date", item["issuer_payable_date"]) != item["issuer_payable_date"]:
            raise ValueError("Provider and issuer payable dates disagree")
        release = texts[item["source"]]
        pay = date.fromisoformat(item["issuer_payable_date"])
        announcement = date.fromisoformat(item["announcement"])
        # Primary issuer text repairs February's absent provider payment field.
        if f"${item['cash_per_share']} per share" not in release or f"{pay.strftime('%B')} {pay.day}, {pay.year}" not in release:
            raise ValueError("Issuer release does not corroborate cash amount and payment date")
        if f"{announcement.strftime('%B')} {announcement.day}, {announcement.year}" not in release:
            raise ValueError("Issuer release does not corroborate the dated announcement")
        known = session_after(sessions, item["announcement"], offset=2).opens_at.isoformat()
        available = session_after(sessions, item["issuer_payable_date"]).opens_at.tz_convert("America/New_York").date().isoformat()
        dividends.append({"event_id": row["id"], "instrument_id": review["instrument_id"],
                          "ex_session": item["ex_session"], "pay_session": available,
                          "cash_per_share": item["cash_per_share"], "known_at": known,
                          "source": review["sources"][item["source"]]["url"] + "; next-session cash convention"})
    split = review["split"]
    if len(actions["forward_splits"]) != 1:
        raise ValueError("Expected one reviewed split")
    row = actions["forward_splits"][0]
    if (row["id"], row["symbol"], row["cusip"], row["ex_date"], row["new_rate"], row["old_rate"]) != (
            split["event_id"], "AAPL", "037833100", split["effective_session"], split["new_shares"], split["old_shares"]):
        raise ValueError("Split terms differ from the explicit review")
    if "four-for-one" not in texts["july"] or "August 31, 2020" not in texts["july"]:
        raise ValueError("Issuer release does not corroborate split ratio/trading date")
    return {"schema_version": 2, "currency": "USD", "price_basis": "raw",
            "action_scope": "explicit_splits_and_ordinary_cash_dividends",
            "sessions": [{"opens_at": s.opens_at.isoformat(), "closes_at": s.closes_at.isoformat()} for s in sessions],
            "listings": [{"instrument_id": review["instrument_id"], "symbol": "AAPL", "exchange": "NASDAQ",
                          "security_type": "common_stock", "start_session": "2019-01-01", "end_session_exclusive": None,
                          "start_known_at": "2018-11-07T00:00:00Z", "end_known_at": None,
                          "source": review["sources"]["listing"]["url"] + "; clipped input coverage, not IPO date"}],
            "cash_outcomes": [], "dividends": dividends,
            "splits": [{"event_id": split["event_id"], "instrument_id": review["instrument_id"],
                        "effective_session": split["effective_session"], "new_shares": 4, "old_shares": 1,
                        "known_at": session_after(sessions, split["announcement"], offset=2).opens_at.isoformat(),
                        "source": review["sources"]["july"]["url"]}]}


class PilotEntry(Strategy):
    name = "engineering_one_entry_hold_not_investment_strategy"
    latest_row_only = True

    def generate_signal(self, market_data, portfolio=None):
        row = market_data.iloc[-1]
        stamp = pd.Timestamp(row["timestamp"])
        action = SignalAction.BUY if stamp.date().isoformat() == "2020-01-02" else SignalAction.HOLD
        return Signal(str(row["symbol"]), action, 1, "Predetermined accounting fixture", stamp.to_pydatetime(), self.name)


def run_pilot(output: Path, *, review_path: Path = REVIEW, source_root: Path | None = None) -> dict:
    if output.exists():
        raise FileExistsError("Choose a fresh pilot output directory")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    expected = ("AAPL", "1Day", "sip", "raw", "2019-01-01", "2021-01-01")
    if tuple(review["prices"][key] for key in ("symbol", "timeframe", "feed", "adjustment", "start", "end_exclusive")) != expected:
        raise ValueError("Frozen pilot price conventions changed")
    if (review["trade_start"], review["trade_end_exclusive"]) != ("2020-01-01", "2021-01-01"):
        raise ValueError("Frozen accounting-pilot window changed")
    root = source_root or Path(review["source_root"])
    paths = {name: checked_file(root, entry) for name, entry in review["sources"].items()}
    price_path, calendar_path = (checked_file(root, review[key]) for key in ("prices", "calendar"))
    provider_path = checked_file(Path.cwd(), review["provider"])
    sessions = [TradingSession(pd.Timestamp(s["opens_at"]), pd.Timestamp(s["closes_at"]))
                for s in json.loads(calendar_path.read_text(encoding="utf-8"))]
    frame = pd.read_csv(price_path)
    validate_candles(frame, config=ValidationConfig(timeframe=TimeFrame.Day))  # rejects naive input before coercion
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    if len(frame) != 505 or len(sessions) != 505 or set(frame["symbol"]) != {"AAPL"}:
        raise ValueError("Pilot input coverage/identity changed")
    if frame["timestamp"].min() < pd.Timestamp("2019-01-01", tz="UTC") or frame["timestamp"].max() >= pd.Timestamp("2021-01-01", tz="UTC"):
        raise ValueError("Pilot contains prices outside its declared 2019-2020 scope")
    manifest = curate_manifest(review, json.loads(provider_path.read_text(encoding="utf-8")), sessions,
                               {name: source_text(path) for name, path in paths.items()})
    output.mkdir(parents=True, exist_ok=False)
    def write(name, value):
        (output / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write("universe.json", manifest)
    universe = HistoricalUniverse.load(output / "universe.json")
    costs = replace(COST_SCENARIOS["base"], initial_cash=10000, periods_per_year=252)
    # Loss gates disabled for this accounting fixture only; no personal limits approved.
    engine = PortfolioBacktestEngine(PilotEntry(), costs=costs,
                                    limits=ResearchPortfolioLimits(max_daily_loss=.99, max_drawdown=.99))
    result = engine.run({review["instrument_id"]: frame}, universe=universe,
                        trade_start=pd.Timestamp("2020-01-01", tz="UTC"), trade_end=pd.Timestamp("2021-01-01", tz="UTC"))
    financial = pack(result)
    risk = daily_risk_envelope(financial, {review["instrument_id"]: frame})
    checks = {"one_next_open_buy_no_synthetic_sales": len(result.fills) == 1 and result.fills[0].timestamp.date().isoformat() == "2020-01-03",
              "initial_three_shares": len(result.fills) == 1 and result.fills[0].quantity == 3,
              "four_for_one_converted_to_twelve": result.final_positions == {review["instrument_id"]: 12},
              "four_entitlements_and_payments": len(result.dividend_entitlements) == len(result.dividend_payments) == 4,
              "dividend_cash_9_69": isclose(sum(p["amount"] for p in result.dividend_payments), 9.69, abs_tol=1e-9),
              "no_final_receivable": not result.final_dividend_receivables,
              "risk_and_financial_ledgers_reconcile": risk["corporate_actions_reconciled"]}
    report = {"purpose": review["purpose"], "review_sha256": digest(review_path),
              "source_sha256": {str(p): digest(p) for p in [*paths.values(), price_path, calendar_path, provider_path]},
              "execution_sha256": {name: digest(Path(name)) for name in (
                  "backtesting/raw_action_pilot.py", "backtesting/portfolio_engine.py", "backtesting/corporate_actions.py",
                  "backtesting/universe.py", "backtesting/risk_diagnostics.py", "backtesting/daily_research.py", "backtesting/research.py")},
              "checks": checks, "all_checks_passed": all(checks.values()), "metrics": financial["metrics"],
              "raw_daily_bars": len(frame), "trading_sessions": len(result.equity_curve),
              "cash_availability_verified_at_broker": False, "market_wide_ready": False,
              "strategy_candidate_approved": False, "limitations": review["limitations"]}
    write("financial.json", financial)
    write("risk.json", risk)
    write("report.json", report)
    if not report["all_checks_passed"]:
        raise ValueError("Accounting pilot failed a declared check; inspect saved report")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--review", default=REVIEW, type=Path)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    report = run_pilot(args.output, review_path=args.review, source_root=args.source_root)
    print(json.dumps({"checks": report["checks"], "market_wide_ready": False}, indent=2))


if __name__ == "__main__":
    main()

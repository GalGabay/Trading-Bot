"""Approved, bounded AAPL/CBRE diagnostic on cached raw prices only.

This separate input path models vendor-dependent entitlement and cash timing.
It never promotes those assumptions to independently verified evidence.
"""

import argparse
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import date
import json
from math import isclose, isfinite
from pathlib import Path

import pandas as pd

from backtesting.cohort_audit import checked_file, digest, SavedCalendar
from backtesting.pilot_readiness_review import offline_only, write_json
from backtesting.pilot_qualification import after
from backtesting.universe import HistoricalUniverse, ListingPeriod, SplitAction, UniverseDataError, _date, _aware, _text
from backtesting.daily_strategies import DailyResearchStrategy, DailyRuleConfig, market_regime
from backtesting.daily_research import pack
from backtesting.engine import BacktestConfig
from backtesting.holding_policy import HoldingPolicy
from backtesting.holding_research import holding_summary
from backtesting.portfolio_engine import PortfolioBacktestEngine, ResearchPortfolioLimits
from backtesting.protective_exits import ProtectiveExitConfig
from backtesting.research_policy import AllocationPolicy, HaltPolicy
from backtesting.risk_diagnostics import daily_risk_envelope
from app.data.market_calendar import TradingSession
from app.data.market_data import validate_candles, ValidationConfig
from alpaca.data.timeframe import TimeFrame

APPROVAL = Path("docs/next_pilot_experiment_approval.json")
POLICIES = ("base", "delayed_five_sessions", "no_credit")


@dataclass(frozen=True)
class DiagnosticDividend:
    event_id: str
    instrument_id: str
    ex_session: str
    pay_session: str | None
    cash_per_share: float
    known_at: str
    source: str
    kind: str = "ordinary_cash"
    share_basis: str = "post_split"

    def __post_init__(self):
        for name in ("event_id", "instrument_id", "source"):
            _text(getattr(self, name), name)
        if self.instrument_id != self.instrument_id.strip().upper():
            raise UniverseDataError("Diagnostic dividends require uppercase stable IDs")
        ex = _date(self.ex_session)
        if self.pay_session is not None and _date(self.pay_session) < ex:
            raise UniverseDataError("Modeled payment precedes ex-session")
        _aware(self.known_at)
        if (isinstance(self.cash_per_share, bool) or not isinstance(self.cash_per_share, (int, float))
                or not isfinite(self.cash_per_share) or self.cash_per_share <= 0):
            raise UniverseDataError("Positive finite ordinary dividend amount required")
        if (self.kind, self.share_basis) != ("ordinary_cash", "post_split"):
            raise UniverseDataError("Special/due-bill or ambiguous share-basis events are unsupported")


class DiagnosticUniverse(HistoricalUniverse):
    """Reuse the engine with explicitly modeled, possibly deferred payments.

    The legacy universe/ownership loaders and their evidence gates are unchanged.
    None means no modeled cash credit in this window, never a future date.
    """

    def __init__(self, *, sessions, listings, splits=(), dividends=(), cash_policy,
                 approval_sha256, owner_approved, journal):
        if owner_approved is not True or cash_policy not in POLICIES or not approval_sha256:
            raise UniverseDataError("Diagnostic mode requires explicit approval and a named cash policy")
        super().__init__(sessions=sessions, listings=listings, splits=splits,
                         price_basis="raw", action_scope="explicit_splits_and_ordinary_cash_dividends")
        ids = {a.event_id for a in self.splits}
        schedule = {}
        for item in dividends:
            if not isinstance(item, DiagnosticDividend) or item.event_id in ids:
                raise UniverseDataError("Duplicate or unsupported diagnostic event")
            ids.add(item.event_id)
            day = _date(item.ex_session)
            stamp = pd.Timestamp(day, tz="America/New_York").tz_convert("UTC")
            if day not in self._by_day or self.listing_at(item.instrument_id, stamp) is None:
                raise UniverseDataError("Diagnostic ex-date lacks an actual listed session")
            if _aware(item.known_at) > self._by_day[day].opens_at:
                raise UniverseDataError("Diagnostic event terms not known before required boundary")
            if item.pay_session is not None and _date(item.pay_session) not in self._by_day:
                raise UniverseDataError("Modeled payment must be an actual session in this window")
            if cash_policy == "no_credit" and item.pay_session is not None:
                raise UniverseDataError("No-credit scenario cannot schedule cash")
            schedule[item.event_id] = {"pay_session": item.pay_session}
            self._dividends.setdefault(stamp, []).append(item)
        self.dividends = tuple(dividends)
        self.diagnostic = dict(schema_version=1, owner_approved=True, approval_sha256=approval_sha256,
            cash_policy=cash_policy, independently_verified_entitlement=False,
            broker_cash_credit_verified=False, ready_for_strict_scoring=False,
            vendor_reliance=True, paper_authorized=False, cash_schedule=schedule,
            assumption_journal=journal)

    def metadata(self):
        return {**super().metadata(), "diagnostic_research": self.diagnostic}


def cash_open(sessions, payable, policy, end_exclusive):
    if policy not in POLICIES:
        raise ValueError("Unknown diagnostic cash scenario")
    _date(payable)
    if policy == "no_credit":
        return None
    instant = after(sessions, payable, 1 if policy == "base" else 6)
    if instant is None:
        return None
    day = pd.Timestamp(instant).tz_convert("America/New_York").date().isoformat()
    return day if day < end_exclusive else None


def load_approved():
    root = Path.cwd()
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    if (approval.get("owner_approved") is not True or approval.get("max_strategy_attempts") != 24
            or approval.get("paper_trading_approved") is not False or approval.get("purchases_budget_usd") != 0):
        raise ValueError("Only the approved offline capped diagnostic is supported")
    path = checked_file(root, approval["proposal"])
    proposal = json.loads(path.read_text(encoding="utf-8"))
    for item in proposal["inputs"]:
        checked_file(root, item)
    if (proposal["max_strategy_runs"] != 24 or proposal["candidate_symbols"] != ["AAPL", "CBRE"]
            or proposal["context_only"] != ["SPY"] or proposal["adjustment"] != "raw"):
        raise ValueError("Approved diagnostic scope changed")
    summary = json.loads(checked_file(root, proposal["evidence_report"]).read_text(encoding="utf-8"))
    for name, sha in summary["input_sha256"].items():
        checked_file(root, dict(path=name, sha256=sha))
    for item in summary["tracked_outputs"].values():
        checked_file(root, item)
    frozen = json.loads(Path("docs/free_data_pilot_proposal.json").read_text(encoding="utf-8"))
    sessions = [TradingSession(pd.Timestamp(r["opens_at"]), pd.Timestamp(r["closes_at"]))
                for r in json.loads(checked_file(root, frozen["calendar"]).read_text(encoding="utf-8"))]
    rows = pd.read_csv(summary["tracked_outputs"]["events"]["path"], keep_default_na=False).to_dict("records")
    data, identities = {}, {}
    for stream in frozen["streams"]:
        symbol = stream.get("symbol", "CBRE")
        if symbol not in {"AAPL", "CBRE", "SPY"}:
            continue
        frame = pd.read_csv(checked_file(root, stream["csv"]))
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        logical = frame.copy()
        logical["symbol"] = stream["instrument_id"]
        validate_candles(logical, calendar=SavedCalendar(sessions),
            config=ValidationConfig(timeframe=TimeFrame.Day, require_all_scheduled_bars=True),
            requested_start=pd.Timestamp("2016-01-01", tz="UTC"), requested_end=pd.Timestamp("2023-12-31T23:59:59Z"))
        if len(frame) != 2012 or frame["timestamp"].max() >= pd.Timestamp("2024-01-01", tz="UTC"):
            raise ValueError("Unexpected saved price coverage")
        data[symbol], identities[symbol] = frame, stream["instrument_id"]
    return approval, proposal, sessions, rows, data, identities


def build_window(window, policy, sessions, rows, data, identities, approval_sha):
    begin, end = window["warmup_start"], window["end_exclusive"]
    if not "2016-01-01" <= begin < window["evaluation_start"] < end <= "2024-01-01":
        raise ValueError("Invalid diagnostic development window")
    selected = [s for s in sessions if begin <= s.opens_at.date().isoformat() < end]
    first = selected[0].opens_at.tz_convert("America/New_York").date().isoformat()
    assumed_known = (pd.Timestamp(first, tz="UTC") - pd.Timedelta(days=1)).isoformat()
    rename_known = after(sessions, "2018-03-08", 2)
    listings = [ListingPeriod(identities["AAPL"], "AAPL", "NASDAQ", "common_stock", first, None,
                             assumed_known, None, "Diagnostic clipped vendor coverage; not IPO or independently certified publication")]
    if first < "2018-03-19":
        listings.append(ListingPeriod(identities["CBRE"], "CBG", "NYSE", "common_stock", first,
            "2018-03-19", assumed_known, rename_known, "Diagnostic vendor coverage plus issuer CBG-to-CBRE boundary"))
    listings.append(ListingPeriod(identities["CBRE"], "CBRE", "NYSE", "common_stock", max(first, "2018-03-19"),
        None, rename_known, None, "Issuer alias boundary; clipped vendor coverage, unresolved tax subtype unused"))
    splits, dividends, journal = [], [], []
    for row in rows:
        if row["symbol"] not in {"AAPL", "CBRE"}:
            continue
        ex = row["ex_or_effective_date"]
        if not begin <= ex < end:
            continue
        kind = row["kind"]
        if kind == "cash_dividend":
            if row["symbol"] != "AAPL" or row["ex_date_basis"] != "provider_only_cross_reference":
                raise ValueError("Unsupported diagnostic dividend identity/basis")
            known = after(sessions, row["declared"], 2)
            pay = cash_open(sessions, row["payable"], policy, end)
            dividends.append(DiagnosticDividend(row["event_id"], identities["AAPL"], ex, pay,
                float(row["nominal_amount"]), known, row["source_url"] + "; modeled vendor ex-date and cash availability"))
            journal.append(dict(event_id=row["event_id"], issuer_payable=row["payable"], provider_ex_date=ex,
                modeled_known_at=known, modeled_cash_session=pay, cash_policy=policy,
                independently_verified_entitlement=False, broker_cash_credit_verified=False))
        elif kind == "split_4_for_1":
            splits.append(SplitAction(row["event_id"], identities["AAPL"], ex, 4, 1,
                after(sessions, row["declared"], 2), row["source_url"]))
        elif kind != "alias_change_no_automatic_quantity_change":
            raise ValueError("Unexpected action kind; no automatic admission")
    universe = DiagnosticUniverse(sessions=selected, listings=listings, splits=splits, dividends=dividends,
        cash_policy=policy, approval_sha256=approval_sha, owner_approved=True, journal=journal)
    subset = {name: frame.loc[(frame["timestamp"] >= pd.Timestamp(begin, tz="UTC")) &
                             (frame["timestamp"] < pd.Timestamp(end, tz="UTC"))].reset_index(drop=True)
              for name, frame in data.items()}
    return universe, {identities[s]: subset[s] for s in ("AAPL", "CBRE")}, subset["SPY"]


def diagnostic_pack(result, years):
    case = pack(result)
    m = case["metrics"]
    after_exit = m["hypothetical_liquidated_return"]
    m.update(net_marked_return_after_estimated_share_exits=after_exit,
        net_marked_cagr_after_estimated_share_exits=(1 + after_exit) ** (1 / years) - 1,
        marked_cagr=(1 + m["total_return"]) ** (1 / years) - 1,
        net_account_profit=m["final_equity"] - result.costs.initial_cash,
        final_spendable_cash=result.equity_curve[-1].cash,
        final_receivable=result.equity_curve[-1].dividend_receivable,
        realized_trading_pnl=m["realized_pnl"], dividend_income_includes_unpaid_rights=True)
    if result.final_dividend_receivables:
        m["hypothetical_liquidated_return"] = None
        m["claims_not_liquidated"] = True
    pnl = m["realized_pnl"] + m["marked_unrealized_pnl"] + m["dividend_income_earned"]
    if not isclose(pnl, m["net_account_profit"], abs_tol=1e-6):
        raise ValueError("Diagnostic realized/open/dividend equity reconciliation failed")
    daily = [result.costs.initial_cash] + [p.equity for p in result.equity_curve]
    m["worst_closing_daily_return"] = min(b/a - 1 for a,b in zip(daily,daily[1:]))
    m["mean_cash_fraction"] = sum(p.cash/p.equity for p in result.equity_curve)/len(result.equity_curve)
    multiplier = (result.costs.slippage_bps + result.costs.spread_bps/2)/10000
    slip = spread = 0.0
    for fill in result.fills:
        reference = (fill.fill_price/(1-multiplier) if fill.signal_reason.startswith("PROTECTIVE_STOP_") else fill.reference_open)
        expected = reference*(1+multiplier if fill.side.value == "BUY" else 1-multiplier)
        if not isclose(expected,fill.fill_price,abs_tol=1e-8):
            raise ValueError("Diagnostic fill cost attribution failed")
        slip += reference*fill.quantity*result.costs.slippage_bps/10000
        spread += reference*fill.quantity*result.costs.spread_bps/20000
    m.update(modeled_slippage_cost=slip, modeled_spread_cost=spread,
        total_modeled_trade_cost=slip+spread+m["commissions_paid"],
        decision="exploratory_only_not_eligible_for_paper", investment_criteria_relaxed=False)
    case["holding_reviews"] = list(result.holding_reviews)
    case["holding_statistics"] = holding_summary(result)
    contributions = {}
    for key in {p["instrument_id"] for p in result.universe_metadata["listings"]}:
        realized = m["realized_pnl_by_symbol"].get(key, 0.0)
        unrealized = m["open_positions"].get(key, {}).get("marked_unrealized_pnl", 0.0)
        dividend = sum(e["amount"] for e in result.dividend_entitlements if e["instrument_id"] == key)
        contributions[key] = dict(realized_trading_pnl=realized, open_marked_pnl=unrealized,
            dividend_income_earned=dividend, net_marked_profit=realized+unrealized+dividend)
    if not isclose(sum(v["net_marked_profit"] for v in contributions.values()), m["net_account_profit"], abs_tol=1e-6):
        raise ValueError("Per-instrument contributions do not reconcile")
    case["instrument_contributions"] = contributions
    case["risk_events"] = list(result.risk_events)
    case["buy_decisions"] = list(result.buy_decisions)
    return case


def execute_case(proposal, window, capital, cost, policy, inputs):
    approval, _, sessions, rows, data, identities = inputs
    universe, datasets, context = build_window(window, policy, sessions, rows, data, identities, digest(APPROVAL))
    regime = market_regime(context)
    settings = proposal["strategy"]
    engine = PortfolioBacktestEngine(DailyResearchStrategy(DailyRuleConfig("breakout",55,20),regime=regime),
        costs=BacktestConfig(initial_cash=capital,position_fraction=settings["position_cap"],periods_per_year=252,
            slippage_bps=cost["slippage_bps_per_side"],spread_bps=cost["full_spread_bps"],commission_per_order=cost["commission_per_order_usd"]),
        limits=ResearchPortfolioLimits(max_single_position=settings["position_cap"],max_portfolio_exposure=settings["portfolio_cap"],
            max_positions=settings["max_positions"],max_daily_loss=settings["daily_loss_latched_halt"],max_drawdown=settings["drawdown_latched_halt"]),
        protection=ProtectiveExitConfig(atr_multiple=3,max_risk_per_trade=.005,trailing=False),
        reentry_cooldown_sessions=10,allocation=AllocationPolicy(.01),halt_policy=HaltPolicy(),
        holding_policy=HoldingPolicy("continuation"),holding_market_review=regime,record_decisions=True)
    result = engine.run(datasets,universe=universe,trade_start=pd.Timestamp(window["evaluation_start"],tz="UTC"),
                        trade_end=pd.Timestamp(window["end_exclusive"],tz="UTC"))
    years = int(window["end_exclusive"][:4])-int(window["evaluation_start"][:4])
    case = diagnostic_pack(result,years)
    risk = daily_risk_envelope(case,datasets)
    if not risk["ledger_reconciled"] or not risk.get("corporate_actions_reconciled", True):
        raise ValueError("Diagnostic risk ledger failed")
    case["diagnostic_risk"] = risk
    return case


def execution_hashes():
    names = ["backtesting/pilot_diagnostic.py", "backtesting/risk_diagnostics.py", "tests/test_pilot_diagnostic.py",
             "backtesting/universe.py", "backtesting/corporate_actions.py", "backtesting/portfolio_engine.py",
             "backtesting/daily_research.py", "backtesting/daily_strategies.py", "backtesting/holding_policy.py",
             "backtesting/research_policy.py", "backtesting/protective_exits.py", "app/ai/features.py"]
    return {p:digest(p) for p in names}


def run(output, verification_path):
    inputs = load_approved()
    approval, proposal = inputs[:2]
    if output.resolve() != Path(approval["output_directory"]).resolve() or output.exists():
        raise ValueError("This approval permits one fresh named output directory; no automatic reruns")
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    if (verification["passed"] is not True or verification["failures"] or verification["errors"]
            or verification["tests_run"] < 25 or verification["skipped"]
            or verification["approval_sha256"] != digest(APPROVAL) or verification["execution_sha256"] != execution_hashes()):
        raise ValueError("Passing current offline verification is required before performance runs")
    output.mkdir(parents=True,exist_ok=False)
    report = dict(status="running",approval_sha256=digest(APPROVAL),proposal_sha256=digest(Path(approval["proposal"]["path"])),
        verification_sha256=digest(verification_path),execution_sha256=execution_hashes(),attempts=[],runs=[],
        network_requests=0,purchases_usd=0,broker_account_requests=0,orders=0,holdout_candles_read=False,
        paper_authorized=False,market_wide_ready=False,strict_evidence_flags_promoted=False)
    write_json(output/"report.json",report)
    try:
        for window in proposal["windows"]:
            for capital in proposal["account_sizes_usd"]:
                for cost in proposal["costs"]:
                    for policy in POLICIES:
                        if len(report["attempts"]) >= 24:
                            raise ValueError("Approved strategy-attempt cap exhausted")
                        key=f"{window['id']}_{capital}_{cost['id']}_{policy}"
                        report["attempts"].append(key)
                        write_json(output/"report.json",report)
                        case=execute_case(proposal,window,capital,cost,policy,inputs)
                        write_json(output/f"{key}.json",case)
                        report["runs"].append(dict(id=key,window=window["id"],capital=capital,cost=cost["id"],cash_policy=policy,
                            file=f"{key}.json",sha256=digest(output/f"{key}.json"),metrics=case["metrics"]))
                        write_json(output/"report.json",report)
                        print(f"Completed {len(report['runs'])}/24: {key}",flush=True)
        report.update(status="completed",strategy_simulations=len(report["runs"]))
    except Exception as exc:
        report.update(status="stopped_on_error",error_type=type(exc).__name__,error=str(exc))
        raise
    finally:
        write_json(output/"report.json",report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--verification",type=Path,required=True)
    args=parser.parse_args()
    with offline_only():
        report=run(args.output,args.verification)
    print(json.dumps(dict(status=report["status"],runs=len(report["runs"]))))


if __name__ == "__main__":
    main()

"""Six fixed synthetic event-free control comparisons; no research signals.

Compare new diagnostic accounting with legacy fill/equity behavior under the
same costs and 70/5/20 entry settings. This is not a replay of old real-market
research returns, a strategy parameter search or any of the 24 performance cases.
"""

import argparse
from dataclasses import replace
from math import isclose
from pathlib import Path

from backtesting.broad_collection import pin
from backtesting.diagnostic_bridge import DiagnosticSchedule, DiagnosticUniverse
from backtesting.engine import BacktestConfig
from backtesting.pilot_readiness_review import offline_only, write_json
from backtesting.portfolio_engine import PortfolioBacktestEngine, ResearchPortfolioLimits
from tests.test_universe import UniverseFixture
from tests.test_portfolio_backtesting import ScriptedDailyStrategy
from app.strategy.base import SignalAction


def run(output):
    if output.exists() or not output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Choose a fresh synthetic-control report directory inside the workspace")
    fixture=UniverseFixture()
    fixture.setUp()
    n=209
    legacy=fixture.universe(n=n,listings=[fixture.listing(),fixture.listing(key="ID-B",symbol="BBB")])
    original={"ID-A":fixture.bars(symbol="AAA",end=n),"ID-B":fixture.bars(symbol="BBB",end=n,price=80)}
    diagnostic_data={key:frame.assign(symbol=key) for key,frame in original.items()}
    streams=[dict(instrument_id=key,parts=[dict(start=fixture.day(0),end_exclusive=fixture.day(n))]) for key in original]
    actions={(key,fixture.day(199)):SignalAction.BUY for key in original}
    actions.update({("ID-A",fixture.day(202)):SignalAction.SELL,("ID-B",fixture.day(205)):SignalAction.SELL})
    limits=ResearchPortfolioLimits(max_portfolio_exposure=.70,max_single_position=.05,max_positions=20)
    checks=[]
    for name,slip,spread,commission in (("base",5,2,0),("pessimistic",20,10,1)):
        costs=BacktestConfig(initial_cash=10000,position_fraction=.05,periods_per_year=252,
            slippage_bps=slip,spread_bps=spread,commission_per_order=commission)
        def engine():
            return PortfolioBacktestEngine(ScriptedDailyStrategy(actions),costs=costs,limits=limits)
        expected=engine().run(original,trade_start=fixture.dates[0],trade_end=fixture.dates[n],universe=legacy)
        for scenario in ("base","delayed_five_sessions","no_credit"):
            universe=DiagnosticUniverse(fixture.sessions[:n],streams)
            schedule=DiagnosticSchedule(entry_instrument_ids=list(original),scenario=scenario,
                approval_sha256="SYNTHETIC FIXTURE ONLY",membership_not_before=fixture.known(0))
            actual=engine().run(diagnostic_data,trade_start=fixture.dates[0],trade_end=fixture.dates[n],universe=universe,diagnostic=schedule)
            if (actual.fills!=expected.fills or actual.final_positions!=expected.final_positions or
                    len(actual.equity_curve)!=len(expected.equity_curve)):
                raise AssertionError("Synthetic diagnostic control fills/final holdings differ from legacy")
            for a,b in zip(actual.equity_curve,expected.equity_curve):
                if a.timestamp!=b.timestamp or any(not isclose(getattr(a,key),getattr(b,key),abs_tol=1e-8,rel_tol=1e-11)
                        for key in ("cash","equity","gross_exposure","position_count","drawdown")):
                    raise AssertionError("Synthetic diagnostic control cash/equity/exposure differs from legacy")
            checks.append(dict(cost=name,scenario=scenario,fill_equality=True,financial_curve_equality=True,
                sessions_checked=n,simulated_fixture_only=True))
    output.mkdir()
    report=dict(checks=checks,checks_passed=len(checks),research_strategy_runs=0,synthetic_engine_runs=8,
        real_market_performance_runs=0,network_requests=0,broker_requests=0,orders=0,purchases_usd=0,
        execution=[pin(Path(__file__)),pin("backtesting/diagnostic_bridge.py"),pin("backtesting/portfolio_engine.py")],
        limitation="Synthetic event-free financial compatibility only; not equality to old real-data research results")
    write_json(output/"report.json",report)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    with offline_only():
        result=run(args.output)
        print(f"Passed {result['checks_passed']} synthetic financial control comparisons; zero research performance runs.")

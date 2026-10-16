"""Offline, deterministic checks for the standalone Phase 10 risk gate."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from unittest import TestCase

from app.risk import (
    RiskLimits, RiskManager, RiskPortfolioSnapshot, RiskPosition, TradeCandidate,
)
from app.strategy.base import Signal, SignalAction


SIGNAL_TIME = datetime(2026, 1, 2, 15, 0, tzinfo=UTC)
EVALUATED_AT = SIGNAL_TIME + timedelta(minutes=1)


def candidate(
    action: SignalAction = SignalAction.BUY,
    *, symbol: str = "AAPL", quantity: int = 5, price: float = 100.0,
    stop: float | None = 90.0, sector: str | None = None,
    volatility: float | None = None,
) -> TradeCandidate:
    signal = Signal(symbol, action, 1.0, "risk test", SIGNAL_TIME, "test_strategy")
    return TradeCandidate(
        signal=signal, quantity=quantity, estimated_price=price,
        stop_price=stop, sector=sector, annualized_volatility=volatility,
    )


def snapshot(
    *, cash: float = 10_000.0, equity: float = 10_000.0,
    day_start: float = 10_000.0, peak: float = 10_000.0,
    positions: tuple[RiskPosition, ...] = (), complete: bool = True,
    as_of: datetime = SIGNAL_TIME - timedelta(seconds=30),
) -> RiskPortfolioSnapshot:
    return RiskPortfolioSnapshot(
        as_of=as_of, cash=cash, equity=equity,
        day_start_equity=day_start, peak_equity=peak,
        positions=positions, complete=complete,
    )


def codes(decision) -> set[str]:
    return {issue.code for issue in decision.issues}


class RiskManagerTests(TestCase):
    def setUp(self) -> None:
        self.manager = RiskManager()

    def test_valid_buy_is_approved_with_auditable_calculations(self) -> None:
        decision = self.manager.evaluate(candidate(), snapshot(), evaluated_at=EVALUATED_AT)
        self.assertTrue(decision.approved)
        self.assertEqual(decision.issues, ())
        self.assertEqual(decision.policy_version, "risk_v1")
        self.assertEqual(decision.limits, self.manager.limits)
        self.assertEqual(decision.evaluated_at, EVALUATED_AT)
        self.assertAlmostEqual(decision.proposed_notional, 500.0)
        self.assertAlmostEqual(decision.projected_exposure_fraction, 0.05)
        self.assertAlmostEqual(decision.estimated_risk_fraction, 0.005)
        with self.assertRaises(FrozenInstanceError):
            decision.approved = False

    def test_plan_example_limits_are_provisional_and_invalid_limits_fail(self) -> None:
        self.assertEqual(self.manager.limits.max_portfolio_exposure, 0.70)
        self.assertEqual(self.manager.limits.max_single_position, 0.10)
        self.assertEqual(self.manager.limits.max_risk_per_trade, 0.01)
        self.assertEqual(self.manager.limits.max_daily_loss, 0.03)
        invalid = (
            {"max_portfolio_exposure": float("nan")},
            {"max_single_position": True},
            {"max_single_position": 0.8},
            {"max_positions": 0},
            {"max_snapshot_age_seconds": 0},
            {"max_signal_age_seconds": 0},
            {"max_sector_exposure": float("inf")},
            {"max_annualized_volatility": -1},
        )
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                RiskLimits(**values)

    def test_hold_and_invalid_candidate_values_cannot_be_approved(self) -> None:
        cases = (
            (candidate(SignalAction.HOLD), "not_actionable"),
            (candidate(quantity=0), "invalid_quantity"),
            (candidate(quantity=True), "invalid_quantity"),
            (candidate(price=float("nan")), "invalid_price"),
            (candidate(price=0), "invalid_price"),
        )
        for trade, expected in cases:
            with self.subTest(expected=expected):
                decision = self.manager.evaluate(trade, snapshot())
                self.assertFalse(decision.approved)
                self.assertIn(expected, codes(decision))

    def test_missing_or_invalid_stop_rejects_buy(self) -> None:
        for stop in (None, 0, 100, 101, float("inf")):
            with self.subTest(stop=stop):
                decision = self.manager.evaluate(candidate(stop=stop), snapshot())
                self.assertIn("invalid_stop", codes(decision))

    def test_stop_based_risk_and_single_position_limits(self) -> None:
        risk = self.manager.evaluate(candidate(stop=1), snapshot())
        self.assertIn("risk_per_trade_limit", codes(risk))
        size = self.manager.evaluate(candidate(quantity=11, stop=99), snapshot())
        self.assertIn("single_position_limit", codes(size))
        self.assertNotIn("risk_per_trade_limit", codes(size))

    def test_cash_exposure_and_position_count_limits(self) -> None:
        existing = (RiskPosition("MSFT", 65, 100),)
        account = snapshot(cash=3_500, positions=existing)
        exposure = self.manager.evaluate(candidate(quantity=6, stop=99), account)
        self.assertIn("portfolio_exposure_limit", codes(exposure))
        self.assertNotIn("single_position_limit", codes(exposure))
        count = RiskManager(limits=RiskLimits(max_positions=1)).evaluate(candidate(), account)
        self.assertIn("position_count_limit", codes(count))
        cash = self.manager.evaluate(candidate(), snapshot(cash=400, positions=(RiskPosition("MSFT", 96, 100),)))
        self.assertIn("insufficient_cash", codes(cash))

    def test_daily_loss_and_drawdown_block_new_buys_at_the_limit(self) -> None:
        daily = self.manager.evaluate(candidate(), snapshot(cash=9_700, equity=9_700))
        self.assertIn("daily_loss_limit", codes(daily))
        drawdown = self.manager.evaluate(candidate(), snapshot(
            cash=9_000, equity=9_000, day_start=9_000, peak=10_000,
        ))
        self.assertIn("drawdown_limit", codes(drawdown))
        self.assertNotIn("daily_loss_limit", codes(drawdown))

    def test_reducing_sell_can_pass_after_loss_but_cannot_exceed_holding(self) -> None:
        account = snapshot(
            cash=9_000, equity=9_500,
            positions=(RiskPosition("AAPL", 5, 100),),
        )
        sell = self.manager.evaluate(candidate(SignalAction.SELL, stop=None), account)
        self.assertTrue(sell.approved)
        self.assertEqual(sell.proposed_notional, 500)
        too_many = self.manager.evaluate(candidate(SignalAction.SELL, quantity=6), account)
        self.assertIn("invalid_exit", codes(too_many))
        no_holding = self.manager.evaluate(candidate(SignalAction.SELL), snapshot())
        self.assertIn("invalid_exit", codes(no_holding))

    def test_repeated_buy_for_an_open_position_is_rejected(self) -> None:
        account = snapshot(
            cash=9_500, positions=(RiskPosition("aapl", 5, 100),),
        )
        decision = self.manager.evaluate(candidate(), account)
        self.assertIn("position_already_open", codes(decision))

    def test_missing_incomplete_or_invalid_snapshot_fails_closed(self) -> None:
        cases = (
            (None, "incomplete_snapshot"),
            (snapshot(complete=False), "incomplete_snapshot"),
            (snapshot(cash=float("nan")), "invalid_snapshot"),
            (snapshot(cash=9_000), "invalid_snapshot"),
            (snapshot(as_of=datetime(2026, 1, 2, 15, 0)), "invalid_snapshot_time"),
            (snapshot(positions=(RiskPosition("AAPL", 1, 100), RiskPosition("aapl", 1, 100)), cash=9_800), "invalid_snapshot"),
        )
        for account, expected in cases:
            with self.subTest(expected=expected):
                decision = self.manager.evaluate(candidate(), account)
                self.assertFalse(decision.approved)
                self.assertIn(expected, codes(decision))

    def test_signal_and_snapshot_freshness_use_actual_evaluation_time(self) -> None:
        # A snapshot fetched after signal generation is valid when it precedes
        # the explicitly supplied paper-workflow evaluation time.
        after_signal = snapshot(as_of=SIGNAL_TIME + timedelta(seconds=30))
        approved = self.manager.evaluate(candidate(), after_signal, evaluated_at=EVALUATED_AT)
        self.assertTrue(approved.approved)
        old_snapshot = snapshot(as_of=SIGNAL_TIME - timedelta(minutes=5))
        self.assertIn("stale_snapshot", codes(self.manager.evaluate(candidate(), old_snapshot, evaluated_at=EVALUATED_AT)))
        stale_exit_account = snapshot(
            cash=9_500, positions=(RiskPosition("AAPL", 5, 100),), as_of=old_snapshot.as_of,
        )
        self.assertIn("stale_snapshot", codes(self.manager.evaluate(
            candidate(SignalAction.SELL), stale_exit_account, evaluated_at=EVALUATED_AT,
        )))
        old_signal = self.manager.evaluate(candidate(), snapshot(), evaluated_at=SIGNAL_TIME + timedelta(minutes=6))
        self.assertIn("stale_signal", codes(old_signal))
        future_snapshot = snapshot(as_of=EVALUATED_AT + timedelta(seconds=1))
        self.assertIn("stale_snapshot", codes(self.manager.evaluate(candidate(), future_snapshot, evaluated_at=EVALUATED_AT)))
        naive_evaluation = datetime(2026, 1, 2, 15, 1)
        self.assertIn("invalid_evaluation_time", codes(self.manager.evaluate(candidate(), snapshot(), evaluated_at=naive_evaluation)))

    def test_optional_sector_and_volatility_gates_require_metadata(self) -> None:
        manager = RiskManager(limits=RiskLimits(
            max_sector_exposure=0.20, max_annualized_volatility=0.40,
        ))
        missing = manager.evaluate(candidate(), snapshot())
        self.assertEqual(codes(missing), {"sector_data_missing", "volatility_data_missing"})
        valid = manager.evaluate(candidate(sector="TECH", volatility=0.30), snapshot())
        self.assertTrue(valid.approved)
        volatile = manager.evaluate(candidate(sector="TECH", volatility=0.50), snapshot())
        self.assertIn("volatility_limit", codes(volatile))
        sector_account = snapshot(cash=8_500, positions=(RiskPosition("MSFT", 15, 100, "TECH"),))
        at_limit = manager.evaluate(candidate(sector="TECH", volatility=0.30), sector_account)
        self.assertTrue(at_limit.approved)
        concentrated = manager.evaluate(candidate(quantity=6, sector="TECH", volatility=0.30), sector_account)
        self.assertIn("sector_exposure_limit", codes(concentrated))
        unlabeled = snapshot(cash=9_500, positions=(RiskPosition("MSFT", 5, 100),))
        self.assertIn("sector_data_missing", codes(manager.evaluate(candidate(sector="TECH", volatility=0.30), unlabeled)))

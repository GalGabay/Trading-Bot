"""Offline boundaries, approval checks, accounting, and audit refusal paths."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from backtesting.goal_fit import (
    POLICY, above_loss_limit, assess_saved_stresses, checks_for,
    cost_attribution, frozen_source_path, load_policy, run_audit, write,
)


class ResearchApprovalTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "policy.json"
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def load(self, **changes):
        self.path.write_text(json.dumps({**self.policy, **changes}), encoding="utf-8")
        return load_policy(self.path)

    def test_approved_policy_retains_separate_order_and_holdout_refusals(self):
        policy = self.load()
        self.assertEqual(policy["annual_return_cagr_minimum"], .06)
        self.assertEqual(policy["drawdown_rejection_level"], .05)
        self.assertFalse(policy["approved_for_paper"])
        self.assertFalse(policy["approved_for_final_evaluation"])

    def test_unapproved_or_truthy_non_boolean_flags_are_rejected(self):
        for value in (False, 1, "true", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.load(approved_for_development_audit=value)

    def test_paper_or_final_approval_cannot_be_smuggled_into_audit_record(self):
        for key in ("approved_for_final_evaluation", "approved_for_paper"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.load(**{key: True})

    def test_wrong_boundary_basis_or_account_sizes_are_rejected(self):
        for changes in ({"reserved_start": "2025-01-01"}, {"drawdown_basis": "starting_equity"},
                        {"audit_account_sizes": [10000]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.load(**changes)

    def test_nonfinite_out_of_range_and_malformed_fractions_are_rejected(self):
        for key in ("annual_return_cagr_minimum", "drawdown_rejection_level", "drawdown_review_level", "daily_loss_rejection_level"):
            for value in (True, 0, -1, 1, float("nan"), float("inf"), "0.06", None):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.load(**{key: value})

    def test_invalid_evidence_and_profit_factor_requirements_are_rejected(self):
        for key, values in (("minimum_completed_trades", (True, 0, 1.5)),
                            ("minimum_instruments", (True, 0, 1.5)),
                            ("minimum_profit_factor", (True, 1, float("nan"), None, "1.2"))):
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.load(**{key: value})

    def test_review_level_must_precede_rejection_level(self):
        with self.assertRaisesRegex(ValueError, "Review drawdown"):
            self.load(drawdown_review_level=.05)


class GoalThresholdTests(TestCase):
    def setUp(self):
        self.policy = load_policy(POLICY)
        self.metrics = {"hypothetical_liquidated_return": 1.06**2 - 1, "profit_factor": 1.2,
                        "max_drawdown": -.039, "worst_closing_daily_return": -.019,
                        "completed_trades": 30, "instruments_with_closed_trades": 5,
                        "realized_pnl": 1, "permanent_halt_reason": None}

    def check(self, **changes):
        return checks_for({**self.metrics, **changes}, 2, self.policy)

    def test_exact_return_trade_count_breadth_and_profit_factor_are_inclusive(self):
        report = self.check()
        for key in ("net_cagr_meets_minimum", "sufficient_closed_trades", "sufficient_closed_instruments", "profit_factor_meets_minimum"):
            self.assertEqual(report["checks"][key], "pass")
        self.assertAlmostEqual(report["net_liquidated_cagr"], .06)

    def test_missing_intraday_evidence_prevents_an_overall_pass(self):
        report = self.check()
        self.assertEqual(report["checks"]["actual_intraday_drawdown_measured"], "inconclusive")
        self.assertEqual(report["decision"], "inconclusive")

    def test_exact_loss_thresholds_reject_and_float_rounding_cannot_bypass(self):
        self.assertFalse(above_loss_limit(.95 - 1, .05))
        self.assertTrue(above_loss_limit(-.049, .05))
        self.assertEqual(self.check(max_drawdown=-.05)["checks"]["closing_drawdown_below_rejection_level"], "fail")
        self.assertEqual(self.check(worst_closing_daily_return=-.02)["checks"]["daily_closing_loss_below_rejection_level"], "fail")

    def test_review_flag_starts_at_four_percent_without_creating_a_failure(self):
        report = self.check(max_drawdown=-.04)
        self.assertTrue(report["closing_drawdown_review_flag"])
        self.assertEqual(report["checks"]["closing_drawdown_below_rejection_level"], "pass")

    def test_short_breadth_and_undefined_profit_factor_are_inconclusive(self):
        report = self.check(completed_trades=29, instruments_with_closed_trades=4, profit_factor=None)
        for key in ("sufficient_closed_trades", "sufficient_closed_instruments", "profit_factor_meets_minimum"):
            self.assertEqual(report["checks"][key], "inconclusive")

    def test_measured_failure_overrides_inconclusive_evidence(self):
        self.assertEqual(self.check(hypothetical_liquidated_return=.04, completed_trades=2)["decision"], "does_not_qualify")
        self.assertEqual(self.check(realized_pnl=0)["checks"]["positive_realized_profit"], "fail")
        self.assertEqual(self.check(permanent_halt_reason="daily loss limit reached")["checks"]["no_permanent_halt"], "fail")

    def test_final_exit_costs_must_be_included_in_cagr(self):
        report = self.check(hypothetical_liquidated_return=.12, total_return=.13)
        self.assertEqual(report["checks"]["net_cagr_meets_minimum"], "fail")

    def test_no_losses_or_nonfinite_profit_factor_is_not_infinite_evidence(self):
        for value in (None, float("inf"), float("nan")):
            with self.subTest(value=value):
                self.assertEqual(self.check(profit_factor=value)["checks"]["profit_factor_meets_minimum"], "inconclusive")


class AccountingTests(TestCase):
    def case(self):
        return {"costs": {"initial_cash": 1000, "slippage_bps": 20, "spread_bps": 10},
                "fills": [{"side": "BUY", "quantity": 2, "reference_open": 100, "fill_price": 100.25,
                           "commission": 1, "signal_reason": "breakout"},
                          {"side": "SELL", "quantity": 2, "reference_open": 80, "fill_price": 89.775,
                           "commission": 1, "signal_reason": "PROTECTIVE_STOP_TOUCH: active stop 90"}],
                "metrics": {"realized_pnl": -22.95, "marked_unrealized_pnl": 0,
                            "final_equity": 977.05, "hypothetical_exit_cost": 0},
                "equity_curve": [{"exposure": .2}, {"exposure": 0}]}

    def attribute(self, case):
        return cost_attribution(case, {"daily_envelopes": [{"cash_at_close": 799}, {"cash_at_close": 977.05}]}, 2, load_policy(POLICY))

    def test_stop_cost_uses_trigger_reference_not_session_open(self):
        result = self.attribute(self.case())
        self.assertAlmostEqual(result["modeled_slippage_cost"], .76)
        self.assertAlmostEqual(result["modeled_half_spread_cost"], .19)
        self.assertAlmostEqual(result["modeled_cost_total"], 2.95)
        self.assertAlmostEqual(result["fixed_fill_path_profit_before_cost_addback"], -20)
        self.assertAlmostEqual(result["profit_required_for_goal"], 123.6)
        self.assertEqual(result["cash_interest_credited"], 0)

    def test_cash_exposure_and_full_cash_sessions_are_reported(self):
        result = self.attribute(self.case())
        self.assertEqual(result["mean_closing_cash_fraction"], .9)
        self.assertEqual(result["fully_in_cash_sessions"], 1)

    def test_inconsistent_fill_model_or_pnl_is_rejected(self):
        for field in ("fill", "pnl"):
            case = self.case()
            if field == "fill":
                case["fills"][0]["fill_price"] += 1
            else:
                case["metrics"]["final_equity"] += 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.attribute(case)


class AuditBoundaryTests(TestCase):
    def test_legacy_windows_posix_and_relative_source_paths_resolve(self):
        expected = Path("backtesting/daily_strategies.py")
        for path in (str(expected), r"C:\old\repo\backtesting\daily_strategies.py", "/home/pi/repo/backtesting/daily_strategies.py"):
            with self.subTest(path=path):
                self.assertEqual(frozen_source_path(path), expected)

    def test_unknown_or_non_source_path_is_rejected(self):
        for path in ("unknown.py", "backtesting/missing.py", "backtesting/../config/research_acceptance.json"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                frozen_source_path(path)

    def test_existing_output_is_never_overwritten_or_scored(self):
        with TemporaryDirectory() as temp, patch("backtesting.goal_fit.simulate_policy") as simulate:
            with self.assertRaises(FileExistsError):
                run_audit(Path(temp))
            simulate.assert_not_called()

    def test_unapproved_policy_stops_before_any_replay(self):
        with TemporaryDirectory() as temp, patch("backtesting.goal_fit.load_policy", side_effect=ValueError("approval")), \
                patch("backtesting.goal_fit.simulate_policy") as simulate:
            with self.assertRaisesRegex(ValueError, "approval"):
                run_audit(Path(temp) / "new")
            simulate.assert_not_called()

    def test_reference_chain_and_source_mutation_stop_before_data_loading(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            r3, r4 = root / "r3.json", root / "r4.json"
            r3.write_text(json.dumps({"selected_on_earlier_years": "vol_latched"}), encoding="utf-8")
            from backtesting.goal_fit import digest
            base = {"reference_sha256": digest(r3), "coverage_mode": "primary",
                    "source_sha256": {"backtesting/daily_strategies.py": "changed"}}
            for bad_chain in (True, False):
                r4.write_text(json.dumps({**base, **({"reference_sha256": "changed"} if bad_chain else {})}), encoding="utf-8")
                with self.subTest(bad_chain=bad_chain), patch("backtesting.goal_fit.R3", r3), patch("backtesting.goal_fit.R4", r4), \
                        patch("backtesting.goal_fit.load_study_data") as loader, patch("backtesting.goal_fit.simulate_policy") as simulate:
                    with self.assertRaises(ValueError):
                        run_audit(root / "output")
                    loader.assert_not_called()
                    simulate.assert_not_called()

    def test_json_report_refuses_nonfinite_output(self):
        with TemporaryDirectory() as temp, self.assertRaises(ValueError):
            write(Path(temp) / "report.json", {"bad": float("nan")})

    def test_saved_stress_scope_is_not_promoted_to_small_account_or_intraday(self):
        metric = {"total_return": .01, "max_drawdown": -.05}
        diag = {"reverse_priority": {"metrics": deepcopy(metric)}, "extra_session_delay_and_50bps_stops": {"metrics": deepcopy(metric)},
                "leave_one_symbol_out": {"AAPL": deepcopy(metric)}}
        result = assess_saved_stresses(diag, load_policy(POLICY), neighbors=False)
        self.assertTrue(all(case["status"] == "fail" for case in result["results"].values()))
        self.assertEqual(result["account_size"], 100000)
        self.assertEqual(result["ten_thousand_dollar_stresses"], "not_run_no_extrapolation")
        self.assertEqual(result["intraday_risk"], "not_measured")

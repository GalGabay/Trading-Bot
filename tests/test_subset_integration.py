"""Offline synthetic window compilation checks, without strategy execution."""

from copy import deepcopy
import json
from pathlib import Path

import pandas as pd

from backtesting.subset_integration import build_window, make_engine
from backtesting.universe import UniverseDataError
from tests.test_diagnostic_bridge import DiagnosticFixture


class SubsetWindowTests(DiagnosticFixture):
    def inputs(self):
        u,s,data=self.make_case()
        streams=deepcopy(u.streams)
        for row in streams:
            row["eligible_for_new_entries_candidate"]=row["instrument_id"]=="ID-A"
        material=[]
        for scenario,release in (("base",201),("delayed_five_sessions",206),("no_credit",None)):
            material.extend(self.make_case(scenario=scenario,release=release)[1].material)
        return dict(proposal=dict(proposed_arms=[dict(id="subset",root_ids=["ID-A"])],
            windows=[dict(id="window",warmup_start="2021-01-01",evaluation_start=self.day(199),end_exclusive=self.day(209))],
            scenarios=["base","delayed_five_sessions","no_credit"]),
            manifest=dict(streams=streams,membership_not_before=self.known(0),effective_feature_resets=[],
                source_selection_bias="SYNTHETIC"),manifest_pin=dict(path="SYNTHETIC",sha256="SYNTHETIC"),
            sessions=u.sessions,data=data,context=self.bars(symbol="SPY",end=209),
            schedules=dict(actions=[],material=material,dividends=[]))

    def test_exact_scenarios_have_distinct_delivery_schedules(self):
        inputs=self.inputs()
        dates=[]
        for scenario in inputs["proposal"]["scenarios"]:
            u,s,data,context=build_window(inputs,"subset","window",scenario)
            dates.append(s.material[0]["share_legs"][0]["modeled_release_at"])
            self.assertEqual(set(data),{"ID-A","ID-B"})
            self.assertEqual(s.entry_instrument_ids,{"ID-A"})
        self.assertEqual(dates,[self.sessions[201].opens_at.isoformat(),self.sessions[206].opens_at.isoformat(),None])

    def test_holdout_window_is_rejected_before_clipping(self):
        inputs=self.inputs()
        inputs["proposal"]["windows"][0]["end_exclusive"]="2025-01-01"
        with self.assertRaisesRegex(UniverseDataError,"development window"):
            build_window(inputs,"subset","window","base")

    def test_unknown_arm_window_and_scenario_are_rejected(self):
        inputs=self.inputs()
        for args in (("other","window","base"),("subset","other","base"),("subset","window","other")):
            with self.subTest(args=args),self.assertRaisesRegex(UniverseDataError,"exact approved"):
                build_window(inputs,*args)

    def test_delivery_outside_window_is_retained_as_unpaid_not_fabricated(self):
        inputs=self.inputs()
        inputs["proposal"]["windows"][0]["end_exclusive"]=self.day(204)
        u,s,data,context=build_window(inputs,"subset","window","delayed_five_sessions")
        leg=s.material[0]["share_legs"][0]
        self.assertIsNone(leg["modeled_release_at"])
        self.assertEqual(leg["release_outside_window"],self.sessions[206].opens_at.isoformat())

    def test_cannot_promote_received_security_into_entry_universe(self):
        inputs=self.inputs()
        inputs["manifest"]["streams"][1]["eligible_for_new_entries_candidate"]=True
        with self.assertRaisesRegex(UniverseDataError,"Only original roots"):
            build_window(inputs,"subset","window","base")

    def test_ended_reference_remains_declared_with_empty_window_history(self):
        inputs=self.inputs()
        inputs["manifest"]["streams"].append(dict(instrument_id="REFERENCE",root_id="ID-A",
            eligible_for_new_entries_candidate=False,parts=[dict(start="2016-01-01",end_exclusive="2017-01-01")]))
        inputs["data"]["REFERENCE"]=inputs["data"]["ID-A"].iloc[:0].copy()
        u,s,data,context=build_window(inputs,"subset","window","base")
        self.assertIn("REFERENCE",u.instrument_ids)
        self.assertTrue(data["REFERENCE"].empty)

    def test_window_clipping_does_not_modify_source_data_or_schedules(self):
        inputs=self.inputs()
        original=deepcopy(inputs["schedules"])
        frame=inputs["data"]["ID-A"].copy(deep=True)
        inputs["proposal"]["windows"][0]["end_exclusive"]=self.day(204)
        build_window(inputs,"subset","window","delayed_five_sessions")
        self.assertEqual(inputs["schedules"],original)
        pd.testing.assert_frame_equal(inputs["data"]["ID-A"],frame)

    def test_factory_uses_the_approved_allocation_and_frozen_controls(self):
        proposal=json.loads(Path('docs/faster_research_scope_proposal.json').read_text(encoding='utf-8'))
        engine=make_engine(dict(proposal=proposal),self.bars(symbol='SPY',end=209),'pessimistic')
        self.assertEqual(engine.limits.max_portfolio_exposure,.70)
        self.assertEqual(engine.limits.max_single_position,.05)
        self.assertEqual(engine.limits.max_positions,20)
        self.assertEqual(engine.protection.max_risk_per_trade,.005)
        self.assertEqual(engine.costs.initial_cash,10000)
        self.assertEqual(engine.costs.slippage_bps,20)
        self.assertEqual(engine.costs.spread_bps,10)
        self.assertEqual(engine.costs.commission_per_order,1)
        self.assertEqual(engine.limits.max_daily_loss,.03)
        self.assertEqual(engine.limits.max_drawdown,.10)

    def test_factory_does_not_construct_an_unapproved_cost_case(self):
        proposal=json.loads(Path('docs/faster_research_scope_proposal.json').read_text(encoding='utf-8'))
        with self.assertRaises(UniverseDataError):
            make_engine(dict(proposal=proposal),self.bars(symbol='SPY',end=209),'optimistic')

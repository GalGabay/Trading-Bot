"""Offline recovery authorization, lifetime accounting and reporting checks."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from backtesting import subset_recovery as recovery
from backtesting.subset_runner import Budget,atomic_json,pin,read


class RecoveryTests(TestCase):
    def setUp(self):
        self.owner=read(recovery.OWNER)
        self.scope=read(recovery.SCOPE)
        self.cases=read(self.scope["original_protocol"]["path"])["ordered_cases"]

    def ledger(self):
        return dict(scope=pin(recovery.OWNER),case_ids=[c["id"] for c in self.cases[3:]],
            original_attempts_consumed=4,lifetime_attempts_limit=25,original_ledger=self.scope["original_ledger"],
            total_seconds=3600,case_seconds=600,max_workers=1,attempts=[],completed=[],
            research_strategy_attempts=0,status="profiling")

    def test_approved_exact_scope_passes(self):
        recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_missing_approval_rejected(self):
        self.owner["owner_approved"]=False
        with self.assertRaises(ValueError):recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_lifetime_limit_cannot_be_raised(self):
        self.owner["lifetime_attempts_limit"]=26
        with self.assertRaises(ValueError):recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_original_attempts_cannot_be_reset(self):
        self.scope["original_attempts_consumed"]=0
        with self.assertRaises(ValueError):recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_extra_retry_cannot_be_added(self):
        self.scope["remaining_ordered_cases"].append(self.cases[3])
        with self.assertRaises(ValueError):recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_case_order_cannot_change(self):
        self.scope["remaining_ordered_cases"].reverse()
        with self.assertRaises(ValueError):recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_only_failed_case_may_be_retried(self):
        self.scope["one_retry_case"]=self.cases[0]
        with self.assertRaises(ValueError):recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_longer_segment_rejected(self):
        self.scope["recovery_segment_seconds"]=7200
        with self.assertRaises(ValueError):recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_longer_case_rejected(self):
        self.scope["case_seconds"]=601
        with self.assertRaises(ValueError):recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_multiple_workers_rejected(self):
        self.owner["max_workers"]=2
        with self.assertRaises(ValueError):recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_automatic_retries_rejected(self):
        self.scope["automatic_retry"]=True
        with self.assertRaises(ValueError):recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_paper_access_rejected(self):
        self.owner["paper_authorized"]=True
        with self.assertRaises(ValueError):recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_reserved_year_access_rejected(self):
        self.owner["heldout_2024_2025_access"]=True
        with self.assertRaises(ValueError):recovery.approved_scope(self.owner,self.scope,self.cases)

    def test_original_stopped_case_files_still_reconcile_with_ledger(self):
        protocol,original=recovery.original_state(self.scope)
        self.assertEqual(len(original["attempts"]),4)
        self.assertEqual(len(original["completed"]),3)
        self.assertEqual(protocol["ordered_cases"],self.cases)

    def test_changed_original_ledger_fails_checksum(self):
        self.scope["original_ledger"]["sha256"]="0"*64
        with self.assertRaises(ValueError):recovery.original_state(self.scope)

    def test_new_recovery_ledger_retains_four_attempt_offset(self):
        recovery.validate_ledger(self.ledger(),self.scope)

    def test_ledger_cannot_drop_original_offset(self):
        ledger=self.ledger();ledger["original_attempts_consumed"]=0
        with self.assertRaises(ValueError):recovery.validate_ledger(ledger,self.scope)

    def test_ledger_cannot_use_original_approval(self):
        ledger=self.ledger();ledger["scope"]=self.owner["original_approval"]
        with self.assertRaises(ValueError):recovery.validate_ledger(ledger,self.scope)

    def test_ledger_cannot_claim_completion_with_missing_cases(self):
        ledger=self.ledger();ledger["status"]="completed"
        with self.assertRaises(ValueError):recovery.validate_ledger(ledger,self.scope)

    def test_reservation_order_and_numbers_checked(self):
        ledger=self.ledger();ledger.update(attempts=[dict(id=self.cases[4]["id"],number=1)],research_strategy_attempts=1)
        with self.assertRaises(ValueError):recovery.validate_ledger(ledger,self.scope)

    def test_completed_results_cannot_exceed_consumed_attempts(self):
        ledger=self.ledger();ledger["completed"]=[dict(id=self.cases[3]["id"])]
        with self.assertRaises(ValueError):recovery.validate_ledger(ledger,self.scope)

    def test_real_budget_persists_lineage_and_consumes_failure(self):
        with TemporaryDirectory() as tmp:
            budget=Budget(Path(tmp)/"budget",pin(recovery.OWNER),self.ledger()["case_ids"],total_seconds=3600)
            budget.state.update(original_attempts_consumed=4,lifetime_attempts_limit=25,original_ledger=self.scope["original_ledger"])
            budget.profile_passed(dict(passed=True))
            budget.reserve(self.cases[3]["id"],dict(path="synthetic",sha256="fixture"))
            budget.stop("synthetic timeout")
            saved=read(budget.path)
            recovery.validate_ledger(saved,self.scope)
            self.assertEqual(saved["original_attempts_consumed"]+len(saved["attempts"]),5)
            with self.assertRaises(ValueError):budget.reserve(self.cases[3]["id"],{})

    def test_combined_stopped_report_keeps_all_failed_attempts(self):
        original=dict(completed=[dict(id=c["id"]) for c in self.cases[:3]])
        ledger=self.ledger();ledger["attempts"]=[dict(id=self.cases[3]["id"])]
        ledger["status"]="stopped"
        execution,combined=recovery.combine(original,ledger,dict(status="stopped"),self.cases)
        self.assertEqual(execution["attempts"],5)
        self.assertEqual(execution["completed"],3)
        self.assertEqual(combined["status"],"stopped")

    def test_combined_completed_report_has_25_attempts_24_unique_cases(self):
        original=dict(completed=[dict(id=c["id"]) for c in self.cases[:3]])
        ledger=self.ledger();ledger.update(attempts=[dict(id=c["id"]) for c in self.cases[3:]],
            completed=[dict(id=c["id"]) for c in self.cases[3:]],status="completed")
        execution,combined=recovery.combine(original,ledger,dict(status="completed"),self.cases)
        self.assertEqual(execution["attempts"],25)
        self.assertEqual(len(combined["completed"]),24)
        self.assertEqual(original["completed"],[dict(id=c["id"]) for c in self.cases[:3]])

    def test_combined_report_rejects_duplicate_completed_case(self):
        original=dict(completed=[dict(id=c["id"]) for c in self.cases[:3]])
        ledger=self.ledger();ledger["completed"]=[dict(id=self.cases[0]["id"])]
        with self.assertRaises(ValueError):recovery.combine(original,ledger,dict(status="stopped"),self.cases)

    def test_report_cannot_substitute_another_run_directory(self):
        with self.assertRaises(ValueError):recovery.report_evidence(Path("other"),{}, {})

    def test_driver_does_not_recreate_existing_output(self):
        with TemporaryDirectory() as tmp,patch.object(recovery,"authority",return_value=(self.scope,{},{})),patch.object(recovery,"OUTPUT",Path(tmp)):
            with self.assertRaisesRegex(ValueError,"no retry"):recovery.run()

    def test_worker_rejects_task_outside_recovery(self):
        with patch.object(recovery,"authority",return_value=(self.scope,{},{})):
            with self.assertRaises(ValueError):recovery.worker(Path("other/task.json"))

    def test_unverified_driver_cannot_start_research(self):
        with TemporaryDirectory(dir=Path.cwd()) as tmp:
            path=Path(tmp)/"proof.json";atomic_json(path,dict(passed=False))
            with self.assertRaisesRegex(ValueError,"verification required"):recovery.authority(path)

    def test_failed_profile_stops_before_any_case_reservation(self):
        with TemporaryDirectory(dir=Path.cwd()) as tmp:
            output=Path(tmp)/"run"
            with patch.object(recovery,"authority",return_value=(self.scope,{},dict(execution=[]))),patch.object(recovery,"OUTPUT",output),patch.object(recovery,"PROOF",recovery.OWNER),patch.object(recovery.runner,"supervise",side_effect=TimeoutError("synthetic profile timeout")):
                with self.assertRaises(TimeoutError):recovery.run()
            state=read(output/"budget/ledger.json")
            self.assertEqual(state["status"],"stopped")
            self.assertEqual(state["attempts"],[])
            self.assertEqual(read(output/"summary.json")["lifetime_attempts"],4)

"""Synthetic/offline schedule and heartbeat checks. Never register OS tasks."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch
import xml.etree.ElementTree as ET

from app.shadow import repeat as R, schedule as S, scheduled as H
from app.shadow.config import ROOT, canonical, load_config, read_json, utc
from app.shadow.repeat_state import controller_lock, save_state, read_state

NS = {"t":"http://schemas.microsoft.com/windows/2004/02/mit/task"}
FAKE_SID = "S-1-5-21-111111111-222222222-333333333-1234"


class ScheduleBase(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.campaign = self.root / "campaign with spaces"
        self.reports = self.root / "reports with spaces"
        self.review = self.root / "review with spaces"
        self.campaign.mkdir()
        self.config = load_config()
        self.repeat_config = R.load_repeat_config(ROOT / "config/shadow_repeat.json")
        self.moment = "2026-10-31T12:00:00+00:00"
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                "app.broker.alpaca_client._AlpacaCredentials.load", "app.broker.alpaca_client.TradingClient"):
            guard = patch(target, side_effect=AssertionError("Network/credentials/trading client forbidden"))
            guard.start()
            self.addCleanup(guard.stop)
        timer = patch.object(R, "clock", return_value=utc(self.moment))
        timer.start()
        self.addCleanup(timer.stop)
        timer = patch.object(H, "now", return_value=self.moment)
        timer.start()
        self.addCleanup(timer.stop)
        report = dict(session="2026-10-30", observed_at="2026-10-31T09:00:00+00:00",
            next_session_open="2026-11-02T14:30:00+00:00",global_blockers=[],signals=[])
        path = self.campaign / "seed.json"
        path.write_text(canonical(report),encoding="utf-8")
        self.state = dict(schema_version=1,status="ready",reason=None,
            created_at=self.moment,expires_at=(datetime.now(timezone.utc)+timedelta(days=30)).isoformat(),
            policy=R.policy(self.config,self.repeat_config),last_session="2026-10-30",
            latest_report=R.pin(path),calendar_checked_at=self.moment,
            calendar=[dict(date=d,open="09:30",close="16:00") for d in
                ("2026-10-30","2026-11-02","2026-11-03","2026-11-04")],
            reserved_requests=0,known_requests=0,collection_attempts=0,calendar_attempts=0,
            pending=None,events=[])
        save_state(self.campaign,self.state)

    def prepare(self, sid=FAKE_SID):
        return S.prepare(self.review,self.campaign,self.reports,sid,"/home/pi/trading-bot","pi")

    def change_manifest(self, **fields):
        path=self.review/"manifest.json"
        manifest=read_json(path)
        manifest.update(fields)
        path.write_text(canonical(manifest),encoding="utf-8")
        return manifest

    def value(self, **fields):
        value=R.status(self.campaign,self.config,self.repeat_config)
        value.update(fields)
        return value

    def event(self, **fields):
        value=dict(id="fixture",phase="finished",started_at="2026-10-31T11:59:00+00:00",
            finished_at=self.moment,issues=[],exit_code=0,controller=self.value())
        value.update(fields)
        if value["phase"] == "started":
            value.pop("finished_at",None)
        return value

    def publish(self, **fields):
        event=self.event(**fields)
        H.publish(self.reports,event,event["phase"])
        return event


class DefinitionTests(ScheduleBase):
    def test_prepared_review_verifies_offline(self):
        self.prepare()
        self.assertTrue(S.verify(self.review)["verified"])
        self.assertEqual(read_state(self.campaign)["reserved_requests"],0)

    def test_windows_principal_is_current_user_interactive_and_least_privilege(self):
        self.prepare()
        root=ET.parse(self.review/"windows-task.xml")
        self.assertEqual(root.findtext(".//t:Principal/t:UserId",namespaces=NS),FAKE_SID)
        self.assertEqual(root.findtext(".//t:LogonType",namespaces=NS),"InteractiveToken")
        self.assertEqual(root.findtext(".//t:RunLevel",namespaces=NS),"LeastPrivilege")

    def test_every_thirty_minutes_and_matching_signin_owner(self):
        self.prepare()
        root=ET.parse(self.review/"windows-task.xml")
        self.assertEqual(root.findtext(".//t:Repetition/t:Interval",namespaces=NS),"PT30M")
        self.assertEqual(root.findtext(".//t:Repetition/t:Duration",namespaces=NS),"P1D")
        self.assertEqual(root.findtext(".//t:LogonTrigger/t:UserId",namespaces=NS),FAKE_SID)

    def test_no_wakeup_overlap_or_unbounded_execution(self):
        self.prepare()
        root=ET.parse(self.review/"windows-task.xml")
        for field,expected in (("WakeToRun","false"),("MultipleInstancesPolicy","IgnoreNew"),
                ("ExecutionTimeLimit","PT5M"),("Hidden","false"),("RunOnlyIfNetworkAvailable","true")):
            self.assertEqual(root.findtext(".//t:"+field,namespaces=NS),expected)

    def test_trigger_end_boundaries_match_campaign(self):
        self.prepare()
        root=ET.parse(self.review/"windows-task.xml")
        self.assertEqual([e.text for e in root.findall(".//t:EndBoundary",NS)],
            [self.state["expires_at"],self.state["expires_at"]])

    def test_hidden_launcher_arguments_include_quoted_review_and_runtime_paths(self):
        self.prepare()
        root=ET.parse(self.review/"windows-task.xml")
        arguments=root.findtext(".//t:Arguments",namespaces=NS)
        for value in (str(self.campaign),str(self.reports),str(self.review)):
            self.assertIn('"'+value+'"',arguments)
        self.assertIn("-WindowStyle Hidden",arguments)
        self.assertEqual(root.findtext(".//t:WorkingDirectory",namespaces=NS),str(ROOT))
        self.assertNotIn("encoding=",(self.review/"windows-task.xml").read_text())

    def test_future_pi_examples_have_no_unsubstituted_tokens_or_windows_paths(self):
        self.prepare()
        service=(self.review/"shadow-observer.service").read_text()
        timer=(self.review/"shadow-observer.timer").read_text()
        self.assertNotIn("@",service+timer)
        self.assertIn("User=pi",service)
        self.assertIn("--review-directory /home/pi/trading-bot/data/shadow/schedule/review",service)
        for expected in ("Restart=no","KillMode=control-group","TimeoutStartSec=300", "ProtectSystem=strict"):
            self.assertIn(expected,service)
        self.assertIn("OnCalendar=*-*-* *:00,30:00",timer)
        self.assertIn("WakeSystem=false",timer)

    def test_invalid_sid_and_pi_inputs_are_rejected(self):
        for sid,pi_root,pi_user in (("name","/home/pi/bot","pi"),(FAKE_SID,"/home/pi/../bot","pi"),
                (FAKE_SID,"/home/pi/bot\nRestart=always","pi"),(FAKE_SID,"/home/pi/bot","root")):
            with self.subTest(sid=sid,pi_root=pi_root,pi_user=pi_user),self.assertRaises(ValueError):
                S.prepare(self.review,self.campaign,self.reports,sid,pi_root,pi_user)

    def test_nonempty_review_is_never_overwritten(self):
        self.prepare()
        before=(self.review/"manifest.json").read_bytes()
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual((self.review/"manifest.json").read_bytes(),before)

    def test_changed_artifact_or_source_is_rejected(self):
        self.prepare()
        artifact=self.review/"windows-task.xml"
        artifact.write_text(artifact.read_text()+" ",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"changed"):S.verify(self.review)

    def test_source_checksum_change_is_rejected(self):
        manifest=self.prepare()
        manifest["sources"][0]["sha256"]="bad"
        self.change_manifest(sources=manifest["sources"])
        with self.assertRaisesRegex(ValueError,"changed"):S.verify(self.review)

    def test_wrong_repository_task_and_platform_are_rejected(self):
        original=self.prepare()
        for field,value in (("repository","other"),("task_name","other"),("platform","other")):
            with self.subTest(field=field):
                self.change_manifest(**original)
                self.change_manifest(**{field:value})
                with self.assertRaises(ValueError):S.verify(self.review)

    def test_extra_source_or_output_path_is_rejected(self):
        original=self.prepare()
        for field in ("sources","artifacts"):
            self.change_manifest(**original)
            changed=[*original[field],dict(path=str(self.root/"outside"),sha256="unused")]
            self.change_manifest(**{field:changed})
            with self.subTest(field=field),self.assertRaises(ValueError):S.verify(self.review)

    def test_duplicate_source_and_output_records_are_rejected(self):
        original=self.prepare()
        for field in ("sources","artifacts"):
            self.change_manifest(**original)
            self.change_manifest(**{field:[*original[field],original[field][0]]})
            with self.subTest(field=field),self.assertRaises(ValueError):S.verify(self.review)

    def test_manifest_cannot_redirect_reports_without_changing_task(self):
        self.prepare()
        self.change_manifest(reports=str(self.root/"unreviewed reports"))
        with self.assertRaises(ValueError):S.verify(self.review)

    def test_manifest_cannot_change_expiry_without_changing_task(self):
        self.prepare()
        self.change_manifest(windows_end_boundary="2099-01-01T00:00:00Z")
        with self.assertRaises(ValueError):S.verify(self.review)

    def test_changed_controller_policy_is_rejected(self):
        self.prepare()
        self.change_manifest(controller_policy="different")
        with self.assertRaisesRegex(ValueError,"differs"):S.verify(self.review)

    def test_install_preflight_refuses_halted_paused_finished_or_running(self):
        self.prepare()
        for state in ("halted","paused","finished","running"):
            with self.subTest(state=state),patch.object(R,"status",return_value=self.value(state=state)):
                with self.assertRaises(ValueError):S.verify(self.review)
                self.assertTrue(S.verify(self.review,require_ready=False)["verified"])

    def test_runtime_preflight_still_refuses_policy_changes(self):
        self.prepare()
        with patch.object(R,"status",return_value=self.value(policy_matches=False)):
            with self.assertRaises(ValueError):S.verify(self.review,require_ready=False)

    def test_linux_manifest_verification_does_not_require_windows_xml(self):
        manifest=self.prepare()
        self.change_manifest(platform="linux",artifacts=[e for e in manifest["artifacts"] if not e["path"].endswith(".xml")])
        self.assertTrue(S.verify(self.review)["verified"])

    def test_prepare_pi_cli_selects_local_nonroot_owner_without_sid(self):
        out=io.StringIO()
        with patch.object(sys,"argv",["schedule","prepare-pi"]),patch.object(S,"prepare") as prepare,redirect_stdout(out):
            self.assertEqual(S.main(),0)
        self.assertEqual(prepare.call_args.kwargs["platform"],"linux")
        self.assertIsNone(prepare.call_args.args[3])


class HeartbeatTests(ScheduleBase):
    def test_missing_heartbeat_is_attention_without_credentials(self):
        value=H.health(self.reports)
        self.assertEqual(value["exit_code"],3)
        self.assertIn("no_heartbeat_or_missing_artifact",value["issues"])

    def test_successful_wrapper_tick_uses_real_waiting_controller_without_requests(self):
        before=(self.campaign/"campaign.json").read_bytes()
        with patch.object(R,"client_for",side_effect=AssertionError("Transport forbidden")):
            event=H.tick(self.campaign,self.reports,self.config,self.repeat_config)
        self.assertEqual(event["exit_code"],0)
        self.assertEqual(H.health(self.reports)["exit_code"],0)
        self.assertEqual((self.campaign/"campaign.json").read_bytes(),before)
        self.assertEqual(len(list((self.reports/"runs").glob("*.json"))),2)

    def test_halted_policy_and_quality_problems_map_to_errors(self):
        cases=[self.value(state="halted"),self.value(state="running"),self.value(policy_matches=False),
            self.value(latest_global_blockers=["market_context_unavailable"])]
        for value in cases:
            with self.subTest(value=value):self.assertEqual(H.controller_health(value)[1],2)

    def test_paused_finished_and_unavailable_symbols_map_to_attention(self):
        for value in (self.value(state="paused"),self.value(state="finished"),self.value(latest_unavailable_symbols=["AAA"])):
            with self.subTest(value=value):self.assertEqual(H.controller_health(value)[1],3)

    def test_wrapper_does_not_tick_when_policy_differs(self):
        with patch.object(R,"status",return_value=self.value(policy_matches=False)),patch.object(R,"tick") as tick:
            event=H.tick(self.campaign,self.reports,self.config,self.repeat_config)
        tick.assert_not_called()
        self.assertIn("policy_changed",event["issues"])

    def test_stopped_tick_records_only_exception_type_and_no_secret(self):
        with patch.object(R,"tick",side_effect=OSError("FAKE_SECRET_SENTINEL")):
            event=H.tick(self.campaign,self.reports,self.config,self.repeat_config)
        self.assertEqual(event["exit_code"],2)
        self.assertEqual(event["error_type"],"OSError")
        for path in self.reports.rglob("*.json"):
            self.assertNotIn("FAKE_SECRET_SENTINEL",path.read_text())

    def test_keyboard_interrupt_is_durably_reported(self):
        with patch.object(R,"tick",side_effect=KeyboardInterrupt()):
            event=H.tick(self.campaign,self.reports,self.config,self.repeat_config)
        self.assertEqual(event["issues"],["tick_stopped"])
        self.assertEqual(H.health(self.reports)["exit_code"],2)

    def test_stale_success_is_attention(self):
        self.publish(finished_at="2026-10-31T10:00:00+00:00",started_at="2026-10-31T09:59:00+00:00")
        value=H.health(self.reports)
        self.assertEqual(value["exit_code"],3)
        self.assertIn("heartbeat_stale",value["issues"])

    def test_staleness_does_not_downgrade_hard_error(self):
        self.publish(finished_at="2026-10-31T10:00:00+00:00",started_at="2026-10-31T09:59:00+00:00",issues=["tick_stopped"],exit_code=2)
        self.assertEqual(H.health(self.reports)["exit_code"],2)

    def test_current_started_run_is_attention(self):
        self.publish(phase="started",exit_code=None)
        self.assertIn("tick_in_progress",H.health(self.reports)["issues"])

    def test_old_started_run_is_interrupted_or_stuck(self):
        self.publish(phase="started",exit_code=None,started_at="2026-10-31T11:00:00+00:00")
        self.assertIn("interrupted_or_stuck",H.health(self.reports)["issues"])

    def test_future_heartbeat_is_error(self):
        self.publish(finished_at="2026-10-31T13:00:00+00:00")
        self.assertIn("heartbeat_clock_inconsistent",H.health(self.reports)["issues"])

    def test_finish_cannot_precede_start(self):
        self.publish(started_at="2026-10-31T11:59:00+00:00",finished_at="2026-10-31T11:58:00+00:00")
        self.assertEqual(H.health(self.reports)["exit_code"],2)

    def test_unrecognized_event_phase_or_exit_code_is_error(self):
        for fields in (dict(phase="garbage"),dict(exit_code=99)):
            with self.subTest(fields=fields):
                event=self.event(**fields)
                path=self.reports/("test"+str(len(list(self.reports.glob('*')))))
                path.mkdir(parents=True)
                H.publish(path,event,event["phase"])
                self.assertEqual(H.health(path)["exit_code"],2)

    def test_json_nonobject_is_reported_as_unreadable(self):
        event=self.publish()
        pointer=read_json(self.reports/"latest.json")
        path=Path(pointer["path"])
        path.write_text("[]",encoding="utf-8")
        pointer["sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
        H.atomic_json(self.reports/"latest.json",pointer)
        self.assertEqual(H.health(self.reports)["exit_code"],2)

    def test_corruption_and_pointer_escape_are_rejected(self):
        self.publish()
        pointer=read_json(self.reports/"latest.json")
        Path(pointer["path"]).write_text("{}",encoding="utf-8")
        self.assertIn("heartbeat_unreadable",H.health(self.reports)["issues"])
        outside=self.root/"outside.json"
        outside.write_text(canonical(self.event()),encoding="utf-8")
        H.atomic_json(self.reports/"latest.json",S.reference(outside))
        self.assertIn("heartbeat_unreadable",H.health(self.reports)["issues"])

    def test_new_launcher_failure_is_error_and_later_success_supersedes_it(self):
        self.publish(started_at="2026-10-31T11:59:00+00:00")
        H.atomic_json(self.reports/"launcher_failure.json",dict(failed_at="2026-10-31T11:59:30+00:00",issue="failed"))
        self.assertIn("launcher_failed",H.health(self.reports)["issues"])
        self.publish(id="later",started_at=self.moment)
        self.assertNotIn("launcher_failed",H.health(self.reports)["issues"])
        self.assertTrue((self.reports/"launcher_failure.json").exists())

    def test_bad_launcher_report_is_error(self):
        self.reports.mkdir()
        (self.reports/"launcher_failure.json").write_text("{",encoding="utf-8")
        self.assertEqual(H.health(self.reports)["exit_code"],2)

    def test_expired_campaign_does_not_appear_healthy(self):
        value=self.value(expires_at="2026-10-31T11:00:00+00:00")
        self.publish(controller=value)
        self.assertIn("campaign_expired",H.health(self.reports)["issues"])

    def test_failed_atomic_pointer_write_retains_previous_pointer(self):
        self.publish()
        before=(self.reports/"latest.json").read_bytes()
        with patch.object(H.os,"replace",side_effect=OSError("disk full")),self.assertRaises(OSError):
            H.atomic_json(self.reports/"latest.json",{})
        self.assertEqual((self.reports/"latest.json").read_bytes(),before)
        self.assertFalse(list(self.reports.glob(".heartbeat-*.tmp")))

    def test_started_report_failure_prevents_controller_tick(self):
        with patch.object(H,"publish",side_effect=OSError("disk full")),patch.object(R,"tick") as tick,self.assertRaises(OSError):
            H.tick(self.campaign,self.reports,self.config,self.repeat_config)
        tick.assert_not_called()

    def test_wrapper_lock_prevents_a_second_tick(self):
        with controller_lock(self.reports/"wrapper_lock"),patch.object(R,"tick") as tick,self.assertRaises(ValueError):
            H.tick(self.campaign,self.reports,self.config,self.repeat_config)
        tick.assert_not_called()

    def test_event_phases_are_immutable(self):
        self.publish()
        with self.assertRaises(ValueError):self.publish(exit_code=2,issues=["different"])

    def cli(self,*args):
        out,err=io.StringIO(),io.StringIO()
        with patch.object(sys,"argv",["scheduled",*args,"--directory",str(self.campaign),
                "--report-directory",str(self.reports)]),redirect_stdout(out),redirect_stderr(err):
            result=H.main()
        return result,out.getvalue(),err.getvalue()

    def test_status_cli_does_not_load_controller_or_config(self):
        with patch.object(H,"load_config",side_effect=AssertionError("config load")),patch.object(R,"tick") as tick:
            code,out,_=self.cli("status","--json")
        self.assertEqual(code,3)
        self.assertIn("no_heartbeat",out)
        tick.assert_not_called()

    def test_runtime_preflight_failure_prevents_tick(self):
        with patch.object(S,"verify",side_effect=ValueError("FAKE_SECRET_SENTINEL")),patch.object(H,"tick") as tick:
            code,out,err=self.cli("tick","--review-directory",str(self.review))
        self.assertEqual(code,2)
        self.assertNotIn("FAKE_SECRET_SENTINEL",out+err)
        tick.assert_not_called()

    def test_reviewed_runtime_directory_mismatch_prevents_tick(self):
        self.prepare()
        with patch.object(S,"verify",return_value=dict(campaign=str(self.root/"other"))),patch.object(H,"tick") as tick:
            code,_,_=self.cli("tick","--review-directory",str(self.review))
        self.assertEqual(code,2)
        tick.assert_not_called()

    def test_stale_threshold_rejects_invalid_values(self):
        for value in ("0","29","1441"):
            with self.subTest(value=value):self.assertEqual(self.cli("status","--stale-minutes",value)[0],2)


@skipUnless(os.name=="nt","Windows PowerShell boundary checks require Windows")
class WindowsDeploymentTests(ScheduleBase):
    @classmethod
    def setUpClass(cls):
        completed=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
            '[Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],capture_output=True,text=True,timeout=15)
        if completed.returncode: raise RuntimeError('Could not read current Windows SID')
        cls.owner_sid=completed.stdout.strip()

    def setUp(self):
        super().setUp()
        # Child Python verification has the same offline boundary, inherited
        # through PYTHONPATH. No broker reads or real keys are permitted.
        self.child_guard=self.root/'child_guard'
        self.child_guard.mkdir()
        (self.child_guard/'sitecustomize.py').write_text(
            "import socket\ndef deny(*a,**k): raise RuntimeError('Offline deployment test')\n"
            "socket.socket.connect=socket.socket.connect_ex=socket.create_connection=deny\n"
            "try:\n import app.broker.alpaca_client as b\n b._AlpacaCredentials.load=deny\n b.TradingClient=deny\n"
            "except ModuleNotFoundError: pass\n",encoding='utf-8')

    def harness(self,case,relative=False):
        env=dict(os.environ)
        env['PYTHONPATH']=os.pathsep.join([str(self.child_guard),str(ROOT)])
        path=self.review.name if relative else str(self.review)
        command=['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-File',
            str(ROOT/'tests/helpers/shadow_deployment_harness.ps1'),'-Repository',str(ROOT),
            '-ReviewDirectory',path,'-Case',case]
        if relative:command+=['-OutsideDirectory',str(self.root)]
        completed=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
        if completed.returncode: self.fail('Harness failed: '+completed.stderr)
        lines=[s for s in completed.stdout.splitlines() if s.startswith('SHADOW_HARNESS_RESULT=')]
        self.assertEqual(len(lines),1,completed.stdout+completed.stderr)
        result=json.loads(lines[0].split('=',1)[1])
        self.assertEqual(result['real_mutations'],0)
        return result

    def test_install_registers_only_through_mocked_boundary(self):
        self.prepare(self.owner_sid)
        result=self.harness('install')
        self.assertFalse(result['failed'],result['message'])
        self.assertEqual(result['calls'],['register'])

    def test_install_whatif_never_calls_registration(self):
        self.prepare(self.owner_sid)
        result=self.harness('installWhatIf')
        self.assertFalse(result['failed'],result['message'])
        self.assertEqual(result['calls'],[])

    def test_install_refuses_existing_named_task(self):
        self.prepare(self.owner_sid)
        result=self.harness('installExisting')
        self.assertTrue(result['failed'])
        self.assertEqual(result['calls'],[])

    def test_install_refuses_another_windows_owner(self):
        self.prepare()
        result=self.harness('installBadSid')
        self.assertTrue(result['failed'])
        self.assertIn('principal',result['message'])
        self.assertEqual(result['calls'],[])

    def test_install_refuses_changed_review(self):
        self.prepare(self.owner_sid)
        (self.review/'windows-task.xml').write_text('<changed/>',encoding='utf-8')
        result=self.harness('installBadReview')
        self.assertTrue(result['failed'])
        self.assertEqual(result['calls'],[])

    def test_install_refuses_halted_campaign(self):
        self.prepare(self.owner_sid)
        self.state['status']='halted'
        save_state(self.campaign,self.state)
        result=self.harness('installNotReady')
        self.assertTrue(result['failed'])
        self.assertEqual(result['calls'],[])

    def test_install_resolves_relative_review_from_calling_directory(self):
        self.prepare(self.owner_sid)
        result=self.harness('installRelative',relative=True)
        self.assertFalse(result['failed'],result['message'])
        self.assertEqual(result['calls'],['register'])

    def test_remove_absent_task_is_noop(self):
        result=self.harness('removeAbsent')
        self.assertFalse(result['failed'])
        self.assertEqual(result['calls'],[])

    def test_remove_refuses_other_repository_task(self):
        result=self.harness('removeForeign')
        self.assertTrue(result['failed'])
        self.assertEqual(result['calls'],[])

    def test_remove_refuses_running_task_without_explicit_stop(self):
        result=self.harness('removeRunning')
        self.assertTrue(result['failed'])
        self.assertEqual(result['calls'],[])

    def test_remove_whatif_does_not_stop_or_unregister(self):
        result=self.harness('removeWhatIf')
        self.assertFalse(result['failed'])
        self.assertEqual(result['calls'],[])

    def test_remove_stopped_task_preserves_campaign(self):
        before=(self.campaign/'campaign.json').read_bytes()
        result=self.harness('remove')
        self.assertFalse(result['failed'],result['message'])
        self.assertEqual(result['calls'],['unregister'])
        self.assertEqual((self.campaign/'campaign.json').read_bytes(),before)

    def test_explicit_stop_removes_running_task_only_at_mocked_boundary(self):
        result=self.harness('removeForce')
        self.assertFalse(result['failed'],result['message'])
        self.assertEqual(result['calls'],['stop','unregister'])

    def launcher(self,exit_code=None):
        repository=self.root/'launcher repository'
        repository.mkdir()
        if exit_code is not None:
            # A temporary Python launcher and a tiny inert module exercise the
            # real PowerShell entry point without importing the trading app.
            scripts=repository/'.venv/Scripts'
            scripts.mkdir(parents=True)
            shutil.copy2(sys.executable,scripts/'python.exe')
            shutil.copy2(Path(sys.prefix)/'pyvenv.cfg',repository/'.venv/pyvenv.cfg')
            package=repository/'app/shadow'
            package.mkdir(parents=True)
            (repository/'app/__init__.py').write_text('',encoding='utf-8')
            (package/'__init__.py').write_text('',encoding='utf-8')
            (package/'scheduled.py').write_text(
                "import json,sys\nprint(json.dumps(sys.argv))\nraise SystemExit("+str(exit_code)+")\n",encoding='utf-8')
        env=dict(os.environ)
        env['PYTHONPATH']=str(self.child_guard)
        command=['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-File',
            str(ROOT/'deploy/windows/Invoke-ShadowObserver.ps1'),'-Repository',str(repository),
            '-Campaign',str(self.campaign),'-ReportDirectory',str(self.reports),'-ReviewDirectory',str(self.review)]
        return subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)

    def test_launcher_missing_python_writes_fixed_local_failure(self):
        result=self.launcher()
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        failure=read_json(self.reports/'launcher_failure.json')
        self.assertEqual(failure['issue'],'launcher_or_observer_failed')
        self.assertNotIn('Exception',canonical(failure))

    def test_launcher_success_preserves_arguments_with_spaces(self):
        result=self.launcher(0)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse((self.reports/'launcher_failure.json').exists())
        logs=list((self.reports/'launcher_logs').glob('*.stdout.log'))
        self.assertEqual(len(logs),1)
        args=json.loads(logs[0].read_text(encoding='utf-16'))
        self.assertIn(str(self.campaign),args)
        self.assertIn(str(self.review),args)
        self.assertIn(str(self.reports),args)

    def test_launcher_attention_exit_is_not_rewritten_as_failure(self):
        result=self.launcher(3)
        self.assertEqual(result.returncode,3,result.stdout+result.stderr)
        self.assertFalse((self.reports/'launcher_failure.json').exists())

    def test_launcher_observer_failure_writes_fallback_and_keeps_logs(self):
        result=self.launcher(2)
        self.assertEqual(result.returncode,2)
        self.assertTrue((self.reports/'launcher_failure.json').exists())
        self.assertEqual(len(list((self.reports/'launcher_logs').glob('*.log'))),2)

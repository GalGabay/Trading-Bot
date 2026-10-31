"""Render reviewable OS definitions and verify their local preflight; no install."""

import argparse
from datetime import datetime
import getpass
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from app.shadow import repeat
from app.shadow.config import ROOT, canonical, digest, load_config, read_json
from app.shadow.store import write_once

DEFAULT_REVIEW = ROOT / "data/shadow/schedule/review"
TASK_NAME = "TradingBot-ShadowObserver"


def reference(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def source_paths():
    return [ROOT / name for name in ("app/shadow/schedule.py", "app/shadow/scheduled.py",
        "deploy/windows/Invoke-ShadowObserver.ps1", "deploy/windows/Install-ShadowObserver.ps1",
        "deploy/windows/Remove-ShadowObserver.ps1", "deploy/systemd/shadow-observer.service.in",
        "deploy/systemd/shadow-observer.timer.in")]


def windows_xml(campaign, reports, user, expires_at, review_directory):
    if not re.fullmatch(r"S-1-[0-9-]+", user):
        raise ValueError("Windows task owner must be the current user's explicit SID")
    namespace = "http://schemas.microsoft.com/windows/2004/02/mit/task"
    ET.register_namespace("", namespace)
    def child(parent, name, text=None, **attributes):
        item = ET.SubElement(parent, "{" + namespace + "}" + name, attributes)
        if text is not None:
            item.text = str(text)
        return item
    task = ET.Element("{" + namespace + "}Task", dict(version="1.4"))
    info = child(task, "RegistrationInfo")
    child(info, "Description", "TradingBot shadow-only observer | " + str(ROOT))
    triggers = child(task, "Triggers")
    daily = child(triggers, "CalendarTrigger")
    repetition = child(daily, "Repetition")
    child(repetition, "Interval", "PT30M")
    child(repetition, "Duration", "P1D")
    child(repetition, "StopAtDurationEnd", "false")
    child(daily, "StartBoundary", datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat())
    child(daily, "EndBoundary", expires_at)
    child(daily, "Enabled", "true")
    child(child(daily, "ScheduleByDay"), "DaysInterval", 1)
    logon = child(triggers, "LogonTrigger")
    child(logon, "EndBoundary", expires_at)
    child(logon, "Enabled", "true")
    child(logon, "UserId", user)
    principal = child(child(task, "Principals"), "Principal", id="ObserverUser")
    child(principal, "UserId", user)
    child(principal, "LogonType", "InteractiveToken")
    child(principal, "RunLevel", "LeastPrivilege")
    settings = child(task, "Settings")
    for name, value in (('MultipleInstancesPolicy','IgnoreNew'),
            ('DisallowStartIfOnBatteries','false'),('StopIfGoingOnBatteries','false'),
            ('AllowHardTerminate','true'),('StartWhenAvailable','true'),
            ('RunOnlyIfNetworkAvailable','true'),('AllowStartOnDemand','true'),
            ('Enabled','true'),('Hidden','false'),('RunOnlyIfIdle','false'),
            ('WakeToRun','false'),('ExecutionTimeLimit','PT5M'),('Priority','7')):
        child(settings, name, value)
    action = child(child(task, "Actions", Context="ObserverUser"), "Exec")
    child(action, "Command", str(Path(os.environ.get('SystemRoot', 'C:/Windows')) /
        'System32/WindowsPowerShell/v1.0/powershell.exe'))
    arguments = ['-NoLogo','-NoProfile','-NonInteractive','-WindowStyle','Hidden',
        '-ExecutionPolicy','Bypass','-File',str(ROOT/'deploy/windows/Invoke-ShadowObserver.ps1'),
        '-Repository',str(ROOT),'-Campaign',str(campaign),'-ReportDirectory',str(reports),
        '-ReviewDirectory',str(review_directory)]
    child(action, "Arguments", subprocess.list2cmdline(arguments))
    child(action, "WorkingDirectory", str(ROOT))
    ET.indent(task, space="  ")
    # Task Scheduler receives a .NET Unicode string via -Xml/COM. Omitting an
    # encoding declaration avoids asking its parser to reinterpret it as UTF-8.
    return ET.tostring(task, encoding="unicode") + "\n"


def prepare(review_directory, campaign, reports, user, pi_root, pi_user, *, platform="windows"):
    if not re.fullmatch(r"/[A-Za-z0-9._/-]+", pi_root) or '..' in PurePosixPath(pi_root).parts or pi_root == '/':
        raise ValueError("Pi repository must be an absolute POSIX path without spaces, '..' or shell syntax")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]*", pi_user) or pi_user == "root":
        raise ValueError("Choose an explicit non-root Pi account")
    if platform == 'linux' and (Path(pi_root).resolve() != ROOT or
            campaign.resolve() != ROOT/'data/shadow/repeat' or reports.resolve() != ROOT/'data/shadow/schedule'):
        raise ValueError("Prepare Pi units on that host with its actual repository and default runtime directories")
    if platform == 'linux' and not re.fullmatch(r"/[A-Za-z0-9._/-]+",str(Path(review_directory).resolve())):
        raise ValueError("Pi review directory must be an absolute path without spaces or systemd syntax")
    config = load_config()
    repeat_config = repeat.load_repeat_config(ROOT/'config/shadow_repeat.json')
    value = repeat.status(campaign, config, repeat_config)
    if not value['policy_matches']:
        raise ValueError("Campaign version differs; definitions were not prepared")
    review_directory = Path(review_directory).resolve()
    if review_directory.exists() and any(review_directory.iterdir()):
        raise ValueError("Review directory is not empty; preserve it and use a fresh version")
    review_directory.mkdir(parents=True, exist_ok=True)
    artifacts = []
    if platform == 'windows':
        xml = review_directory/'windows-task.xml'
        write_once(xml, windows_xml(campaign.resolve(), reports.resolve(), user, value['expires_at'],review_directory))
        artifacts.append(reference(xml))
    for name in ('shadow-observer.service','shadow-observer.timer'):
        text = (ROOT/'deploy/systemd'/(name+'.in')).read_text(encoding='utf-8')
        text = text.replace('@USER@',pi_user).replace('@REPO@',pi_root.rstrip('/'))
        text = text.replace('@REVIEW@',str(review_directory) if platform=='linux' else pi_root.rstrip('/')+'/data/shadow/schedule/review')
        path = review_directory/name
        write_once(path,text)
        artifacts.append(reference(path))
    manifest = dict(schema_version=1,platform=platform,prepared_at=repeat.clock().isoformat(),task_name=TASK_NAME,
        repository=str(ROOT),campaign=str(campaign.resolve()),reports=str(reports.resolve()),
        windows_user_sid=user,windows_logon='current user logged in; locked screen supported',
        interval_minutes=30,wake_computer=False,windows_end_boundary=value['expires_at'],
        pi_root=pi_root.rstrip('/'),pi_user=pi_user,pi_status='future template; not validated on Pi',
        controller_policy=digest(repeat.policy(config,repeat_config)),
        sources=[reference(path) for path in source_paths()],artifacts=artifacts,
        installed=False,executed=False)
    write_once(review_directory/'manifest.json',canonical(manifest)+'\n')
    return manifest


def verify(review_directory, *, require_ready=True):
    directory = Path(review_directory).resolve()
    manifest = read_json(directory/'manifest.json')
    if (manifest.get('schema_version') != 1 or manifest.get('repository') != str(ROOT)
            or manifest.get('task_name') != TASK_NAME):
        raise ValueError("Reviewed task belongs to another repository or version")
    expected_sources = {str(p.resolve()) for p in source_paths()}
    sources = manifest.get('sources')
    if (not isinstance(sources,list) or len(sources) != len(expected_sources) or
            any(not isinstance(entry,dict) or set(entry) != {'path','sha256'} for entry in sources) or
            {entry['path'] for entry in sources} != expected_sources):
        raise ValueError("Reviewed source set differs")
    if manifest.get('platform') not in ('windows','linux'):
        raise ValueError('Unsupported review platform')
    names = ['shadow-observer.service','shadow-observer.timer']
    if manifest['platform'] == 'windows':
        names.append('windows-task.xml')
    expected_artifacts = {str(directory/name) for name in names}
    artifacts = manifest.get('artifacts')
    if (not isinstance(artifacts,list) or len(artifacts) != len(expected_artifacts) or
            any(not isinstance(entry,dict) or set(entry) != {'path','sha256'} for entry in artifacts) or
            {entry['path'] for entry in artifacts} != expected_artifacts):
        raise ValueError("Reviewed output paths differ")
    for entry in [*manifest['sources'],*manifest['artifacts']]:
        if reference(entry['path']) != entry:
            raise ValueError("A source or generated definition changed; prepare a fresh review")
    config = load_config()
    repeat_config = repeat.load_repeat_config(ROOT/'config/shadow_repeat.json')
    if digest(repeat.policy(config,repeat_config)) != manifest['controller_policy']:
        raise ValueError("Controller version/config/environment differs from review")
    value = repeat.status(Path(manifest['campaign']), config, repeat_config)
    if not value['policy_matches'] or (require_ready and (value['state'] != 'ready' or value['action']['action'] in ('finished','halted'))):
        raise ValueError("Campaign is not ready; inspect its status before scheduling")
    # Inspect the principal in addition to the exact artifact/source checksums.
    if manifest['platform'] == 'windows':
        tree = ET.parse(directory/'windows-task.xml')
        ns={'t':'http://schemas.microsoft.com/windows/2004/02/mit/task'}
        if manifest['windows_end_boundary'] != value['expires_at']:
            raise ValueError("Reviewed Windows expiry differs from campaign")
        expected = ET.fromstring(windows_xml(Path(manifest['campaign']),Path(manifest['reports']),
            manifest['windows_user_sid'],value['expires_at'],directory))
        # The original local StartBoundary remains fixed across later review
        # dates. Every other XML element must match the current manifest/code.
        start_path = './/t:CalendarTrigger/t:StartBoundary'
        start = tree.findtext(start_path,namespaces=ns)
        local_start = datetime.fromisoformat(start)
        if local_start.tzinfo is not None or repeat.utc(local_start.astimezone()) >= repeat.utc(value['expires_at']):
            raise ValueError("Reviewed Windows start boundary is invalid")
        expected.find(start_path,ns).text = start
        if ET.tostring(tree.getroot()) != ET.tostring(expected):
            raise ValueError("Reviewed Windows task differs from manifest settings/paths")
    return dict(verified=True,task_name=TASK_NAME,repository=str(ROOT),
        campaign=manifest['campaign'],expires_at=value['expires_at'],installed=False,
        message='Local files/preflight only; no scheduler registration or requests')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','prepare-pi','verify'))
    parser.add_argument('--review-directory',type=Path,default=DEFAULT_REVIEW)
    parser.add_argument('--directory',type=Path,default=repeat.DEFAULT_DIRECTORY)
    parser.add_argument('--report-directory',type=Path,default=ROOT/'data/shadow/schedule')
    parser.add_argument('--windows-user',help='Explicit Windows user SID; no password')
    parser.add_argument('--runtime',action='store_true',help='Verify version pins while allowing halted/finished state for reporting/recovery')
    parser.add_argument('--pi-root',help='Future Pi repository; defaults to /home/pi/trading-bot for Windows review')
    parser.add_argument('--pi-user',help='Non-root Pi owner; defaults to pi for Windows review')
    args=parser.parse_args()
    try:
        if args.command in ('prepare','prepare-pi'):
            linux = args.command == 'prepare-pi'
            if not linux and args.windows_user is None:
                raise ValueError('prepare requires --windows-user with your current Windows SID')
            pi_root = args.pi_root or (str(ROOT) if linux else '/home/pi/trading-bot')
            pi_user = args.pi_user or (getpass.getuser() if linux else 'pi')
            value=prepare(args.review_directory,args.directory,args.report_directory,args.windows_user,
                pi_root,pi_user,platform='linux' if linux else 'windows')
            print(f"Prepared {'Pi units' if linux else 'Windows task and future Pi units'}: {args.review_directory}\nNothing installed or started.")
        else:
            print(canonical(verify(args.review_directory,require_ready=not args.runtime)))
        return 0
    except (ValueError,KeyError,TypeError,OSError,RuntimeError) as exc:
        print(f"Schedule preparation stopped ({type(exc).__name__}); inspect local campaign/review inputs.",file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())

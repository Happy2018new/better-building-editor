"""Archive actual read-only closeout results; do not change processes or task settings."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '.runtime/round-20261023'
OUT = ROOT / 'docs/evidence/r28-closeout-v1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--final-readback', type=Path, required=True)
args = parser.parse_args()
final_path = args.final_readback.resolve()
assert final_path.is_relative_to(RUN.resolve())
inputs = [RUN / 'precloseout-v1.json', RUN / 'scope-freeze-v1.json', final_path]
reports = [json.loads(path.read_bytes()) for path in inputs]
assert digest(inputs[0].read_bytes()) == '4d163a2907c6d3b7b03d0048c7f0c5578eb39b2c39189838f92c9125e1574f51'
assert digest(inputs[1].read_bytes()) == 'c9d64dbabae710f3ddee71cd60aa3cb94a1f6dbeb0898694a33dfed93dd64c88'
assert datetime(2026, 10, 22, 23, 40, tzinfo=timezone.utc) <= datetime.fromisoformat(reports[-1]['at']) < datetime(2026, 10, 23, tzinfo=timezone.utc)
for report in reports:
    assert report['read_only'] and report['processes_stopped_by_this_script'] == 0
    assert not report['registry_read_errors']
    assert not report['actual_live_MC']
    assert not report['matching_live_managed_sessions']
    assert not report['live_R28_watcher_observer_candidates']
    assert not report['CIM_records_not_live_or_tombstone_qualified']
    assert len(report['R28_sessions']) == 27
    assert all(row['registry_state'] == 'stopped' and not row['exact_live_processes'] for row in report['R28_sessions'])
    frozen = report['frozen_b70_runtime_check']
    assert frozen['files'] == 3712 and frozen['exact_raw_Git_matches'] == 2645
    assert len(frozen['only_Git_CRLF_conversions']) == 1067 and not frozen['other_changes']
    assert report['water_explicit_source_contract_check']['files'] == 39
    assert not report['water_explicit_source_contract_check']['changes']
    assert not report['hibernation_executed_by_this_script']
    repos = report['repositories']
    assert len(repos) == 3 and [r['branch'] for r in repos] == ['dev', 'main', 'main']
    assert not any(r['tracked_status'] for r in repos)
    assert repos[1]['head'] == 'ca1035615410db75aeaffdd7e8f3feb73ae6c0f0'
    assert repos[2]['head'] == '58534dc5956848b4e6e5bcba97ad7112e2802388'
    task = report['hibernation_task']
    assert task['TaskName'] == 'Codex-BBE-R28-Hibernate-20261023'
    assert task['State'] == 3 and task['Enabled'] and task['TriggerEnabled']
    assert task['StartBoundary'] == '2026-10-23T08:00:00+08:00'
    assert task['Execute'].lower() == r'c:\windows\system32\shutdown.exe'
    assert task['Arguments'] == '/h'
    assert not task['StartWhenAvailable'] and task['WakeToRun']
    assert not task['DisallowStartIfOnBatteries'] and not task['StopIfGoingOnBatteries']

assert not OUT.exists()
OUT.mkdir()
for path in inputs + [RUN / 'readback_closeout_r28_v1.py', Path(__file__)]:
    shutil.copyfile(path, OUT / path.name)
power = subprocess.run(['powercfg.exe', '/a'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
assert power.returncode == 0
(OUT / 'powercfg-a.stdout.bin').write_bytes(power.stdout)
(OUT / 'powercfg-a.stderr.bin').write_bytes(power.stderr)
export = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
    "Export-ScheduledTask -TaskName 'Codex-BBE-R28-Hibernate-20261023'"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
(OUT / 'hibernation-task.xml').write_bytes(export.stdout)
final = reports[-1]
local_time = datetime.fromisoformat(final['at']).astimezone(timezone(timedelta(hours=8)))
receipt = {
    'at': final['at'], 'time_Beijing': local_time.isoformat(),
    'input_sha256': {path.name: digest(path.read_bytes()) for path in inputs},
    'registry_rows_checked': final['registry_rows_checked'], 'owned_R28_sessions_all_stopped': 27,
    'actual_live_MC': 0, 'matching_live_managed_sessions': 0, 'R28_watcher_observer_candidates': 0,
    'CIM_zero_resource_tombstones': len(final['zero_resource_CIM_tombstones']),
    'frozen_runtime_files': 3712, 'raw_Git_byte_matches': 2645,
    'valid_UTF8_CRLF_only_differences': 1067, 'other_runtime_changes': 0,
    'explicit_water_contract_files': 39, 'explicit_water_contract_changes': 0,
    'three_tracked_worktrees_clean_before_this_archive_commit': True,
    'game_runtime_source': 'b70ce7bf13ad6a4472f2b089ac812c162b174861',
    'hibernation_task_ready': True, 'hibernation_trigger_Beijing': '2026-10-23T08:00:00+08:00',
    'hibernation_observed': False, 'processes_stopped_by_archive_script': 0,
    'qualification_changed_by_archive': False, 'manual_issues_closed': 0,
}
(OUT / 'root-review.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf8')
(OUT / 'README.md').write_text(
    '# R28最终只读收尾\n\n'
    + local_time.strftime('北京时间 %Y-%m-%d %H:%M:%S')
    + ' 的最终读回及两个早期检查点保持原字节。三次均无存活MC、受管会话或本轮watcher／observer；'
    '27个R28会话均stopped。CIM零资源墓碑不是存活实例。3712项运行源核对分列2645项Git原字节与'
    '1067项仅CRLF转换，其他差异为零；显式水39项不变，不宣称完整传递／资源／GPU闭包。\n\n'
    '三个受跟踪工作区在新增本收尾归档前干净；历史untracked和用户probe未清理。原收集器只读，'
    '完整命令行未保存；归档脚本不停止进程、不修改任务、不调用资格工具。08:00+08休眠任务再次读回就绪并导出XML，'
    '不代表已观察到休眠。powercfg原始输出保留，需按Windows系统编码读取。\n\n'
    '脚本保留主仓.runtime路径假设，不能从此目录直接盲跑。新增人工关闭0，旧异常退出记录不改写，'
    '本归档不增加功能或验证资格。\n', encoding='utf8')
entries = []
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        data = path.read_bytes()
        entries.append({'path': path.relative_to(OUT).as_posix(), 'bytes': len(data), 'sha256': digest(data)})
(OUT / 'index.json').write_text(json.dumps({'entries': entries, 'hibernation_observed': False}, indent=2, sort_keys=True) + '\n', encoding='utf8')
print(json.dumps({'completed': True, 'files': len(entries) + 1,
                  'final_time_Beijing': local_time.isoformat(), 'hibernation_observed': False,
                  'index_sha256': digest((OUT / 'index.json').read_bytes())}))

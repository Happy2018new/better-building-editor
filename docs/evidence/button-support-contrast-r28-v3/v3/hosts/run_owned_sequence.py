"""One already-launched granted owner: configure, audits, six stages, ordinary stop."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNER = 'r28-button-support-contrast-v3'


def main():
    launch = json.loads((HERE / 'launch/report.json').read_bytes())
    assert launch['source_unchanged'] is True and launch['launch_exit_code'] == 0 and launch['owner'] == OWNER
    grant = json.loads((HERE / 'root-review-and-slot-v1.json').read_bytes())
    assert grant['passed'] and datetime.now(timezone.utc) < datetime.fromisoformat(grant['cutoff_utc'])
    receipt = HERE / 'sequence-receipt.json'
    assert not receipt.exists()
    records = []
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', MCDEV_ALLOW_USER_FOREGROUND='0')

    def run(label, script, arguments=(), require_success=True):
        command = [sys.executable, '-B', '-X', 'utf8', str(HERE / script)] + list(arguments)
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=300)
        (HERE / (label + '-stdout.txt')).write_bytes(result.stdout)
        (HERE / (label + '-stderr.txt')).write_bytes(result.stderr)
        records.append({'label': label, 'command': command, 'returncode': result.returncode})
        receipt.write_text(json.dumps(records, indent=2) + '\n', encoding='utf8')
        print(json.dumps({'label': label, 'returncode': result.returncode}), flush=True)
        if require_success:
            assert result.returncode == 0, label

    try:
        run('configure-live', 'configure.py', ('--session', launch['session_file']))
        run('audit-before', 'audit_restore.py', ('--phase', 'before'))
        try:
            run('diagnostic', 'run_support_runtime.py', ('--config', str(HERE / 'live-config.json')))
        finally:
            try:
                run('audit-after1', 'audit_restore.py', ('--phase', 'after1'), require_success=False)
            finally:
                run('audit-after2', 'audit_restore.py', ('--phase', 'after2'), require_success=False)
    finally:
        try:
            run('ordinary-stop', 'stop_owned.py', require_success=False)
        finally:
            try:
                run('watcher-close', 'close_final_watch.py', require_success=False)
            finally:
                run('independent-release', 'independent_release.py', require_success=False)
    assert all(row['returncode'] == 0 for row in records), records


if __name__ == '__main__':
    main()

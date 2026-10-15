"""One normal close, then exact observer exit and stopped-registry finalization."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

os.environ['OPENBLAS_NUM_THREADS'] = '1'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EVIDENCE = ROOT / '.runtime/water-r21-depth-cache-ab-v1'
OWNER = 'water-r20-depth-cache-ab-v1'
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
import instances
from _session import load_session, process_identity


def main(args):
    assert args.scheduled_by_root
    session = load_session(args.session, OWNER, live=False)
    ready = json.loads((EVIDENCE / 'launch-ready.json').read_bytes())
    for key in ('id', 'owner', 'session_file', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'):
        assert ready[key] == session[key]
    observer = json.loads((EVIDENCE / 'exit-watcher.json').read_bytes())
    assert observer['identity'] and process_identity(observer['pid']) == observer['identity']
    report = {'schema': 1, 'session': session['id'], 'owner': OWNER,
        'one_normal_close_only': True, 'force': False, 'window_activation': False,
        'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'normal_close_started': time.time(), 'exact_exits_observed': False, 'finalized': False}
    target = HERE / 'normal-close.json'
    with target.open('x', encoding='ascii') as handle:
        handle.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    try:
        closed = instances.stop(session, force=False)
        report['normal_close_returned_state'] = closed['state']
    except Exception:
        report['normal_close_error'] = traceback.format_exc()
    deadline = time.monotonic() + 60.
    while time.monotonic() < deadline:
        try:
            exact = json.loads((EVIDENCE / 'process-exits.json').read_bytes())
        except (OSError, json.JSONDecodeError):
            time.sleep(.2)
            continue
        if exact['completed']:
            assert exact['session'] == session['id'] and exact['owner'] == OWNER
            assert all(exact['processes'][kind]['pid'] == session[kind + '_pid']
                       and exact['processes'][kind]['identity'] == session[kind + '_identity']
                       and exact['processes'][kind]['state'] == 'exited' for kind in ('game', 'mcdk'))
            report['exact_exits_observed'] = True
            report['exact_exit_receipt'] = exact
            break
        time.sleep(.2)
    if report['exact_exits_observed']:
        assert all(process_identity(session[kind + '_pid']) != session[kind + '_identity']
                   for kind in ('game', 'mcdk'))
        # Both retained handles have signaled; this only finalizes the registry/junction.
        finalized = instances.stop(load_session(args.session, OWNER, live=False), force=False)
        report['finalized'] = finalized['state'] == 'stopped' and not finalized['ready']
    report['finished'] = time.time()
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps({key: report.get(key) for key in ('exact_exits_observed', 'finalized', 'normal_close_error')}))
    return 0 if report['exact_exits_observed'] and report['finalized'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--scheduled-by-root', action='store_true')
    raise SystemExit(main(parser.parse_args()))

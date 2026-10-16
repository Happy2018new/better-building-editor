"""Reuse the reviewed launch transport for the existing five cyan controls."""
import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
TRANSPORT = HERE / 'launch_native_book_attached_v3_amendment.py'
TRANSPORT_SHA256 = 'b8fe49d8c6f6feea9483eb417b454ce012a07435c21d88e1e6c816ec220a0ab3'
assert hashlib.sha256(TRANSPORT.read_bytes()).hexdigest() == TRANSPORT_SHA256

import launch_native_book_attached_v3_amendment as transport
import probe_context_hidden_v1 as hidden

transport.attached = SimpleNamespace(base=hidden, verify=hidden.verify,
                                     PROJECT=hidden.PROJECT, OWNER=hidden.OWNER)
transport.HOST_SHA256 = 'baca5f6372a4031543b9a294cb97df8ed9ff822605c88cd83e239d4eb3eb30c2'
transport.OUTPUT = HERE / 'context-hidden-v1-launch-amendment-v1'
WATCHER = hidden.ROOT / 'tools/watch_owned_disabled_skin_assert_r20.py'
WATCHER_STATUS = hidden.ROOT / '.runtime/disabled-skin-watch-r20-v2/status.json'
transport.EXPECTED[WATCHER] = '704cc3de732c3315d046dbcee393d72cb34fd60f232e16f64978b3e61f9cad89'
transport.EXPECTED[hidden.ROOT / 'tools/verify_debug_blueprints.py'] = '73b725a0bb14d354ae0e6648578c24f8fe2de622ba98a1d4eae39d14737b89f9'
transport_preflight = transport.preflight


def preflight():
    result = transport_preflight()
    status = json.loads(WATCHER_STATUS.read_bytes())
    now = datetime.now(timezone.utc)
    age = (now - datetime.fromisoformat(status['checked_at'])).total_seconds()
    covered = any(hidden.OWNER == item or item.endswith('*') and len(item) > 1 and
                  hidden.OWNER.startswith(item[:-1]) for item in status['owners'])
    assert covered and 0 <= age <= 60 and now < datetime.fromisoformat(status['until'])
    assert status['host_sha256'] == transport.EXPECTED[WATCHER]
    result.update(transport_sha256=TRANSPORT_SHA256,
        entry_sha256=hidden.sha(Path(__file__)),
        watcher={'owner_covered': covered, 'checked_at': status['checked_at'],
                 'age_seconds': age, 'until': status['until'],
                 'host_sha256': status['host_sha256']})
    return result


transport.preflight = preflight


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    check = sub.add_parser('preflight')
    check.add_argument('--output', type=Path)
    start = sub.add_parser('launch')
    start.add_argument('--scheduled-by-root', action='store_true', required=True)
    args = parser.parse_args()
    if args.action == 'preflight':
        receipt = preflight()
        if args.output:
            transport.write(args.output, receipt)
        print(json.dumps(receipt, ensure_ascii=True), flush=True)
    else:
        sys.exit(transport.launch())

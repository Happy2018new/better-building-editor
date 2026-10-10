"""One owned native batch captures nondefault entity data; it does not certify rendering."""
import argparse
import json
import sys
import time
from pathlib import Path

from verify_debug_blueprints import Client, return_value, write_json

ROOT = Path(__file__).resolve().parents[1]


def execute(client, code, client_side=False):
    response = client.call('execute_code', {'code': code, 'is_client': client_side, 'direct_return': True})
    if response.get('isError'):
        raise RuntimeError(response)
    value = return_value(response)
    return json.loads(value) if isinstance(value, str) else value


def replicated_palettes(client, code, timeout=12):
    deadline = time.monotonic() + timeout
    while True:
        result = execute(client, code, True)
        if result.get('ready'):
            return result
        if time.monotonic() >= deadline:
            raise RuntimeError('Native appearance client replication timed out: %r' % result.get('pending'))
        time.sleep(.15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--frame-rotations', action='store_true', help='Observe eight documented angles in each filled frame')
    args = parser.parse_args()
    evidence = {'schema': 1, 'completed': False,
                'scope': 'Native player-placed nondefault data and actual client palettes, not visual acceptance'}
    try:
        with Client(timeout=30) as client:
            try:
                evidence['setup'] = execute(client, (ROOT / 'tools/p0_entity_appearance_setup.py').read_text(encoding='utf8'))
                execute(client, 'import sys\nsys._p0_entity_appearance_rows=%r\n_result=True' % evidence['setup']['rows'], True)
                read_code = (ROOT / 'tools/p0_entity_appearance_read.py').read_text(encoding='utf8')
                evidence['before_fill'] = replicated_palettes(client, read_code)
                write_json(args.output, evidence)
                evidence['filled'] = execute(client, (ROOT / 'tools/p0_entity_appearance_fill.py').read_text(encoding='utf8'))
                if args.frame_rotations:
                    evidence['frame_rotations'] = execute(client,
                        (ROOT / 'tools/p0_entity_appearance_rotations.py').read_text(encoding='utf8'))
                execute(client, 'import sys\nsys._p0_entity_appearance_rows=%r\n_result=True' % evidence['filled']['rows'], True)
                evidence['client'] = replicated_palettes(client, read_code)
                evidence['completed'] = True
            finally:
                prior_error = sys.exc_info()[0]
                cleanup_errors = []
                try:
                    evidence['final_server_snapshot'] = execute(client,
                        'import json,sys\n_result=json.dumps(getattr(sys,"_p0_entity_appearances",None))')
                except Exception as cleanup_error:
                    cleanup_errors.append('final_server_snapshot: %s' % cleanup_error)
                try:
                    saved = execute(client, 'import sys\n_result=hasattr(sys,"_p0_entity_appearances")')
                    if saved:
                        execute(client, (ROOT / 'tools/p0_entity_appearance_cleanup.py').read_text(encoding='utf8'))
                    evidence['native_cleaned'] = True
                except Exception as cleanup_error:
                    cleanup_errors.append('native_fixture: %s' % cleanup_error)
                try:
                    execute(client, 'import sys\n'
                        'for name in ("_p0_entity_appearance_rows","_p0_entity_appearance_palettes",'
                        '"_p0_entity_appearance_entities"):\n'
                        ' if hasattr(sys,name):delattr(sys,name)\n_result=True', True)
                    evidence['client_cleaned'] = True
                except Exception as cleanup_error:
                    cleanup_errors.append('client_state: %s' % cleanup_error)
                if cleanup_errors:
                    evidence['cleanup_errors'] = cleanup_errors
                    evidence['completed'] = False
                    if prior_error is None:
                        raise RuntimeError('Native appearance cleanup failed: ' + '; '.join(cleanup_errors))
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)
    print(json.dumps({'evidence': str(args.output.resolve()), 'completed': evidence['completed'],
                      'native_cleaned': evidence.get('native_cleaned')}))


if __name__ == '__main__':
    main()

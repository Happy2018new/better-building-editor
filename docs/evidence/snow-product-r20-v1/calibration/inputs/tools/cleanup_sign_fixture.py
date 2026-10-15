"""Verify and clear a previous sign probe only within the routed managed world."""
import argparse
import json
from pathlib import Path

from verify_debug_blueprints import Client, write_json
from verify_native_entity_appearances import execute
from verify_native_sign_fields import CLEANUP
from verify_sign_visuals import NATIVE_RESTORE_PLAYER


STATUS = '''import json,sys
_result=json.dumps({'native_sign_probe':hasattr(sys,'_native_sign_probe'),
 'environment_probe':hasattr(sys,'_context_environment_saved')})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = {'completed': False, 'restored': False}
    try:
        with Client(timeout=30) as client:
            report['before'] = execute(client, STATUS)
            if report['before']['native_sign_probe']:
                report['player'] = execute(client, NATIVE_RESTORE_PLAYER)
                report['native'] = execute(client, CLEANUP)
                assert report['native']['cleaned'], report['native']
            report['after'] = execute(client, STATUS)
            report['client'] = execute(client, '''import json,sys
_result=json.dumps({'blueprint_probe':hasattr(sys,'_blueprint_qa_saved'),
 'visual_probe':hasattr(sys,'_blueprint_visual_saved'),
 'options_probe':hasattr(sys,'_neighbor_visual_options_saved')})
''', True)
            report['restored'] = not any(report['after'].values()) and not any(report['client'].values())
            report['completed'] = True
            assert report['restored'], report
    finally:
        write_json(args.output, report)
    print(json.dumps(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

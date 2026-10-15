"""Recover this diagnostic's exact missing-NORMAL modal, then restore its fixture."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import dismiss_owned_disabled_skin_assert as dismiss

OWNER = 'root-shelf-r20-mesh-inputs-v1'
CONTROL = ROOT/'.runtime/shelf-mesh-inputs-r21-start-v1'
READY = json.loads((CONTROL/'start-summary.json').read_bytes())
assert READY['owner'] == OWNER


def exact_missing_normal(row):
    return row['pid'] == READY['game_pid'] and all(value in row.get('text', '') for value in (
        'Mesh missing vertex field NORMAL required by shader. Skipping draw.',
        'mce::ShaderBase::checkVertexFormat', 'ShaderBase.cpp @ 118'))


dismiss.known_disabled_skin_assertion = exact_missing_normal
sys.argv = [__file__, '--session', READY['session_file'], '--owner', OWNER,
            '--receipt', str(CONTROL/'missing-normal-dismissal.json')]
if dismiss.main() != 0:
    raise RuntimeError('The diagnostic modal remains; no cleanup dispatched')

os.environ.update(MCDEV_SESSION_FILE=READY['session_file'], MCDEV_OWNER=OWNER,
                  MCDEV_ALLOW_USER_FOREGROUND='1')
import probe_liquid_pose_channel as native
import probe_native_palette_body_r16 as body

result = {'diagnostic_failure': 'missing NORMAL vertex field', 'restored': False,
          'actions': {}, 'errors': []}
with native.Client(timeout=40) as client:
    for label, code, server in (
            ('client', native.CLEAN_CLIENT, False), ('world', native.CLEAN_WORLD, True),
            ('environment', native.RESTORE_ENVIRONMENT, True),
            ('workspace', body.RESTORE_WORKSPACE, False)):
        try:
            result['actions'][label] = native.run(client, code, server)
        except Exception as error:
            result['errors'].append(label+': '+repr(error))
        native.write(CONTROL/'delayed-restoration.json', result)
result['restored'] = not result['errors']
native.write(CONTROL/'delayed-restoration.json', result)
print(json.dumps(result))

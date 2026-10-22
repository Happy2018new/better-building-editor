"""Independent read-only session audit around the unchanged frozen T04 driver."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROJECT = ROOT / '.runtime/projects/r28-button-support-contrast-v3'
OWNER = 'r28-button-support-contrast-v3'
sys.path[:0] = [str(PROJECT / '.agents/skills/pyreact-debugging/scripts'), str(PROJECT / 'tools')]
import verify_transform_runtime_r23 as base
from verify_debug_blueprints import BlueprintCheck, Client
from frozen_guard import verify
from lifecycle_helpers import handles, memory

CODE = '''import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory();cam=factory.CreateCamera(api.GetLevelId())
assert not s.busy and s.edit_job is None and s.io_job is None
assert not s.projection_active and not b.preparing_entity and not b.entity and not b.projection_entities
assert not navigator.is_transitioning
markers=[key for key in ('_blueprint_qa_saved','_blueprint_visual_saved','_transform_r23_saved','_transform_missing_r23_saved','_transforms_r27','_strict_cache_r27','_r27_native_pair') if hasattr(sys,key)]
assert not markers,markers
fields=('tool','page','name','view','focus_view','section','solo_layer','focused','box_anchor',
 'canvas_x','canvas_z','paste_origin','paste_pinned','camera_pose','camera_yaw','camera_pitch',
 'zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose','camera_focus_request',
 'camera_reset_animated','progress','direct_mode','origin','opacity','projection_missing',
 'projection_outline','grid')
_result=json.dumps({'session_id':id(s),'editor_id':id(s.editor),'document_id':id(s.editor.document),
 'document':s.editor.document.to_data(),'factory_id':id(b.factory),
 'geometry_override': 'geometry' in b.__dict__,
 'geometry_function_id':id(getattr(b.geometry,'im_func',b.geometry)),
 'fields':dict((key,getattr(s,key)) for key in fields),
 'profiles':dict((key,id(getattr(s,key))) for key in ('liquid_profile','book_profile','portal_profile','item_profile','native_render_profile')),
 'workspace':navigator.contains('modern_projection_workspace'),'top':navigator.top.key if navigator.top else None,
 'performance':dict(s.performance),'camera_pos':cam.GetPosition(),'camera_rot':cam.GetCameraRotation(),
 'pitch_lock':cam.IsModCameraLockPitch(),'yaw_lock':cam.IsModCameraLockYaw(),
 'projection_active':s.projection_active,'actor_count':len(b.projection_entities)+int(bool(b.entity)),
 'markers':markers,'preview_ready':s.ready and not s.preview_pending and not s.tiles.running and not s.tiles.dirty,
 'preview_error':s.preview_error})
'''

parser = argparse.ArgumentParser()
parser.add_argument('--phase', required=True, choices=('before', 'after1', 'after2', 'after3'))
args = parser.parse_args()
output = HERE / ('face-restore-' + args.phase + '.json')
assert not output.exists()
manifest = verify()
binding = base.bind_owned_session(Path(json.loads((HERE / 'launch/report.json').read_bytes())['session_file']), OWNER, PROJECT)
os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '0'
mem = memory()
game_handles = handles(binding['game_pid'])
assert mem['headroom_bytes'] >= 6 * 1024 ** 3
assert game_handles is not None and game_handles < 250000
report = {'phase': args.phase, 'started_at': datetime.now(timezone.utc).isoformat(),
          'owner': OWNER, 'game_pid': binding['game_pid'], 'game_identity': binding['game_identity'],
          'source_commit': manifest['source_commit'],
          'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'read_only': True, 'memory': mem, 'game_handles': game_handles, 'completed': False}
try:
    with Client(timeout=30) as client:
        check = BlueprintCheck(client, output, 30)
        state = check.wait('original preview settled', lambda row: row['preview_ready'] and not row['preview_error'], lambda: check.run(CODE))
    report['state'] = state
    if args.phase != 'before':
        before = json.loads((HERE / 'face-restore-before.json').read_bytes())['state']
        strict_keys = [key for key in state if key not in ('preview_ready', 'camera_rot', 'performance')]
        report['changed_keys'] = [key for key in strict_keys if state[key] != before[key]]
        report['camera_rotation_delta'] = [(state['camera_rot'][i] - before['camera_rot'][i] + 180.) % 360. - 180. for i in range(3)]
        report['camera_rotation_exact'] = state['camera_rot'] == before['camera_rot']
        report['performance_observed'] = {'before': before['performance'], 'after': state['performance'], 'volatile_fields': ['previewWall'], 'reason': 'Restored preview rebuild publishes a fresh measured wall duration; configuration and nonvolatile performance fields remain strict.'}
        assert {k:v for k,v in state['performance'].items() if k!='previewWall'} == {k:v for k,v in before['performance'].items() if k!='previewWall'}
        assert not report['changed_keys'], report['changed_keys']
        assert max(abs(value) for value in report['camera_rotation_delta']) <= .0001
    report['source_unchanged'] = verify() == manifest
    assert report['source_unchanged']
    report['completed'] = True
finally:
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps({key: report.get(key) for key in ('phase', 'completed', 'changed_keys', 'source_unchanged')}))

"""Diagnose book self-rotation with fixed-camera, original native WGC frames.

Uses an already owned session only. This tool neither admits a product nor
changes resource files. The optional frozen pose uses a preinstalled R17 alias.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

from audit_native_coordinates_r15 import LOAD, PROJECT
from audit_native_visual_r15 import save
from probe_book_native_r16 import (BookAudit, BOOK_STATUS, CANDIDATE_SETUP,
                                   CANDIDATE_RESTORE, book_sources, document)
from verify_debug_blueprints import CLIENT


TRACE_START = CLIENT + '''assert not hasattr(sys,'_book_motion_r19')
c=s.book_controls
assert c is not None and not c.pending
saved={'controls':c,'update':c.update,'rows':[],'overflow':False}
sys._book_motion_r19=saved
def traced_update(*args,**kwargs):
 result=saved['update'](*args,**kwargs)
 rows=[]
 for key,entry in sorted(c.registry.items()):
  renderer=entry.get('renderer')
  if renderer is not None:
   rows.append((repr(key),renderer.front,tuple(renderer.ids),tuple(renderer.visible),
                bool(renderer.pending),str(renderer.error or ''),
                tuple(group.model_name if group else None for group in renderer.groups)))
 if len(saved['rows'])<20000:
  saved['rows'].append((time.time(),s.camera_pose,s.camera_depth,c.pending,str(c.error or ''),rows))
 else:saved['overflow']=True
 return result
c.update=traced_update
_result=True
'''
TRACE_STOP = CLIENT + '''saved=sys._book_motion_r19
saved['controls'].update=saved['update']
_result=json.dumps({'rows':saved['rows'],'overflow':saved['overflow']})
del sys._book_motion_r19
'''
TRACE_RESTORE = CLIENT + '''if hasattr(sys,'_book_motion_r19'):
 saved=sys._book_motion_r19
 saved['controls'].update=saved['update']
 del sys._book_motion_r19
_result=True
'''
WORLD_CAMERA = CLIENT + '''cam=b.factory.CreateCamera(b.level)
target=tuple(s.origin[i]+(3.5,3.65,3.5)[i] for i in range(3))
position=tuple(s.origin[i]+(6.3,5.7,-.5)[i] for i in range(3))
rot=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()})
'''
NATIVE_SETUP = '''import json,sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
assert dimension==0
info=factory.CreateBlockInfo(player)
assert not hasattr(sys,'_book_motion_r19_native')
journal=[]
sys._book_motion_r19_native=journal
position=%r
for pos,name in ((tuple(position[i]-(1 if i==1 else 0) for i in range(3)),'minecraft:stone'),
                 (position,'minecraft:enchanting_table')):
 original=info.GetBlockNew(pos,dimension)
 assert original['name']=='minecraft:air',original
 journal.append((pos,original))
 assert info.SetBlockNew(pos,{'name':name,'aux':0},0,dimension,True,False)
 assert info.GetBlockNew(pos,dimension)['name']==name
_result=json.dumps({'journal':journal,'table':info.GetBlockNew(position,dimension),
 'actor':info.GetBlockEntityData(dimension,position)})
'''
NATIVE_RESTORE = '''import sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
info=factory.CreateBlockInfo(player)
if hasattr(sys,'_book_motion_r19_native'):
 for pos,original in reversed(sys._book_motion_r19_native):
  info.SetBlockNew(pos,original,0,dimension,True,False)
  assert info.GetBlockNew(pos,dimension)==original
 del sys._book_motion_r19_native
_result=True
'''


def alias_sources(project, prefix):
    if not prefix:
        return None
    registry = json.loads((project/'resource_pack/models/netease_models.json').read_bytes())
    materials = json.loads((project/'resource_pack/materials/entity.material').read_bytes())['materials']
    result = {'models': {}, 'materials': {}, 'files': {}}
    for family in ('enchanting_table', 'lectern'):
        for suffix in ('', '_world'):
            name = prefix + 'modern_projection_book_' + family + suffix
            model = registry[name]
            material = materials[model['material'] + ':entity_for_skeleton_alpha']
            result['models'][name] = model
            result['materials'][name] = material
            paths = ('resource_pack/' + material['vertexShader'],
                     'resource_pack/' + material['fragmentShader'],
                     'resource_pack/models/' + model['mesh'])
            for path in paths:
                result['files'][path] = hashlib.sha256((project/path).read_bytes()).hexdigest()
    return result


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
    audit = BookAudit(args)
    # This maintained provider derives ROOT from its own installed file. Keep
    # its strict project/session identity check intact when the probe lives in
    # the main checkout and the owned game is an isolated clone.
    provider = args.project/'tools/capture_native_burst.py'
    spec = importlib.util.spec_from_file_location('book_motion_native_burst', provider)
    native_burst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native_burst)
    report = {'schema_version': 1, 'engine': '3.10.0.420447',
              'purpose': 'editor_self_rotation_flicker_diagnostic',
              'product_qualified': False, 'animation_accepted': False,
              'completed': False, 'restored': False, 'cleanup_errors': [],
              'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_before': book_sources(args.project), 'routes': {}}
    data, source = document('enchanting_table')
    report['source_document'] = data
    report['source_actor'] = source
    native_started = False
    try:
        report['candidate_setup'] = audit.execute('candidate_setup', CANDIDATE_SETUP)
        report['loaded'] = audit.execute('load', LOAD % ('production', (), json.dumps(data)))
        audit.settle()
        if args.stage == 'editor':
            audit.view(args.yaw, args.zoom, 0.)
            time.sleep(1.)
            audit.settle()
        else:
            code = (PROJECT % False).replace('s.origin=(0,-57,0)',
                'foot=b.player_position.GetFootPos()\ns.origin=(int(foot[0]),int(foot[1])+32,int(foot[2]))')
            report['projected'] = audit.execute('project', code)
            audit.settle(True)
            report['camera'] = audit.execute('close_camera', WORLD_CAMERA)
            if args.stage == 'native':
                origin = audit.execute('native_origin', CLIENT+'_result=json.dumps(s.origin)')
                audit.execute('stop_for_native', CLIENT+'b.stop_projection()\n_result=True')
                native_started = True
                position = tuple(origin[axis]+3 for axis in range(3))
                report['native_reference'] = audit.execute('native_setup', NATIVE_SETUP % (position,), False)
                time.sleep(1.5)
        prefix = 'r19_book_frozen_' if args.frozen else args.model_prefix
        if prefix:
            assert args.stage == 'editor', 'Alias controls currently trace editor ownership'
            report['alias_sources'] = alias_sources(args.project, prefix)
            report['alias_assignment'] = audit.execute('frozen_alias', CLIENT + '''for table in (s.book_profile.models,s.book_profile.world_models):
 for key,value in tuple(table.items()):table[key]=%r+value
s.book_profile.identity=s.book_profile.identity+(%r,)
s.book_preview.retry()
s.emit('preview')
_result=s.book_profile.identity
''' % (prefix, prefix))
            audit.settle()
        label = args.stage + ('_alias' if args.model_prefix else '_frozen' if args.frozen else '_active')
        row = {'before': audit.execute(label+'_before', BOOK_STATUS), 'frozen': args.frozen,
               'time_source': '10.0 diagnostic alias' if args.frozen else 'TOTAL_REAL_WORLD_TIME',
               'fixed_camera': True}
        report['routes'][label] = row
        expected = prefix+'modern_projection_book_enchanting_table'
        if args.stage == 'editor' and any(group[1] != expected for group in row['before']['book']['groups']):
            raise ValueError('Book control did not reach its requested model: '+expected)
        if args.stage == 'editor':
            row['trace_started'] = audit.execute('trace_start', TRACE_START)
        try:
            row['capture'] = native_burst.capture(args.session, args.owner, args.output/label,
                                     args.capture_helper, args.capture_sha256,
                                     args.duration_ms, 1800, args.max_gap_ms)
        except native_burst.CaptureError as error:
            row['capture'] = error.report
            raise
        if args.stage == 'editor':
            row['trace'] = audit.execute('trace_stop', TRACE_STOP)
        row['after'] = audit.execute(label+'_after', BOOK_STATUS)
        for key in ('camera', 'rotation', 'screen', 'editor_camera', 'editor_depth'):
            if row['before'][key] != row['after'][key]:
                raise ValueError('Fixed book camera changed: '+key)
        report['completed'] = True
    finally:
        if args.stage == 'editor' and 'row' in locals() and 'trace' not in row:
            try:
                row['trace'] = audit.execute('trace_after_failure', TRACE_STOP)
            except Exception as error:
                report['cleanup_errors'].append('Failed capture trace: '+str(error))
        if native_started:
            try:
                report['native_restoration'] = audit.execute('native_restore', NATIVE_RESTORE, False)
            except Exception as error:
                report['cleanup_errors'].append('Native reference restore: '+str(error))
        for label, code in (('trace_restore', TRACE_RESTORE),
                            ('cleanup', CLIENT + '''b.stop_projection()
if navigator.top is not None:navigator.pop()
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(False);cam.LockModCameraYaw(False)
_result=True
'''), ('candidate_restore', CANDIDATE_RESTORE)):
            try:
                report[label] = audit.execute(label, code)
            except Exception as error:
                report['cleanup_errors'].append(label+': '+str(error))
        report['restored'] = not report['cleanup_errors']
        report['source_after'] = book_sources(args.project)
        report['source_unchanged'] = report['source_before'] == report['source_after']
        save(args.output/'report.json', report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'source_unchanged': report['source_unchanged'],
                      'capture': native_burst.summary(row['capture'])}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--capture-helper', required=True, type=Path)
    parser.add_argument('--capture-sha256', required=True)
    parser.add_argument('--duration-ms', type=int, default=17000)
    parser.add_argument('--max-gap-ms', type=int, default=250)
    parser.add_argument('--stage', choices=('editor', 'world', 'native'), default='editor')
    parser.add_argument('--frozen', action='store_true')
    parser.add_argument('--model-prefix', default='')
    parser.add_argument('--yaw', type=float, default=35.)
    parser.add_argument('--zoom', type=float, default=3.)
    args = parser.parse_args()
    run(args)


if __name__ == '__main__':
    main()

"""Five native cyan controls for committed hidden-layer context; never launch."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / '.agents/skills/pyreact-debugging/scripts')]
import probe_liquid_pose_channel as native
from verify_debug_blueprints import CLIENT
from census_intrinsic_glint_ui_r21 import commit_at_boundary, handles_at_boundary, resource_stop
from freeze_intrinsic_glint_project_r21 import fingerprint
from _session import load_session


PROJECT = ROOT / '.runtime/projects/book-r20-context-hidden-v1'
MANIFEST = HERE / 'context-hidden-v1/source-manifest.json'
MANIFEST_SHA256 = '63a8ec78cbf46c7a15d2a9b33331b2a90b9174c419c42c15523e7a0223a4ee63'
SOURCE_DIGEST = 'c13cddcb9789441fd4cf8bf3cf2105cf9fc05095f3a456c85e8909d76e8e059e'
OWNER = 'book-r20-context-hidden-v1'
COMMIT = 'c946307911a205d4c957de1f919ba8308061c2dd'
CAPTURE_SHA256 = 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
EXPECTED_FULL = [4421, 8517, 16709, 20805]

INSTALL = CLIENT + '''assert api.GetEngineVersion()=='3.10.0.420447'
assert not s.busy and s.edit_job is None and s.io_job is None
assert not s.projection_active and not b.preparing_entity
assert not navigator.is_transitioning
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not hasattr(sys,'_context_hidden_r21')
fields=('page','name','view','focus_view','section','solo_layer','focused','box_anchor',
 'canvas_x','canvas_z','paste_origin','paste_pinned','camera_pose','camera_yaw',
 'camera_pitch','zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose',
 'camera_focus_request','camera_reset_animated','progress','direct_mode',
 'origin','opacity','projection_missing','projection_outline','grid')
saved={'editor':s.editor,'fields':dict((key,getattr(s,key)) for key in fields),
 'factory':b.factory,'workspace':navigator.top is not None,'receipts':[]}
sys._context_hidden_r21=saved
class ContextHiddenGeometryReceipt(object):
 def __init__(self,target):self.target=target
 def __getattr__(self,name):return getattr(self.target,name)
 def CombineBlockPaletteToGeometry(self,palette,name,mode=0):
  data=palette.SerializeBlockPalette()
  result=self.target.CombineBlockPaletteToGeometry(palette,name,mode)
  sys._context_hidden_r21['receipts'].append({'name':name,'result':result,'volume':data['volume'],
   'common':repr(data.get('common',{})),'extra':repr(data.get('extra',{})),
   'actor':repr(data.get('actor',{})),
   'materials':[{'material':material,'indices':list(indices)}
    for material,indices in data.get('common',{}).items()]})
  return result
class ContextHiddenFactoryReceipt(object):
 def __init__(self,target):self.target=target
 def __getattr__(self,name):return getattr(self.target,name)
 def CreateBlockGeometry(self,level):return ContextHiddenGeometryReceipt(self.target.CreateBlockGeometry(level))
b.factory=ContextHiddenFactoryReceipt(b.factory)
if navigator.top is not None:navigator.pop()
_result={'engine':api.GetEngineVersion(),'candidate_gate_changed':False}
'''

SERVER = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
factory=api.GetEngineCompFactory()
info=factory.CreateBlockInfo(saved['player'])
dimension=saved['dimension']
origin=tuple(saved['origin'])
def world(pos):return tuple(origin[axis]+pos[axis] for axis in range(3))
def clear(pos):
 current=info.GetBlockNew(world(pos),dimension)
 assert current is not None
 if current['name']!='minecraft:air':
  assert info.SetBlockNew(world(pos),{'name':'minecraft:air','aux':0},0,dimension,True,False)
 assert info.GetBlockNew(world(pos),dimension)['name']=='minecraft:air'
'''
BUILD = SERVER + '''for x in range(3):
 for y in range(3):
  for z in range(3):clear((x,y,z))
for pos in ((1,0,1),(1,1,1)):
 assert info.SetBlockNew(world(pos),{'name':'minecraft:cyan_concrete','aux':0},0,dimension,True,False)
_result=True
'''
LOWER_ONLY = SERVER + "clear((1,1,1))\n_result=True\n"
REMOVE = SERVER + "clear((1,0,1))\nclear((1,1,1))\n_result=True\n"
WORLD_STATE = SERVER + '''_result=json.dumps([{'position':pos,
 'block':info.GetBlockNew(world(pos),dimension)} for pos in ((1,0,1),(1,1,1))])
'''
CLIENT_WORLD = native.CLIENT + '''origin=tuple(sys._liquid_pose_client['origin'])
info=factory.CreateBlockInfo(level)
_result=json.dumps([info.GetBlock(tuple(origin[i]+pos[i] for i in range(3)))
 for pos in ((1,0,1),(1,1,1))])
'''
READ_SOURCE = CLIENT + '''from modern_projection.projection.model import Document
from modern_projection.projection.cell import AIR,make_cell,foreground
origin=tuple(sys._liquid_pose_client['origin'])
high=tuple(value+2 for value in origin)
palette=factory.CreateBlock(level).GetBlockPaletteBetweenPos(origin,high,False)
assert palette is not None
raw=palette.SerializeBlockPalette()
assert tuple(raw['volume'])==(3,3,3),raw['volume']
nonair=dict((material,list(indices)) for material,indices in raw['common'].items() if material!=AIR)
assert nonair=={('minecraft:cyan_concrete',0):[4,13]},nonair
assert not raw.get('extra') and not raw.get('actor'),raw
document=Document((3,3,3))
for pos in ((1,0,1),(1,1,1)):document.set_cell(pos,make_cell(('minecraft:cyan_concrete',0)))
saved=sys._context_hidden_r21
saved['document']=document.to_data()
_result=json.dumps({'document':saved['document'],'native_common':repr(raw['common']),
 'native_extra':repr(raw.get('extra',{})),'native_actor':repr(raw.get('actor',{}))})
'''
LOAD = CLIENT + '''from modern_projection.projection.model import Document
saved=sys._context_hidden_r21
s.tiles.cancel();s.tiles.parts.clear();s.tiles.context=None
s._loaded(Document.from_data(json.loads(json.dumps(saved['document']))))
s.grid=False;s.opacity=1.;s.projection_outline=False
s.section=False;s.solo_layer=False;s.editor.hidden_layers.clear()
s.origin=tuple(sys._liquid_pose_client['origin']);s.projection_missing=False
saved['document_id']=id(s.editor.document);saved['editor_id']=id(s.editor)
s.refresh_preview();s.emit()
_result=True
'''
PROJECT_CODE = CLIENT + '''saved=sys._context_hidden_r21
saved['receipts']=[]
assert id(s.editor)==saved['editor_id'] and id(s.editor.document)==saved['document_id']
assert s.editor.document.to_data()==saved['document']
b.project()
_result=True
'''
TOGGLE = CLIENT + "s.toggle_layer('hide',1)\n_result=True\n"
STATE = CLIENT + '''saved=sys._context_hidden_r21
work=b.projection_work
_result=json.dumps({'preview_ready':s.ready and not s.preview_pending and not s.tiles.running and not s.tiles.dirty,
 'preview_error':s.preview_error,'work_ready':bool(work and work.ready),
 'error':work.error if work else None,'active':s.projection_active,'preparing':bool(b.preparing_entity),
 'parts':b.context_models.get(b.projection_mesh[1],()) if b.projection_mesh else (),
 'hidden':sorted(s.editor.hidden_layers),'document_id':id(s.editor.document),'editor_id':id(s.editor),
 'source_unchanged':s.editor.document.to_data()==saved['document'],
 'same_document':id(s.editor.document)==saved['document_id'] and id(s.editor)==saved['editor_id'],
 'receipts':saved['receipts']})
'''
RESTORE = CLIENT + '''saved=getattr(sys,'_context_hidden_r21',None)
if saved is not None:
 b.stop_projection()
 b.factory=saved['factory']
 s.tiles.cancel();s.editor=saved['editor']
 for key,value in saved['fields'].items():setattr(s,key,value)
 s.model_revision=None;s.camera_reset_revision+=1
 s.refresh_preview();s.emit()
 if saved['workspace'] and navigator.top is None:owner.open_workspace()
 if not saved['workspace'] and navigator.top is not None:navigator.pop()
 del sys._context_hidden_r21
_result=True
'''
CAMERA = native.CAMERA.replace('target=(origin[0]+.5,origin[1]+.5,origin[2]+.5)',
    'target=(origin[0]+1.5,origin[1]+1.,origin[2]+1.5)').replace('offset=(3.,3.,5.)','offset=(3.,2.4,5.)')
CAMERA_CHECK = native.CAMERA_CHECK.replace('target=tuple(axis+.5 for axis in origin)',
    'target=(origin[0]+1.5,origin[1]+1.,origin[2]+1.5)')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    assert sha(MANIFEST) == MANIFEST_SHA256
    frozen = json.loads(MANIFEST.read_bytes())
    assert frozen['files_sha256'] == SOURCE_DIGEST and fingerprint(PROJECT) == frozen['files']
    config = json.loads((PROJECT / '.mcdev.json').read_bytes())
    assert all(config.get(key) is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                                   'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
    templates = (INSTALL, BUILD, LOWER_ONLY, REMOVE, WORLD_STATE, CLIENT_WORLD, READ_SOURCE,
                 LOAD, PROJECT_CODE, TOGGLE, STATE, RESTORE, native.CLIENT + CAMERA,
                 native.CLIENT + CAMERA_CHECK)
    for index, code in enumerate(templates):
        compile(code, 'context_hidden_' + str(index), 'exec')
    return {'schema': 1, 'project': str(PROJECT), 'owner': OWNER, 'commit': COMMIT,
        'source_digest': SOURCE_DIGEST, 'source_manifest_sha256': sha(MANIFEST),
        'host_sha256': sha(Path(__file__)), 'compiled_templates': len(templates),
        'planned_captures': 5, 'game_calls': 0, 'candidate_gate_changed': False,
        'production_qualified': False, 'pixel_acceptance_claimed': False,
        'dependencies': {name: sha(ROOT / 'tools' / name) for name in (
            'probe_liquid_pose_channel.py', 'verify_debug_blueprints.py', 'capture_native_window.py',
            'census_intrinsic_glint_ui_r21.py', 'freeze_intrinsic_glint_project_r21.py')}}


def run(args):
    binding = verify()
    session = load_session(args.session, OWNER, live=True)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    assert not args.output.exists() and sha(args.capture_exe) == CAPTURE_SHA256
    args.output.mkdir(parents=True)
    os.environ.update(MCDEV_SESSION_FILE=str(args.session), MCDEV_OWNER=OWNER, MCDEV_ALLOW_USER_FOREGROUND='1')
    report = {'schema': 1, 'binding': binding, 'created_at': datetime.now(timezone.utc).isoformat(),
        'session': {key: session[key] for key in ('id','owner','game_pid','game_identity')},
        'completed': False, 'restored': False, 'cleanup_errors': [], 'operations': [], 'captures': {},
        'resource_boundaries': [], 'phases': {}, 'pixel_acceptance_claimed': False,
        'production_qualified': False, 'candidate_gate_changed': False}
    started = time.monotonic()

    def persist():
        native.write(args.output / 'report.json', report)

    with native.Client(timeout=20) as client:
        installed = world = camera = environment = False

        def call(label, code, server=False):
            row = {'label': label, 'code': code, 'server': server}
            report['operations'].append(row)
            persist()
            row['result'] = native.run(client, code, server)
            persist()
            return row['result']

        def boundary(label):
            handles, memory = handles_at_boundary(args.session, OWNER), commit_at_boundary()
            report['resource_boundaries'].append({'label': label, 'handles': handles, 'memory': memory})
            persist()
            reason = resource_stop(handles, memory, 200000, 6.)
            if reason or time.monotonic() - started >= 120.:
                raise RuntimeError(reason or 'Cyan control exceeded 120 seconds')

        def replicated(expected):
            deadline = time.monotonic() + 20.
            while True:
                actual = call('independent client world readback', CLIENT_WORLD)
                if actual == [[name, 0] for name in expected]:
                    return actual
                if time.monotonic() >= deadline:
                    raise RuntimeError('Native world replication did not converge: ' + repr(actual))
                time.sleep(.25)

        def settled(projected=False):
            deadline = time.monotonic() + 25.
            while True:
                state = call('public route state', STATE)
                assert state['same_document'] and state['source_unchanged'], state
                if state['preview_error'] or state['error']:
                    raise RuntimeError('Public route failed: ' + repr(state))
                if state['preview_ready'] and (not projected or state['work_ready'] and
                        state['active'] and not state['preparing']):
                    return state
                if time.monotonic() >= deadline:
                    raise RuntimeError('Public route did not settle: ' + repr(state))
                time.sleep(.25)

        def frame(label, state=None):
            boundary(label)
            time.sleep(.7)
            before = call(label + ' camera before', CAMERA_CHECK)
            receipt = native.capture(str(args.session), OWNER, args.output / (label + '.png'), args.capture_exe)
            after = call(label + ' camera after', CAMERA_CHECK)
            assert receipt['reliable'] and before == after
            report['captures'][label] = {'receipt': receipt, 'before': before, 'after': after, 'state': state}
            persist()

        try:
            boundary('before fixture')
            installed = True
            report['installed'] = call('install native receipts only', INSTALL)
            environment = True
            report['environment'] = call('save stable environment', native.ENVIRONMENT, True)
            world = True
            report['world'] = call('prepare independently checked air region', native.PREPARE % 'minecraft:cyan_concrete', True)
            report['near_player'] = call('move to owned platform', native.NEAR_PLAYER, True)
            camera = True
            call('save native camera', native.SAVE % (tuple(report['world']['origin']),))
            call('build two native cyan blocks', BUILD, True)
            replicated(['minecraft:cyan_concrete', 'minecraft:cyan_concrete'])
            report['source'] = call('independent complete native source', READ_SOURCE)
            call('fixed cyan camera', CAMERA)
            frame('native_two')
            call('remove upper native block', LOWER_ONLY, True)
            replicated(['minecraft:cyan_concrete', 'minecraft:air'])
            report['native_lower_world'] = call('native lower server readback', WORLD_STATE, True)
            frame('native_lower')
            call('remove fixture before projection', REMOVE, True)
            replicated(['minecraft:air', 'minecraft:air'])
            call('load source exactly once', LOAD)
            settled()
            for label, hidden in (('full', False), ('hidden', True), ('shown', False)):
                boundary('before ' + label)
                if label != 'full':
                    call('public upper-layer toggle ' + label, TOGGLE)
                    settled()
                call('public projection update ' + label, PROJECT_CODE)
                state = settled(True)
                assert state['hidden'] == ([1] if hidden else []), state
                active = {name: context for name, unused, context in state['parts']}
                receipts = [row for row in state['receipts'] if row['result'] in active]
                assert len(receipts) == 1 and active[receipts[0]['result']], receipts
                materials = receipts[0]['materials']
                assert len(materials) == 1 and materials[0]['material'] == ['minecraft:cyan_concrete',0], materials
                assert sorted(materials[0]['indices']) == ([4421] if hidden else EXPECTED_FULL), materials
                report['phases'][label] = {'state': state, 'active_native_receipts': receipts}
                frame('projected_' + label, state)
            report['completed'] = len(report['captures']) == 5
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
            raise
        finally:
            actions = [('projection_stop', CLIENT + 'b.stop_projection()\n_result=True', False)] if installed else []
            if world:
                actions.append(('world_restore', native.CLEAN_WORLD, True))
            if camera:
                actions.append(('camera_restore', native.CLEAN_CLIENT, False))
            if environment:
                guarded = "import sys\nif hasattr(sys,'_context_environment_saved'):\n" + ''.join(
                    ' ' + line + '\n' for line in native.RESTORE_ENVIRONMENT.splitlines()) + '\n_result=True'
                actions.append(('environment_restore', guarded, True))
            if installed:
                actions.append(('session_restore', RESTORE, False))
            for label, code, server in actions:
                try:
                    result = call(label, code, server)
                    report[label] = result
                    assert not isinstance(result, dict) or result.get('restored') is not False
                except Exception as error:
                    report['cleanup_errors'].append(label + ': ' + str(error))
            report['source_unchanged'] = fingerprint(PROJECT) == json.loads(MANIFEST.read_bytes())['files']
            report['restored'] = not report['cleanup_errors']
            report['elapsed_seconds'] = time.monotonic() - started
            persist()
    print(json.dumps({key: report[key] for key in ('completed','restored','source_unchanged')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('verify')
    command = sub.add_parser('run')
    command.add_argument('--session', required=True, type=Path)
    command.add_argument('--capture-exe', required=True, type=Path)
    command.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.action == 'verify':
        print(json.dumps(verify()))
    else:
        run(args)

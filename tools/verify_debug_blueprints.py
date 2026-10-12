"""Accept built-in blueprints through the owned game's ordinary workspace.

Run with run_live_check.py. This host tool does not start a game, write world
blocks, or persist drafts. Native submission evidence and screenshots are kept
separate: successful Combine calls are not a GPU or per-block visual guarantee.
"""
import argparse
import base64
import hashlib
import io
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
sys.path.insert(0, str(SCRIPTS))
from mcdk import Client, return_value

CLIENT = '''import json,sys,time
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.session is not None, 'Workspace is not initialized'
s=owner.session
b=owner.bridge
'''

INSTALL_PROBE = '''assert not s.busy and s.edit_job is None and s.io_job is None
assert not s.projection_active and not b.preparing_entity, 'Stop the previous projection first'
assert s.pending_confirm is None and s.pending_rename is None and not s.sharing.opened
assert not navigator.is_transitioning, 'Wait for navigation to settle'
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not hasattr(sys,'_blueprint_qa_saved'), 'A previous blueprint probe needs cleanup'
fields=('page','name','view','focus_view','section','solo_layer','focused','box_anchor',
 'canvas_x','canvas_z','paste_origin','paste_pinned','camera_pose','camera_yaw',
 'camera_pitch','zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose',
 'camera_focus_request','camera_reset_animated','progress','direct_mode')
sys._blueprint_qa_saved={'editor':s.editor,'fields':dict((key,getattr(s,key)) for key in fields),
 'factory':b.factory,'workspace':navigator.contains('modern_projection_workspace')}
sys._blueprint_qa_records=[]
sys._blueprint_qa_identity=None
sys._blueprint_qa_nonce=0
sys._blueprint_qa_expected=None
class BlueprintNativeGeometryProbe(object):
 def __init__(self,target):self.target=target
 def __getattr__(self,name):return getattr(self.target,name)
 def CombineBlockPaletteToGeometry(self,palette,name,mode=0):
  data=palette.SerializeBlockPalette()
  record={'fixture':sys._blueprint_qa_identity,'name':name,'mode':mode,
   'nonce':sys._blueprint_qa_nonce,'editor_id':id(s.editor),
   'document_id':id(s.editor.document),
   'volume':data.get('volume'),'common_cells':sum(len(v) for v in data.get('common',{}).values()),
   'extra_cells':sum(len(v) for v in data.get('extra',{}).values()),
   'actor_cells':sum(len(v) for v in data.get('actor',{}).values()),
   'common_materials':len(data.get('common',{})),'extra_materials':len(data.get('extra',{})),
   'submitted_materials':[{'material':value,'indices':list(indices)}
    for value,indices in data.get('common',{}).items()],
   'frame_materials':[{'material':value,'indices':list(indices)}
    for value,indices in data.get('common',{}).items()
    if value[0] in ('minecraft:frame','minecraft:glow_frame') or
       value[0].startswith('modern_projection:preview_item_')],
   'actor_names':sorted(data.get('actor',{})),
   'states':len(data.get('states',{})),'extra_states':len(data.get('extraStates',{}))}
  started=time.time()
  try:
   result=self.target.CombineBlockPaletteToGeometry(palette,name,mode)
   record['result']=result
   return result
  except Exception as error:
   record['error']=str(error)
   raise
  finally:
   record['seconds']=time.time()-started
   sys._blueprint_qa_records.append(record)
class BlueprintGeometryFactoryProbe(object):
 def __init__(self,target):self.target=target
 def __getattr__(self,name):return getattr(self.target,name)
 def CreateBlockGeometry(self,level):
  return BlueprintNativeGeometryProbe(self.target.CreateBlockGeometry(level))
b.factory=BlueprintGeometryFactoryProbe(b.factory)
_result=True
'''

STATUS = '''from modern_projection.projection.cell import actor_data,background,AIR
from modern_projection.projection.visible_actor import render_actor
doc=s.editor.document
t=s.tiles
rows=[{'key':key,'name':part.get('name'),'count':part.get('count'),
 'pending':part.get('pending'),'size':part.get('size'),
 'render_layout':b.model_layouts.get(part.get('name')),
 'signature':part.get('signature'),'current_signature':part.get('signature')==s.preview_signature(),
 'cache_current':part.get('bank') in part.get('cache',{}) and
  part['cache'][part['bank']][0]==part['data'] and
  part['cache'][part['bank']][1]==part.get('name') and
  part.get('source') in part['cache'][part['bank']][2],
 'common_cells':sum(len(v) for v in part['data'][0].values()),
 'extra_cells':sum(len(v) for v in part['data'][1].values()),
 'actor_cells':sum(len(v) for v in part['data'][2].values())}
 for key,part in sorted(t.parts.items()) if key in t.region_owners]
expected=sys._blueprint_qa_expected or {}
document_id=id(doc)
metadata={'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)}
if (expected.get('metadata') == metadata and expected.get('previous_document_id') != document_id and
    expected.get('editor_id') is None):
 expected['editor_id']=id(s.editor)
 expected['document_id']=document_id
 sys._blueprint_qa_expected=expected
current_source=(expected.get('metadata')==metadata and
                expected.get('document_id')==document_id and
                expected.get('editor_id')==id(s.editor))
liquid=getattr(s,'liquid_preview',None)
liquid_controls=getattr(s,'liquid_controls',None)
liquid_state={'enabled':getattr(s,'liquid_profile',None) is not None,
 'owned':liquid is not None and liquid_controls is not None,
 'plan_ready':liquid is not None and liquid.published==liquid.signature(),
 'controls_pending':liquid_controls.pending if liquid_controls is not None else True,
 'groups':len(liquid.groups) if liquid is not None else 0,
 'error':str(liquid.error or liquid_controls.error or getattr(s,'liquid_error',''))
  if liquid is not None and liquid_controls is not None else getattr(s,'liquid_error','')}
_result=json.dumps({'page':s.page,'name':doc.name,'size':doc.size,'blocks':len(doc.blocks),
 'liquid':liquid_state,
 'document_actor_cells':sum(actor_data(v) is not None for p,v in doc.blocks.items()),
 'document_render_actor_cells':sum(bool(render_actor(actor_data(v))) for p,v in doc.blocks.items()),
 'document_background_cells':sum(background(v)!=AIR for p,v in doc.blocks.items()),
 'preview_pending':s.preview_pending,'preview_error':s.preview_error,
 'edit_active':s.edit_job is not None,'io_active':s.io_job is not None,
 'running':t.running,'dirty':len(t.dirty),'mounting':getattr(t,'mounting',False),
 'renderer_active':t.renderer_active,'renderer_age':time.time()-t.last_render,
 'model_revision_current':s.model_revision==s.preview_signature(),
 'metadata':metadata,'expected_metadata':expected.get('metadata'),
 'editor_id':id(s.editor),'document_id':document_id,
 'expected_editor_id':expected.get('editor_id'),'expected_document_id':expected.get('document_id'),
 'current_source':current_source,'all_parts_current':all(row['current_signature'] for row in rows),
 'model_name':s.model_name,'parts':rows,'tile_builds':t.builds,
 'world_actors':len(b.projection_entities)+int(bool(b.entity)),
 'native_calls':[row for row in sys._blueprint_qa_records
                 if row['nonce']==sys._blueprint_qa_nonce and row['editor_id']==id(s.editor) and
                 row['document_id']==document_id]})
'''

RESTORE = '''saved=sys._blueprint_qa_saved
b.factory=saved['factory']
s.tiles.cancel()
s.editor=saved['editor']
for key,value in saved['fields'].items():setattr(s,key,value)
s.pending_confirm=None
s.model_revision=None
s.camera_reset_revision+=1
s.refresh_preview()
s.emit()
del sys._blueprint_qa_saved
del sys._blueprint_qa_identity
del sys._blueprint_qa_nonce
del sys._blueprint_qa_expected
del sys._blueprint_qa_records
_result=True
'''


def walk(node):
    yield node
    for child in node.get('children', ()):
        yield from walk(child)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def source_matches(state, metadata, editor_id, document_id):
    return (state.get('metadata') == metadata and state.get('editor_id') == editor_id and
            state.get('document_id') == document_id and state.get('current_source') and
            state.get('all_parts_current'))


def editor_preview_ready(state, metadata, editor_id, document_id):
    if state.get('preview_error'):
        raise AssertionError('Editor preview failed: %r' % state)
    liquid = state.get('liquid', {})
    if liquid.get('enabled'):
        if liquid.get('error'):
            raise AssertionError('Editor liquid preview failed: %r' % state)
        if not liquid.get('owned') or not liquid.get('plan_ready') or liquid.get('controls_pending', True):
            return False
    current = (source_matches(state, metadata, editor_id, document_id) and
               state['page'] == 'workspace' and not state['preview_pending'] and
               not state['running'] and not state['dirty'] and not state['mounting'] and
               not state['edit_active'] and not state['io_active'] and
               state['model_revision_current'] and
               all(not row['pending'] and row['cache_current'] for row in state['parts']))
    if not current:
        return False
    if not metadata['blocks']:
        return not state['model_name'] and not any(row['name'] for row in state['parts'])
    return (bool(state['model_name'] and state['parts']) and state['renderer_active'] and
            state['renderer_age'] < .5 and
            all(row.get('result') and not row.get('error') for row in state['native_calls']))


class BlueprintCheck:
    def __init__(self, client, output, timeout):
        self.client, self.output, self.timeout = client, output, timeout
        self.bridge_source = (SCRIPTS / '_game_bridge.py').read_text(encoding='utf8')

    def run(self, code):
        response = self.client.call('execute_code', {
            'code': CLIENT + code, 'is_client': True, 'direct_return': True})
        if response.get('isError'):
            raise RuntimeError(response)
        value = return_value(response)
        return json.loads(value) if isinstance(value, str) else value

    def command(self, cmd, node=None):
        payload = {'cmd': cmd, 'seq': uuid.uuid4().hex}
        if node is not None:
            payload['id'] = node
        code = ('scope={}\n'
                'eval(compile(%r,"<blueprint-pyreact>","exec"),scope)\n'
                '_result=json.dumps(scope["pyreact_request"](json.loads(%r),'
                '"modern_projection.pyreact"))' %
                (self.bridge_source, json.dumps(payload)))
        result = self.run(code)
        if not result.get('pyreact_ack') or result.get('error'):
            raise RuntimeError(result)
        return result

    def wait(self, label, predicate, read):
        deadline, last = time.monotonic() + self.timeout, None
        while time.monotonic() < deadline:
            last = read()
            if predicate(last):
                return last
            time.sleep(.2)
        raise TimeoutError('%s: %r' % (label, last))

    def editor_preview(self, label, metadata=None, editor_id=None, document_id=None):
        def ready(state):
            return editor_preview_ready(
                state, metadata if metadata is not None else state['expected_metadata'],
                editor_id if editor_id is not None else state['expected_editor_id'],
                document_id if document_id is not None else state['expected_document_id'])
        self.wait(label, ready, lambda: self.run(STATUS))
        time.sleep(.15)
        return self.wait(label + ' stable', ready, lambda: self.run(STATUS))

    def navigation(self):
        return self.run('_result=json.dumps({"transition":navigator.is_transitioning,'
                        '"open":navigator.contains("modern_projection_workspace"),'
                        '"top":navigator.top.key if navigator.top else None})')

    def refresh(self):
        for name in ('debug_blueprints', 'debug_entity_blueprints', 'debug_blueprint_ui', 'panels', 'ui'):
            path = ROOT / ('behavior_pack/modern_projection/projection/' + name + '.py')
            encoded = base64.b64encode(path.read_bytes()).decode('ascii')
            self.run('import base64\n'
                     'import modern_projection.projection.%s as refreshed\n'
                     'eval(compile(base64.b64decode(%r),%r,"exec"),refreshed.__dict__)\n'
                     '_result=True' % (name, encoded, str(path)))
        self.run('import modern_projection.client_system as client_module\n'
                 'from modern_projection.projection.ui import Workspace\n'
                 'client_module.Workspace=Workspace\n_result=True')
        if self.navigation()['open']:
            self.run('navigator.pop()\n_result=True')
            self.wait('close old workspace', lambda state: not state['open'] and not state['transition'],
                      self.navigation)

    def capture(self, label, tree=None):
        result = self.client.call('capture_game_window', {})
        block = next((item for item in result.get('content', ()) if item.get('type') == 'image'), None)
        if block is None:
            raise RuntimeError('capture_game_window did not return an image: %r' % result)
        payload = base64.b64decode(block['data'])
        extension = '.png' if block.get('mimeType') == 'image/png' else '.jpg'
        path = self.output.parent / (self.output.stem + '_' + label + extension)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        record = {'path': str(path.resolve()), 'bytes': len(payload),
                  'sha256': hashlib.sha256(payload).hexdigest(), 'mime': block.get('mimeType')}
        from PIL import Image, ImageStat
        with Image.open(io.BytesIO(payload)) as image:
            record['size'] = image.size
            record['variance'] = ImageStat.Stat(image.convert('RGB')).var
            if max(record['variance']) <= 1:
                raise AssertionError('The captured game window is blank: %r' % record)
        if tree is not None:
            tree_path = path.with_suffix('.tree.json')
            write_json(tree_path, tree)
            record['tree'] = str(tree_path.resolve())
        return record

    def page(self):
        self.run('owner.open_workspace()\ns.set("page","testing")\n_result=True')
        self.wait('workspace navigation', lambda state: state['open'] and not state['transition'],
                  self.navigation)
        tree = self.wait('testing page mounts',
                         lambda root: any(node.get('type') == 'TestBlueprints' for node in walk(root)),
                         lambda: self.command('dump_tree')['tree'])
        assert self.run('_result=json.dumps(s.page)') == 'testing'
        return self.capture('testing_page', tree)

    def fixture(self, identity):
        started = time.monotonic()
        self.run('from functools import partial\n'
                 'from modern_projection.projection.debug_blueprints import open_blueprint,build\n'
                 'sys._blueprint_qa_identity=%r\n'
                 'sys._blueprint_qa_nonce+=1\n'
                 'expected_doc=build(%r)\n'
                 'sys._blueprint_qa_expected={"metadata":{"name":expected_doc.name,"size":expected_doc.size,"blocks":len(expected_doc.blocks)},"previous_document_id":id(s.editor.document),"editor_id":None}\n'
                 's.set("page","testing")\n'
                 's.confirm("Blueprint acceptance",partial(open_blueprint,s,%r))\n'
                 'assert s.pending_confirm is not None\ns.accept()\n'
                 'assert s.pending_confirm is None\n_result=True' %
                 (identity, identity, identity))

        state = self.editor_preview('preview ' + identity)
        assert state['blocks'] > 0 and state['model_name'] and state['parts'], state
        assert state['world_actors'] == 0, state
        calls = state['native_calls']
        assert calls or all(row['cache_current'] for row in state['parts']), state
        if calls:
            assert all(row.get('result') and not row.get('error') for row in calls), calls
            assert any(row['common_cells'] > 0 and row['states'] > 0 for row in calls), calls
        else:
            assert any(row['common_cells'] > 0 for row in state['parts']), state
        state['native_evidence'] = 'current_source_submission' if calls else 'current_source_retained_geometry'
        if state['document_background_cells']:
            assert any(row['extra_cells'] > 0 for row in state['parts']), state
        if identity.startswith('test.entities.') or identity == 'test.connections.context':
            assert state['document_actor_cells'] > 0, state
        if state['document_render_actor_cells']:
            assert any(row['actor_cells'] > 0 for row in state['parts']), state
        time.sleep(.4)
        tree = self.command('dump_tree')['tree']
        scenes = [node for node in walk(tree) if node.get('type') == 'Scene']
        assert len(scenes) == 1, len(scenes)
        dolls = [node for node in walk(scenes[0]) if node.get('type') == 'PaperDoll']
        assert dolls, 'No native preview surfaces are mounted'
        state.update(fixture=identity, seconds=time.monotonic() - started,
                     paper_dolls=len(dolls), screenshot=self.capture(identity.replace('.', '_'), tree))
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='Evidence JSON; screenshots use the same filename stem')
    parser.add_argument('--refresh', action='store_true', help='Refresh blueprint and UI Python modules in an existing game')
    parser.add_argument('--fixture', action='append', help='Stable fixture key; repeat to select a subset')
    parser.add_argument('--timeout', type=float, default=90, help='Maximum seconds for each asynchronous wait')
    parser.add_argument('--keep-fixture', action='store_true', help='Keep the last blueprint open for manual inspection')
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    evidence = {'schema': 1, 'fixtures': [], 'completed': False,
                'visual_acceptance': 'Screenshots require inspection; submissions do not prove each block model.'}
    installed = False
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, args.timeout)
            evidence['error_logs_before'] = client.call('get_latest_error_logs', {'max_count': 30})
            check.run(INSTALL_PROBE)
            installed = True
            try:
                if args.refresh:
                    check.refresh()
                available = check.run('from modern_projection.projection.debug_blueprints import BLUEPRINTS\n'
                                      '_result=json.dumps([row[0] for row in BLUEPRINTS])')
                identities = args.fixture or available
                assert identities and all(identity in available for identity in identities), identities
                evidence['available'] = available
                evidence['page'] = check.page()
                for identity in identities:
                    result = check.fixture(identity)
                    evidence['fixtures'].append(result)
                    write_json(args.output, evidence)
                    print(json.dumps({'fixture': identity, 'seconds': result['seconds'],
                                      'native_calls': len(result['native_calls']),
                                      'actor_cells': result['document_actor_cells'],
                                      'screenshot': result['screenshot']['path']}), flush=True)
                evidence['completed'] = True
            finally:
                try:
                    evidence['error_logs_after'] = client.call('get_latest_error_logs', {'max_count': 30})
                except Exception as error:
                    evidence['error_logs_error'] = '%s: %s' % (type(error).__name__, error)
                if installed:
                    if args.keep_fixture:
                        check.run('b.factory=sys._blueprint_qa_saved["factory"]\n'
                                  'del sys._blueprint_qa_saved\ndel sys._blueprint_qa_identity\n'
                                  'del sys._blueprint_qa_nonce\ndel sys._blueprint_qa_expected\n'
                                  'del sys._blueprint_qa_records\n_result=True')
                        evidence['restored'] = False
                    else:
                        was_open = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                        check.run(RESTORE)
                        if not was_open and check.navigation()['open']:
                            check.run('navigator.pop()\n_result=True')
                            check.wait('restore closed workspace', lambda state: not state['open'] and not state['transition'],
                                       check.navigation)
                        evidence['restored'] = True
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)
    print(json.dumps({'evidence': str(args.output.resolve()), 'fixtures': len(evidence['fixtures']),
                      'completed': evidence['completed'], 'restored': evidence.get('restored')}))


if __name__ == '__main__':
    main()

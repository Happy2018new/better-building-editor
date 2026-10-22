"""Real public card callbacks, native documents, dry editor WGC, and restoration."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUTS = Path('D:\\Happy2018newの个人文件\\GitHub\\better-building-editor\\.runtime\\projects\\r27-transform-runtime-v1')
SCRIPTS = INPUTS / '.agents/skills/pyreact-debugging/scripts'
sys.path.insert(0, str(INPUTS / 'tools'))
sys.path.insert(0, str(SCRIPTS))
import verify_debug_blueprints as blue
blue.SCRIPTS = SCRIPTS
from _session import load_session
from mcdk import Client
from lifecycle_helpers import handles, memory


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf8')


def walk(node):
    if node is not None:
        yield node
        for child in node.get('children', ()):
            yield from walk(child)


def one(nodes, label):
    rows = list(nodes)
    assert len(rows) == 1, (label, [(row.get('type'), row.get('key'), row.get('id')) for row in rows])
    return rows[0]


STATE = '''_result=json.dumps({'editor_id':id(s.editor),'document_id':id(s.editor.document),
 'document':s.editor.document.to_data(),'factory_id':id(b.factory),'grid':s.grid,
 'fields':dict((key,getattr(s,key)) for key in ('page','name','view','focus_view','section',
 'solo_layer','focused','box_anchor','canvas_x','canvas_z','paste_origin','paste_pinned',
 'camera_pose','camera_yaw','camera_pitch','zoom','camera_pan','camera_pivot','camera_depth',
 'camera_depth_pose','camera_focus_request','camera_reset_animated','progress','direct_mode')),
 'workspace':navigator.contains('modern_projection_workspace'),'navigator_top':navigator.top.key if navigator.top else None,
 'projection_active':s.projection_active,'world_actors':len(b.projection_entities)+int(bool(b.entity)),
 'probe_installed':hasattr(sys,'_blueprint_qa_saved')})
'''

CONTROLS = '''from modern_projection.pyreact.debug import _type_name
host=navigator.top._host
def entry_walk(fiber):
 yield fiber
 for child in fiber.child_fibers:
  for descendant in entry_walk(child):yield descendant
scenes=[fiber for fiber in entry_walk(host._root_fiber) if _type_name(fiber)=='Scene' and fiber.props.get('session') is s]
assert len(scenes)==1
rows=[]
for tile in entry_walk(scenes[0]):
 if _type_name(tile)!='PreviewTile':continue
 key=tile.props['identity']
 if key not in s.tiles.parts:continue
 dolls,surfaces,preview=tile.props['registry'][key]
 part=s.tiles.parts[key]
 if not preview.ready(part['name']):continue
 assert preview.pending is None
 names=set(row['result'] for row in sys._blueprint_qa_records if row['nonce']==sys._blueprint_qa_nonce and row.get('result'))
 assert part['name'] in names
 controls=[]
 for ref in dolls:
  control=ref.current
  if control is not None:controls.append({'visible':control.GetVisible(),'type':str(type(control))})
 rows.append({'key':key,'name':part['name'],'front':preview.front,'poses':preview.poses,
  'control_count':len(controls),'controls':controls,'current_signature':part['signature']==s.preview_signature()})
assert rows and all(row['current_signature'] for row in rows)
_result=json.dumps({'editor_id':id(s.editor),'document_id':id(s.editor.document),'models':rows})
'''


class EntryCheck(blue.BlueprintCheck):
    def __init__(self, client, output, binding, report):
        super().__init__(client, output / 'report.json', 55)
        self.directory, self.binding, self.report = output, binding, report
        self.previous_handles = None
        self.cleaning = False

    def guard(self):
        row = load_session(self.binding['session_file'], self.binding['owner'], live=True)
        assert all(row.get(key) == self.binding.get(key) for key in
                   ('id', 'owner', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity', 'project', 'mcp_url'))
        current = {key: handles(row[key + '_pid']) for key in ('game', 'mcdk')}
        previous = self.previous_handles or current
        mem = memory()
        sample = {'at': time.time(), 'handles': current, 'memory': mem}
        self.report.setdefault('guard_samples', []).append(sample)
        self.previous_handles = current
        if not self.cleaning:
            assert all(value is not None and value < 250000 and value - previous[key] < 10000
                       for key, value in current.items()), sample
            assert mem['headroom_bytes'] >= 6 * 1024**3, sample

    def run(self, code):
        self.guard()
        return super().run(code)

    def command(self, cmd, node=None, value=None):
        payload = {'cmd': cmd, 'seq': uuid.uuid4().hex}
        if node is not None:
            payload['id'] = node
        if value is not None:
            payload['value'] = value
        code = ('scope={}\n'
                'eval(compile(%r,"<peony-entry-pyreact>","exec"),scope)\n'
                '_result=json.dumps(scope["pyreact_request"](json.loads(%r),'
                '"modern_projection.pyreact"))' % (self.bridge_source, json.dumps(payload)))
        result = self.run(code)
        assert result.get('pyreact_ack') and not result.get('error'), result
        return result

    def tree(self):
        return self.command('dump_tree')['tree']

    def capture(self, label, tree=None):
        self.guard()
        path = self.directory / (label + '.png')
        executable = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
        assert hashlib.sha256(executable.read_bytes()).hexdigest() == 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
        command = [sys.executable, '-B', '-X', 'utf8', str(INPUTS / 'tools/capture_native_window.py'),
                   '--session', self.binding['session_file'], '--owner', self.binding['owner'],
                   '--output', str(path), '--executable', str(executable)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding='utf8', errors='replace', timeout=45)
        receipt = {'command': command, 'returncode': result.returncode,
                   'stdout': result.stdout, 'stderr': result.stderr}
        save(self.directory / (label + '.host.json'), receipt)
        assert result.returncode == 0, receipt
        if tree is not None:
            save(self.directory / (label + '.tree.json'), tree)
        from PIL import Image
        with Image.open(path) as image:
            size = image.size
        return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'size': size}

    def actual_button(self, component):
        return one((node for node in walk(component) if node.get('type') == 'Button'), 'actual Button')

    def testing_registry(self):
        self.run('owner.open_workspace()\ns.set("page","testing")\n_result=True')
        self.wait('workspace navigation', lambda row: row['open'] and not row['transition'], self.navigation)
        tree = self.wait('actual registry segment', lambda tree: any(
            node.get('type') == 'SegmentChoice' and node.get('props', {}).get('identity') == 'transforms'
            for node in walk(tree)), self.tree)
        segment = one((node for node in walk(tree) if node.get('type') == 'SegmentChoice'
                       and node.get('props', {}).get('identity') == 'transforms'), 'registry category')
        button = self.actual_button(segment)
        result = self.command('click', button['id'])
        return {'segment': segment['id'], 'button': button['id'], 'dispatch': result}

    def load_card(self, identity):
        row = {'identity': identity, 'category_navigation': self.testing_registry(),
               'manual_issues_closed': 0, 'shape_accepted': False}
        self.report.setdefault('attempted_cards', []).append(row)
        tree = self.wait('public card mounts ' + identity, lambda tree: any(
            node.get('key') == identity for node in walk(tree)), self.tree)
        card = one((node for node in walk(tree) if node.get('key') == identity), 'exact card')
        scroll = one((node for node in walk(tree) if 'Scroll' in node.get('type', '') and
                      node.get('type') != 'Scroll' and any(child.get('key') == identity for child in walk(node))),
                     'native containing ScrollView')
        current = self.command('get_scroll', scroll['id'])['result']['position']
        panel = next((node for node in walk(card) if node.get('layout')), None)
        viewport = scroll.get('layout')
        assert panel is not None and viewport is not None, (panel, viewport)
        target = max(0., current + panel['layout']['y'] - viewport['y'] - 8.)
        row['scroll'] = self.command('scroll', scroll['id'], target)
        time.sleep(.3)
        tree = self.tree()
        card = one((node for node in walk(tree) if node.get('key') == identity), 'visible exact card')
        row['card'] = {'key': card['key'], 'id': card['id'], 'props': card['props']}
        row['card_capture'] = self.capture(identity.replace('.', '_') + '_card', tree)
        load_action = one((node for node in walk(card) if node.get('type') == 'Action'
                           and node.get('props', {}).get('label') == '\u8f7d\u5165'), 'card load Action')
        load_button = self.actual_button(load_action)
        row['expected_before_load'] = self.run(
            'from modern_projection.projection.debug_blueprints import build\n'
            'expected_doc=build(%r)\n'
            'sys._blueprint_qa_identity=%r\nsys._blueprint_qa_nonce+=1\n'
            'sys._blueprint_qa_expected={"metadata":{"name":expected_doc.name,"size":expected_doc.size,"blocks":len(expected_doc.blocks)},"previous_document_id":id(s.editor.document),"editor_id":None}\n'
            '_result=json.dumps({"expected":expected_doc.to_data(),"previous_document_id":id(s.editor.document)})'
            % (identity, identity))
        row['load_button'] = load_button['id']
        row['load_dispatch'] = self.command('click', load_button['id'])
        row['pending_confirm'] = self.run('_result=json.dumps({"opened":s.pending_confirm is not None,"message":s.pending_confirm[0] if s.pending_confirm else None})')
        assert row['pending_confirm']['opened']
        tree = self.wait('real confirmation Action mounts', lambda tree: any(
            node.get('type') == 'Action' and node.get('props', {}).get('label') == '\u786e\u8ba4\u7ee7\u7eed'
            and node.get('props', {}).get('enabled') for node in walk(tree)), self.tree)
        confirmation = one((node for node in walk(tree) if node.get('type') == 'Action'
                            and node.get('props', {}).get('label') == '\u786e\u8ba4\u7ee7\u7eed'
                            and node.get('props', {}).get('enabled')), 'enabled real confirmation')
        button = self.actual_button(confirmation)
        row['confirm_button'] = button['id']
        row['confirm_dispatch'] = self.command('click', button['id'])
        row['preview'] = self.editor_preview('actual card ' + identity)
        actual = self.run(STATE)
        assert actual['document'] == row['expected_before_load']['expected'], 'Real loaded Document differs from builder'
        assert actual['document_id'] != row['expected_before_load']['previous_document_id']
        assert not actual['projection_active'] and actual['world_actors'] == 0
        row['actual'] = actual
        if identity == 'test.blocks.peony_visibility':
            materials = [value['material'][0] for call in row['preview']['native_calls']
                         for value in call['submitted_materials']]
            row['formal_peony_resource_ids'] = sorted(set(value for value in materials
                                                         if 'ordinary_peony_' in value))
            assert row['formal_peony_resource_ids'] == [
                'modern_projection:ordinary_peony_bottom', 'modern_projection:ordinary_peony_top']
        row['controls'] = self.run(CONTROLS)
        row['editor_capture'] = self.capture(identity.replace('.', '_') + '_editor', self.tree())
        return row

    def peony_pose(self, label, yaw, focus, zoom):
        self.run('s.camera_focus_request=None\ns.camera_pivot=%r\ns.camera_pan=(0.,0.)\ns.grid=False\n'
                 's.camera_view(%r,15.,%r)\n_result=True' % (focus, yaw, zoom))
        def pose_ready(row):
            pose = row['camera_pose']
            return abs((pose[0] - yaw + 180.) % 360. - 180.) < .03 and abs(pose[1] - 15.) < .03 and abs(pose[2] - zoom) < .003
        state = self.wait('editor camera settles ' + label, pose_ready,
                          lambda: self.run('_result=json.dumps({"camera_pose":s.camera_pose,"pivot":s.camera_pivot,"pan":s.camera_pan,"document_id":id(s.editor.document)})'))
        self.editor_preview('stable peony pose ' + label)
        time.sleep(.3)
        return {'state': state, 'controls': self.run(CONTROLS), 'capture': self.capture(label, self.tree()),
                'shape_accepted': False}


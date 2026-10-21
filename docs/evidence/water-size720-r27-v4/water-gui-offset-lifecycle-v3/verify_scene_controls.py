"""Execute native readback, geometry negatives and restore ordering without MC."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import types
import scene_game as game
from scene_policy import describe_scene
import scene_restore

WORK = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', required=True, type=Path)
    args = parser.parse_args()
    out = args.output_root.resolve()
    out.mkdir(exist_ok=False)
    controls = []
    def check(name, passed):
        assert passed, name
        controls.append({'name': name, 'passed': True})
    # The real payload must import Theme itself: no previous RPC global is
    # assumed. Only the SDK/model/UI objects and that imported module are fake.
    fixture = '''import json,sys,types
class Obj(object):pass
class Ref(object):
 def __init__(self,value):self.current=value
class Native(object):
 def __init__(self,active):self.active=active
 def GetPosition(self):return (12.,124.)
 def GetGlobalPosition(self):return (40.,160.)
 def GetSize(self):return (400.,300.) if self.active else (0.,0.)
 def GetVisible(self):return self.active
 def asNeteasePaperDoll(self):return self
 def GetModelId(self):return 5 if self.active else -1
class FakeGame(object):
 def GetScreenSize(self):return (533,300)
 def GetScreenViewInfo(self):return (1600,900,0,0)
class Factory(object):
 def CreateGame(self,level):return FakeGame()
theme=Obj();theme.native_gui_scale=3.;theme.scale=.5;theme.input_font_scale=1.
for name in ('modern_projection','modern_projection.projection','modern_projection.projection.widgets'):
 module=types.ModuleType(name);module.__path__=[];sys.modules[name]=module
sys.modules['modern_projection.projection.widgets'].Theme=theme
b=Obj();b.factory=Factory();b.level='fake-level'
renderer=Obj();renderer.front=0;renderer.visible=[True,False];renderer.ids=[5,None];renderer.error=None
active=Native(True);hidden=Native(False)
entry={'renderer':renderer,'geometry':((12.,124.),(400.,300.)),
 'dolls':[Ref(active),Ref(hidden)],'surfaces':[Ref(active),Ref(hidden)],'ready_request':('fake',)}
controls=Obj();controls.registry={'fake':entry}
s=Obj();s.liquid_controls=controls
_result=json.dumps({})
assert 'Theme' not in globals()
exec compile(%r,'<actual-readback-payload>','exec')
row=json.loads(_result)
assert row['gui_cache']['cached_gui']==3.
assert row['gui_cache']['sdk_integer_gui']==3.
assert row['native_water_controls'][0]['banks'][0]['native_model_id']==5
assert row['native_water_controls'][0]['banks'][1]['size']==[0.,0.]
print(json.dumps(row))
''' % game.EXTRA_STATE
    result = subprocess.run(['D:/Program/Python27/python.exe', '-B', '-c', fixture], capture_output=True)
    assert result.returncode == 0, result.stderr
    (out / 'native-readback-py2-v1.json').write_bytes(result.stdout)
    state = json.loads(result.stdout)
    check('Actual Py2 EXTRA_STATE resolves its own Theme import and retains hidden zero-size',
          describe_scene(state, 3, True)['complete'])
    for label, edit in (
        ('wrong cache', lambda row: row['gui_cache'].update(cached_gui=4)),
        ('wrong native position', lambda row: row['native_water_controls'][0]['banks'][0].update(position=[33, 124])),
        ('wrong native size', lambda row: row['native_water_controls'][0]['banks'][0].update(size=[400, 298])),
        ('wrong skeleton identity', lambda row: row['native_water_controls'][0]['banks'][0].update(native_model_id=-1)),
        ('hidden surface', lambda row: row['native_water_controls'][0]['banks'][0].update(surface_visible=False)),
        ('unready publication', lambda row: row['native_water_controls'][0].update(request_ready=False)),
        ('nonfinite position', lambda row: row['native_water_controls'][0]['banks'][0].update(position=[float('nan'), 124]))):
        negative = copy.deepcopy(state)
        edit(negative)
        check('Native gate rejects ' + label, not describe_scene(negative, 3, True)['complete'])
    empty = copy.deepcopy(state)
    empty['native_water_controls'] = []
    check('Wet empty rejects and dry empty accepts',
          not describe_scene(empty, 3, True)['complete'] and describe_scene(empty, 3, False)['complete'])
    check('Dry visible water rejects', not describe_scene(state, 3, False)['complete'])

    class FakeBlueprints:
        RESTORE = '<EXPLICIT_FAKE_BLUEPRINT_RESTORE>'
    clock = types.SimpleNamespace(monotonic=lambda: 1., sleep=lambda seconds: None)
    original_clock = scene_restore.time
    scene_restore.time = clock
    actions = []
    before = {'restored': False, 'own_marker': True, 'blueprint_marker': True,
              'navigator_top': 'modern_projection_workspace', 'navigator_transitioning': False,
              'busy': False, 'edit_job': False, 'io_job': False, 'projection_active': False,
              'world_actors': 0, 'preparing_entity': False}
    current = dict(before)
    def fake_run(client, code):
        assert code.startswith(game.PREFIX)
        tail = code[len(game.PREFIX):]
        if tail == game.RESTORED:
            return dict(current)
        if tail == game.CLOSE:
            actions.append('close')
            current['navigator_top'] = None
            return True
        if tail == game.CLOSED:
            return {'closed': current['navigator_top'] is None}
        if tail == FakeBlueprints.RESTORE:
            actions.append('restore_blueprint')
            current['blueprint_marker'] = False
            return True
        if tail == game.RESTORE_OWN:
            actions.append('restore_own')
            current.update(own_marker=False, restored=True)
            return True
        raise AssertionError('Unrecognized payload')
    try:
        restored = scene_restore.restore_scene(None, fake_run, FakeBlueprints)
        check('Actual restore helper closes UI before blueprint factory/own state restoration',
              actions == ['close', 'restore_blueprint', 'restore_own'] and restored['restored'])
        current.update(before)
        def failure_run(client, code):
            if code == game.PREFIX + FakeBlueprints.RESTORE:
                raise OSError('explicit synthetic restore IO failure')
            return fake_run(client, code)
        try:
            scene_restore.restore_scene(None, failure_run, FakeBlueprints)
        except OSError:
            check('Actual restore helper propagates restore failure without claiming restored', current['own_marker'])
        else:
            raise AssertionError('Restore failure swallowed')
    finally:
        scene_restore.time = original_clock
    report = {'schema': 1, 'passed': True, 'MC_started': False, 'controls': controls,
              'scope': 'Real readback payload executed in Python2; actual geometry policy/restore helper with explicit SDK/UI/IO fakes',
              'host_sha256': {name: sha(WORK / name) for name in ('scene_game.py', 'scene_policy.py', 'scene_restore.py')},
              'formal_A_accepted': False, 'default_path_evidence': False}
    output = out / 'scene-controls-v1.json'
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': True, 'controls': len(controls), 'report_sha256': sha(output)}))


if __name__ == '__main__':
    main()

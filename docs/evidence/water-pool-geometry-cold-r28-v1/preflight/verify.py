"""Execute the actual launch prefix and actual source/profile values before MC."""
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
WORK = OUT.with_name('water-pool-geometry-cold-v1')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    spec = importlib.util.spec_from_file_location('preflight_' + name[:-3], WORK / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    target = OUT / 'report.json'
    assert not target.exists()
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    hosts = json.loads((WORK / 'prelaunch-host-binding-v1.json').read_bytes())
    sys.path.insert(0, str(WORK))
    launcher = load('launch_r25.py')
    watch = {'owners': [binding['owner']], 'errors': [], 'other_assertions': [],
             'checked_at': datetime.now(timezone.utc).isoformat(),
             'host_sha256': binding['diagnostic_watcher']['sha256']}
    tree = ast.parse((WORK / 'launch_r25.py').read_bytes())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    statements = []
    mocks = []
    for node in function.body:
        if isinstance(node, ast.With) and 'stdout.json' in ast.unparse(node.items[0].context_expr):
            break
        if isinstance(node, ast.Assign) and any(isinstance(item, ast.Name) and item.id == 'watch' for item in node.targets):
            node = ast.parse('watch=STATIC_WATCH').body[0]
            mocks.append('fresh watcher status dictionary')
        elif isinstance(node, ast.Assign) and any(isinstance(item, ast.Name) and item.id == 'out' for item in node.targets):
            node = ast.parse('out=STATIC_OUT/"launch-prefix"').body[0]
            mocks.append('launch output directory')
        statements.append(node)
    assert len(mocks) == 2
    namespace = dict(launcher.__dict__, STATIC_WATCH=watch, STATIC_OUT=OUT)
    before = sys.argv[:]
    sys.argv = [str(WORK / 'launch_r25.py')]
    try:
        exec(compile(ast.fix_missing_locations(ast.Module(body=statements, type_ignores=[])),
                     'actual_launcher_prefix', 'exec'), namespace)
    finally:
        sys.argv = before
    for name, expected in hosts['host_sha256'].items():
        assert sha(WORK / name) == expected, name
    for name, expected in hosts['external_host_sha256'].items():
        assert sha(ROOT / name) == expected, name
    for path in WORK.glob('*.py'):
        ast.parse(path.read_bytes(), filename=str(path))
    sys.path.insert(0, str(Path(binding['project']) / 'tools'))
    import probe_product_water as probe
    game = load('scene_game.py')
    world = load('world_readback.py')
    cold = load('observe_cold_default.py')
    payloads = {'cold': cold.CODE, 'extra_scene': probe.SCENE_STATE + game.EXTRA_STATE,
                'world_server': world.SERVER_CODE, 'world_client': world.CLIENT_CODE,
                'profile': probe.PROFILE % (True, True)}
    compiled_source = []
    for name in ('liquid_product_deployment.py', 'scene.py'):
        path = Path(binding['project']) / 'behavior_pack/modern_projection/projection' / name
        result = subprocess.run(['D:/Program/Python27/python.exe', '-B', '-c',
            'import sys;compile(sys.stdin.read(),sys.argv[1],"exec")', str(path)],
            input=path.read_bytes(), capture_output=True)
        assert result.returncode == 0, (name, result.stderr)
        compiled_source.append(name)
    for name, text in payloads.items():
        result = subprocess.run(['D:/Program/Python27/python.exe', '-B', '-c',
            'import sys;compile(sys.stdin.read(),"payload","exec")'],
            input=text.encode('utf8'), capture_output=True)
        assert result.returncode == 0, (name, result.stderr)
    # Actual SDK-free Product profile, source_document, iter_groups and packed
    # uniform contracts run in real Py2. Only UI/session methods are fake.
    values = '''import json,sys
sys.path.insert(0,sys.argv[1])
from modern_projection.projection import liquid_product_deployment as product
from modern_projection.projection.debug_product_water_blueprints import CASES
from modern_projection.projection.liquid_render_plan import iter_groups,render_steps
from modern_projection.projection.liquid_transport import validate_uniforms
request=json.loads(sys.stdin.read())
class FakeEditor(object):
 document=None
class FakeSession(object):
 grid=True
 liquid_profile=product.production_profile(product.TARGET_ENGINE_VERSION)
 editor=FakeEditor()
 def _loaded(self,doc):self.editor.document=doc
 def camera_view(self,*pose):self.camera_pose=pose
 def emit(self):pass
s=FakeSession()
original=s.liquid_profile
exec request['profile']
assert s.liquid_profile is not original
assert s.liquid_profile.ui_offset_for_gui((300.,400.),2)==(0.,150.)
for gui in (1.,2.,3.,4.):
 for p,size in (((0.,0.),(366.6114,413.8420)),((-77.,0.),(418.,164.))):
  np,ns=s.liquid_profile.ui_geometry_for_gui(p,size,gui)
  scale=s.liquid_profile.ui_pose(52.9092,25.,35.,ns)[0]
  assert abs(scale*min(ns)-52.9092)<1e-8
  assert min(ns)==ns[0] and np[1]<=p[1]+1e-8 and np[1]+ns[1]>=p[1]+size[1]-1e-8
  assert abs(np[1]+ns[1]/2.-min(ns)/gui-p[1]-size[1]/2.)<1e-8
assert request['cases']==['pool'] and set(request['cases'])<=set(row['id'] for row in CASES)
sys._blueprint_qa_nonce=0
rows=[]
for case in request['cases']:
 controls=('wet','dry','liquid_only','water_only','rearless','empty') if case.startswith('wet_') else ('wet','dry')
 for control in controls:
  pose=(0.,0.,3.) if case.startswith('wet_') else (35.,25.,4.6)
  exec request['load'] % ((case,control,pose),)
  doc=s.editor.document
  groups=list(iter_groups(doc,s.liquid_profile.provider_factory(doc)))
  packed=list(render_steps(groups,s.liquid_profile.models,1.,s.liquid_profile.max_groups))
  for row in packed:validate_uniforms(row.uniforms)
  assert len(groups)<=256
  rows.append({'case':case,'control':control,'cells':len(doc.blocks),'groups':len(groups),'packed':len(packed)})
assert len(rows)==2
s.liquid_profile,s.grid=sys._product_water_saved_profile
del sys._product_water_saved_profile
assert s.liquid_profile is original and s.grid is True
print(json.dumps({'passed':True,'rows':rows,'profile_restored':True,'SDK_called':False,'UI_and_session_fake':True}))
'''
    flow_tree = ast.parse((WORK / 'run_frozen_editor.py').read_bytes())
    cases = ast.literal_eval(next(node.value for node in flow_tree.body if isinstance(node, ast.Assign)
                                 and any(isinstance(item, ast.Name) and item.id == 'CASES' for item in node.targets)))
    request = {'profile': payloads['profile'], 'load': probe.LOAD, 'cases': cases}
    with (OUT / 'python2-values-payload.py').open('x', encoding='ascii', newline='\n') as stream:
        stream.write(values)
    result = subprocess.run(['D:/Program/Python27/python.exe', '-B', str(OUT / 'python2-values-payload.py'),
                             str(Path(binding['project']) / 'behavior_pack')],
                            input=json.dumps(request).encode('ascii'), capture_output=True)
    (OUT / 'python2-values.stdout.txt').write_bytes(result.stdout)
    (OUT / 'python2-values.stderr.txt').write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr
    actual_values = json.loads(result.stdout)
    with (OUT / 'python2-values.json').open('x', encoding='ascii') as stream:
        json.dump(actual_values, stream, indent=2)
    report = {'schema': 1, 'passed': True, 'MC_started': False, 'RPC_dispatched': False,
              'launcher_prefix_nodes': len(statements), 'explicit_mocks': mocks,
              'source_count': len(binding['source_sha256']), 'auxiliary_count': len(binding['auxiliary_sha256']),
              'source_contract_sha256': binding['source_contract_sha256'],
              'plan_sha256': sha(WORK / 'plan-v1.json'),
              'prelaunch_host_binding_sha256': sha(WORK / 'prelaunch-host-binding-v1.json'),
              'python2_proposed_source_compiled': compiled_source, 'python2_payloads_compiled': list(payloads), 'python2_actual_value_rows': len(actual_values['rows']),
              'profile_values_restored': actual_values['profile_restored'],
              'native_pixels_or_UI_accepted': False}
    with target.open('x', encoding='ascii') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report))


if __name__ == '__main__':
    main()

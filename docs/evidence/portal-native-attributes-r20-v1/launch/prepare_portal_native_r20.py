"""Create one isolated cold portal diagnostics project and start it hidden."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from generate_liquid_product_resources import merge_registry, write_json
from generate_portal_native_adapter_r19 import generate, install, layered_mesh
from probe_product_water import snapshot_digest, snapshot_sources
from _session import load_session, process_identity

parser = argparse.ArgumentParser()
parser.add_argument('--round', default='v1')
parser.add_argument('--old-session', default='52bceb09152245a1b20b440d012f0f74')
parser.add_argument('--old-owner', default='root-portal-r20-v5')
parser.add_argument('--prepare-only', action='store_true')
args = parser.parse_args()
project = ROOT / ('.runtime/projects/portal-r20-native-' + args.round)
control = ROOT / ('.runtime/portal-native-control-r20-' + args.round)
native = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data')
old = load_session('C:/Users/Happy2018new/.pyreact-debug/instances/' + args.old_session + '/session.json', args.old_owner)
assert process_identity(old['game_pid']) is None
assert process_identity(old['mcdk_pid']) is None
assert not project.exists() and not control.exists()
shutil.copytree(ROOT / '.runtime/projects/portal-r20', project)
control.mkdir()
aliases = control / 'adapter'
contract = generate(project, native, aliases, 16)
install(aliases, project)

# A process-local native material override is admitted only if its sentinel appears.
native_vertex = (native / 'shaders/glsl/end_portal.vertex').read_bytes()
(project / 'resource_pack/shaders/glsl/r20_native_attribute.vertex').write_bytes(native_vertex)
fragment = '''// __multiversion__
precision highp float;
#define main nativePortalMain
#include "r19_native_portal_original.h"
#undef main
#include "uniformPerFrameConstants.h"
void main() {
    float depth=encodedPlane.w*32.0;
    if(depth>31.0) { gl_FragColor=vec4(0.,0.,0.,0.); return; }
    float stripe=mod(floor(gl_FragCoord.x/4.0),32.0);
    if(abs(floor(depth+0.5)-stripe)>0.25) discard;
    gl_FragColor=vec4(vec3(0.25)+0.75*vec3(colorLookupUV,encodedPlane.w),0.);
}
'''
(project / 'resource_pack/shaders/glsl/r20_native_attribute.fragment').write_text(fragment, encoding='ascii', newline='\n')
portal_material = json.loads((native / 'resource_packs/vanilla/materials/portal.material').read_bytes())
portal_material['materials']['portal_base'].update(
    vertexShader='shaders/glsl/r20_native_attribute.vertex',
    fragmentShader='shaders/glsl/r20_native_attribute.fragment')
merge_registry(project / 'resource_pack/materials/entity.material',
               {'portal_base': portal_material['materials']['portal_base']}, nested=True)
write_json(project / 'resource_pack/materials/portal.material', portal_material)
for name in ('common.json', 'fancy.json', 'sad.json'):
    shutil.copyfile(native / 'resource_packs/vanilla/materials' / name,
                    project / 'resource_pack/materials' / name)

materials, models = {}, {}
world = (aliases / 'resource_pack/shaders/glsl/r19_native_portal_world.vertex').read_text(encoding='ascii')
shader = (aliases / 'resource_pack/shaders/glsl/r19_native_portal_native.fragment').read_text(encoding='ascii')
for variant, count, first in (('depth8first8', 8, 8), ('depth16first8', 16, 8),
                              ('depth16first16', 16, 16), ('depth24first8', 24, 8),
                              ('depth31first1', 31, 1)):
    prefix = 'r20_native_portal_' + variant + '_'
    for family in ('end_gateway', 'end_portal'):
        base = 'r19_native_portal_' + family + '_world'
        name = prefix + family + '_world'
        model = deepcopy(contract['models'][base])
        source = json.loads((project / 'resource_pack/models/modern_projection/portal' / (family + '_mesh.json')).read_bytes())
        mesh = 'modern_projection/portal/' + name + '_mesh.json'
        write_json(project / 'resource_pack/models' / mesh, layered_mesh(source, count, first))
        model.update(mesh=mesh, material=name)
        models[name] = model
        materials[name + ':entity_for_skeleton_alpha'] = deepcopy(contract['materials'][base + ':entity_for_skeleton_alpha'])
merge_registry(project / 'resource_pack/models/netease_models.json', models)
merge_registry(project / 'resource_pack/materials/entity.material', materials, nested=True)
config = json.loads((project / '.mcdev.json').read_bytes())
for key in list(config):
    if key.startswith('auto_hot_reload_'):
        config[key] = False
write_json(project / '.mcdev.json', config)
for source in (ROOT / 'tools').glob('*.py'):
    shutil.copyfile(source, project / 'tools' / source.name)
sources = snapshot_sources(project)
write_json(control / 'launch-inputs.json', {'source_contract_sha256': snapshot_digest(sources), 'files': sources})
if args.prepare_only:
    print(json.dumps({'prepared': True, 'project': str(project), 'control': str(control)}))
    sys.exit(0)
guard = old['noactivation']
for name in ('mcdk', 'dll'):
    assert hashlib.sha256(Path(guard[name]['path']).read_bytes()).hexdigest() == guard[name]['sha256']
command = [sys.executable, '-X', 'utf8', str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'),
           'start', '--project', str(project), '--owner', 'portal-r20-native-' + args.round,
           '--name', 'portal-r20-native-' + args.round, '--wait', '180', '--preset', 'ui',
           '--game-exe', 'D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/Minecraft.Windows.exe',
           '--mcdk', guard['mcdk']['path'], '--noactivate-mcdk-sha256', guard['mcdk']['sha256'],
           '--noactivate-dll', guard['dll']['path'], '--noactivate-sha256', guard['dll']['sha256']]
with (control / 'start.stdout.json').open('w', encoding='utf8') as stdout, (control / 'start.stderr.txt').open('w', encoding='utf8') as stderr:
    result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1'), stdout=stdout, stderr=stderr, timeout=300)
assert result.returncode == 0, 'Inspect startup receipt before retrying'
session = json.loads((control / 'start.stdout.json').read_bytes())
receipt = {key: session[key] for key in ('session_file', 'owner', 'state', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')}
write_json(control / 'ready-summary.json', receipt)
print(json.dumps(receipt))

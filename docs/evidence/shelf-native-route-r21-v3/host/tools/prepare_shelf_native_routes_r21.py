"""Freeze a four-resource native route selector copied from a frozen v2 clone."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil

from freeze_intrinsic_glint_project_r21 import fingerprint, RELOADS
from generate_shelf_resources_r17 import write_json
from prepare_shelf_native_light_r21 import digest


ROOT = Path(__file__).resolve().parents[1]
OWNER = 'root-shelf-r20-native-routes-v3'
ROUTES = {
    'entity_static_netease': ('entity', 'color', (0., 1., 1.)),
    'terrain_base': ('renderchunk', 'diffuse', (1., 1., 0.)),
}


def fragment_path(root):
    return 'resource_pack/shaders/glsl/modern_projection_shelf_route_'+root+'.fragment'


def selector_fragment(original, variable, marker):
    anchor = 'gl_FragColor = '+variable+';'
    if original.count(anchor) != 1 or original.count('// __multiversion__') != 1:
        raise ValueError('The installed native fragment output changed')
    output = '''float shelfRouteStripe=mod(floor(gl_FragCoord.x/16.0),2.0);
    vec3 shelfRouteRgb=%s.rgb;
    if(shelfRouteStripe<0.5) shelfRouteRgb=vec3(%s);
    gl_FragColor=vec4(shelfRouteRgb,%s.a);''' % (
        variable, ','.join(str(value) for value in marker), variable)
    return original.replace(anchor, output).replace('// __multiversion__',
        '// __multiversion__\nprecision highp float;\nprecision highp int;', 1)


def host_sources():
    names = ['prepare_shelf_native_routes_r21.py', 'verify_shelf_native_routes_r21.py',
        'probe_shelf_native_routes_r21.py', 'prepare_shelf_native_light_r21.py',
        'freeze_intrinsic_glint_project_r21.py', 'generate_shelf_resources_r17.py',
        'probe_liquid_pose_channel.py', 'probe_native_palette_body_r16.py',
        'probe_shelf_body_matrix_r20.py', 'probe_shelf_native_shape_r17.py',
        'probe_product_water.py', 'census_intrinsic_glint_ui_r21.py',
        'capture_native_window.py', 'diagnose_window_dpi.py', 'context_test_environment.py',
        'watch_intrinsic_glint_exit_r21.py']
    paths = ['tools/'+name for name in names]
    paths += ['.runtime/start_shelf_baked_r21.py', '.runtime/shelf-native-routes-r21-v3/run.py']
    paths += ['.agents/skills/pyreact-debugging/scripts/'+name
              for name in ('instances.py', '_session.py', '_window.py', 'mcdk.py')]
    return {name: digest(ROOT/name) for name in paths}


def verify(manifest):
    frozen = json.loads(manifest.read_bytes())
    if fingerprint(Path(frozen['source'])) != frozen['source_files']:
        raise RuntimeError('The frozen v2 source changed')
    if digest(Path(frozen['source_freeze'])) != frozen['source_freeze_sha256']:
        raise RuntimeError('The v2 freeze record changed')
    if digest(Path(frozen['v2_capture_report'])) != frozen['v2_capture_report_sha256']:
        raise RuntimeError('The v2 restored capture evidence changed')
    if fingerprint(Path(frozen['project'])) != frozen['files']:
        raise RuntimeError('The prepared v3 clone changed')
    if host_sources() != frozen['host_sources']:
        raise RuntimeError('A frozen route-selector host source changed')
    for name, expected in frozen['native_sources'].items():
        if digest(Path(name)) != expected:
            raise RuntimeError('An installed native source changed: '+name)
    if digest(Path(frozen['capture_exe'])) != frozen['capture_exe_sha256']:
        raise RuntimeError('The known WGC executable changed')
    for name, expected in frozen['evidence_sha256'].items():
        if digest(manifest.parent/name) != expected:
            raise RuntimeError('A route-selector evidence file changed: '+name)
    return frozen


def prepare(source, source_freeze, headers, project, output, capture_report):
    occupied = output.exists() and any(path.name != 'run.py' for path in output.iterdir())
    if project.exists() or occupied or source.resolve() == project.resolve():
        raise ValueError('Use a distinct new clone and fresh evidence directory')
    prior = json.loads(source_freeze.read_bytes())
    before = fingerprint(source)
    if Path(prior['project']).resolve() != source.resolve() or prior['files'] != before:
        raise ValueError('The v2 source must match its exact frozen manifest')
    config = json.loads((source/'.mcdev.json').read_bytes())
    if any(config.get(key) is not False for key in RELOADS):
        raise ValueError('All four automatic reload options must remain disabled')
    if '3.10.0.420447' not in config.get('game_executable_path', ''):
        raise ValueError('The source must use the target engine')
    receipt = json.loads(capture_report.read_bytes())
    if not all(receipt.get(key) for key in ('completed', 'restored', 'source_unchanged')) or receipt['cleanup_errors']:
        raise ValueError('The v2 capture evidence must have completed and restored')
    helper = next(iter(receipt['captures'].values()))['helper']
    if digest(Path(helper['path'])) != helper['sha256']:
        raise ValueError('The prior capture executable changed')
    for folder in ('behavior_pack', 'resource_pack'):
        shutil.copytree(source/folder, project/folder)
    shutil.copyfile(source/'.mcdev.json', project/'.mcdev.json')
    if fingerprint(project) != before:
        raise ValueError('The copied clone differs from its frozen v2 source')
    output.mkdir(parents=True, exist_ok=True)
    native_sources, overrides = {}, {}
    for root, (family, variable, marker) in ROUTES.items():
        original = (headers/(family+'.fragment')).read_text(encoding='utf8')
        path = project/fragment_path(root)
        path.write_text(selector_fragment(original, variable, marker), encoding='ascii', newline='\n')
        material = 'entity' if family == 'entity' else 'terrain'
        registry = project/('resource_pack/materials/'+material+'.material')
        data = json.loads(registry.read_bytes())
        overrides[root] = data['materials'].get(root)
        data['materials'][root] = {'fragmentShader': fragment_path(root).removeprefix('resource_pack/')}
        registry.write_text(json.dumps(data, indent=2)+'\n', encoding='ascii', newline='\n')
        for suffix in ('.vertex', '.fragment'):
            native_sources[str(headers/(family+suffix))] = digest(headers/(family+suffix))
    after = fingerprint(project)
    by_name = {row['path']: row for row in before}
    changed = [row['path'] for row in after if by_name.get(row['path']) != row]
    expected = sorted(['resource_pack/materials/entity.material', 'resource_pack/materials/terrain.material']+
                      [fragment_path(root) for root in ROUTES])
    if sorted(changed) != expected:
        raise ValueError('The selector changed more than its four declared resource paths')
    evidence = []
    for relative in expected:
        original = (source/relative).read_bytes() if (source/relative).exists() else b''
        incoming = (project/relative).read_bytes()
        for label, content in (('before', original), ('after', incoming)):
            path = output/'diffs'/label/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            evidence.append(path)
        patch = output/'diffs'/(Path(relative).name+'.patch')
        patch.write_text(''.join(difflib.unified_diff(original.decode('ascii').splitlines(True),
            incoming.decode('ascii').splitlines(True), fromfile='v2/'+relative, tofile='v3/'+relative)),
            encoding='ascii', newline='\n')
        evidence.append(patch)
    if fingerprint(source) != before:
        raise ValueError('Preparation mutated its frozen v2 source')
    for pack, material in (('vanilla', 'terrain'), ('vanilla_netease', 'terrain'),
                           ('vanilla_netease', 'entity')):
        path = headers.parents[1]/('resource_packs/'+pack+'/materials/'+material+'.material')
        native_sources[str(path)] = digest(path)
    frozen = {'schema_version': 1, 'owner': OWNER, 'project': str(project.resolve()),
        'source': str(source.resolve()), 'source_freeze': str(source_freeze.resolve()),
        'source_freeze_sha256': digest(source_freeze), 'source_files': before, 'files': after,
        'files_sha256': hashlib.sha256(json.dumps(after, ensure_ascii=True).encode('ascii')).hexdigest(),
        'changed_paths': expected, 'previous_overrides': overrides, 'native_sources': native_sources,
        'host_sources': host_sources(), 'capture_exe': helper['path'], 'capture_exe_sha256': helper['sha256'],
        'v2_capture_report': str(capture_report.resolve()), 'v2_capture_report_sha256': digest(capture_report),
        'evidence_sha256': {path.relative_to(output).as_posix(): digest(path) for path in evidence},
        'vertex_or_fields_changed': False, 'game_launched': False, 'production_qualified': False,
        'routes': {root: {'marker_rgb': marker, 'native_family': family}
                   for root, (family, variable, marker) in ROUTES.items()},
        'limits': ['Only south native/empty captures are admitted; root review is required before expansion.',
                   'Marker pixels on background terrain or creatures do not establish the shelf route.',
                   'A no-hit result cannot exclude explicit descendant fragment overrides or separate roots.',
                   'Original final RGB survives alternate 16px strips; original alpha and discard survive every strip.']}
    write_json(output/'frozen.json', frozen)
    verify(output/'frozen.json')
    print(json.dumps({'prepared': True, 'files': len(after), 'changed_paths': expected,
                      'files_sha256': frozen['files_sha256'], 'game_launched': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'source-freeze', 'headers', 'project', 'output', 'capture-report'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.source_freeze, args.headers, args.project, args.output, args.capture_report)

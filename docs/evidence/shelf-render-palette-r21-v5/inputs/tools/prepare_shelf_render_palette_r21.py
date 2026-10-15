"""Freeze one oak/south use_ao block proxy with the existing native geometry path."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from freeze_intrinsic_glint_project_r21 import fingerprint
from generate_liquid_product_resources import merge_registry
from generate_shelf_resources_r17 import body_model, write_json
from shelf_render_palette_candidate_r21 import PROXY

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'root-shelf-r20-render-palette-v5'
FRAGMENT = 'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment'
DIAGNOSTIC = '''
    if (abs(EXTRA_ACTOR_UNIFORM4.x-19491.0) < 0.25) {
        gl_FragColor=vec4(color.rgb,1.0);
        return;
    }
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hosts():
    names = ('tools/shelf_render_palette_candidate_r21.py', 'tools/prepare_shelf_render_palette_r21.py',
             'tools/probe_shelf_render_palette_r21.py', 'tools/verify_shelf_render_palette_r21.py',
             '.runtime/shelf-render-palette-r21-v5/run.py')
    return {name: digest(ROOT/name) for name in names}


def verify(path):
    frozen = json.loads(path.read_bytes())
    if fingerprint(Path(frozen['project'])) != frozen['files'] or hosts() != frozen['host_sources']:
        raise ValueError('The frozen render-palette clone or host changed')
    if digest(Path(frozen['source_freeze'])) != frozen['source_freeze_sha256']:
        raise ValueError('The frozen source manifest changed')
    source = json.loads(Path(frozen['source_freeze']).read_bytes())
    if fingerprint(Path(source['project'])) != source['files']:
        raise ValueError('The frozen source clone changed')
    if digest(Path(frozen['capture_exe'])) != frozen['capture_exe_sha256']:
        raise ValueError('The capture helper changed')
    return frozen


def prepare(source_freeze, project, output):
    source_freeze, project, output = source_freeze.resolve(), project.resolve(), output.resolve()
    if project.exists() or (output/'frozen.json').exists():
        raise ValueError('Choose a fresh clone and freeze')
    source = json.loads(source_freeze.read_bytes())
    previous = fingerprint(Path(source['project']))
    if previous != source['files']:
        raise ValueError('The frozen source clone changed')
    for folder in ('behavior_pack', 'resource_pack'):
        shutil.copytree(Path(source['project'])/folder, project/folder)
    shutil.copyfile(Path(source['project'])/'.mcdev.json', project/'.mcdev.json')
    if fingerprint(project) != previous:
        raise ValueError('The new clone differs before its overlay')
    reference = json.loads((ROOT/'.runtime/shelf-skeleton-r21-v1/reference.json').read_bytes())
    model = body_model(reference, 'oak', 'unpowered', 'south')
    model['netease:block_geometry']['description'].update(identifier=PROXY[0], use_ao=True)
    stem = PROXY[0].split(':')[1]
    write_json(project/('resource_pack/models/netease_block/'+stem+'.json'), model)
    write_json(project/('behavior_pack/netease_blocks/'+stem+'.json'), {
        'format_version': '1.10.0', 'minecraft:block': {
            'description': {'identifier': PROXY[0], 'register_to_creative_menu': False},
            'components': {'netease:render_layer': {'value': 'alpha'}, 'netease:no_crop_face_block': {},
                           'minecraft:block_light_absorption': {'value': 0}}}})
    merge_registry(project/'resource_pack/blocks.json', {PROXY[0]: {'netease_model': PROXY[0], 'sound': 'wood'}})
    texture_key = 'modern_projection_shelf_oak'
    texture = project/('resource_pack/textures/blocks/'+texture_key+'.png')
    texture.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT/'.runtime/shelf-skeleton-r21-v1/resource_pack/textures/models/modern_projection/shelf_r21/oak.png', texture)
    terrain_path = project/'resource_pack/textures/terrain_texture.json'
    terrain = json.loads(terrain_path.read_bytes())
    terrain['texture_data'][texture_key] = {'textures': 'textures/blocks/'+texture_key}
    write_json(terrain_path, terrain)
    fragment = (project/FRAGMENT).read_text(encoding='utf8')
    anchor = '    if (previewClip > 0.0) discard;'
    if fragment.count(anchor) != 1 or 'varying vec4 color;' not in fragment:
        raise ValueError('The existing common-block fragment anchor changed')
    (project/FRAGMENT).write_text(fragment.replace(anchor, anchor+DIAGNOSTIC, 1), encoding='ascii', newline='\n')
    files = fingerprint(project)
    prior = {row['path']: row['sha256'] for row in previous}
    changed = [row['path'] for row in files if prior.get(row['path']) != row['sha256']]
    expected = {FRAGMENT, 'resource_pack/blocks.json', 'resource_pack/textures/terrain_texture.json',
                'resource_pack/textures/blocks/'+texture_key+'.png',
                'resource_pack/models/netease_block/'+stem+'.json',
                'behavior_pack/netease_blocks/'+stem+'.json'}
    if set(changed) != expected:
        raise ValueError('The narrow overlay must change exactly its six declared paths')
    output.mkdir(parents=True, exist_ok=True)
    write_json(output/'frozen.json', {'schema_version': 1, 'owner': OWNER, 'project': str(project),
        'source_freeze': str(source_freeze), 'source_freeze_sha256': digest(source_freeze),
        'files': files, 'files_sha256': hashlib.sha256(json.dumps(files, ensure_ascii=True).encode('ascii')).hexdigest(),
        'host_sources': hosts(), 'changed_paths': changed, 'proxy': PROXY,
        'capture_exe': source['capture_exe'], 'capture_exe_sha256': source['capture_exe_sha256'],
        'reference_sha256': digest(ROOT/'.runtime/shelf-skeleton-r21-v1/reference.json'),
        'source_identity': ['minecraft:oak_shelf', 0], 'game_launched': False, 'production_qualified': False,
        'scope': 'South oak unpowered only. One main Combine palette contains body and support. No standalone body overlay or scalar correction.'})
    return verify(output/'frozen.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-freeze', type=Path, required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.source_freeze, args.project, args.output)
    print(json.dumps({'prepared': True, 'files': len(result['files']), 'changed_paths': result['changed_paths'],
                      'files_sha256': result['files_sha256'], 'game_launched': False}))


if __name__ == '__main__':
    main()

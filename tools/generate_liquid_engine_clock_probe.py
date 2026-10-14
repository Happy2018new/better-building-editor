"""Generate an isolated clock-only RP for an independently managed minimal world."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import uuid

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'modern_projection_engine_clock_probe_v1'
ASSET = 'modern_projection/engine_clock_probe_v1'
FRAGMENT = '''// __multiversion__
precision highp float;
#include "fragmentVersionCentroidUV.h"
#include "uniformInterFrameConstants.h"
varying highp float liquidVisible;
void main() {
    if (liquidVisible<0.5) discard;
    gl_FragColor=vec4(mod(TOTAL_REAL_WORLD_TIME,8.0)/8.0,0.25,1.0,1.0);
}
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='ascii', newline='\n')


def generate(output):
    if output.exists():
        raise ValueError('Choose a fresh isolated probe directory')
    pack = output / 'resource_pack'
    sources = {
        'resource_pack/models/modern_projection/liquid/skeleton.json': 'models/' + ASSET + '/skeleton.json',
        'resource_pack/models/modern_projection/liquid/flowing_water_grey_top_mesh.json': 'models/' + ASSET + '/mesh.json',
        'resource_pack/shaders/glsl/modern_projection_liquid_product_geometry_top_world.vertex':
            'shaders/glsl/' + MODEL + '.vertex'}
    for source, target in sources.items():
        destination = pack / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, destination)
    mesh_path = pack / ('models/' + ASSET + '/mesh.json')
    mesh = json.loads(mesh_path.read_bytes())
    for part in mesh['mesh']:
        part['material'] = ASSET + '/white'
    write_json(mesh_path, mesh)
    (pack / ('shaders/glsl/' + MODEL + '.fragment')).write_text(FRAGMENT, encoding='ascii', newline='\n')
    texture = pack / ('textures/models/' + ASSET + '/white.png')
    texture.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGBA', (1, 1), (255, 255, 255, 255)).save(texture)
    write_json(pack / 'manifest.json', {'format_version': 2, 'header': {
        'name': MODEL, 'description': 'Independent native animation clock probe',
        'uuid': str(uuid.uuid4()), 'version': [1, 0, 0], 'min_engine_version': [1, 21, 0]},
        'modules': [{'type': 'resources', 'uuid': str(uuid.uuid4()), 'version': [1, 0, 0]}]})
    write_json(pack / 'models/netease_models.json', {MODEL: {
        'dy_load': True, 'mesh': ASSET + '/mesh.json', 'skeleton': ASSET + '/skeleton.json',
        'animation': {}, 'material': MODEL, 'texture': {'tex0': ASSET + '/white'}}})
    write_json(pack / 'materials/entity.material', {'materials': {'version': '1.0.0',
        MODEL + ':entity_for_skeleton_alpha': {
            'vertexShader': 'shaders/glsl/' + MODEL + '.vertex',
            'fragmentShader': 'shaders/glsl/' + MODEL + '.fragment',
            '+states': ['InvertCulling']}}})
    report = {'schema_version': 1, 'model': MODEL, 'diagnostic': 'Independent native clock only',
              'clock_uniform': 'TOTAL_REAL_WORLD_TIME', 'period_seconds': 8,
              'source_sha256': {name: sha(ROOT / name) for name in sources},
              'output_sha256': {path.relative_to(output).as_posix(): sha(path)
                                for path in sorted(output.rglob('*')) if path.is_file()},
              'game_acceptance_claimed': False}
    write_json(output / 'clock-probe-contract.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({'model': generate(args.output)['model'], 'output': str(args.output.resolve())}))


if __name__ == '__main__':
    main()

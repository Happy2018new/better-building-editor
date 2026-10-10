"""Bind native liquid mesh descendants explicitly instead of relying on inheritance."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE_PATH = 'resource_packs/vanilla_netease/materials/terrain.material'
BASE = 'netease_block_as_mesh_blend'
VERTEX = 'shaders/glsl/modern_projection_biome_blocks.vertex'
FRAGMENT = 'shaders/glsl/modern_projection_biome_blocks.fragment'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse_native(text):
    # Native material files are JSON5; comments and duplicate keys need a parser.
    import json5
    return json5.loads(text, allow_duplicate_keys=False)['materials']


def liquid_descendants(materials):
    parents = {}
    for key in materials:
        if key == 'version':
            continue
        name, separator, parent = key.partition(':')
        if name in parents:
            raise ValueError('Duplicate native material identity: ' + name)
        parents[name] = parent if separator else None
    if BASE not in parents:
        raise ValueError('Native liquid mesh material is missing')
    result = []
    for name in parents:
        current, visited = name, set()
        while current in parents:
            if current in visited:
                raise ValueError('Native material inheritance cycle: ' + name)
            visited.add(current)
            if current == BASE:
                result.append(name)
                break
            current = parents[current]
    return sorted(result)


def snapshot(raw, manifest):
    text = raw.decode('utf8')
    materials = parse_native(text)
    return {'schema_version': 1, 'game_version': manifest['game_version'],
            'palette_sha256': manifest['source_sha256'], 'native_path': NATIVE_PATH,
            'native_sha256': digest(raw), 'native_text': text,
            'liquid_materials': liquid_descendants(materials),
            'scope': 'Explicit native liquid shader binding candidate; visual acceptance is independent.'}


def checked_descendants(source, manifest):
    if (source.get('schema_version') != 1 or source.get('native_path') != NATIVE_PATH or
            source.get('game_version') != manifest['game_version'] or
            source.get('palette_sha256') != manifest['source_sha256']):
        raise ValueError('Native liquid materials belong to a different registry')
    raw = source['native_text'].encode('utf8')
    if digest(raw) != source['native_sha256']:
        raise ValueError('Native liquid material source changed')
    result = liquid_descendants(parse_native(source['native_text']))
    if result != source['liquid_materials']:
        raise ValueError('Native liquid descendant coverage changed')
    return result


def adapted_materials(current, descendants):
    result = dict(current)
    for name in descendants:
        definition = dict(result.get(name, {}))
        definition.update(vertexShader=VERTEX, fragmentShader=FRAGMENT)
        result[name] = definition
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-data', type=Path)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.capture and (args.game_data is None or args.check):
        parser.error('--capture requires --game-data and cannot be combined with --check')
    manifest = json.loads((ROOT/'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    version = manifest['game_version'].removeprefix('NEMC ')
    source_path = ROOT/'tools/data'/('native_liquid_materials_nemc_'+version+'.json')
    if args.capture:
        source = snapshot((args.game_data/NATIVE_PATH).read_bytes(), manifest)
        source_path.write_text(json.dumps(source, ensure_ascii=True, indent=2)+'\n', encoding='ascii')
    source = json.loads(source_path.read_text(encoding='utf8'))
    descendants = checked_descendants(source, manifest)
    if args.game_data and digest((args.game_data/NATIVE_PATH).read_bytes()) != source['native_sha256']:
        raise ValueError('Installed native liquid material changed; review the version diff')
    destination = ROOT/'resource_pack/materials/terrain.material'
    data = json.loads(destination.read_text(encoding='utf8'))
    materials = data['materials']
    adapted = adapted_materials(materials, descendants)
    if args.check:
        if adapted != materials:
            raise ValueError('Native liquid shader bindings are stale')
    else:
        data['materials'] = adapted
        destination.write_text(json.dumps(data, ensure_ascii=True, indent=2)+'\n', encoding='ascii')
    print(json.dumps({'game_version': source['game_version'], 'materials': descendants,
                      'check': args.check, 'visual_acceptance': False}))


if __name__ == '__main__':
    main()

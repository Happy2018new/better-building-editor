"""Keep native shader sources and reviewed adaptations tied to one block dump."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    'shaders/glsl/entity.vertex',
    'shaders/glsl/netease_block_as_entity_specified.fragment',
    'shaders/glsl/color_uv.vertex',
    'shaders/glsl/text.fragment',
    'resource_packs/vanilla_netease/materials/entity.material',
    'resource_packs/vanilla/materials/ui3D.material',
)
ADAPTED = (
    'resource_pack/materials/entity.material',
    'resource_pack/shaders/glsl/modern_projection_native_actor.fragment',
    'resource_pack/shaders/glsl/modern_projection_sign_text.vertex',
    'resource_pack/shaders/glsl/modern_projection_sign_text.fragment',
    'resource_pack/materials/ui3D.material',
)
ADAPTED_HASH_FORMAT = 'sha256-utf8-lf-v1'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def adapted_digest(raw):
    """Git may check these UTF-8 text artifacts out with CRLF on Windows."""
    text = raw.decode('utf8').replace('\r\n', '\n')
    return digest(text.encode('utf8'))


def check(snapshot, registry, root=ROOT, game_data=None):
    if (snapshot.get('schema_version') != 2 or
            snapshot.get('adapted_hash_format') != ADAPTED_HASH_FORMAT or
            snapshot.get('game_version') != registry['game_version'] or
            snapshot.get('palette_sha256') != registry['source_sha256']):
        raise ValueError('Native actor materials belong to a different registry')
    if set(snapshot['sources']) != set(SOURCES) or set(snapshot['adapted']) != set(ADAPTED):
        raise ValueError('Native material source coverage changed')
    for name, value in snapshot['sources'].items():
        if digest(value['text'].encode('utf8')) != value['sha256']:
            raise ValueError('Native source snapshot changed: ' + name)
        if game_data and digest((game_data / name).read_bytes()) != value['native_sha256']:
            raise ValueError('Installed native source changed; diff and review it: ' + name)
    for name, value in snapshot['adapted'].items():
        if adapted_digest((root / name).read_bytes()) != value:
            raise ValueError('Adapted material changed; repeat shader and visual checks: ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-data', type=Path, help='Compare with this installed game data directory')
    parser.add_argument('--capture', action='store_true', help='Capture sources after reviewing a new version')
    args = parser.parse_args()
    registry = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    version = registry['game_version'].removeprefix('NEMC ')
    path = ROOT / ('tools/data/native_actor_materials_nemc_' + version + '.json')
    if args.capture:
        if not args.game_data:
            parser.error('--capture requires --game-data')
        snapshot = {'schema_version': 2, 'game_version': registry['game_version'],
                    'adapted_hash_format': ADAPTED_HASH_FORMAT,
                    'palette_sha256': registry['source_sha256'], 'sources': {}, 'adapted': {},
                    'scope': 'Native source and adaptation consistency; shader and visual acceptance are separate.'}
        for name in SOURCES:
            raw = (args.game_data / name).read_bytes()
            source = raw.decode('utf8')
            snapshot['sources'][name] = {'text': source, 'sha256': digest(source.encode('utf8')),
                                         'native_sha256': digest(raw)}
        snapshot['adapted'] = {name: adapted_digest((ROOT / name).read_bytes()) for name in ADAPTED}
        path.write_text(json.dumps(snapshot, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    snapshot = json.loads(path.read_text(encoding='utf8'))
    check(snapshot, registry, game_data=args.game_data)
    print('Native actor materials match ' + registry['game_version'])


if __name__ == '__main__':
    main()

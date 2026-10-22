"""Fingerprint water owner implementations without runtime file I/O."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'behavior_pack/modern_projection/projection/liquid_product_owner_data.py'
CONTRACT = ROOT / 'tools/data/liquid_product_owner_contract_v1.json'
SOURCES = tuple('behavior_pack/modern_projection/projection/' + name + '.py' for name in (
    'liquid_shape', 'liquid_native_shapes', 'liquid_product_shape_data', 'liquid_product_flow_top',
    'liquid_face_textures', 'liquid_face_texture_data', 'liquid_product_profile', 'liquid_product_render',
    'liquid_product_projection', 'liquid_product_plan', 'liquid_product_preview',
    'liquid_render_plan', 'liquid_transport', 'liquid_render', 'liquid_preview',
    'liquid_projection', 'liquid_viewport', 'liquid_scene', 'scene', 'scene_owner', 'world_projection',
    'projection_companions', 'liquid_render_ownership', 'geometry_palette',
    'render_context', 'bridge', 'session', 'tiles', 'ui', 'occupancy',
    'liquid_render_target_data',
    'liquid_product_deployment', 'liquid_deployment', 'biomes', 'biome_water_data',
    'block_traits', 'block_traits_data', 'block_registry', 'block_registry_data',
    'debug_product_water_blueprints'))


def digest(value):
    return hashlib.sha256(value).hexdigest()


def source_contract():
    rows = {name: digest((ROOT / name).read_bytes().replace(b'\r\n', b'\n')) for name in SOURCES}
    return {'schema_version': 1, 'normalization': 'CRLF_to_LF_only', 'source_sha256': rows,
            'generator_sha256': digest(Path(__file__).read_bytes().replace(b'\r\n', b'\n'))}


def generated():
    contract = source_contract()
    encoded = (json.dumps(contract, sort_keys=True, ensure_ascii=True, indent=2) + '\n').encode('ascii')
    source = ('"""Generated water rule and owner fingerprints; regenerate before acceptance."""\n'
              'SCHEMA_VERSION = 1\nIMPLEMENTATION_CONTRACT_SHA256 = %r\n' % digest(encoded)).encode('ascii')
    return encoded, source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    contract, source = generated()
    if args.check:
        for path, expected in ((CONTRACT, contract), (OUTPUT, source)):
            if not path.is_file() or path.read_bytes().replace(b'\r\n', b'\n') != expected:
                raise ValueError('Water implementation contract needs regeneration: ' + str(path))
    else:
        CONTRACT.write_bytes(contract)
        OUTPUT.write_bytes(source)
    print(json.dumps({'checked': args.check, 'sources': len(SOURCES), 'contract_sha256': digest(contract)}))


if __name__ == '__main__':
    main()

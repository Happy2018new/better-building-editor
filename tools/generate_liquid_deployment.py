"""Generate the closed, disabled liquid deployment from a concrete resource bundle."""
import argparse
import json
from pathlib import Path
import pprint
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry, liquid_shape_data, liquid_face_texture_data
from generate_liquid_payload_poc import source_snapshot
from generate_liquid_skeleton_resources import digest

TEMPLATE = 'native_water_side_nw_bottom_edges_v1'


def resource_profile(contract, frozen=False):
    if not contract.get('world_bone_matrix') or not contract.get('preview_depth'):
        raise ValueError('Deployment needs both existing UI-depth and world-bone resource paths')
    models, capabilities = [], []
    suffix = '_frozen' if frozen else ''
    for texture, template in (('still_water_grey', None), ('flowing_water_grey', TEMPLATE)):
        model = 'modern_projection_liquid_' + texture + suffix
        if model not in contract['models'] or model + '_world' not in contract['models']:
            raise ValueError('Deployment bundle lacks separate UI/world artwork models: ' + texture)
        for name, transform in ((model, 'native_ui_neg_x_neg_z_neg_y_center1_5'),
                                (model + '_world', 'native_bone_after_reverse_z')):
            options = contract['model_options'].get(name, {})
            if (options.get('texture') != texture or options.get('transform') != transform
                    or options.get('uv_rotations') != [0]
                    or options.get('preview_depth') is not (name == model)):
                raise ValueError('Deployment model transform/depth/rotation differs: ' + name)
        models.append((texture, template, model, model + '_world'))
        capabilities.append((texture, template, (0,)))
    return {'schema_version': 2, 'payload_version': contract['payload_version'],
            'game_version': block_registry.source_version(),
            'palette_sha256': block_registry.fingerprint(),
            'shape_candidate_sha256': liquid_shape_data.CANDIDATE_SHA256,
            'face_texture_rows_sha256': liquid_face_texture_data.RESOURCE_ROWS_SHA256,
            'models': tuple(models), 'uv_rotations': tuple(capabilities),
            'supported_names': ('minecraft:water', 'minecraft:flowing_water'),
            'side_templates': {'flowing_water_grey': (TEMPLATE, 0)},
            'world_scale': (16., 16., 16.), 'world_rotation': (0., 0., 0.),
            'max_groups': 256}


def verify_installed_resources(path, project):
    contract = json.loads(path.read_bytes())
    for relative, expected in contract['output_sha256'].items():
        installed = project / relative
        if relative in ('resource_pack/materials/entity.material', 'resource_pack/models/netease_models.json'):
            generated = json.loads((path.parent / relative).read_bytes())
            current = json.loads(installed.read_bytes())
            if relative.endswith('entity.material'):
                generated, current = generated['materials'], current['materials']
            if any(current.get(name) != value for name, value in generated.items()):
                raise ValueError('Installed liquid model/material differs from the bundle: ' + relative)
        elif digest(installed) != expected:
            raise ValueError('Installed liquid resource differs from the bundle: ' + relative)


def runtime_source(path, native, project=ROOT):
    contract = json.loads(path.read_bytes())
    snapshot = source_snapshot(native)
    if any(contract.get(key) != snapshot[key] for key in
           ('native_source_sha256', 'native_atlas_entries', 'native_flipbook_entries')):
        raise ValueError('Deployment native texture metadata differs from installed bytes')
    if contract['generator_sha256'] != digest(ROOT / 'tools/generate_liquid_skeleton_resources.py'):
        raise ValueError('Deployment resource generator differs from the concrete bundle')
    original_native = Path(contract['textures']['still_water_grey']['source']).parents[4]
    for reference, expected in contract['source_sha256'].items():
        archived = Path(reference)
        if archived.name == 'modern_projection_liquid_preview_depth.h':
            current = project / 'resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h'
        else:
            current = native / archived.relative_to(original_native)
        if digest(current) != expected:
            raise ValueError('Deployment resource source differs from the concrete bundle: ' + reference)
    for relative, expected in contract['output_sha256'].items():
        if digest(path.parent / relative) != expected:
            raise ValueError('Deployment resource bytes differ from the bundle: ' + relative)
    for key in ('still_water_grey', 'flowing_water_grey'):
        texture = contract['textures'][key]
        source = native / 'resource_packs/vanilla' / (texture['flipbook']['flipbook_texture'] + '.png')
        if digest(source) != texture['sha256']:
            raise ValueError('Deployment liquid artwork differs from installed bytes: ' + key)
    verify_installed_resources(path, project)
    resources = resource_profile(contract)
    frozen = resource_profile(contract, True)['models']
    return ('"""Generated native liquid resources; visible qualification is still required."""\n'
            'PRODUCTION_QUALIFIED = False\nQUALIFICATION_SHA256 = None\n'
            'QUALIFICATION_RESOURCE_CONTRACT_SHA256 = None\n'
            'RESOURCE_CONTRACT_SHA256 = %r\nRESOURCES = %s\nFROZEN_MODELS = %s\n' %
            (digest(path), pprint.pformat(resources, width=100, sort_dicts=True),
             pprint.pformat(frozen, width=100)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--native-data', type=Path, required=True)
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'behavior_pack/modern_projection/projection/liquid_resource_data.py')
    args = parser.parse_args()
    args.output.write_text(runtime_source(args.contract, args.native_data), encoding='ascii')
    print('Generated liquid deployment: production qualification gate closed')


if __name__ == '__main__':
    main()

"""Freeze same-alias opaque-cube controls beside an unchanged water neighborhood."""
from copy import deepcopy
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path
import shutil

from liquid_coordinate_markers import fingerprint, manifest, write
import liquid_static_coordinate_epochs as static

ROOT = Path(__file__).resolve().parents[1]
CUBE_ORIGIN = (9, 96, 4)
CUBE_NATIVE = ['minecraft:gold_block', 0]


def add_cube(source, native_reference):
    result = deepcopy(source)
    liquids = [tuple(pos) for pos, value in result['controls']['liquid_only']['cells']
               if value[0] in ('minecraft:water', 'minecraft:flowing_water')]
    if not liquids:
        raise ValueError('Opaque witness needs an independently declared water source')
    separation = min(max(abs(CUBE_ORIGIN[axis] - pos[axis]) for axis in range(3)) for pos in liquids)
    if separation < 2 or tuple(result['platform']) == CUBE_ORIGIN:
        raise ValueError('Opaque cube would alter the water height neighborhood or player platform')
    if CUBE_ORIGIN in {tuple(pos) for row in result['controls'].values() for pos, _ in row['cells']}:
        raise ValueError('Opaque cube overlaps an existing fixed control cell')
    for control in result['controls'].values():
        control['cells'] = sorted(control['cells'] + [(CUBE_ORIGIN, CUBE_NATIVE)])
        control['native_cells'] = native_reference(control['cells'])
    guard = {tuple(CUBE_ORIGIN[axis] + offset[axis] for axis in range(3))
             for offset in itertools.product((-1, 0, 1), repeat=3)}
    result['cavity'] = sorted(set(map(tuple, result['cavity'])) | guard)
    result['reserved'] = sorted(set(map(tuple, result['reserved'])) | guard)
    result.update(opaque_same_alias_cube={'position': CUBE_ORIGIN, 'native_cell': CUBE_NATIVE,
                  'atlas_tile': 'flowing_water_grey', 'minimum_source_chebyshev_distance': separation},
                  context_changed=True, source_neighbor_context_changed=False)
    return result


def check_alias(plan):
    target = ROOT / 'resource_pack/blocks.json'
    if fingerprint(target)['sha256'] != plan['cube_alias_override']['sha256']:
        raise ValueError('Same-alias opaque cube resource mapping changed')


def prepare(base, old_plan_path, grid_path):
    if base.exists():
        raise ValueError('Choose a fresh immutable same-alias experiment root')
    old = json.loads(old_plan_path.read_bytes())
    static.check(old)
    grid = json.loads(grid_path.read_bytes())
    if (grid['original_plan'] != fingerprint(old_plan_path) or not grid['no_uv_labels_or_rgb_used']
            or grid['guard_native_pixels'] != 3. or grid['minimum_selected_clearance_pixels'] < 3.):
        raise ValueError('New water samples need independent all-FOV interior geometry')
    audit = json.loads(Path(grid['v1_audit']['path']).read_bytes())
    if (fingerprint(grid['v1_audit']['path']) != grid['v1_audit']
            or not audit['prerequisites']['passed'] or audit['static_side_audit_passed']):
        raise ValueError('Original failed experiment and passed prerequisites must remain intact')
    base.mkdir(parents=True)
    backup = base / 'original-blocks.json'
    target = ROOT / 'resource_pack/blocks.json'
    shutil.copyfile(target, backup)
    mapping = json.loads(backup.read_bytes())
    if 'gold_block' in mapping:
        raise ValueError('Existing custom gold mapping is outside this isolated experiment')
    mapping['gold_block'] = {'textures': 'flowing_water_grey', 'sound': 'metal'}
    override = base / 'cube-blocks.json'
    write(override, mapping)
    plan = deepcopy(old)
    plan.update(created_at=datetime.now(timezone.utc).isoformat(), previous_static_plan=fingerprint(old_plan_path),
        previous_static_audit=grid['v1_audit'], interior_geometry=fingerprint(grid_path),
        sample_grid=grid['new_sample_grid'], cube_sample_grid=old['sample_grid'],
        cube_original_blocks=fingerprint(backup), cube_original_blocks_target=fingerprint(target),
        cube_alias_override=fingerprint(override),
        cube_surfaces=[{'cell_origin': CUBE_ORIGIN, 'corner_heights': [1.] * 4, 'side': side}
                       for side in ('north', 'west')],
        cube_scope='Opaque native unit gold cube on exact same atlas_tile. Local LOW/HIGH transfer and source/filter candidates scored independently of water. Cube V basis is degenerate and not claimed.',
        water_scope='Original static source neighbors with exact remote opaque witness; independent geometric 3px interior samples, original thresholds',
        cube_orientation_contract='Each face has its own D4 orientation; common source region, edge/center convention and sampler require independent gates',
        native_uv_accepted=False, production_accepted=False)
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location('cube_plan_fixture', ROOT / '.runtime/capture_static_water_controls_r9.py')
    fixture = module_from_spec(spec)
    spec.loader.exec_module(fixture)
    from verify_wet_actor_visuals import camera_side_platform
    for row in plan['geometry_sequences']:
        document = fixture.source_document(row['case'])
        cells = [(tuple(plan['origin'][i] + pos[i] - fixture.FOCUS[i] for i in range(3)),
                  fixture.frozen.encode(value)) for pos, value in document.blocks.items()]
        platform = camera_side_platform(cells, tuple(plan['camera_offset']))
        source = add_cube(fixture.fixture_plan(row['case'], tuple(plan['origin']), platform),
                          fixture.frozen.native_reference)
        row['controls'] = json.loads(json.dumps(source['controls']))
    for epoch, asset in plan['assets'].items():
        destination = base / 'assets' / epoch / 'water_flow_grey.png'
        destination.parent.mkdir(parents=True)
        shutil.copyfile(asset['path'], destination)
        plan['assets'][epoch] = dict(fingerprint(destination), **static.verify_strip(destination, epoch))
    plan['frozen_sources'] = deepcopy(old['frozen_sources'])
    for name in ('tools/liquid_static_cube_epochs.py', 'tools/capture_liquid_static_cube.py',
                 'tools/analyze_liquid_static_cube.py', '.runtime/static_cube_session_r11.py'):
        source, archived = ROOT / name, base / 'sources' / name
        archived.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, archived)
        plan['frozen_sources'][name] = {'live': fingerprint(source), 'archive': fingerprint(archived)}
    for ref in (plan['cube_original_blocks'], plan['cube_alias_override'], plan['interior_geometry']):
        if not Path(ref['path']).is_file():
            raise ValueError('New immutable source is absent')
    write(base / 'plan.json', plan)
    return fingerprint(base / 'plan.json')


def install(plan, epoch, receipt):
    if fingerprint(plan['cube_original_blocks']['path']) != plan['cube_original_blocks']:
        raise ValueError('Original resource backup changed')
    if fingerprint(ROOT / 'resource_pack/blocks.json') != plan['cube_original_blocks_target']:
        raise ValueError('Original blocks mapping is not restored')
    static.install(plan, epoch, receipt)
    shutil.copyfile(plan['cube_alias_override']['path'], ROOT / 'resource_pack/blocks.json')
    check_alias(plan)
    write(receipt.parent / 'cube-installed.json', {'epoch': epoch, 'original': plan['cube_original_blocks_target'],
          'installed': fingerprint(ROOT / 'resource_pack/blocks.json'), 'metadata_unchanged': True})


def restore(plan, epoch, receipt):
    check_alias(plan)
    if fingerprint(plan['cube_original_blocks']['path']) != plan['cube_original_blocks']:
        raise ValueError('Refusing to restore a changed original resource backup')
    shutil.copyfile(plan['cube_original_blocks']['path'], ROOT / 'resource_pack/blocks.json')
    static.restore(plan, epoch, receipt)
    write(receipt.parent / 'cube-restored.json', {'epoch': epoch,
          'original_blocks_bytes_restored': fingerprint(ROOT / 'resource_pack/blocks.json') == plan['cube_original_blocks_target'],
          'full_resource_manifest_equals_baseline': manifest(ROOT) == plan['baseline_resource_manifest']})


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--old-plan', type=Path, required=True)
    parser.add_argument('--grid', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.base.resolve(), args.old_plan.resolve(), args.grid.resolve())))

"""Rebuild only three measured, unqualified cube candidates in a fresh directory."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import generate_frame_block_items as generator

ITEMS = (('minecraft:stone', 0), ('minecraft:quartz_block', 0),
         ('minecraft:grass_block', 0))
CATALOG_PATH = 'tools/data/frame_block_item_measured_candidate_r21.json'
LIMITS = [
    'Pose .25 / Z .4375 comes from the measured stone, quartz and grass diagnostic clones only.',
    'The historical .5 catalog and all production resources remain separate.',
    'No universal .93 light factor or ordinary-sword glint acceptance is transferred here.',
    'Direction, rotations, absolute thickness, shared depth, lighting and material gates remain open.',
    'No special geometry, cutout, translucent or intermediate-alpha material is qualified.']


def measured_catalog(catalog, install):
    if (catalog.get('pose') != generator.POSE or catalog.get('production_qualified') is not False or
            catalog.get('qualified_materials') or catalog.get('qualification_sha256') is not None or
            catalog.get('qualification_resource_sha256') is not None):
        raise ValueError('Expected the historical unqualified catalog')
    selected = [row for row in catalog['items'] if (row['name'], row['aux']) in ITEMS]
    if (len(selected) != len(ITEMS) or
            {(row['name'], row['aux']) for row in selected} != set(ITEMS)):
        raise ValueError('Measured candidate requires exactly the three known item pairs')
    packs, blocks, terrain, sources = generator.source_records(install)
    if sources != catalog['source_sha256']:
        raise ValueError('Native source metadata changed')
    result = deepcopy(catalog)
    result.update(pose=deepcopy(generator.MEASURED_POSE), items=[], resources={}, unsupported={},
                  native_items={name: deepcopy(catalog['native_items'][name]) for name, aux in ITEMS})
    cache = {}
    for saved in selected:
        row = deepcopy(saved)
        key, entry, unused_bitmap = generator.resolve_block(
            packs, blocks, terrain, row['block_material'][0], cache, generator.MEASURED_POSE)
        original = catalog['resources'][row['resource']]
        # The historical atlas deduplicates stone with infested_stone; compare
        # exact bitmap provenance while validating this item's own native alias.
        native_faces = lambda value: {face: {key: field for key, field in record.items()
                                             if key != 'atlas_key'}
                                      for face, record in value['faces'].items()}
        if (entry['definition_key'] != row['definition_key'] or
                entry['texture_selection'] != row['texture_selection'] or
                blocks.get(original['definition_key']) != original['definition'] or
                native_faces(entry) != native_faces(original) or
                entry['rectangles'] != original['rectangles'] or entry['material'] != 'opaque'):
            raise ValueError('Measured native face provenance or material changed')
        row['resource'] = key
        result['items'].append(row)
        result['resources'][key] = entry
    return result


def resources(catalog, install):
    measured = measured_catalog(catalog, install)
    files = generator.outputs(measured, install, generator.MEASURED_POSE, ('opaque',))
    files[CATALOG_PATH] = generator.encoded(measured)
    return files, measured


def prepare(install, catalog_path, output, check=False):
    if not check and output.exists():
        raise ValueError('Use a fresh output directory')
    files, catalog = resources(generator.load(catalog_path), install)
    manifest = {'schema': 1, 'engine_version': generator.VERSION,
        'items': [list(item) for item in ITEMS], 'pose': generator.MEASURED_POSE,
        'production_qualified': False, 'qualified_materials': [],
        'catalog_sha256': generator.sha(catalog_path.read_bytes()),
        'generator_sha256': generator.sha(Path(generator.__file__).read_bytes()),
        'entry_sha256': generator.sha(Path(__file__).read_bytes()),
        'resources': sorted(catalog['resources']), 'limits': LIMITS,
        'files': {path: generator.sha(data) for path, data in sorted(files.items())}}
    files['candidate.json'] = generator.encoded(manifest)
    if check:
        stale = [relative for relative, data in files.items()
                 if not (output / relative).is_file() or (output / relative).read_bytes() != data]
        actual = {path.relative_to(output).as_posix() for path in output.rglob('*') if path.is_file()}
        if stale or actual != set(files):
            raise ValueError('Measured candidate differs: ' + repr(stale or sorted(actual ^ set(files))))
    else:
        output.mkdir(parents=True, exist_ok=False)
        for relative, data in files.items():
            path = output / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return {'prepared': not check, 'checked': check, 'output': str(output.resolve()),
            'item_pairs': len(ITEMS), 'resources': len(catalog['resources']),
            'production_qualified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, default=generator.CATALOG)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(json.dumps(prepare(args.install, args.catalog, args.output, args.check)))


if __name__ == '__main__':
    main()

"""Read the existing qualifier's BRG requirements without admission or mutation."""
import hashlib
import json
from pathlib import Path
import sys

WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(WORK))
import analyze_matrix_v2 as host


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = WORK / 'original-brg-gates-v1.json'
    assert not out.exists()
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    project = Path(binding['project'])
    sys.path.insert(0, str(project / 'tools'))
    activation = host.activate_reviewed_hosts(project)
    import qualify_water_product_r16 as q
    assert Path(q.__file__).resolve().parent == (project / 'tools').resolve()
    assert q.ROOT == project
    metadata = ('tools/data/liquid_product_owner_contract_v1.json',
                q.MODULE + 'liquid_product_owner_data.py',
                q.MODULE + 'liquid_product_qualification_data.py')
    before = {name: sha(project / name) for name in metadata}
    contract = json.loads((project / q.RESOURCE).read_bytes())
    paths = {name: WORK / ('product-v2-' + name.lower() + '-v1.json') for name in ('B', 'R', 'G')}
    rows, analyses = {}, {}
    for name, path in paths.items():
        rows[name], analyses[name] = q.collect(path, project, contract,
                                              native_world_geometry=True,
                                              native_editor_gui=True)
    q.occupancy(rows['B'])
    reverse = rows['R']
    q.require(reverse['fixture_view']['reverse_view'] is True and set(reverse['routes']) == q.ROUTES
              and q.NEIGHBORS <= set(reverse['cases']),
              'Opposite-angle water neighbors/overlap are absent')
    reverse_pixels = q.visible_rows(reverse, q.NEIGHBORS, q.ROUTES)
    fa = WORK.parent / 'water-final-matrix-v1'
    frozen_paths = (fa / 'product-v2-f-editor-v1.json', fa / 'product-v2-f-full-v2.json',
                    fa / 'product-v2-f-missing-v2.json')
    frozen = [json.loads(path.read_bytes()) for path in frozen_paths]
    frozen_rows = {label: row for report in frozen for label, row in report['rows'].items()}
    comparisons = {}
    for label, row in reverse['rows'].items():
        same_source = row['source']['cells'] == frozen_rows[label]['source']['cells']
        same_shape = row['ready']['shapes'] == frozen_rows[label]['ready']['shapes']
        q.require(same_source and same_shape, 'Opposite-angle control changed public geometry: ' + label)
        comparisons[label] = {'same_source_cells': same_source, 'same_ready_shapes': same_shape}
    gallery = rows['G']
    q.require(set(gallery['routes']) == {'editor'} and set(gallery['cases']) == {'gallery'},
              'Public water gallery was not opened in the editor')
    expected = q.source_document('gallery')
    state = gallery['rows']['editor_gallery_wet']
    q.require(tuple(state['ready']['scene_size']) == q.METADATA[3] and
              len(state['source']['cells']) == len(expected.blocks),
              'Public water gallery was cropped logically or omitted cells')
    gallery_pixels = q.visible_rows(gallery, ('gallery',), ('editor',))
    after = {name: sha(project / name) for name in metadata}
    q.require(before == after, 'Readonly inspection mutated private owner/gate')
    value = {
        'schema': 1, 'passed_original_brg_requirements': True,
        'original_qualifier_path': str(Path(q.__file__)),
        'original_qualifier_sha256': sha(Path(q.__file__)),
        'source_contract_sha256': binding['source_contract_sha256'],
        'reports': {name: {'path': str(path), 'sha256': sha(path),
                           'evidence_valid': analyses[name]['evidence_valid']}
                    for name, path in paths.items()},
        'frozen_report_sha256': {str(path): sha(path) for path in frozen_paths},
        'reverse_pixels': reverse_pixels, 'reverse_source_shape_comparisons': comparisons,
        'gallery_pixels': gallery_pixels, 'gallery_scene_size': state['ready']['scene_size'],
        'gallery_source_cells': len(state['source']['cells']),
        'gallery_expected_source_cells': len(expected.blocks), 'biome_occupancy_passed': True,
        'non_gating_geometry_diagnostics': {
            name: {key: row for key, row in analyses[name]['geometry'].items() if not row['passed']}
            for name in ('R', 'G')},
        'reviewed_host_activation': activation,
        'owner_and_qualification_unchanged': before == after,
        'inspection_host_sha256': sha(Path(__file__)), 'MC_started': False,
        'pixels_human_reviewed': False, 'qualification_performed': False,
        'manual_closures_added': 0,
    }
    with out.open('x', encoding='ascii') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'path': str(out), 'sha256': sha(out),
                      'reverse_pixels': reverse_pixels, 'gallery_pixels': gallery_pixels,
                      'gallery_source_cells': len(state['source']['cells'])}, indent=2))


if __name__ == '__main__':
    main()

"""Install clone-only page-clearance meshes without changing book depth or UVs."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from book_model_geometry import shape
from generate_liquid_product_resources import merge_registry, write_json


def prepare(project, receipt):
    registry = json.loads((project/'resource_pack/models/netease_models.json').read_bytes())
    models, files = {}, {}
    for label, clearance in (('010', .01), ('03125', .03125), ('0625', .0625), ('125', .125), ('25', .25)):
        for family in ('enchanting_table', 'lectern'):
            mesh = shape(family, 'modern_projection/book/'+family,
                         clearance if family == 'enchanting_table' else .01)
            baseline = shape(family, 'modern_projection/book/'+family)
            assert [v['uvcoord'] for v in mesh['mesh'][0]['vertices']] == [
                v['uvcoord'] for v in baseline['mesh'][0]['vertices']]
            mesh_name = 'modern_projection/book/r20_gap'+label+'_'+family+'_mesh.json'
            path = project/'resource_pack/models'/mesh_name
            write_json(path, mesh)
            files[path.relative_to(project).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            for suffix in ('', '_world'):
                base = 'modern_projection_book_'+family+suffix
                name = 'r20_book_gap'+label+'_'+base
                model = copy.deepcopy(registry[base])
                model['mesh'] = mesh_name
                models[name] = model
    merge_registry(project/'resource_pack/models/netease_models.json', models)
    result = {'schema': 1, 'product_qualified': False, 'cold_start_required': True,
              'depth_and_shaders_unchanged': True, 'uv_unchanged': True,
              'scope': 'Closed enchanting book page clearance; lectern unchanged.',
              'models': models, 'files': files}
    write_json(receipt, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.project, args.receipt)
    print(json.dumps({'models': len(result['models']), 'cold_start_required': True}))

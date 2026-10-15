"""Preinstall clone-only depth controls before a cold native book diagnostic."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from generate_liquid_product_resources import merge_registry, write_json


def prepare(project, receipt):
    registry = json.loads((project/'resource_pack/models/netease_models.json').read_bytes())
    materials = json.loads((project/'resource_pack/materials/entity.material').read_bytes())['materials']
    models, controls, files = {}, {}, {}
    for family in ('enchanting_table', 'lectern'):
        for world in (False, True):
            base = 'modern_projection_book_'+family+('_world' if world else '')
            for mode, factor in (('depth1', 1.), ('depth100', 4.), ('frozen', .04)):
                name = 'r19_book_'+mode+'_'+base
                model = copy.deepcopy(registry[base])
                material = copy.deepcopy(materials[model['material']+':entity_for_skeleton_alpha'])
                model['material'] = name
                original = (project/'resource_pack'/material['vertexShader']).read_bytes()
                token = b'clip * PROJ[2][2] * 0.04)'
                assert original.count(token) == (0 if world else 1)
                shader = original if world else original.replace(token,
                    ('clip * PROJ[2][2] * %r)' % factor).encode('ascii'))
                if mode == 'frozen':
                    shader = shader.replace(b'TOTAL_REAL_WORLD_TIME', b'10.0')
                material['vertexShader'] = 'shaders/glsl/'+name+'.vertex'
                path = project/'resource_pack'/material['vertexShader']
                path.write_bytes(shader)
                models[name] = model
                controls[name+':entity_for_skeleton_alpha'] = material
                files[path.relative_to(project).as_posix()] = {
                    'sha256': hashlib.sha256(shader).hexdigest(),
                    'base_sha256': hashlib.sha256(original).hexdigest(),
                    'preview_depth_factor': None if world else factor,
                    'time_source': '10.0' if mode == 'frozen' else 'TOTAL_REAL_WORLD_TIME'}
    merge_registry(project/'resource_pack/models/netease_models.json', models)
    merge_registry(project/'resource_pack/materials/entity.material', controls, nested=True)
    result = {'schema': 1, 'product_qualified': False, 'cold_start_required': True,
              'geometry_unchanged': True, 'normal_time': True, 'models': models,
              'materials': controls, 'shader_files': files}
    write_json(receipt, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.project, args.receipt)
    print(json.dumps({'models': len(result['models']), 'cold_start_required': True}))

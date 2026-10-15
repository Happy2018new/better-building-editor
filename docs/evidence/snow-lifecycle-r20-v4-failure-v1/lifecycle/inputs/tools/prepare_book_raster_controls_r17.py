"""Cold-load book culling controls without changing the candidate models.

Thin cover volumes need a sensitive self-occlusion control independently of
the rear-block selection outline test. All variants write depth and share one
frozen pose; only the rasterizer's face selection differs.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

from generate_liquid_product_resources import merge_registry, write_json


def raster_material(original,mode):
    material=copy.deepcopy(original)
    for field in ('states','+states','-states'):
        if field in material:
            material[field]=[state for state in material[field]
                             if state not in ('DisableDepthWrite','DisableCulling','InvertCulling')]
    material.setdefault('-states',[]).append('DisableDepthWrite')
    material.setdefault('+states' if mode=='double' else '-states',[]).append('DisableCulling')
    material.setdefault('+states' if mode=='front' else '-states',[]).append('InvertCulling')
    return material


def prepare(project, output, moving=False):
    output.mkdir(parents=True, exist_ok=False)
    registry_path = project/'resource_pack/models/netease_models.json'
    material_path = project/'resource_pack/materials/entity.material'
    registry = json.loads(registry_path.read_bytes())
    materials = json.loads(material_path.read_bytes())['materials']
    models, variants, shaders = {}, {}, {}
    for name, record in registry.items():
        if not name.startswith('modern_projection_book_'):
            continue
        original = materials[record['material']+':entity_for_skeleton_alpha']
        for mode in ('double', 'back', 'front'):
            alias = 'r17_book_'+('moving_' if moving else '')+mode+'_'+name
            model = copy.deepcopy(record)
            model['material'] = alias
            models[alias] = model
            material = raster_material(original,mode)
            for field in ('vertexShader', 'fragmentShader'):
                path = material[field]
                frozen = Path(path).with_name(('r17_book_moving_' if moving else 'r17_book_frozen_')+Path(path).name).as_posix()
                if frozen not in shaders:
                    source = (project/'resource_pack'/path).read_text(encoding='ascii')
                    shaders[frozen] = source if moving else re.sub(r'\b(?:TIME|TOTAL_REAL_WORLD_TIME)\b', '10.0', source)
                material[field] = frozen
            variants[alias+':entity_for_skeleton_alpha'] = material
    for relative, content in shaders.items():
        (project/'resource_pack'/relative).write_text(content, encoding='ascii', newline='\n')
    merge_registry(registry_path, models)
    merge_registry(material_path, variants, nested=True)
    write_json(output/'contract.json', {
        'schema': 1, 'diagnostic_only': True, 'requires_cold_start': True, 'moving': moving,
        'models': models, 'materials': variants,
        'shader_sha256': {name: hashlib.sha256((project/'resource_pack'/name).read_bytes()).hexdigest()
                          for name in shaders}})
    print(json.dumps({'models': len(models), 'materials': len(variants)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--moving', action='store_true', help='Retain the live animation shader for raster controls.')
    args = parser.parse_args()
    prepare(args.project, args.output, args.moving)

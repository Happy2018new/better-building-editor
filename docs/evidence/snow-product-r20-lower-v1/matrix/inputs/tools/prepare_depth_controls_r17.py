"""Install paired depth-state controls into a disposable 3.10 project.

Both variants are registered before cold startup. Switching the model does not
depend on material hot reload, whose success must not be inferred from disk.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from generate_liquid_product_resources import merge_registry, write_json


def resource_sources(project):
    """Fingerprint actual installed aliases and their closed resource graph."""
    registry_path=project/'resource_pack/models/netease_models.json'
    material_path=project/'resource_pack/materials/entity.material'
    registry=json.loads(registry_path.read_bytes())
    materials=json.loads(material_path.read_bytes())['materials']
    paths={registry_path,material_path}
    for name,record in registry.items():
        if not name.startswith('r17_depth_'):continue
        for key in ('mesh','skeleton'):
            paths.add(project/'resource_pack/models'/record[key])
        material=materials[record['material']+':entity_for_skeleton_alpha']
        for key in ('vertexShader','fragmentShader'):
            paths.add(project/'resource_pack'/material[key])
        for value in record['texture'].values():
            paths.add(project/'resource_pack/textures/models'/(value+'.png'))
    return {p.relative_to(project).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def prepare(project, output):
    output.mkdir(parents=True, exist_ok=False)
    registry_path=project/'resource_pack/models/netease_models.json'
    material_path=project/'resource_pack/materials/entity.material'
    registry=json.loads(registry_path.read_bytes())
    materials=json.loads(material_path.read_bytes())['materials']
    selected={name:record for name,record in registry.items()
              if name.startswith(('modern_projection_book_', 'modern_projection_portal_',
                                  'modern_projection_cauldron_'))}
    # Include every currently registered flat icon: a resource key can differ
    # from the item identifier, and diagnostics must retain that exact mapping.
    selected.update((name,record) for name,record in registry.items()
                    if record.get('material','').startswith('modern_projection_item_icon'))
    new_models,new_materials={},{}
    frozen_shaders={}
    for name,record in selected.items():
        original=record['material']+':entity_for_skeleton_alpha'
        if original not in materials:
            raise ValueError('Unrecognized native material ancestry: '+original)
        for mode in ('off','on'):
            alias='r17_depth_'+mode+'_'+name
            material_alias='r17_depth_'+mode+'_'+record['material']
            model=copy.deepcopy(record);model['material']=material_alias
            new_models[alias]=model
            value=copy.deepcopy(materials[original])
            for field in ('vertexShader','fragmentShader'):
                path=value[field]
                frozen=str(Path(path).with_name('r17_depth_frozen_'+Path(path).name)).replace('\\','/')
                if frozen not in frozen_shaders:
                    source=(project/'resource_pack'/path).read_text(encoding='ascii')
                    frozen_shaders[frozen]=re.sub(r'\b(?:TOTAL_REAL_WORLD_TIME|TIME)\b','10.0',source)
                value[field]=frozen
            for key in ('states','+states','-states'):
                if key in value:
                    value[key]=[s for s in value[key] if s!='DisableDepthWrite']
            value.setdefault('-states' if mode=='on' else '+states',[]).append('DisableDepthWrite')
            new_materials[material_alias+':entity_for_skeleton_alpha']=value
    write_json(output/'models.json',new_models)
    write_json(output/'materials.json',new_materials)
    for relative,source in frozen_shaders.items():
        path=project/'resource_pack'/relative
        path.write_text(source,encoding='ascii',newline='\n')
    merge_registry(registry_path,new_models)
    merge_registry(material_path,new_materials,nested=True)
    paths={record[field] for record in new_materials.values()
           for field in ('vertexShader','fragmentShader')}
    write_json(output/'contract.json',{
        'schema_version':1,'diagnostic_only':True,'requires_cold_start':True,
        'engine_version':'3.10.0.420447','source_models':sorted(selected),
        'registry_sha256':hashlib.sha256(registry_path.read_bytes()).hexdigest(),
        'material_sha256':hashlib.sha256(material_path.read_bytes()).hexdigest(),
        'installed_resources':resource_sources(project),
        'shaders':{p:hashlib.sha256((project/'resource_pack'/p).read_bytes()).hexdigest() for p in sorted(paths)}})
    print(json.dumps({'models':len(new_models),'materials':len(new_materials)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();prepare(args.project,args.output)

"""Generate isolated alpha/depth/clip probes; never modify release resources."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    args=parser.parse_args()
    project=args.project.resolve()
    assert project != ROOT, 'UI shader probes require an isolated project'
    registration=json.loads((ROOT/'tools/data/item_icon_registrations_nemc_3.10.0.420447.json').read_bytes())
    from importlib.util import module_from_spec,spec_from_file_location
    spec=spec_from_file_location('icon_data',ROOT/'behavior_pack/modern_projection/projection/item_icon_data.py')
    data=module_from_spec(spec)
    spec.loader.exec_module(data)
    template=registration['models'][data.ITEMS[('minecraft:diamond_sword',0)]['ui_model']]
    material=registration['materials']['modern_projection_item_icon:entity_for_skeleton_alpha']
    shader_dir=project/'resource_pack/shaders/glsl'
    vertex=(ROOT/'resource_pack/shaders/glsl/modern_projection_item_icon.vertex').read_text(encoding='ascii')
    fragment=(ROOT/'resource_pack/shaders/glsl/modern_projection_item_icon.fragment').read_text(encoding='ascii')
    registry_path=project/'resource_pack/models/netease_models.json'
    material_path=project/'resource_pack/materials/entity.material'
    registry=json.loads(registry_path.read_bytes())
    materials=json.loads(material_path.read_bytes())
    rows={}
    for name,alpha,depth,clip in (('alpha',True,False,False),('depth',False,True,False),
                                ('clip',False,False,True),('all',True,True,True)):
        prefix='modern_projection_item_ui_probe_'+name
        v,f=vertex,fragment
        if alpha:
            f=f.replace('    if(abs(PROJ[3][3])>0.5) alpha*=CURRENT_COLOR.a;\n','')
        if depth:
            v=v.replace('    itemUv=TEXCOORD_0;', '    gl_Position.z=-0.9*gl_Position.w;\n    itemUv=TEXCOORD_0;')
        if clip:
            f=f.replace(' || itemClip>0.0','')
        (shader_dir/(prefix+'.vertex')).write_text(v,encoding='ascii')
        (shader_dir/(prefix+'.fragment')).write_text(f,encoding='ascii')
        registry[prefix]=dict(template,material=prefix)
        materials['materials'][prefix+':entity_for_skeleton_alpha']=dict(material,
            vertexShader='shaders/glsl/'+prefix+'.vertex',fragmentShader='shaders/glsl/'+prefix+'.fragment')
        rows[name]={'model':prefix,'alpha_bypass':alpha,'depth_bypass':depth,'clip_bypass':clip}
    registry_path.write_text(json.dumps(registry,ensure_ascii=True,indent=2)+'\n',encoding='ascii')
    material_path.write_text(json.dumps(materials,ensure_ascii=True,indent=2)+'\n',encoding='ascii')
    print(json.dumps({'schema':1,'isolated_project':str(project),'probes':rows}))


if __name__=='__main__':
    main()

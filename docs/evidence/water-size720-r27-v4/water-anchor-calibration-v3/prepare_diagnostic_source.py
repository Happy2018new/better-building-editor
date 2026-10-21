"""Fork the frozen private source and add isolated neutral/matrix diagnostics."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
SOURCE = ROOT/'.runtime/projects/water-r25-final41-v2'
PROJECT = ROOT/'.runtime/projects/water-r27-anchor-diagnostic-v1'
OLD_BINDING = ROOT/'.runtime/round-20261022/water-size720-v3/final-source-binding-v1.json'
NAMESPACE = 'modern_projection_r27_anchor'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')


def main():
    assert not PROJECT.exists(), 'A prepared source is immutable; choose a new version'
    assert PROJECT.resolve().parent == (ROOT/'.runtime/projects').resolve()
    old=json.loads(OLD_BINDING.read_bytes())
    assert Path(old['project']).resolve()==SOURCE.resolve()
    originals=dict(old['source_sha256'],**old['auxiliary_sha256'])
    for relative,expected in originals.items():
        original=SOURCE/relative
        destination=PROJECT/relative
        assert destination.resolve().is_relative_to(PROJECT.resolve())
        assert sha(original)==expected,relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(original,destination)
    sys.path.insert(0,str(SOURCE/'tools'))
    from generate_liquid_skeleton_resources import MATRIX_VERTEX,MATRIX_FRAGMENT
    from generate_liquid_product_resources import merge_registry
    import probe_product_water as probe
    registry_path=PROJECT/'resource_pack/models/netease_models.json'
    materials_path=PROJECT/'resource_pack/materials/entity.material'
    original_registry=json.loads(registry_path.read_bytes())
    original_materials=json.loads(materials_path.read_bytes())['materials']
    template=original_registry['modern_projection_liquid_product_still_water_grey']
    vertex=(SOURCE/'resource_pack/shaders/glsl/modern_projection_liquid_product_geometry.vertex').read_text('ascii')
    assert vertex.count('entityPoint=vec4(-localPoint.x,-localPoint.z+1.5,-localPoint.y,1.0);')==1
    fragment='''// __multiversion__
precision highp float;
#include "fragmentVersionCentroidUV.h"
#include "uniformExtraVectorConstants.h"
varying highp float liquidVisible;
void main() {
    if(liquidVisible<0.5 || EXTRA_VECTOR4.w<=0.0) discard;
    gl_FragColor=vec4(0.25,0.25,0.25,1.0);
}
'''
    shader_dir=PROJECT/'resource_pack/shaders/glsl'
    files={NAMESPACE+'_15.vertex':vertex,
        NAMESPACE+'_0.vertex':vertex.replace('-localPoint.z+1.5','-localPoint.z+0.0'),
        NAMESPACE+'_neutral.fragment':fragment,
        NAMESPACE+'_matrix.vertex':MATRIX_VERTEX,
        NAMESPACE+'_matrix.fragment':MATRIX_FRAGMENT}
    for name,text in files.items():
        with (shader_dir/name).open('x',encoding='ascii',newline='\n') as stream:stream.write(text)
    additions={};materials={}
    for variant in ('15','0','matrix'):
        name=NAMESPACE+'_'+variant
        additions[name]=dict(template,material=name)
        materials[name+':entity_for_skeleton_alpha']={
            'vertexShader':'shaders/glsl/'+NAMESPACE+'_'+variant+'.vertex',
            'fragmentShader':'shaders/glsl/'+NAMESPACE+('_matrix.fragment' if variant=='matrix' else '_neutral.fragment'),
            '+states':['DisableCulling','DisableDepthWrite']}
    merge_registry(registry_path,additions)
    merge_registry(materials_path,materials,nested=True)
    after_registry=json.loads(registry_path.read_bytes())
    after_materials=json.loads(materials_path.read_bytes())['materials']
    assert all(after_registry[key]==value for key,value in original_registry.items())
    assert all(after_materials[key]==value for key,value in original_materials.items())
    before_actual=probe.snapshot_sources(SOURCE)
    assert before_actual==old['source_sha256']
    after_actual=probe.snapshot_sources(PROJECT)
    changed={key:dict(before=old['source_sha256'].get(key),after=value)
        for key,value in after_actual.items() if old['source_sha256'].get(key)!=value}
    assert len(changed)==7 and len(after_actual)==len(old['source_sha256'])+5
    assert all(sha(PROJECT/name)==expected for name,expected in old['auxiliary_sha256'].items())
    output=dict(schema=1,prepared_at_utc=datetime.now(timezone.utc).isoformat(),
        MC_started=False,production_admission_performed=False,formal_A_accepted=False,
        private_project=str(PROJECT),base_project=str(SOURCE),base_binding_sha256=sha(OLD_BINDING),
        base_source_contract_sha256=old['source_contract_sha256'],base_source_count=len(before_actual),
        source_contract_sha256=probe.snapshot_digest(after_actual),source_count=len(after_actual),
        source_sha256=after_actual,auxiliary_sha256=old['auxiliary_sha256'],
        changed_files=changed,generator_sha256=sha(Path(__file__)),
        namespace=NAMESPACE,models=additions,materials=materials,
        retained_product_owner_contract_sha256=old['owner_contract_sha256'],
        diagnostic_assets_are_not_production_qualification=True,
        new_source_is_not_complete_transitive_closure=True,
        original_source_unchanged=probe.snapshot_sources(SOURCE)==before_actual,
        existing_registry_entries_unchanged=True,existing_material_entries_unchanged=True)
    target=WORK/'diagnostic-source-v1.json'
    write(target,output)
    print(json.dumps(dict(source_count=len(after_actual),source_contract_sha256=output['source_contract_sha256'],
        preparation_sha256=sha(target),changed_files=list(changed),MC_started=False)))


if __name__=='__main__':main()

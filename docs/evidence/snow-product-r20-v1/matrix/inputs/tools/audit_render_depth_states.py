"""Inventory native material depth inheritance for version-update review.

This is a configuration audit. It does not replace actual occlusion captures,
and variant overrides are reported explicitly rather than silently ignored.
"""
import argparse
import hashlib
import json
from pathlib import Path

import json5

ROOT=Path(__file__).resolve().parents[1]


def overlay(definitions,materials,source):
    for key,value in materials.items():
        if not isinstance(value,dict):continue
        name,separator,parent=key.partition(':')
        previous=definitions.get(name,{'parent':None,'fields':{},'sources':[]})
        fields=dict(previous['fields']);fields.update(value)
        definitions[name]={'parent':parent if separator else previous['parent'],
                           'fields':fields,'sources':previous['sources']+[source]}


def resolve(definitions,name,ancestry=()):
    if name in ancestry:raise ValueError('Material inheritance cycle: '+repr(ancestry+(name,)))
    if name not in definitions:raise ValueError('Missing native material: '+name)
    row=definitions[name];fields=row['fields']
    parent=resolve(definitions,row['parent'],ancestry+(name,)) if row['parent'] else {
        'states':[],'ancestors':[],'variant_state_overrides':[]}
    states=set(fields.get('states',parent['states']))
    states.update(fields.get('+states',()))
    states.difference_update(fields.get('-states',()))
    variants=list(parent['variant_state_overrides'])
    for variant in fields.get('variants',[])+fields.get('+variants',[]):
        for key,value in variant.items():
            changes={k:value[k] for k in ('states','+states','-states') if k in value}
            if changes:variants.append({'material':name,'variant':key,'changes':changes})
    return {'states':sorted(states),'ancestors':parent['ancestors']+[name],
            'depth_write': 'DisableDepthWrite' not in states,
            'depth_test': 'DisableDepthTest' not in states,
            'variant_state_overrides':variants}


def audit(project,native):
    definitions,sources={},{}
    folders=(native/'resource_packs/vanilla/materials',
             native/'resource_packs/vanilla_netease/materials',project/'resource_pack/materials')
    declared=set()
    for folder in folders:
        for path in sorted(folder.glob('*.material')):
            relative=path.relative_to(project if folder==folders[-1] else native).as_posix()
            label=('project/' if folder==folders[-1] else 'native/')+relative
            raw=path.read_bytes()
            document=json5.loads(raw.decode('utf-8-sig'))
            materials=document.get('materials',document)
            overlay(definitions,materials,label)
            sources[label]=hashlib.sha256(raw).hexdigest()
            if folder==folders[-1]:declared.update(key.split(':')[0] for key,value in materials.items() if isinstance(value,dict))
    registry=json.loads((project/'resource_pack/models/netease_models.json').read_bytes())
    referenced={}
    for name,row in registry.items():
        material=row.get('material')
        if material:referenced.setdefault(material,[]).append(name)
    rows={};unresolved={}
    for name in sorted(declared):
        try:rows[name]=dict(resolve(definitions,name),registered_models=sorted(referenced.get(name,())))
        except ValueError as error:unresolved[name]=str(error)
    return {'schema_version':1,'engine_directory':native.parent.name,
            'scope':'Base material states; texture alpha, render order and actual visibility require runtime evidence.',
            'sources':sources,'materials':rows,'unresolved':unresolved}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=ROOT)
    parser.add_argument('--native-data',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();data=audit(args.project,args.native_data)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n',encoding='ascii')
    print(json.dumps({'materials':len(data['materials']),'unresolved':data['unresolved']}))

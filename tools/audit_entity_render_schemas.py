"""Keep per-cell native renderer evidence, including explicitly changed fixtures."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.nbt_spatial import scalar


def audit(source):
    raw=source.read_bytes()
    data=json.loads(raw)
    native=data.get('native',{})
    if (data.get('schema')!=1 or not data.get('cleanup',{}).get('cleaned') or
            native.get('game_version')!=registry.source_version() or
            native.get('palette_sha256')!=registry.fingerprint()):
        raise ValueError('A restored native capture matching the registry is required')
    records=[]
    groups={}
    for row in data['client']['rows']:
        palette=row['palette']
        value=(row['name'],row['block']['aux'])
        material=[row['name'],row['block']['aux']]
        matching=any(entry['material']==material for entry in palette['common'])
        states=next((entry['value'] for entry in palette['states'] if entry['material']==material),None)
        matching=matching and states==registry.states(value)
        payloads=palette['actor'].get(row['name'],{})
        actor=next(iter(payloads.values()),None)
        record={'material':material,'entity':scalar(row['nbt'],'id'),'verified_material_and_states':matching,
                'actor':actor,'states':states,'observed_materials':palette['common']}
        records.append(record)
        if matching:
            fields=tuple(sorted(actor)) if isinstance(actor,dict) else None
            groups.setdefault(fields,[]).append({'material':material,'entity':record['entity']})
    schemas=[{'fields':fields,'members':members} for fields,members in groups.items()]
    return {'schema_version':1,'game_version':registry.source_version(),'palette_sha256':registry.fingerprint(),
            'source_sha256':hashlib.sha256(raw).hexdigest(),'capture_completed':data['completed'],
            'scope':'default client renderer schemas, not nondefault appearance or GPU certification',
            'total_records':len(records),'verified_records':sum(row['verified_material_and_states'] for row in records),
            'records':records,'schemas':schemas}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'tools/data/native_entity_renderers_nemc_3.9.0.401155.json')
    args=parser.parse_args()
    data=audit(args.source)
    args.output.write_text(json.dumps(data,ensure_ascii=True,sort_keys=True,indent=2)+'\n',encoding='ascii')
    print('Native renderer audit: %d/%d verified cells, %d schemas, %d explicit changed cells' %
          (data['verified_records'],data['total_records'],len(data['schemas']),data['total_records']-data['verified_records']))

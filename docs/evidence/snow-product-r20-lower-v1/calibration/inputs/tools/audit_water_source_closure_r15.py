"""Read-only source closure audit for the final water qualification snapshots."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SNAPSHOTS=(('final','water-production-final310-r15-v1','launch-inputs.json','production-sources.zip'),
           ('biome','water-production-biome310-r15-v1','launch-inputs-host-v2.json','production-sources-host-v2.zip'))


def digest(value):
    return hashlib.sha256(value).hexdigest()


def normalized(value):
    return value.replace(b'\r\n',b'\n')


def audit():
    contract_path=ROOT/'tools/data/liquid_product_owner_contract_v1.json'
    contract=json.loads(contract_path.read_bytes())
    result={'schema':1,'owner_contract_sha256':digest(contract_path.read_bytes()),
            'normalization':contract['normalization'],'owners':len(contract['source_sha256']),
            'current_owner_mismatches':[],'snapshots':{},'qualification_modified':False}
    for relative,expected in contract['source_sha256'].items():
        if digest(normalized((ROOT/relative).read_bytes()))!=expected:
            result['current_owner_mismatches'].append(relative)
    for label,folder,launch_name,archive_name in SNAPSHOTS:
        evidence=ROOT/'docs/evidence'/folder
        launch=json.loads((evidence/launch_name).read_bytes())
        archive_path=evidence/archive_name
        if digest(archive_path.read_bytes())!=launch['archive']['sha256']:
            raise ValueError('Frozen source archive hash differs: '+label)
        row={'launch_sha256':digest((evidence/launch_name).read_bytes()),
             'archive_sha256':launch['archive']['sha256'],'owner_differences':{},
             'water_resource_differences':{},'water_registry_differences':{},'raw_archive_verified':False}
        with zipfile.ZipFile(archive_path) as archive:
            if set(archive.namelist())!=set(launch['source_sha256']):
                raise ValueError('Archive member names differ from the frozen launch snapshot')
            for relative,expected in launch['source_sha256'].items():
                if digest(archive.read(relative))!=expected:
                    raise ValueError('Frozen archived member changed: '+relative)
            row['raw_archive_verified']=True
            for relative,current_hash in contract['source_sha256'].items():
                frozen=normalized(archive.read(relative))
                if digest(frozen)==current_hash:
                    continue
                current=normalized((ROOT/relative).read_bytes())
                row['owner_differences'][relative]={
                    'frozen_sha256':digest(frozen),'current_sha256':digest(current),
                    'diff':''.join(difflib.unified_diff(frozen.decode('utf8').splitlines(True),
                                current.decode('utf8').splitlines(True),fromfile='frozen/'+relative,
                                tofile='current/'+relative,n=3))}
            for relative,expected in launch['source_sha256'].items():
                dedicated=(relative.startswith('resource_pack/') and 'liquid' in relative)
                data=relative=='behavior_pack/modern_projection/projection/liquid_product_resource_data.py'
                if (dedicated or data) and digest((ROOT/relative).read_bytes())!=expected:
                    row['water_resource_differences'][relative]={
                        'frozen_sha256':expected,'current_sha256':digest((ROOT/relative).read_bytes())}
            for relative,nested in (('resource_pack/models/netease_models.json',False),
                                     ('resource_pack/materials/entity.material',True)):
                frozen=json.loads(archive.read(relative));current=json.loads((ROOT/relative).read_bytes())
                if nested:
                    frozen,current=frozen['materials'],current['materials']
                keys={name for name in set(frozen)|set(current) if name.startswith('modern_projection_liquid')}
                changed=[name for name in sorted(keys) if frozen.get(name)!=current.get(name)]
                if changed:
                    row['water_registry_differences'][relative]=changed
        result['snapshots'][label]=row
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    value=audit()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n',encoding='ascii')
    print(json.dumps({'owners':value['owners'],'current_owner_mismatches':value['current_owner_mismatches'],
         'snapshots':{name:{'owner_changes':list(row['owner_differences']),
                           'water_resource_changes':row['water_resource_differences'],
                           'water_registry_changes':row['water_registry_differences']}
                      for name,row in value['snapshots'].items()}}))


if __name__=='__main__':
    main()

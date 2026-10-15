"""Freeze reviewed banner evidence before admitting its measured editor route.

Gate metadata is excluded from the implementation digest to avoid a circular
qualification fingerprint. Shader bytes, registrations, measurements and the
native profile implementation must match the actually captured bundle.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

from probe_banner_product_r16 import OWNED_SOURCES
from verify_banner_contract_r16 import contract as current_contract

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = 'tools/data/banner_render_contract_nemc310_v1.json'
GATE = 'behavior_pack/modern_projection/projection/banner_render_contract.py'
LABELS = ('editor','world','opacity')
GATES = ('editor','transform','zoom','layers','cutaway','projection_full',
         'projection_missing','occupancy','restoration','opacity','default_path')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n',encoding='ascii',newline='\n')


def collect(folder,project,label,destination):
    report=json.loads((folder/'report.json').read_bytes())
    if (report['completed'] is not True or report['restored'] is not True or
            report['source_unchanged'] is not True or report['cleanup_errors'] or
            report['fixture']!='test.entities.banners'):
        raise ValueError('Banner runtime failed or did not restore: '+label)
    for relative in OWNED_SOURCES:
        if report['source_sha256'].get(relative)!=digest(project/relative):
            raise ValueError('Banner implementation differs from actual evidence: '+relative)
    captures={}
    for name,entry in report['captures'].items():
        receipt=entry['capture']
        source=folder/Path(receipt['path']).name
        if (receipt.get('ok') is not True or receipt.get('reliable') is not True or
                receipt.get('agent_activation_allowed') is not False or
                receipt.get('activation_fallback') is not False or digest(source)!=receipt['sha256']):
            raise ValueError('Banner capture changed or was not reliable: '+name)
        captures[name]=receipt['sha256']
        if destination is not None:
            destination.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,destination/source.name)
    analysis_path=folder/'review/analysis.json'
    analysis=json.loads(analysis_path.read_bytes())
    if analysis['report_sha256']!=digest(folder/'report.json'):
        raise ValueError('Banner review belongs to a different report')
    if label=='editor' and any(row['colored_pixels']<=80 for row in analysis['rows'].values()):
        raise ValueError('Editor banner review contains too few visible pixels')
    if destination is not None:
        shutil.copyfile(folder/'report.json',destination/'report.json')
        shutil.copytree(folder/'review',destination/'review',dirs_exist_ok=True)
    return {'report_sha256':digest(folder/'report.json'),'review_sha256':digest(analysis_path),
            'captures':captures,'candidate':report['candidate']}


def set_gate(project,sha,enabled):
    path=project/GATE
    text=path.read_text(encoding='ascii')
    text=re.sub(r'^PRODUCT_QUALIFIED = .*$', 'PRODUCT_QUALIFIED = '+repr(enabled),text,flags=re.M)
    text=re.sub(r"^QUALIFICATION_SHA256 = .*$", 'QUALIFICATION_SHA256 = '+repr(sha),text,flags=re.M)
    text=re.sub(r'^GATES = .*$', 'GATES = dict((name, '+repr(enabled)+') for name in REQUIRED_GATES)',text,flags=re.M)
    path.write_text(text,encoding='ascii',newline='\n')


def run(args):
    resource=json.loads((ROOT/CONTRACT).read_bytes())
    if current_contract(args.project)!=resource:
        raise ValueError('Banner installed resource registrations differ from the frozen contract')
    evidence={}
    for label in LABELS:
        evidence[label]=collect(getattr(args,label),args.project,label,
                                None if args.admit_candidate else args.output/label)
    required={'editor':26,'world':16,'opacity':3}
    if any(len(evidence[label]['captures'])!=required[label] for label in LABELS):
        raise ValueError('Banner acceptance does not cover the complete declared matrix')
    if args.default_editor is not None:
        evidence['default_editor']=collect(args.default_editor,args.project,'default_editor',args.output/'default_editor')
        if evidence['default_editor']['candidate']:
            raise ValueError('Default banner capture injected a candidate profile')
    if not args.admit_candidate and (not args.accept_reviewed or args.default_editor is None):
        raise ValueError('Final banner admission needs reviewed default-path pixels')
    manifest={'schema_version':1,'engine_version':resource['engine_version'],
        'fixture':'test.entities.banners','stage':'isolated_candidate' if args.admit_candidate else 'product',
        'resource_contract_sha256':digest(ROOT/CONTRACT),'measurement_sha256':resource['measurement_sha256'],
        'implementation_sha256':{name:digest(args.project/name) for name in OWNED_SOURCES},
        'evidence':evidence,'gates':{name:bool(args.accept_reviewed) for name in GATES},
        'limits':['Three standing and three wall banners cover 0/3/6 authentic patterns.',
                  'Editor route is admitted only for the exact measured engine bundle.',
                  'Gate metadata differs between isolated admission and final production; renderer bytes are identical.']}
    args.output.mkdir(parents=True,exist_ok=True)
    write(args.output/'qualification.json',manifest)
    if args.admit_candidate:
        if args.project.resolve()==ROOT.resolve():
            raise ValueError('Candidate admission is allowed only in the disposable project')
        set_gate(args.project,digest(args.output/'qualification.json'),True)
    else:
        set_gate(ROOT,digest(args.output/'qualification.json'),True)
    print(json.dumps({'stage':manifest['stage'],'qualification_sha256':digest(args.output/'qualification.json')}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    for name in LABELS:
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--default-editor',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--admit-candidate',action='store_true')
    parser.add_argument('--accept-reviewed',action='store_true')
    run(parser.parse_args())


if __name__=='__main__':
    main()

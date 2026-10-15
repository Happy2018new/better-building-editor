"""Freeze reviewed portal surface evidence before enabling the exact engine."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

from probe_portal_product_r16 import SOURCES, RESOURCES

ROOT=Path(__file__).resolve().parents[1]
PROFILE='behavior_pack/modern_projection/projection/portal_profile.py'
CONTRACT='tools/data/portal_resource_contract_nemc310_v1.json'
GATES=('editor','transform','zoom','layers','cutaway','animation','projection_full',
       'projection_missing','occupancy','restoration','opacity','default_path')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metadata(text, enabled, sha):
    text=re.sub(r'^PRODUCT_QUALIFIED = .*$', 'PRODUCT_QUALIFIED = '+repr(enabled),text,flags=re.M)
    return re.sub(r'^QUALIFICATION_SHA256 = .*$', 'QUALIFICATION_SHA256 = '+repr(sha),text,flags=re.M)


def implementation(project):
    rows={name:digest(project/name) for name in SOURCES+RESOURCES}
    text=metadata((project/PROFILE).read_text(encoding='ascii'),False,'Pending')
    rows[PROFILE]=hashlib.sha256(text.encode('ascii')).hexdigest()
    return rows


def collect(folder,project,label,destination):
    report=json.loads((folder/'report.json').read_bytes())
    if (not report['completed'] or not report['restored'] or not report['source_unchanged'] or
            report['cleanup_errors'] or report['fixture']!='test.dynamic.portals'):
        raise ValueError('Portal runtime failed or was not restored: '+label)
    expected=implementation(project)
    for name in SOURCES+RESOURCES:
        actual=report['source_sha256'].get(name)
        allowed=(expected[name],digest(project/name)) if name==PROFILE else (expected[name],)
        if actual not in allowed:
            raise ValueError('Portal renderer differs from its captured source: '+name)
    captures={}
    for label_name,entry in report['captures'].items():
        receipt=entry['capture'];path=folder/Path(receipt['path']).name
        if (not receipt.get('ok') or not receipt.get('reliable') or
                receipt.get('agent_activation_allowed') is not False or
                receipt.get('activation_fallback') is not False or digest(path)!=receipt['sha256']):
            raise ValueError('Portal pixels changed or were not reliably captured: '+label_name)
        captures[label_name]=receipt['sha256']
        if destination is not None:
            destination.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,destination/path.name)
    analysis_path=folder/'review/analysis.json'
    analysis=json.loads(analysis_path.read_bytes())
    if analysis['report_sha256']!=digest(folder/'report.json'):
        raise ValueError('Portal review belongs to a different report')
    if any(row['changed_colored_pixels']<20 for group in analysis['motion'].values() for row in group):
        raise ValueError('Portal animation was not visibly recorded')
    if label!='world':
        for family in ('end_portal','end_gateway'):
            for sample in range(3):
                if analysis['rows']['editor_'+family+'_motion%d' % sample]['colored_pixels']<80:
                    raise ValueError('Portal editor texture contains too few visible pixels')
    if destination is not None:
        shutil.copyfile(folder/'report.json',destination/'report.json')
        shutil.copytree(folder/'review',destination/'review',dirs_exist_ok=True)
    return {'report_sha256':digest(folder/'report.json'),'review_sha256':digest(analysis_path),
            'captures':captures,'candidate':report['candidate'],'motion':analysis['motion']}


def set_gate(project,sha):
    path=project/PROFILE
    path.write_text(metadata(path.read_text(encoding='ascii'),True,sha),encoding='ascii',newline='\n')


def run(args):
    contract=json.loads((ROOT/CONTRACT).read_bytes())
    for name,expected in contract['output_sha256'].items():
        if name in ('resource_pack/materials/entity.material','resource_pack/models/netease_models.json'):
            continue
        if digest(args.project/name)!=expected:
            raise ValueError('Portal resource bundle differs: '+name)
    if implementation(args.project)!=implementation(ROOT):
        raise ValueError('Captured portal implementation differs from the repository')
    evidence={}
    for label in ('editor','world'):
        evidence[label]=collect(getattr(args,label),args.project,label,
            None if args.admit_candidate else args.output/label)
    if len(evidence['editor']['captures'])!=31 or len(evidence['world']['captures'])!=28:
        raise ValueError('Portal acceptance does not cover its complete declared matrix')
    if args.default_editor is not None:
        evidence['default_editor']=collect(args.default_editor,args.project,'default_editor',args.output/'default_editor')
        if evidence['default_editor']['candidate'] or len(evidence['default_editor']['captures'])!=31:
            raise ValueError('Default portal evidence injected a candidate or omitted cases')
    if not args.accept_reviewed or (not args.admit_candidate and args.default_editor is None):
        raise ValueError('Portal admission needs actual reviewed pixels and the default path')
    manifest={'schema_version':1,'engine_version':contract['engine_version'],
        'fixture':'test.dynamic.portals','stage':'isolated_candidate' if args.admit_candidate else 'product',
        'style':contract['style'],'native_parity_claimed':False,'gates':{name:True for name in GATES},
        'resource_contract_sha256':digest(ROOT/CONTRACT),'implementation_sha256':implementation(args.project),
        'evidence':evidence,'limits':['Gate metadata is excluded from the renderer fingerprint.',
            'Finite End portal and End gateway surfaces only; gateway transient activation beam remains pending.',
            'Nether portal stays on the native renderer. Teleportation and particles are outside visual adaptation.']}
    args.output.mkdir(parents=True,exist_ok=True)
    path=args.output/'qualification.json'
    path.write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n',encoding='ascii',newline='\n')
    if args.admit_candidate:
        if args.project.resolve()==ROOT.resolve():
            raise ValueError('Candidate admission must be in the disposable project')
        set_gate(args.project,digest(path))
    else:set_gate(ROOT,digest(path))
    print(json.dumps({'stage':manifest['stage'],'qualification_sha256':digest(path)}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    for name in ('editor','world','default-editor'):
        parser.add_argument('--'+name,type=Path,required=name!='default-editor')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--admit-candidate',action='store_true')
    parser.add_argument('--accept-reviewed',action='store_true')
    run(parser.parse_args())


if __name__=='__main__':main()

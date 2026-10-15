"""Preserve bounded slab/portal observations without granting product admission."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n', encoding='ascii', newline='\n')


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def freeze(source, destination, project, source_root):
    report = json.loads(source.read_bytes())
    if not all(report.get(key) is True for key in ('completed', 'restored', 'source_unchanged')):
        raise ValueError('Incomplete or unrestored observation: '+str(source))
    if report.get('cleanup_errors') != []:
        raise ValueError('Observation has cleanup errors: '+str(source))
    destination.mkdir(parents=True)
    copy(source, destination/'report.json')
    for label, entry in report['captures'].items():
        receipt = entry.get('capture', entry)
        path = source.parent/Path(receipt['path']).name
        if not receipt.get('reliable') or digest(path) != receipt['sha256']:
            raise ValueError('Changed or unreliable capture: '+label)
        copy(path, destination/path.name)
        copy(path.with_suffix('.capture.json'), destination/path.with_suffix('.capture.json').name)
    for relative, expected in report['source_sha256'].items():
        path = project/relative
        if digest(path) != expected:
            raise ValueError('Project no longer matches captured source: '+relative)
        copy(path, source_root/relative)
    return {'captures': len(report['captures']), 'pixel_acceptance': report.get('pixel_acceptance', False),
            'report_sha256': digest(source)}


def verify(folder):
    manifest = json.loads((folder/'manifest.json').read_bytes())
    actual = {p.relative_to(folder).as_posix(): digest(p)
              for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    if actual != manifest:
        raise ValueError('Checkpoint contents differ from manifest')
    print(json.dumps({'files': len(actual), 'manifest_verified': True, 'product_admission': False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--slab-pointer', type=Path)
    parser.add_argument('--slab-world', type=Path)
    parser.add_argument('--portal-reference', type=Path)
    parser.add_argument('--adapter', type=Path)
    parser.add_argument('--state-map', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        verify(args.output)
        return
    if any(getattr(args, name) is None for name in
           ('project', 'slab_pointer', 'slab_world', 'portal_reference', 'adapter', 'state_map')):
        parser.error('Packing requires all declared inputs')
    args.output.mkdir(parents=True, exist_ok=False)
    index = {'product_admission': False, 'observations': {}}
    for label, report in (('slab-pointer', args.slab_pointer), ('slab-world', args.slab_world),
                          ('portal-reference', args.portal_reference)):
        index['observations'][label] = freeze(report, args.output/label, args.project, args.output/'sources')
    contract = json.loads((args.adapter/'contract.json').read_bytes())
    for relative, expected in contract['output_sha256'].items():
        if digest(args.adapter/relative) != expected or digest(args.project/relative) != expected:
            # The two shared registries also contain pre-existing product entries.
            if relative not in ('resource_pack/models/netease_models.json', 'resource_pack/materials/entity.material'):
                raise ValueError('Diagnostic adapter differs: '+relative)
        copy(args.adapter/relative, args.output/'adapter'/relative)
    copy(args.adapter/'contract.json', args.output/'adapter/contract.json')
    states = json.loads(args.state_map.read_bytes())
    if not states.get('read_only') or not states.get('completed') or len(states['state_mapping']) != 384:
        raise ValueError('Shelf state observation is incomplete')
    copy(args.state_map, args.output/'shelf-state-map.json')
    root = Path(__file__).resolve().parents[1]
    for name in ('probe_slab_interactions_r19.py', 'probe_portal_reference_r19.py',
                 'generate_portal_native_adapter_r19.py', 'probe_shelf_native_shape_r17.py',
                 'pack_root_visual_checkpoint_r20.py'):
        copy(root/'tools'/name, args.output/'host-tools'/name)
    (args.output/'.gitattributes').write_text('* -text -diff whitespace=cr-at-eol\n', encoding='ascii', newline='\n')
    (args.output/'README.md').write_text(
        '# R20 bounded slab and portal checkpoint\n\n'
        'Target: NEMC 3.10.0.420447. This package does not grant product admission.\n\n'
        '- Slab pointer: 14 live Scene callback cases; physical input and full pixel acceptance remain false.\n'
        '- Slab world: viewed full/missing public galleries, without a freshness or occupancy acceptance claim.\n'
        '- Portal: corrected native star texture and verbatim fragment, ten applicable visible surfaces; '
        'two level End portal views are edge-on. Candidate brightness remains above native.\n'
        '- Shelf: read-only API mapping of 384 states, not visual or connected-group qualification.\n\n'
        'Capture reports and original PNG receipts retain their acquisition paths. Packaged PNG siblings '
        'are authoritative for portable reads. Source snapshots are the declared report files, '
        'not a complete executable import closure. Host tools are checkpoint snapshots; the slab '
        'reports did not record a host SHA at acquisition. Prior failed white/grass portal captures '
        'remain in private runtime storage and must not be treated as valid references.\n\n'
        'Verify all packaged bytes with:\n\n```powershell\n'
        'python tools/pack_root_visual_checkpoint_r20.py --verify --output '
        'docs/evidence/root-visual-r20-v1\n```\n', encoding='ascii', newline='\n')
    write(args.output/'index.json', index)
    write(args.output/'manifest.json', {p.relative_to(args.output).as_posix(): digest(p)
                                      for p in args.output.rglob('*') if p.is_file()})
    verify(args.output)


if __name__ == '__main__':
    main()

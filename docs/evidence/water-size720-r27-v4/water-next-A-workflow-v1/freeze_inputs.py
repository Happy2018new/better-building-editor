"""Write a fresh source inventory for a candidate attempt, never acceptance data."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
OWNER_FILES = ('tools/data/liquid_product_owner_contract_v1.json',
               'behavior_pack/modern_projection/projection/liquid_product_owner_data.py',
               'behavior_pack/modern_projection/projection/liquid_product_qualification_data.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()


def inventory(project):
    # Match actual probe.snapshot_sources; do not import the probe or SDK to enumerate.
    paths = [path for folder in ('behavior_pack', 'resource_pack')
             for path in (project / folder).rglob('*')
             if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo')]
    paths += list((project / 'tools').glob('*.py'))
    paths += list((project / '.agents/skills/pyreact-debugging/scripts').glob('*.py'))
    return {path.relative_to(project).as_posix(): sha(path) for path in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--auxiliary-template', type=Path, required=True)
    parser.add_argument('--host-binding', type=Path, action='append', default=[])
    parser.add_argument('--source-metadata', type=Path, action='append', default=[])
    args = parser.parse_args()
    assert not args.output.exists(), 'Never reuse an old attempt manifest'
    project = args.project.resolve(strict=True)
    owner_before = {name: sha(project / name) for name in OWNER_FILES}
    snapshot = inventory(project)
    template = json.loads(args.auxiliary_template.read_bytes())
    # The names define explicit auxiliary scope only. Hash new project bytes afresh.
    auxiliary = {name: sha(project / name) for name in template['auxiliary_sha256']}
    spec = importlib.util.spec_from_file_location('_water_actual_probe_inventory', project / 'tools/probe_product_water.py')
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    assert probe.snapshot_sources(project) == snapshot
    assert probe.snapshot_digest(snapshot) == contract(snapshot)
    host_bindings = []
    for path in args.host_binding:
        binding = json.loads(path.read_bytes())
        records = dict(binding.get('sources', {}))
        for relative, expected in binding.get('external_host_sha256', {}).items():
            records[str(ROOT / relative)] = expected
        for name, expected in binding.get('host_sha256', {}).items():
            records[str(path.parent / name)] = expected
        if 'binary' in binding:
            records[binding['binary']['path']] = binding['binary']['sha256']
        for name, expected in records.items():
            assert sha(Path(name)) == expected, 'Bound host source differs: ' + name
        host_bindings.append({'path': str(path.resolve()), 'sha256': sha(path),
                              'explicit_bound_files': records,
                              'is_complete_transitive_closure': False})
    try:
        head = subprocess.run(['git', '-C', str(project), 'rev-parse', 'HEAD'],
                              capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError:
        head = None
    report = {
        'schema': 1, 'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
        'project': str(project), 'source_root_head': head,
        'source_contract_sha256': contract(snapshot), 'source_sha256': snapshot,
        'auxiliary_sha256': auxiliary,
        'source_count': len(snapshot), 'auxiliary_count': len(auxiliary),
        'inventory_matches_actual_probe': True,
        'scope': 'All behavior/resource regular files plus probe-enumerated tools and explicit auxiliary paths',
        'is_complete_transitive_dependency_closure': False,
        'host_bindings': host_bindings,
        'source_metadata_only': [{'path': str(path.resolve()), 'sha256': sha(path),
                                  'actual_runtime_dependency': False} for path in args.source_metadata],
        'owner_and_qualification_preserved_sha256': owner_before,
        'qualification_hash_recomputed_or_copied': False,
        'production_admission_performed': False, 'default_path_evidence': False,
        'formal_A_accepted': False, 'MC_started': False,
        'prior_acceptance_evidence_reused': False,
        'generator_sha256': sha(Path(__file__)),
    }
    assert inventory(project) == snapshot
    assert all(sha(project / name) == value for name, value in auxiliary.items())
    assert all(sha(project / name) == value for name, value in owner_before.items())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf8', newline='\n') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps({'source_count': len(snapshot), 'auxiliary_count': len(auxiliary),
                      'source_contract_sha256': report['source_contract_sha256'],
                      'manifest_sha256': sha(args.output), 'MC_started': False,
                      'owner_and_qualification_written': False}))


if __name__ == '__main__':
    main()

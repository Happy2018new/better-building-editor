"""Copy only the enumerated frozen inputs and apply three reviewed private files."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
MANIFEST = WORK.with_name('water-anchor-calibration-v1') / 'diagnostic-source-v1.json'
PROJECT = ROOT / '.runtime/projects/water-r27-gui-offset-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not PROJECT.exists(), 'Private source is immutable after preparation'
    original = json.loads(MANIFEST.read_bytes())
    candidate = json.loads((WORK / 'candidate-v1.json').read_bytes())
    assert sha(MANIFEST) == candidate['base_manifest_sha256']
    base = Path(original['private_project'])
    expected = dict(original['source_sha256'], **original['auxiliary_sha256'])
    for relative, fingerprint in expected.items():
        source, destination = base / relative, PROJECT / relative
        assert destination.resolve().is_relative_to(PROJECT.resolve())
        assert sha(source) == fingerprint, relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    for relative, row in candidate['changed_files'].items():
        assert sha(PROJECT / relative) == row['base_sha256']
        revised = WORK / 'candidate' / relative
        assert sha(revised) == row['candidate_sha256']
        (PROJECT / relative).write_bytes(revised.read_bytes())
    sys.path.insert(0, str(base / 'tools'))
    import probe_product_water as probe
    actual = probe.snapshot_sources(PROJECT)
    assert set(actual) == set(original['source_sha256'])
    changed = {name: {'before': original['source_sha256'][name], 'after': value}
               for name, value in actual.items() if original['source_sha256'][name] != value}
    assert set(changed) == set(candidate['changed_files'])
    assert all(sha(PROJECT / name) == value for name, value in original['auxiliary_sha256'].items())
    assert all(sha(base / name) == value for name, value in expected.items())
    report = {'schema': 1, 'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
              'private_project': str(PROJECT), 'base_project': str(base),
              'base_manifest_sha256': sha(MANIFEST), 'candidate_manifest_sha256': sha(WORK / 'candidate-v1.json'),
              'base_source_contract_sha256': original['source_contract_sha256'],
              'source_contract_sha256': probe.snapshot_digest(actual), 'source_count': len(actual),
              'source_sha256': actual, 'auxiliary_sha256': original['auxiliary_sha256'],
              'changed_files': changed, 'original_source_unchanged': True,
              'new_source_is_not_complete_transitive_closure': True,
              'retained_product_owner_contract_sha256': original['retained_product_owner_contract_sha256'],
              'MC_started': False, 'production_admission_performed': False,
              'formal_A_accepted': False, 'manual_closures_added': 0,
              'shared_production_source_written': False, 'original_contracts_modified': False}
    with (WORK / 'private-source-v1.json').open('x', encoding='utf-8', newline='\n') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps({'private_project': str(PROJECT), 'source_count': len(actual),
                      'source_contract_sha256': report['source_contract_sha256'],
                      'manifest_sha256': sha(WORK / 'private-source-v1.json'), 'MC_started': False}))


if __name__ == '__main__':
    main()

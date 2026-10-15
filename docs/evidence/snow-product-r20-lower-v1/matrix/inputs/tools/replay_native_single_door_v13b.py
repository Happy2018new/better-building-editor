"""Rescore preserved V13b observations offline without changing native receipts."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import probe_native_single_door as corrected

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tools/data/native_single_door_observed_r11_v13b'


def source_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(directory=DATA):
    original_path = directory / 'probe.json'
    original_bytes = original_path.read_bytes()
    original = json.loads(original_bytes)
    spec = importlib.util.spec_from_file_location('frozen_single_door_v13b_scorer',
                                                 directory / 'probe_native_single_door.py')
    frozen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frozen)
    rows, support = original['requested'], original['support']
    legacy = [step['legacy_aux'] for step in original['setup']['steps'] if step['method'] == 'SetBlockNew']
    report = {'schema': 1, 'scope': 'Offline replay of already captured V13b single-pair observations',
              'new_native_calls': 0, 'new_sdk_calls': 0, 'new_launches': 0,
              'source_probe_sha256': source_sha(original_path),
              'original_scorer_sha256': source_sha(directory / 'probe_native_single_door.py'),
              'corrected_scorer_sha256': source_sha(Path(corrected.__file__)),
              'replay_source_sha256': source_sha(Path(__file__)),
              'original_verdicts': {key: original[key] for key in
                  ('data_replication_verified', 'client_typed_pair_verified', 'physical_orientation_accepted')},
              'physical_orientation_accepted': False, 'client_typed_pair_verified': False,
              'capture_reliable': False, 'production_mapping_changed': False, 'observations': {}}
    for stage in ('after_200ms', 'later'):
        observation = original[stage]
        raw = corrected.thaw(observation['client']['palettes']['pair']['serialized'])
        previous = frozen.diagnose_pair(observation['server'], observation['client'], rows, support, legacy)
        diagnosis = corrected.diagnose_pair(observation['server'], observation['client'], rows, support, legacy)
        covered = corrected.palette_rows(observation['client'], rows)
        report['observations'][stage] = {
            'thawed_metadata_key_types': sorted({type(key).__name__ for key in raw}),
            'text_volume_lookup': raw.get('volume'), 'byte_volume_lookup': raw.get(b'volume'),
            'original_diagnosis': original['diagnosis'][stage],
            'original_diagnosis_reproduced': previous == original['diagnosis'][stage],
            'corrected_offline_diagnosis': diagnosis,
            'observed_palette_rows': [covered[index] for index in sorted(covered)]}
    report['original_bytes_unchanged'] = original_bytes == original_path.read_bytes()
    report['data_replication_verified_from_existing_observations'] = all(
        row['corrected_offline_diagnosis']['data_replication_verified'] for row in report['observations'].values())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=DATA)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Offline replay output must be fresh')
    report = replay(args.directory)
    corrected.shapes.write(args.output, report)
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()

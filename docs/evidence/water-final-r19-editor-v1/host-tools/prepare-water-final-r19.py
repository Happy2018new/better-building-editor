"""Sync one final cold project and record root equality without changing root inputs."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path('D:/bbe-r18-water-production')
OUTPUT = ROOT / '.runtime/water-final-r19-v1'
sys.path.insert(0, str(ROOT / 'tools'))
from probe_product_water import snapshot_digest, snapshot_sources


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    before = snapshot_sources(ROOT)
    old = snapshot_sources(PROJECT)
    if set(old) - set(before):
        raise ValueError('Unexpected clone-only inputs require inspection')
    changed = sorted(name for name, value in before.items() if old.get(name) != value)
    for name in changed:
        target = PROJECT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    extras = ['tools/data/liquid_product_owner_contract_v1.json']
    extras.extend(path.relative_to(ROOT).as_posix() for path in
                  (ROOT / 'tools/native_wgc').iterdir() if path.is_file())
    for name in extras:
        target = PROJECT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    after_root, after_project = snapshot_sources(ROOT), snapshot_sources(PROJECT)
    if before != after_root or before != after_project:
        raise ValueError('Final source sync changed during the copy or differs')
    configs = {}
    for key, project in (('root', ROOT), ('cold_project', PROJECT)):
        path = project / '.mcdev.json'
        configs[key] = {'sha256': digest(path), 'content': json.loads(path.read_bytes())}
    report = {'schema': 1, 'root_project': str(ROOT), 'cold_project': str(PROJECT),
              'root_equals_cold_project': True, 'source_files': len(before),
              'source_contract_sha256': snapshot_digest(before), 'changed_paths': changed,
              'extra_copied_sha256': {name: digest(ROOT / name) for name in extras},
              'mcdev_configs': configs,
              'configuration_scope': 'Identical product/source/resources/tools; cold project disables hot reload and fixes seed/world/mode',
              'production_qualified': False}
    (OUTPUT / 'sync.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps({'synced': len(changed), 'files': len(before),
                      'root_equals_cold_project': True,
                      'source_contract_sha256': snapshot_digest(before)}))


if __name__ == '__main__':
    main()
